# Feature Specification: Table Layout and DOCX Import Fidelity

**Feature Branch**: `031-table-docx-layout-fidelity`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Tôi đã rà soát trực tiếp mã nguồn trên GitHub của repository caoduongle/viet, tập trung vào luồng từ nhập tài liệu đến bố cục bảng và xuất Xournal++ .xopp. P1: Lỗi nhập DOCX trên web có thể làm mất toàn bộ bảng; P1: Phân trang chưa xử lý an toàn mọi trường hợp ô gộp; P1: Chiều cao dòng công thức trong ô chưa được tính đủ; P2: Phân bổ chiều rộng cột và token dài; P2: Nhập DOCX chưa bảo toàn đầy đủ cấu trúc và định dạng bảng; P2: Bộ sinh đường viền có thể tốn chi phí lớn với bảng lớn; UX: Giao diện tạo bảng còn quá cố định; Lỗ hổng kiểm thử và thứ tự triển khai khuyến nghị."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lossless Table Preservation during Document Import and Web Editing (Priority: P1)

Users (such as educators and students) importing DOCX documents containing structured tables need their tables to be completely preserved through the import, editing, preview, and export workflows rather than having table data silently discarded.

**Why this priority**: Silent data loss is the most critical failure mode. Losing entire tables breaks user trust and destroys document fidelity before any layout logic is even reached.

**Independent Test**: Import a DOCX document containing paragraphs, multiple tables (with various cell data types), and following paragraphs. Verify all tables appear in the web editor, retain cell content, render in document previews, and export without missing elements.

**Acceptance Scenarios**:

1. **Given** a DOCX document containing text paragraphs and one or more tables, **When** imported via the web interface, **Then** all tables and cell contents are preserved alongside surrounding paragraphs and presented in the editor.
2. **Given** an imported document containing formatting features not fully representable in the default view, **When** the import completes, **Then** the interface displays clear diagnostic notices/warnings explaining what was simplified, while preserving all textual data.
3. **Given** an imported document with tables, **When** previewed or exported to output formats (e.g. Xournal++ `.xopp`), **Then** all table rows, columns, and text values match the source document data without omission.

---

### User Story 2 - Safe Multi-Page Table Pagination with Merged Cells (Priority: P1)

Users working with long documents containing multi-row merged cells (`rowspan`) need tables to paginate cleanly across multiple pages without splitting merged cells mid-span, cutting borders incorrectly, or entering infinite layout loops.

**Why this priority**: Document export correctness requires that merged blocks of information remain visually unified and readable across page breaks, avoiding overlapping text, broken strokes, or hangs.

**Independent Test**: Process a multi-page table where multiple columns contain overlapping or chained row merges (e.g. Cell A spans rows 1–2, Cell B spans rows 2–3). Verify page breaks occur strictly at valid row boundaries outside merged groups.

**Acceptance Scenarios**:

1. **Given** a table with transitively linked merged row groups (where a merge in one column overlaps rows merged in another column), **When** paginating across pages, **Then** the entire connected row group is treated as an indivisible unit and never bisected by a page break.
2. **Given** a row group whose height exceeds the remaining space on the current page, **When** paginating, **Then** the entire row group moves to the next page to start fresh from the top margin if it fits on a full page.
3. **Given** an exceptionally tall single cell or row group whose height exceeds an entire printable page, **When** paginating, **Then** the system applies a deterministic continuation strategy with explicit boundary demarcation and produces a non-blocking diagnostic notice, preventing infinite looping or crashes.
4. **Given** a table split across multiple pages, **When** pages are rendered, **Then** all top, bottom, and outer borders are drawn consistently for each page slice without dangling or missing border segments.

---

### User Story 3 - Formula and Rich Inline Height Calculation in Table Cells (Priority: P1)

Users creating STEM materials (math, physics, chemistry) need formulas inside table cells (such as multi-tier fractions, square roots, integrals, super/subscripts) to be allotted sufficient row height and accurate baseline alignment so that formula strokes never bleed into adjacent rows or collide with cell borders.

**Why this priority**: Scientific and educational worksheets heavily depend on formulas inside tables. Formulas clipping through borders or overlapping neighboring rows makes exported documents unusable for teaching and grading.

**Independent Test**: Construct a table containing cells with plain text and cells with tall math expressions (e.g. `\frac{a}{b}`, `\sqrt{\frac{x}{y}}`). Verify measured row height accommodates full formula ascent, descent, and cell padding, with zero stroke collision against cell boundaries.

**Acceptance Scenarios**:

1. **Given** a table cell containing rich text or math formulas, **When** cell content height is calculated, **Then** the height accounts for the exact vertical span (ascent above baseline + descent below baseline + line spacing) of each line rather than a fixed uniform text height.
2. **Given** a row containing both short single-line text and tall multi-tier formula expressions, **When** rendered, **Then** the row height expands to match the tallest cell content, and baselines are aligned consistently with proper vertical cell margins.
3. **Given** cells with multi-line formulas, **When** exported, **Then** all formula bounding boxes reside strictly within the cell's interior rectangle and maintain minimum padding from all four borders.

