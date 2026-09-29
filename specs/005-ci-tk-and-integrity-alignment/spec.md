# Feature Specification: CI Environment Hardening, Tk/Tcl Probing, and Data Integrity Alignment

**Feature Branch**: `005-ci-tk-and-integrity-alignment`

**Created**: 2026-09-29

**Status**: Implemented

**Input**: User audit and feedback on commit `c5d7b6d4c781503e2d027a2872a882f0c688e30f` (CI run 36556305255):
1. P1: Robust Tk/Tcl runtime probing in `tests/conftest.py` to prevent false-negative evaluation (e.g. Windows Python 3.11 missing `listbox.tcl` causing `MainWindow` crashes during collection or execution) and ensure headless/broken Tk environments skip cleanly.
2. P2: Synchronize and clarify tombstone conflict resolution semantics (generation metadata vs operational timestamps) across codebase and documentation, eliminating over-claimed distributed consensus.
3. P2: Reconcile large-bank persistence benchmark between specification and test implementation to sequentially teach and save 50 words on $\ge 5,000$ samples.
4. P2: Operational execution of git history purge script (`scripts/purge_git_history.ps1` / `.sh`) with backup bundle creation to sanitize historical commits (`5a25e92`, `621c013`), leaving remote mirror push as explicit manual guidance.
5. P3: Refine `Bank.drop()` to return 0 immediately on non-existent words without creating dead tombstones or incrementing generation.
6. P3: Strengthen `pen.color` schema validation using `re.fullmatch()`.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comprehensive Tk/Tcl Runtime Verification & Clean CI Skipping (Priority: P1)

As a developer and CI engineer running tests across multiple operating systems and Python versions (Ubuntu/Windows × Python 3.10–3.13), I want the test harness to perform a deep, non-destructive probe of the Tk/Tcl runtime (including core script files like `init.tcl`, `tk.tcl`, `listbox.tcl`) before running GUI tests, so that incomplete or broken Tk installations (such as Windows Python 3.11 missing widget scripts) skip GUI tests cleanly without causing unhandled `TclError` crashes.

**Why this priority**: In CI run 36556305255, 7 of 8 test matrix jobs passed, but Windows Python 3.11 failed due to a missing `listbox.tcl` when initializing `MainWindow` in `test_khoi_dong_voi_duong_dan_bank_sai_khong_tu_tao_file`. The existing probe created dummy widgets without verifying the script loading lifecycle, yielding a false-negative that allowed tests to execute and fail.

**Independent Test**: Simulate an environment where Tk exists but widget library files (`listbox.tcl`) are missing or unreadable; run `pytest tests/test_gui.py`; verify that all GUI tests are cleanly skipped with an informative reason rather than terminating with an unhandled exception.

**Acceptance Scenarios**:
1. **Given** an environment where Tcl/Tk is missing, uninitialized, or missing critical library scripts (`listbox.tcl`, `tk.tcl`), **When** `conftest.is_tk_usable()` is evaluated, **Then** it returns `False` and records a detailed diagnostic reason.
2. **Given** `conftest.is_tk_usable()` returns `False`, **When** `pytest` runs across the entire test suite, **Then** all tests marked with `gui` or calling `tk_root` or `MainWindow` are skipped with `SKIPPED`, resulting in 100% test run success (0 failed).
3. **Given** any test directly instantiating `MainWindow` (e.g. `test_khoi_dong_voi_duong_dan_bank_sai_khong_tu_tao_file`), **When** executed, **Then** it is protected by the Tk usability guard and safely skips if runtime initialization fails.

---

### User Story 2 - Reconciled 50-Word Large-Bank Persistence Benchmark (Priority: P2)

As a system performance tester, I want the large-bank persistence benchmark test to execute 50 sequential `add_sample_incremental()` + `save()` operations on a profile with $\ge 5,000$ samples, so that test assertions strictly match the specification's acceptance criteria (SC-004) and prove sub-second latency under sustained interactive usage.

**Why this priority**: The previous implementation tested only 20 sequential additions due to a mismatch between task definitions and specification success criterion SC-004. Aligning test execution to 50 operations provides empirical proof of sustained sub-second performance.

