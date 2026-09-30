# Feature Specification: Comprehensive Quality, Correctness, and Performance Hardening

**Feature Branch**: `014-core-engine-hardening`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: Comprehensive repository audit across `model/`, `layout/`, `math/`, `document/`, `importer/`, and `fidelity/`, covering verified defects L1–L14, architectural suspicions R1–R10, a phased engineering roadmap (Phases 0–8), and 4 core architectural decisions.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Number & Punctuation Learning & Writing (L1, v2.0.1) (Priority: P1) 🎯 MVP

When a user teaches individual digits (0–9) or punctuation marks (such as commas, periods, parentheses, quotes) via the GUI canvas or batch learning, the system correctly categorizes them into `bank.digits` and `bank.punct`. When generating handwriting for multi-digit numbers (e.g., "2024") and decimal numbers (e.g., "3,5"), the engine uses these digit samples directly, with an automatic fallback to `words` if specific digit samples are missing.

**Why this priority**: Without this fix, newly trained font banks cannot write basic numerical values or decimals, rendering handwriting generation broken for dates, numbers, formulas, and general notes.

**Independent Test**:
- Create a new font bank, train samples for digits `0`–`9` and punctuation `, .`.
- Render the text `"Năm 2024 đạt 3,5 điểm"`.
- Verify that digits and punctuation are drawn from the learned samples and no missing token errors are raised for numbers.

**Acceptance Scenarios**:
1. **Given** a font bank with samples taught for `"2"`, `"0"`, `"4"`, `"3"`, `","`, `"5"`, **When** the user writes `"2024"` and `"3,5"`, **Then** the engine outputs valid handwriting strokes for every digit and symbol without reporting them as missing.
2. **Given** a legacy font bank where digits were stored as whole tokens in `words`, **When** the engine renders numbers, **Then** it seamlessly falls back to `words` without data migration.

---

### User Story 2 - Accurate Missing Token Statistics & Page Buffer Reporting (L2, L3, v2.0.1) (Priority: P1) 🎯 MVP

When running handwriting generation from the CLI or GUI, the output summary accurately reports the actual total number of pages generated (retrieved from the page buffer instead of hardcoded to 1), and correctly tallies missing words and missing symbols without duplicate reporting or negative ratios (e.g., avoids reporting "-2/1").

**Why this priority**: Users and downstream automation scripts rely on accurate run summaries and logs to diagnose font bank completeness and multi-page output integrity.

**Independent Test**:
- Write a 5-page text document with an empty or partially populated font bank.
- Verify that `result.n_pages == 5`.
- Verify that `result.missing` and `result.n_missing_tokens` match the unique missing tokens without negative values or double-counting.

**Acceptance Scenarios**:
1. **Given** a multi-page document that spills across 5 pages, **When** generation completes, **Then** `result.n_pages` equals 5 in both API and CLI output.
2. **Given** an empty bank and the input text `"(Xin,"`, **When** missing tokens are calculated, **Then** the summary displays clean counts (e.g., 1 word missing, 2 punctuation marks missing) without negative ratios.

---

### User Story 3 - Robust Importer Fidelity & Content Preservation (L6, L7, L8, L10, v2.0.1) (Priority: P1) 🎯 MVP

When importing Markdown or DOCX documents, mathematical inequalities (such as `1 < 2 và 3 > 2` or `$a < b$`) are preserved in full without being swallowed by HTML sanitizers. Nested Markdown lists retain their hierarchical structure. Formatting marks, tabs, tracked changes, and fields in DOCX are properly handled, and any genuinely unsupported elements are transparently recorded in `unsupported` rather than silently dropped.

**Why this priority**: Content corruption during import causes silent omission of user text, mathematical equations, and list hierarchies.

**Independent Test**:
- Import a Markdown file containing `"1 < 2 và 3 > 2"`, nested lists, and code blocks.
- Verify the document IR contains the complete text with `<` and `>`, nested list items are properly parented, and code blocks are recorded in `unsupported`.

