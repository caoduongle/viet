# Feature Specification: Preserve Markdown Ordered List Start Numbering

**Feature Branch**: `010-markdown-ordered-list-start`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User feedback: "Bảo toàn start của ordered list trong Markdown importer khi danh sách có số bắt đầu khác 1 hoặc bị gián đoạn bởi khối không thụt lề (bảng, đoạn văn)."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Start Number for Ordered Lists Split by Unindented Blocks (Priority: P1) 🎯 MVP

When writing Markdown notes or documents, users frequently interrupt numbered lists with un-indented blocks such as GFM tables, diagrams, or notes:
```markdown
1. Bước một
2. Bước hai
3. Theo loài:
| species | n |
|---|---|
| Adelie | 10 |
4. Bước bốn
5. Bước năm
```
Because the table is unindented, standard Markdown parsers (`markdown-it-py`) close the first ordered list and open a second `ordered_list_open` with attribute `start="4"`. The system must preserve `start=4` so the final rendered output displays items 4 and 5 as `4. Bước bốn` and `5. Bước năm` instead of resetting to `1. Bước bốn` and `2. Bước năm`.

**Why this priority**: Without this capability, document numbering becomes corrupted and misleading whenever lists are separated by tables, code blocks, or formulas. This is a critical structural fidelity bug in Markdown document import.

**Independent Test**: Parse a markdown string containing an ordered list with custom start (or interrupted by a table), assert that the resulting `ListBlock.start` matches the Markdown source number, and assert that rendered line prefixes contain the correct numbers (`4. `, `5. `).

**Acceptance Scenarios**:
1. **Given** a Markdown document with an ordered list starting at number 4 (`4. D\n5. E`), **When** imported via `MarkdownImporter`, **Then** the resulting `ListBlock` has `ordered=True` and `start=4`.
2. **Given** a Markdown document with a list interrupted by a table (`1. A\n2. B\n| x |\n|---|\n| 1 |\n3. C`), **When** imported and converted to Document IR, **Then** the first `ListBlock` has `start=1` and the second `ListBlock` has `start=3`.
3. **Given** a converted Document IR containing `ListBlock(ordered=True, start=4)`, **When** rendered by `DocumentLayoutEngine`, **Then** the items are prefixed with `4. ` and `5. ` in the handwriting strokes.

---

### User Story 2 - Resilient Parsing of Token Attributes (Priority: P2)

The parser must safely inspect token attributes across different versions and internal representations of `markdown-it-py` (attribute dictionaries, attribute lists, or helper methods like `tok.attrGet()`), and handle non-numeric or missing attributes without crashing.

**Why this priority**: Guarantees parser stability and robustness against malformed or missing attributes.

**Independent Test**: Execute unit tests passing various token structures (dict, list of pairs, missing attribute, non-integer string) and verify clean fallback to `start=1`.

**Acceptance Scenarios**:
1. **Given** an `ordered_list_open` token with `attrs={"start": "10"}`, **When** processed, **Then** `start` is parsed as integer `10`.
2. **Given** an `ordered_list_open` token with `attrs=[("start", "7")]`, **When** processed, **Then** `start` is parsed as integer `7`.
3. **Given** an `ordered_list_open` token with no `attrs` or `attrs={"start": "invalid"}`, **When** processed, **Then** `start` gracefully falls back to `1` without raising exceptions.

---

### User Story 3 - End-to-End Multi-Block Document Integrity (Priority: P3)

Users exporting real-world assignment, problem-set, or lecture note documents containing headings, lists, tables, and continuing numbered lists must produce `.xopp` documents that accurately reflect the sequential logic of the source text.

**Why this priority**: Validates that the full pipeline (Importer -> Document IR -> Layout Engine -> PageBuffer -> XOPP) maintains numbering fidelity end-to-end.

**Independent Test**: Run CLI conversion on a Markdown document with split lists and inspect the generated XML layer to verify stroke sequences corresponding to item prefixes.

**Acceptance Scenarios**:
1. **Given** a realistic test fixture containing numbered questions interrupted by tables, **When** compiled via CLI to `.xopp`, **Then** the CLI finishes with exit code 0 and the numbering sequence is preserved.

---

### Edge Cases

- **Unordered lists (`bullet_list_open`)**: Must ignore any `start` attribute and maintain bullet formatting (`- `).
- **Negative or zero start numbers**: If Markdown explicitly specifies `0. Item`, `start` should be parsed as `0` and render `0. Item`.
- **Nested ordered lists**: Child ordered lists inside a list item must independently parse and maintain their own `start` numbers without inheriting or overwriting parent list numbering.
- **Lists with arbitrary jump**: A list starting at `99. Ninety-nine` must preserve `start=99`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `MarkdownImporter` MUST inspect `ordered_list_open` tokens for the `start` attribute.
- **FR-002**: `MarkdownImporter` MUST parse the `start` attribute to an integer and pass `start=start` when instantiating `ListBlock`.
- **FR-003**: If `start` is absent, `None`, empty, or cannot be parsed as an integer, `MarkdownImporter` MUST default `start` to `1`.
- **FR-004**: `MarkdownImporter` MUST handle both dictionary-style `tok.attrs` and list-of-tuples `tok.attrs` (or use `tok.attrGet("start")`).
- **FR-005**: `DocumentLayoutEngine` MUST preserve and use `block.start` when formatting item prefixes (`f"{block.start + idx}. "`).
- **FR-006**: Bullet lists (`bullet_list_open`) MUST continue to produce `ordered=False` with prefix `- `.

---

### Key Entities

- **`ListBlock`**: Document IR dataclass representing a sequence of items, with attributes:
  - `items: list[list[Block]]`: Nested blocks per list item.
  - `ordered: bool`: Whether the list is numbered (`True`) or bulleted (`False`).
  - `start: int`: Starting number for the first item in the list (default `1`).
- **`MarkdownImporter`**: Importer converting parsed Markdown tokens into Document IR blocks.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of ordered lists with custom or split start numbers in Markdown preserve their starting index in Document IR.
- **SC-002**: For test cases with split lists (`1..3`, `Table`, `4..5`), the second list is verified to render with prefixes `4. ` and `5. `.
- **SC-003**: 0 crashes or unhandled exceptions when encountering malformed or absent `start` attributes.
- **SC-004**: 100% pass rate across the automated test suite (all 334+ existing tests remain green).

---

## Assumptions

- Standard CommonMark / GFM behavior sets the `start` attribute on `ordered_list_open` tokens when the list starts at a number other than 1.
- In Markdown source text, mathematical expressions written without dollar delimiters `$...$` (e.g. `(1+2)/3 = 1`) are treated as plain handwriting text rather than `MathInline`/`MathBlock`, which is expected behavior.
- Document IR already supports `start: int = 1` in `ListBlock`, and `DocumentLayoutEngine` already formats `f"{block.start + idx}. "`; only the importer layer currently drops the attribute.
