# Feature Specification: GUI Test Exception Scope Refinement, Tk Probe Contract Alignment, Server-Side Object Clarification, and CI Maintenance

**Feature Branch**: `006-test-quality-and-maintenance`

**Created**: 2026-09-29

**Status**: Implemented

**Input**: User review of commit `5fb378a7a4221702426f80d246ae0e996c3ac138` (CI run 36561014168):
1. P1: Restrict `except Exception` in `tests/test_gui.py` (`MainWindow` initialization and `app` fixture) to `tkinter.TclError` so application/controller bugs fail tests rather than causing false-green skips.
2. P2: Align `is_tk_usable()` in `tests/conftest.py` with specification contract by explicitly probing `$tcl_library/init.tcl` alongside `$tk_library/{tk.tcl, listbox.tcl, button.tcl, entry.tcl}`.
3. P2: Document that while local and branch git history has been purged, GitHub retains unreachable commit objects by SHA until server garbage collection or a GitHub Support request.
4. P3: Fix documentation discrepancies in `quickstart.md` (benchmark is SC-003, not SC-004) and `README.md` (update test count from >210 to >240).
5. P3: Audit and modernize GitHub Actions in `.github/workflows/ci.yml` (`actions/checkout`, `actions/setup-python`).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Precise GUI Test Exception Scoping to Prevent False Greens (Priority: P1)

As a software quality engineer, I want GUI test initialization guards to catch only genuine Tk/Tcl platform errors (specifically `tkinter.TclError` or display subsystem unreachability) and let application logic errors fail loudly, so that regressions in `AppController`, `Bank`, or tab construction are immediately detected instead of silently masked as skipped tests.

**Why this priority**: In `tests/test_gui.py`, catching `except Exception as e: pytest.skip(...)` is overly broad. If an application bug (such as an `AttributeError`, `TypeError`, `ValueError`, or `BankError`) occurs during `MainWindow` initialization or update, the test is recorded as `SKIPPED` instead of `FAILED`, creating a dangerous "false-green" CI status.

**Independent Test**: Introduce a deliberate syntax or attribute error in `AppController` or `MainWindow`; run `pytest tests/test_gui.py`; verify that the test fails (`FAILED`) rather than skipping (`SKIPPED`).

**Acceptance Scenarios**:
1. **Given** an environment with a broken Tk/Tcl installation (missing `listbox.tcl` or unreadable Tcl script), **When** a GUI test instantiates `MainWindow`, **Then** `tkinter.TclError` is caught and the test is marked `SKIPPED` with an informative message.
2. **Given** an environment with a functional Tk runtime, **When** an application logic defect (`AttributeError`, `TypeError`, `ValueError`, `BankError`) occurs during `MainWindow` initialization, **Then** the exception propagates normally, failing the test suite (`FAILED`).
3. **Given** the `app` fixture in `tests/test_gui.py`, **When** initializing `MainWindow`, **Then** it restricts skip handling strictly to `tkinter.TclError`.

---

### User Story 2 - Tk/Tcl Runtime Probe Contract & Specification Alignment (Priority: P2)

As a maintainer verifying runtime probing, I want `is_tk_usable()` to explicitly probe `$tcl_library/init.tcl` alongside `$tk_library/{tk.tcl, listbox.tcl, button.tcl, entry.tcl}`, so that runtime probing code precisely matches the specification's architectural contract 1:1.

**Why this priority**: The specification in feature 005 stated that the probe must verify `init.tcl`, `tk.tcl`, and `listbox.tcl`. While `init.tcl` was previously loaded implicitly during `tk.Tk()` initialization, explicitly querying `$tcl_library` and validating `init.tcl` ensures strict 1:1 compliance with the specification contract.

**Independent Test**: Run `tests/test_gui_resilience.py`; verify that `is_tk_usable()` checks `$tcl_library/init.tcl` and returns `False` if `init.tcl` is missing.

**Acceptance Scenarios**:
1. **Given** `is_tk_usable()` in `tests/conftest.py`, **When** probing the Tcl environment, **Then** it explicitly inspects `$tcl_library` for `init.tcl` as well as `$tk_library` for `tk.tcl`, `listbox.tcl`, `button.tcl`, and `entry.tcl`.
2. **Given** an environment where `init.tcl` cannot be found or sourced, **When** `is_tk_usable()` runs, **Then** it returns `False` and records the missing script in `_tk_unusable_reason`.

---

### User Story 3 - Transparent Git Object Retention & Server Cache Documentation (Priority: P2)

As a repository owner managing sensitive data hygiene, I want scripts, commit logs, and documentation to clearly state that while branch history rewriting eliminates files from current ref ancestry, remote platforms like GitHub retain loose commit objects by SHA until server garbage collection or an explicit support request, so that data hygiene claims remain accurate and actionable.

**Why this priority**: Although branch history rewriting successfully removes sensitive blobs (`chu_cua_ban.json.gz` and `kho_mau_chup_lai.json.gz`) from all commits reachable from branch heads, GitHub's server-side object database may retain unreferenced commit objects by SHA in server-side packfile caches until GitHub's backend garbage collection runs or the user contacts GitHub Support to purge unreachable objects. Documenting this distinction prevents over-promising complete server-side eviction.

**Independent Test**: Review `scripts/purge_git_history.ps1`, `scripts/purge_git_history.sh`, `README.md`, and `CHANGELOG.md`; confirm that the distinction between branch ref rewriting and remote server-side object caching is accurately explained.

