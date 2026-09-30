# Quickstart & Verification Guide: Letter-Level Handwriting Assembly

**Feature**: `016-letter-assembly-synthesis`  
**Date**: 2026-09-30  
**Status**: Ready  

---

## Prerequisites

- Python 3.10+ virtual environment with development dependencies installed (`pytest`).
- Clean repository working directory at `d:\viet\app`.

---

## Scenario 1: Golden Master Invariance (Regression Protection)

Verify that the existing handwriting synthesis engine produces 100% byte-identical outputs when `assemble_letters=False`.

```powershell
pytest tests/test_golden_master.py -v
```

**Expected Outcome**:
All golden master cases (`co_ban`, `tuy_chon`, `nhieu_trang`, `strict_case`) pass with 0 hash discrepancies.

---

## Scenario 2: Unit Testing Letter Decomposition & Greedy Set-Cover

Verify that Vietnamese words are decomposed into 29 base NFC letters and accurate tone metadata, and that greedy coverage correctly ranks missing letters.

```powershell
pytest tests/test_letter_assembly.py -k "test_split_letters or test_missing_letters_ranked" -v
```

**Expected Outcome**:
- Words such as `bà`, `đường`, `chào`, `học` decompose to NFC letters and proper tone marks.
- Unlearned words produce a greedy letter ranking ordering the most impactful letters first.

---

## Scenario 3: Fallback Word Synthesis from Letters

Verify that `Writer` synthesizes missing words when letters are available in `bank.letters`.

```powershell
pytest tests/test_letter_assembly.py -k "test_assemble_word_with_tone or test_word_resolution_cascade" -v
```

**Expected Outcome**:
- `assemble_word("chào")` produces continuous stroke coordinates aligned to baseline $y = 0$.
- Upper tone mark is placed over vowel `a` without colliding with adjacent letters.
- Dot on letter `i` in words like `gì` is suppressed when grave tone is affixed.
- Whole-word matches and root substitutions still take precedence over assembled letters.

---

## Scenario 4: Bank Schema v4 Migration & Concurrency

Verify that existing v1-v3 bank files upgrade to v4 in-memory without errors, and that concurrent saves properly merge letter additions and deletions.

```powershell
pytest tests/test_letter_bank_storage.py -v
```

**Expected Outcome**:
- `Bank.create_empty()` outputs a valid schema v4 dictionary with `letters: {}`.
- Existing `chu_cua_ban.json.gz` loads and validates cleanly.
- Multi-process `merge_bank_dicts` retains letter additions and respects letter tombstones.

---

## Scenario 5: End-to-End CLI Writing with `--assemble`

Verify the CLI execution flow with the new `--assemble` flag.

```powershell
# Standard run without --assemble (missing word left blank and reported)
python -m chuviettay.cli write -t "chào bạn" -o out_legacy.xopp

# Assembly run with --assemble (missing word synthesized from learned letters)
python -m chuviettay.cli write -t "chào bạn" --assemble -o out_assembled.xopp

# Verify bank stats output includes letter counts
python -m chuviettay.cli stats
```

**Expected Outcome**:
- Legacy run reports missing words and generates `out_legacy_thieu.xopp`.
- Assembly run reports synthesized words and has 0 missing words if constituent letters exist.
- `stats` displays letter inventory statistics.
