# Research: Markdown Ordered List Start Numbering Preservation

**Feature Branch**: `010-markdown-ordered-list-start`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md)

---

## 1. Problem Investigation & Root Cause

### 1.1 CommonMark / GFM List Parsing Behavior
In CommonMark and GitHub Flavored Markdown (GFM), lists require indentation to contain nested blocks. When a block element (such as a table or paragraph) is written without indentation:

```markdown
1. First
2. Second
3. Third:
| species | n |
|---|---|
| Gentoo | 2 |
4. Fourth
5. Fifth
```

Because the table starts at column 0 without indentation, `markdown-it-py` terminates the first ordered list and emits `ordered_list_close`. When it reaches `4. Fourth`, it opens a new list by emitting `ordered_list_open`.

Under the CommonMark specification, when an ordered list does not start at 1, the parser attaches an attribute `start` with the starting number:
- Token 1: `type='ordered_list_open', attrs={}, attrGet('start')=None`
- Token 2: `type='ordered_list_open', attrs={'start': 4}, attrGet('start')=4`

### 1.2 Inspection of `chuviettay/importer/markdown_importer.py`
Examining lines 114–132 of `markdown_importer.py`:
```python
elif tok.type in ("bullet_list_open", "ordered_list_open"):
    is_ordered = (tok.type == "ordered_list_open")
    items: list[list[Block]] = []
    # ... loops over list items ...
    blocks.append(ListBlock(ordered=is_ordered, items=items))
```
Notice that:
1. `tok.attrs` or `tok.attrGet("start")` is completely ignored.
2. `ListBlock` is instantiated without the `start` argument.
3. In `chuviettay/document/ir.py`:
   ```python
   @dataclass
   class ListBlock(Block):
       items: list[list[Block]]
       ordered: bool = False
       start: int = 1
   ```
   `start` defaults to `1`.
4. As a result, the second list is assigned `start=1`.

### 1.3 Inspection of `chuviettay/layout/engine.py`
Examining lines 240–248 of `engine.py`:
```python
elif isinstance(block, ListBlock):
    for idx, item_blocks in enumerate(block.items):
        pfx = f"{block.start + idx}. " if block.ordered else "- "
        # ... renders text line with prefix ...
```
The layout engine already calculates `pfx = f"{block.start + idx}. "`.
Therefore, the bug is isolated to `MarkdownImporter` dropping the `start` attribute during token parsing.

---

## 2. Technical Evaluation & Attribute Extraction Strategy

### 2.1 API Compatibility across `markdown-it-py` Versions
`markdown-it-py` provides multiple ways to access token attributes:
1. `tok.attrGet(name: str)`: Standard helper returning the attribute value or `None`.
2. `tok.attrs`: Dictionary or list depending on initialization:
   - In modern `markdown-it-py` (v2, v3, v4), `tok.attrs` is a `dict[str, Any]` (e.g. `{'start': 4}`).
   - In JavaScript Markdown-it and some mock environments, `tok.attrs` can be a list of `[name, value]` tuples (e.g. `[['start', 4]]`).

### 2.2 Resilient Extraction Algorithm
To ensure 100% reliability and prevent crashes under any environment or mock:
```python
start = 1
if is_ordered:
    raw_start = tok.attrGet("start") if hasattr(tok, "attrGet") else None
    if raw_start is None and tok.attrs:
        if isinstance(tok.attrs, dict):
            raw_start = tok.attrs.get("start")
        elif isinstance(tok.attrs, list):
            for item in tok.attrs:
                if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "start":
                    raw_start = item[1]
                    break
    if raw_start is not None:
        try:
            start = int(raw_start)
        except (ValueError, TypeError):
            start = 1
```

### 2.3 Edge Cases Tested
1. **Unordered Lists (`bullet_list_open`)**:
   `is_ordered == False`. `start` is kept at default 1 and ignored during bullet formatting (`- `).
2. **Missing `start` Attribute**:
   When list starts at 1, `raw_start` is `None` -> defaults cleanly to `1`.
3. **Custom Non-1 Starts**:
   - `4. D` -> `start=4`
   - `10. Item` -> `start=10`
   - `0. Zero` -> `start=0`
4. **Malformed Attribute Value**:
   - `attrs={'start': 'invalid'}` -> `int()` raises `ValueError` -> caught and safely set to `1`.

---

## 3. Conclusions & Implementation Plan

1. Modify `chuviettay/importer/markdown_importer.py` at `ordered_list_open` to extract `start` using the resilient extraction algorithm and pass `start=start` to `ListBlock`.
2. Create unit tests in `tests/test_markdown_importer.py` asserting `ListBlock.start` preservation on split lists, custom start lists, and malformed attributes.
3. Validate end-to-end rendering in `tests/test_cli_format.py` ensuring output prefixes render `4. `, `5. ` properly.
