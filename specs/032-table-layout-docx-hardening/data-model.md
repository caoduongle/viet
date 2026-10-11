# Phase 1 Data Model: Table Layout Robustness & DOCX Import

**Feature**: `032-table-layout-docx-hardening`
**Date**: 2026-10-11

---

## Entities & Data Structures

### 1. `TableSlice` (Pagination Slice)
Represents a vertical partition of a table allocated to a single page.

| Field | Type | Description |
|---|---|---|
| `start_row` | `int` | Zero-based index of the first row included in this slice |
| `end_row` | `int` | Exclusive index of the last row included in this slice |
| `slice_height` | `float` | Total physical height in points occupied by this slice |
| `is_continuation` | `bool` | True if this slice continues an unfinished merged cell from a prior page |
| `cap_top` | `bool` | True if a top horizontal border cap should be drawn for this slice |
| `cap_bottom` | `bool` | True if a bottom horizontal border cap should be drawn for this slice |
| `issue_warning` | `str \| None` | Diagnostic warning if slice exceeds standard page margins |

**Validation Rules**:
- `start_row < end_row` (ensures strictly monotonic progression; no zero-height or infinite loops).
- `slice_height <= max_page_available_height` (except in extreme cases where a single atomic row exceeds page capacity, clamped to `max_page_y`).

---

### 2. `CellInlineItem` (Formatted Table Cell Item)
Represents an atomic or wrapped element within a table cell's inline line layout.

| Field | Type | Description |
|---|---|---|
| `strokes` | `list[Stroke]` | Handwritten or vector stroke list in local coordinates |
| `width` | `float` | Physical horizontal extent in points ($w = \text{raw} \times S \times \text{scale\_mult}$) |
| `ascent` | `float` | Scaled vertical ascent in points ($h_{\text{asc}} = \text{raw\_asc} \times S \times \text{scale\_mult}$) |
| `descent` | `float` | Scaled vertical descent in points ($h_{\text{desc}} = \text{raw\_desc} \times S \times \text{scale\_mult}$) |
| `text` | `str` | Original text or LaTeX math source |
| `is_break` | `bool` | True if item represents a hard newline (`__LINE_BREAK__`) |

**Validation Rules**:
- `width <= usable_cell_width` (tokens wider than column width MUST be split into multiple `CellInlineItem` sub-tokens).
- `ascent >= 0.0` and `descent >= 0.0`.

---

### 3. `TableOccupancyGrid` (2D Table Logical Grid)
Maps table cells onto a regular rectangular matrix of logical rows and columns, resolving rowspans and colspans.

| Field | Type | Description |
|---|---|---|
| `num_rows` | `int` | Total count of logical rows in the table |
| `num_cols` | `int` | Total count of logical columns across all rows ($\max(\text{col\_cursor})$) |
| `grid` | `list[list[OccupancyCell]]` | 2D matrix of size `[num_rows][num_cols]` |

### 4. `OccupancyCell` (Cell Slot in Occupancy Grid)

| Field | Type | Description |
|---|---|---|
| `cell` | `TableCell \| None` | Reference to the underlying table cell |
| `is_origin` | `bool` | True if this coordinate is the top-left origin of the cell |
| `logical_col` | `int` | Logical column index ($0 \le c < \text{num\_cols}$) |
| `logical_row` | `int` | Logical row index ($0 \le r < \text{num\_rows}$) |

**State Transitions & Mapping**:
```
DOCX Table Rows with spans
         │
         ▼
TableOccupancyGrid.build()
         │
         ├── For each cell at (r, c):
         │     col_start = first_free_col(r)
         │     grid[r..r+rowspan-1][col_start..col_start+colspan-1] = cell
         │
         ▼
Markdown Table Serialization:
  Row r:
    Col 0..num_cols-1:
      if is_origin: output cell text
      else: output " " (empty padding cell)
```

---

### 5. `TableGeometryBounds` (Test Verification Entity)
Records exact spatial bounds extracted from unpacked `.xopp` documents to verify stroke containment.

| Field | Type | Description |
|---|---|---|
| `cell_bbox` | `tuple[float, float, float, float]` | `(x, y, width, height)` of the cell border |
| `strokes_bbox` | `tuple[float, float, float, float]` | `(min_x, min_y, max_x, max_y)` of all enclosed strokes |
| `page_index` | `int` | Page on which cell is rendered |
| `contains_strokes` | `bool` | True if `strokes_bbox` is strictly inside `cell_bbox` |
| `inside_print_margins` | `bool` | True if all points lie within `[margin_top, page_height - margin_bottom]` |

---

## Invariants & Guarantees
1. **Print Boundary Invariant**: No stroke point $(x, y)$ in any generated page may have $y > \text{page\_height} - \text{margin\_bottom}$.
2. **Column Containment Invariant**: No text stroke point $(x, y)$ in any cell may have $x > \text{cell\_x} + \text{col\_width}$.
3. **Monotonic Pagination Invariant**: `TableLayoutEngine.slice_rows` MUST return `end_idx > start_row_idx` for every slice.