**Acceptance Scenarios**:
1. **Given** text with mathematical comparison symbols (`<`, `>`), **When** imported from Markdown, **Then** no characters are stripped or converted to empty spaces.
2. **Given** inline bold/italic text followed by punctuation (e.g., `"**chào**,"`), **When** segmented into tokens, **Then** no extraneous whitespace is inserted between `"chào"` and `","`.
3. **Given** a DOCX document with tabs, soft line breaks, and tracked revisions, **When** imported, **Then** all visible text is retained with proper alignment, and omitted fields are listed in `unsupported`.

---

### User Story 4 - Bank Data Integrity, Deduplication & Clean Architecture (L11, L12, L13, R7, R10, v2.0.1) (Priority: P1)

When importing or learning from the same template sheet twice, duplicate samples are prevented via sample signature hashing. When symbols, digits, or punctuation are deleted (`drop_symbol`), tombstones are recorded so they do not resurrect during bank merges. Tone mark quartile trimming is symmetrical. The layout engine does not depend on controller classes, preserving strict MVC layering.

**Why this priority**: Bank corruption, resurrecting deleted symbols, and sample bloat degrade long-term usability. Clean architecture ensures zero test regressions.

**Independent Test**:
- Learn the same `.xopp` grid twice; verify sample count remains 1 per cell.
- Drop a symbol, merge with another bank; verify the dropped symbol does not return.
- Run `test_architecture.py` to verify `layout/engine.py` imports only from `model.composer`.

**Acceptance Scenarios**:
1. **Given** a handwriting sheet already learned, **When** learned again, **Then** sample count does not increase for identical strokes.
2. **Given** a dropped symbol, **When** merged with a peer bank containing the old symbol, **Then** the tombstone ensures the symbol remains deleted.
3. **Given** 11 tone mark samples, **When** trimming outliers, **Then** symmetric trimming applies equally to both lower and upper percentiles.

---

### User Story 5 - Proportional Font & Geometry Scaling Across Layout Elements (L4, L5, R8, R9, v2.1) (Priority: P2)

When the user specifies a font scale (e.g., `--scale 2.0`), line spacing automatically scales proportionally with the font height, preventing line collisions. Inline and block mathematical formulas scale uniformly with body text. Table column widths are calculated from actual handwritten stroke bounding boxes rather than rough character counts, preventing text overflow beyond table cell borders.

**Why this priority**: Changing scale currently causes text to overlap and formulas to appear mismatched in size relative to surrounding words.

**Independent Test**:
- Render text at scale 1.0 and scale 2.0.
- Verify that default line step at scale 2.0 is approximately double the line step at scale 1.0.
- Verify math blocks scale proportionally with adjacent text.

**Acceptance Scenarios**:
1. **Given** a document rendered at scale 2.0, **When** no explicit `--line` height is provided, **Then** the line spacing doubles to match the increased character height.
2. **Given** a table with long Vietnamese words, **When** column widths are computed, **Then** widths are measured from actual stroke bounds and word wrapping or auto-scaling prevents overflow.

---

### User Story 6 - Advanced Mathematical Expression & LaTeX Macro Support (L9, v2.1) (Priority: P2)

The mathematical formula parser handles superscripts (`^`) and subscripts (`_`) at arbitrary nesting depths inside grouping braces `{}` (such as `\frac{x^2}{y}` or `e^{x^2}`). Standard LaTeX macros (such as `\cdot`, `\to`, `\forall`, `\exists`, `\partial`, `\nabla`, `\left`, `\right`, and Greek letters) render to their corresponding mathematical symbols or report missing symbols, rather than emitting the command name as literal plain text.

**Why this priority**: Technical, educational, and STEM documents require robust LaTeX expression handling without syntax leakage into output strokes.

**Independent Test**:
- Parse and render `\frac{x^2}{y}` and `a \cdot b \to c`.
- Verify the syntax tree parses exponents within fractions and renders `\cdot` as a multiplication dot.

**Acceptance Scenarios**:
1. **Given** formula `\frac{x^2}{y}`, **When** parsed, **Then** `x^2` is treated as the numerator with `2` in the superscript position.
2. **Given** an unsupported or unknown LaTeX macro, **When** encountered, **Then** a warning is logged and the symbol is recorded in `missing_symbols`, rather than printing the raw macro name as body text.

