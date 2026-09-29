# Tasks: CI Workflow Deadlock Prevention, Test Timeout Diagnostics, and Runner Concurrency Hardening

**Feature**: `008-ci-test-hang-prevention`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update dependency specifications and test configuration

- [x] T001 [P] Configure development and test dependencies (add `pytest-timeout>=2.3.1`, `python-docx>=1.1.0`, `markdown-it-py>=3.0.0`, `mdit-py-plugins>=0.4.0`) in `requirements-dev.txt`
- [x] T002 [P] Configure non-breaking test timeout default (`timeout = 30`) in `pytest.ini`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core safety fixtures preventing headless test hangs across all GUI test modules

**⚠️ CRITICAL**: Must complete before running GUI test suites under headless virtual displays

- [x] T003 Implement global autouse modal dialog mock fixture `_safe_gui_dialogs` in `tests/conftest.py` to intercept `tkinter.messagebox` and `tkinter.simpledialog` during headless execution

**Checkpoint**: Foundation ready — all GUI tests are immune to hanging on unmocked modal dialogs under `xvfb-run`.

---

## Phase 3: User Story 1 - CI Workflow Timeout & Branch Concurrency Cancellation (Priority: P1) 🎯 MVP

**Goal**: Prevent GitHub Actions runner starvation by enforcing 10-minute job limits and auto-cancelling stale workflow runs on branch updates.

**Independent Test**: Trigger concurrent pushes to the same branch; verify previous workflow run is cancelled immediately, and verify any job running past 10 minutes is automatically terminated.

### Implementation for User Story 1

- [x] T004 [US1] Configure unconditional workflow concurrency cancellation (`cancel-in-progress: true`) in `.github/workflows/ci.yml`
- [x] T005 [US1] Set job-level timeouts (`timeout-minutes: 10` on `test` job, `timeout-minutes: 5` on `lint` job) in `.github/workflows/ci.yml`

**Checkpoint**: User Story 1 complete. GitHub Actions runners will never hang for 6 hours or leave subsequent commits stalled in Pending queue.

---

## Phase 4: User Story 2 - Per-Test Watchdog Timeout & Traceback Diagnostics (Priority: P1) 🎯 MVP

**Goal**: Catch individual deadlocks and infinite loops within 30 seconds and dump an actionable thread traceback pointing to the exact line of code.

**Independent Test**: Run a test with a simulated sleep or loop using `--timeout=5`; verify pytest terminates at 5s with thread dump and continues the suite.

### Implementation for User Story 2

- [x] T006 [P] [US2] Add watchdog timeout parameter (`--timeout=30`) to Linux and Windows pytest steps in `.github/workflows/ci.yml`
- [x] T007 [P] [US2] Add extended timeout marker (`@pytest.mark.timeout(120)`) to the 50-word large-bank persistence benchmark in `tests/test_bank.py`
- [x] T008 [US2] Create watchdog timeout verification test in `tests/test_timeout_diagnostics.py`

**Checkpoint**: User Story 2 complete. Any infinite loop or deadlocked test is halted within 30 seconds with a diagnostic traceback.

---

## Phase 5: User Story 3 - Optional Dependency Collection Safety & CI Dependency Alignment (Priority: P1) 🎯 MVP

**Goal**: Prevent collection crashes (`ModuleNotFoundError: No module named 'docx'`) and ensure clean skips when optional packages are missing.

**Independent Test**: Run `pytest --collect-only` in an environment without `python-docx`; verify 0 collection errors and 100% clean skips.

### Implementation for User Story 3

- [x] T009 [P] [US3] Guard top-level docx imports with `pytest.importorskip("docx")` in `tests/test_docx_omml_diagnostics.py`
- [x] T010 [P] [US3] Add module-level `pytest.importorskip("docx")` in `tests/test_importer_docx.py`
- [x] T011 [P] [US3] Add module-level `pytest.importorskip` for `markdown_it` and `mdit_py_plugins` in `tests/test_importer_markdown.py`
- [x] T012 [P] [US3] Add function-level `pytest.importorskip("docx")` in `tests/test_gui_document.py`, `tests/test_table_merged_cells.py`, and `tests/test_cli_format.py`
- [x] T013 [US3] Convert `OptionalDependencyError` into `pytest.skip` inside test fixtures in `tests/test_importer_docx.py` and `tests/test_docx_omml_diagnostics.py`

