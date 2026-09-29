# Implementation Plan: CI Environment Hardening, Tk/Tcl Probing, and Data Integrity Alignment

**Branch**: `005-ci-tk-and-integrity-alignment` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-ci-tk-and-integrity-alignment/spec.md`

## Summary

Resolve the CI failure on Windows Python 3.11 (Tk `listbox.tcl` missing), reconcile the large-bank benchmark to 50 consecutive saves on $\ge 5,000$ samples, refine `Bank.drop()` to prevent dead tombstones on non-existent words, harden `pen.color` schema validation via `re.fullmatch()`, accurately document the concurrency architecture, and execute the local git history purge with backup verification.

## Technical Context

**Language/Version**: Python 3.10+ (tested across 3.10, 3.11, 3.12, 3.13 on Ubuntu and Windows)

**Primary Dependencies**: `filelock` (cross-process locking), `gzip`/`json` (persistence), `tkinter`/`ttk` (GUI, optional), `re` (schema regex)

**Storage**: Single gzip-compressed JSON file (`*.json.gz`) with atomic replace; local git repository history

**Testing**: `pytest` with deep runtime probing in `conftest.py`, `multiprocessing` for concurrency tests

**Target Platform**: Windows 10/11, Ubuntu Linux (CI), desktop environment

**Project Type**: Desktop application (MVC: `chuviettay/model/`, `chuviettay/view/`, `chuviettay/controller/`)

**Performance Goals**: 50 consecutive interactive saves on $\ge 5,000$ samples with average latency $< 1.0\text{s}$ and total elapsed time $< 30.0\text{s}$

**Constraints**: Clean 100% CI pass rate across all matrix jobs; headless and partial Tk environments must skip cleanly without unhandled crashes; no destructive remote git commands executed automatically

**Scale/Scope**: 5 affected source/test files, 2 scripts, documentation alignment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Maintainability & Code Cleanliness | Self-documenting implementations, clear naming, and accurate docstrings | ✅ PASS — accurate documentation of hybrid concurrency and clean probe encapsulation |
| II. Simple Architecture (KISS & YAGNI) | Direct solutions without speculative abstractions | ✅ PASS — standard Tcl probing and simple guards without external wrapper dependencies |
| III. Comprehensive Automated Testing | Deterministic CI execution and regression coverage | ✅ PASS — 100% green CI immunity across all matrix environments and 50-save benchmark |
| IV. Loose Coupling & High Cohesion | Well-scoped responsibilities and clean public contracts | ✅ PASS — probe isolated to `conftest.py`; model invariants preserved in `Bank` |

## Project Structure

### Documentation (this feature)

```text
specs/005-ci-tk-and-integrity-alignment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py              # Refine drop() to check word existence before tombstones/generation
│   └── bank_schema.py       # Update pen.color validation to use re.fullmatch()
├── view/
│   └── app_window.py        # MainWindow widget hierarchy
└── config.py

tests/
├── conftest.py               # Deep Tk/Tcl probe: inspect scripts, verify listbox.tcl, test event loop
├── test_gui.py               # Guard MainWindow initialization in standalone test functions
├── test_bank.py              # Update benchmark test to 50 saves on 5,000 samples
├── test_schema.py            # Test re.fullmatch pen.color validation
└── test_bank_multiprocess.py # Multi-process concurrency tests

scripts/
├── purge_git_history.ps1     # Executable local purge script (Windows)
└── purge_git_history.sh      # Executable local purge script (POSIX)

README.md                     # Concurrency documentation alignment
CHANGELOG.md                  # Accurate concurrency architecture description
```

**Structure Decision**: Single desktop application. Changes are strictly confined to testing infrastructure, model invariant refinement, schema validation, and operational purge scripts.

## Complexity Tracking

No constitution violations to justify. All changes are minimal, defensive, and targeted directly at observed defects.
