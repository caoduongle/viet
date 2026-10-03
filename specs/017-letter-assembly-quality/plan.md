# Implementation Plan: High-Fidelity Letter Assembly & Handwriting Synthesis Quality

**Branch**: `017-letter-assembly-quality` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-letter-assembly-quality/spec.md`

---

## Summary

Resolve letter-assembly visual defects (touching strokes, ink pooling blobs, uneven baselines, and missing accented words) by overhauling the letter placement engine, normalizing glyph geometries to authentic handwriting baselines, and providing clear collection guidelines. 

The technical approach introduces:
1. Boundary contour kerning with explicit side bearings (`lsb`, `rsb`) and an invariant physical stroke clearance floor ($k \times \text{pen\_thickness}$) to replace the flawed `advance = w - overlap` logic.
2. Group-based x-height normalization and dynamic stroke width scaling matching reference metrics from `2026-09-20-Note-17-02.xopp`.
3. Dual-path Vietnamese diacritic synthesis: direct support for precomposed accented glyphs and grid-aware tone mark extraction, with collision-free placement.
4. Redesigned collection grid template (`hw3`) with 4-line guides, inner margin boundaries, explicit Vietnamese instructions, and dedicated standalone tone mark cells (`sắc, huyền, hỏi, ngã, nặng`) featuring a ghost reference vowel (`o`).
5. Non-destructive migration utilities (`scripts/migrate_letter_bank.py`) and objective quality measurement tools (`tools/measure_ink.py`, `tools/render_xopp.py`).
6. 100% byte invariance for legacy whole-word synthesis on golden-master benchmarks and zero core dependencies outside the Python standard library.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested across Python 3.10–3.14).  
**Primary Dependencies**: Python standard library (`unicodedata`, `gzip`, `json`, `math`, `random`, `dataclasses`, `tkinter`, `argparse`), `pytest` for test execution. `Pillow` is used exclusively in `tools/` and optional test suites (guarded by `pytest.importorskip`).  
**Storage**: Gzip-compressed JSON (`.json.gz`), Schema v4 (automatic in-memory migration from v1, v2, v3), cross-process file locking via `.lock` files, deletion tombstones with generation tracking.  
**Testing**: `pytest`, golden master regression suite (`test_golden_master.py`), unit tests for spatial invariants, kerning, bank storage, writer synthesis, and GUI integration.  
**Target Platform**: Windows, Linux, macOS.  
**Project Type**: Desktop GUI (Tkinter) + Command-Line Interface (CLI) + Standalone Tools.  
**Performance Goals**: Word assembly < 1ms per word; full 1,000-word document synthesis < 10% overhead; ink measurement analysis < 2s for 13-page note.  
**Constraints**: Zero GUI (`tkinter`) or `print()` dependencies in `model/`; zero third-party dependencies in `chuviettay/model|controller`; Golden Master 100% hash invariance when `assemble_letters=False`; preserve `config.py` constants and `find_tone` thresholds.  
**Scale/Scope**: 178 single-character units, multi-page `.xopp` documents, Vietnamese orthography.  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Compliance Status | Analysis & Verification |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | PASS | Modular, self-documenting pure domain functions with strict typing and docstrings. No dead code or convoluted heuristics. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | Direct analytical placement using bounding boxes, side bearings, and nearest-point clearance. No unneeded computational geometry dependencies. |
| **III. Comprehensive Automated Testing** | PASS | Unit tests covering non-overlap invariants, minimum stroke clearance, x-height normalization bounds, bank migration, concurrency merging, and golden master parity. |
| **IV. Loose Coupling & High Cohesion** | PASS | Strict MVC separation maintained: Model contains pure geometry and storage algorithms; Controller coordinates between Model and UI; View and CLI handle display only. Zero Tkinter or print in Model. |
| **Golden Master Invariance Guarantee** | PASS | `assemble_letters` defaults to `False` in `WriteOptions`. Programmatic calls and golden master tests execute without letter fallback, ensuring byte-identical hashes. |
| **Multi-Process Data Safety** | PASS | `letters` and `marks` participate fully in `merge_bank_dicts()` and tombstone deletions under `FileLock`. |
| **Zero Core Dependencies** | PASS | No third-party packages in `chuviettay/model` or `chuviettay/controller`. `Pillow` restricted to `tools/`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/017-letter-assembly-quality/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 architectural decisions & root-cause analysis
├── data-model.md        # Phase 1 data entities and schema v4 definition
├── quickstart.md        # Phase 1 runnable validation scenarios
├── contracts/           # Phase 1 interface and schema contracts
│   ├── assembly-engine-api.md
│   ├── bank-schema-metrics.md
│   ├── grid-hw3-spec.md
│   └── tools-cli-contracts.md
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank_schema.py    # Schema v4 upgrade & migration migrators
│   ├── bank.py           # Bank.letters, add_letter_sample, drop_letter, merge_bank_dicts
│   ├── text_utils.py     # split_letters, missing_letters_ranked, contour classification
│   ├── writer.py         # assemble_word with clearance floor and contour kerning
│   └── composer.py       # WriteOptions (letter_gap, auto_xh, target_xh), WriteResult
├── controller/
│   ├── app_controller.py # teach_letter, missing_letters_for_words, get_stats extension
│   └── results.py        # BankStats, WriteResult fields
├── view/
│   ├── write_tab.py      # Assembly controls, missing letters display, teach button
│   ├── teach_tab.py      # Letter teaching integration
│   └── bank_tab.py       # Letter stats, letter list & drop
├── cli.py                # --assemble, --letter-gap, --target-xh, --auto-xh flags
scripts/
├── migrate_letter_bank.py # Non-destructive bank migration utility
tools/
├── measure_ink.py        # Quantitative ink measurement tool
└── render_xopp.py        # High-resolution XOPP vector renderer

tests/
├── data/
│   └── accept_sample.txt          # Acceptance standard test sample
├── test_letter_assembly.py        # Unit tests for kerning, clearance floor, tone attachment
├── test_letter_bank_storage.py    # Unit tests for schema v4, migration, concurrency merging
├── test_letter_gui_cli.py         # Tests for controller, CLI flags, and GUI wiring
├── test_letter_assembly_quality.py# Quality invariant tests (overlap <= 10%, clearance >= 0.8*pen)
└── test_golden_master.py          # Regression suite (must stay 100% green)
```

**Structure Decision**:
Follows the established repository architecture:
- Core algorithms and geometry sit in `chuviettay/model/` (pure Python standard library).
- Coordination logic sits in `chuviettay/controller/`.
- UI sits in `chuviettay/view/` and `chuviettay/cli.py`.
- Analysis and verification utilities sit in `tools/` and `scripts/`.
- Regression and unit tests sit in `tests/`.

---

## Complexity Tracking

> **Constitution Check passed with zero violations.** No unwarranted patterns or dependencies introduced.
