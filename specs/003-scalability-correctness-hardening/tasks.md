# Tasks: Scalability, Correctness, and CI Hardening

**Feature**: `003-scalability-correctness-hardening`
**Input**: Design artifacts from `specs/003-scalability-correctness-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)
**Status**: Ready for Implementation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish test configuration markers and CI workflow baseline

- [x] T001 Register `gui` custom marker in `pytest.ini`
- [x] T002 [P] Update CI workflow matrix in `.github/workflows/ci.yml` for Python 3.10, 3.11, 3.12, 3.13

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities and helper functions required across multiple user stories

- [x] T003 Implement session-level Tk runtime probe `is_tk_usable()` in `tests/conftest.py`
- [x] T004 [P] Implement `_sample_signature` helper incorporating stroke geometry and metadata in `chuviettay/model/bank.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Resilient Cross-Platform CI and Graphical Test Isolation (Priority: P1)

**Goal**: Ensure automated CI runs deterministically across all platforms, cleanly skipping GUI tests when Tcl/Tk is incomplete or missing, with zero unhandled `TclError` fixture errors.

**Independent Test**: Run `python -m pytest -q` in an environment where Tcl/Tk is uninstalled or incomplete; verify all core tests pass and GUI tests report clean skips with zero errors.

### Tests for User Story 1

- [x] T005 [P] [US1] Add unit tests for Tk runtime detection and skip handling in `tests/test_gui_resilience.py`

### Implementation for User Story 1

- [x] T006 [US1] Decorate GUI test modules with `@pytest.mark.gui` in `tests/test_gui.py` and `tests/test_word_canvas.py`
- [x] T007 [US1] Guard Tk initialization and widget creation in `tests/conftest.py` and `tests/test_gui.py` using `is_tk_usable()`
- [x] T008 [US1] Verify CI test runner steps for Windows and Linux in `.github/workflows/ci.yml`

**Checkpoint**: At this point, CI jobs on Windows 3.10 pass with zero unhandled TclErrors.

---

## Phase 4: User Story 2 - Incremental Indexing Parity and Raw Mark Preservation (Priority: P1)

**Goal**: Guarantee that incremental sample addition produces lookup indexes (`tl`, `marks`) mathematically identical to `rebuild()`, never permanently discarding raw tone marks during percentile filtering.

**Independent Test**: Incrementally teach 50 samples with tone marks into an empty bank; compare `marks`, `_raw_marks`, and `tl` against a bank populated with the same samples and refreshed with `rebuild()`; verify identical candidate sets and percentiles.

### Tests for User Story 2

- [x] T009 [P] [US2] Add unit tests for raw mark retention and rebuild equivalence in `tests/test_bank_indexing.py`

### Implementation for User Story 2

- [x] T010 [US2] Add `self._raw_marks` dictionary and initialize it in `rebuild()` in `chuviettay/model/bank.py`
- [x] T011 [US2] Refactor `_harvest()` to append to `_raw_marks` without dropping outliers in `chuviettay/model/bank.py`
- [x] T012 [US2] Implement `_refresh_tone_marks(T)` in `chuviettay/model/bank.py` to filter `marks[T]` dynamically from `_raw_marks[T]`
- [x] T013 [US2] Update `add_sample_incremental()` to append to `_raw_marks` and refresh `marks` in `chuviettay/model/bank.py`

**Checkpoint**: Incremental indexing produces 100% parity with `rebuild()`.

---

## Phase 5: User Story 3 - Persistent Deletion Tombstones and Cross-Process Deletion Safety (Priority: P1)

**Goal**: Ensure word deletions persist across concurrent multi-process saves by recording deletion tombstones, preventing older snapshots from resurrecting deleted words while permitting explicit re-teaching.

**Independent Test**: Simulate two concurrent processes where Process A deletes "xin" and saves, Process B adds a different word from an older snapshot and saves; verify "xin" remains deleted. Then explicitly re-teach "xin" and verify tombstone is revoked.

### Tests for User Story 3

- [x] T014 [P] [US3] Add unit tests for tombstone persistence and resurrection prevention in `tests/test_bank_tombstones.py`

### Implementation for User Story 3