---

### User Story 7 - Responsive Bank Persistence & Deferred Saves (L14, v2.1) (Priority: P2)

When a user teaches multiple words in succession, saving the font bank does not freeze the GUI. The persistence layer uses debounced deferred saving (e.g., saving after 2 seconds of inactivity, on tab switch, or on window close) and writes to disk on a background thread with safe locking and atomic replacement.

**Why this priority**: As banks grow to 700–1500 words, writing the entire `json.gz` file on every single word takes 2–7 seconds, creating severe UI lag.

**Independent Test**:
- Teach 10 words in rapid succession in the GUI.
- Verify each word input is instantaneous (<50ms UI response) and changes are safely flushed to disk within 2 seconds of idle time.

**Acceptance Scenarios**:
1. **Given** a large font bank with >1000 words, **When** a new word is saved in the GUI canvas, **Then** the interface responds immediately without blocking.
2. **Given** pending unsaved changes in the debounce buffer, **When** the user closes the application or switches tabs, **Then** all pending changes are synchronously flushed to disk.

---

### User Story 8 - High-Fidelity PDF-Based Document Layout Reconstruction (R1-R6, v2.2 → v3.0) (Priority: P3)

The Fidelity pipeline transitions to a clean PDF-first architecture:
1. DOCX is converted to PDF using available system tools (Microsoft Word or LibreOffice) with unique temporary filenames and safe process management.
2. Text lines, exact spatial bounding boxes, and font sizes are extracted directly from the intermediate PDF using an MIT-licensed PDF parser (`pdfplumber` / `pdfminer.six`).
3. Printed text is cleanly neutralized with white overlay rectangles in the PDF background.
4. Handwriting strokes are placed line-by-line, scaled to true x-height, with accurate multi-page linking.

**Why this priority**: Resolves paragraph-level single-line squeezing (R1), removes dependence on COM run inspection for line layout, and provides cross-platform fidelity rendering on Linux CI with LibreOffice.

**Independent Test**:
- Convert a multi-page DOCX document containing multi-line paragraphs and images using Fidelity Mode.
- Verify handwritten strokes wrap naturally per line matching the original PDF layout.

**Acceptance Scenarios**:
1. **Given** a multi-line paragraph in DOCX, **When** processed in Fidelity Mode, **Then** each line is extracted as a separate spatial bounding box rather than compressed into a single line.
2. **Given** headless Linux environments with LibreOffice installed, **When** converting DOCX in Fidelity Mode, **Then** the PDF is generated and parsed successfully without Word COM.

---

### Edge Cases

- **Empty / Incomplete Digits**: If a bank has only digits `0`–`4` but the text requires `5`, the engine must write `0`–`4` using `digits` and cleanly report `5` in missing tokens, without corrupting the word spacing.
- **Nested Braces in LaTeX**: Formulas with deep nesting (e.g., `a_{i_{j_k}}` or `e^{{x^2}+1}`) must parse correctly up to a recursion depth limit (e.g., 32) without stack overflow.
- **Unexpected Process Termination during Deferred Save**: An atomic temporary file swap (`.tmp` -> `.json.gz`) ensures that power loss or abrupt exit never corrupts the primary bank file.
- **Extreme Scale Ratios**: Extremely small (<0.2) or large (>5.0) scale factors must clamp line height and baseline shifts to prevent infinite loops or negative coordinates.
- **DOCX Tracked Changes & Deletions**: Deletions (`w:delText`) must be ignored, insertions (`w:ins`) must be retained, and field instructions (`w:instrText`) must be suppressed.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Category 1: Digit & Punctuation Pipeline (Phase 1, v2.0.1)
- **FR-001**: System MUST classify learned character labels into distinct bank collections: digits (0–9) into `bank.digits`, standard punctuation marks into `bank.punct`, symbols into `bank.symbols`, and all other lexical tokens into `bank.words`.
- **FR-002**: `Writer.number` MUST first look up individual digit samples in `bank.digits`, and fallback to `bank.words` if not present in `digits`, preserving backward compatibility with legacy banks.
- **FR-003**: The training queue in GUI and CLI MUST include a "Minimal Essentials" set containing digits 0–9, common punctuation marks, and the top 60 frequent Vietnamese words.

