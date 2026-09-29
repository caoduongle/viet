# Feature Specification: Document IR, Multi-Format Importers (TXT/MD/DOCX), Layout Engine, and Math/Table Rendering

**Feature Branch**: `007-document-ir-and-importers`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User architectural review and design proposal for extending the handwriting input pipeline:
- Replacing the flat `str -> normalize_text -> split("\n") -> split(" ") -> Writer.token() -> composer` pipeline with a decoupled `Importer -> Document IR -> Layout Engine -> Handwriting Renderer` architecture.
- Preserving full backward compatibility for `.txt` input and the `ctl.write_text(...)` API to protect golden-master tests and existing workflows.
- Adding native importers for Markdown (`.md`, `.markdown`) via `markdown-it-py` (with GFM tables and math syntax, raw HTML disabled for security) and Microsoft Word (`.docx`) via `python-docx` (`iter_inner_content()` order and OMML math XML extraction).
- Decoupling `composer.py` into dedicated document layout, table layout, math layout (with width, height, ascent, descent, and baseline metrics), and pagination modules with streaming buffer support for large documents.
- Elevating tables into a first-class IR and layout entity rendered as crisp stroke borders (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`) with cell wrapping and column sizing.
- Introducing Schema v3 to support a dedicated `"symbols"` category in the bank dictionary while maintaining compatibility with v2 banks, separating Level 1 symbols (`≤`, `∑`, `π`) from Level 2 structured math ASTs (`Fraction`, `Superscript`, `Subscript`, `Root`), and using dimensioned placeholders for missing glyphs to prevent layout collapse.
- Upgrading GUI ("Mở tài liệu...", structural diagnostics, missing symbol reporting) and CLI (extension auto-detection `--format auto`).
- Maintaining zero external dependencies for core handwriting (`dependencies = []`), placing document parsers under optional dependencies (`[project.optional-dependencies] docs = [...]`).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Document Intermediate Representation (IR), Plaintext Importer & Backward-Compatible Pipeline (Priority: P1) ⭐ MVP

As an application developer and end user, I want the system to represent text documents as structured elements (Document, Paragraph, Heading, PageBreak, Inline Text) via a clean Document IR, and import `.txt` files through a dedicated importer, so that existing text generation behaves identically while opening the architecture for structured document formats.

**Why this priority**: The existing pipeline directly tokenizes raw strings with whitespace splitting inside `composer.py`, making structured formatting (tables, headings, math) impossible without breaking core text generation. Introducing the Document IR and `TxtImporter` while preserving `ctl.write_text(...)` establishes the unified foundation without risking regression on existing workflows.

**Independent Test**: Can be fully tested by running `TxtImporter` on existing sample texts, asserting that `ctl.write_text(...)` produces byte-identical output to legacy golden-master files (`tests/test_golden_master.py`), and asserting that `ctl.write_document(...)` renders matching handwriting pages.

**Acceptance Scenarios**:
1. **Given** a plain text file (`.txt`) or string input, **When** imported via `TxtImporter`, **Then** a `Document` IR is produced consisting of `Paragraph` blocks and `Text` inline nodes with normalized line breaks.
2. **Given** an existing text generation request via `ctl.write_text("Xin chào", options, "out.xopp")`, **When** executed, **Then** it delegates to the legacy path or equivalent IR path and generates `.xopp` documents that match golden-master SHA-256 hashes byte-for-byte.
3. **Given** a `Document` IR, **When** passed to `ctl.write_document(document, options, "out.xopp")`, **Then** it paginates and renders lines into `.xopp` format matching the configured pen options and line margins.

---

### User Story 2 - Markdown Document Import with GFM Tables and Math Blocks (Priority: P1)

As a student or technical writer, I want to import `.md` and `.markdown` files containing headings, paragraphs, bullet/numbered lists, GitHub Flavored Markdown (GFM) tables, and LaTeX-style math expressions (`$...$` and `$$...$$`) into the handwriting pipeline, so that formatted notes are converted into handwriting with their document hierarchy preserved.

**Why this priority**: Markdown is the primary lightweight markup language used by developers, researchers, and students. Supporting GFM tables and math syntax directly fulfills the core need for importing structured technical notes into Xournal++.

**Independent Test**: Can be fully tested by importing a Markdown document containing headings, lists, tables, and math blocks, and verifying that `MarkdownImporter` creates the corresponding `Heading`, `Paragraph`, `ListBlock`, `Table`, and `MathBlock` IR nodes with 0 raw HTML execution.

**Acceptance Scenarios**:
1. **Given** a Markdown file with headings `#` through `######`, **When** imported, **Then** `Heading` nodes are created with appropriate hierarchy levels (1 to 6) and inline text formatting.
2. **Given** a Markdown file with GFM table syntax (`| Col 1 | Col 2 |`), **When** imported, **Then** a `Table` IR node is generated with rows, cells, and column alignment metadata.
3. **Given** a Markdown file containing math expressions (`$x^2$` or `$$\frac{a}{b}$$`), **When** imported, **Then** `MathInline` and `MathBlock` nodes are constructed containing the raw LaTeX mathematical expressions.
4. **Given** a Markdown file containing raw HTML tags (`<script>`, `<div style="...">`), **When** imported, **Then** the parser ignores or sanitizes the HTML tags without executing scripts or injecting untrusted content into the document tree.

---

### User Story 3 - Layout Engine Decoupling, Table Sizing & Multi-Border Stroke Rendering (Priority: P2)

As a user writing documents with data tables, I want tables to automatically compute column widths and row heights, wrap cell content, and render crisp grid borders (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`) as distinct pen strokes, so that tabular information is clearly formatted in the handwriting document.

**Why this priority**: Tables currently cannot be represented or rendered by the flat line composer. Decoupling the layout engine from `composer.py` enables proper measurement, cell padding, column proportioning, and stroke rendering without cluttering word-level handwriting logic.

**Independent Test**: Can be fully tested by creating a `Table` IR with varying cell text lengths, running the table layout engine, and verifying that column widths adapt to content, text wraps within cell boundaries, and output `.xopp` contains both grid border strokes and aligned cell handwriting strokes.

**Acceptance Scenarios**:
1. **Given** a `Table` IR node with $N$ columns and $M$ rows, **When** processed by the layout engine, **Then** column widths are calculated based on cell content length up to the maximum available page width.
2. **Given** a table cell whose content exceeds the allocated column width, **When** measured, **Then** the text within the cell wraps onto multiple lines, expanding the row's height proportionally.
3. **Given** a table with border style `ALL`, `OUTER`, or `HORIZONTAL`, **When** rendered to `.xopp`, **Then** clean horizontal and vertical line strokes are drawn using configured pen properties, framing the handwriting contents of each cell.
4. **Given** a long table that exceeds the remaining space on the current page, **When** paginated, **Then** the table splits cleanly across pages at row boundaries without truncating cell contents.

---

### User Story 4 - Math Symbol Schema v3, Inline/Block Math AST & Baseline-Aligned Layout (Priority: P2)

As a math or science learner, I want mathematical formulas (fractions, powers, indices, roots, Greek letters, operators) to be parsed into an expression AST and rendered with proper vertical alignment (ascent, descent, baseline), and mathematical symbols stored in bank schema v3, so that formulas look natural, legible, and do not break document layout when glyphs are missing.

**Why this priority**: Mathematical expressions cannot be rendered by simple linear token concatenation; subscripts, superscripts, fractions, and square roots require 2D positioning relative to a shared typographic baseline. Storing symbols in bank schema v3 ensures individual glyphs (`∑`, `≤`, `π`) are cleanly managed without polluting word dictionaries.

**Independent Test**: Can be fully tested by parsing expressions such as `\frac{-b \pm \sqrt{b^2-4ac}}{2a}` into a math AST, computing their typographic bounding boxes (`width`, `height`, `ascent`, `descent`), and verifying that missing symbols render with sized placeholders (`[ ∑ ]`) that preserve layout geometry.

**Acceptance Scenarios**:
1. **Given** an existing bank file with schema version 2, **When** loaded, **Then** it automatically recognizes and migrates the bank to schema v3 by initializing the `"symbols": {}` dictionary without corrupting existing words, digits, or puncts.
2. **Given** mathematical notation with superscripts (`x^2`), subscripts (`x_i`), fractions (`\frac{a}{b}`), or square roots (`\sqrt{x}`), **When** parsed, **Then** a hierarchical `MathNode` AST is constructed representing the nested mathematical structure.
3. **Given** a `MathNode` AST, **When** laid out, **Then** each sub-element computes its dimensions and baseline offset such that numerator, denominator, fraction bar, roots, and exponents align typographically.
4. **Given** a formula referencing a symbol not yet taught in the bank (e.g. `∑`), **When** rendered, **Then** the layout engine reserves the glyph's bounding dimensions using a placeholder bracket (`[ ∑ ]`) so surrounding characters and fraction bars remain properly aligned.

---

### User Story 5 - DOCX Document Importer with OMML Formula Translation & Unsupported Content Diagnostics (Priority: P3)

As a user working with Microsoft Word documents, I want to import `.docx` files preserving paragraph order, headings, tables, and Word math equations (OMML), while receiving an explicit summary of any unsupported elements (images, SmartArt), so that complex assignments can be written by hand without silent omissions.

**Why this priority**: `.docx` is the most common document interchange format in academic and office settings. Supporting `.docx` import with explicit diagnostics allows users to convert actual homework assignments and reports directly into handwriting.

**Independent Test**: Can be fully tested by importing a sample `.docx` containing text, a table, an OMML equation, and an embedded image, verifying that text, tables, and equations are preserved in the `Document` IR, while the image is reported under `ImportResult.unsupported`.

**Acceptance Scenarios**:
1. **Given** a `.docx` file containing mixed paragraphs and tables, **When** imported via `DocxImporter`, **Then** elements are extracted in their exact document appearance order using `iter_inner_content()`.
2. **Given** a `.docx` file containing Office Math Markup (`m:oMath`), **When** parsed, **Then** fractions (`m:f`), superscripts (`m:sSup`), subscripts (`m:sSub`), and radicals (`m:rad`) are converted to the unified `MathBlock` / `MathInline` AST.
3. **Given** a `.docx` file containing unsupported elements (embedded images, charts, SmartArt, comments), **When** imported, **Then** `ImportResult` lists these elements under `unsupported` warnings without halting import execution or crashing the application.

---

### User Story 6 - Document-Centric GUI & Smart CLI Workflow (Priority: P3)

As an interactive desktop and command-line user, I want WriteTab to provide a "Mở tài liệu..." action supporting all document types with structural summaries (counts of paragraphs, headings, tables, math blocks, and missing symbols), and the CLI to auto-detect input formats from file extensions, so that document generation is intuitive and transparent across both interfaces.

**Why this priority**: Users need visual feedback on what was parsed from complex documents before generating hundreds of handwritten strokes. Clear reporting of missing symbols enables targeted practice in the "Dạy từ mới" tab.

**Independent Test**: Can be fully tested by selecting a `.md` or `.docx` file in the GUI file picker, asserting that the status panel updates with structural metrics, and executing CLI `python hw_note.py write baitap.docx -o ra.xopp` with `--format auto`.

**Acceptance Scenarios**:
1. **Given** the GUI WriteTab, **When** the user clicks "Mở tài liệu...", **Then** the file picker filters for `.txt`, `.md`, `.markdown`, `.docx`, and `*.*`.
2. **Given** a parsed document in WriteTab, **When** loaded, **Then** the interface displays an informational summary (e.g., "12 đoạn, 2 tiêu đề, 1 bảng, 3 công thức") and lists any missing words and missing symbols separately.
3. **Given** the CLI command `python hw_note.py write <input> -o <output>`, **When** run with `--format auto` (default), **Then** the CLI automatically selects `TxtImporter`, `MarkdownImporter`, or `DocxImporter` based on the file extension.
4. **Given** missing symbols detected during document generation, **When** reported in GUI or CLI, **Then** the user is informed with the exact count and list of missing glyphs (e.g., `Ký hiệu: ∑ (x3), ≤ (x1)`).

---

## Edge Cases

- **What happens when an imported document contains empty paragraphs or trailing blank lines?**
  Empty paragraphs are preserved as vertical paragraph spacing blocks or stripped if redundant, matching standard typographic behavior. If a document is completely empty, the layout engine emits a single blank page with empty layer to preserve valid `.xopp` document structure.
- **What happens if an imported Markdown file has an unbalanced table or mismatched column count?**
  The table importer pads incomplete rows with empty cells up to the maximum column count detected across rows. If total minimum column widths exceed available line width, columns scale down uniformly to 0.7x before soft-clipping with an informational warning.
- **What happens if a single table cell contains text taller than the entire page?**
  The table layout engine splits the cell's wrapped text lines across page breaks at the line level rather than hanging in an infinite page-allocation loop.
- **What happens when an OMML or LaTeX formula contains deeply nested fractions or roots?**
  The recursive math layout engine handles arbitrary nesting with a maximum AST depth guard of 10. Inner superscripts/subscripts scale font size down to a clamped minimum readable scale of 0.5x.
- **What happens if the optional `docs` dependencies (`python-docx`, `markdown-it-py`) are not installed and the user attempts to open a `.docx` or `.md` file?**
  The importer catches `ImportError` gracefully and raises `OptionalDependencyError` directing the user to install the document extras (`pip install ".[docs]"`). The GUI displays a user-friendly error dialog without crashing, and CLI exits with code 1. Plain `.txt` import and handwriting rendering continue to work with zero external dependencies.
- **What happens if a document contains a symbol that is not in the bank and cannot be represented?**
  A fallback placeholder box with dimension metrics is rendered (`[ ? ]`), ensuring the surrounding text and math layout remain visually stable. The missing symbol is recorded in `missing_symbols` and exported to `_thieu.xopp` for interactive learning.
- **What happens if a document is exceptionally large (e.g., 50+ pages)?**
  The layout engine paginates incrementally with streaming page buffer generation, avoiding multi-hundred-megabyte in-memory XML string concatenation.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a unified `Document` Intermediate Representation (IR) consisting of block nodes (`Paragraph`, `Heading`, `ListBlock`, `Table`, `MathBlock`, `PageBreak`) and inline nodes (`Text`, `MathInline`, `Symbol`, `LineBreak`).
- **FR-002**: The system MUST implement an extensible `Importer` interface with concrete implementations for plaintext (`TxtImporter`), Markdown (`MarkdownImporter`), and Word documents (`DocxImporter`).
- **FR-003**: `TxtImporter` MUST parse plain text files and raw strings into `Document` IR without modifying or breaking legacy `ctl.write_text(...)` behavior or golden-master regression tests.
- **FR-004**: The system MUST provide a new `ctl.write_document(document, options, output_path)` controller API that accepts a `Document` IR and coordinates layout, pagination, and handwriting stroke generation.
- **FR-005**: `MarkdownImporter` MUST parse headings (levels 1–6), paragraphs, ordered/unordered lists, GFM tables, inline math (`$...$`), and block math (`$$...$$`).
- **FR-006**: `MarkdownImporter` MUST explicitly disable and sanitize raw HTML parsing to prevent untrusted script injection or DOM vulnerabilities in the desktop application.
- **FR-007**: `DocxImporter` MUST parse Word documents using sequential content iteration (`iter_inner_content()`) to preserve the exact interleaving order of paragraphs and tables.
- **FR-008**: `DocxImporter` MUST parse Office Math Markup Language (OMML) XML trees (`m:oMath`, `m:f`, `m:sSup`, `m:sSub`, `m:rad`) and convert them into the unified `MathNode` AST.
- **FR-009**: The system MUST return an `ImportResult` dataclass containing the parsed `Document`, list of warning messages, and list of unsupported document features (images, shapes, SmartArt).
- **FR-010**: The layout engine MUST compute table column widths, wrap multiline cell text, and render table borders as pen strokes supporting at least four border modes: `NONE`, `OUTER`, `ALL`, and `HORIZONTAL`.
- **FR-011**: The math layout engine MUST compute width, height, ascent, descent, and baseline offsets for mathematical AST nodes (fractions, exponents, indices, roots, operators).
- **FR-012**: The bank schema MUST be incremented to version 3, adding a top-level `"symbols": {}` dictionary for mathematical glyphs and special symbols, while automatically migrating schema v2 banks without data loss.
- **FR-013**: When a word, digit, or symbol is missing from the bank, the layout engine MUST assign a non-zero bounding box with valid baseline metrics to prevent layout collapse.
- **FR-014**: The GUI `WriteTab` MUST replace "Mở file .txt..." with "Mở tài liệu...", support file filters for `.txt`, `.md`, `.markdown`, and `.docx`, and display structural summary metrics and missing symbol counts.
- **FR-015**: The CLI `write` command MUST support file extension auto-detection (`--format auto`) and accept `.txt`, `.md`, and `.docx` input files.
- **FR-016**: Core handwriting features MUST remain zero-dependency (`dependencies = []`), with document parsers (`python-docx`, `markdown-it-py`, `mdit-py-plugins`) declared as optional extras (`[project.optional-dependencies] docs = [...]`).

---

### Key Entities

- **Document**: The root of the Document IR, holding an ordered list of `Block` elements and document-level metadata.
- **Block**: Base entity for block-level elements: `Paragraph`, `Heading` (with level), `ListBlock` (ordered/unordered with items), `Table`, `MathBlock`, and `PageBreak`.
- **Inline**: Base entity for inline elements inside paragraphs and headings: `Text` (string content), `MathInline` (mathematical expression), `Symbol` (isolated math/typographic glyph), and `LineBreak`.
- **Table**: Block entity containing rows and cells, with border style (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`), cell padding, column alignment, and row spanning.
- **MathNode**: AST entity for mathematical expressions: `Fraction` (numerator, denominator), `Superscript` (base, exponent), `Subscript` (base, index), `Root` (radicand, degree), `SymbolNode` (glyph identifier), and `MathRow` (linear sequence).
- **Size / TypographicMetrics**: Geometry entity specifying `width`, `height`, `ascent`, `descent`, and `baseline` offsets for text and math layout positioning.
- **ImportResult**: Data entity bundling the parsed `Document`, list of human-readable warnings, and list of unsupported features encountered during parsing.
- **SymbolBank**: Dictionary within Bank Schema v3 mapping symbol strings (e.g., `∑`, `≤`, `π`) to arrays of stroke sample data.

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
- **SC-008**: Large multi-page documents (up to 50 pages) process with streaming memory management, maintaining interactive responsiveness.

---

## Assumptions

- Python 3.10+ remains the target runtime across Windows and Linux platforms.
- `markdown-it-py` and `mdit-py-plugins` will be used for Markdown AST tokenization when installed.
- `python-docx` will be used for Word document and OMML extraction when installed.
- Math rendering in MVP focuses on common school and university mathematics: arithmetic, algebra, calculus basics (`\frac`, `^`, `_`, `\sqrt`, `\sum`, `\int`, `\prod`, Greek letters, standard relation symbols). Advanced LaTeX macro programming is out of scope.
- Standalone PyInstaller releases will bundle the optional `docs` dependencies so end users do not need to manage Python packages.
