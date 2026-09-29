# Tasks: Concurrency Deep Safety and Scalability Hardening

**Feature**: `002-concurrency-deep-safety` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Setup (Shared Infrastructure & Environment Alignment)

**Purpose**: Dependency alignment and operational script scaffolding

- [x] T001 [P] Align dev dependencies with build tooling in [requirements-dev.txt](file:///d:/viet/app/requirements-dev.txt)
- [x] T002 [P] Scaffolding for PowerShell git history purge script in [scripts/purge_git_history.ps1](file:///d:/viet/app/scripts/purge_git_history.ps1)
- [x] T003 [P] Scaffolding for Bash git history purge script in [scripts/purge_git_history.sh](file:///d:/viet/app/scripts/purge_git_history.sh)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data structures and deduplication utilities required across user stories

**⚠️ CRITICAL**: Foundational utilities that MUST be completed before user stories

- [x] T004 Implement `_stroke_signature()` helper in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) for floating-point coordinate deduplication
- [x] T005 [P] Add `_deleted_words: set[str]` tracking in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) to prevent resurrection of dropped words during merge
- [x] T006 [P] Define `REQUIRED_METADATA_KEYS` and `DEFAULT_METRICS` in [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py)

**Checkpoint**: Core helpers ready — story implementation can proceed.

---

## Phase 3: User Story 1 - Concurrency Safety & Lost-Update Prevention Across Processes (Priority: P1) 🎯 MVP

**Goal**: Guarantee that concurrent saves across multiple processes (GUI + CLI) preserve all additions without lost updates.

**Independent Test**: Run `pytest tests/test_bank.py -k "test_concurrent_save"` verifying all 8 workers (`tu_0` through `tu_7`) exist in the final bank file.

### Tests for User Story 1
- [x] T007 [P] [US1] Strengthen concurrent save test in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py) to assert presence of all `tu_0`..`tu_7` in the final saved bank
- [x] T008 [P] [US1] Unit test for `merge_bank_dicts()` covering sample deduplication and deleted word suppression in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 1
- [x] T009 [US1] Implement `merge_bank_dicts()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) per [contracts/bank-concurrency.md](file:///d:/viet/app/specs/002-concurrency-deep-safety/contracts/bank-concurrency.md)
- [x] T010 [US1] Refactor `Bank.save()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) to perform disk reload-and-merge under `FileLock` before writing to temp file

**Checkpoint**: Concurrency test passes with 100% of tokens preserved; lost updates eliminated.

---

## Phase 4: User Story 2 - Deep Structural and Runtime Schema Validation (Priority: P1)

**Goal**: Validate stroke geometry (even parity, finite coordinates, min length 2) and all runtime typographic metadata fields.

**Independent Test**: Run `pytest tests/test_bank.py -k "test_deep_schema"` verifying invalid stroke lists and missing runtime keys raise `BankValidationError` naming the exact key and index.

