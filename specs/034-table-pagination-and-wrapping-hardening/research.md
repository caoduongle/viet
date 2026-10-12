# Phase 0 Research: Table Pagination, Anti-Collision Line Spacing, Math Accents, and Geometry Hardening

**Feature**: `034-table-pagination-and-wrapping-hardening`  
**Date**: 2026-10-12  
**Status**: Completed

## 1. Research Overview

This research artifact consolidates the architectural investigations, root cause analyses, and design decisions for resolving:
1. P1: Silently dropped table cell lines at page bottom boundaries (`line_bottom_y > max_page_y`).
2. P1: Line collision and border strike-through when line spacing is configured to small positive values (e.g., `1.0pt`).
3. P2: Abnormally high math accent displacement ($\bar{x}, \hat{x}, \tilde{x}, \vec{x}$) and inflated line ascent metrics.
4. P2: Inconsistent row indices and broken `rowspan` ranges caused by dynamic row insertion in table slices.
5. P2: Quadratic complexity $O(N^2)$ and tentative mutation of `Writer` state during long token wrapping.
6. P2: Loss of intentional blank lines in table cells during line formatting.
7. P3: Strict geometric containment and exact-count invariant verification in automated test suites.

---

## 2. Technical Investigation & Decisions

### Decision 1: Bottom-Margin Overflow Protection & Remainder Rollover

