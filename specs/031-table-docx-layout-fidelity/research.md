# Research & Architecture Decisions: Table Layout and DOCX Import Fidelity

**Feature Branch**: `031-table-docx-layout-fidelity`
**Date**: 2026-10-11
**Status**: Completed

## 1. DOCX Table Import & Web Client Fidelity

### Problem
In `chuviettay/browser/bridge.py` (`import_docx()`), the method parses document blocks into `lines`. Because it only filters blocks with `hasattr(b, "inlines")` (`Paragraph` and `Heading`), all `Table` blocks (which contain `rows` and `cells`) are silently omitted. Subsequently, `webapp/js/write.js` places `res.markdown_text` into the editor, completely dropping all tables from preview and export. Furthermore, `res.warnings` and `res.unsupported` returned by `_ctl.import_document()` are ignored by the web frontend.

### Decision
1. **Bridge Conversion (`bridge.py`)**:
   - Implement structured table-to-Markdown conversion in `import_docx()` for `Table` blocks.
   - For standard tables and tables with simple cell paragraphs, convert rows into Markdown pipe table syntax:
     - Header row with delimiter row `| :--- | :---: | ---: |` respecting column alignments if present.
     - Single-row table handling: If a DOCX table contains only 1 row (no dedicated header), emit a header row with that row's text or empty header indicators accompanied by the delimiter row so `MarkdownImporter` recognizes it as a valid table.
     - Cell contents: sanitize pipe characters `|` to `\|` and normalize internal line breaks or multiple cell paragraphs by joining them with spaces or controlled dividers, because `MarkdownImporter` strips `<br>` via HTML sanitization.
     - Inline text, symbols, and LaTeX formulas inside cells are serialized (e.g. `$math$`).
   - If complex multi-row or multi-column spans (`rowspan > 1` or `colspan > 1`) exist in the DOCX table that standard Markdown pipe tables cannot express natively, emit the cell text in pipe format and append an explicit user warning in `res.warnings` indicating that merged cells were flattened for Markdown editing.
2. **Web Client Feedback (`webapp/js/write.js`)**:
   - Check `res.warnings` and `res.unsupported` upon DOCX import completion.
   - If warnings are present, display a non-blocking toast or banner in the web UI summarizing what formatting or structural aspects were converted/simplified.
3. **DOCX Importer Nested Tables (`chuviettay/importer/docx_importer.py`)**:
   - In `_parse_table()`, recursively inspect cell elements: if a cell contains child tables (`w:tbl`), extract their rows/paragraphs into the cell flow and record a warning in `unsupported`, preventing silent loss of nested tables.

### Alternatives Considered
- *Direct IR transmission to web editor*: Requires replacing the Markdown `textarea` with a full-blown block WYSIWYG editor. Rejected because it violates Constitution Principle II (Simplicity & YAGNI) and would require major rewrite of the web editing architecture. Serializing tables to Markdown maintains full compatibility with the existing editor, live preview pipeline, and user habits.

---

## 2. Table Pagination with Transitive Row Merge Closure

### Problem
In `chuviettay/layout/table_layout.py` (`TableLayoutData.slice_page()`), `row_group_end` is populated by iterating each cell's `rowspan`. However, if Cell A spans rows 1–2 and Cell B in another column spans rows 2–3, `row_group_end[1]` remains 2. If a page break occurs after row 2, Cell B is bisected. Additionally, the fallback when a group exceeds remaining page height slices 1 row, causing arbitrary cell clipping and missing continuation cells.

### Decision
1. **Transitive Row Group Closure**:
   - Precompute disjoint connected row intervals using interval merging / Union-Find over all cell row spans:
     - Any cell with span `[r, r + rowspan - 1]` binds all rows in that range into a single contiguous interval `[start, end]`.
     - Overlapping intervals are iteratively merged until no intervals overlap (transitive closure).
   - In `slice_page()`:
     - `target_end` for row `r` is looked up from the closed interval `[group_start, group_end]`.
     - Page breaks are strictly restricted to row indices where `end_idx` coincides with an interval boundary.
2. **Oversized Group & Page Break Strategy**:
   - If `curr_h > 0` (page already contains content) and the next row group does not fit in `max_height`: break the page immediately; move the entire row group to start at the top of the next page.
   - If `curr_h == 0` (row group starts at top of fresh page) and the row group exceeds `max_height`:
     - Because `DocumentLayoutEngine` already creates a new page when a table slice cannot fit on the current page, when `curr_h == 0`, taking the entire atomic group (even if it exceeds `max_height`) guarantees:
       1. `next_row = target_end + 1 > start_row_idx`, strictly guaranteeing forward progression and eliminating any risk of infinite pagination loops.
       2. Cells within the atomic group are never severed or dropped.
       3. Borders close cleanly for the slice.
