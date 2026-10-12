# Technical Research: Table Content Continuation Across Pages, True Geometry Clamping & Layout Hardening

**Feature**: `specs/033-table-content-continuation-and-geometry`
**Date**: 2026-10-12
**Status**: Completed (Refined after Engineering Review)

---

## 1. Multi-Page Table Text Content Continuation

### Decision
Implement a two-tier content continuation mechanism:
1. **Rowspan Cross-Page Line Transfer**: For `rowspan` cells that span across page boundaries, partition lines $[0..k]$ onto the initial page slice, and transfer remaining lines $[k..\text{end}]$ into the continuation cell on subsequent page slices instead of creating an empty placeholder cell (`rendered_lines=[]`).
2. **Dynamic Row Splitting for Tall Rows**: When a single row's height exceeds available page space on a fresh page (or after deferral), dynamically split the row in `TableLayoutData`:
   - Slice Row: Contains lines $[0..k]$ that fit vertically within `max_height`, with row height $H_1 \le \text{max\_height}$.
   - Continuation Row: Contains remaining lines $[k..\text{end}]$ with row height $H_2 = H_{\text{orig}} - H_1$, marked with `is_continuation=True`, inserted into `self.cells` and `self.row_heights`.
   - In multi-column rows where Column 0 has 25 lines and Column 1 has 3 lines, Column 1 finishes on Page 1; on Page 2, Column 1's continuation cell has `rendered_lines=[]` and `is_continuation=True`, preserving the 2D grid structure, column width, and border lines without duplicating text.
   - Monotonic Progression: `next_row` always advances to `start_row_idx + 1`, maintaining invariant integer progression in `DocumentLayoutEngine.render()` without complex caller loops or infinite pagination hangs.

### Rationale
- In `TableLayoutData.slice_page()`, when a `rowspan` cell extended into the next page, a continuation `LaidOutCell` was created with `rendered_lines=[]`.
- In `DocumentLayoutEngine.render()`, if line baseline exceeded `max_page_y`, rendering simply broke out of the loop.
- Together, this caused any cell lines that did not fit on the first page to be permanently dropped.
- Dynamic row splitting ensures that both `rowspan` groups and oversized single rows continue seamlessly across 2, 3, or more pages with 100% content preservation.

### Atomic Line Fallback
If an individual line or atomic inline formula is taller than the entire page's printable height, the engine places that single line on the fresh page, clamps it safely, emits an explicit diagnostic warning, and advances past that line/row to ensure positive progress and prevent an infinite loop.

---

## 2. True Stroke Geometry Boundary Containment

### Decision
Determine line bottom boundaries using $\text{bottom\_y} = \text{baseline\_y} + \text{effective\_descent} + \text{jitter\_tolerance}$, where $\text{effective\_descent} = \max(\text{line\_metrics.descent}, 0.3 \times \text{line\_height} \times S \times \text{scale\_mult})$ and $\text{jitter\_tolerance} \approx 1.5\text{ pt}$. Cease rendering or paginate when $\text{bottom\_y} > \text{max\_page\_y}$.

### Rationale
- Letters with descenders ("g", "y", "p", "q", "j"), deep mathematical symbols (radicals, fractions, integrals), and vertical handwriting synthesis jitter all extend below the baseline.
- Testing only `baseline_y > max_page_y` allows strokes with deep descenders (which can reach $15\text{ pt}$ or more below baseline) to spill across the bottom margin ($y > 841.89 - 60.0$) and into footers.
- Similarly, inside table cells, testing against $\text{laid\_cell.y} + \text{laid\_cell.height} - \text{padding}$ guarantees strokes never collide with horizontal bottom borders.

---

## 3. Pure Geometric Width Measurement Without Writer Mutation

### Decision
Add a non-mutating width measurement utility (`Writer.measure_text_width(text, scale)` caching character widths in `_char_width_cache: dict[str, float]`) to evaluate candidate substring lengths during character-level token wrapping, reserving `Writer.token()` calls exclusively for the final accepted line chunks.
- Text is normalized with Unicode NFC before token evaluation to prevent splitting combining diacritical marks.
- Character widths are queried directly from bank glyph samples without invoking `self.pick()`, `self.counts`, `self.last`, or `self.assembled`.

### Rationale
- `Writer.token()` executes full stroke synthesis, selects glyph samples via `self.pick()`, increments frequency counters in `self.counts`, updates `self.last`, and appends strings to `self.assembled`.
- Iteratively calling `Writer.token()` for candidate prefixes in an $O(n^2)$ loop pollutes random variant selection and incurs unnecessary CPU overhead.
- Pure geometric measurement calculates width in $O(L)$ time with zero side effects.

---

## 4. Tight Per-Cell Stroke Bounding Box Testing

### Decision
Update `test_table_wrapping_pipeline.py` and `test_table_rich_inlines.py` to extract strokes per cell and assert that all $(x, y)$ coordinates stay strictly inside individual cell bounding boxes:
- $x \in [\text{cell.x}, \text{cell.x} + \text{cell.width}]$
- $y \in [\text{cell.y}, \text{cell.y} + \text{cell.height}]$
- Minimum padding maintained between content strokes and border strokes.

### Rationale
- Existing tests verified only document-wide bounds ($y \le 841.89 - 60$) or full-table width ($x \le x_0 + \text{width}$).
- Per-cell assertions catch column bleeding, column border collisions, and formula height underestimations that document-wide tests miss.

---

## 5. End-to-End Layout Warning Propagation

### Decision
1. Add `warnings: list[str] = field(default_factory=list)` to `WriteResult`.
2. In `DocumentLayoutEngine.render()`, collect `slice_data.warnings` and pass them into `WriteResult.warnings`.
3. In `chuviettay/browser/bridge.py`, merge `result.warnings` into the JSON response payload.
4. In `webapp/js/write.js`, display warnings in the existing `#editor-warnings` banner.
5. In `chuviettay/cli.py` and `chuviettay/formatting.py`, print layout warnings in the user summary report.

### Rationale
- `TableLayoutData.slice_page()` already generates descriptive warnings when rows/cells are clamped or deferred.
- Connecting this pipeline end-to-end ensures users receive clear diagnostics whenever documents require layout adaptations.
