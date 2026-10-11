# Feature Specification: Table Layout Robustness, Geometry Scaling & DOCX Import Hardening

**Feature Branch**: `032-table-layout-docx-hardening`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User review of commit `c6fe1cf` on `main`, focusing on table pagination overflow prevention, math metrics scaling synchronization in table cells, long unbroken token wrapping in the live rendering pipeline, DOCX table column count with merged cells, document block order for nested tables, table generation modal header controls, and geometric stroke bounding box test tightening.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe Pagination for Merged Row Groups Exceeding Page Limits (Priority: P1)

As a user composing documents with complex merged-cell tables, I want tables with tall merged row groups to paginate safely without overflowing beyond the printable bottom margin of the page or hanging the layout engine, so that every handwritten stroke remains completely visible within the physical page boundaries.

**Why this priority**: An oversized merged row group currently risks being placed onto the current page even when its required height exceeds the remaining printable height, causing table borders and text to spill off the bottom of the page or into the footer area. Ensuring all visual elements stay strictly within the page bounds is a fundamental correctness requirement.

**Independent Test**: Render a document containing a table with merged row groups of varying heights:
1. When a merged group exceeds the remaining page height but fits on an empty page, verify the engine moves the entire group to a new page intact.
2. When a merged group exceeds even the full height of a fresh empty page, verify the engine executes a controlled continuation strategy with closed border caps, continuation diagnostics, and confirms 100% of rendered strokes lie within printable vertical limits (`y <= page_height - margin_bottom`).

**Acceptance Scenarios**:

