# Quickstart & Verification Guide: Number Typography and CI Fallback Hardening

**Feature**: `047-number-typography-ci-fix` | **Date**: 2026-10-20

## Overview
This guide provides executable verification commands to validate that the number typography, vector fallback engine, and synthetic test fixtures satisfy all acceptance criteria and pass cleanly in isolated CI environments.

---

## 1. Prerequisites
- Python 3.10+ installed with test dependencies (`pytest`, `pytest-timeout`).
- Clean repository clone or temporary isolation from local uncommitted bank files.

---

## 2. Test Execution & Verification Scenarios

### Scenario 1: Verify Negative Number & Percent Rendering (US1)
Validates that `Writer.number("-25")` and `Writer.token("%")` render with proper mathematical alignment and baseline contact without reporting missing glyphs, even when using the synthetic bank.

```powershell
pytest tests/test_number_fraction_typography.py -k "test_minus_and_percent_digit_normalization" -v
```
**Expected Outcome**: PASS (0 missing characters reported, minus centered at `-0.45 * xh`).

---

### Scenario 2: Verify Decimal Comma Spacing Harmony (US2)
Validates that decimal numbers (`"0,39"`, `"0,0278"`) maintain an optical gap of `0.08 * xh` to `0.14 * xh` after the comma, eliminating unnatural wide gaps.

```powershell
pytest tests/test_number_fraction_typography.py -k "test_decimal_number_spacing_harmony" -v
```
**Expected Outcome**: PASS (`0.08 * xh <= gap_after_comma <= 0.14 * xh`).

---

### Scenario 3: Verify Advance Width Measurement Synchronization (US3)
Validates that `Writer.measure_text_width()` and `Writer.number()` produce identical geometric widths within `0.05 * xh` for negative numbers, decimals, and long digit strings.

```powershell
pytest tests/test_system_hardening_feature_046.py -k "test_measure_text_width_number_sync" -v
```
**Expected Outcome**: PASS (diff <= `0.05 * xh` for all test numbers including `"-5"`, `"-123,45"`, `"0,39"`).

---

### Scenario 4: Clean-Environment Synthetic Bank Validation (US4)
Simulates a clean CI runner by temporarily pointing `sample_bank_v4` directly to `tests/data/kho_mau_tong_hop.json.gz`:

```powershell
pytest tests/test_number_fraction_typography.py tests/test_system_hardening_feature_046.py -v
```
**Expected Outcome**: All 14 tests in both test suites pass with 0 failures and 0 warnings.

---

### Scenario 5: Full Regression Test Suite
Executes the comprehensive repository test suite (1250+ tests) to guarantee zero regressions.

```powershell
pytest
```
**Expected Outcome**: 1255+ passed, 0 failed.
