# Tasks: Comprehensive Quality, Correctness, and Performance Hardening

**Input**: Design artifacts from `specs/014-core-engine-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `research.md`, `contracts/`, `quickstart.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test harness initialization, benchmarking tools, and development dependency configuration.

- [X] T001 Configure dev dependencies and benchmark script in `pyproject.toml` and `scripts/benchmark_bank_io.py`
- [X] T002 [P] Setup Phase 0 safety net regression test file reproducing defects L1–L14 in `tests/test_engine_hardening_safety_net.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared classification utilities, sample signatures, and architectural boundary rules that block all user stories.

- [X] T003 Implement unified token classification `classify_token(token: str) -> str` (`digits`, `punct`, `symbols`, `words`) in `chuviettay/model/learning.py`
- [X] T004 [P] Implement `_sample_signature(strokes) -> str` coordinate-based deduplication hash in `chuviettay/model/learning.py`
- [X] T005 [P] Update `tests/test_architecture.py` to strictly forbid `chuviettay.controller` imports within `chuviettay/layout/`
- [X] T006 Fix MVC layering in `chuviettay/layout/engine.py` by importing `WriteOptions` and `WriteResult` from `chuviettay.model.composer`

**Checkpoint**: Foundational classification and architectural integrity gates verified — user stories can proceed.

---

## Phase 3: User Story 1 - Number & Punctuation Learning & Writing (L1, v2.0.1) 🎯 MVP

**Goal**: Enable newly trained font banks to learn individual digits (0–9) and punctuation marks, storing them in `bank.digits` and `bank.punct`, and rendering multi-digit and decimal numbers cleanly with backward-compatible fallback to `words`.

**Independent Test**: Train digits `0`–`9` and `, .` in a fresh bank; write `"Năm 2024 đạt 3,5 điểm"` and verify strokes are generated without missing token errors.

### Tests for User Story 1
- [X] T007 [P] [US1] Unit test for digit (0–9) and punctuation learning and `Writer.number` handwriting generation in `tests/test_digits_and_punct.py`

### Implementation for User Story 1
- [X] T008 [US1] Route classified samples to `bank.digits` and `bank.punct` during `add_sample` and `add_sample_incremental` in `chuviettay/model/bank.py`
- [X] T009 [US1] Implement backward-compatible lookup in `Writer.number` (search `digits` then `words`) in `chuviettay/model/writer.py`
- [X] T010 [US1] Add "Minimal Essentials" training queue (0–9, common punctuation, top 60 frequent words) to GUI in `chuviettay/view/write_tab.py`

**Checkpoint**: User Story 1 functional — newly trained banks can write numbers and punctuation; MVP milestone reached.

---

## Phase 4: User Story 2 - Accurate Missing Token Statistics & Page Buffer Reporting (L2, L3, v2.0.1) 🎯 MVP

**Goal**: Ensure `WriteResult` accurately reflects physical page count (`n_pages` from `PageBuffer`) and correctly calculates missing tokens and symbols without negative ratios or duplicate counting.

**Independent Test**: Generate a 5-page document with an empty bank; verify `result.n_pages == 5`, missing tokens are strictly positive, and missing symbols are counted once.

### Tests for User Story 2
- [X] T011 [P] [US2] Unit test for accurate `n_pages` from `PageBuffer` and non-negative missing token ratios in `tests/test_reporting_statistics.py`

### Implementation for User Story 2
- [X] T012 [US2] Pass `n_pages=len(buffer.pages)` into `WriteResult` instantiation in `chuviettay/layout/engine.py`
- [X] T013 [US2] Fix missing token count granularity and eliminate duplicate symbol accumulation in `_layout_inlines` and `render` in `chuviettay/layout/engine.py`

**Checkpoint**: User Story 2 functional — page count and token diagnostics are 100% accurate.

---

## Phase 5: User Story 3 - Robust Importer Fidelity & Content Preservation (L6, L7, L8, L10, v2.0.1) 🎯 MVP

**Goal**: Preserve mathematical comparisons (`<`, `>`), nested list hierarchies, soft line breaks, tabs, and tracked changes in Markdown and DOCX documents, recording unsupported blocks transparently in `Document.unsupported`.

**Independent Test**: Import Markdown with `1 < 2 và 3 > 2`, nested lists, and code blocks; import DOCX with tabs and soft breaks; verify 0% text omission and proper `unsupported` metadata.

### Tests for User Story 3
- [X] T014 [P] [US3] Unit tests for `<` and `>` inequality preservation, nested lists, and DOCX soft breaks/tabs/tracked changes in `tests/test_importer_fidelity.py`

### Implementation for User Story 3
- [X] T015 [US3] Remove `_sanitize_html` in `chuviettay/importer/markdown_importer.py` to preserve `<` and `>` characters
- [X] T016 [US3] Implement recursive nested list parsing and record omitted blocks (`code_block`, `hr`) in `unsupported` in `chuviettay/importer/markdown_importer.py`
- [X] T017 [US3] Iterate all `<w:t>` runs, convert `<w:tab/>` and `<w:br/>`, process `<w:ins>`, and record unsupported fields in `chuviettay/importer/docx_importer.py`
- [X] T018 [US3] Prevent artificial whitespace inflation across inline formatting spans followed by punctuation in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: User Story 3 functional — document importers preserve 100% of user text and mathematical comparisons.

---

## Phase 6: User Story 4 - Bank Data Integrity, Deduplication & Clean Architecture (L11, L12, L13, R7, R10, v2.0.1)

**Goal**: Prevent duplicate sample ingestion via stroke signatures, ensure dropped symbols/digits stay deleted via tombstones, fix symmetric quartile trimming, and eliminate resource leaks.

**Independent Test**: Re-learn an identical sheet; verify sample count does not double; drop a symbol and merge; verify it remains deleted; verify symmetric quartile trimming on $n=11$.

### Tests for User Story 4
- [X] T019 [P] [US4] Unit tests for sample deduplication, tombstones across symbols/digits/punct, symmetric tone mark trimming, and closed file descriptors in `tests/test_bank_integrity.py`

### Implementation for User Story 4
- [X] T020 [US4] Enforce `_sample_signature` coordinate check in `add_sample` to reject duplicate identical samples in `chuviettay/model/bank.py`
- [X] T021 [US4] Implement tombstones for `drop_symbol` and apply tombstones across `symbols`, `digits`, and `punct` in `merge_bank_dicts` in `chuviettay/model/bank.py`
- [X] T022 [US4] Fix symmetric percentile trimming formula `hi_idx = len(dy_vals) - 1 - cut` in `_refresh_tone_marks` in `chuviettay/model/bank.py`
- [X] T023 [US4] Use context manager `with open(...)` in `read_xopp` and escape XML attributes in `stroke_xml` in `chuviettay/model/xopp.py`

**Checkpoint**: User Story 4 functional — bank integrity protected, zero memory/file leaks, v2.0.1 milestone complete.

---

## Phase 7: User Story 5 - Proportional Font & Geometry Scaling Across Layout Elements (L4, L5, R8, R9, v2.1)

**Goal**: Automatically scale line spacing with font size, ensure uniform scaling between body text and math formulas, measure table columns from stroke bounding boxes, and add deterministic table border jitter.

**Independent Test**: Render at scale 2.0; verify line spacing is ~2x scale 1.0 without overlap; verify table words do not overflow cell borders.

### Tests for User Story 5
- [X] T024 [P] [US5] Unit tests for scale-proportional line height, math block scaling, and stroke-bounded table measurement in `tests/test_geometry_scaling.py`

### Implementation for User Story 5
- [X] T025 [US5] Implement scale-proportional line height (`base_line_h * opts.scale`) when `--line` is not explicitly set in `chuviettay/layout/engine.py`
- [X] T026 [US5] Unify `eff_scale` across inline math and standalone display math blocks in `chuviettay/layout/math_layout.py`
- [X] T027 [US5] Measure table columns using stroke bounding boxes (`calc_text_bounds`) and add deterministic border jitter in `chuviettay/layout/table_layout.py`
- [X] T028 [US5] Checkpoint: Perform manual visual verification in Xournal++ for Group B outputs before updating any golden master constants in `tests/test_golden_master.py`

**Checkpoint**: User Story 5 functional — geometry and scaling scale in perfect visual harmony.

---

## Phase 8: User Story 6 - Advanced Mathematical Expression & LaTeX Macro Support (L9, v2.1)

**Goal**: Evaluate nested exponents (`^`) and subscripts (`_`) within grouping braces `{}` up to depth 32, and map standard LaTeX macros (`\cdot`, `\to`, `\forall`, Greek letters) into math symbol entities.

**Independent Test**: Parse and render `\frac{x^2}{y}` and `e^{x^2}`; verify numerator exponents are elevated and macros like `\cdot` render as symbols rather than text.

### Tests for User Story 6
- [X] T029 [P] [US6] Unit tests for nested `{}` exponents/subscripts, macro expansion (`\cdot`, `\to`, `\forall`, Greek letters), and recursion limit in `tests/test_latex_macros.py`

### Implementation for User Story 6
- [X] T030 [US6] Implement recursive row parser `parse_row` for nested braces `{}` up to depth 32 in `chuviettay/math/parser.py`
- [X] T031 [US6] Expand LaTeX macro dictionary and gracefully route unknown macros to `missing_symbols` in `chuviettay/math/parser.py`

**Checkpoint**: User Story 6 functional — technical documents and formulas render with complete mathematical syntax trees.

---

## Phase 9: User Story 7 - Responsive Bank Persistence & Deferred Saves (L14, v2.1)

**Goal**: Deliver <50ms interactive training responsiveness on banks with >1,000 words using debounced 2-second saving, thread-safe JSON snapshotting, and background worker disk writes.

**Independent Test**: Rapidly teach 10 words in succession; verify UI responds instantly and changes are flushed to disk after 2 seconds of inactivity or upon closing.

### Tests for User Story 7
- [X] T032 [P] [US7] Benchmark and unit test for non-blocking debounced save and thread-safe background writing in `tests/test_debounced_save.py`

### Implementation for User Story 7
- [X] T033 [US7] Implement thread-safe JSON snapshot serialization under lock and background worker writing with atomic tempfile replacement in `chuviettay/model/bank.py`
- [X] T034 [US7] Integrate 2-second debounce timer, tab switch flush, and window close flush in `chuviettay/controller/app_controller.py` and `chuviettay/view/write_tab.py`

**Checkpoint**: User Story 7 functional — interactive training is smooth and latency-free; v2.1 milestone complete.

---

## Phase 10: User Story 8 - High-Fidelity PDF-Based Document Layout Reconstruction (R1-R6, v2.2 → v3.0)

**Goal**: Transition Fidelity Mode to a PDF-first architecture: convert DOCX to PDF, extract coordinates per line via an MIT-licensed parser (`pdfplumber`), neutralize printed text with white overlays, and cache converter availability.

**Independent Test**: Convert a multi-line multi-page DOCX in Fidelity mode on headless Linux with LibreOffice; verify each line is extracted as a separate bounding box and pages render with true x-height scaling.

### Tests for User Story 8
- [X] T035 [P] [US8] Integration test for PDF-first line-by-line bounding box extraction using MIT parser in `tests/test_fidelity_pdf_first.py`

### Implementation for User Story 8
- [X] T036 [US8] Implement line-by-line spatial extraction via `pdfplumber` (MIT) in `chuviettay/fidelity/extractor.py`
- [X] T037 [US8] Implement whiteout PDF rectangle overlay generator in `chuviettay/fidelity/background.py`
- [X] T038 [US8] Cache converter availability and enforce clean COM lifecycle management in `chuviettay/fidelity/converter.py`

**Checkpoint**: User Story 8 functional — Fidelity mode is cross-platform, line-accurate, and license-compliant; v2.2/v3.0 milestone complete.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Option synchronization, packaging dependencies, documentation updates, and complete regression verification.

- [X] T039 [P] Synchronize GUI options (`lined`, `iso_dotted`, paper sizes) with CLI flags in `chuviettay/view/write_tab.py`
- [X] T040 [P] Update `pyproject.toml` with `pytest-timeout`, `ruff`, and Python 3.13 classifier in `pyproject.toml`
- [X] T041 [P] Update README test counts and document tree in `README.md`
- [X] T042 Run validation scenarios in `specs/014-core-engine-hardening/quickstart.md`
- [X] T043 [P] Run linter `python -m ruff check .` and ensure 0 lint errors
- [X] T044 Run full automated test suite `pytest -v --timeout=60` ensuring 100% pass rate across all 425+ tests

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3, v2.0.1)**: Depends on Phase 2.
- **User Story 2 (Phase 4, v2.0.1)**: Depends on Phase 2.
- **User Story 3 (Phase 5, v2.0.1)**: Depends on Phase 2.
- **User Story 4 (Phase 6, v2.0.1)**: Depends on Phase 2; completes v2.0.1 release milestone.
- **User Story 5 (Phase 7, v2.1)**: Depends on Phase 2 and US3.
- **User Story 6 (Phase 8, v2.1)**: Depends on Phase 2.
- **User Story 7 (Phase 9, v2.1)**: Depends on Phase 2 and US4; completes v2.1 release milestone.
- **User Story 8 (Phase 10, v2.2/v3.0)**: Depends on Phase 2.
- **Polish (Phase 11)**: Depends on all user stories completed.

### Parallel Opportunities
- T002 can run in parallel with T001 in Setup.
- T004 and T005 can run in parallel with T003 in Foundational.
- Test tasks T007, T011, T014, T019, T024, T029, T032, and T035 can all be authored in parallel.
- Polish tasks T039, T040, T041, and T043 can run in parallel.

---

## Implementation Strategy

### MVP First (v2.0.1 Core Milestone: Phases 1, 2, 3, 4, 5, 6)
1. Complete Setup and Foundational tasks (T001–T006).
2. Complete US1 (Digits and Punctuation) -> validates core writing capability.
3. Complete US2 (Reporting & Page Count) -> validates diagnostic reporting.
4. Complete US3 (Importer Content Preservation) -> validates text fidelity without data loss.
5. Complete US4 (Bank Integrity & Deduplication) -> locks down data safety and architecture rules.
6. Validate v2.0.1 without touching visual golden master constants (Group A).

### Incremental Delivery (v2.1 & Beyond)
1. Implement US5 (Proportional Scaling & Line Height) -> perform visual verification in Xournal++ before updating golden master constants.
2. Implement US6 (LaTeX Macro Expansion) -> expands formula expressiveness.
3. Implement US7 (Debounced Deferred Bank Persistence) -> removes interactive GUI lag.
4. Implement US8 (PDF-First Fidelity Pipeline) -> achieves cross-platform fidelity.
5. Execute full polish, documentation, and regression suite.
