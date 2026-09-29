# Implementation Plan: GUI Test Exception Scope Refinement, Tk Probe Contract Alignment, Server-Side Object Clarification, and CI Maintenance

**Branch**: `006-test-quality-and-maintenance` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-test-quality-and-maintenance/spec.md`

## Summary

Refine GUI test exception handling in `tests/test_gui.py` to catch only `tkinter.TclError` (eliminating false-green CI on application bugs), align `tests/conftest.py` with the spec by explicitly probing `$tcl_library/init.tcl`, document GitHub's remote object retention behavior in purge scripts and documentation, resolve documentation numbering discrepancies, and verify GitHub Actions versions.

## Technical Context

**Language/Version**: Python 3.10+ (tested across 3.10, 3.11, 3.12, 3.13 on Ubuntu and Windows)

**Primary Dependencies**: `tkinter`/`ttk` (standard library, GUI test exception boundaries), `filelock`, `gzip`/`json`, `re`

**Storage**: Single gzip-compressed JSON file (`*.json.gz`); local Git repository history

**Testing**: `pytest` with granular exception guards, headless skipping, and unit/integration coverage

**Target Platform**: Windows 10/11, Ubuntu Linux (CI), desktop environment

**Project Type**: Desktop application (MVC: `chuviettay/model/`, `chuviettay/view/`, `chuviettay/controller/`)

**Performance Goals**: 100% test pass rate with 0 false-green skipped tests on application logic failures

**Constraints**: Skip only on genuine Tk/Tcl platform failures (`tkinter.TclError`); all application logic errors must fail tests; no destructive remote operations

**Scale/Scope**: 4 affected test/script files, documentation files, GitHub Actions workflow

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Maintainability & Code Cleanliness | Accurate docstrings, transparent remote object retention explanations | ✅ PASS — honest reporting of branch rewrite vs remote GitHub cache |
| II. Simple Architecture (KISS & YAGNI) | Targeted exception handling without complex wrapper layers | ✅ PASS — narrow `except tk.TclError` directly targeting the platform boundary |
| III. Comprehensive Automated Testing | High test sensitivity; application bugs must fail instead of skipping | ✅ PASS — eliminates false-green CI vulnerability |
| IV. Loose Coupling & High Cohesion | Platform probes and test guards cleanly decoupled from model/controller logic | ✅ PASS — isolated to `tests/conftest.py` and `tests/test_gui.py` |

## Project Structure

### Documentation (this feature)

```text
specs/006-test-quality-and-maintenance/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
tests/
├── conftest.py               # Explicit probe for $tcl_library/init.tcl alongside $tk_library
├── test_gui.py               # Narrow exception guards to tkinter.TclError
└── test_gui_resilience.py    # Test that application errors propagate while TclError skips

scripts/
├── purge_git_history.ps1     # Document remote GitHub loose object retention and support contact
└── purge_git_history.sh      # Document remote GitHub loose object retention and support contact

.github/workflows/
└── ci.yml                    # Modernize actions versions (actions/checkout, actions/setup-python)

README.md                     # Update test count to >240, clarify git object caching
CHANGELOG.md                  # Document test guard narrowing and Git object retention notes
specs/005-ci-tk-and-integrity-alignment/quickstart.md # Fix SC-004 typo to SC-003
```

**Structure Decision**: Standard desktop repository layout. Changes are strictly confined to test infrastructure, operational scripts, workflow configuration, and documentation accuracy.

## Complexity Tracking

No constitution violations to justify. All changes decrease risk by increasing test sensitivity and documentation accuracy.
