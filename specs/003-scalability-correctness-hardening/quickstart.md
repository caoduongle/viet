# Quickstart Validation Guide: Scalability, Correctness, and CI Hardening

**Feature**: `003-scalability-correctness-hardening`
**Date**: 2026-09-29
**Status**: Implemented & Verified

## 1. Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13 installed
- Virtual environment with dev dependencies:
  ```bash
  pip install -r requirements-dev.txt
  ```

---

## 2. Validation Scenarios

### Scenario 1: Headless / Incomplete Tk Runtime Test Verification
**Goal**: Verify that CI runners and headless environments with broken Tcl runtimes execute non-GUI tests with 100% pass rate and cleanly skip GUI tests.

```bash
# Run full pytest suite in current environment
python -m pytest -q

# Run specifically non-GUI unit tests
python -m pytest -q -m "not gui"
```
**Expected Outcome**: 0 errors, 0 failures, 262+ passed tests. Any GUI tests on broken Tk environments report `SKIPPED` rather than `ERROR`.

---

### Scenario 2: Incremental Indexing Parity with Rebuild
**Goal**: Verify that `add_sample_incremental` produces exact parity with `rebuild()` without losing marks or violating percentiles.

```bash
python -m pytest -q tests/test_bank.py -k "incremental"
```
**Expected Outcome**: All incremental indexing tests pass. Adding samples past the 10-mark percentile threshold preserves raw marks and matches full rebuild state.

---

### Scenario 3: Cross-Process Deletion Safety (Tombstones)
**Goal**: Verify that deleted words are not resurrected by concurrent processes saving older snapshots.

```bash
python -m pytest -q tests/test_bank.py -k "concurrent_delete or tombstone"
```
**Expected Outcome**: When Process A deletes "xin" and saves, and Process B saves a separate word, "xin" remains deleted in the final bank file.

---

### Scenario 4: Large Bank Interactive Teaching Performance
**Goal**: Verify that teaching words sequentially via `teach_word()` achieves sub-second latency on a pre-populated bank with tone marks, exercising fast-path mtime skips.

```bash
python -m pytest -q tests/test_bank.py -k "performance or teach_word"
```
**Expected Outcome**: Sequentially teaching 20+ words with tones into a bank containing 100+ existing samples executes under 1.0 second total (averaging $< 30\text{ms}$ per word), validating that full disk reload, full merge, and full collection re-indexing are bypassed during interactive teaching.

---

### Scenario 5: Deep Invariant Schema Validation
**Goal**: Verify that invalid tone indices (`ti >= len(s)`), invalid vowel positions (`vi`), and malformed pen colors are rejected with descriptive errors.

```bash
python -m pytest -q tests/test_schema.py -k "invariant or pen"
```
**Expected Outcome**: 100% of invalid samples and malformed pen configs raise `BankValidationError`.

---

### Scenario 6: Git History Purge Verification
**Goal**: Verify that `scripts/purge_git_history.ps1` and `.sh` enforce external backup safety.

```powershell
# PowerShell check-only mode
pwsh scripts/purge_git_history.ps1 -CheckOnly
```
**Expected Outcome**: Reports scan of historical personal data blobs and verifies external backup prerequisites.
