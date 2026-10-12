# Data Model: Table Content Continuation Across Pages & Layout Geometry

**Feature**: `specs/033-table-content-continuation-and-geometry`
**Date**: 2026-10-12
**Status**: Completed

---

## Entities & Data Structures

### 1. LaidOutCell

Represents a positioned table cell within a specific page slice, containing its geometric coordinates, cell spans, and rendered content lines for that slice.

```python
@dataclass
class LaidOutCell:
    x: float
    y: float
    width: float
    height: float
    text_lines: list[str]
    cell: TableCell | None = None
    col: int = 0
    row: int = 0
    colspan: int = 1
    rowspan: int = 1
    rendered_lines: list[Any] = field(default_factory=list)
    line_metrics: list[LineVerticalMetrics] = field(default_factory=list)
    is_continuation: bool = False
```

#### Fields & Semantics
- `x`, `y`: Top-left coordinates of the cell on the current page slice.
- `width`, `height`: Resolved geometric width and height of the cell for this slice.
- `rendered_lines`: Sequence of formatted line items allocated to be drawn on this page slice. For a continuation cell, contains lines $[k..\text{end}]$ carried over from previous slices.
- `line_metrics`: Vertical measurement records matching each entry in `rendered_lines`.
- `is_continuation`: Boolean flag indicating if this cell is continuing content or geometry from an earlier page slice. When `True`, the top border cap is rendered with a continuation style.

---

### 2. TableLayoutData

Container representing the geometric layout of an entire table or a single page slice.

```python
@dataclass
class TableLayoutData:
    x: float
    y: float
    width: float
    height: float
    col_widths: list[float]
    row_heights: list[float]
    cells: list[list[LaidOutCell]]
    warnings: list[str] = field(default_factory=list)

    def slice_page(
        self,
        start_row_idx: int,
        max_height: float,
        new_y: float,
        can_defer_to_next_page: bool = False,
    ) -> tuple[TableLayoutData, int]:
        ...
```

#### Invariants & Constraints
- `start_row_idx`: Index of the row to start slicing from.
- `max_height`: Maximum vertical printable space available on the target page.
- `warnings`: Diagnostic messages generated during slicing (e.g., cell clamping, row deferrals).
- Monotonicity: Each slicing step must make strictly positive progress ($>0$ lines or advancing `next_row`).

---

### 3. LineVerticalMetrics

Encapsulates vertical geometric extents of a rendered line (plain text, formatted tokens, or inline formulas).

```python
@dataclass
class LineVerticalMetrics:
    ascent: float
    descent: float
    height: float
    width: float
```

#### Invariants
- `ascent >= 0.0`: Distance above baseline.
- `descent >= 0.0`: Distance below baseline (positive value).
- `height >= ascent + descent`: Total line vertical step.
- Line bottom boundary calculation: $\text{bottom\_y} = \text{baseline\_y} + \text{descent} + \text{jitter\_tolerance}$.

---

### 4. WriteResult

Structured output record returned by the handwriting layout and rendering engine.

```python
@dataclass
class WriteResult:
    out_path: str
    n_lines: int
    n_strokes: int
    n_tokens: int
    n_missing_tokens: int
    missing: dict[str, int] = field(default_factory=dict)
    missing_grid_path: str | None = None
    missing_symbols: dict[str, int] = field(default_factory=dict)
    missing_letters: list[tuple[str, int]] = field(default_factory=list)
    assembled_words: list[str] = field(default_factory=list)
    n_tables: int = 0
    n_math_blocks: int = 0
    n_pages: int = 1
    n_images: int = 0
    warnings: list[str] = field(default_factory=list)  # NEW: layout diagnostics
```

#### Invariants
- `warnings`: Collects all diagnostic messages from table slicing, document conversion, and geometric boundary clamping.
- Default: Empty list `[]` when no warnings occur.