- [x] T015 [US3] Initialize `self._tombstones` and `self._readded_words` in `Bank.__init__` in `chuviettay/model/bank.py`
- [x] T016 [US3] Update `Bank.drop()` to record deletion timestamp in `_tombstones` in `chuviettay/model/bank.py`
- [x] T017 [US3] Update `Bank.add_sample()` and `add_sample_incremental()` to clear `_tombstones` and record in `_readded_words` in `chuviettay/model/bank.py`
- [x] T018 [US3] Update `merge_bank_dicts()` to reconcile tombstones and honor `readded_words` in `chuviettay/model/bank.py`

**Checkpoint**: Cross-process deletions are durable and cannot be accidentally resurrected.

---

## Phase 6: User Story 4 - Scalable Persistence Architecture for Large Handwriting Profiles (Priority: P1)

**Goal**: Optimize `Bank.save()` with nanosecond mtime/size change-detection and faster compression, avoiding redundant disk re-reads, merges, and full rebuilds during interactive teaching sessions (`teach_word()`).

**Independent Test**: Measure execution time when teaching 20 consecutive words with tones via `teach_word()` into a pre-populated bank; verify total runtime is $< 1.0\text{s}$ (averaging $< 30\text{ms}$ per word).

### Tests for User Story 4

- [x] T019 [P] [US4] Add realistic sequential `teach_word()` benchmark test with tones in `tests/test_bank.py`

### Implementation for User Story 4

- [x] T020 [US4] Track `_last_synced_mtime_ns` and `_last_synced_size` in `Bank` in `chuviettay/model/bank.py`
- [x] T021 [US4] Implement fast-path cache validation in `Bank.save()` in `chuviettay/model/bank.py`
- [x] T022 [US4] Adjust gzip compression level to standard balance (`compresslevel=6`) in `Bank.save()` in `chuviettay/model/bank.py`

**Checkpoint**: Interactive word teaching persists each word with sub-second latency on large profiles.

---

## Phase 7: User Story 5 - Deep Schema Invariants for Tone Metadata and Pen Configuration (Priority: P2)

**Goal**: Enforce strict validation on tone diacritic invariants (`ti`, `vi`, `T`), pen rendering attributes (`tool`, hex `color`, `width`), and preserve backward compatibility by making `w` optional for punctuation (`punct`).

**Independent Test**: Attempt to load banks with invalid `ti >= len(s)`, mismatched `vi`, malformed pen hex color strings, and punctuation samples lacking `w`; verify invalid data is rejected and legacy punctuation is accepted.

### Tests for User Story 5

- [x] T023 [P] [US5] Add schema validation tests for tone invariants, punctuation without `w`, and pen config in `tests/test_schema.py`

### Implementation for User Story 5

- [x] T024 [US5] Update `validate_sample()` in `chuviettay/model/bank_schema.py` to make `w` optional for punctuation
- [x] T025 [US5] Add tone diacritic invariant validation (`ti`, `vi`, `T`) in `validate_sample()` in `chuviettay/model/bank_schema.py`
- [x] T026 [US5] Add pen configuration invariant validation (`tool`, hex `color`, `width`) in `validate_bank_dict()` in `chuviettay/model/bank_schema.py`
- [x] T027 [US5] Add optional `tombstones` validation in `validate_bank_dict()` in `chuviettay/model/bank_schema.py`

**Checkpoint**: 100% of invalid tone invariants and malformed pen configs are rejected at the boundary; legacy punctuation loads without error.

---

## Phase 8: User Story 6 - Explicit Sample Identity Contract for Multi-Process Merging (Priority: P2)

**Goal**: Unambiguously identify duplicate samples during cross-process merging based on both stroke geometry and sample metadata (`s, w, T, vi, ti`), preserving distinct variations.

**Independent Test**: Merge two banks where samples share identical stroke coordinates but have different widths or tone annotations; verify distinct samples are preserved.

### Tests for User Story 6

- [x] T028 [P] [US6] Add test for sample identity deduplication across stroke geometry and metadata in `tests/test_bank.py`

### Implementation for User Story 6

- [x] T029 [US6] Update deduplication in `merge_bank_dicts()` using full `_sample_signature` in `chuviettay/model/bank.py`

**Checkpoint**: Sample identity deduplication evaluates both geometry and metadata accurately.

---

## Phase 9: User Story 7 - Safe and Isolated Git History Purge Automation (Priority: P2)

**Goal**: Mandate external clone and standalone bundle backup in purge automation scripts before rewriting history with `git-filter-repo`.

**Independent Test**: Run `scripts/purge_git_history.ps1 -CheckOnly` and inspect script execution checks; verify external bundle creation and isolation requirements.

