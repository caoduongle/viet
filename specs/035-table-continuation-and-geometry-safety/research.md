# Research: Table Continuation, Rowspan Stability, and Geometry Safety Hardening

**Feature**: [035-table-continuation-and-geometry-safety](spec.md)  
**Date**: 2026-10-13  
**Status**: Completed  

---

## 1. Physical Stroke Containment & Guaranteed Page Clamping

### Decision
Implement physical coordinate containment and safe proportional downscaling in `DocumentLayoutEngine`:
1. When rendering table cell lines or indivisible content situated at the top of a page (`cur_y <= pf.content_top + 1e-6`) where `line_bottom_y > max_page_y`:
   - Calculate a proportional downscaling factor:
     $$\text{scale\_down} = \max\left(0.2, \min\left(1.0, \frac{\text{max\_page\_y} - \text{baseline\_y}}{\text{cur\_desc} + \text{jitter\_tol}}\right)\right)$$
   - Render the line with `scale_mult = scale_down`.
   - Post-process the generated stroke coordinates with physical hard-clamping: for every point $(x, y)$ in the line strokes, enforce $y \leftarrow \min(y, \text{max\_page\_y})$.
   - Record an explicit, factual diagnostic warning: `"Dòng {l_idx} trong ô ({row}, {col}) quá khổ trên trang mới; đã co tỷ lệ {scale_down:.2f}x và kẹp tọa độ trong giới hạn trang."`
2. For all other content where `line_bottom_y > max_page_y` and `cur_y > pf.content_top`:
   - Never attempt to render the overflowing lines on the current page; cleanly defer remaining lines to the next page continuation pass.
   - Never log false clamping warnings when content was simply deferred or when coordinates were not physically clamped.

### Rationale
- Calling `_render_text_line` without scaling or clamping resulted in stroke coordinates bleeding past `max_page_y` while simultaneously logging a warning that claimed the line was clamped.
- Combining proportional downscaling with physical point clamping guarantees $y_{\text{stroke}} \le \text{max\_page\_y}$ mathematically while maintaining stroke legibility.
- Truthful logging ensures user trust and automated geometry verification integrity.

### Alternatives Considered
- *Hard clipping/truncation*: Truncating strokes at $y = \text{max\_page\_y}$ by dropping points. Rejected because it cuts off letters mid-stroke and creates visual artifacts.
- *Infinite page height expansion*: Rejected because page formats (A4, Letter) have fixed printable boundary constraints.

---

## 2. Stable Cell Identity Tracking Across Multi-Page Slices

### Decision
Introduce a persistent identifier `source_cell_id: int` on both `TableCell` and `LaidOutCell`:
1. When `TableCell` objects are initialized or processed by `TableLayoutEngine`, assign a stable `source_cell_id` (using unique integer numbering or `id(cell)`).
2. During `TableLayoutEngine.layout_table()` and `slice_page()`, every created `LaidOutCell` preserves its origin `source_cell_id`.
3. When dynamic row splitting occurs, continuation cells (`c2` and continuation cells across page boundaries) retain the exact same `source_cell_id`.
4. In `DocumentLayoutEngine`:
   - When table cell content overflows a page slice, the engine identifies the origin cell in `full_table_data` by matching `orig_c.source_cell_id == laid_cell.source_cell_id` across all cells in `full_table_data`.
   - The remaining unrendered lines (`rem_lines` and `rem_metrics`) are assigned directly to the matched source cell, with `is_continuation = True`.

### Rationale
- Reconstructing source row indices via `actual_r = curr_row_idx + laid_cell.row` fails for multi-page continuations because `laid_cell.row` is local to the slice offset ($r_{\text{offset}} = 0$ for continuations of previous rows), causing line rollovers to misidentify rows, overwrite wrong cells in the same column, or drop text entirely.
- A persistent `source_cell_id` decouples cell tracking from table slice geometry, guaranteeing exact $O(1)$ or clean linear lookup of the true originating cell across 3+ page continuations.

### Alternatives Considered
- *Maintaining a nested row offset mapping dictionary `dict[tuple[slice_idx, r_offset], orig_r]`*: Rejected because it introduces fragile coupling between slice pagination iterations and table layout state.
- *Rebuilding the entire table AST on each page*: Rejected because it is inefficient and destroys pre-computed cell line partitions.

---

## 3. Explicit Non-Overlapping Rowspan Partitioning

### Decision
Partition `rowspan` explicitly between the origin cell and continuation cells during dynamic row splitting in `TableLayoutData.slice_page`:
1. When splitting row `start_row_idx` into row `start_row_idx` (part 1) and `start_row_idx + 1` (part 2):
   - For a cell with initial `rowspan = K`:
     - Part 1 (`c1`) covers the current row on the active page: `c1.rowspan = 1`.
     - Part 2 (`c2`) covers the continuation row on the next page: `c2.rowspan = max(1, K)`. (Since row `start_row_idx` was split into two rows, `c1` occupies 1 row, and `c2` starts at `start_row_idx + 1` spanning the remaining rows).
   - Update `self.reindex_rows()` and adjust spanning of prior rows reaching past the split point.
