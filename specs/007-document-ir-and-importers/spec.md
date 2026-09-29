# Feature Specification: Document IR, Multi-Format Importers (TXT/MD/DOCX), Layout Engine, and Math/Table Rendering

**Feature Branch**: `007-document-ir-and-importers`

**Updated**: 2026-09-29

**Status**: Draft (Iteration 2: Math Glyph Rendering, Rich Table Cells, Colspan/Rowspan, Unified Plaintext IR & End-to-End Streaming)

**Input**: User review of commits `33185d7` and `20ef69c` identifying 13 critical functional gaps:
1. Math formulas missing actual handwriting strokes for variables and digits (`TextNode` in `MathLayoutEngine` only measures size without generating strokes).
2. Inline math experiencing double-scaling when custom scale or headings are applied.
3. Tables lacking `colspan` and `rowspan` support for merged cells from Word and IR.
4. Tables dropping `MathInline`, `Symbol`, and `LineBreak` inside cells (flattening cells to plain text).
5. Table column alignments (`left`, `center`, `right`) ignored during cell stroke rendering.
6. Plaintext files currently bypassing Document IR in CLI/GUI rather than flowing through the unified pipeline.
7. Plaintext importer stripping blank lines, causing paragraph spacing collapse.
8. Streaming `PageBuffer` implemented in isolation but not wired end-to-end into `DocumentLayoutEngine.render()`.
9. DOCX importer silently dropping unsupported OMML structures (matrix, nary, limits, accents) without reporting them.
10. Ambiguity between non-fatal warnings (style simplifications) and unsupported elements (unrendered content).
11. Typo in dependency installation hint (`pip install ".[ docs ]"` vs `pip install ".[docs]"`).
12. `get_importer_for_path()` falling back all unknown extensions (`.pdf`, `.xlsx`, `.jpg`) to plaintext.
13. Need for comprehensive end-to-end regression tests covering the 12 functional areas above.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Math AST Glyph Generation & Single-Scale Text Alignment (Priority: P0) ⭐ CRITICAL

As a student or math learner, I want mathematical formulas (equations like $x^2 + y^2 = 10$ or fractions like $\frac{-b}{2a}$) to render actual handwritten pen strokes for every letter variable and number digit, and inline math expressions to align typographically within sentences without being enlarged twice when font scaling is changed, so that formulas are complete, readable, and accurately proportioned.

**Why this priority**: Currently, `TextNode` in the math layout engine only computes bounding dimensions without generating strokes from the bank. Formulas display fraction lines and radical symbols, but variables ($x, y$) and numbers ($10$) disappear completely. Furthermore, inline math is scaled once in `MathLayoutEngine` and then scaled a second time in text line rendering, causing distorted sizes whenever `--scale != 1.0` or inside headings.

**Independent Test**:
- Create a math expression with variables and numbers (e.g. `x^2 + y^2 = 10`), layout and render it, and assert that the resulting stroke collection contains non-zero pen strokes for $x$, $y$, $1$, and $0$.
- Place an inline math expression `$a + b = c$` inside a paragraph with `--scale 1.5`, assert that the glyph heights of the math expression match the height of surrounding normal text (ratio $\approx 1.0$, not $1.5$).

**Acceptance Scenarios**:
1. **Given** a mathematical expression containing alphabetic variables and digits (`TextNode`), **When** rendered by `MathLayoutEngine` / `MathGlyphRenderer`, **Then** the engine retrieves stroke data from `Writer` / `Bank` for each character and positions them along the formula's baseline.
2. **Given** an inline math expression inside a paragraph or heading, **When** rendered by `DocumentLayoutEngine`, **Then** the math strokes are placed into the line's coordinate space with single scaling, matching the effective line height and scale of surrounding text.
3. **Given** a math token referencing a character not present in the bank, **When** rendered, **Then** the layout allocates a sized placeholder box (`[ char ]`) and records the token in `missing_tokens` or `missing_symbols`.

---

### User Story 2 - Rich Table Cells with Math, Symbols & Column Alignment (Priority: P1)

As a technical note taker, I want table cells to contain mathematical formulas (`MathInline`), special symbols (`Symbol`), and manual line breaks (`LineBreak`), and for text within columns to align to the left, center, or right according to document specifications, so that complex data and calculation tables are fully legible.

**Why this priority**: `TableLayoutEngine` currently flattens cell contents by extracting only `Text` inline strings and discarding `MathInline` and `Symbol`. Furthermore, column alignment metadata (`left`, `center`, `right`) read from Markdown or IR is currently ignored, forcing all cell content to align to the top-left corner.