1. **Given** a page with existing content where the remaining vertical space is 200 pt and a merged row group requires 350 pt (and the full page height is 800 pt), **When** pagination slices the table, **Then** the entire merged row group is deferred to the beginning of the next page rather than overflowing the current page.
2. **Given** a table with an oversized merged cell whose content requires 900 pt (exceeding an entire 842 pt page's printable area), **When** pagination evaluates the group on a fresh page, **Then** the engine paginates the rows or content across page boundaries with valid top/bottom border caps, emits an explicit diagnostic warning, and keeps every stroke within the printable page vertical bounds.
3. **Given** any table pagination operation, **Then** progression is strictly monotonic (`next_row > start_row_idx` or incremental slice progress) without infinite loops or hanging.

---

### User Story 2 - Formula Vertical Metrics Scaling Synchronization (Priority: P1)

As a user inserting mathematical formulas (fractions, square roots, integrals, matrices) inside table cells across various font sizes and handwriting scales, I want table row heights and cell vertical padding to scale proportionally with the formula's actual rendered height, so that formulas never collide with or spill over the cell's horizontal borders.

**Why this priority**: Formula vertical ascent and descent in table cells are currently tracked in unscaled bank units ($S=1.0$) rather than being scaled by the effective handwriting scale factor ($S$). When font scale is increased or when `auto_xh` normalization is active, row heights are underestimated, causing tall formulas to clip through cell borders.

**Independent Test**: Render tables containing tall multi-story formulas (e.g. `\frac{a}{b}`, `\sqrt{\frac{x}{y}}`, `\int_0^1 f(x) dx`) under multiple scale settings (`scale=0.8`, `scale=1.0`, `scale=1.5`, and `--auto-xh`). Assert that measured row height is strictly greater than formula vertical span plus padding, and that no formula stroke touches or crosses top/bottom cell borders.

**Acceptance Scenarios**:

1. **Given** a table cell containing a tall fraction $\frac{x^2 + 1}{y^2 - 1}$, **When** rendered at scale $S=1.5$, **Then** the cell's row height dynamically expands to accommodate $1.5 \times$ the formula's height plus cell margins.
2. **Given** a table with both text-only rows and formula-containing rows, **When** rendered at any valid scale, **Then** the row containing the formula expands appropriately while text-only rows maintain standard line heights.
3. **Given** a table containing formulas, **When** uncompressed `.xopp` stroke points are extracted, **Then** every point $(x, y)$ of the formula strokes satisfies $y_{\text{cell\_top}} < y < y_{\text{cell\_bottom}}$ and $x_{\text{cell\_left}} < x < x_{\text{cell\_right}}$.

---

### User Story 3 - Long Unbroken Token Wrapping in Live Table Rendering Pipeline (Priority: P2)

As a user writing tables that contain long URLs, file paths, hashes, or unbreakable technical identifiers, I want the table layout pipeline to automatically break long tokens across character boundaries when they exceed column width, so that text does not bleed horizontally into adjacent columns or off the right side of the page.

**Why this priority**: While a fallback text wrapping utility supports character-level breaking, the active document formatting pipeline used during document layout currently treats tokens as unbreakable units. When a single word or URL exceeds the usable column width, it overflows the cell boundaries.

**Independent Test**: Render a table cell containing an unbroken string of 60+ characters (e.g., `https://example.com/very/long/nested/path/to/resource/without/spaces`) whose natural width exceeds the column width. Assert that the string wraps into multiple lines within the cell, the cell expands vertically, and all stroke coordinates remain inside the column's horizontal bounds.

**Acceptance Scenarios**:

1. **Given** a table cell with column width 120 pt and an unbroken token with measured width 250 pt, **When** the document formatting pipeline processes the cell, **Then** the token is broken into multiple lines that each fit within the 120 pt width.
2. **Given** a table cell with mixed normal words and one long unbreakable URL, **When** formatted, **Then** normal words break at spaces while the URL breaks across character boundaries, maintaining natural word boundaries where possible.
3. **Given** any wrapped token inside a cell, **Then** the maximum horizontal stroke coordinate $x_{\max}$ does not exceed the cell's right border minus inner padding.

---

### User Story 4 - DOCX Table Column Alignment & Nested Block Document Order (Priority: P2)

As a user importing Microsoft Word documents (.docx) containing complex tables with merged cells and nested tables, I want the imported Markdown table to maintain correct column alignment based on the true logical grid, and I want paragraphs and nested tables within cells to preserve their original document sequence, so that imported document content is not jumbled or misaligned.

**Why this priority**: DOCX table conversion currently determines table column count by counting cell objects in raw rows rather than mapping the underlying occupancy grid (considering `colspan` and `rowspan`). This creates misaligned Markdown columns. Furthermore, paragraphs and nested tables within a single cell are currently parsed out of order (all paragraphs first, then child tables appended at the end).

**Independent Test**:
1. Import a DOCX file containing a 3-column table where the first row merges columns 1 and 2: verify the generated Markdown table has exactly 3 columns and that non-merged cells in subsequent rows align with their correct column headers.
2. Import a DOCX file containing a cell with sequential content (Paragraph A $\to$ Nested Table $\to$ Paragraph B): verify the extracted content preserves the exact sequence $A \to \text{Nested Table} \to B$.

**Acceptance Scenarios**:

1. **Given** a DOCX table where row 1 has a cell spanning 2 columns followed by 1 normal cell, and row 2 has 3 normal cells, **When** exported to Markdown in the web bridge, **Then** the Markdown table produces a 3-column structure where row 1 includes placeholder/spanning padding maintaining column 3's alignment.
2. **Given** a DOCX cell containing text, followed by an inner table, followed by trailing text, **When** parsed by the DOCX importer, **Then** the resulting block list preserves the alternating sequence without relocating trailing text ahead of the inner table.
3. **Given** any complex DOCX table conversion, **Then** descriptive user warnings are emitted when rowspan/colspan structures are simplified to standard Markdown pipe tables.

---

### User Story 5 - Table Generation Modal Header Controls & Geometric Verification Gates (Priority: P3)

As a user inserting tables via the web interface modal, I want the "Has header row" checkbox to accurately control whether the inserted Markdown table has a header row or starts immediately with data rows, and as a repository maintainer, I want CI to enforce strict geometric stroke verification gates in `.xopp` documents.

**Why this priority**: The web table creation dialog currently reads the `hasHeader` checkbox but ignores it, always generating a header row and separator. Additionally, unit and integration tests currently check superficial conditions (such as string presence or slice counts) without verifying the physical bounding boxes of strokes in generated files.

**Independent Test**:
1. Open the web table creation modal, uncheck "Has header row", click Insert, and verify the inserted template properly represents a headerless table in Markdown.
2. Execute the automated geometric test suite: unpack generated `.xopp` files and assert all stroke points $(x, y)$ strictly adhere to cell bounding boxes and page print margins.

**Acceptance Scenarios**:

1. **Given** the table creation modal in the web app, **When** the user unchecks "Has header row" (or "Hàng tiêu đề") and confirms a $2 \times 3$ table, **Then** the inserted Markdown table produces a valid representation for a headerless table rather than generating standard "Cột 1 | Cột 2 | Cột 3" headers.
2. **Given** an automated test asserting table rendering, **When** the test runs, **Then** it verifies that all handwritten stroke coordinates within each table cell satisfy bounding constraints: $x \in [\text{cell\_left}, \text{cell\_right}]$ and $y \in [\text{cell\_top}, \text{cell\_bottom}]$.
3. **Given** an automated test asserting document pagination, **When** testing tables split across pages, **Then** it verifies that no stroke across any page has a $y$ coordinate exceeding $\text{page\_height} - \text{margin\_bottom}$.

---

### Edge Cases

- **Merged row group height larger than 2 full pages**: The continuation engine must split the rows or content across multiple pages cleanly without infinite loops, generating top and bottom table border caps on each page slice.
- **Table cell width smaller than a single character**: Character wrapping must break down to 1 character per line without throwing zero-division or infinite loop errors.
- **Formulas wider than cell column width**: Large formulas must scale down or wrap sub-expressions so that formula strokes do not bleed past cell borders.
- **DOCX table with irregular or zero-width grid definitions**: Occupancy grid builder must fall back gracefully to sequential column counting without crashing.
- **Empty table cells and empty rows**: Serializer and layout engine must preserve empty cell spacing without collapsing row heights below minimum line height.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The table pagination engine MUST detect when a merged row group cannot fit within the remaining vertical space of the active page and MUST defer the entire group to a fresh page if it fits on an empty page.
- **FR-002**: When a single row or merged row group exceeds the total printable height of an entire empty page, the pagination engine MUST perform controlled continuation across multiple pages, closing borders cleanly on each page slice and emitting a warning diagnostic.
- **FR-003**: The layout engine MUST guarantee that no stroke coordinate in any rendered table page exceeds the printable vertical boundary ($\text{page\_height} - \text{margin\_bottom}$).
- **FR-004**: Table cell inline formatting MUST scale formula vertical metrics (ascent and descent) by the active scale factor ($S \times \text{scale\_mult}$) before calculating line heights and cell bounding boxes.
- **FR-005**: Table cell row heights MUST expand dynamically to accommodate the scaled vertical height of any enclosed mathematical formulas plus inner cell margins.
- **FR-006**: The document formatting pipeline used for table cells MUST support character-level wrapping for tokens whose natural width exceeds the usable cell width.
- **FR-007**: When breaking long tokens inside table cells, the engine MUST preserve standard whitespace word breaking for words that fit normally and apply character-level breaking only to individual tokens that exceed the available width.
- **FR-008**: The web bridge DOCX-to-Markdown converter MUST reconstruct table column structure using a 2D occupancy grid that accounts for cell `colspan` and `rowspan`.
- **FR-009**: The DOCX-to-Markdown converter MUST place non-merged cells into their true logical columns and pad merged cell spans with appropriate Markdown table cell fillers.
- **FR-010**: The DOCX document importer MUST iterate cell children in document order, preserving the interleaved sequence of paragraphs and nested tables.
- **FR-011**: The web table creation modal MUST respect the "has header" checkbox, generating valid Markdown table templates matching the user's header selection.
- **FR-012**: The test suite MUST provide geometric verification utilities that unpack `.xopp` documents and validate stroke coordinate bounds against cell borders and page margins.
- **FR-013**: Existing Plain paper golden master test hashes MUST remain 100% invariant, ensuring table layout enhancements introduce zero regression to continuous text layout.
- **FR-014**: All architecture rules enforced by `tests/test_architecture.py` MUST remain fully compliant (zero MVC violations across Model, View, CLI, and Controller).

---

### Key Entities

- **Table**: Semantic document block representing a tabular grid of rows and cells, supporting row/column spans, column alignments, and nested blocks.
- **TableRow**: Sequence of table cells within a table row.
- **TableCell**: Individual cell containing one or more blocks (paragraphs, formulas) and optional spanning metadata (`rowspan`, `colspan`).
- **TableOccupancyGrid**: 2D logical matrix mapping $(r, c)$ coordinate cells to their occupying logical column positions, accounting for merged spans.
- **LaidOutCell**: Positioned table cell with resolved spatial coordinates $(x, y, \text{width}, \text{height})$ and rendered stroke lines.
- **LineVerticalMetrics**: Vertical measurement record capturing baseline ascent, descent, line width, and total height for text and formula lines.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated table strokes across all test cases remain strictly inside page vertical boundaries ($y \le \text{page\_height} - \text{margin\_bottom}$).
- **SC-002**: 100% of mathematical formula strokes in table cells remain within the vertical bounding box of their respective cells across all supported scale factors ($0.5 \le S \le 2.0$ and `--auto-xh`).
- **SC-003**: Long unbreakable tokens (URLs, hashes, strings $> 50$ characters) wrap completely inside column widths with zero horizontal stroke overflow ($x \le \text{cell\_right} - \text{padding}$).
- **SC-004**: DOCX tables with merged cells import into Markdown with correct logical column counts and proper column alignment across 100% of test fixtures.
- **SC-005**: Nested DOCX cell elements maintain 100% order fidelity (paragraphs before, between, and after child tables retain exact sequential order).
- **SC-006**: The full test suite passes with zero failures, zero regressions on Golden Master SHA-256 hashes, and zero MVC violations.

---

## Assumptions

- Markdown pipe tables have inherent limitations representing complex cell merges (`colspan` and `rowspan`). Emitting occupancy-padded Markdown with user diagnostics is the agreed standard.
- When a table modal creates a headerless table, generating a valid GFM representation (such as an empty header row `|   |   |` with separator followed by data rows) ensures compatibility with CommonMark and markdown-it parsers.
- Scaling down formulas wider than a cell column to fit available column width provides better readability than clipping or horizontal overflow.
- Performance impact of character-level token wrapping and occupancy grid construction is negligible for typical document sizes (< 100 table rows).