**Checkpoint**: User Story 3 complete. Zero collection crashes occur regardless of installed packages.

---

## Phase 6: User Story 4 - Real-Time Streaming Test Verbosity in CI Logs (Priority: P2)

**Goal**: Stream live per-test names and stdout to the continuous integration console, eliminating silent execution buffers.

**Independent Test**: Run CI test step and observe live real-time output in GitHub Actions console logs.

### Implementation for User Story 4

- [x] T014 [US4] Update pytest CLI invocation flags from `-q` to `-vv -s` in `.github/workflows/ci.yml`

**Checkpoint**: User Story 4 complete. Developers can inspect test execution progress in real time.

---

## Phase 7: User Story 5 - Layout Engine, Pagination, and File Lock Bounded Termination Safety (Priority: P2)

**Goal**: Ensure document pagination and table layout algorithms guarantee monotonic vertical advancement and bounded loop iterations.

**Independent Test**: Run layout engine tests with degenerate inputs (table taller than page, empty blocks); verify bounded completion $< 5.0\text{s}$.

### Implementation for User Story 5

- [x] T015 [P] [US5] Audit and enforce monotonic cursor progress and bounded loops in `chuviettay/layout/engine.py`
- [x] T016 [P] [US5] Audit and enforce column padding and row height loop bounds in `chuviettay/layout/table_layout.py`
- [x] T017 [US5] Verify bounded timeout handling and exception semantics in `chuviettay/model/file_lock.py`

**Checkpoint**: User Story 5 complete. Layout algorithms have strict termination guarantees on degenerate inputs.

---

## Phase 8: User Story 6 - Headless GUI Virtual Display Modal Dialog Interception (Priority: P3)

**Goal**: Eliminate unmocked modal dialog popups in `tests/test_gui_document.py` that trigger xvfb hangs.

**Independent Test**: Trigger an error path in `test_gui_document.py` under xvfb; verify no modal event loop blocks and test completes cleanly.

### Implementation for User Story 6

- [x] T018 [P] [US6] Add explicit `Dialogs` mock fixture usage in `tests/test_gui_document.py`
- [x] T019 [US6] Add headless error handling verification test in `tests/test_gui_document.py`

**Checkpoint**: User Story 6 complete. All document GUI tests safely intercept modal popups.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates, verification runs, and final quality checks

- [x] T020 [P] Update documentation and release notes in `README.md` and `CHANGELOG.md`
- [x] T021 Run `quickstart.md` validation scenarios across local environment
- [x] T022 Execute full test suite locally with `py -3.12 -m pytest -vv -s --timeout=30`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all GUI and document tests.
- **User Stories (Phase 3–8)**:
  - User Story 1 (CI Timeout & Concurrency): Can proceed in parallel with US2/US3.
  - User Story 2 (Watchdog Timeout): Depends on Phase 1 (`requirements-dev.txt`).
  - User Story 3 (Collection Safety): Depends on Phase 1 (`requirements-dev.txt`).
  - User Story 4 (Verbosity): Depends on US1 (`ci.yml`).
  - User Story 5 (Layout Boundedness): Independent domain logic.
  - User Story 6 (GUI Document Mocking): Depends on Phase 2 (`conftest.py`).
- **Polish (Phase 9)**: Depends on all user stories being implemented.

### Parallel Opportunities

- **Phase 1**: T001 and T002 can execute in parallel.
- **Phase 4**: T006 and T007 can execute in parallel.
- **Phase 5**: T009, T010, T011, and T012 can all execute in parallel across different test files.
- **Phase 7**: T015 and T016 can execute in parallel.
- **Phase 8 & 9**: T018, T020 can execute in parallel.

---

## Implementation Strategy

### MVP First (Phases 1, 2, 3, 4, 5)

1. Complete Phase 1: Add `pytest-timeout`, `python-docx`, `markdown-it-py` to `requirements-dev.txt`.
2. Complete Phase 2: Add global headless dialog fixture in `tests/conftest.py`.
3. Complete Phase 3: Set `timeout-minutes: 10` and `cancel-in-progress: true` in `ci.yml`.
4. Complete Phase 4: Add `--timeout=30` watchdog to CI test invocations.
5. Complete Phase 5: Guard all optional imports with `pytest.importorskip` to fix collection crash.
6. **VALIDATE MVP**: Run `pytest --collect-only` and `pytest --timeout=30` locally and push to trigger clean CI.