---

### User Story 4 - Robust Column Width Distribution and Token Containment (Priority: P2)

Users working with tables containing long unbroken tokens (such as URLs, code identifiers, chemical notation, or unspaced Vietnamese words) need tables to distribute widths gracefully without overflowing column borders or shrinking entire tables into illegibility.

**Why this priority**: Wide tokens currently risk bursting beyond cell boundaries or causing arbitrary global compression of all columns, degrading visual document quality.

**Independent Test**: Lay out a table containing long unbroken strings in one column alongside normal text in other columns. Verify columns adapt properly, long strings break cleanly at permitted boundaries or character boundaries when needed, and cell boundaries remain respected.

**Acceptance Scenarios**:

1. **Given** a cell containing a continuous token wider than the assigned column width, **When** text wrapping is performed, **Then** the token is wrapped at appropriate character boundaries or break opportunities rather than overflowing past the cell boundary.
2. **Given** a table with heavy content across multiple columns, **When** column widths are solved, **Then** the system applies reasonable minimum readability constraints before any proportional reduction.
3. **Given** a table narrower than the printable page width, **When** rendered, **Then** the layout honors the configured table width strategy (e.g., natural content fit versus full page-width expansion) without forced artificial distortion.

---

### User Story 5 - High-Fidelity Table Formatting and Structural Diagnostics (Priority: P2)

Users importing DOCX documents need table column alignments, specified widths, and structural metadata preserved where possible, and need informative warnings when complex unsupported structures (like nested tables) are simplified.

**Why this priority**: Preserves document authoring intent and prevents surprise alterations, ensuring users are fully informed of any formatting transformations.

**Independent Test**: Import DOCX documents featuring left/center/right aligned columns, custom column widths, and nested tables. Verify alignment and width retention, and confirm appropriate warning messages appear for nested or unsupported elements.

**Acceptance Scenarios**:

1. **Given** a source table with specific column alignments (left, center, right), **When** imported and rendered, **Then** text within each column respects the source alignment.
2. **Given** a table containing nested tables inside a cell, **When** processed, **Then** nested content is extracted without data loss and an informative user notification is recorded explaining the flattening or simplification.
3. **Given** an import operation completing with warnings or simplified formatting, **When** viewed in the user interface, **Then** a visible summary panel displays all diagnostic messages clearly.

---

### User Story 6 - Interactive Table Creation and Grid Customization (Priority: P3)

Users authoring documents directly in the web application need intuitive controls to insert and configure tables with custom rows, columns, and header configurations rather than being restricted to a fixed 3x3 sample template.

**Why this priority**: Enhances authoring speed and flexibility for non-DOCX web users who need custom grid dimensions for lesson plans, rubrics, and answer keys.

**Independent Test**: Open the web application editor, trigger the table creation tool, specify custom dimensions (e.g. 5 rows, 4 columns with header row), and verify the generated table structure in the editor and preview.

**Acceptance Scenarios**:

1. **Given** the document editor toolbar, **When** a user clicks the table creation control, **Then** a configuration dialog or menu allows specifying the number of rows, columns, and header options.
2. **Given** selected table dimensions, **When** confirmed, **Then** the structured table template is inserted at the cursor position with correct row/column structure.

---

### Edge Cases