2. For multi-page slicing where a cell with `rowspan` crosses `end_idx`:
   - The slice cell takes `eff_rs = min(cell.rowspan, end_idx - r)`.
   - The continuation cell created for the subsequent page slice takes `rem_rs = cell.rowspan - eff_rs`.
   - `BorderLookupGrid.from_cells()` uses the partitioned `rowspan` values so that no interior horizontal lines are drawn across merged cells, and no grid occupancy collisions occur.

### Rationale
- When `c1` and `c2` both retain the original `rowspan`, both copies claim overlapping grid coordinates, causing `BorderLookupGrid` and border rendering to calculate overlapping boundaries, shift columns, and generate duplicate or missing borders.
- Explicit partitioning guarantees that $\sum \text{slice\_rowspans} = \text{total\_effective\_rows}$, eliminating overlap.

### Alternatives Considered
- *Ignoring rowspan during dynamic row splitting*: Rejected because it turns merged cells into regular cells, breaking the table structure.

---

## 4. Whole-Word Aware Hybrid Token Wrapping

### Decision
Enhance `Writer.measure_text_width()` and `_layout_inlines()` to recognize whole-word models:
1. In `Writer.measure_text_width(text, scale=1.0)`:
   - Check if `text` exists in `self.b.words` (or `self.b.letters` for single-character tokens).
   - If a whole-word sample exists with an explicit `"w"` field:
     $$\text{return } \text{float}(\text{sample}["w"]) \times \text{scale}$$
   - Otherwise, fall back to summing character advance widths and letter gaps.
2. In `_layout_inlines()`:
   - Calculate `est_w = self.wr.measure_text_width(tok) * self.S * scale_mult`.
   - If `est_w <= max_item_width`, preserve `tok` as a single indivisible unit.
   - If `est_w > max_item_width`, invoke `_partition_long_token_linear` to split into sub-tokens using pure measurement in $O(N)$ linear time.
   - When generating tokens via `self.wr.token(chunk)`: execute synthesis exactly once per chunk. If minor optical adjustments (kerning, pen clearance) cause slight width variations, accommodate the line boundary in a single pass without discarding samples or triggering repeated synthesis loops.

### Rationale
- Checking `bank.words` first prevents breaking pre-composed words and ligatures into awkward character fragments when they actually fit the column.
- Pure measurement in linear time ensures synthesis state (`assembled`, `counts`, `last`) remains strictly monotonic and uncontaminated.

### Alternatives Considered
- *Trial synthesis with rollback*: Calling `self.wr.token()` and rolling back internal state on failure. Rejected because rollback in complex stochastic handwriting engines is error-prone and causes state leakage.

---

## 5. Synchronized Line Height under `auto_xh`

### Decision
Reorder initialization in `DocumentLayoutEngine.__init__`:
1. Calculate the finalized effective scale factor `self.S` and `self.effective_wscale` *first*, incorporating `auto_xh` adjustments:
   ```python
   self.S = opts.scale
   self.effective_wscale = opts.wscale
   if getattr(opts, "auto_xh", False):
       current_xh = getattr(bank, "xh", 7.94) or 7.94
       target_xh = getattr(opts, "target_xh", 7.94)
       if current_xh > 0 and abs(current_xh - target_xh) > 0.05:
           self.S = opts.scale * (target_xh / current_xh)
       base_pen = float(bank.pen.get("width", 1.41)) if bank.pen else 1.41
       desired_pen = 0.178 * target_xh * (self.S / (target_xh / current_xh if current_xh > 0 else 1.0))
       self.effective_wscale = opts.wscale * (desired_pen / base_pen if base_pen > 0 else 1.0)
   ```
2. Then resolve the effective line height using the finalized `self.S`:
   ```python
   self.line_h = resolve_effective_line_height(opts.line, bank, self.S)
   ```

### Rationale
- Previously, `self.line_h` was computed at line 122 using unscaled `self.S = opts.scale` before `auto_xh` updated `self.S` at lines 145-149.
- Calculating `self.line_h` after updating `self.S` ensures that the anti-collision floor `max(1.4 * font_xh * scale, 0.65 * default_bank_line)` accurately reflects the scaled letter size, preventing character overlapping when small `line` values (e.g. 1.0 pt) are used with scaled fonts.

---

## 6. Deterministic Labeled Line Verification & Decoupled CI Benchmarks

### Decision
1. In `tests/test_table_pagination_closure.py`:
   - Construct integration tests where table cells contain uniquely labeled lines: `LINE_0001`, `LINE_0002`, ..., `LINE_NNNN`.
   - Render multi-page tables across 3+ pages with combinations of tall rows and `rowspan > 1`.
   - Inspect output lines (via rendered result and/or `.xopp` XML) to assert:
     - The set of rendered line labels exactly equals the set of input line labels (zero loss, zero duplicates).
     - The labels appear in strict monotonically increasing sequence.
2. In `tests/test_table_wrapping_pipeline.py`:
   - Replace wall-clock threshold assertion (`assert t_elapsed < 0.010`) with call-count inspection:
     - Wrap `char_width_measurer` with a call counter.
     - Verify that for an input of $N$ characters, `call_count` is exactly $O(N)$ ($\le N$).
     - This guarantees algorithmic linear complexity without any dependency on CI CPU load or virtualization jitter.

### Rationale
- Counting lines (`assert res.n_lines >= 70`) can pass if lines are duplicated or swapped. Labeled identifiers provide mathematically strict proof of content preservation.
- Wall-clock assertions fail intermittently on loaded CI agents; call-count invariants never flake.
