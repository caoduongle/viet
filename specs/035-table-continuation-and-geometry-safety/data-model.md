# Data Model: Table Continuation, Rowspan Stability, and Geometry Safety

**Feature**: [035-table-continuation-and-geometry-safety](spec.md)  
**Date**: 2026-10-13  
**Status**: Draft  

---

## 1. Entities & Data Structures

### TableCell (`chuviettay.document.ir`)
Intermediate Representation (IR) node representing a single cell in a table.

```python
@dataclass
class TableCell:
    blocks: list[Block] = field(default_factory=list)
    align: str = "left"
    colspan: int = 1
    rowspan: int = 1
    source_cell_id: int | None = None  # Persistent identity across slicing and continuations
```

- **Validation Rules**:
  - `colspan >= 1`
  - `rowspan >= 1`
  - `source_cell_id`: Unique integer assigned upon ingestion/table layout initialization. Must remain invariant across row splits and pagination slices.

---

### LaidOutCell (`chuviettay.layout.table_layout`)
Positioned and sized representation of a cell after layout calculation.

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
    source_cell_id: int | None = None  # Inherited from cell or assigned at layout time
```

- **State Transitions**:
  - `is_continuation`: Defaults to `False`. Becomes `True` when the cell represents the continuation of an unrendered remainder from a previous page slice.
  - `rendered_lines`: Contains synthesized stroke lines to be drawn on the active page. Unrendered lines are partitioned into subsequent continuation cells.
  - `rowspan`: Dynamically partitioned so that $\sum \text{slice\_rowspans} = \text{total\_effective\_rows}$. Never overlaps between consecutive slices.

---

### TableLayoutData (`chuviettay.layout.table_layout`)
Container holding geometric layout results for a table or sub-table slice.

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
```

- **Invariants**:
  - `len(cells) == len(row_heights)`
  - For any row $r$, `cell.row == r` for all cells in `cells[r]` after `reindex_rows()`.
  - For any cell with `rowspan > 1` at row $r$, the cell covers rows $[r, r + \text{rowspan})$. No two cells with the same column index may claim overlapping row intervals.

---

### BorderLookupGrid (`chuviettay.layout.table_layout`)
$O(1)$ fast lookup grid determining whether cell borders are visible or covered by merged cells.

```python
@dataclass
class BorderLookupGrid:
    num_rows: int
    num_cols: int
    horiz_spanned: list[list[bool]]  # [num_rows - 1][num_cols]: True if horizontal border between row r and r+1 is covered
    vert_spanned: list[list[bool]]   # [num_rows][num_cols - 1]: True if vertical border between col c and c+1 is covered
```

- **Invariants**:
  - `horiz_spanned[r][c] == True` if and only if a cell covering column $c$ starts at row $\le r$ and ends at row $> r + 1$.
  - Interior border strokes are strictly omitted when `horiz_spanned` or `vert_spanned` is `True`.

---

## 2. Relationships & Lifecycle

```
[Markdown / Document IR Table]
       │
       ▼ (assigns unique source_cell_id)
[TableLayoutEngine.layout_table()]
       │
       ├─────────────────────────────────┐
       ▼ (Page 1)                        ▼ (Page 2 Continuation)
[TableLayoutData Slice 1]       [TableLayoutData Slice 2]
  - LaidOutCell (part 1)          - LaidOutCell (continuation)
    • source_cell_id: 101           • source_cell_id: 101 (SAME ID)
    • rowspan: 1                    • rowspan: rem_rs (NON-OVERLAPPING)
    • rendered_lines: [0..K]        • rendered_lines: [K..N]
```

1. **Table Construction**: `TableCell` nodes are populated with `source_cell_id`.
2. **First Slice Execution**: Lines $[0 \dots K]$ fit on Page 1; `LaidOutCell` is rendered.
3. **Rollover Matching**: When Page 1 reaches `max_page_y`, remaining lines $[K \dots N]$ are mapped back to `source_cell_id == 101` in the master table data.
4. **Subsequent Slices**: Next slice picks up unrendered lines using `source_cell_id`, continuing seamlessly without relying on calculated row indices.