**Independent Test**:
- Create a table where column 1 is left-aligned text and column 2 is right-aligned with inline math (e.g. `$\pi r^2$`), render to `.xopp`, and assert that math strokes for $\pi$ and $r^2$ are present inside column 2's bounding box with horizontal offset reflecting right alignment.

**Acceptance Scenarios**:
1. **Given** a table cell containing `MathInline` or `Symbol` elements, **When** measured and laid out, **Then** the cell layout uses the unified inline layout engine to position both text and math glyphs within the cell width.
2. **Given** a table with column alignments `left`, `center`, and `right`, **When** rendered, **Then** each cell's text lines and math strokes are positioned with corresponding horizontal offsets inside the cell borders.
3. **Given** a table cell containing `LineBreak`, **When** laid out, **Then** the text splits onto a new line within the cell at the exact break point.

---

### User Story 3 - Table Merged Cells Support (`colspan` and `rowspan`) (Priority: P1)

As a user importing tables from Word documents or structured notes, I want cells that span multiple columns (`colspan > 1`) or multiple rows (`rowspan > 1`) to be measured across their combined width and height, and for interior grid lines within the merged region to be omitted, so that complex merged tables render cleanly without overlapping lines.

**Why this priority**: Word documents frequently use merged header cells or grouped row categories. Currently, `colspan` and `rowspan` exist in the IR dataclass but are ignored by `TableLayoutEngine` and `DocxImporter`, causing merged cells to render with interior border lines crossing through the text.

**Independent Test**:
- Import a Word document or construct a Table IR with a header cell having `colspan=2`, assert that column widths are combined for that cell and that the vertical border stroke between columns 1 and 2 is suppressed for that row.

**Acceptance Scenarios**:
1. **Given** a `.docx` file containing merged cells (`w:gridSpan` for horizontal merge or `w:vMerge` for vertical merge), **When** imported via `DocxImporter`, **Then** the resulting `TableCell` nodes are populated with accurate `colspan` and `rowspan` values.
2. **Given** a table with a cell having `colspan = K`, **When** laid out, **Then** the cell width equals the sum of the $K$ spanned column widths, and cell text wraps based on the total merged width.
3. **Given** a table with merged cells, **When** vector borders are rendered, **Then** no horizontal or vertical dividing lines are drawn inside the merged rectangular area.

---

### User Story 4 - Unified Plaintext Document IR Pipeline & Blank Line Preservation (Priority: P1)

As a CLI and GUI user, I want plain text files (`.txt`) to be imported through `TxtImporter` into `Document` IR and laid out by `DocumentLayoutEngine`, while preserving empty lines as paragraph spacing, so that text files benefit from the modern document pipeline while keeping distinct paragraphs separated.

**Why this priority**: CLI `write` and GUI currently route `.txt` files directly to the legacy `composer.py` rather than through Document IR. Additionally, `TxtImporter` currently strips blank lines, causing multiple paragraphs to collapse into one monolithic block.

**Independent Test**:
- Import a `.txt` file with two paragraphs separated by an empty line via `TxtImporter`, assert that the Document IR contains two distinct `Paragraph` blocks with vertical spacing, and assert that `ctl.write_text(...)` legacy API remains 100% byte-for-byte SHA-256 identical to golden-master benchmarks.

**Acceptance Scenarios**:
1. **Given** a plain text file with blank lines between paragraphs, **When** imported via `TxtImporter`, **Then** distinct `Paragraph` blocks are created and rendered with vertical paragraph separation matching standard typographic formatting.
2. **Given** the CLI command `hw-note write note.txt -o out.xopp`, **When** executed with `--format auto` or `--format txt`, **Then** the document is processed through `TxtImporter -> Document IR -> DocumentLayoutEngine`.
3. **Given** direct calls to `ctl.write_text(text, opts, path)`, **When** tested against `tests/test_golden_master.py`, **Then** SHA-256 hashes match legacy benchmarks byte-for-byte without deviation.

---

### User Story 5 - DOCX Advanced OMML Diagnostics & Transparent Warning Categorization (Priority: P2)

As an academic or office user importing Word documents, I want the importer to distinguish between non-fatal formatting warnings (such as unsupported text colors or font styles) and unsupported elements (such as images, drawings, SmartArt, and advanced OMML equations like matrices or limit notations), explicitly logging the exact unsupported construct names in `ImportResult.unsupported`, so that formulas never vanish silently without notice.

