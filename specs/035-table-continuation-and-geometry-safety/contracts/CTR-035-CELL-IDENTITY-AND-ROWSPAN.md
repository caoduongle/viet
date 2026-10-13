# Contract CTR-035-CELL-IDENTITY-AND-ROWSPAN: Persistent Cell Identity and Non-Overlapping Rowspan Partitioning

**Identifier**: `CTR-035-CELL-IDENTITY-AND-ROWSPAN`  
**Applies to**: `TableLayoutEngine`, `TableLayoutData`, `DocumentLayoutEngine` (`chuviettay/layout/table_layout.py`, `chuviettay/layout/engine.py`)  
**Status**: Normative  

---

## 1. Specification

### C1. Persistent Cell Identity
1. Every `TableCell` and `LaidOutCell` MUST have an identifiable `source_cell_id: int`.
2. When creating sub-table slices in `TableLayoutData.slice_page()`, all slice cells and continuation cells MUST inherit `source_cell_id` from their originating cell.
3. In `DocumentLayoutEngine`, when rollover lines occur at a page break:
   - Rollover lines MUST be matched back to `full_table_data` using `cell.source_cell_id == laid_cell.source_cell_id`.
   - The engine MUST NOT rely on `curr_row_idx + laid_cell.row` to identify the origin cell.

### C2. Non-Overlapping Rowspan Partitioning
When dynamically splitting an oversized row $R$ into row $R$ (part 1) and row $R+1$ (part 2):
1. For every cell in row $R$ with initial row span $K$:
   - Part 1 (`c1`) MUST have `rowspan = 1`.
   - Part 2 (`c2`) MUST start at row $R+1$ with `rowspan = max(1, K)`.
2. For any cell spanning multiple rows that crosses slice boundary `end_idx`:
   - The cell in the current slice MUST cover `eff_rs = min(cell.rowspan, end_idx - r)` rows.
   - The continuation cell created for the next slice MUST cover `rem_rs = cell.rowspan - eff_rs` rows.
3. The row ranges covered by the origin slice and the continuation slice MUST be strictly disjoint:
   $$[r_{\text{start}}, r_{\text{start}} + \text{eff\_rs}) \cap [r_{\text{cont}}, r_{\text{cont}} + \text{rem\_rs}) = \emptyset$$

### C3. Border Alignment Invariant
1. `BorderLookupGrid.from_cells()` MUST compute border visibility using the partitioned, non-overlapping `rowspan` ranges.
2. 100% of merged cell interiors MUST be free of spurious interior divider lines across all page slices.
