# Feature Specification: Table Merged-Cell Occupancy Grid Layout, Single-Pipeline Architecture, and Math Root Stroke Deduplication

**Feature Branch**: `009-table-and-math-layout-fixes`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User review of commit `8b4aae0bf83c7bca7c45d60c668333c071dd3b87`:
1. **Critical Defect (P0 - Math Root Glyph Duplication)**: Mathematical root layout (`RootNode` in `math_layout.py`) duplicates radicand strokes and glyphs. Currently, `strokes = list(rad_item.strokes)` and `glyphs = list(rad_item.glyphs)` are copied before subsequently appending shifted glyphs and strokes again. For expressions such as $\sqrt{x^2+1}$, symbols under the radical appear twice (once at the unshifted origin, once under the radical), doubling vector strokes and distorting output.
2. **Critical Defect (P0 - Table Rowspan Missing Occupancy Grid)**: Table rendering in `DocumentLayoutEngine.render()` resets column indexing (`c_curr = 0`) on every row without tracking multi-row cell reservations. When a cell in row $N$ spans multiple rows (`rowspan > 1`), row $N+1$ treats column 0 as free, causing subsequent cells to overlap and shift horizontally. An explicit 2D cell occupancy grid (`grid[row][col]`) is required to skip occupied slots and locate the first vacant column.
3. **Architectural Debt (P1 - Dual Table Layout Divergence)**: Table layout calculation is currently split between `TableLayoutEngine.layout_table()` and `DocumentLayoutEngine.render()`. Both calculate cell dimensions and coordinate offsets independently. All table layout and pagination calculations must be consolidated into a single source of truth: `TableLayoutEngine` produces structured `TableLayoutData` (or page slices), and `DocumentLayoutEngine` renders that data without recomputing geometry.
4. **Test Completeness (P1 - Merged Cell & Math Stroke Regressions)**:
   - Existing table tests only cover column widths, jagged row padding, and outer border styles. Add regression tests asserting exact cell coordinates, non-overlapping bounds, and suppression of internal grid borders for `colspan=2`, `rowspan=2`, and combined `colspan + rowspan`.
   - Existing math tests only verify positive bounding boxes (`width > 0`, `height > 0`). Add tests verifying that `TextNode` (e.g. $\sqrt{x}$, $\sqrt{x^2+1}$, $\frac{x+1}{2}$, $x^2+1$, $x_i^2$) actually generates non-empty handwriting glyphs and vector strokes (`total_glyph_strokes > 0`).
5. **Real-World Document Verification (P2)**: Convert representative sample documents (`sample.txt`, `sample.md`, `sample.docx`) with Vietnamese diacritics, lists, merged tables, and math formulas into `.xopp` files, verifying clean visual rendering in Xournal++.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Mathematical Root Rendering Without Duplicate Strokes or Glyphs (Priority: P1)

As a student or reader viewing handwritten mathematical notes, I want square root and nth-root expressions (e.g. $\sqrt{x}$, $\sqrt{x^2+1}$, $\sqrt[3]{a+b}$) to display exactly one clean set of characters positioned under the radical sign, so that characters are never duplicated, shifted, or drawn with double vector lines.

**Why this priority**: Duplicate glyphs and vector strokes cause severe visual artifacts, illegible math notation, doubled file sizes, and erratic pen-stroke animations in handwriting vector applications like Xournal++.

**Independent Test**: Measure and render a composite root expression (such as $\sqrt{x^2+1}$); inspect the resulting layout item's glyphs and strokes; verify that the total stroke count equals exactly the radical bar/hook strokes plus the radicand's strokes, and that all radicand glyphs have horizontal offsets greater than or equal to the radical sign width.

