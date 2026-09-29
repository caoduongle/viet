# Implementation Plan: Scalability, Correctness, and CI Hardening

**Branch**: `003-scalability-correctness-hardening` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-scalability-correctness-hardening/spec.md`

## Summary

This feature resolves all critical audit findings and CI failures identified in the latest repository audit:
1. **CI Hardening**: Cleanly isolate Tcl/Tk runtime dependencies via a session-level probe (`is_tk_usable()`) and fixture guards in `conftest.py` / `test_gui.py` so Windows 3.10 and headless runners with incomplete Tcl runtimes pass non-GUI tests with 100% reliability, eliminating false-positive CI errors.
2. **Incremental Indexing Correctness**: Decouple raw harvested tone marks (`_raw_marks`) from the query-filtered index (`marks`), guaranteeing complete mathematical equivalence with `rebuild()` while preserving scale-independent $O(1)$ amortized append performance.
3. **Cross-Process Deletion Safety**: Introduce persistent deletion tombstones in bank metadata (`tombstones`) with in-memory `_readded_words` reconciliation, so concurrent processes saving older snapshots never resurrect deleted words while allowing explicit re-teaching.
4. **Scalable Persistence & Realistic Benchmark**: Optimize `Bank.save()` with nanosecond mtime/size change-detection and faster compression, avoiding redundant full-bank decompressions, merges, and rebuilds during interactive teaching sessions (`teach_word()`); benchmark the actual save-per-word path on pre-populated banks.
5. **Deep Invariant Validation**: Enforce strict schema validation on tone metadata (`ti, vi, T`), pen attributes (`tool, color, width`), and preserve backward compatibility by treating `w` as optional for punctuation (`punct`).
6. **Sample Identity Contract**: Base merge deduplication on both stroke geometry and sample metadata (`s, w, T, vi, ti`).
7. **Safe Git Purge & Documentation**: Mandate external clone/bundle backup in purge scripts, and align documentation with the automated CI matrix.

## Technical Context

**Language/Version**: Python 3.10, 3.11, 3.12, 3.13 (zero external runtime dependencies).

**Primary Dependencies**: Standard library (`tkinter`, `gzip`, `json`, `math`, `os`, `sys`, `tempfile`, `re`). Dev dependencies: `pytest`, `ruff`, `pyinstaller`.

**Storage**: Gzip-compressed JSON bank profiles (`.json.gz`) with atomic write pipeline (`mkstemp`, `fsync`, `os.replace`, `FileLock`).

**Testing**: Pytest test suite with markers (`gui`, `slow`) and fixtures for synthetic banks.

**Target Platform**: Cross-platform: Windows 10/11, Linux (Ubuntu), macOS.

**Project Type**: Standalone desktop handwriting synthesis application with CLI (`hw_note.py`) and GUI (`hw_gui.py`).

**Performance Goals**: Sub-second interactive save latency (< 50ms per taught word on banks up to 100,000 samples); $O(1)$ amortized incremental indexing.

**Constraints**: Zero external runtime dependencies; 100% backward compatibility with existing v1/v2 bank profiles; byte-exact golden master rendering preservation.

**Scale/Scope**: Banks containing 1 to 100,000+ words; multi-process concurrency support; 215+ automated tests passing cleanly on CI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Assessment | Status |
|-----------|----------------------|--------|
| **I. Maintainability & Code Cleanliness** | Design uses explicit, modular separation between raw marks and query caches, clear naming, and self-documenting invariants. | PASS |
| **II. Simple Architecture (KISS & YAGNI)** | Reuses existing `.json.gz` format with lightweight timestamp tombstones and mtime cache checks; no heavy database layers introduced. | PASS |
| **III. Comprehensive Automated Testing** | Every audit finding and edge case is covered by dedicated automated tests; CI environment isolation ensures deterministic runs. | PASS |
| **IV. Loose Coupling & High Cohesion** | Persistence and indexing invariants are encapsulated within `Bank` and `bank_schema`; controller and views interact purely via contracts. | PASS |

## Project Structure

### Documentation (this feature)

```text
specs/003-scalability-correctness-hardening/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Technical research and design decisions
├── data-model.md        # Entities, invariants, and state transitions
├── quickstart.md        # Runnable verification guide
├── contracts/           # Component interface contracts
│   ├── bank-indexing.md
│   ├── bank-persistence.md
│   ├── bank-schema.md
│   └── bank-tombstones.md
├── checklists/
│   └── requirements.md
└── tasks.md             # (To be created by /speckit-tasks)
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py          # Bank model (incremental index, raw marks, tombstones, mtime cache save)
│   ├── bank_schema.py   # Deep schema validation (ti, vi, T, pen attributes)
│   └── file_lock.py     # Cross-process file locking
├── controller/
│   └── app_controller.py# AppController orchestration (teach_word, drop_words)
└── view/
    └── app_window.py    # GUI MainWindow

tests/
├── conftest.py          # Test fixtures (resilient Tk environment probe & skip guard)
├── test_bank.py         # Bank unit, concurrent, tombstone, and incremental tests
├── test_gui.py          # GUI tests with graceful TkError guards
├── test_schema.py       # Deep schema validation tests
└── test_word_canvas.py  # WordCanvas tests

scripts/
├── purge_git_history.ps1# Safe history purge script with external clone/backup
└── purge_git_history.sh # Shell equivalent

.github/workflows/
└── ci.yml               # CI matrix (Python 3.10, 3.11, 3.12, 3.13)
```

**Structure Decision**: Preserves the established MVC architecture and directory conventions, modifying only targeted models, test fixtures, workflows, and scripts.

## Complexity Tracking

*No constitutional violations identified. Design adheres strictly to simplicity and zero-runtime-dependency standards.*