#### Category 2: Reporting, Importer & Integrity Correctness (Phase 2, v2.0.1)
- **FR-004**: System MUST calculate missing words and missing symbols through dedicated token deduplication, ensuring missing token ratios never display negative values.
- **FR-005**: Document layout engine MUST populate `WriteResult.n_pages` from the actual number of pages produced in `PageBuffer`.
- **FR-006**: Markdown importer MUST NOT strip mathematical comparison operators (`<`, `>`); HTML tag sanitization MUST be bypassed when raw HTML parsing is disabled.
- **FR-007**: Markdown importer MUST parse nested lists recursively and record unsupported structural blocks (such as unhandled code blocks or horizontal rules) in `Document.unsupported`.
- **FR-008**: Markdown and text importers MUST NOT insert extraneous whitespace between consecutive inline spans when the second span begins with punctuation.
- **FR-009**: DOCX importer MUST iterate run children (`w:t`, `w:tab`, `w:br`), skip `w:instrText` and `w:delText`, preserve content within `w:ins` / `w:sdt` / `w:hyperlink`, and retain paragraph alignment and bullet/numbering styles.
- **FR-010**: Bank sample addition MUST deduplicate identical samples using a stroke signature hash (`_sample_signature`).
- **FR-011**: Deleting symbols, digits, or punctuation (`drop_symbol`, `drop_digit`, `drop_punct`) MUST record tombstones to prevent resurrection during bank merges.
- **FR-012**: Tone mark quartile trimming (`_refresh_tone_marks`) MUST apply symmetric percentile trimming to both upper and lower bounds.
- **FR-013**: `layout/engine.py` MUST NOT import `chuviettay.controller` or any GUI modules, adhering strictly to MVC dependency rules.
- **FR-014**: File readers (`read_xopp`) MUST ensure file descriptors are closed via context managers (`with gzip.open...`), and XML generator MUST escape all pen attributes.

#### Category 3: Proportional Geometry & Layout Scaling (Phase 3, v2.1)
- **FR-015**: Default line height MUST scale proportionally with the configured font scale (`opts.scale`), unless the user explicitly provides `--line`.
- **FR-016**: Mathematical formulas (inline and block) MUST scale in unison with surrounding body text scale factors.
- **FR-017**: Table column widths MUST be measured from actual handwritten stroke bounding boxes, and cells exceeding column boundaries MUST auto-wrap or scale down.
- **FR-018**: Table border strokes MUST include controlled jitter matching `opts.jitter` and remain deterministic for a given `opts.seed`.

#### Category 4: Mathematical Parser & LaTeX Macros (Phase 4, v2.1)
- **FR-019**: LaTeX parser MUST handle superscripts (`^`) and subscripts (`_`) recursively within `{}` groupings across all nesting levels.
- **FR-020**: LaTeX parser MUST expand common mathematical macros (`\cdot`, `\to`, `\forall`, `\exists`, `\partial`, `\nabla`, `\left`, `\right`, and Greek letters) into structured math nodes, and log warnings without printing macro names as plain text.

#### Category 5: Bank Persistence Performance (Phase 5, v2.1)
- **FR-021**: Bank saving during interactive teaching MUST use debounced deferred writing (2-second idle window, tab change, or window close) with atomic file replacement.
- **FR-022**: Disk writes for bank persistence MUST execute asynchronously on a background worker thread with thread-safe locking.

#### Category 6: Fidelity Redesign & PDF-First Pipeline (Phase 6, v2.2 → v3.0)
- **FR-023**: Fidelity pipeline MUST extract text coordinates per line from intermediate PDF using an MIT-licensed PDF parsing library (`pdfplumber` / `pdfminer.six`).
- **FR-024**: Fidelity converter MUST manage Word COM and LibreOffice processes safely, suppressing alerts (`DisplayAlerts = 0`), closing documents without prompts, and releasing COM references.
- **FR-025**: Fidelity mode in GUI MUST indicate experimental status and disable selection when required conversion tools are unavailable on the host.