**Acceptance Scenarios**:
1. **Given** a mathematical root expression with a composite radicand (e.g. $\sqrt{x^2+1}$), **When** the math layout engine measures and positions the root, **Then** all glyphs and strokes of the radicand are shifted horizontally by the width of the radical sign without leaving unshifted duplicate copies at the origin.
2. **Given** a root expression with an index (e.g. $\sqrt[3]{n}$), **When** the expression is laid out, **Then** the index, radical symbol, horizontal overbar, and radicand characters are rendered once without stroke duplication.
3. **Given** a nested root expression (e.g. $\sqrt{1 + \sqrt{x}}$), **When** layout occurs, **Then** each nested radical bounds its inner terms accurately without repeating internal glyphs.

---

### User Story 2 - Accurate Multi-Row Table Merged Cells (Rowspan) via Occupancy Grid (Priority: P1)

As a document author converting tables with merged cells from Markdown or Word documents, I want multi-row cells (`rowspan > 1`) and multi-column cells (`colspan > 1`) to reserve their full rectangular area across all spanned rows and columns, so that subsequent cells in lower rows automatically find the next available vacant column without overlapping, colliding, or misaligning.

**Why this priority**: Without an occupancy grid, any table containing a cell with `rowspan=2` in column 0 will cause the second row's first cell to also be placed at column 0. This corrupts table layouts, overlaps cell text, and breaks complex Word/DOCX import.

**Independent Test**: Define a 2-row by 2-column table where cell (0, 0) has `rowspan=2`, cell (0, 1) is "B", and row 1 contains cell "C"; layout the table; verify that cell "C" is assigned to column index 1 and horizontal coordinate $x_1$, and that column 0 on row 1 is marked as occupied by cell (0, 0).

**Acceptance Scenarios**:
1. **Given** a table with a cell spanning $R$ rows and $C$ columns at row $r$, column $c$, **When** the layout engine assigns cell positions, **Then** all grid coordinates $(r..r+R-1, c..c+C-1)$ are reserved in an occupancy grid.
2. **Given** subsequent cells in the current or subsequent spanned rows, **When** the layout engine places the next cell, **Then** it advances to the first unoccupied column in that row.
3. **Given** a table containing cells with both `colspan` and `rowspan` simultaneously (e.g., $2 \times 2$ merged cell block), **When** cells are positioned, **Then** none of the table cells have overlapping bounding boxes, and total table width matches the sum of column widths.
4. **Given** table border rendering with merged cells, **When** grid border strokes are generated, **Then** interior grid lines within the merged rectangular areas are suppressed, while outer perimeter borders around the merged cells remain intact.

---

### User Story 3 - Unified Table Layout Pipeline & Single Source of Truth (Priority: P1)

As a software engineer maintaining the layout engine, I want a single unified table layout component (`TableLayoutEngine`) that computes all cell geometries, text wrapping, row heights, and pagination slices into a structured layout object (`TableLayoutData`), and a document renderer (`DocumentLayoutEngine`) that consumes this data directly without re-implementing layout logic, so that layout behavior and border rendering are always consistent and bug fixes apply universally.

**Why this priority**: Having duplicate layout logic across `TableLayoutEngine.layout_table()` and `DocumentLayoutEngine.render()` leads to desynchronized behavior, where fixes applied to one engine are not reflected in actual document rendering.

**Independent Test**: Provide an identical table to `TableLayoutEngine.layout_table()` and `DocumentLayoutEngine.render()`; verify that cell positions, row heights, and column widths used during rendering match the output of `TableLayoutEngine` exactly.

**Acceptance Scenarios**:
1. **Given** a table block in a document, **When** `DocumentLayoutEngine` encounters the table, **Then** it delegates cell wrapping, row height computation, and occupancy positioning to `TableLayoutEngine`.
2. **Given** a multi-page table, **When** the table exceeds the remaining height of the active page, **Then** `TableLayoutEngine` segments the table into page slices (`TableLayoutData`) respecting row boundaries, and each slice is rendered with appropriate top/bottom borders.
3. **Given** inline content (rich text and math formulas) within table cells, **When** the table is laid out, **Then** cell dimensions accommodate wrapped text and math heights consistently across all rows.

