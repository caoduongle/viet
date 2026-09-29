# Quickstart & Verification Guide: Concurrency Deep Safety and Scalability Hardening

**Feature**: `002-concurrency-deep-safety` | **Date**: 2026-09-29

This guide provides end-to-end validation procedures to verify that concurrency protection, deep schema validation, release packaging, and scaling improvements work as specified.

## Prerequisites

- Python 3.10 or higher (`py -3.10` or `py -3.12` or `python3`)
- Clean virtual environment or existing development environment with `pytest` installed

---

## Scenario 1: Verify Concurrency Lost-Update Prevention

Validates that concurrent processes saving new words do not overwrite each other's additions ([contract](contracts/bank-concurrency.md)).

```powershell
# Run the concurrent save stress test
pytest tests/test_bank.py -k "test_concurrent_save" -v
```

**Expected Outcome**:
- 8 worker processes or threads concurrently add `tu_0` through `tu_7` to a shared bank.
- Test verifies that all 8 words exist in the final saved bank file.
- Test passes with 0 lost updates.

---

## Scenario 2: Verify Deep Stroke & Runtime Metadata Schema Validation

Validates that invalid stroke coordinate counts, non-finite values, and missing runtime metadata keys are caught immediately upon loading ([contract](contracts/deep-schema.md)).

```powershell
# Run deep schema validation tests
pytest tests/test_bank.py -k "stroke or metadata or legacy" -v
```

**Expected Outcome**:
- Bank with odd stroke coordinate count raises `BankValidationError` naming the exact glyph and stroke.
- Bank with `NaN` or `inf` coordinate raises `BankValidationError`.
- Bank with missing runtime metadata (`line`, `width`, `wgaps`, etc.) is cleanly migrated with default typographic values or rejected if structurally unfixable.

---

## Scenario 3: Verify GitHub Actions Linux Packaging Integrity

Validates that the packaging command for Linux release archives correctly bundles repository documentation files.

```bash
# Simulate release archive command locally
mkdir -p dist
touch dist/hw_gui
cp README.md LICENSE dist/
tar -czf dist/hw_gui-linux.tar.gz -C dist hw_gui README.md LICENSE
tar -tzf dist/hw_gui-linux.tar.gz
```

**Expected Outcome**:
- Output includes `hw_gui`, `README.md`, and `LICENSE` without errors.

---

## Scenario 4: Verify Incremental Indexing Performance

Validates that `teach_word()` performs fast incremental updates without full dictionary re-indexing ([contract](contracts/incremental-indexing.md)).

```powershell
# Run performance test for sequential word teaching
pytest tests/test_bank.py -k "test_incremental_teach_performance" -v
```

**Expected Outcome**:
- Teaching 50 words sequentially completes within < 1.0s.

---

## Scenario 5: Verify Git History Purge Script Dry-Run

Validates that `scripts/purge_git_history.ps1` (or `.sh`) checks prerequisites safely.

```powershell
# Run history purge script with dry-run/check flag
powershell -ExecutionPolicy Bypass -File "scripts/purge_git_history.ps1" -CheckOnly
```

**Expected Outcome**:
- Script verifies git status and reports whether historical blobs exist without performing destructive actions.

---

## Scenario 6: Full Regression Suite Verification

```powershell
# Run full test suite including golden-master regression
pytest tests/test_golden_master.py tests/test_architecture.py
pytest
```

**Expected Outcome**:
- 100% of tests pass.
- 4/4 golden-master tests produce exact SHA-256 byte matches.