**Why this priority**: Currently, unrecognized OMML tags are skipped silently during child traversal without adding to `ImportResult.unsupported`. If a user imports a Word document with a matrix or limit notation, part of the equation vanishes without an error message.

**Independent Test**:
- Import a `.docx` containing an unsupported OMML matrix (`m:m`) or n-ary operator (`m:nary`), assert that import succeeds without crashing and that `ImportResult.unsupported` contains `"OMML: matrix"` or `"OMML: nary"`.

**Acceptance Scenarios**:
1. **Given** a `.docx` file with unsupported OMML structures (`m:m`, `m:nary`, `m:limLow`, `m:limUpp`, `m:func`, `m:bar`, `m:acc`, `m:groupChr`, `m:eqArr`), **When** imported, **Then** the importer logs the specific structure name under `ImportResult.unsupported` while parsing surrounding supported text and equations.
2. **Given** minor formatting simplifications (e.g. bold/italic formatting rendered as standard handwriting), **When** encountered, **Then** the importer records an informational message under `ImportResult.warnings` rather than `unsupported`.

---

### User Story 6 - End-to-End Streaming Pagination, Strict Format Rejection & UX Polish (Priority: P2)

As a user processing long documents or running CLI commands, I want large documents (50+ pages) to stream pages to disk via `PageBuffer` during layout rather than accumulating hundreds of megabytes of XML in memory; I want the importer to immediately reject unsupported file formats (`.pdf`, `.xlsx`, `.zip`) with an explicit error instead of decoding binary as corrupted text; and I want dependency installation hints to display copy-pasteable commands without extra spaces.

**Why this priority**: `PageBuffer` currently exists as an isolated class but is not used in `DocumentLayoutEngine.render()`. Furthermore, `get_importer_for_path()` defaults any unknown extension to `TxtImporter`, leading to binary decoding errors on PDFs or images. A typo in `dependency.py` (`.[ docs ]`) also causes copy-pasted `pip install` commands to fail.

**Independent Test**:
- Pass a multi-page document to `DocumentLayoutEngine.render()`, assert that pages are emitted via `PageBuffer` and verified in `.xopp` output.
- Call `get_importer_for_path("document.pdf")`, assert that `UnsupportedFormatError` is raised with a list of supported extensions (`.txt`, `.md`, `.docx`).
- Trigger `OptionalDependencyError`, assert that the instruction string contains exact `pip install ".[docs]"` without internal spaces.

**Acceptance Scenarios**:
1. **Given** a multi-page document rendered by `DocumentLayoutEngine`, **When** pages are finalized, **Then** each page is emitted to disk via `PageBuffer` to maintain constant memory consumption.
2. **Given** a file path with an unknown extension (e.g. `.pdf`, `.xlsx`, `.jpg`), **When** passed to `get_importer_for_path(path, fmt="auto")`, **Then** the system raises `UnsupportedFormatError` specifying valid document formats.
3. **Given** missing optional dependencies when attempting to import `.md` or `.docx`, **When** `OptionalDependencyError` is raised, **Then** the error message provides the exact command `pip install ".[docs]"`.

---

## Edge Cases

- **What happens when a formula contains a multi-character identifier (e.g. `x_1` or `\sin(x)`)?**
  Multi-character tokens inside `TextNode` (e.g. `10` or `abc`) are broken down into individual characters or tokens and positioned sequentially along the horizontal baseline, querying the bank for each character's stroke data.
- **What happens when custom scaling (`--scale 1.5`) or heading scale (`1.35x`) is applied to inline math?**
  The inline math layout engine receives the exact font scale once and computes all glyph coordinates and stroke line widths relative to that single scale; the text line renderer places the resulting strokes into the page without applying an additional scale multiplication.
- **What happens when a merged table cell spans across page boundaries?**
  If a row containing a vertically merged cell (`rowspan > 1`) exceeds the remaining page height, the table paginates at the start of that merged row group to avoid splitting a vertically merged cell across pages.
- **What happens when a table cell contains both multiline text and an inline formula?**
  The cell wraps text and inline math across lines using the inline layout engine, adjusting the row height to fit the tallest cell in that row.
- **What happens when a plain text document has multiple consecutive blank lines?**
  Consecutive blank lines are collapsed into a single vertical paragraph spacing unit (1.5x line height) to prevent excessive empty vertical gaps on the page.
- **What happens if a user provides an unknown file format via CLI or GUI (e.g. `report.pdf`)?**
  The CLI displays `Lỗi định dạng: Chỉ hỗ trợ các tệp .txt, .md, .docx (nhận được: .pdf)` and exits with code 1. The GUI displays an alert dialog and leaves the text area unchanged.