---

### User Story 4 - Rigorous Regression Testing of Math Handwriting Strokes & Merged Cell Geometry (Priority: P1)

As a test engineer, I want automated test suites to verify that mathematical text nodes produce concrete handwriting strokes and glyphs (not merely non-zero widths), and to verify that merged table cells have exact bounding boxes, non-overlapping coordinates, and correct border segment counts, so that layout regressions cannot slip into releases unnoticed.

**Why this priority**: Prior tests only checked `item.size.width > 0` and `item.size.height > 0`. A dummy implementation that calculates dimensions without generating vector handwriting strokes would pass existing tests. Comprehensive assertions on glyph counts and stroke counts are essential for production reliability.

**Independent Test**: Execute `pytest tests/test_math_layout.py tests/test_table_layout.py`; verify that assertions check `len(item.glyphs) > 0`, `sum(len(g.strokes) for g in item.glyphs) > 0`, cell coordinate non-overlap, and border line counts for merged cells.

**Acceptance Scenarios**:
1. **Given** math expressions including $x^2+1$, $\sqrt{x}$, $\sqrt{x^2+1}$, $\frac{x+1}{2}$, and $x_i^2$, **When** processed by `MathLayoutEngine`, **Then** the output contains at least one `PositionedGlyph` and the sum of vector strokes across all glyphs is strictly greater than zero.
2. **Given** a square root expression $\sqrt{x^2+1}$, **When** verified in tests, **Then** the number of radicand glyphs equals the number of characters in the radicand ($x, 2, +, 1$), and the total glyph count equals exactly 4 (no duplicates).
3. **Given** tables with `colspan=2`, `rowspan=2`, and combined `colspan=2, rowspan=2`, **When** processed by `TableLayoutEngine`, **Then** tests assert that no cell bounding boxes overlap, cell widths span the exact sum of covered columns, cell heights span the exact sum of covered rows, and internal dividing lines within merged areas are omitted from generated border strokes.

---

### User Story 5 - Real-World End-to-End Document Conversion & Xournal++ Verification (Priority: P2)

As an end-user converting study materials, I want to convert representative real-world documents (`sample.txt`, `sample.md`, `sample.docx`) containing Vietnamese diacritics, numbered lists, merged-cell tables, and inline/block mathematical formulas into `.xopp` files, so that the resulting notes can be opened and studied seamlessly in Xournal++.

**Why this priority**: Synthetic unit tests cannot replace end-to-end verification of actual user files. Testing real documents guarantees that all layers (importer, IR, math layout, table layout, stroke synthesizer, XOPP gzip export) function harmoniously together.

**Independent Test**: Run a conversion CLI or automated verification script against sample test files (`sample.txt`, `sample.md`, `sample.docx`); verify that valid `.xopp` archives are produced without warnings or errors, and inspect the XML stroke output to confirm proper pagination and rendering.

**Acceptance Scenarios**:
1. **Given** a `sample.txt` document containing Vietnamese paragraphs, blank line separators, and list items, **When** converted to `.xopp`, **Then** lines are wrapped correctly, blank line vertical spacing is preserved, and page streaming completes cleanly.
2. **Given** a `sample.md` document containing headers, lists, tables with alignment and merged headers, and LaTeX math blocks ($E = mc^2$, $\sqrt{x^2+y^2}$), **When** converted to `.xopp`, **Then** tables and math expressions render with handwritten vector strokes.
3. **Given** a `sample.docx` document with Word tables, merged cells, and equation blocks, **When** converted to `.xopp`, **Then** the importer extracts table structures, merged cell spans, and equations into Document IR, and the layout engine renders them accurately.

---

## Edge Cases

