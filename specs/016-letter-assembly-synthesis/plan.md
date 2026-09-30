# Implementation Plan: Letter-Level Handwriting Assembly & Fallback Synthesis

**Branch**: `016-letter-assembly-synthesis` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-letter-assembly-synthesis/spec.md`

---

## Summary

Enable automatic letter-level assembly and fallback synthesis in the handwriting engine. When words in a document do not exist in the handwriting bank, the system identifies and reports the missing base letters (~29 Vietnamese letters + uppercase + 5 tone marks) ranked by greedy coverage. When enabled via GUI toggle or CLI `--assemble`, `Writer` synthesizes missing words dynamically from learned letter glyphs along the baseline, attaching tone marks and suppressing the tittle on letter `i`. The storage engine evolves to Schema v4 (`letters: dict`) with automatic migration and multi-process tombstone safety. When `assemble_letters=False` (default), the engine guarantees 100% byte parity with the golden master test suite.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested across Python 3.10–3.14).  
**Primary Dependencies**: Python standard library (`unicodedata`, `gzip`, `json`, `math`, `random`, `dataclasses`, `tkinter`, `argparse`), `pytest` for test execution.  
**Storage**: Gzip-compressed JSON (`.json.gz`), Schema v4 (automatic in-memory migration from v1, v2, v3), cross-process file locking via `.lock` files, deletion tombstones with generation tracking.  
**Testing**: `pytest`, golden master regression suite (`test_golden_master.py`), unit tests for text utilities, bank storage, writer synthesis, and GUI integration.  
**Target Platform**: Windows, Linux, macOS.  
**Project Type**: Desktop GUI (Tkinter) + Command-Line Interface (CLI).  
**Performance Goals**: Letter decomposition & assembly < 1ms per word; full 1,000-word document synthesis < 10% overhead; debounced storage flush < 50ms UI latency.  
**Constraints**: Zero GUI (`tkinter`) or `print()` dependencies in `model/`; Golden Master 100% hash invariance when `assemble_letters=False`; preserve `config.py` constants and `find_tone` thresholds.  
**Scale/Scope**: ~60 base character units (29 lowercase letters, uppercase variants as needed, 5 tone marks); arbitrary Vietnamese word synthesis coverage.  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Rule | Compliance Status | Analysis & Verification |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | PASS | Pure functions in `text_utils` (`split_letters`, `missing_letters_ranked`) with comprehensive type hints and docstrings. No dead code or speculative abstractions. |
| **II. Simple Architecture (KISS & YAGNI)** | PASS | Direct extension of existing cascade: Whole word $\rightarrow$ Root substitute $\rightarrow$ Letter assembly $\rightarrow$ Blank gap. No unnecessary external libraries. |
| **III. Comprehensive Automated Testing** | PASS | Unit tests covering decomposition, greedy set-cover, letter baseline layout, tone placement, dot suppression, schema v4 migration, concurrency merging, and golden master invariance. |
| **IV. Loose Coupling & High Cohesion** | PASS | Strict MVC separation maintained: Model contains pure geometry and storage algorithms; Controller coordinates between Model and UI; View and CLI handle display only. Zero Tkinter or print in Model. |
| **Golden Master Invariance Guarantee** | PASS | `assemble_letters` defaults to `False` in `WriteOptions`. Programmatic calls and golden master tests execute without letter fallback, ensuring byte-identical hashes. |
| **Multi-Process Data Safety** | PASS | `letters` participates fully in `merge_bank_dicts()` and tombstone deletions under `FileLock`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/016-letter-assembly-synthesis/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 architectural decisions & analysis
├── data-model.md        # Phase 1 data entities and schema v4 definition
├── quickstart.md        # Phase 1 runnable validation scenarios
├── contracts/           # Phase 1 interface and schema contracts
│   ├── writer-assembly-api.md
│   ├── bank-schema-v4.md
│   └── controller-gui-cli.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank_schema.py    # Schema v4 upgrade & migration migrators
│   ├── bank.py           # Bank.letters, add_letter_sample, drop_letter, merge_bank_dicts
│   ├── text_utils.py     # split_letters, missing_letters_ranked
│   ├── writer.py         # assemble_word, cascade integration in word()
│   └── composer.py       # WriteOptions.assemble_letters, WriteResult.assembled_words
├── controller/
│   ├── app_controller.py # teach_letter, missing_letters_for_words, get_stats extension
│   └── results.py        # BankStats, WriteResult fields
├── view/
│   ├── write_tab.py      # Assembly checkbox, missing letters display, teach button
│   ├── teach_tab.py      # Letter teaching integration
│   └── bank_tab.py       # Letter stats, letter list & drop
└── cli.py                # --assemble flag, stats output

tests/
├── test_letter_assembly.py      # Unit tests for decomposition, ranking, word assembly
├── test_letter_bank_storage.py  # Unit tests for schema v4, migration, concurrency merging
├── test_letter_gui_cli.py       # Tests for controller, CLI flags, and GUI wiring
└── test_golden_master.py        # Regression suite (must stay 100% green)
```

**Structure Decision**:
Follows the established repository architecture:
- Algorithmic and geometric functions reside in `model/text_utils.py` and `model/writer.py`.
- Storage and schema definitions reside in `model/bank_schema.py` and `model/bank.py`.
- Coordination logic sits exclusively in `controller/app_controller.py`.
- Presentation sits in `view/` and `cli.py`.
- Tests are added in dedicated test modules without mutating existing test expectations.

---

## Complexity Tracking

> **Constitution Check passed with zero violations.** No unwarranted patterns or dependencies introduced.
