# Phase 0 Research: Table Layout Robustness, Geometry Scaling & DOCX Import Hardening

**Feature**: `032-table-layout-docx-hardening`
**Date**: 2026-10-11

---

## Research Question 1: Table Pagination Boundary Clamping & Multi-Page Group Continuation

### Context & Problem
In `chuviettay/layout/table_layout.py` lines 132-150:
```python
if curr_h > 0 and curr_h + needed_h > max_height:
    break
if curr_h == 0 and needed_h > max_height:
    end_idx = target_end + 1
    curr_h = needed_h
    break
```
When `curr_h == 0` (on a fresh page) and a merged group's height `needed_h` exceeds `max_height`, the engine takes the entire group `[start_row_idx, target_end]`. When `needed_h` exceeds the printable page area, strokes overflow beyond the bottom margin of the page. Furthermore, test `tests/test_table_pagination_closure.py` only validated `next_row > start_row_idx` without verifying vertical coordinate boundaries.

### Technical Decision
1. **Two-Stage Pagination Evaluation**:
   - **Case A (Group does not fit remainder of current page, but fits on fresh page)**: When `curr_h > 0` and `curr_h + needed_h > max_height`: break immediately, deferring the entire group to a new page.
   - **Case B (Group exceeds total page printable height)**: When `curr_h == 0` and `needed_h > max_height`:
     - If the group contains multiple underlying rows: take as many complete rows as fit within `max_height` (at least 1 row to ensure forward progress), cutting the spanning cell at the page boundary.
     - If even a single row exceeds `max_height`: take the single row, clamp vertical stroke positioning so text and cell borders never extend past `page_height - margin_bottom`, close horizontal border caps cleanly, and emit a diagnostic warning (`TableIssue(code="ROW_TALLER_THAN_PAGE")`).
2. **Border Closing**:
   Each table page slice must draw its top border and bottom border at `y = min(cur_y + slice_h, max_page_y)` so that partial table slices look finished rather than broken.
3. **Stroke Clamping Invariant**:
   In `DocumentLayoutEngine`, ensure that for any table slice, every stroke $y$ satisfies $y \le \text{page\_height} - \text{margin\_bottom}$.

### Alternatives Considered
- *Scaling down the entire table*: Rejected because scaling a huge table to fit a single page makes text illegibly tiny when a table has dozens of lines.
- *Blind truncation / dropping rows*: Rejected because data loss is unacceptable.

---

## Research Question 2: Math Formula Vertical Metrics Scaling Normalization in Table Cells

### Context & Problem
In `chuviettay/layout/engine.py` line 234:
`self._math_extent[id(math_strokes)] = (m_item.size.ascent, m_item.size.descent)` stores ascent and descent in unscaled bank units ($S=1.0$).
In normal paragraph rendering (lines 369-370):
`line_asc = max(line_asc, ext[0] * self.S * scale_mult)` properly scales by `self.S`.
However, in table cell inline formatting (`cell_inlines_formatter`, lines 529-530):
`item_asc, item_desc = self._math_extent[id(st)]` accessed raw unscaled values.
When `self.S != 1.0` (or when `--auto-xh` changes scale), row height calculation under- or over-estimates formula height, causing formula strokes to collide with cell borders.

### Technical Decision
Inside `cell_inlines_formatter`:
```python
item_asc = item_desc = 0.0
if id(st) in self._math_extent:
    ext_asc, ext_desc = self._math_extent[id(st)]
    item_asc = ext_asc * self.S
    item_desc = ext_desc * self.S
```
In `flush_cur_line()`:
```python
extra_t = max(0.0, cur_asc - 0.7 * self.line_h)
extra_b = max(0.0, cur_desc - 0.3 * self.line_h)
line_h_tot = self.line_h + extra_t + extra_b
```
Now `cur_asc`, `cur_desc`, and `self.line_h` are all expressed in the same scaled coordinate space. Cell row height expansion accurately accommodates formulas at any scale.

### Alternatives Considered
- *Storing scaled ascent/descent directly in `_math_extent`*: Rejected because `_math_extent` can be shared across contexts with different `scale_mult` multipliers (e.g., headings with `scale_mult=1.35`). Storing native $S=1.0$ extent and multiplying by active scale at access time is consistent with the rest of the layout engine.

---

## Research Question 3: Long Unbroken Token Wrapping in Real Table Pipeline