**Independent Test**: Execute `pytest tests/test_bank.py -k "benchmark_large" -v -s`; verify that 50 consecutive word teaching and saving cycles complete on a $\ge 5,000$ sample profile with average per-word latency $< 1.0\text{s}$ and total elapsed time $< 30.0\text{s}$.

**Acceptance Scenarios**:
1. **Given** a synthetic handwriting bank populated with $\ge 5,000$ samples, **When** teaching and saving 50 consecutive words, **Then** the average per-operation latency is $< 1.0\text{s}$ and the maximum single latency is $< 2.0\text{s}$.
2. **Given** the completion of 50 saves, **When** reloaded from disk, **Then** all 50 added samples are present, uncorrupted, and verified by schema validation.

---

### User Story 3 - Transparent Conflict Resolution Semantics & Clean Non-Existent Drop (Priority: P2)

As an API consumer and contributor, I want the documentation, API docstrings, and implementation of `Bank` mutation tracking to accurately reflect its hybrid timestamped-tombstone architecture with generation counters, and I want `Bank.drop()` on non-existent words to safely no-op without creating dead tombstones or incrementing generation, so that model state remains concise and maintainable.

**Why this priority**: The documentation previously over-claimed "generation-based conflict resolution" when actual cross-process reconciliation relies on operational timestamps (`deleted_at`, `readded_at`) with generation serving as sequential mutation metadata. Furthermore, dropping a word that never existed currently pollutes `_tombstones` and increments generation needlessly.

**Independent Test**: Call `bank.drop("non_existent_word")`; verify that the method returns 0, `self._tombstones` does not gain a record, and `self._generation` is unchanged. Review documentation (`README.md`, `CHANGELOG.md`) to confirm alignment with actual conflict resolution semantics.

**Acceptance Scenarios**:
1. **Given** a bank instance, **When** `bank.drop("foo")` is called where "foo" does not exist in `self.words`, **Then** the method returns `0`, `self._tombstones` remains unchanged, and `self._generation` is not incremented.
2. **Given** `README.md` and `CHANGELOG.md`, **When** reviewed, **Then** the concurrency architecture is accurately described as cross-process atomic file locking with timestamped tombstone reconciliation and monotonic generation metadata.

---

### User Story 4 - Repository Git History Purge Execution (Priority: P2 / Operational)

As a repository maintainer, I want the git history purge process to be executed on the local repository (after creating a complete external backup bundle) to purge blobs `chu_cua_ban.json.gz` and `tests/data/kho_mau_chup_lai.json.gz` from historical commits (`5a25e92`, `621c013`), so that historical repository storage is sanitized while remote force-push remains documented for manual authorization.

**Why this priority**: The purge automation scripts were created and validated in feature 004, but historical commits still contain large personal handwriting blobs. Performing the local purge sanitizes the local repository history and leaves clear instructions for remote synchronization.

**Independent Test**: Run `scripts/purge_git_history.ps1 -CheckOnly`; execute the purge; query `git log --all -- "chu_cua_ban.json.gz"`; verify zero historical commits contain the purged blobs.

**Acceptance Scenarios**:
1. **Given** the local repository clone, **When** the purge script is executed, **Then** a full bundle backup (`repo-backup-*.bundle`) is created outside or before rewriting, and `git-filter-repo` (or equivalent filter-branch) removes all references to the sensitive blobs across all historical commits.
2. **Given** completion of local history rewriting, **When** checked, **Then** `git log --all` contains zero references to the sensitive files, and the working tree remains 100% clean and functional.

---

### User Story 5 - Schema Validation Hardening (Priority: P3)

As a developer enforcing data integrity, I want `validate_bank_dict()` to use exact pattern matching (`re.fullmatch()`) for `pen.color`, so that malformed color strings with trailing invalid characters are strictly rejected.

**Why this priority**: `re.match()` matches from the beginning of the string; although the pattern had a trailing `$`, using `re.fullmatch()` provides clearer intent and prevents potential edge-case matching bugs across Python versions.

**Independent Test**: Pass `pen.color = "#000000ff\nextra"`; verify `validate_bank_dict()` raises `BankValidationError`.

**Acceptance Scenarios**:
1. **Given** a bank dictionary with `pen.color`, **When** validated by `validate_bank_dict()`, **Then** `re.fullmatch()` validates that the color is strictly `#RRGGBB` or `#RRGGBBAA`.