- **What happens when a Word document contains deeply nested or unsupported OMML structures?**
  Supported outer elements (e.g. a fraction enclosing a matrix) are rendered up to the unsupported node; the unsupported node is replaced with a placeholder bracket (`[ OMML: matrix ]`) and reported in `ImportResult.unsupported`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a unified `Document` Intermediate Representation (IR) consisting of block nodes (`Paragraph`, `Heading`, `ListBlock`, `Table`, `MathBlock`, `PageBreak`) and inline nodes (`Text`, `MathInline`, `Symbol`, `LineBreak`).
- **FR-002**: The system MUST implement an extensible `Importer` interface with concrete implementations for plaintext (`TxtImporter`), Markdown (`MarkdownImporter`), and Word documents (`DocxImporter`).
- **FR-003**: `TxtImporter` MUST parse plain text files and raw strings into `Document` IR preserving blank lines as paragraph breaks, without modifying or breaking legacy `ctl.write_text(...)` golden-master regression tests.
- **FR-004**: The system MUST provide a `ctl.write_document(document, options, output_path)` controller API that accepts a `Document` IR and coordinates layout, pagination, and handwriting stroke generation.
- **FR-005**: `MarkdownImporter` MUST parse headings (levels 1–6), paragraphs, ordered/unordered lists, GFM tables, inline math (`$...$`), and block math (`$$...$$`).
- **FR-006**: `MarkdownImporter` MUST explicitly disable and sanitize raw HTML parsing to prevent untrusted script injection or DOM vulnerabilities in the desktop application.
- **FR-007**: `DocxImporter` MUST parse Word documents using sequential content iteration (`iter_inner_content()`) to preserve the exact interleaving order of paragraphs and tables.
- **FR-008**: `DocxImporter` MUST parse Office Math Markup Language (OMML) XML trees (`m:oMath`, `m:f`, `m:sSup`, `m:sSub`, `m:rad`, `m:d`) and convert them into the unified `MathNode` AST.
- **FR-009**: The system MUST return an `ImportResult` dataclass containing the parsed `Document`, list of format warnings (`warnings`), and list of unrenderable features (`unsupported`).
- **FR-010**: The layout engine MUST compute table column widths, wrap multiline cell text, and render table borders as pen strokes supporting at least four border modes: `NONE`, `OUTER`, `ALL`, and `HORIZONTAL`.
- **FR-011**: The math layout engine MUST compute width, height, ascent, descent, and baseline offsets for mathematical AST nodes (fractions, exponents, indices, roots, operators).
- **FR-012**: The bank schema MUST be incremented to version 3, adding a top-level `"symbols": {}` dictionary for mathematical glyphs and special symbols, while automatically migrating schema v2 banks without data loss.
- **FR-013**: When a word, digit, or symbol is missing from the bank, the layout engine MUST assign a non-zero bounding box with valid baseline metrics to prevent layout collapse.
- **FR-014**: The GUI `WriteTab` MUST support file filters for `.txt`, `.md`, `.markdown`, and `.docx`, and display structural summary metrics and missing symbol counts.
- **FR-015**: The CLI `write` command MUST support file extension auto-detection (`--format auto`) and route supported file types through the Document IR pipeline.
- **FR-016**: Core handwriting features MUST remain zero-dependency (`dependencies = []`), with document parsers (`python-docx`, `markdown-it-py`, `mdit-py-plugins`) declared as optional extras (`[project.optional-dependencies] docs = [...]`).
- **FR-017**: The math rendering engine MUST generate actual handwriting strokes for `TextNode` (alphabetic variables and numbers) by querying `Writer` / `Bank`, rather than emitting empty dimension boxes.
- **FR-018**: The system MUST render inline math formulas within text lines using a unified typographic coordinate system, guaranteeing that `MathInline` glyphs and lines are scaled exactly once by the effective font scale without double-scaling.
- **FR-019**: The table layout engine MUST render cell blocks using the inline layout engine, preserving `MathInline`, `Symbol`, and `LineBreak` elements inside table cells.
- **FR-020**: The table layout engine MUST support horizontal `colspan` and vertical `rowspan`, allocating column widths and row heights across merged spans and suppressing interior border strokes inside merged cells.
- **FR-021**: The table layout engine MUST position cell content according to `col_alignments` (`left`, `center`, `right`).
- **FR-022**: The CLI and GUI file loading workflows MUST route `.txt` files through `TxtImporter` and the Document IR layout engine, preserving empty lines as paragraph spacing.
- **FR-023**: `get_importer_for_path()` MUST strictly accept only supported extensions (`.txt`, `.md`, `.markdown`, `.docx`), raising an explicit `UnsupportedFormatError` for unknown extensions.
- **FR-024**: `DocxImporter` MUST detect and log unsupported OMML elements (matrix, nary, limLow, limUpp, func, bar, acc, groupChr, eqArr) into `ImportResult.unsupported`.
- **FR-025**: `DocumentLayoutEngine.render()` MUST write completed pages sequentially through `PageBuffer` during layout for multi-page documents.
- **FR-026**: `OptionalDependencyError` and documentation MUST display valid, copy-pasteable installation syntax (`pip install ".[docs]"`).

