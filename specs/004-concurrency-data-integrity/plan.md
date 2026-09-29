# Implementation Plan: Concurrency Data Integrity, Tombstone Versioning, and Robust Persistence

**Branch**: `004-concurrency-data-integrity` | **Date**: 2026-09-29 | **Spec**: [spec.md](specs/004-concurrency-data-integrity/spec.md)

**Input**: Feature specification from `specs/004-concurrency-data-integrity/spec.md`

## Summary

Fix 6 correctness/performance defects in `Bank` persistence and add verification infrastructure. The core issues are: (1) `Bank.save()` silently overwrites corrupt disk files when merge validation fails, (2) tombstones lack generation metadata allowing stale snapshots to resurrect deleted words, (3) `drop()` leaves stale entries in lookup indexes, (4) `_tombstones` dictionary aliasing breaks after merge, (5) tone mark percentile calculation performs 4 redundant sorts per addition, and (6) concurrency tests use threads instead of true OS processes. Secondary work includes large-bank benchmarks, git history purge documentation, CI lint integration, and documentation alignment.

## Technical Context

**Language/Version**: Python 3.10+ (minimum supported), tested on 3.10, 3.11, 3.12, 3.13

**Primary Dependencies**: `filelock` (cross-process file locking), `gzip`/`json` (persistence), `tkinter` (GUI, optional), `bisect` (stdlib, for optimized percentile insertion)

**Storage**: Single gzip-compressed JSON file (`*.json.gz`) with atomic write via `tempfile.mkstemp` + `os.fsync` + `os.replace`

**Testing**: `pytest` with `conftest.py` fixtures (`tiny_bank`, `real_bank`), `multiprocessing`/`subprocess` for new concurrency tests

**Target Platform**: Windows 10/11, Ubuntu Linux (CI), desktop application

**Project Type**: Desktop app (MVC: `chuviettay/model/`, `chuviettay/view/`, `chuviettay/controller/`)

**Performance Goals**: Sub-second interactive save latency on banks with ≥5,000 samples; fast-path cache validation avoids redundant disk reads

**Constraints**: Single-file persistence model (no database), Python GIL limits in-process concurrency, `FileLock` timeout 10.0s

**Scale/Scope**: Typical bank: 100–500 words; stress target: 5,000–10,000 samples; 262+ existing tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Maintainability & Code Cleanliness | All changes must be self-documenting with clear naming | ✅ PASS — targeted fixes in existing methods with Vietnamese docstrings |
| II. Simple Architecture (KISS & YAGNI) | No speculative extensibility; complexity proportional to problem | ✅ PASS — generation field on tombstones is minimal correct solution; `bisect.insort` is stdlib |
| III. Comprehensive Automated Testing | All critical paths validated by automated tests in CI | ✅ PASS — spec mandates multi-process tests, benchmarks, regression tests |
| IV. Loose Coupling & High Cohesion | Modules interact through public contracts only | ✅ PASS — all changes within `Bank` model; schema validation extended compatibly |

## Project Structure

### Documentation (this feature)

```text
specs/004-concurrency-data-integrity/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py              # Bank class — save(), merge, drop(), add_sample, _harvest, _refresh_tone_marks
│   ├── bank_schema.py       # Schema validation — validate_bank_dict, load_and_validate, exceptions
│   ├── composer.py           # Page composition (unaffected)
│   ├── writer.py             # Xournalpp output (unaffected)
│   └── file_lock.py          # FileLock — cross-platform file locking
├── view/                     # GUI tabs (unaffected)
├── controller/               # AppController (unaffected)
├── config.py                 # TONES, layout constants
└── logging_setup.py          # Logging configuration

tests/
├── conftest.py               # Fixtures: tiny_bank, real_bank, is_tk_usable
├── test_bank.py              # 32 tests — lifecycle, persistence, basic concurrency
├── test_bank_tombstones.py   # 3 tests — deletion tracking
├── test_bank_indexing.py     # 2 tests — incremental index parity
├── test_schema.py            # 35 tests — deep schema validation
├── test_gui.py               # GUI tests (unaffected)
├── test_gui_resilience.py    # Tk resilience (unaffected)
└── data/
    └── kho_mau_tong_hop.json.gz  # Synthetic test bank

scripts/
├── purge_git_history.ps1     # Git history purge (Windows)
└── purge_git_history.sh      # Git history purge (POSIX)

.github/workflows/
└── ci.yml                    # CI matrix: Ubuntu+Windows × Python 3.10–3.13
```

**Structure Decision**: Single-project desktop application. All changes target existing files in `chuviettay/model/` and `tests/`. No new modules or architectural layers introduced.

## Complexity Tracking

No constitution violations to justify. All changes are targeted fixes within existing architecture.
