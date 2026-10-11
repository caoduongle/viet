# Contract: Table Layout & Pagination Interface

**Module**: `chuviettay/layout/table_layout.py` & `chuviettay/layout/engine.py`

---

## 1. Pagination Method Contract

### `TableLayoutData.slice_page`

```python
def slice_page(
    self,
    start_row_idx: int,
    max_height: float,
    new_y: float,
    can_defer_to_next_page: bool = True,
    page_bottom_limit: float | None = None,
) -> tuple[TableLayoutData, int]:
    """Slice table rows starting from start_row_idx that fit within max_height.

    Parameters:
        start_row_idx: Index of starting row in self.cells
        max_height: Maximum height available for this slice in points
        new_y: Top y-coordinate where this table slice will be rendered
        can_defer_to_next_page: True if current page can be broken to move content to a fresh page
        page_bottom_limit: Absolute y-coordinate boundary (e.g. page_height - margin_bottom)

    Returns:
        tuple of:
            slice_data (TableLayoutData): Sub-table layout containing cells and row heights for this slice
            next_row (int): Index of the next row to be rendered (strictly > start_row_idx if slice_data.cells non-empty)
    """
```

### Preconditions & Postconditions
- **Precondition**: `0 <= start_row_idx < len(self.cells)`, `max_height > 0`.
- **Postcondition**:
  - `next_row > start_row_idx` (forward progression guaranteed).
  - For all $(x, y)$ in `border_strokes` and cell contents:
    `y <= page_bottom_limit` (if provided).
  - If a row group cannot fit on the remainder of an existing page (`not is_fresh_page`), `next_row` is returned as `start_row_idx` and `slice_h == 0.0` to signal caller to trigger `new_page()`.

---

## 2. Cell Inline Formatter Contract

### `cell_inlines_formatter` (DocumentLayoutEngine)

```python
def cell_inlines_formatter(
    cell: TableCell,
    usable_w: float,
) -> list[list[tuple[float, list[Stroke], float]]]:
    """Format cell inlines into lines, scaling formula metrics and wrapping long tokens.

    Parameters:
        cell: TableCell instance containing paragraphs and math blocks
        usable_w: Usable horizontal width in points (column width - 2 * padding)

    Returns:
        cell_lines: list of lines, where each line is a list of (start_x, strokes, width)
    """
```

### Invariants
1. **Formula Metric Scaling**:
   Whenever an inline math item is processed, its ascent and descent are multiplied by `self.S * scale_mult` before determining line height.
2. **Token Width Invariant**:
   For every token `(start_x, strokes, width)` in any line:
   `start_x + width <= usable_w + 1e-3`. Tokens wider than `usable_w` are broken into sub-tokens across character boundaries.