---

### Key Entities

- **Document**: The root of the Document IR, holding an ordered list of `Block` elements and document-level metadata.
- **Block**: Base entity for block-level elements: `Paragraph`, `Heading` (with level), `ListBlock` (ordered/unordered with items), `Table`, `MathBlock`, and `PageBreak`.
- **Inline**: Base entity for inline elements: `Text`, `MathInline`, `Symbol`, and `LineBreak`.
- **TableCell**: Table cell entity supporting `colspan` (horizontal span) and `rowspan` (vertical span) containing a list of `Block` elements.
- **Table**: Block entity containing rows and cells, with border style (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`), cell padding, and column alignment array (`col_alignments`).
- **MathNode**: AST entity for mathematical expressions: `Fraction`, `Superscript`, `Subscript`, `SubSuperscript`, `Root`, `SymbolNode`, `TextNode`, and `MathRow`.
- **MathGlyphRenderer**: Subsystem that renders strokes for math AST nodes (`TextNode` via `Writer`, `SymbolNode` via `Bank.symbols`, fraction bars and radicals via vector strokes).
- **PageBuffer**: Streaming buffer emitting completed XOPP page XML directly to a gzip file on disk.
- **ImportResult**: Data entity bundling the parsed `Document`, list of non-blocking formatting warnings (`warnings`), and list of unrenderable features (`unsupported`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% pass rate on all existing regression and golden-master tests (`test_golden_master.py`), guaranteeing zero regression for legacy `.txt` generation.
- **SC-002**: Markdown importer successfully parses 100% of standard GFM table and LaTeX math syntax samples in test fixtures without unhandled exceptions.
- **SC-003**: DOCX importer preserves 100% of paragraph and table sequencing in test documents as verified against document structure assertions.
- **SC-004**: Table layout produces properly bounded cell strokes with 0 text overlaps across columns for any table fitting within standard page margins.
- **SC-005**: Math layout accurately positions fractions, radicals, and exponents with correct baseline alignment, maintaining readable vertical separation.
- **SC-006**: Missing glyphs (words or symbols) do not cause formula distortion or table column misalignments; layout preserves reserved bounding dimensions.
- **SC-007**: Core application runs without external package dependencies; document parsing features gracefully prompt when optional dependencies are absent.
- **SC-008**: Large multi-page documents (up to 50 pages) process with streaming memory management via `PageBuffer`, maintaining interactive responsiveness.
- **SC-009**: Math formulas containing algebraic variables and numbers (e.g. $x^2 + y^2 = 10$) generate non-zero stroke counts for 100% of variables and digits present in the bank.
- **SC-010**: Inline math formulas rendered at scale $\ne 1.0$ or inside headings maintain proportional font size matching surrounding text without quadratic double-scaling.
- **SC-011**: Tables containing merged cells (`colspan` / `rowspan`) render with correct column widths and 0 intersecting grid lines through merged cell regions.
- **SC-012**: Tables containing math expressions (`$E = mc^2$`) render math strokes inside cell boundaries with proper alignment.
- **SC-013**: Unsupported file formats (e.g. `.pdf`, `.zip`) are rejected with `UnsupportedFormatError` without corrupting memory or decoding binary as text.

---

## Assumptions

- Python 3.10+ remains the target runtime across Windows and Linux platforms.
- `markdown-it-py` and `mdit-py-plugins` will be used for Markdown AST tokenization when installed.
- `python-docx` will be used for Word document and OMML extraction when installed.
- Math rendering in MVP focuses on common school and university mathematics: arithmetic, algebra, calculus basics (`\frac`, `^`, `_`, `\sqrt`, `\sum`, `\int`, `\prod`, Greek letters, standard relation symbols). Advanced LaTeX macro programming is out of scope.
- Standalone PyInstaller releases will bundle the optional `docs` dependencies so end users do not need to manage Python packages.
