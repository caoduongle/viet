# Implementation Plan: Concurrency Deep Safety and Scalability Hardening

**Branch**: `002-concurrency-deep-safety` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-concurrency-deep-safety/spec.md`

## Summary

Eliminate concurrency lost-update bugs between GUI and CLI instances using transactional reload-and-merge under cross-process file locks, enforce deep schema validation on stroke coordinate parity and runtime typographic metadata, optimize word teaching performance through in-memory incremental indexing, harmonize packaging and dependency definitions, make bank creation persistence fully atomic, and provide a standalone safety script for historical git biometric blob purging. Golden-master handwriting synthesis remains strictly untouched.

## Technical Context

**Language/Version**: Python 3.10+ (`str | None`, `dict[str, Any]` union syntax)

**Primary Dependencies**: Standard library only (tkinter for GUI, `msvcrt`/`fcntl` for file locking). Zero external runtime dependencies.

**Storage**: Gzip-compressed JSON files (`.json.gz`) with cross-process `FileLock`, unique temporary files, `fsync`, and atomic `os.replace`.

**Testing**: `pytest>=8` with headless Tkinter testing (`xvfb-run` on Linux, native on Windows).

**Target Platform**: Windows 10/11 (primary) + Linux desktop (Ubuntu 22.04/24.04).

**Project Type**: Desktop GUI application (Tkinter) + CLI tool with strict MVC architecture.

**Performance Goals**: Sequential teaching of 50 words into a 5,000-sample bank completes in < 1.0s. Atomic reload-and-merge completes in < 100ms.

**Constraints**: Zero algorithm modifications to `writer.py` and `text_utils.py`. Zero new external runtime dependencies. 100% backward-compatible migration of legacy bank files.

**Scale/Scope**: Single-user desktop app supporting multiple concurrent processes (GUI + CLI) and scaling up to 100,000 samples.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check ✅

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Maintainability & Code Cleanliness | ✅ Pass | Deep schema rules and merge functions are isolated and clearly documented |
| II. Simple Architecture (KISS & YAGNI) | ✅ Pass | Reload-and-merge under lock avoids complex distributed locking or introducing heavy embedded databases |
| III. Comprehensive Automated Testing | ✅ Pass | Concurrency tests strictly assert survival of all tokens; deep validation tests cover odd counts, NaNs, and missing metadata |
| IV. Loose Coupling & High Cohesion | ✅ Pass | Merge logic lives purely within model layer; controller and view layers remain untouched or simplified |

### Post-Design Check ✅

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Maintainability | ✅ Pass | Clear separation between validation, migration, concurrency merging, and indexing |
| II. KISS & YAGNI | ✅ Pass | Stdlib-only file locking maintained; no external database or message broker added |
| III. Testing | ✅ Pass | Comprehensive test scenarios defined in quickstart.md covering all critical failure and edge cases |
| IV. Coupling | ✅ Pass | View layer remains completely unaware of `.bank` or file lock internals |

**Dependency Inversion**: High-level modules interact with `Bank` abstract operations (`save`, `teach_word`), not low-level file descriptors. ✅
**Explicit Data Flow**: Pipeline is explicit: lock -> read disk -> merge in-memory -> write temp -> fsync -> replace -> unlock. ✅
**Dependency Minimization**: Zero new runtime dependencies introduced. ✅

## Project Structure

### Documentation (this feature)

```text
specs/002-concurrency-deep-safety/
├── spec.md                   # Feature specification
├── plan.md                   # This file
├── research.md               # Phase 0 research findings
├── data-model.md             # Phase 1 data model & state machine
├── quickstart.md             # Phase 1 verification guide
├── contracts/
│   ├── bank-concurrency.md   # Concurrency reload-and-merge contract
│   ├── deep-schema.md        # Deep stroke & metadata validation contract
│   └── incremental-indexing.md # Incremental indexing contract
└── checklists/
    └── requirements.md       # Requirements quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py               # MODIFIED: reload-and-merge in save(), incremental add_sample_incremental(), atomic create_empty()
│   ├── bank_schema.py        # MODIFIED: deep stroke coordinate validation (parity, finiteness), metadata keys validation & migration
│   ├── file_lock.py          # UNCHANGED (stdlib cross-platform locking)
│   ├── composer.py           # UNCHANGED (WriteOptions validation preserved)
│   ├── writer.py             # UNCHANGED (golden-master protected)
│   └── text_utils.py         # UNCHANGED (golden-master protected)
├── controller/
│   ├── app_controller.py     # MODIFIED: teach_word() calls incremental bank method
│   └── ...
├── view/
│   ├── app_window.py         # MODIFIED: handle None log_path gracefully in error dialogs
│   └── ...
├── logging_setup.py          # MODIFIED: log_path() returns None when all file handlers fail
└── paths.py                  # UNCHANGED

tests/
├── conftest.py               # UNCHANGED
├── test_bank.py              # MODIFIED: strict tu_0..tu_7 assertion in concurrent test, deep schema tests, incremental teach test
├── test_golden_master.py     # UNCHANGED (golden-master verification)
├── test_architecture.py      # UNCHANGED (AST boundary enforcement)
└── ...

scripts/
├── purge_git_history.ps1     # NEW: PowerShell script for safe git history biometric purge
├── purge_git_history.sh      # NEW: Bash script for safe git history biometric purge
└── gen_synthetic_bank.py     # UNCHANGED

.github/workflows/
└── ci.yml                    # MODIFIED: fix Linux release archive tar command (copy README/LICENSE to dist first)

requirements-dev.txt          # MODIFIED: pin development tooling consistently
README.md                     # MODIFIED: specify Python 3.10+, remove bundled binary mentions
```

**Structure Decision**: Preserves existing clean MVC architecture. Fixes and enhancements are localized to `bank.py`, `bank_schema.py`, `app_controller.py`, `logging_setup.py`, and CI/script configurations.

## Complexity Tracking

No constitution violations. All enhancements directly fulfill concrete safety, performance, and operational requirements.