- **Chained and Transitive Row Merges**: Row 1-2 merged in Col 1, Row 2-3 merged in Col 2, Row 3-4 merged in Col 3. The entire sequence rows 1–4 must be recognized as a single inseparable row cluster during pagination.
- **Single Row Exceeding Page Height**: A single row containing extensive text or large formulas taller than a blank page's printable area. System must handle this without freezing, inf-looping, or crashing, advancing cleanly with diagnostic notification.
- **Empty Cells and Whitespace-only Cells**: Merged or individual cells with no text or only spaces must still retain correct height, border stroke rendering, and background geometry.
- **Extremely Wide Tables**: Tables with 15+ columns exceeding printable page width. System should notify the user or support landscape / scaling options rather than silently clipping columns outside page margins.
- **Multi-line Rich Inlines with Mixed Content**: A single line having a fraction, plain text, square root, and superscript exponents where baseline heights differ across elements.
- **Large Tables Performance**: Tables with 100+ rows and 10+ columns. Border stroke generation and layout calculations must execute efficiently without noticeable UI lag.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document import system MUST preserve all table structures, rows, columns, and cell contents from imported documents into the intermediate document representation and web editing workspace without omitting table blocks.
- **FR-002**: The web import bridge and editor MUST display import diagnostic notices, warnings, and unsupported feature summaries to the user whenever document structures are simplified or transformed.
- **FR-003**: The table layout engine MUST compute the transitive closure of all merged row groups (`rowspan`) so that any overlapping or chained merged rows form an indivisible page slice unit.
- **FR-004**: The pagination algorithm MUST strictly forbid placing a page break inside any indivisible merged row group unless the group height exceeds the maximum printable height of an entire page.
- **FR-005**: When a row or row group height exceeds the remaining height of the active page, the pagination algorithm MUST advance the entire group to a new page rather than bisecting cells or overlapping existing page elements.
- **FR-006**: When an oversized row group exceeds the total printable height of an entire single page, the layout engine MUST execute a deterministic fallback handling (demarcating continued segments) and generate a diagnostic warning, without causing infinite loops.
- **FR-007**: The line formatting contract for table cells MUST provide comprehensive vertical metrics for each rendered line, including line ascent above baseline, line descent below baseline, total line height, and line width.
- **FR-008**: Cell height and row height calculations MUST be derived from the actual composite vertical spans (sum of ascents and descents plus interline spacing and cell padding) of all constituent lines in all cells of that row.
- **FR-009**: The stroke and content renderer MUST position math formulas and rich inline elements within cell boundaries such that baseline placement and vertical extents maintain a guaranteed clearance from cell borders.
- **FR-10**: The layout engine MUST wrap long continuous tokens and formulas within cell width constraints at allowable breakpoints or character boundaries to prevent content bleeding across column borders.
- **FR-011**: The table layout engine MUST support selectable table width behavior, allowing tables to either size naturally according to content and specified column widths or stretch to fill available page width.
- **FR-012**: The DOCX importer MUST preserve source column alignments (left, center, right) and apply them to the corresponding table columns and cells in the document model.
- **FR-013**: The DOCX importer MUST recursively parse or cleanly extract contents from nested tables, recording an informational notice if nested table structures are flattened into parent cells.
- **FR-014**: The table border stroke generator MUST utilize optimized lookup structures (such as cell occupancy matrices and merge-region bounding indices) to ensure efficient boundary evaluation for tables of any size.
- **FR-015**: The web editor MUST provide an interactive table creation interface allowing users to customize rows, columns, and header row configuration.
- **FR-016**: The automated test suite MUST validate table data preservation, transitive merge pagination, formula bounding box containment within cells, and web end-to-end import fidelity using concrete coordinate and content assertions.

### Key Entities

- **Document Intermediate Model (IR)**: The structured representation holding all document elements (paragraphs, headings, tables, formulas) that bridges file import, editing, preview, and export without lossy conversion.
- **Table Node**: Represents a structured tabular grid containing an ordered collection of rows, cells, column definitions, alignment settings, and border styles.
- **Table Cell**: An individual grid cell defined by column index, row index, horizontal span (`colspan`), vertical span (`rowspan`), and rich block/inline content.
- **Merged Row Group (Closure)**: A set of consecutive table rows bound together directly or transitively by one or more multi-row cell spans (`rowspan`), forming an atomic pagination unit.
- **Line Vertical Metrics**: Precise measurement data for a formatted line inside a cell, consisting of ascent (distance above baseline), descent (distance below baseline), line height, and line width.
- **Page Table Slice**: The subset of table rows assigned to a specific document page, along with boundary stroke definitions indicating closed or continued table borders.
- **Import Diagnostic Notice**: A structured warning or informative message emitted during document parsing that details unsupported attributes, flattened hierarchies, or formatting adjustments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tables present in imported test DOCX documents are preserved in the web editor and exported files with all text and numeric cell values intact (0% silent table drop rate).
- **SC-002**: 100% of multi-page test tables with complex, transitive merged rows are paginated cleanly without any cell split across a page boundary or missing border strokes.
- **SC-003**: 0% border collision rate: All math formulas and rich inline expressions in test tables maintain a minimum clearance of at least 1 mm (or equivalent configured padding) from cell borders, with zero stroke clipping.
- **SC-004**: Zero text overflow: In 100% of tested narrow-column scenarios containing long unbroken tokens or formulas, all rendered content remains fully contained within column boundaries.
- **SC-005**: 100% of document imports involving unsupported or simplified formatting generate user-visible diagnostic notices detailing the modifications.
- **SC-006**: Table border stroke generation for a 100-row by 20-column table executes in under 50 milliseconds, eliminating UI stutter during rendering.

## Assumptions

- Users importing documents expect text and tabular data preservation as the primary priority over pixel-perfect matching of proprietary Word styling.
- When an imported DOCX table contains nested tables inside cells, flattening nested cell text into the parent cell with clear delimiter spacing and an informational warning is an acceptable fallback to prevent data loss.
- Markdown remains a convenient editing syntax, but rich document features (tables with multi-row merges, custom alignments) require the internal document representation to be the primary source of truth for rendering and export.
- Standard printable page orientation defaults to portrait, but future or advanced layout configurations can provide landscape orientation when tables require wider printable margins.
- Formula rendering employs standard typographic rules where formula height is dynamically computed from constituent symbols (radicals, fractions, matrices) rather than estimated from font line-height constants.
