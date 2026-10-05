# Implementation Plan: P1 — Core Foundation & Ecosystem Harmonization

**Branch**: `refactor/phase1-foundation` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-core-foundation/spec.md`

## Summary

Harmonize the core application foundation across documentation, test infrastructure, packaging, and external data formats. Establish Schema Version 4 as the single source of truth across all tools and scripts (Q3); migrate remaining legacy test calls to the production layout engine and prune deprecated composer code (Q2); implement a deterministic synthetic letter bank generator and automated quantitative acceptance test suite (Q4); expand practice sheet grid definition to include foreign Latin letters f, j, w, z (F3); resolve default bank paths to standard OS user data directories for pip installations (F4); align serialized background style names with native Xournal++ XML attributes (F7); and harden CI with pip smoke testing and uninstrumented benchmark execution.

## Technical Context

**Language/Version**: Python 3.10+ (tested on Python 3.12, strict typing with `from __future__ import annotations`)  
**Primary Dependencies**: None for core package (`dependencies = []`). Optional extras: `python-docx`, `markdown-it-py`, `mdit-py-plugins` (`docs`), `pdfplumber` (`fidelity`).  
**Storage**: Gzip compressed JSON (`.json.gz`), XML (.xopp) via `xml.etree.ElementTree`.  
**Testing**: `pytest`, `pytest-timeout`, `ruff`, Xvfb virtual display for Tkinter tests.  
**Target Platform**: Cross-platform (Windows, Linux, macOS).  
**Project Type**: Python CLI & Desktop GUI application (MVC architecture).  
**Performance Goals**: Synthetic letter bank generation < 50ms; acceptance metrics analysis < 500ms; full test suite < 60s.  
**Constraints**: Zero external dependencies in core; 100% backward compatibility with existing banks and .xopp files; strict MVC boundary adherence (`tests/test_architecture.py` must stay green).  
**Scale/Scope**: 21 affected files; ~7 modular tasks executed in strict priority sequence: Q3 → Q2 → Q4 → F3 → F4 → F7 → CI.  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Maintainability & Cleanliness)**: PASS. Pruning ~150 lines of deprecated dead code in `composer.py` and unifying on Schema v4 eliminates dual-path confusion and technical debt.
- **Principle II (KISS & YAGNI)**: PASS. No new frameworks, classes, or external dependencies are introduced. Standard library (`os`, `sys`, `pathlib`) is used exclusively for OS path resolution.
- **Principle III (Automated Testing)**: PASS. Every item requires Red-to-Green automated regression tests. Step 0 real-path golden master is strictly preserved.
- **Principle IV (Loose Coupling & High Cohesion)**: PASS. MVC boundary rules remain inviolable (`view` calls `controller`, `model` is independent of UI/CLI, `controller` orchestrates services).
- **Rule of No Unjustified Dependencies**: PASS. Core dependencies remain `[]`.

## Project Structure

### Documentation (this feature)

```text
specs/019-core-foundation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── bank-schema-v4.md
│   ├── paths-resolution.md
│   └── xopp-background-styles.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
chuviettay/
├── cli.py                  # CLI argument parsing and commands (F4, F7)
├── paths.py                # OS standard user data and bank path resolution (F4)
├── controller/
│   └── app_controller.py   # export_letter_grid, drop_words routing (F3, Q3)
├── document/
│   └── page_format.py      # Background style mapping to Xournal++ XML (F7)
├── layout/
│   └── engine.py           # Production layout engine
├── model/
│   ├── bank.py             # Core bank data model and persistence (Q3)
│   ├── bank_schema.py      # Schema validation and migration (Q3)
│   ├── composer.py         # WriteOptions/WriteResult public contracts; prune dead code (Q2)
│   ├── learning.py         # Practice sheet ingestion; filter letter tokens (F3)
│   ├── seed_words.py       # Minimal essentials data (Q3)
│   └── xopp.py             # make_letter_grid with f, j, w, z (F3)
scripts/
├── gen_synthetic_bank.py   # build_synthetic_letter_bank generator (Q3, Q4)
└── migrate_letter_bank.py  # Schema v4 output alignment (Q3)
tests/
├── test_acceptance_metrics.py     # Quantitative acceptance test suite (Q4)
├── test_architecture.py           # MVC boundary enforcement (all items)
├── test_composer.py               # Migrated to DocumentLayoutEngine (Q2)
├── test_golden_master_real_path.py# Step 0 golden master invariant (Q2)
├── test_letter_assembly_quality.py# Migrated to DocumentLayoutEngine (Q2)
├── test_paths.py                  # Standard OS user data path unit tests (F4)
└── test_xopp_format.py            # Xournal++ XML background style tests (F7)
.github/
└── workflows/
    └── ci.yml                     # Pip smoke test and benchmark isolation (CI)
README.md                          # Documentation fixes (Q3)
CHANGELOG.md                       # Release notes and schema v4 documentation (Q3)
```

**Structure Decision**: Monolithic single-package layout adhering to existing project architecture. All core modules reside in `chuviettay/`, CLI and GUI entrypoints remain thin shells, and tests are located under `tests/`.

## Complexity Tracking

*No constitutional violations identified. No new architectural layers or dependencies introduced.*
