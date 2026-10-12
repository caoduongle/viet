# Contract: Table Continuation, Remainder Rollover, and Index Consistency

**Contract ID**: `CTR-034-TABLE-CONTINUATION-AND-PAGINATION`  
**Target Modules**: [`chuviettay/layout/table_layout.py`](file:///d:/viet/app/chuviettay/layout/table_layout.py), [`chuviettay/layout/engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py)

---

## 1. Specification

### 1.1 Bottom-Margin Overflow Protection
1. `DocumentLayoutEngine.render()` checks `line_bottom_y > max_page_y` for every text/formula line inside each cell.
2. If `line_bottom_y > max_page_y`:
   - The engine MUST NOT permanently drop the line or break execution without saving state.
   - All unrendered lines from the current line index to the end of the cell are collected into a continuation remainder.
   - A continuation slice is instantiated for the next page, and the current row pointer remains on the current row until all remainder lines are rendered.
3. For indivisible oversized elements where $H > \text{max\_page\_y} - \text{content\_top}$, the engine downscales the element to fit or logs a structured warning, guaranteeing that pagination never enters an infinite loop.

### 1.2 Table Row Index and Span Synchronization
1. When a continuation row is created via dynamic row splitting (`insert(start_row_idx + 1, ...)`):
   - Explicit re-indexing MUST execute across `self.cells`:
     - For all rows $r \ge \text{inserted\_idx} + 1$: update `cell.row = r` for every cell.
     - For any cell starting at row $r_{\text{orig}} < \text{inserted\_idx}$ whose span spans across the split ($r_{\text{orig}} + \text{rowspan} > \text{inserted\_idx}$): increment its `rowspan` by 1 to cover the newly inserted split slice.
2. In `TableLayoutData.slice_page()`, when constructing `sliced_cells`:
   - Each cell in `sliced_cells` MUST have its `cell.row` mapped strictly to its local row offset $0 \le r_{\text{offset}} < \text{len}(\text{sliced\_row\_heights})$.
3. `BorderLookupGrid.from_cells(num_rows, num_cols, sliced_cells)` MUST receive local coordinates so that borders across multi-page tables match cell outer edges and never cut through merged cells.

### 1.3 Linear Token Wrapping & State Isolation
1. Before calling `Writer.token(tok)`, the layout engine checks `measure_text_width(tok)`.
2. If the token fits within `usable_w`, `Writer.token(tok)` is called once.
3. If the token exceeds `usable_w`:
   - Break positions are computed in $O(N)$ linear time using prefix character width calculations.
   - Safety guard: If an individual character is wider than `usable_w`, the chunker MUST allocate at least 1 character (`min_chars = 1`) to guarantee termination.
   - `Writer.token()` is invoked strictly once per finalized segment.
   - No trial synthesis calls are permitted to modify `Writer.assembled` or `Writer.counts`.