### Context & Problem
In `chuviettay/layout/engine.py` lines 533-543:
When `cur_lw + sp + w > usable_w`, the cell formatter flushes the current line and starts a new line with the current item: `cur_l = [(0.0, st, w)]`. If a single token has $w > \text{usable\_w}$, it is placed unconditionally on a line with width $w$, spilling across the column's right border. While `table_layout.py` had a standalone `wrap_cell_text()` function with character breaking, `DocumentLayoutEngine` uses `cell_inlines_formatter`.

### Technical Decision
1. **Sub-token Breaking in `cell_inlines_formatter`**:
   For text tokens where $w > \text{usable\_w}$:
   - Inspect the token text (`tok_str` from `_layout_inlines`).
   - If the token is a single unbroken string (e.g. URL, hex hash, long word) exceeding `usable_w`:
     - Break the string into character slices `[c_1..c_k]` using `self.wr.token` / handwriting layout such that each sub-slice width $\le \text{usable\_w}$.
     - Each sub-slice is formatted as its own line item in `cell_lines`.
2. **Formula Overflow Handling**:
   - If an atomic formula item exceeds `usable_w`: scale down the formula slightly to fit `usable_w`, or break at major relational/binary operators (`=`, `+`, `-`).

### Alternatives Considered
- *Hard clipping of strokes with SVG/XOPP clip path*: Rejected because Xournal++ `.xopp` format does not support XML clipping masks on individual stroke layers; strokes must be geometrically positioned within cell bounds.

---

## Research Question 4: DOCX Table Occupancy Grid Column Alignment & Nested Block Order

### Context & Problem
1. In `chuviettay/browser/bridge.py` line 581:
   `num_cols = max(len(r.cells) for r in b.rows)` fails when rows have merged cells (`colspan > 1`). For example, a row with 1 cell spanning 2 columns has `len(r.cells) == 1`, even though the table has 2 logical columns.
2. In `chuviettay/importer/docx_importer.py` lines 345-375:
   `for p in c.paragraphs:` runs first, followed by `nested_tables = getattr(c, "tables", [])` appended afterwards, scrambling the original sequence of paragraphs and nested tables within the cell.

### Technical Decision
1. **2D Occupancy Grid for DOCX Table Serialization**:
   - Construct a matrix `grid[row_idx][col_idx]` tracking logical positions.
   - For each cell, determine its starting `c_idx` (first unassigned column in `grid[r]`), then fill `c_idx .. c_idx + colspan - 1` and `r .. r + rowspan - 1`.
   - Total columns $C = \max(\text{len}(grid[r]))$.
   - When generating Markdown pipe table rows:
     - Output cell text at its logical start column.
     - For spanned columns or skipped positions, output an empty cell `" "` to maintain vertical column alignment.
2. **Cell Block Order Preservation in `docx_importer.py`**:
   - In `python-docx`, inspect `c._tc.iterchildren()`:
     - For `<w:p>`: parse via `_parse_paragraph_blocks`.
     - For `<w:tbl>`: parse as nested table.
   - Maintain the exact sequence of blocks in `cell.blocks`.

---

## Research Question 5: Web Modal Table Header Checkbox Behavior

### Context & Problem
In `webapp/js/write.js` lines 425-436:
`const hasHeader = inputHeader ? inputHeader.checked : true;` was read, but the template string generator unconditionally emitted `Cột 1 | Cột 2 ...` and `:--- | :---`.

### Technical Decision
When `hasHeader === false`:
Generate:
```markdown
|   |   |   |
| :--- | :--- | :--- |
| R1C1 | R1C2 | R1C3 |
| R2C1 | R2C2 | R2C3 |
```
This satisfies the GFM/CommonMark pipe table syntax requirement (which mandates a header and delimiter row) while leaving the header row blank so no unwanted "Cột 1" titles are displayed.

---

## Summary of Decisions
| Item | Decision | Key Advantage |
|---|---|---|
| Pagination | 2-stage split + border closure caps + stroke clamping | 100% of strokes stay within printable bounds; no hangs |
| Math Metrics | Multiply ascent/descent by `self.S` in `cell_inlines_formatter` | Formulas scale harmoniously with cell row height |
| Token Wrapping | Wire character-level breaking into `cell_inlines_formatter` | Long URLs and identifiers stay inside column borders |
| DOCX Columns | 2D Occupancy Grid in `bridge.py` | Accurate logical column counts and aligned Markdown tables |
| Nested Order | `iterchildren()` on `c._tc` in `docx_importer.py` | Preserves true document sequence of paragraphs and tables |
| Header Modal | Blank header row for headerless tables in `write.js` | User checkbox works correctly with valid GFM syntax |