---

### Key Entities *(include if feature involves data)*

- **`Bank`**: Represents a handwriting collection. Contains categorized sample dictionaries: `words`, `digits`, `punct`, `symbols`, along with metadata (`xh`, `wgaps`, `pen`, `tombstones`).
- **`Document IR`**: Universal intermediate representation containing `Paragraph`, `Heading`, `Table`, `MathBlock`, `ListItem`, and `unsupported` metadata.
- **`WriteResult`**: Execution summary reporting `out_path`, `n_pages`, `n_lines`, `n_strokes`, `n_tokens`, `n_missing_tokens`, `missing`, and `missing_symbols`.
- **`FixedDocument`**: Layout model representing absolute spatial pages, `TextBox`es, `ImageBox`es, and background PDF references.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **100% Digit & Punctuation Usability**: A newly created font bank trained on digits 0–9 and punctuation can render multi-digit and decimal numbers ("2024", "3,5") with 0 missing digit errors.
- **SC-002**: **Zero Negative / Duplicate Token Errors**: 100% of generated run summaries report non-negative missing token ratios and exact page counts matching physical pages.
- **SC-003**: **Zero Accidental Character Loss in Importers**: 100% of mathematical comparison symbols (`<`, `>`) and list items in Markdown/DOCX test suites are preserved in document IR.
- **SC-004**: **Sub-50ms UI Latency on Interactive Word Teaching**: Adding or updating words in font banks of up to 1,500 words responds in <50ms without blocking the UI thread.
- **SC-005**: **Proportional Font Scaling**: At 2x scale (`--scale 2.0`), body text, line spacing, math formulas, and table columns scale within ±5% relative proportion without text overlap.
- **SC-006**: **Formula Nesting Depth**: LaTeX parser correctly evaluates formulas nested up to 10 levels deep (such as `\frac{x^2}{y}` and `e^{x^2}`) into proper superscript/subscript hierarchies.
- **SC-007**: **Strict License Conformance**: All newly introduced dependencies for PDF extraction in Fidelity mode use MIT or Apache 2.0 licenses (zero AGPL dependencies).
- **SC-008**: **Zero Architectural Regressions**: All 15+ architectural dependency checks in `test_architecture.py` pass cleanly, with 0 forbidden imports across layers.

---

## Assumptions

1. **Golden Master Visual Verification**: Regression tests affecting visual stroke output (Group B: line spacing L4, math scaling L5, inline word boundaries L6, tone mark quartile trimming L13, and table border jitter) will only update golden master constants after visual inspection in Xournal++.
2. **Line Spacing Behavior**: Default line spacing will scale proportionally with font size; users wishing to retain fixed absolute line spacing can explicitly specify `--line <val>`.
3. **Fidelity PDF Parsing Library**: PDF spatial extraction will use MIT-licensed libraries (`pdfplumber` / `pdfminer.six`) to strictly preserve the MIT license of this repository.
4. **Storage Format**: Font bank persistence will remain in `json.gz` format; database or journal formats (schema v4) are deferred unless deferred asynchronous debounced writes prove insufficient under empirical benchmarks.
5. **Execution Sequence**: Phases will be implemented in the verified order:
   - Phase 0: Test safety net (red tests for L1–L14 + benchmark script).
   - Phase 1: Digits and punctuation (L1) -> v2.0.1.
   - Phase 2: Correctness & truth fixes (L2–L3, L7–L8, L10–L12, R7, R10) -> v2.0.1.
   - Phase 3: Layout & geometry (L4, L5, L6, R8, R9) -> v2.1.
   - Phase 4: Math formulas & LaTeX parser (L9) -> v2.1.
   - Phase 5: Bank performance & debounced persistence (L14, L13) -> v2.1.
   - Phase 6: Fidelity PDF-first redesign (R1–R6) -> v2.2 / v3.0.
   - Phase 7: GUI ergonomics & experience.
   - Phase 8: Releases & technical discipline.
