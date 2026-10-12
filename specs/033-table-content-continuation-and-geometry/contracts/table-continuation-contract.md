# Contract: Table Multi-Page Continuation & Content Partitioning

**Domain**: Table Layout & Multi-Page Pagination
**Module**: `chuviettay.layout.table_layout` & `chuviettay.layout.engine`

---

## 1. Specification

When a table spans across multiple pages, no cell text lines may be dropped. Slicing partitions rows and cell lines across page boundaries such that:
1. Every cell in a slice contains only the lines that fit vertically on that page.
2. Cells that cannot complete their lines on the current page emit continuation cells on subsequent pages containing the remaining lines.
3. For single rows or merged groups taller than a single page, the row is dynamically partitioned:
   - Current slice receives lines $[0..k]$ fitting within `max_height`.
   - Subsequent slice receives lines $[k..\text{end}]$ with `is_continuation=True`.
   - Columns that exhaust all their lines on Page 1 receive `rendered_lines=[]` and `is_continuation=True` on Page 2, maintaining 2D grid structure, column width, and cell borders.
4. Monotonicity: `next_row_idx` advances monotonically ($next\_row\_idx = start\_row\_idx + 1$), preventing infinite pagination loops.
5. Atomic Fallback: If an individual line or formula exceeds printable page height, the single line is placed, clamped, warned, and advanced past.

## 2. Interface Contract

### `TableLayoutData.slice_page`

```python
def slice_page(
    self,
    start_row_idx: int,
    max_height: float,
    new_y: float,
    can_defer_to_next_page: bool = False,
) -> tuple[TableLayoutData, int]:
```

#### Pre-conditions
- `0 <= start_row_idx <= len(self.row_heights)`
- `max_height > 0.0`
- `new_y >= 0.0`

#### Post-conditions
- Returns `(slice_data, next_row_idx)`.
- `next_row_idx > start_row_idx` (strictly positive progress).
- If `slice_data.row_heights` is non-empty, `slice_data.height <= max_height + eps`.
- Every cell in `slice_data.cells` has `rendered_lines` containing the exact lines to be drawn on this slice.
- Any cell from previous rows that spans into this slice (`rowspan` continuation or tall row continuation) receives its remaining `rendered_lines` and `line_metrics` with `is_continuation = True`.
- Total line conservation: $\sum_{\text{all slices}} \text{len}(\text{cell.rendered\_lines}) = \text{original\_line\_count}(\text{cell})$.

## 3. Visual Border Contract

- First page slice of a spanning cell: Top border closed, bottom border closed/continuation cap.
- Intermediate page slice: Top continuation cap, bottom continuation cap.
- Final page slice: Top continuation cap, bottom border closed.