---

## Edge Cases

- **What happens if a system has Python installed with Tkinter, but the Tcl script directory is completely empty or missing required widgets?**
  `conftest.is_tk_usable()` evaluates both widget creation and Tcl script sourcing (`listbox.tcl`, `ttk` theme initialization), catching `TclError` and marking the environment unusable.
- **What happens if `test_khoi_dong_voi_duong_dan_bank_sai_khong_tu_tao_file` is run individually via `pytest -k`?**
  The test is guarded by `pytestmark = [pytest.mark.gui]` at module level AND an explicit `conftest.is_tk_usable()` check, ensuring it skips cleanly even when invoked in isolation.
- **What happens if `bank.drop(word)` is called for a word that was previously dropped in the current session?**
  `count = len(self.words.pop(word, []))` is 0; it returns 0 and does not re-increment generation or alter the existing tombstone.
- **What happens if the git purge script encounters active uncommitted changes?**
  The script aborts immediately and demands a clean working tree before proceeding.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In `tests/conftest.py`, `is_tk_usable()` MUST perform a deep runtime probe that verifies critical Tcl script sourcing (including `init.tcl`, `tk.tcl`, `listbox.tcl`) and widget rendering, returning `False` on any failure.
- **FR-002**: In `tests/test_gui.py`, all test functions and fixtures MUST be guarded so that any failure in `MainWindow` instantiation due to Tk/Tcl environment failure skips gracefully instead of failing the test suite.
- **FR-003**: In `tests/test_bank.py`, the benchmark test `test_large_bank_persistence_benchmark_5000_samples` MUST execute 50 consecutive interactive saves on a bank with $\ge 5,000$ samples, asserting average latency $< 1.0\text{s}$ and total runtime $< 30.0\text{s}$.
- **FR-004**: In `chuviettay/model/bank.py`, `Bank.drop(word)` MUST check if `word` exists in `self.words` before incrementing `self._generation` or recording a tombstone, returning 0 immediately if the word is absent.
- **FR-005**: In `chuviettay/model/bank_schema.py`, `pen.color` validation MUST use `re.fullmatch(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$", color_val)`.
- **FR-006**: The repository documentation (`README.md`, `CHANGELOG.md`) MUST accurately describe the concurrency model as multi-process atomic locking with timestamped tombstones and mutation generation metadata.
- **FR-007**: The local git repository history MUST be purged of sensitive blobs `chu_cua_ban.json.gz` and `tests/data/kho_mau_chup_lai.json.gz` using the provided purge script after creating an external bundle backup.

---

### Key Entities

- **Tk Runtime Probe**: A diagnostic probe in `tests/conftest.py` that validates the operational availability of Tk/Tcl GUI subsystems.
- **Tombstone Record**: Persistent metadata `{"deleted_at": float, "generation": int}` tracking genuine word deletions.
- **Large-Bank Benchmark Suite**: Automated performance harness validating scaling characteristics across $\ge 5,000$ samples.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% test pass rate across all 8 CI matrix jobs (Ubuntu + Windows × Python 3.10, 3.11, 3.12, 3.13), with 0 failed tests.
- **SC-002**: 100% clean skip rate for all GUI tests on environments with broken or partial Tk/Tcl libraries.
- **SC-003**: Benchmark completion of 50 consecutive saves on $\ge 5,000$ samples with average per-word latency $< 1.0\text{s}$.
- **SC-004**: 0 dead tombstones or spurious generation increments when calling `Bank.drop()` on non-existent words.
- **SC-005**: 0 occurrences of historical blobs `chu_cua_ban.json.gz` and `kho_mau_chup_lai.json.gz` in local git history.

---

## Assumptions

- Windows Python 3.11 runners in GitHub Actions may have partial Tk library installations; skipping GUI tests when Tcl script files are absent preserves CI integrity without sacrificing test coverage on supported environments.
- The 50-save benchmark on a 5,000-sample synthetic bank executes within 10–15 seconds total on standard developer and CI hardware.
- The local git history purge modifies local commit hashes; remote synchronization requires explicit manual execution of `git push --force --mirror origin` by the repository owner.
