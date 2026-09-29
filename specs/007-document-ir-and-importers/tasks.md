# Tasks: Document IR, Multi-Format Importers (TXT/MD/DOCX), Layout Engine, and Math/Table Rendering (Iteration 2)

**Feature Branch**: `007-document-ir-and-importers`  
**Spec**: [specs/007-document-ir-and-importers/spec.md](file:///d:/viet/app/specs/007-document-ir-and-importers/spec.md)  
**Plan**: [specs/007-document-ir-and-importers/plan.md](file:///d:/viet/app/specs/007-document-ir-and-importers/plan.md)  
**Review Decisions**: Incorporates all 7 critical findings from `/repo-engineering-review`

---

## Phase 1: Setup & Environment Validation

**Purpose**: Confirm dependencies, environment invariants, and baseline regression safety.

- [x] T001 Verify baseline test suite passes 100% (340/340 tests) and ruff lint clean across repository
- [x] T002 Fix optional dependency install syntax typo (`pip install ".[docs]"`) in chuviettay/importer/dependency.py
- [x] T003 [P] Add UnsupportedFormatError class definition in chuviettay/importer/base.py

---

## Phase 2: Foundational Invariants & Shared Contracts

**Purpose**: Core model updates, tokenizer fixes, and coordinate invariants that block user stories.

- [x] T004 Fix LaTeX math tokenizer in chuviettay/math/parser.py to separate numeric digits `[0-9]+` and alphabetic variables `[a-zA-Z]+`
- [x] T005 Update MathLayoutItem in chuviettay/layout/math_layout.py and data-model.md to enforce normalized unscaled bank coordinates ($S = 1.0$)
- [x] T006 Update MathLayoutEngine.__init__ in chuviettay/layout/math_layout.py to accept optional shared `writer: Writer` and `rnd: random.Random`

**Checkpoint**: Foundation ready — math AST tokenization and coordinate invariants established.

---

## Phase 3: User Story 1 - Math AST Stroke Generation & Single-Scale Text Alignment (Priority: P0) ⭐ MVP

**Goal**: Mathematical expressions (e.g. $x^2 + y^2 = 10$) generate real handwritten strokes for variables and digits via Writer, synthetic vector strokes for operators (`+`, `-`, `=`, `/`), and scale uniformly without quadratic double-scaling.

**Independent Test**: Render formulas with variables, numbers, exponents, fractions, and operators; assert non-zero stroke count for all known elements and verify uniform scaling factor under heading levels.

### Tests for User Story 1
- [x] T007 [P] [US1] Create unit tests for Math AST stroke generation (variables, numbers, operators) in tests/test_math_ast_strokes.py
- [x] T008 [P] [US1] Create unit tests for inline math single-scaling invariant across headings in tests/test_math_scaling.py

### Implementation for User Story 1
- [x] T009 [US1] Implement TextNode stroke and glyph generation in MathLayoutEngine.measure() using Writer.token() and Writer.number() in chuviettay/layout/math_layout.py
- [x] T010 [US1] Implement SymbolNode stroke generation with Bank.symbols lookup and synthetic vector stroke fallbacks for `+`, `-`, `=`, `/` in chuviettay/layout/math_layout.py
- [x] T011 [US1] Normalize MathLayoutItem output coordinates in chuviettay/layout/math_layout.py so baseline is at $y = 0$ in base bank units
- [x] T012 [US1] Update DocumentLayoutEngine._layout_inlines() in chuviettay/layout/engine.py to pass shared self.wr to MathLayoutEngine and keep math strokes in base bank units
- [x] T013 [US1] Update DocumentLayoutEngine._render_text_line() in chuviettay/layout/engine.py to accept `scale_mult` and apply $s = \text{self.S} \times \text{scale\_mult} \times (1 + \text{jitter})$ uniformly across all items

**Checkpoint**: User Story 1 complete — formulas render real handwritten strokes and scale properly with adjacent text.

---

## Phase 4: User Story 2 - Rich Table Cell Inlines & Column Alignments (Priority: P1)

**Goal**: Table cells render rich inlines (`MathInline`, `Symbol`, `LineBreak`, `Text`) without flattening to plain strings, and position content according to column alignments (`left`, `center`, `right`).

**Independent Test**: Render a table containing an inline math equation (`$E = mc^2$`) and discrete symbols; assert math strokes are rendered within cell boundaries and respect column alignments.

### Tests for User Story 2
- [x] T014 [P] [US2] Create unit tests for rich inlines (math, symbol, linebreak) inside table cells in tests/test_table_rich_inlines.py
- [x] T015 [P] [US2] Create unit tests for table column alignments (`left`, `center`, `right`) in tests/test_table_alignments.py

### Implementation for User Story 2
- [x] T016 [US2] Update TableLayoutEngine in chuviettay/layout/table_layout.py to measure cell natural width considering inline elements
- [x] T017 [US2] Refactor table cell rendering in DocumentLayoutEngine.render() in chuviettay/layout/engine.py to execute _layout_inlines() for each cell's paragraph blocks
- [x] T018 [US2] Implement horizontal alignment offset calculation (`left`, `center`, `right`) based on Table.col_alignments in chuviettay/layout/engine.py

**Checkpoint**: User Story 2 complete — tables render inline math, symbols, line breaks, and column alignments correctly.

---

## Phase 5: User Story 3 - Table Merged Cells (`colspan` & `rowspan`) (Priority: P1)

**Goal**: Word documents with merged cells (`w:gridSpan` and `w:vMerge`) import accurately with correct cell dimensions and without interior border lines cutting through merged areas.

**Independent Test**: Import and layout a table with merged cells; verify column width allocation and assert that interior border strokes do not intersect merged cell bounding boxes.

### Tests for User Story 3
- [x] T019 [P] [US3] Create unit tests for table colspan and rowspan parsing and layout in tests/test_table_merged_cells.py

### Implementation for User Story 3
- [x] T020 [US3] Update DocxImporter._parse_table() in chuviettay/importer/docx_importer.py to parse `w:gridSpan` and `w:vMerge` while deduplicating `c._tc` elements
- [x] T021 [US3] Update TableLayoutEngine.compute_column_widths() and layout_table() in chuviettay/layout/table_layout.py to handle multi-column and multi-row spans
- [x] T022 [US3] Update TableLayoutEngine.generate_border_strokes() in chuviettay/layout/table_layout.py to segment interior grid lines and suppress lines inside merged cell spans

**Checkpoint**: User Story 3 complete — tables with merged cells render accurately with seamless borders.

---

## Phase 6: User Story 4 - Unified Plaintext IR Pipeline & Paragraph Spacing (Priority: P1)

**Goal**: Plaintext `.txt` files route through `TxtImporter` and Document IR in CLI/GUI with blank lines preserved as vertical paragraph spacing, while preserving 100% SHA-256 byte parity for `ctl.write_text()`.

**Independent Test**: Load a `.txt` file with empty separating lines; verify vertical spacing in output. Run `tests/test_golden_master.py` to confirm 100% SHA-256 hash compatibility.

### Tests for User Story 4
- [x] T023 [P] [US4] Create unit tests for plaintext IR pipeline and blank line preservation in tests/test_txt_unified_pipeline.py

### Implementation for User Story 4
- [x] T024 [US4] Update TxtImporter.import_text() in chuviettay/importer/txt_importer.py to preserve blank lines as empty Paragraph(inlines=[])
- [x] T025 [US4] Update DocumentLayoutEngine.render() in chuviettay/layout/engine.py to advance `cur_y += self.line_h * 0.8` for empty paragraphs
- [x] T026 [US4] Update CLI write command in chuviettay/cli.py to route `.txt` files through ctl.import_document() and ctl.write_document()
- [x] T027 [US4] Update open_document() in chuviettay/view/write_tab.py to import `.txt` files as Document IR and set self.current_doc

**Checkpoint**: User Story 4 complete — unified plaintext workflow active, paragraph spacing preserved, golden master intact.

---

## Phase 7: User Story 5 - End-to-End Streaming `PageBuffer` Layout (Priority: P1)

**Goal**: Multi-page documents stream completed page XML to disk incrementally during layout, keeping memory constant.

**Independent Test**: Render a multi-page document and assert that `PageBuffer.append_page()` is invoked as each page completes and output file is valid gzip XML.

### Tests for User Story 5
- [x] T028 [P] [US5] Create unit tests for streaming PageBuffer integration in tests/test_page_buffer_stream.py

### Implementation for User Story 5
- [x] T029 [US5] Wire PageBuffer into DocumentLayoutEngine.render() in chuviettay/layout/engine.py to stream page XML sequentially and clear page memory

**Checkpoint**: User Story 5 complete — multi-page documents render with constant memory streaming.

---

## Phase 8: User Story 6 - Strict Format Validation & Unsupported OMML Diagnostics (Priority: P2)

**Goal**: Unrecognized file formats are rejected immediately with `UnsupportedFormatError`, and unsupported OMML tags are categorized into `ImportResult.unsupported`.

**Independent Test**: Pass unsupported extensions (`.pdf`, `.xlsx`) to `get_importer_for_path()` and verify `UnsupportedFormatError` is raised. Import a DOCX with matrix/limits and verify tags in `ImportResult.unsupported`.

### Tests for User Story 6
- [x] T030 [P] [US6] Create unit tests for format validation and OMML diagnostics in tests/test_format_validation.py and tests/test_docx_omml_diagnostics.py

### Implementation for User Story 6
- [x] T031 [US6] Update get_importer_for_path() in chuviettay/importer/base.py to validate extensions strictly and raise UnsupportedFormatError for invalid extensions
- [x] T032 [US6] Update DocxImporter in chuviettay/importer/docx_importer.py to detect unsupported OMML tags (`m:m`, `m:nary`, `m:limLow`, `m:limUpp`, `m:func`, `m:bar`, `m:acc`, `m:groupChr`, `m:eqArr`) and log into `ImportResult.unsupported`

**Checkpoint**: User Story 6 complete — strict format validation and comprehensive OMML diagnostics active.

---

## Phase 9: Polish, Regression Verification & Documentation

**Purpose**: System-wide verification across all tests, linters, and documentation.

- [x] T033 Verify tests/test_golden_master.py passes 100% (all 4 SHA-256 hashes match)
- [x] T034 Run full test suite (`py -3.12 -m pytest`) ensuring 100% pass across all test modules
- [x] T035 Run linter (`ruff check .`) and resolve any formatting or type inconsistencies
- [x] T036 Run quickstart.md validation scenarios across CLI and test suites

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Can start immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — blocks all user stories.
- **Phase 3 (User Story 1 - Math AST)**: Depends on Phase 2 — priority P0 MVP.
- **Phase 4 (User Story 2 - Rich Table Inlines)**: Depends on Phase 3 completion (reuses math inline layout).
- **Phase 5 (User Story 3 - Merged Table Cells)**: Depends on Phase 4 completion (enhances table layout).
- **Phase 6 (User Story 4 - Plaintext IR Pipeline)**: Can run in parallel with Phase 4/5.
- **Phase 7 (User Story 5 - Streaming PageBuffer)**: Depends on Phase 3/4/6 layout engine stabilization.
- **Phase 8 (User Story 6 - Format Validation & OMML Diagnostics)**: Can run in parallel with Phase 7.
- **Phase 9 (Polish & Regression)**: Depends on all user stories being complete.

---

## Parallel Execution Opportunities

- **Test Writing**: Tasks T007, T008, T014, T015, T019, T023, T028, T030 are marked `[P]` and can be written in parallel.
- **Independent Modules**:
  - T004 (`parser.py`) and T005/T006 (`math_layout.py`) can be modified independently.
  - T020 (`docx_importer.py`) and T021/T022 (`table_layout.py`) can proceed in parallel.
  - T024 (`txt_importer.py`) and T031 (`base.py`) can proceed in parallel.

---

## Implementation Strategy: MVP First

1. **Step 1**: Execute Phase 1 & Phase 2 (Foundational tokenizer and coordinate fixes).
2. **Step 2**: Execute Phase 3 (US1: Math AST stroke generation and single-scaling) — **Validate MVP**.
3. **Step 3**: Execute Phase 4 & Phase 5 (US2 & US3: Rich table inlines, column alignments, merged cells).
4. **Step 4**: Execute Phase 6 & Phase 7 (US4 & US5: Plaintext IR pipeline, blank lines, streaming PageBuffer).
5. **Step 5**: Execute Phase 8 & Phase 9 (US6: Format validation, diagnostics, full test suite & golden master verification).