- **Root with Empty or Degenerate Radicand**: A root expression with no radicand (e.g. $\sqrt{}$) MUST render the radical sign with a minimum horizontal bar width and zero radicand glyphs without throwing `IndexError` or producing negative dimensions.
- **Deeply Nested Roots**: An expression such as $\sqrt{\sqrt{\sqrt{x}}}$ MUST correctly propagate scale and bounding heights at each nesting depth without multiplying strokes or corrupting vertical alignment.
- **Rowspan Exceeding Total Rows**: If an imported table row specifies `rowspan=5` but only 2 rows remain in the table, the layout engine MUST defensively clamp the effective `rowspan` to the remaining row count rather than raising `IndexError`.
- **Colspan Exceeding Total Columns**: If a cell specifies `colspan=10` on a 3-column table, the layout engine MUST clamp `colspan` to the remaining column count on that row.
- **Fully Merged Table (Single Cell $N \times M$)**: A table consisting of a single cell with `rowspan=N` and `colspan=M` MUST render as a single large bordered cell without generating any internal grid strokes.
- **Multi-Page Rowspan Boundary**: When a table splits across a page boundary while a cell with `rowspan > 1` is active, the engine MUST either fit the entire merged cell row-group on the next page or cleanly slice visible borders without leaving orphaned negative heights.
- **Zero-Width or Extreme Column Widths**: If available width is very narrow (e.g. table cell width $< 20$ units), cell text wrapping MUST gracefully wrap character-by-character or clamp to minimum padding without dividing by zero.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Math root layout MUST initialize glyph and stroke collections as empty lists (`glyphs = []`, `strokes = []`) prior to populating radical sign components, optional degree glyphs/strokes, and horizontally shifted radicand items.
- **FR-002**: Math root layout MUST append radicand glyphs and strokes exactly once, shifted by the width of the radical sign (`sign_w`). Unshifted copies of the radicand MUST NOT be added to the output. If `node.degree` is present, it MUST be scaled and positioned above the radical hook without duplicating radicand strokes.
- **FR-003**: The table layout engine MUST maintain a two-dimensional cell occupancy grid (`grid[row][col]`) tracking occupied grid coordinates across all rows and columns. Both `compute_column_widths` and row padding MUST use occupancy resolution to prevent phantom column padding or misplaced cell width attribution when `rowspan` is present.
- **FR-004**: When placing a table cell with column span $C$ and row span $R$ at starting position $(r, c)$, the layout engine MUST mark all grid coordinates $(r+i, c+j)$ for $0 \le i < R$ and $0 \le j < C$ as occupied.
- **FR-005**: When positioning the next cell on row $r$, the layout engine MUST advance past any columns marked as occupied by previous cells or cells spanning from earlier rows to find the first free column.
- **FR-006**: Table cell horizontal coordinate $x$ MUST be computed based on the exact start column index $c$ resolved by the occupancy grid: $x = x_0 + \sum_{k=0}^{c-1} \text{col\_widths}[k]$.
- **FR-007**: Table cell width MUST be computed based on the resolved start column $c$ and column span $C$: $\text{width} = \sum_{k=c}^{c+C-1} \text{col\_widths}[k]$.
- **FR-008**: Table cell height MUST be computed based on the start row $r$ and row span $R$: $\text{height} = \sum_{k=r}^{r+R-1} \text{row\_heights}[k]$.
- **FR-009**: Table layout calculation MUST be unified such that `TableLayoutEngine` is the single source of truth for cell geometries, row heights, and border strokes. `DocumentLayoutEngine` MUST consume structured layout data from `TableLayoutEngine` rather than recalculating cell coordinates independently.
- **FR-010**: Table border generation MUST suppress internal grid lines (both horizontal and vertical) that fall strictly inside any merged cell area defined by `colspan > 1` or `rowspan > 1`.
- **FR-011**: Math layout tests MUST explicitly verify that `TextNode` instances generate non-empty `glyphs` and that the total count of vector strokes across all glyphs is strictly positive (`total_glyph_strokes > 0`).
- **FR-012**: Table layout tests MUST include explicit regression test cases for `colspan=2`, `rowspan=2`, and combined `colspan=2, rowspan=2`, verifying non-overlapping cell rectangles, accurate coordinates, and correct border stroke counts.
- **FR-013**: Test collection across all modules MUST be resilient against missing optional dependencies (e.g. `tkinter` in headless environments, `python-docx`, `markdown-it-py`), skipping gracefully at the module or test level without collection errors.
- **FR-014**: End-to-end conversion workflows MUST support processing `sample.txt`, `sample.md`, and `sample.docx` documents containing Vietnamese text, lists, merged-cell tables, and math formulas, outputting valid `.xopp` documents.
- **FR-015**: Table pagination across page boundaries MUST maintain multi-row cell group cohesion: rows covered by an active `rowspan > 1` MUST be kept on the same page unless the entire merged row-group height exceeds printable page capacity.