### Tests for User Story 2
- [x] T011 [P] [US2] Unit tests for deep stroke coordinate validation (odd coordinate counts, NaNs, inf, empty strokes) in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)
- [x] T012 [P] [US2] Unit tests for runtime metadata validation and backward-compatible default migration in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 2
- [x] T013 [US2] Implement `validate_stroke()` and `validate_sample()` in [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py) per [contracts/deep-schema.md](file:///d:/viet/app/specs/002-concurrency-deep-safety/contracts/deep-schema.md)
- [x] T014 [US2] Update `validate_bank_dict()` in [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py) to enforce deep stroke rules and verify presence of required runtime metadata keys
- [x] T015 [US2] Update `migrate_bank_dict()` in [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py) to backfill missing runtime metadata keys with standard typographic defaults

**Checkpoint**: Malformed stroke coordinates and missing runtime metadata fail fast with clear path-level errors.

---

## Phase 5: User Story 3 - Reliable Packaging and Release Workflow Delivery (Priority: P1)

**Goal**: Fix the Linux release archive packaging step in GitHub Actions CI workflow so that release tags build cleanly without file-not-found errors.

**Independent Test**: Simulate Linux and Windows release archive commands in clean directory; verify output archive contains binary, `README.md`, and `LICENSE`.

### Implementation for User Story 3
- [x] T016 [US3] Update Linux release packaging step in [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml) to copy `README.md` and `LICENSE` to `dist/` before creating archive
- [x] T017 [US3] Update Windows release packaging step in [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml) to ensure consistent file inclusion

**Checkpoint**: CI release archive job builds distributable tarball/zip containing all required artifacts.

---

## Phase 6: User Story 4 - Consistent Atomic Persistence for New Bank Creation (Priority: P2)

**Goal**: Ensure `Bank.create_empty()` uses the exact same atomic write, file locking, and storage synchronization pipeline as `Bank.save()`.

**Independent Test**: Run `pytest tests/test_bank.py -k "test_create_empty_atomic"` verifying atomic replace and lock protection during creation.

### Tests for User Story 4
- [x] T018 [P] [US4] Unit test for `Bank.create_empty()` verifying atomic creation via temp file and lock acquisition in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 4
- [x] T019 [US4] Refactor `Bank.create_empty()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) to instantiate an in-memory bank and persist via `Bank.save()`

**Checkpoint**: Bank creation is uniform and fully protected against mid-write crashes or collisions.

---

## Phase 7: User Story 5 - Scalable Incremental Processing for Word Teaching (Priority: P2)

**Goal**: Implement $O(1)$ in-memory incremental index updates for `teach_word()`, eliminating full-dictionary re-indexing loops.

**Independent Test**: Run `pytest tests/test_bank.py -k "test_incremental_teach_performance"` verifying sequential teaching of 50 words completes in < 1.0s.

### Tests for User Story 5
- [x] T020 [P] [US5] Performance and correctness test for incremental sample teaching in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 5
- [x] T021 [US5] Implement `add_sample_incremental()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) updating `self.words`, `self.tl`, and `self.marks` incrementally per [contracts/incremental-indexing.md](file:///d:/viet/app/specs/002-concurrency-deep-safety/contracts/incremental-indexing.md)
- [x] T022 [US5] Update `teach_word()` in [chuviettay/controller/app_controller.py](file:///d:/viet/app/chuviettay/controller/app_controller.py) to call `bank.add_sample_incremental()` followed by `bank.save()`

**Checkpoint**: Word teaching scales smoothly with dataset size; sequential word teaching performance verified.

---

## Phase 8: User Story 6 - Resilient Logging Fallback and Accurate Documentation (Priority: P2)

**Goal**: Return `None` from `log_path()` when all file logging fails, and bring user documentation into 100% alignment with current project requirements.

**Independent Test**: Simulate unwritable primary and user directories; verify `log_path()` returns `None` and UI dialogue indicates logging is inactive. Verify README and Quickstart reflect `Python 3.10+` and zero external dependencies.

### Tests for User Story 6
- [x] T023 [P] [US6] Unit test for total file logging failure returning `None` in [tests/test_logging.py](file:///d:/viet/app/tests/test_logging.py)

### Implementation for User Story 6
- [x] T024 [US6] Update `configure_logging()` and `log_path()` in [chuviettay/logging_setup.py](file:///d:/viet/app/chuviettay/logging_setup.py) to return `None` when all file handlers fail
- [x] T025 [US6] Update error dialogue handler in [chuviettay/view/app_window.py](file:///d:/viet/app/chuviettay/view/app_window.py) to display inactive logging notice when `log_path()` is `None`
- [x] T026 [P] [US6] Update [README.md](file:///d:/viet/app/README.md) to specify `Python 3.10+`, remove bundled `hw_gui-linux` binary mention, and document GitHub Releases
- [x] T027 [P] [US6] Update quickstart guides across documentation to remove obsolete `filelock` installation references

**Checkpoint**: Ghost log paths eliminated; user documentation is accurate and consistent.

---

## Phase 9: User Story 7 - Complete Git History Purge of Sensitive Biometric Blobs (Priority: P0 / Operational)

**Goal**: Provide standalone, safe automation scripts to purge historical personal handwriting data blobs from version control history.

**Independent Test**: Execute `scripts/purge_git_history.ps1 -CheckOnly` verifying pre-flight checks and blob detection without altering repository state.

### Implementation for User Story 7
- [x] T028 [US7] Implement [scripts/purge_git_history.ps1](file:///d:/viet/app/scripts/purge_git_history.ps1) with worktree cleanliness check, backup branch creation, and `git-filter-repo` execution
- [x] T029 [US7] Implement [scripts/purge_git_history.sh](file:///d:/viet/app/scripts/purge_git_history.sh) with worktree cleanliness check, backup branch creation, and `git-filter-repo` execution

**Checkpoint**: Standalone history purge scripts ready for maintainer execution before public repository exposure.

---

## Phase 10: Polish & Cross-Cutting Verification

**Purpose**: Complete end-to-end regression validation, architecture boundaries, and code quality

- [x] T030 [P] Run full test suite with `pytest` verifying all tests pass cleanly
- [x] T031 [P] Verify 4/4 golden-master tests produce exact SHA-256 byte matches in [tests/test_golden_master.py](file:///d:/viet/app/tests/test_golden_master.py)
- [x] T032 [P] Verify AST boundary rules in [tests/test_architecture.py](file:///d:/viet/app/tests/test_architecture.py) ensuring `view/` has zero direct access to `.bank`
- [x] T033 Execute end-to-end validation scenarios in [quickstart.md](file:///d:/viet/app/specs/002-concurrency-deep-safety/quickstart.md)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────┐
                             ▼
Phase 2: Foundational ───────┼──────────┬──────────┬──────────┐
                             ▼          ▼          ▼          ▼
                          Phase 3    Phase 4    Phase 5    Phase 6
                          (US1:P1)   (US2:P1)   (US3:P1)   (US4:P2)
                             │          │          │          │
                             └──────────┼──────────┴──────────┘
                                        ▼
                                     Phase 7 (US5: Scale)
                                     Phase 8 (US6: Log/Doc)
                                     Phase 9 (US7: Purge)
                                        │
                                        ▼
                                     Phase 10: Polish & Gates
```

### User Story Dependencies

- **US1 (Concurrency)**: Depends on T004 (`_stroke_signature`) and T005 (`_deleted_words`).
- **US2 (Deep Schema)**: Depends on T006 (`REQUIRED_METADATA_KEYS`).
- **US3 (Packaging)**: Independent; modifies CI workflow only.
- **US4 (Bank Creation)**: Depends on US1 completion so `save()` reload-and-merge is active.
- **US5 (Incremental Indexing)**: Depends on US1 completion for underlying bank persistence.
- **US6 (Logging & Docs)**: Independent of bank logic.
- **US7 (Git Purge Script)**: Independent operational utility.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (dependencies)
2. Complete Phase 2: Foundational (deduplication & deletion tracking)
3. Complete Phase 3: User Story 1 (reload-and-merge under FileLock)
4. **STOP and VALIDATE**: Run `pytest tests/test_bank.py -k "test_concurrent_save"` — verify all 8 workers survive.

### Incremental Delivery
1. Setup + Foundational → Core helpers active
2. US1 → Concurrency lost updates eliminated (MVP!)
3. US2 → Deep schema validation active
4. US3 → GitHub Actions Linux release archive fixed
5. US4 → Bank creation persistence made atomic
6. US5 → Incremental indexing active for fast word teaching
7. US6 → Logging fallback `None` contract & documentation synchronized
8. US7 → Git history purge scripts ready
9. Polish → 100% test pass, golden-master verified, AST checks pass
