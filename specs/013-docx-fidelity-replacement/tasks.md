# Tasks: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Input**: Design artifacts from `specs/013-docx-fidelity-replacement/` (`spec.md`, `plan.md`, `data-model.md`, `research.md`, `contracts/`, `quickstart.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module structure initialization, test fixtures, and schema extensions.

- [X] T001 Initialize package structure in `chuviettay/fidelity/__init__.py`
- [X] T002 [P] Configure unit test fixtures and sample data in `tests/fixtures/fidelity/sample_fidelity_data.json` and `tests/fixtures/fidelity/sample_background.pdf`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and foundational converters that MUST be complete before user stories can execute.

- [X] T003 Implement fixed-layout spatial models (`FixedDocument`, `FixedPage`, `SpatialBox`, `TextBox`, `ImageBox`, `TableGeometry`) in `chuviettay/fidelity/fixed_model.py`
- [X] T004 [P] Implement fail-fast `FidelityConverter` interface with `_ps_quote` string escaping and strict `RuntimeError` (zero fixture fallback in production) in `chuviettay/fidelity/converter.py`
- [X] T005 [P] Implement `pdf_background_xml` with relative domain support in `chuviettay/model/xopp.py`

**Checkpoint**: Foundational models and core converter interfaces ready — user story implementation can proceed.

---

## Phase 3: User Story 1 - Exact Layout & Geometry Preservation with In-Place Text Replacement (Priority: P1) 🎯 MVP

**Goal**: Lock document geometry and page count, fit handwritten strokes into text bounding boxes, and segment mixed-inline content (`text -> image -> text`) so strokes never overwrite images.

**Independent Test**: Convert a document with known coordinates; verify output has identical page count, strokes remain inside text bounding boxes, and paragraphs with inline images are split cleanly around image boundaries.

### Tests for User Story 1
- [X] T006 [P] [US1] Unit test for `FixedDocument` deserialization, multiline paragraph splitting, and mixed-inline segmentation in `tests/test_docx_fidelity.py`
- [X] T007 [P] [US1] Unit test for in-place stroke placement, baseline calculation, and scale adjustment in `tests/test_docx_fidelity.py`

### Implementation for User Story 1
- [X] T008 [US1] Implement `SpatialTextExtractor` with multiline splitting and inline image segmentation in `chuviettay/fidelity/extractor.py`
- [X] T009 [US1] Implement `FidelityLayoutEngine` fitting strokes into `TextBox` regions with alignment (`left`, `center`, `right`) and scale adjustment in `chuviettay/fidelity/engine.py`

**Checkpoint**: User Story 1 functional — strokes are fitted into bounding boxes without reflow or image collision.

---

## Phase 4: User Story 2 - Complete Non-Text Graphic Element Preservation & Clean Whiteout (Priority: P1) 🎯 MVP

**Goal**: Preserve 100% of images and tables in the background PDF, while neutralizing all printed text to `#FFFFFF` across standard paragraphs, nested tables, headers, footers, and DrawingML/textbox shapes.

**Independent Test**: Execute whiteout transformation on a document with tables, inline shapes, and DrawingML callouts; verify that all text elements are white (`#FFFFFF`) while image vectors and borders remain intact.

### Tests for User Story 2
- [X] T010 [P] [US2] Unit test for `WhiteoutBackgroundGenerator` verifying complete text whitening across paragraphs, nested tables, and DrawingML shapes in `tests/test_docx_fidelity.py`
- [X] T011 [P] [US2] Integration test for PDF background generation with non-text elements in `tests/test_docx_fidelity.py`

### Implementation for User Story 2
- [X] T012 [US2] Implement comprehensive XPath-based whiteout transform covering `doc.paragraphs`, `cell.tables`, headers/footers, and DrawingML/VML shapes in `chuviettay/fidelity/background.py`
- [X] T013 [US2] Implement Word COM and LibreOffice PDF conversion pipeline in `chuviettay/fidelity/converter.py` with `[char]1` filtering for image-only paragraphs

**Checkpoint**: User Stories 1 and 2 integrated — clean background PDF generated with 100% graphics and zero printed text ghosting.

---

## Phase 5: User Story 3 - Distinct Mode Selection & Strict Production Dependency Enforcement (Priority: P2)

