# Implementation Plan: Data Safety and Core Reliability Hardening

**Branch**: `001-data-safety-hardening` | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-data-safety-hardening/spec.md`

## Summary

Harden the handwriting bank application's data management layer: remove personal data from source control, add schema versioning/validation/migration to the bank format, implement cross-platform file locking with atomic persistence, centralize input validation for write options and color codes, establish GitHub Actions CI, and modernize project packaging. Core handwriting algorithms (`writer.py`, `text_utils.py`, `composer.py`) remain untouched — golden-master tests must continue to pass unchanged.

## Technical Context

**Language/Version**: Python 3.10+ (uses `str | None`, `list[str]` union syntax)

**Primary Dependencies**: Standard library only (tkinter for GUI) + `filelock` (new, for cross-platform file locking)

**Storage**: Gzip-compressed JSON files (`chu_cua_ban.json.gz`) — no database

**Testing**: `pytest>=8` with Tkinter GUI tests (requires `xvfb-run` on headless Linux)

**Target Platform**: Windows (primary) + Linux (secondary) desktop; no macOS-specific support currently

**Project Type**: Desktop application (Tkinter GUI) + CLI tool, MVC architecture

**Performance Goals**: Bank loading and saving must complete in under 2 seconds for banks with up to 10,000 samples. No performance regression in document generation.

**Constraints**: Zero changes to core handwriting synthesis algorithms. New runtime dependency limited to `filelock` only. Must remain compatible with PyInstaller `--onefile --windowed` packaging.

**Scale/Scope**: Single-user desktop app. Current bank: ~362 words / ~859 samples. Expected growth to low thousands.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check ✅

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Maintainability & Code Cleanliness | ✅ Pass | New modules (`bank_schema.py`) are self-documenting with clear naming |
| II. Simple Architecture (KISS & YAGNI) | ✅ Pass | No new patterns beyond what's needed: simple validation function, simple migration chain, standard file locking library |
| III. Comprehensive Automated Testing | ✅ Pass | Adding CI + corruption/edge-case tests directly serves this principle |
| IV. Loose Coupling & High Cohesion | ✅ Pass | Schema validation is a cohesive module; validation logic shared between CLI/GUI via controller |

### Post-Design Check ✅

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Maintainability | ✅ Pass | `bank_schema.py` isolates all validation/migration logic; `WriteOptions.validate()` is self-contained |
| II. KISS & YAGNI | ✅ Pass | `filelock` is the simplest viable solution; no custom locking code. Sequential migration chain, not a framework. |
| III. Testing | ✅ Pass | Comprehensive test plan covers corruption, concurrency, validation edge cases, and golden-master regression |
| IV. Coupling | ✅ Pass | New module only depends on standard library. No circular dependencies introduced. |

**Dependency Inversion**: New `bank_schema.py` has no dependencies on Controller or View layers. ✅
**Explicit Data Flow**: Loading pipeline is a clear sequential pipeline (file → gzip → JSON → validate → migrate → Bank). ✅
**Dependency Minimization**: Single new dependency (`filelock`) — actively maintained, pure Python, no transitive deps. ✅

## Project Structure

### Documentation (this feature)

```text
specs/001-data-safety-hardening/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   ├── bank-schema.md   # Schema validation API contract
│   ├── bank-persistence.md  # Atomic save API contract
│   └── write-options.md # WriteOptions validation contract
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py              # MODIFIED: schema validation on load, atomic save with lock + fsync
│   ├── bank_schema.py       # NEW: validate_bank_dict(), migrate_bank_dict(), error classes
│   ├── composer.py          # MODIFIED: WriteOptions.validate() method added
│   ├── writer.py            # UNCHANGED (golden-master protected)
│   ├── text_utils.py        # UNCHANGED (golden-master protected)
│   ├── xopp.py              # UNCHANGED (color validation happens before reaching here)
│   └── ...
├── controller/
│   ├── app_controller.py    # MODIFIED: pass create_if_missing=False for explicit --bank paths
│   └── ...
├── view/
│   ├── app_window.py        # MODIFIED: accept create_if_missing parameter from GUI entry point
│   └── ...
├── gui.py                   # MODIFIED: pass create_if_missing=(args.bank is None) to MainWindow
├── logging_setup.py         # MODIFIED: fallback log path to OS user data directory
├── paths.py                 # MODIFIED: add log_data_dir() for platform-aware user data paths
└── config.py                # UNCHANGED

tests/
├── conftest.py              # MODIFIED: use new synthetic fixture
├── data/
│   └── kho_mau_tong_hop.json.gz  # NEW: synthetic test fixture (replaces kho_mau_chup_lai.json.gz)
├── test_bank.py             # MODIFIED: add corruption/validation/migration/concurrent tests
├── test_composer.py         # MODIFIED: add WriteOptions validation tests, strengthen jitter test
├── test_golden_master.py    # UNCHANGED (must still pass)
├── test_architecture.py     # MODIFIED: add ctl.bank access restriction check
└── ...

scripts/
└── gen_synthetic_bank.py    # NEW: script to generate synthetic test fixture

.github/workflows/
└── ci.yml                   # NEW: CI workflow

.gitignore                   # MODIFIED: uncomment chu_cua_ban.json.gz, add *.lock
pyproject.toml               # NEW: project metadata
LICENSE                      # NEW: license file
```

**Structure Decision**: Existing MVC structure is preserved. New code is added as new files (`bank_schema.py`, `gen_synthetic_bank.py`, `ci.yml`, `pyproject.toml`) or minimal modifications to existing files. No restructuring needed.

## Complexity Tracking

No constitution violations to justify. All additions are simple, direct implementations of concrete requirements.
