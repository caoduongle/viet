# Tasks: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for the fidelity layout module.

- [X] T001 Create package directory `chuviettay/fidelity/` and initialize `chuviettay/fidelity/__init__.py`
- [X] T002 [P] Create test fixtures directory `tests/fixtures/fidelity/` with mock UTF-8 JSON extraction data and sample background PDF

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models, configuration options, converter interfaces, and architectural safety rules that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Implement `FixedDocument`, `FixedPage`, `SpatialBox`, `TextBox`, `ImageBox`, and `TableGeometry` models in `chuviettay/fidelity/fixed_model.py`
- [X] T004 [P] Implement `WriteMode` (`SEMANTIC = "semantic"`, `FIDELITY = "fidelity"`) and extend `WriteOptions` with `mode: WriteMode` in `chuviettay/model/composer.py`
- [X] T005 Implement `FidelityConverter` interface with Word COM PowerShell runner (UTF-8 JSON bridge + safe COM cleanup) and headless LibreOffice/mock fallback in `chuviettay/fidelity/converter.py`
- [X] T006 Update `tests/test_architecture.py` to include `py_files("fidelity")` in architecture safety rules (no print/input, no sys.exit, no tkinter outside view)

**Checkpoint**: Foundation ready - spatial models, options, and conversion abstractions in place.

---

## Phase 3: User Story 1 - Exact Layout & Geometry Preservation with In-Place Text Replacement (Priority: P1) 🎯 MVP

**Goal**: Extract spatial bounding boxes for all text elements from DOCX, fit handwritten strokes directly into their respective bounding boxes, and preserve exact page count and dimensions without reflowing lines across pages.

**Independent Test**: Provide a multi-page DOCX fixture, execute fidelity replacement, and verify that the output has the exact same page count and that handwritten strokes are placed within the geometric bounding box of each text element.

### Tests for User Story 1
- [X] T007 [P] [US1] Create unit and integration tests for fidelity spatial extraction and stroke placement in `tests/test_docx_fidelity.py`

### Implementation for User Story 1
- [X] T008 [US1] Implement `SpatialTextExtractor` to parse Word COM UTF-8 JSON export into `FixedPage` and `TextBox` models with multi-line paragraph support in `chuviettay/fidelity/extractor.py`
- [X] T009 [US1] Implement `FidelityLayoutEngine` in `chuviettay/fidelity/engine.py` placing handwriting strokes fitted into each `TextBox` bounding box without reflow
- [X] T010 [US1] Implement `AppController.write_docx_fidelity()` in `chuviettay/controller/app_controller.py` coordinating extraction, background generation, and stroke rendering

**Checkpoint**: User Story 1 functional: text replaced in-place into bounding boxes across fixed pages.

---

## Phase 4: User Story 2 - Complete Non-Text Graphic Element Preservation (Priority: P1) 🎯 MVP

**Goal**: Preserve 100% of embedded images (all 19 PNG inline drawings in Problem Set 03), table borders, charts, and diagrams in a non-text visual background generated via DOCX whiteout run transformation.

**Independent Test**: Process a document containing embedded images and tables. Verify all images and tables appear intact at their exact coordinates in the companion background PDF without printed text ghosting.

### Tests for User Story 2
- [X] T011 [P] [US2] Add unit test for whiteout run transformation and non-text element preservation in `tests/test_docx_fidelity.py`

### Implementation for User Story 2
- [X] T012 [US2] Implement `WhiteoutBackgroundGenerator` in `chuviettay/fidelity/background.py` setting text runs to `w:color w:val="FFFFFF"` to preserve 100% of images, table borders, and shapes without printed text bleed
- [X] T013 [US2] Integrate background PDF generation and relative path linking into `FidelityLayoutEngine` in `chuviettay/fidelity/engine.py`

**Checkpoint**: User Stories 1 AND 2 work together as a solid MVP: 19 pages, 19 images, and 8 tables 100% preserved with handwriting overlay.

---

## Phase 5: User Story 3 - Distinct Mode Selection: Semantic Reflow vs. Fidelity In-Place (Priority: P2)

**Goal**: Allow users to explicitly select between Semantic Mode (free-flowing reflow across paper sizes/grids) and Fidelity Mode (fixed-page layout preserving geometry and images) via CLI and GUI.

**Independent Test**: Execute CLI and GUI with `--mode semantic` and `--mode fidelity` and confirm distinct pipeline activation.

### Tests for User Story 3
- [X] T014 [P] [US3] Add CLI and Controller mode switching tests in `tests/test_cli_format.py` and `tests/test_docx_fidelity.py`

### Implementation for User Story 3
- [X] T015 [US3] Add `--mode {semantic,fidelity}` flag to `hw-note write` in `chuviettay/cli.py` routing DOCX to `write_docx_fidelity` or `write_document`
- [X] T016 [US3] Add Fidelity/Semantic mode selection option to GUI `WriteTab` in `chuviettay/view/write_tab.py`

**Checkpoint**: User Story 3 functional: users have clear, distinct control over Semantic vs. Fidelity modes.

---

## Phase 6: User Story 4 - Multi-Page Annotation Viewer Compatibility (Priority: P3)

**Goal**: Ensure generated `.xopp` files open seamlessly in Xournal++ with valid multi-page `<background type="pdf" domain="relative" filename="..." pageno="N"/>` tags and crisp stroke overlays.

**Independent Test**: Verify generated `.xopp` XML conforms to Xournal++ multi-page background specifications and relative path portability.

### Tests for User Story 4
- [X] T017 [P] [US4] Add XOPP background tag validation test verifying multi-page `<background type="pdf" .../>` tags in `tests/test_docx_fidelity.py`

### Implementation for User Story 4
- [X] T018 [US4] Support companion PDF relative path handling and multi-page XML generation in `chuviettay/model/xopp.py`

**Checkpoint**: User Story 4 functional: complete multi-page Xournal++ compatibility verified.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linting, regression prevention, and final quality checks.

- [X] T019 Run validation scenarios in `specs/013-docx-fidelity-replacement/quickstart.md`
- [X] T020 Run linter `python -m ruff check .` and resolve all formatting/linting issues
- [X] T021 Run full automated test suite `pytest -v --timeout=60` across all test suites ensuring 100% pass rate

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2; integrates with US1 to complete MVP.
- **User Story 3 (Phase 5)**: Depends on Phase 3 and Phase 4.
- **User Story 4 (Phase 6)**: Depends on Phase 3 and Phase 4.
- **Polish (Phase 7)**: Depends on all user stories completed.

### Parallel Opportunities
- T002 can run in parallel with T001.
- T003 and T004 can run in parallel in Phase 2.
- Test tasks T007, T011, T014, and T017 can be developed concurrently with their respective domain definitions.
- Polish tasks T019 and T020 can run concurrently.

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, 3, 4)
1. Complete Foundational models and converter interfaces (Phases 1 & 2).
2. Implement Spatial Text Extractor and In-Place Stroke Layout (Phase 3).
3. Implement Whiteout Background Generator for 100% image & table preservation (Phase 4).
4. Validate MVP with `test_docx_fidelity.py`.

### Incremental Delivery
- Add Phase 5 (CLI and GUI `--mode` selector).
- Add Phase 6 (Xournal++ relative path background portability).
- Add Phase 7 (Full regression and lint verification).