### Implementation for User Story 7

- [x] T030 [P] [US7] Update `scripts/purge_git_history.ps1` to create external bundle backup before filter-repo
- [x] T031 [P] [US7] Update `scripts/purge_git_history.sh` to mirror PowerShell external bundle safety

**Checkpoint**: Git history purge scripts enforce external backups and prevent accidental in-tree reference corruption.

---

## Phase 10: User Story 8 - CI Matrix Parity and Documentation Alignment (Priority: P3)

**Goal**: Align user documentation (`README.md`) with continuous integration configuration so claimed Python compatibility is verified by automated testing.

**Independent Test**: Verify that all Python versions advertised in `README.md` are actively represented in `.github/workflows/ci.yml`.

### Implementation for User Story 8

- [x] T032 [P] [US8] Update `README.md` to accurately document supported Python versions and CI status
- [x] T033 [P] [US8] Update `specs/003-scalability-correctness-hardening/quickstart.md` with final validation steps

**Checkpoint**: Documentation and CI configuration are 100% synchronized.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification, regression protection, and code hygiene

- [x] T034 Run full automated pytest suite across all test modules
- [x] T035 Verify golden-master regression tests continue to produce byte-exact outputs in `tests/test_writer.py`
- [x] T036 [P] Run code linter (`ruff check .`) and format check

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Stories.
- **User Stories (Phase 3 through Phase 10)**:
  - All depend on Phase 2 completion.
  - Can proceed sequentially in priority order (US1 → US2 → US3 → US4 → US5 → US6 → US7 → US8) or in parallel where independent files permit.
- **Polish (Phase 11)**: Depends on all user story phases being complete.

### User Story Dependencies

- **User Story 1 (P1 - CI Resilience)**: Independent of bank data structure changes. Can start immediately after Phase 2.
- **User Story 2 (P1 - Incremental Indexing)**: Operates on `Bank.rebuild` and `add_sample_incremental`.
- **User Story 3 (P1 - Deletion Tombstones)**: Operates on `Bank.drop`, `merge_bank_dicts`, and persistent metadata.
- **User Story 4 (P1 - Scalable Persistence)**: Operates on `Bank.save()` fast-path. Benefits from US2 indexing and US3 tombstones.
- **User Story 5 (P2 - Deep Schema Invariants)**: Operates on `bank_schema.py`. Independent of `Bank` runtime logic.
- **User Story 6 (P2 - Sample Identity Contract)**: Operates on `_sample_signature` in `bank.py`. Can integrate with US3.
- **User Story 7 (P2 - Safe Git Purge)**: Operates strictly on `scripts/purge_git_history.*`. Independent of application code.
- **User Story 8 (P3 - Documentation Alignment)**: Operates on `README.md` and `quickstart.md`.

---

## Parallel Opportunities

- All tasks marked `[P]` (different files, no conflicting dependencies) can be executed concurrently:
  - T002 (CI YAML) and T001 (pytest.ini) can run in parallel.
  - T004 (`_sample_signature`) and T003 (`is_tk_usable`) can run in parallel.
  - T005, T009, T014, T019, T023, T028 can be written in parallel as test files before implementation.
  - T030 (`.ps1`) and T031 (`.sh`) can run in parallel.
  - T032 (`README.md`) and T033 (`quickstart.md`) can run in parallel.

---

## Implementation Strategy

### MVP Scope (User Story 1 + User Story 2)
1. Complete Setup (Phase 1) + Foundational (Phase 2).
2. Implement User Story 1 (CI Resilience) → CI Windows 3.10 passes immediately.
3. Implement User Story 2 (Incremental Indexing Parity) → Incremental indexing matches rebuild 100%.
4. **VALIDATE MVP**: Run `pytest` on both Windows and Linux environments.

### Incremental Full Delivery
1. Add User Story 3 (Deletion Tombstones) → Cross-process deletion lost-update resolved.
2. Add User Story 4 (Scalable Persistence) → Sub-second save-per-word interactive teaching.
3. Add User Story 5 (Deep Schema Validation) → Malformed tone invariants rejected; legacy `punct` preserved.
4. Add User Story 6 (Sample Identity Contract) → Deduplication preserves distinct variations.
5. Add User Story 7 (Safe Git Purge) & User Story 8 (Documentation Parity).
6. Execute Final Phase (T034 - T036) for 100% test pass rate and golden-master verification.
