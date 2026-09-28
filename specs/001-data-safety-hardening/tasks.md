# Tasks: Data Safety and Core Reliability Hardening

**Feature**: `001-data-safety-hardening` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Setup (Shared Infrastructure & Git Hygiene)

**Purpose**: Repository configuration, metadata, and git hygiene baseline

- [x] T001 Update [.gitignore](file:///d:/viet/app/.gitignore) to uncomment `chu_cua_ban.json.gz`, add `*.lock`, `hw_gui-linux`, and `hw_gui.exe`
- [x] T002 [P] Untrack personal profile `chu_cua_ban.json.gz` from git index via `git rm --cached` while preserving the file locally
- [x] T003 [P] Remove pre-built binary artifact [hw_gui-linux](file:///d:/viet/app/hw_gui-linux) from git tracking via `git rm`
- [x] T004 [P] Create [LICENSE](file:///d:/viet/app/LICENSE) file with MIT License for software and open usage terms
- [x] T005 [P] Create [pyproject.toml](file:///d:/viet/app/pyproject.toml) declaring project metadata, `requires-python = ">=3.10"`, entry points, and dev dependencies
- [x] T006 [P] Create [requirements-build.txt](file:///d:/viet/app/requirements-build.txt) with pinned PyInstaller packaging dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core validation and locking utilities that MUST be complete before user stories can be implemented

**⚠️ CRITICAL**: Foundational modules required across multiple stories

- [x] T007 Implement zero-dependency cross-platform file locking in [chuviettay/model/file_lock.py](file:///d:/viet/app/chuviettay/model/file_lock.py) using `msvcrt` (Windows) and `fcntl` (POSIX)
- [x] T008 [P] Implement schema validation, error hierarchy, and migration chain in [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py) per [contracts/bank-schema.md](file:///d:/viet/app/specs/001-data-safety-hardening/contracts/bank-schema.md)
- [x] T009 [P] Add `has_bank` property on `AppController` in [chuviettay/controller/app_controller.py](file:///d:/viet/app/chuviettay/controller/app_controller.py) to encapsulate Model access
- [x] T010 [P] Create synthetic benchmark generator script in [scripts/gen_synthetic_bank.py](file:///d:/viet/app/scripts/gen_synthetic_bank.py) to reproducibly create non-personal test fixtures

**Checkpoint**: Core locking, schema validation, and synthetic generator ready — story implementation can proceed.

---

## Phase 3: User Story 1 - Protection of Personal Handwriting Data & Isolated Test Fixtures (Priority: P1) 🎯 MVP

**Goal**: Ensure automated test suite runs completely isolated from personal handwriting data, using reproducible synthetic fixtures.

**Independent Test**: Run `pytest tests/test_bank.py tests/test_gui.py` verifying tests pass using only synthetic benchmark data, with zero dependency on personal user banks.

### Tests for User Story 1
- [x] T011 [P] [US1] Unit test for synthetic fixture integrity and tone coverage in [tests/test_synthetic_bank.py](file:///d:/viet/app/tests/test_synthetic_bank.py)

### Implementation for User Story 1
- [x] T012 [US1] Generate synthetic test fixture [tests/data/kho_mau_tong_hop.json.gz](file:///d:/viet/app/tests/data/kho_mau_tong_hop.json.gz) using [scripts/gen_synthetic_bank.py](file:///d:/viet/app/scripts/gen_synthetic_bank.py)
- [x] T013 [US1] Remove personal test fixture `tests/data/kho_mau_chup_lai.json.gz` from git tracking
- [x] T014 [US1] Update [tests/conftest.py](file:///d:/viet/app/tests/conftest.py) to point `real_bank_path` to the new synthetic benchmark fixture
- [x] T015 [US1] Update assertions in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py) to assert against synthetic fixture metrics instead of hardcoded 362/859 counts
- [x] T016 [US1] Update assertions in [tests/test_gui.py](file:///d:/viet/app/tests/test_gui.py) to reflect synthetic fixture statistics

**Checkpoint**: Personal data is 100% untracked; tests run cleanly on synthetic data alone.

---

## Phase 4: User Story 2 - Safe Bank Loading without Unintended Creation on Typo (Priority: P1)

**Goal**: Prevent GUI and CLI from silently creating a blank bank when the user types an invalid or misspelled `--bank` path.

**Independent Test**: Pass a non-existent file path to `MainWindow` and `gui.py`; verify error dialog is shown and no file is created on disk.

### Tests for User Story 2
- [x] T017 [P] [US2] Integration test verifying explicit missing `--bank` path raises error without creating file in [tests/test_gui.py](file:///d:/viet/app/tests/test_gui.py)

### Implementation for User Story 2
- [x] T018 [US2] Update `MainWindow.__init__` in [chuviettay/view/app_window.py](file:///d:/viet/app/chuviettay/view/app_window.py) to accept `create_if_missing: bool = False` parameter
- [x] T019 [US2] Update `main()` in [chuviettay/gui.py](file:///d:/viet/app/chuviettay/gui.py) to pass `create_if_missing=(args.bank is None)` to `MainWindow`

**Checkpoint**: Typo in `--bank` displays error notification; default bank creation only allowed when no custom path is provided.

---

## Phase 5: User Story 3 - Data Schema Integrity and Backward-Compatible Migration (Priority: P1)

**Goal**: Validate bank dictionary structure on load, reject corrupted or future-version files, and seamlessly migrate legacy v1 banks in memory.

**Independent Test**: Load corrupted gzip, invalid JSON, missing keys, future schema version, and legacy v1 banks; verify appropriate `BankError` subclasses are raised or clean in-memory migration occurs.

### Tests for User Story 3
- [x] T020 [P] [US3] Unit tests for bank corruption (0 bytes, bad gzip, invalid JSON, missing keys) in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)
- [x] T021 [P] [US3] Unit tests for schema version migration (v1 to v2) and unsupported version rejection in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 3
- [x] T022 [US3] Integrate `_load_and_validate()` from [chuviettay/model/bank_schema.py](file:///d:/viet/app/chuviettay/model/bank_schema.py) into `Bank.__init__()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py)
- [x] T023 [US3] Update `Bank.empty_dict()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) to include `"schema_version": 2`
- [x] T024 [US3] Re-export bank exception classes (`BankError`, `BankValidationError`, `BankCorruptedError`) in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py)
- [x] T025 [US3] Catch `BankError` hierarchy in [chuviettay/cli.py](file:///d:/viet/app/chuviettay/cli.py) to report clean user-facing error messages

**Checkpoint**: Corrupted banks fail fast with human-readable errors; legacy banks migrate seamlessly in memory.

---

## Phase 6: User Story 4 - Reliable Concurrent Saving and Write Durability (Priority: P1)

**Goal**: Protect bank saving operations against concurrent write collisions and disk write caching failures using process-unique temporary files, file locking, and `fsync`.

**Independent Test**: Execute concurrent simulated saves across multiple processes/threads; verify zero file corruption and that saved files are committed to disk.

### Tests for User Story 4
- [x] T026 [P] [US4] Unit test for file lock acquire/release and timeout behavior in [tests/test_file_lock.py](file:///d:/viet/app/tests/test_file_lock.py)
- [x] T027 [P] [US4] Integration test for concurrent bank save operations in [tests/test_bank.py](file:///d:/viet/app/tests/test_bank.py)

### Implementation for User Story 4
- [x] T028 [US4] Refactor `Bank.save()` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py) to use `FileLock` context manager with `{path}.lock`
- [x] T029 [US4] Implement process-unique temp file naming via `tempfile.mkstemp` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py)
- [x] T030 [US4] Implement full buffer flush and `os.fsync` on the raw file descriptor, closing all descriptors before calling `os.replace` in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py)
- [x] T031 [US4] Add POSIX parent directory fsync handling with Windows exception safety in [chuviettay/model/bank.py](file:///d:/viet/app/chuviettay/model/bank.py)

**Checkpoint**: Simultaneous saves serialize cleanly; temp files never collide; files are flushed to disk before replacement.

---

## Phase 7: User Story 5 - Comprehensive Input Validation for Writing and Rendering Options (Priority: P1)

**Goal**: Centralize and enforce strict business validation for all write options (numeric boundaries, NaN/inf rejection, strict `#RRGGBB[AA]` color format) across CLI and GUI.

**Independent Test**: Pass invalid write options (scale=-5, width=inf, color='bad') to `WriteOptions.validate()`, CLI, and GUI; verify `ValueError` is raised before document composition.

### Tests for User Story 5
- [x] T032 [P] [US5] Unit tests for `WriteOptions.validate()` (positive values, NaN, infinity, negatives) in [tests/test_composer.py](file:///d:/viet/app/tests/test_composer.py)
- [x] T033 [P] [US5] Unit tests for hex color validation and XML safety in [tests/test_composer.py](file:///d:/viet/app/tests/test_composer.py)

### Implementation for User Story 5
- [x] T034 [US5] Implement `validate()` method on `WriteOptions` in [chuviettay/model/composer.py](file:///d:/viet/app/chuviettay/model/composer.py) per [contracts/write-options.md](file:///d:/viet/app/specs/001-data-safety-hardening/contracts/write-options.md)
- [x] T035 [US5] Implement `parse_color()` validation utility in [chuviettay/model/composer.py](file:///d:/viet/app/chuviettay/model/composer.py)
- [x] T036 [US5] Call `opts.validate()` at start of `AppController.write_text()` in [chuviettay/controller/app_controller.py](file:///d:/viet/app/chuviettay/controller/app_controller.py)
- [x] T037 [US5] Call `opts.validate()` in `read_options()` in [chuviettay/view/write_tab.py](file:///d:/viet/app/chuviettay/view/write_tab.py) to catch invalid input at GUI level

**Checkpoint**: Invalid options and malformed colors are rejected early, protecting XOPP XML output.

---

## Phase 8: User Story 6 - Continuous Quality Assurance via Automated CI Workflows (Priority: P2)

**Goal**: Run automated tests, compilation checks, and release builds via GitHub Actions on Ubuntu and Windows.

**Independent Test**: Trigger workflow or validate workflow configuration; confirm matrix tests run with `xvfb-run` on Linux and native desktop on Windows.

### Implementation for User Story 6
- [x] T038 [US6] Create GitHub Actions workflow [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml) with matrix `{ubuntu-latest, windows-latest} × {3.10, 3.12}`
- [x] T039 [US6] Configure `xvfb-run` for headless Tkinter test execution on Linux in [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml)
- [x] T040 [US6] Configure `python -m compileall -q .` syntax verification step in [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml)
- [x] T041 [US6] Add gated release packaging job for tag pushes in [.github/workflows/ci.yml](file:///d:/viet/app/.github/workflows/ci.yml)

**Checkpoint**: CI runs automatically on push and pull requests; release job packages binaries on tags.

---

## Phase 9: User Story 7 - Reproducible Build Pipeline and Standardized Packaging (Priority: P2)

**Goal**: Standardize packaging scripts to use reproducible virtual environments with pinned dependencies.

**Independent Test**: Run build script in clean environment; verify executable is generated from pinned dependencies.

### Implementation for User Story 7
- [x] T042 [US7] Update [build_windows.bat](file:///d:/viet/app/build_windows.bat) to use `requirements-build.txt` with pinned PyInstaller
- [x] T043 [US7] Update [build_linux_mac.sh](file:///d:/viet/app/build_linux_mac.sh) to use `requirements-build.txt` with pinned PyInstaller

**Checkpoint**: Builds are reproducible and decoupled from the developer's global Python environment.

---

## Phase 10: User Story 8 - Resilient Logging with User-Writable Storage Fallbacks (Priority: P3)

**Goal**: Provide resilient log file storage that falls back to OS user data directories (`%LOCALAPPDATA%`, `~/.local/state/`) when the application directory is read-only.

**Independent Test**: Simulate non-writable application base directory; verify logs are written to fallback location and `log_path()` reflects actual path.

### Tests for User Story 8
- [x] T044 [P] [US8] Unit test for logging fallback when primary directory is unwritable in [tests/test_logging.py](file:///d:/viet/app/tests/test_logging.py)

### Implementation for User Story 8
- [x] T045 [US8] Add platform-aware `user_log_dir()` helper in [chuviettay/paths.py](file:///d:/viet/app/chuviettay/paths.py)
- [x] T046 [US8] Update `configure_logging()` in [chuviettay/logging_setup.py](file:///d:/viet/app/chuviettay/logging_setup.py) to catch `OSError` on primary handler and fall back to `user_log_dir()`
- [x] T047 [US8] Update `log_path()` in [chuviettay/logging_setup.py](file:///d:/viet/app/chuviettay/logging_setup.py) to return the actual active log file path

**Checkpoint**: Application logs reliably even in read-only directories; error dialogs report real log path.

---

## Phase 11: Polish, Quality Gates & Architectural Enforcement

**Purpose**: Strengthen test assertions, enforce strict architectural boundaries, and run end-to-end verification.

- [x] T048 [P] Fix and strengthen `test_jitter_0_thi_khong_con_ngau_nhien_ve_hinh_dang` in [tests/test_composer.py](file:///d:/viet/app/tests/test_composer.py) by testing a single-sample bank where `strip(a) == strip(b)`
- [x] T049 [P] Update [chuviettay/view/app_window.py](file:///d:/viet/app/chuviettay/view/app_window.py) to replace `self.ctl.bank is None` with `not self.ctl.has_bank`
- [x] T050 Add AST rule in [tests/test_architecture.py](file:///d:/viet/app/tests/test_architecture.py) forbidding any file in `chuviettay/view/` from accessing `.bank` attribute
- [x] T051 [P] Verify 100% pass of golden-master regression tests in [tests/test_golden_master.py](file:///d:/viet/app/tests/test_golden_master.py)
- [x] T052 Execute all scenarios in [quickstart.md](file:///d:/viet/app/specs/001-data-safety-hardening/quickstart.md) and verify complete suite passes cleanly

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────┐
                             ▼
Phase 2: Foundational ───────┼──────────┬──────────┬──────────┬──────────┐
                             ▼          ▼          ▼          ▼          ▼
                          Phase 3    Phase 4    Phase 5    Phase 6    Phase 7
                          (US1:P1)   (US2:P1)   (US3:P1)   (US4:P1)   (US5:P1)
                             │          │          │          │          │
                             └──────────┴──────────┴──────────┴──────────┘
                                                   │
                                                   ▼
                                         Phase 8 (US6: CI)
                                         Phase 9 (US7: Build)
                                         Phase 10 (US8: Logging)
                                                   │
                                                   ▼
                                         Phase 11: Polish & Gates
```

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS all user stories.
- **User Stories 1-5 (P1)**: All depend on Foundational phase. Can be executed sequentially or in parallel.
- **User Stories 6-8 (P2/P3)**: Depend on core story completion.
- **Polish (Phase 11)**: Final phase verifying all architectural gates and golden-master fidelity.

### User Story Dependencies

- **US1 (Personal Data Isolation)**: Depends on T010 (synthetic generator). Unblocks clean test execution.
- **US2 (Typo Safety)**: Depends on T009 (`has_bank`). Independent of other stories.
- **US3 (Schema Validation)**: Depends on T008 (`bank_schema.py`). Integrates with `Bank.__init__`.
- **US4 (Persistence & Locking)**: Depends on T007 (`file_lock.py`). Integrates with `Bank.save()`.
- **US5 (WriteOptions Validation)**: Independent of other stories; self-contained in `composer.py`.
- **US6 (CI Workflows)**: Runs best after US1-US5 are complete so CI has passing tests.
- **US7 (Build Reproducibility)**: Depends on T005, T006.
- **US8 (Logging Fallback)**: Independent of bank operations.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004, T005, T006 can all run in parallel.
- **Phase 2**: T007, T008, T009, T010 can all be developed in parallel.
- **Within User Stories**: Test tasks marked `[P]` can be authored in parallel with or before implementation tasks.
- **Across Stories**: Once Phase 2 is complete, US1 through US5 can be developed in parallel across different files.

---

## Parallel Example: User Story 3 & 4

```bash
# Developer A working on US3 (Schema Validation):
Task: "T020 [P] [US3] Unit tests for bank corruption in tests/test_bank.py"
Task: "T022 [US3] Integrate _load_and_validate() in chuviettay/model/bank.py"

# Developer B working on US4 (Locking & Persistence):
Task: "T026 [P] [US4] Unit test for file lock in tests/test_file_lock.py"
Task: "T028 [US4] Refactor Bank.save() to use FileLock in chuviettay/model/bank.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (git hygiene, pyproject.toml)
2. Complete Phase 2: Foundational (locking, schema, generator)
3. Complete Phase 3: User Story 1 (replace personal data with synthetic benchmark fixture)
4. **STOP and VALIDATE**: Run `pytest tests/test_bank.py` — verify 0 personal data referenced.

### Incremental Delivery
1. Setup + Foundational → Repository baseline clean
2. US1 → Personal data safe & test fixtures isolated (MVP!)
3. US2 → Typo protection active in GUI
4. US3 → Bank schema validation & legacy migration active
5. US4 → Atomic saving with cross-platform file locking active
6. US5 → Input & color validation active
7. US6 + US7 → CI/CD pipeline and reproducible builds active
8. US8 → Resilient logging active
9. Polish → AST boundary check & golden-master 100% verified