- **Root Cause**: In [`engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py#L685-L687), when `line_bottom_y > max_page_y`, the rendering loop executes `break`. The unrendered lines in `laid_cell.rendered_lines` are discarded. The engine then sets `curr_row_idx = next_row`, permanently losing the remaining content of that row.
- **Decision**: 
  1. **Strict Slice Planning**: Update `partition_cell_lines_by_height()` and `slice_page()` to account for actual baseline descent, padding, and maximum transformation tolerance so `slice_data` does not over-commit lines that cannot fit on the current page.
  2. **Active Rollover Buffer**: If `render()` encounters `line_bottom_y > max_page_y` during cell stroke emission, it collects all remaining unrendered lines ($l_{\text{idx}} \ge \text{current}$) into a `ContinuationRemainder`. The engine halts the current page, creates a continuation row on the next page with the remaining lines, and does NOT advance `curr_row_idx` past the unrendered content.
  3. **Atomic Element Protection**: For single indivisible elements (such as oversized standalone math blocks) where $H > \text{max\_page\_height} - \text{margin}$, scale the element down proportionally or log a structured warning instead of causing an infinite loop.
- **Alternatives Considered**: 
  - *Hard Truncation with Ellipsis*: Rejected because users expect 100% data preservation in document conversion.
  - *Drawing outside page margins*: Rejected because strokes would be cut off or corrupt PDF/printing margins.

---

### Decision 2: Anti-Collision Line Spacing & Table Row Height Floor

- **Root Cause**: In [`engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py#L70), `self.line_h = opts.line if opts.line is not None else ...`. When a user inputs `1` or `1pt`, `self.line_h` becomes `1.0`. The vertical step between consecutive line baselines becomes $1.0\text{pt}$, while handwriting glyphs are $15-20\text{pt}$ tall, causing total overlapping. In tables, row height becomes $1.0 + 2 \times 6.0 = 13.0\text{pt}$, causing horizontal borders to strike directly through numeric characters.
- **Decision**:
  1. **Anti-Collision Floor**: Define a physical minimum line height floor based on bank font metrics:
     $$\text{safe\_line\_floor} = \max\left(1.4 \times xh \times S,\; 0.65 \times \text{bank.line} \times S\right)$$
  2. **Inter-Line Gap Interpretation**: If the user provides a custom `line` parameter where $0 < \text{opts.line} < \text{safe\_line\_floor}$:
     - Interpret `opts.line` as an **extra inter-line clearance gap** added to the physical glyph height:
       $$\text{eff\_line\_h} = \text{safe\_line\_floor} + \text{opts.line}$$
     - If $\text{opts.line} \ge \text{safe\_line\_floor}$, use `opts.line` directly as the baseline-to-baseline line height.
     - This guarantees that for ANY $\text{opts.line} > 0$, the optical gap between consecutive lines is strictly greater than 0, preventing collision.
  3. **Table Row Height Floor**: In [`TableLayoutEngine`](file:///d:/viet/app/chuviettay/layout/table_layout.py#L588):
     $$\text{min\_row\_h} = \text{safe\_line\_floor} + 2 \times \text{cell\_padding}$$
     Row height cannot be smaller than `min_row_h`, ensuring table borders never intersect numbers or text.
- **Alternatives Considered**:
  - *Strict Validation Error*: Rejecting `line < 10` with a `ValueError`. Rejected because users adjusting spacing in web UI sliders expect intuitive tight spacing, not a crash or error toast.

---

### Decision 3: Natural Math Accent Positioning & Compact Ascent Metrics

- **Root Cause**: In [`math_layout.py`](file:///d:/viet/app/chuviettay/layout/math_layout.py#L666-L681), `_m_Accent` sets `height = 0.38 * xh`, `gap = 0.15 * xh`, and anchors the accent at $y_0 = -(base.size.ascent + gap + height)$. For `\bar`, the stroke is placed at $y_0 + \text{mid} = -(base.size.ascent + 0.34 \times xh)$. For $xh = 8\text{pt}$, the bar floats $2.7\text{pt}$ above the character top. Furthermore, `ascent = -y0` inflates the item ascent to $1.53 \times xh$, which causes [`engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py#L295) to blow up `extra_top`, shifting entire line baselines downward.
- **Decision**:
  1. **Tight Optical Clearance for Linear Accents**:
     - For `"bar"`, `"overline"`: set `gap = 0.08 * xh`, `height = 0.16 * xh`. Stroke is positioned at $y = -(base.size.ascent + 0.08 \times xh + 0.08 \times xh) = -(base.size.ascent + 0.16 \times xh)$. This places the overbar tightly and naturally above $x$.
     - For `"hat"`, `"widehat"`: set `gap = 0.06 * xh`, `height = 0.28 * xh`.
     - For `"tilde"`, `"widetilde"`: set `gap = 0.06 * xh`, `height = 0.24 * xh`.
     - For `"vec"`: set `gap = 0.10 * xh`, `height = 0.35 * xh`.
  2. **Bounded Line Metric Impact**:
     - Normalize `ascent` of simple lowercase accented variables so that inline $\bar{x}, \bar{y}, \hat{x}$ does not trigger disproportionate `extra_top` line inflation.
- **Alternatives Considered**:
  - *Hardcoding fixed point offsets*: Rejected because accents must scale proportionally with math `scale` and variable $x$-height.

---

### Decision 4: Row Index and Rowspan Synchronization for Dynamic Continuation Rows

- **Root Cause**: In [`table_layout.py`](file:///d:/viet/app/chuviettay/layout/table_layout.py#L241-L242), `self.row_heights.insert(start_row_idx + 1, ...)` and `self.cells.insert(start_row_idx + 1, ...)` modify the table layout in-place without updating `cell.row` for subsequent cells or updating multi-row spans intersecting the insertion point.
- **Decision**:
  1. **Immutable Slicing Architecture**: Slicing a table into pages should produce independent `TableLayoutData` instances for each page slice without destructive mutations to the parent table.
  2. **Index Re-synchronization Method**: For any continuation row generated, provide an explicit `reindex_rows()` operation that shifts `cell.row` for all subsequent rows ($r > \text{inserted}$) and properly increments/decrements active spans so that [`BorderLookupGrid`](file:///d:/viet/app/chuviettay/layout/table_layout.py#L750) has exact coordinates on every page.
- **Alternatives Considered**:
  - *Ignoring row indices in border drawing*: Rejected because `BorderLookupGrid` requires accurate 2D coordinates to suppress borders inside merged cells.

---

### Decision 5: Single-Pass Zero-Mutation Token Splitting with O(N) Complexity

- **Root Cause**: 
  - `_layout_inlines()` calls `self.wr.token(tok)` eagerly for every text item, which mutates `Writer` state before checking if the token fits.
  - When $W > \text{usable\_w}$, it enters a while loop that slices prefixes and calls `measure_text_width(cand)` repeatedly ($O(N^2)$), pops from the front ($O(N)$), and speculatively calls `self.wr.token(chunk_str)` multiple times.
- **Decision**:
  1. **Pure Pre-Measurement**: Before invoking `Writer.token()`, check `est_w = self.wr.measure_text_width(tok) * self.S * scale_mult`. If `est_w <= usable_w`, synthesize the token directly once.
  2. **Linear Prefix Scan**: If `est_w > usable_w`, compute cumulative prefix widths using character width cache in a single pass $O(N)$ with a pointer/index instead of `pending_chars.pop(0)`.
  3. **Single Synthesis Execution**: Generate handwriting strokes via `self.wr.token()` strictly ONCE for each confirmed chunk.
- **Alternatives Considered**:
  - *Binary search for split points*: Rejected because character-by-character linear scan with cached widths is already $O(N)$ and simpler to implement while maintaining exact word boundary fidelity.

---

### Decision 6: Preserving Intentional Empty Lines in Table Cells

- **Root Cause**: In [`engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py#L512), `flush_cur_line()` checks `if cur_l:`. If a cell contains an empty paragraph or explicit consecutive `LineBreak` items, `cur_l` is empty and is discarded.
- **Decision**: Update `flush_cur_line()` to accept an optional `preserve_empty=True` flag or detect `LineBreak` when `cur_l` is empty. When flushing a deliberate blank line, append an empty item list `[]` to `cell_lines` and a `LineVerticalMetrics(ascent=0.0, descent=0.0, width=0.0, height=self.line_h)` to `cell_metrics`.
- **Alternatives Considered**:
  - *Inserting a phantom space character*: Rejected because phantom spaces could generate unnecessary stroke attempts or alter column width calculations.

---

### Decision 7: Geometry Containment and Exact Invariant Verification

- **Decision**: Add helper assertions in test suites verifying:
  1. $N_{\text{rendered}} == N_{\text{expected}}$ (exact count match, zero missing, zero duplicated).
  2. Post-transformation stroke bounding boxes stay within $[\text{cell.x}, \text{cell.x} + \text{cell.width}]$ and $y \le \text{page\_height} - 60.0$.
  3. Verify behavior with both jitter enabled (`jitter=1.0`) and disabled (`jitter=0.0`).
