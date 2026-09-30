# Tasks: Unify Direct Text Input into Document IR Pipeline & Margin Validation

**Feature Branch**: `012-unify-write-text-pipeline` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify and harmonize architectural references across specification and research artifacts.

- [X] T001 Review and synchronize design decisions in `specs/012-unify-write-text-pipeline/research.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core validation logic that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Implement margin boundary checks (`margin_left + margin_right >= pf.width` and `margin_top + margin_bottom >= pf.height`) in `WriteOptions.validate()` in `chuviettay/model/composer.py`
- [X] T003 [P] Add unit tests for margin boundary validation errors in `tests/test_page_format.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Direct Text Input Uses Unified Document IR Pipeline & Paper Settings (Priority: P1) 🎯 MVP

**Goal**: Route direct text input through `TxtImporter` and `DocumentLayoutEngine` via `AppController.write_text()`, ensuring paper size, orientation, and background XML apply to all text inputs.

**Independent Test**: Call `ctl.write_text()` with A3 landscape and ô li graph background, asserting generated `.xopp` contains `<page width="1190.55" height="841.89">` and `<background ... style="graph" config="r1=14.17"/>`.

### Tests for User Story 1
- [X] T004 [P] [US1] Add integration test for `ctl.write_text()` with paper size and background in `tests/test_document_pipeline.py`

### Implementation for User Story 1
- [X] T005 [US1] Refactor `AppController.write_text()` in `chuviettay/controller/app_controller.py` to convert text via `TxtImporter` and delegate to `self.write_document()`
- [X] T006 [US1] Update `WriteTab.do_write()` in `chuviettay/view/write_tab.py` to route direct text through `self.ctl.write_text()`
- [X] T007 [US1] Mark legacy `compose_document()` and `write_document()` in `chuviettay/model/composer.py` as deprecated

**Checkpoint**: User Story 1 is functional: direct text input uses the unified Document IR pipeline.

---

## Phase 4: User Story 2 - Strict Margin Boundary Validation (Priority: P1) 🎯 MVP

**Goal**: Protect the layout engine from degenerate configurations by rejecting margin sums that meet or exceed paper dimensions.

**Independent Test**: Assert that `WriteOptions(margin_left=400, margin_right=300).validate()` raises `ValueError`.

### Tests for User Story 2
- [X] T008 [P] [US2] Add unit tests for custom paper size and landscape orientation margin boundary validation in `tests/test_page_format.py`

### Implementation for User Story 2
- [X] T009 [US2] Verify and clamp `PageFormat.usable_width` and `PageFormat.usable_height` safeguards in `chuviettay/document/page_format.py`

**Checkpoint**: User Stories 1 AND 2 work together as a solid, validated MVP.

---

## Phase 5: User Story 3 - GUI Direct-Text End-to-End Regression Verification (Priority: P2)

**Goal**: Fortify GUI tests to guarantee direct text typed into the "Viết chữ" tab applies paper size and background options end-to-end.

**Independent Test**: Run `pytest tests/test_gui_document.py` and confirm direct-text entry produces A3 landscape graph output.

### Implementation & Tests for User Story 3
- [X] T010 [US3] Fortify `test_gui_write_tab_paper_and_background_options` in `tests/test_gui_document.py` with `assert app.write_tab.current_doc is None` and XML checks
- [X] T011 [US3] Add GUI direct text test with custom paper size dialog in `tests/test_gui_document.py`

**Checkpoint**: GUI direct text workflow is fully covered by automated regression tests.

---

## Phase 6: User Story 4 - Backward Compatibility & Verification Integrity (Priority: P3)

**Goal**: Preserve 100% test suite pass rate and maintain legacy golden master algorithm verification.

**Independent Test**: Run `pytest tests/test_golden_master.py` and full test suite to confirm 100% pass rate.

### Implementation & Tests for User Story 4
- [X] T012 [P] [US4] Update `tests/test_golden_master.py` to call `composer.write_document(ctl.bank, text, opts, out)` preserving legacy algorithm verification
- [X] T013 [US4] Update `_cmd_write` in `chuviettay/cli.py` to route raw text through `ctl.write_text()`

**Checkpoint**: Full backward compatibility preserved across legacy and modern workflows.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linting, and final quality checks.

- [X] T014 Run quickstart scenarios in `specs/012-unify-write-text-pipeline/quickstart.md`
- [X] T015 Run linter `python -m ruff check .` and resolve any style/lint issues
- [X] T016 Run complete automated test suite `pytest -v --timeout=60` to ensure zero regressions

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2; integrates with US1.
- **User Story 3 (Phase 5)**: Depends on Phase 3 and Phase 4.
- **User Story 4 (Phase 6)**: Depends on Phase 3.
- **Polish (Phase 7)**: Depends on all user stories completed.

### Parallel Opportunities
- T002 and T003 can proceed in tandem.
- T004, T008, and T012 can run in parallel before dependent implementations.
- Polish tasks T014 and T015 can execute concurrently.

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, 3, 4)
1. Complete Foundational margin validation (Phase 2).
2. Refactor `AppController.write_text()` to use `TxtImporter` $\to$ `self.write_document()` (Phase 3).
3. Validate MVP with `test_document_pipeline.py`.

### Incremental Delivery
- Add Phase 5 (GUI direct-text test fortification).
- Add Phase 6 (Golden master alignment and CLI routing).
- Add Phase 7 (Full regression and lint verification).
