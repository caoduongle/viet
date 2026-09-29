# Data Model: Markdown List Numbering & Document IR

**Feature Branch**: `010-markdown-ordered-list-start`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md)

---

## 1. Document IR Entity: `ListBlock`

The `ListBlock` class in `chuviettay.document.ir` encapsulates an ordered or unordered list of items.

```mermaid
classDiagram
    class Block {
        <<abstract>>
    }
    class ListBlock {
        +list[list[Block]] items
        +bool ordered
        +int start
    }
    class Paragraph {
        +list[Inline] inlines
    }
    Block <|-- ListBlock
    Block <|-- Paragraph
    ListBlock o-- Block : contains items
```

### Fields
| Field | Type | Default | Description |
|---|---|---|---|
| `items` | `list[list[Block]]` | Required | List of item content blocks. Each item can contain one or more blocks (typically `Paragraph`). |
| `ordered` | `bool` | `False` | Whether the list is numbered (`True`) or bulleted (`False`). |
| `start` | `int` | `1` | The starting integer for item numbering when `ordered=True`. |

### Invariants
1. For an ordered list with $K$ items starting at $S = \text{start}$, item $i \in [0, K-1]$ is prefixed with $(S + i)$.
2. If `ordered == False`, `start` has no effect on rendering (bullet `- ` is always used).
3. `start` can be any integer ($\ge 0$, or negative if explicitly declared in source).

---

## 2. Token Stream Mapping

```mermaid
flowchart LR
    MD["Markdown Source Text"] --> Parser["markdown-it-py Parser"]
    Parser --> Token["Token: ordered_list_open\nattrs={'start': N}"]
    Token --> Importer["MarkdownImporter._process_tokens()"]
    Importer --> IR["Document IR: ListBlock(ordered=True, start=N)"]
    IR --> LayoutEngine["DocumentLayoutEngine.render()"]
    LayoutEngine --> Rendered["Rendered Output:\n'N. Item 1'\n'(N+1). Item 2'"]
```

### Token to Entity Translation
| Markdown Syntax | `markdown-it-py` Token | Token Attributes | Resulting `ListBlock` | Rendered Line Prefix |
|---|---|---|---|---|
| `1. A`<br>`2. B` | `ordered_list_open` | `{}` (or `None`) | `ListBlock(ordered=True, start=1)` | `1. A`<br>`2. B` |
| `4. D`<br>`5. E` | `ordered_list_open` | `{'start': 4}` | `ListBlock(ordered=True, start=4)` | `4. D`<br>`5. E` |
| `0. Zero` | `ordered_list_open` | `{'start': 0}` | `ListBlock(ordered=True, start=0)` | `0. Zero` |
| `- A`<br>`- B` | `bullet_list_open` | `{}` | `ListBlock(ordered=False, start=1)` | `- A`<br>`- B` |
