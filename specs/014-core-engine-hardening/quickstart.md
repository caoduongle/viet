# Quickstart & Verification Guide: Comprehensive Engine Hardening

**Feature**: `014-core-engine-hardening`  
**Date**: 2026-09-30  
**Status**: Ready

---

## 1. Setup & Environment

Ensure Python 3.10+ is available with development dependencies:

```powershell
py -3.12 -m pip install -e .
py -3.12 -m pip install pytest pytest-timeout ruff
```

---

## 2. Validation Scenarios

### Scenario 1: Digit and Punctuation Learning & Writing (L1)

1. **Train a minimal bank**:
   ```powershell
   py -3.12 -m pytest tests/test_digits_and_punct.py -k "test_learn_digits_routes_to_bank_digits" -v
   ```
2. **Verify multi-digit handwriting**:
   ```powershell
   py -3.12 hw_note.py write -t "Năm 2024 đạt 3,5 điểm." -o out_numbers.xopp
   ```
3. **Expected Outcome**:
   - `out_numbers.xopp` is created with valid strokes for "2024" and "3,5".
   - `result.missing` does not report missing digits.

---

### Scenario 2: Accurate Page Count & Token Statistics (L2, L3)

1. **Run layout engine on a 5-page text document**:
   ```powershell
   py -3.12 -m pytest tests/test_reporting_statistics.py -k "test_n_pages_matches_page_buffer" -v
   ```
2. **Expected Outcome**:
   - `result.n_pages` reports exactly 5.
   - Missing token calculation does not output negative ratios (e.g. "-2/1").

---

### Scenario 3: Importer Content Preservation (L6, L7, L8, L10)

1. **Verify mathematical inequalities `<` and `>` in Markdown**:
   ```powershell
   py -3.12 -m pytest tests/test_markdown_inequalities.py -v
   ```
2. **Verify inline punctuation boundaries without space padding**:
   ```powershell
   py -3.12 -m pytest tests/test_inline_punctuation_spacing.py -v
   ```
3. **Expected Outcome**:
   - Strings `"1 < 2"` and `$a < b$` pass through without missing text.
   - `"**chào**,"` does not insert a space between `"chào"` and `","`.

---

### Scenario 4: Proportional Scale & Line Spacing (L4, L5)

1. **Generate output at scale 1.0 and scale 2.0**:
   ```powershell
   py -3.12 hw_note.py write -t "Dòng một\nDòng hai" -o out_scale1.xopp --scale 1.0
   py -3.12 hw_note.py write -t "Dòng một\nDòng hai" -o out_scale2.xopp --scale 2.0
   ```
2. **Visual Inspection**:
   - Open `out_scale1.xopp` and `out_scale2.xopp` in Xournal++.
   - Verify that lines in `out_scale2.xopp` do not collide or overlap.

---

### Scenario 5: Full Regression & Architectural Integrity

1. **Verify zero MVC layering violations**:
   ```powershell
   py -3.12 -m pytest tests/test_architecture.py -v
   ```
2. **Run full automated test suite**:
   ```powershell
   py -3.12 -m pytest -v --timeout=60
   ```
3. **Verify lint cleanliness**:
   ```powershell
   py -3.12 -m ruff check .
   ```