**Goal**: Expose `--mode {semantic,fidelity}` on CLI and GUI, enforce non-DOCX validation, report accurate statistics (`n_pages`, `n_images`, `n_tables`), and enforce strict fail-fast behavior without dummy fixture leakage in production.

**Independent Test**: Execute CLI and GUI in both modes; verify semantic mode uses `DocumentLayoutEngine`, fidelity mode uses `FidelityLayoutEngine`, non-DOCX files in fidelity mode are rejected with clear guidance, and missing Word/LibreOffice raises a clear `RuntimeError`.

### Tests for User Story 3
- [X] T014 [P] [US3] Unit test for `WriteMode` validation, `WriteResult` statistics, and fail-fast `RuntimeError` when converter is unavailable in `tests/test_docx_fidelity.py`
- [X] T015 [P] [US3] CLI tests for `--mode fidelity`, `--mode semantic`, non-DOCX rejection, and fidelity statistics output in `tests/test_cli_format.py`
- [X] T016 [P] [US3] GUI test for Fidelity mode selection and non-DOCX error dialog in `tests/test_gui_document.py`

### Implementation for User Story 3
- [X] T017 [US3] Add `WriteMode` enum, `mode` field to `WriteOptions`, and `n_pages`/`n_images` to `WriteResult` in `chuviettay/model/composer.py`
- [X] T018 [US3] Implement `write_docx_fidelity` in `chuviettay/controller/app_controller.py` with strict converter checks and comprehensive logging
- [X] T019 [US3] Add `--mode` argument, non-DOCX validation, and fidelity statistics report to CLI in `chuviettay/cli.py`
- [X] T020 [US3] Add "Chế độ DOCX" Combobox and file requirement enforcement to GUI in `chuviettay/view/write_tab.py`

**Checkpoint**: Mode switching and dependency fail-fast fully operational across CLI, GUI, and Controller.

---

## Phase 6: User Story 4 - Multi-Page Annotation Viewer Compatibility (Priority: P3)

**Goal**: Ensure multi-page `.xopp` files properly link to the companion background PDF using portable relative paths (`domain="relative"`) across all pages.

**Independent Test**: Verify generated `.xopp` XML contains `<background type="pdf" domain="relative" filename="..." pageno="N"/>` for every page matching the source document.

### Tests for User Story 4
- [X] T021 [P] [US4] Test multi-page relative background XML generation and page sequence validation in `tests/test_docx_fidelity.py`

### Implementation for User Story 4
- [X] T022 [US4] Finalize relative path resolution and multi-page XML serialization in `chuviettay/fidelity/engine.py`

**Checkpoint**: Multi-page `.xopp` packages are fully compliant with Xournal++ format specifications and portable across directories.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linting, architectural integrity, and full regression verification.

- [X] T023 Run validation scenarios in `specs/013-docx-fidelity-replacement/quickstart.md`
- [X] T024 [P] Verify layered architecture rules in `tests/test_architecture.py`
- [X] T025 [P] Run linter `python -m ruff check .` and ensure 0 lint errors
- [X] T026 Run full automated test suite `pytest -v --timeout=60` ensuring 100% pass rate across all 422+ tests

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2; integrates with US1 to form the complete MVP.
- **User Story 3 (Phase 5)**: Depends on Phase 3 and Phase 4.
- **User Story 4 (Phase 6)**: Depends on Phase 3 and Phase 4.
- **Polish (Phase 7)**: Depends on all user stories completed.

### Parallel Opportunities
- T002 can run in parallel with T001.
- T004 and T005 can run in parallel in Phase 2.
- Test tasks T006, T007, T010, T011, T014, T015, T016, and T021 can run in parallel.
- Polish tasks T024 and T025 can run in parallel.

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, 3, 4)
1. Complete Foundational models and converter interfaces with zero-fixture fallback (Phases 1 & 2).
2. Implement Spatial Text Extractor with mixed-inline segmentation and In-Place Stroke Layout (Phase 3).
3. Implement Deep XML Whiteout Background Generator for 100% image, table, and shape preservation (Phase 4).
4. Validate MVP with `tests/test_docx_fidelity.py`.

### Incremental Delivery
- Add Phase 5 (CLI and GUI `--mode` selector, non-DOCX validation, and statistics reporting).
- Add Phase 6 (Multi-page relative path background linking for Xournal++ portability).
- Add Phase 7 (Full regression, architectural conformance, and lint verification).
