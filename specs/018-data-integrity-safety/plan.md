# Implementation Plan: Data Integrity Safety Net & Core Persistence Hardening (P0)

**Branch**: `fix/phase0-data-integrity` | **Date**: 2026-10-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/018-data-integrity-safety/spec.md`

---

## Summary

Phase 0 hardens the data integrity, concurrent persistence, and testing foundation of the `chuviettay` application across seven critical areas:
1. **Real-Path Golden Master (Step 0)**: Introduce `tests/test_golden_master_real_path.py` exercising `AppController.write_text` / `DocumentLayoutEngine` across 4 standard cases and 4 extended cases (letter assembly, math, tables, lists), pinning decompressed XML SHA-256 digests prior to any code changes.
2. **Environment Decoupling (Q1)**: Switch Word COM availability guards in `test_docx_fidelity.py` and `test_cli_format.py` to `is_word_available()` and isolate timing-sensitive benchmarks with `@pytest.mark.benchmark`.
3. **Symbol Tombstone Cleanup (D2)**: Update `add_symbol_sample` to clear deletion tombstones, discard keys from `_deleted_words`, and track additions in `_readded_words`.
4. **Debounce Save Concurrency (D5)**: Replace streaming dict serialization with single-pass in-memory `json.dumps`, serialize and compress using level 1 gzip, protect bank mutation and merge serialization with `threading.RLock`, log exceptions and retain dirty flags in `_on_debounce_save`.
5. **Non-Destructive Missing Grid (D4)**: Honor `WriteOptions.missing_grid` in `DocumentLayoutEngine`, introduce `--no-missing-grid` in CLI and GUI checkbox, and preserve existing user pen strokes in `<out>_thieu.xopp` by generating sequential non-colliding suffixes (`_thieu_2.xopp`).
6. **Idempotent Learning (D3)**: Hash decompressed XML content rather than raw gzip archives in `learned_files`, and deduplicate incoming cells using `sample_signature`.
7. **Qualified Tombstones & Schema v4 (D1)**: Scope tombstones by category (`"<category>:<label>"`), accept explicit category targets in `Bank.drop`, pass correct category from `AppController.drop_words` and GUI tabs, upgrade schema to Version 4 with backward compatibility for legacy unqualified tombstones.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested on Python 3.10, 3.12, and 3.14).

**Primary Dependencies**: None in core (`dependencies = []` in `pyproject.toml`; strict zero external dependency rule). Standard library only: `json`, `gzip`, `threading`, `os`, `hashlib`, `pathlib`, `re`.

**Storage**: Compressed JSON bank archive (`.json.gz`), upgraded to Schema Version 4 with backward compatibility for Version 2 and Version 3.

**Testing**: `pytest` (`pytest -q --timeout=90 -p no:cacheprovider`), `pytest-timeout`, `ruff`.

**Target Platform**: Cross-platform (Linux, Windows, macOS).

**Project Type**: Desktop GUI (`hw_gui.py` Tkinter), CLI (`hw_note.py`), and core library (`chuviettay`).

**Performance Goals**: Bank save latency reduced by ~5x (0.77s -> 0.15s for 60,000 samples); zero `RuntimeError` during concurrent background saves; sub-millisecond in-memory sample lookup.

**Constraints**:
- Strict MVC boundaries: `view/` and `cli.py` only call `controller`; `view/` never imports `chuviettay.model` or accesses `.bank`; `model/` never imports `tkinter`, `argparse`, or `controller`.
- Byte-level golden master invariance: existing `test_golden_master.py` and new `test_golden_master_real_path.py` must never change output hashes unexpectedly.
- Zero mandatory external dependencies in core library.
- Test-driven red-to-green implementation with one commit per item.

**Scale/Scope**: Banks containing up to 60,000+ samples; multi-threaded GUI / timer debounce saving; multi-page Xournal++ (`.xopp`) XML synthesis.

---

## Constitution Check

*GATE: Passed before Phase 0 research. Re-evaluated post-design.*

| Principle | Requirement | Status | Verification Plan |
| :--- | :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | Self-documenting code, shared helper extraction, clear rationale for non-obvious choices. | PASS | Helper `_clear_tombstone_and_mark_readded` extracted in `Bank`; clear comments on lock scopes. |
| **II. Simple Architecture (KISS & YAGNI)** | Direct solutions using standard library; no unnecessary abstractions or third-party packages. | PASS | Zero new dependencies added; built-in `threading.RLock` and standard library `json.dumps`. |
| **III. Comprehensive Automated Testing** | Every bug reproduced red before fix; real-path golden master added; 100% tests green. | PASS | `repro_viet_baseline.py` establishes red baseline; regression tests added for all items. |
| **IV. Loose Coupling & High Cohesion** | Strict MVC separation; schema versioning isolated; no leaky abstractions. | PASS | `tests/test_architecture.py` verified green; controller mediates model deletion parameters. |

---

## Project Structure

### Documentation (this feature)

```text
specs/018-data-integrity-safety/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 architectural decisions & root cause analysis
├── data-model.md        # Data models and entity specifications
├── quickstart.md        # Quickstart & verification guide
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── contracts/
    ├── cli-contract.md       # CLI interface specification (--no-missing-grid)
    ├── controller-api.md     # Controller and Bank programmatic interfaces
    └── bank-schema-v4.md     # JSON Schema Version 4 contract
```

### Source Code Layout

```text
chuviettay/
├── model/
│   ├── bank.py               # Tombstones, add_symbol_sample, atomic save, RLock
│   ├── bank_schema.py        # Schema Version 4, migrator, validation
│   ├── learning.py           # Decompressed XML hashing, sample_signature dedup
│   └── xopp.py               # HW3_GUIDE_COLORS, user stroke detection
├── controller/
│   └── app_controller.py     # Debounce error handling, drop_words category routing
├── layout/
│   └── engine.py             # DocumentLayoutEngine missing_grid check & suffix resolution
├── view/
│   ├── bank_tab.py           # GUI category-aware sample deletion
│   └── write_tab.py          # GUI missing_grid checkbox
├── cli.py                    # CLI --no-missing-grid flag
└── formatting.py             # Formatted reports for missing grid path

tests/
├── test_golden_master_real_path.py  # NEW: Real-path production golden master (Step 0)
├── test_docx_fidelity.py            # Q1: Guard update to is_word_available()
├── test_cli_format.py               # Q1: Guard update to is_word_available()
├── test_bank.py                     # Q1: Benchmark marker, D1, D2, D5 tests
├── test_learning.py                 # D3: Idempotent learning tests
├── test_cli.py                      # D4: CLI --no-missing-grid tests
├── test_layout_semantic.py          # D4: Missing grid suffix & user stroke preservation tests
├── test_schema.py                   # D1: Schema v4 validation & migration tests
└── test_architecture.py             # MVC architecture boundary gate
```

**Structure Decision**: Updates are distributed cohesively across existing MVC layers following established architectural contracts. No new modules or subdirectories are created outside standard test suites.

---

## Complexity Tracking

| Violation / Complexity | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| Introducing `threading.RLock` to `Bank` | Guarantees thread safety between background debounce saves and rapid GUI word teaching across all Python versions (including free-threaded 3.13t). | Relying solely on CPython GIL is unportable, non-deterministic on free-threaded runtimes, and vulnerable to future refactoring. |
| Schema Version bump to Version 4 | Ensures older application releases do not misinterpret or corrupt namespaced tombstones during shared bank operations. | Staying on Version 3 with dual semantics risks silent deletion regressions in mixed-version environments. |