3. **Border Stroke Integrity**:
   - When drawing table borders on sliced pages, outer borders (`top`, `bottom`, `left`, `right`) must close cleanly for each page slice.

---

## 3. Rich Inline & Math Formula Line Height Calculations

### Problem
`TableLayoutEngine.layout_table()` computes row height as `num_lines * self.line_height + 2 * self.cell_padding`. When a cell contains math formulas (fractions, square roots, integrals, matrices), the actual stroke extents (ascent above baseline and descent below baseline) can be 2–3x larger than `self.line_height`. In `engine.py`, cells are rendered at fixed baseline `cell_cur_y + self.line_h * 0.8`, causing formula strokes to collide with cell borders and adjacent lines.

### Decision
1. **Reuse `_math_extent` from DocumentLayoutEngine**:
   - `DocumentLayoutEngine._layout_inlines()` already records `self._math_extent[id(math_strokes)] = (ascent, descent)` for each math token.
   - When `cell_inlines_formatter` wraps lines in a table cell:
     - Extract `line_asc = max(extent[0])` and `line_desc = max(extent[1])` across items on that line.
     - Compute line padding matching paragraphs:
       `extra_top = max(0.0, line_asc - 0.7 * line_h)`
       `extra_bot = max(0.0, line_desc - 0.3 * line_h)`
       `effective_line_h = line_h + extra_top + extra_bot`.
     - Return formatted line metrics alongside items to `TableLayoutEngine`.
2. **Accurate Row Height Sizing**:
   - In `layout_table()`, calculate total needed cell height as `sum(effective_line_h) + 2 * self.cell_padding`.
   - Row height `row_heights[r]` is set to `max(needed_cell_height)` across all cells in that row (and distributed for multi-row spanned cells).
3. **Baseline-Centric Rendering**:
   - In `engine.py`, place each line's baseline at `cell_cur_y + extra_top + line_h * 0.8` (or `extra_top + line_h`).
   - Advance `cell_cur_y += effective_line_h`.
   - Guaranteed minimum clearance: formula bounding boxes remain strictly inside the cell rectangle with $\ge \text{cell\_padding}$ margin.

### Alternatives Considered
- *Scaling down formulas to fit standard text line height*: Ruinously shrinks math formulas to illegible sizes. Rejected.
- *Fixed 1.5x multiplier for math cells*: Unpredictable; multi-tier fractions would still clip while simple exponents would have excessive white space. Dynamic ascent/descent measurement is exact and standard typographic practice.

---

## 4. Column Widths & Long Token Breaking

### Problem
In `TableLayoutEngine.compute_column_widths()`, if long unbroken words or formulas exceed available column width, uniform scaling can shrink columns excessively. Furthermore, unbroken tokens that exceed column width are not wrapped, overflowing cell borders.

### Decision
1. **Permissive Token Breaking**:
   - In cell text wrapping, if a single token exceeds available cell width, break the token at character boundaries to fit within `usable_w`.
2. **Minimum Column Width Safeguard**:
   - Enforce a floor on minimum column width (e.g., minimum legible width based on 2-3 average character widths) before applying proportional redistribution.
3. **Table Width Expansion Policy**:
   - Add a configuration option to `TableLayoutEngine`: `expand_to_full_width: bool = True` (default preserving existing behavior), allowing tables with compact content to optionally preserve natural width without artificial stretching.

---

## 5. Optimized Border Stroke Generation

### Problem
`generate_border_strokes()` repeatedly scans all cells in `data.cells` inside nested row and column loops: $O(R \cdot C \cdot N_{cells})$, which on large tables (100 rows $\times$ 20 cols) results in hundreds of thousands of redundant iterations.

### Decision
1. **Precomputed Occupancy & Merge Masks**:
   - Build two 2D boolean matrices in $O(N_{cells})$:
     - `horiz_spanned[r][c]`: true if cell at $(r, c)$ spans across horizontal line $r \leftrightarrow r+1$ (`rowspan > 1`).
     - `vert_spanned[r][c]`: true if cell at $(r, c)$ spans across vertical line $c \leftrightarrow c+1$ (`colspan > 1`).
   - Inner stroke segment generation queries these matrices in $O(1)$.
   - Total time drops to $O(R \cdot C) < 5\text{ms}$ for large tables.

---

## 6. Interactive Table Creation in Web UI

### Problem
`btn-md-table` in `webapp/js/write.js` hardcodes a 3x3 table template. Users needing different table dimensions must manually type or modify markdown pipe tables.

### Decision
1. Add a small modal/dialog or dropdown for table insertion:
   - Inputs: Rows (default 3), Columns (default 3), Header row checkbox (default checked).
   - Generates the matching Markdown pipe table snippet and inserts at cursor position.