**Acceptance Scenarios**:
1. **Given** `scripts/purge_git_history.ps1` and `scripts/purge_git_history.sh`, **When** the script finishes, **Then** it prints a clear notice explaining that GitHub may retain old commits by direct SHA until backend GC occurs, and provides instructions for contacting GitHub Support if immediate cache eviction is required.
2. **Given** `README.md` and `CHANGELOG.md`, **When** reviewed, **Then** they accurately document that branch history is sanitized while noting remote object caching behavior.

---

### User Story 4 - Documentation Precision and Numbering Reconciliation (Priority: P3)

As a reader of project documentation and specifications, I want `quickstart.md` to reference the correct success criteria IDs (SC-003 for 50-save benchmark, SC-004 for non-existent word drop) and `README.md` to report the true test count (>240 tests), so that documentation remains accurate and trustworthy.

**Why this priority**: Discrepancies between specification numbers and guide references cause confusion during audit reviews. Updating the test count in `README.md` from "Hơn 210" to "Hơn 240" accurately reflects the 248 total tests in the suite.

**Independent Test**: Inspect `specs/005-ci-tk-and-integrity-alignment/quickstart.md` and `README.md`; verify numbers and counts are completely synchronized.

**Acceptance Scenarios**:
1. **Given** `specs/005-ci-tk-and-integrity-alignment/quickstart.md`, **When** reviewed, **Then** the 50-save benchmark references SC-003 and non-existent drop references SC-004.
2. **Given** `README.md`, **When** reviewed, **Then** the test count states "Hơn 240 ca kiểm thử tự động".

---

### User Story 5 - Continuous Integration Workflow Maintenance & Upgrades (Priority: P3)

As a DevOps engineer maintaining CI reliability, I want `.github/workflows/ci.yml` actions and configurations to be reviewed and upgraded to recommended modern releases (`actions/checkout`, `actions/setup-python`), so that workflows remain secure, performant, and future-proof against Node runtime deprecations.

**Why this priority**: Modernizing GitHub Actions dependencies periodically prevents deprecation warnings and takes advantage of upstream performance and security improvements.

**Independent Test**: Review `.github/workflows/ci.yml` action versions; run `ruff` and `pytest` to ensure workflow definitions remain valid.

**Acceptance Scenarios**:
1. **Given** `.github/workflows/ci.yml`, **When** inspected, **Then** action versions for `actions/checkout` and `actions/setup-python` use supported, stable major versions.

---

## Edge Cases

- **What happens if a Tk runtime throws an exception other than `TclError` during `MainWindow` creation?**
  Only `tkinter.TclError` is caught by the test skip guard. Standard Python exceptions (`TypeError`, `AttributeError`, `ValueError`, `KeyError`, `BankError`) propagate to pytest and mark the test as failed.
- **What happens if Tcl library directory has no `init.tcl` file?**
  The probe evaluates `source [file join $tcl_library init.tcl]` which fails with `TclError`, correctly setting `_tk_usable_cached = False` and skipping GUI tests.
- **What happens if a user accesses a historical commit via GitHub API or commit SHA URL after a branch purge?**
  GitHub may serve the cached commit until repository GC runs. The documentation provides explicit guidance on how to request a cache purge via GitHub Support.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In `tests/test_gui.py`, all exception guards around `MainWindow` creation in tests and fixtures MUST catch only `tkinter.TclError` (and not broad `Exception`), ensuring application exceptions propagate and trigger test failures.
- **FR-002**: In `tests/conftest.py`, `is_tk_usable()` MUST explicitly probe `$tcl_library/init.tcl` in addition to `$tk_library` scripts (`tk.tcl`, `listbox.tcl`, `button.tcl`, `entry.tcl`).
- **FR-003**: In `scripts/purge_git_history.ps1`, `scripts/purge_git_history.sh`, `README.md`, and `CHANGELOG.md`, the documentation MUST explicitly explain that branch history rewrite removes files from branch history, but GitHub server-side object caches may retain unreachable commit SHAs until GitHub GC or Support ticket.
- **FR-004**: In `specs/005-ci-tk-and-integrity-alignment/quickstart.md`, the reference to SC-004 for the benchmark MUST be corrected to SC-003, and in `README.md` the test suite size MUST be updated to over 240 tests.
- **FR-005**: In `.github/workflows/ci.yml`, actions versions MUST be audited and updated to compatible, secure releases without breaking CI caching or matrix runs.

---

### Key Entities

- **GUI Test Skip Guard**: Exception handler in `tests/test_gui.py` strictly limited to `tkinter.TclError` to protect test sensitivity against application regressions.
- **Tk/Tcl Runtime Probe**: Script-level verifier in `tests/conftest.py` ensuring both Tcl core (`init.tcl`) and Tk widgets (`listbox.tcl`) are verified.
- **Server-Side Object Disclaimer**: Operational documentation describing git commit reachable-history sanitization versus platform-level unreachable object caching.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of non-Tk exceptions raised during `MainWindow` initialization cause test failures rather than being converted into skips.
- **SC-002**: Tk runtime probe directly verifies both `init.tcl` and `listbox.tcl` without false positives.
- **SC-003**: 0 misleading claims regarding immediate server-side GitHub object deletion in documentation or scripts.
- **SC-004**: 100% pass rate across the 8 CI matrix test jobs with upgraded action workflows.
- **SC-005**: Total test count in documentation matches actual repository test suite ($\ge 248$ test cases).

---

## Assumptions

- `tkinter.TclError` encompasses all platform-level Tcl/Tk script sourcing and widget lifecycle failures during `MainWindow` instantiation.
- Application code errors (`BankError`, `AttributeError`, `TypeError`, `ValueError`) should always fail tests when GUI tests execute on capable environments.
- GitHub's backend object database cleans unreferenced commits lazily or upon request to GitHub Support; local history rewriting does not control remote server garbage collection timing.