### Key Entities

- **RootLayoutItem**: Math layout item representing a radical symbol, optional index, horizontal overbar, and radicand. Contains bounding dimensions (`width`, `ascent`, `descent`), radical vector strokes, and deduplicated radicand glyphs/strokes shifted by `sign_w`.
- **TableGridOccupancy**: A 2D tracking matrix (`list[list[Optional[TableCell]]]]` or coordinate set) recording which grid cell positions are occupied by primary cells or spanned cells.
- **LaidOutCell**: Geometric description of a placed table cell, containing physical coordinates $(x, y)$, dimensions $(\text{width}, \text{height})$, grid span indices $(\text{row}, \text{col}, \text{rowspan}, \text{colspan})$, text wrapping lines, and rich inline elements.
- **TableLayoutData**: Complete geometric specification of a laid out table or table page slice, containing bounding origin $(x, y)$, total dimensions $(\text{width}, \text{height})$, column width array, row height array, laid out cells, and generated border vector strokes.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In any mathematical root expression (e.g. $\sqrt{x^2+1}$), the number of output glyphs corresponding to the radicand is exactly equal to the number of characters in the radicand (zero duplicate glyphs), and vector stroke count equals exactly radical strokes plus radicand strokes.
- **SC-002**: For any table containing multi-row cells (`rowspan > 1`), 100% of cells in subsequent rows are placed in unoccupied columns with zero overlapping bounding boxes.
- **SC-003**: 100% of internal grid lines inside merged cell boundaries are omitted from table border stroke rendering, while all outer perimeter boundaries remain fully drawn.
- **SC-004**: 100% of table layout logic is centralized in `TableLayoutEngine`, eliminating duplicate geometry calculation loops from `DocumentLayoutEngine`.
- **SC-005**: 100% of automated tests pass deterministically across Linux and Windows CI environments with zero test collection errors or unhandled timeouts.
- **SC-006**: Representative test documents (`sample.txt`, `sample.md`, `sample.docx`) convert to `.xopp` format and render all Vietnamese characters, tables, and math formulas without layout distortion.

---

## Assumptions

- **Bank Glyph Availability**: Characters present in the symbol bank (e.g. Latin letters, digits, basic math symbols) produce vector strokes via `StrokeBankWriter`. Characters not found in the bank fall back cleanly to character width metrics or generic placeholder strokes without crashing.
- **Table Width Constraints**: Total table width is constrained by the document's printable page width (`page_width - 2 * margin`). If user-specified columns exceed printable width, the layout engine scales column widths proportionally to fit the printable area.
- **Cell Content Overflow**: Cell height expands vertically to accommodate multi-line wrapped text or tall mathematical formulas. The row height equals the maximum height required by any cell starting on that row.
- **Pagination Slicing**: When a table crosses a page boundary, slicing occurs cleanly between table rows. If a single row is taller than an entire empty page, it is placed at the top of the next page.
