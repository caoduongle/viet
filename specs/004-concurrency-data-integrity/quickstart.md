# Quickstart Validation Guide: Concurrency Data Integrity

**Feature**: 004-concurrency-data-integrity | **Date**: 2026-09-29

---

## Prerequisites

- Python 3.10+ installed
- Repository cloned and dependencies installed: `pip install -e ".[dev]"` or `pip install -r requirements.txt`
- `pytest` available: `python -m pytest --version`
- Working directory: repository root (`d:\viet\app` or equivalent)

---

## Validation Scenario 1: Safe Save Abort on Corrupt Disk (FR-001)

**Purpose**: Verify `Bank.save()` refuses to overwrite a corrupt file.

### Commands

```bash
# Run targeted test
python -m pytest tests/test_bank.py -k "corrupt" -v

# Expected: test passes, verifying BankError is raised and disk file untouched
```

### Expected Outcome

- `Bank.save()` raises `BankCorruptedError` (or `BankError` subclass)
- Temporary `.tmp` file is cleaned up
- Original corrupt file on disk remains byte-identical
- With `force_overwrite=True`: save succeeds with audit warning logged

---

## Validation Scenario 2: Tombstone Generation Prevents Stale Resurrection (FR-002, FR-003)

**Purpose**: Verify stale snapshot additions don't resurrect deleted words.

### Commands

```bash
# Run tombstone tests
python -m pytest tests/test_bank_tombstones.py -v

# Expected: all tests pass including generation-aware resurrection prevention
```

### Expected Outcome

- Process A deletes "foo" at generation G1 → tombstone recorded with `generation: G1`
- Process B adds sample to "foo" from snapshot at G0 < G1 → addition rejected during merge
- Fresh session teaches "foo" at G2 > G1 → tombstone revoked, word restored
- Legacy float tombstones loaded and normalized without errors

---

## Validation Scenario 3: Multi-Process Concurrency (FR-007)

**Purpose**: Verify cross-process file locking and merge under true OS processes.

### Commands

```bash
# Run multi-process concurrency tests
python -m pytest tests/test_bank.py -k "multiprocess" -v

# Expected: concurrent OS processes complete without corruption
```

### Expected Outcome

- Multiple OS processes write to same `.json.gz` file concurrently
- `FileLock` prevents interleaving
- Final bank state contains all expected additions and deletions
- No unhandled `LockTimeoutError` or file corruption

---

## Validation Scenario 4: Large-Bank Benchmark (FR-008)

**Purpose**: Verify sub-second save latency on large banks.

### Commands

```bash
# Run benchmark test (may take 10-30 seconds)
python -m pytest tests/test_bank.py -k "benchmark_large" -v -s

# Expected: per-word latency printed, all assertions pass
```

### Expected Outcome

- Synthetic bank with ≥5,000 samples created
- 20 consecutive `add_sample_incremental()` + `save()` operations complete
- Per-word latency < 1.0 second
- Fast-path cache validation bypasses disk re-read on consecutive saves

---

## Validation Scenario 5: Drop Index Pruning (FR-004)

**Purpose**: Verify `drop()` immediately cleans all in-memory indexes.

### Commands

```bash
# Run drop/index tests
python -m pytest tests/test_bank.py -k "drop" -v
python -m pytest tests/test_bank_indexing.py -v

# Expected: can() returns False immediately after drop, indexes clean
```

### Expected Outcome

- After `bank.drop("bà")`: `bank.can("bà")` returns `False`
- `tl[strip_tone("bà")]` has no entries for "bà"
- `_raw_marks[T]` has no marks with `_src == "bà"`
- `marks[T]` is refreshed

---

## Validation Scenario 6: Tombstone Aliasing Fix (FR-005)

**Purpose**: Verify dictionary identity preserved after merge.

### Commands

```bash
# Run merge/aliasing tests
python -m pytest tests/test_bank_tombstones.py -v

# Expected: self._tombstones is self.d["tombstones"] after merge
```

### Expected Outcome

- After `merge_bank_dicts()` + re-bind: `bank._tombstones is bank.d["tombstones"]` is `True`
- Mutations to `bank._tombstones` are reflected in `bank.d["tombstones"]`

---

## Validation Scenario 7: Tone Mark Optimization (FR-006)

**Purpose**: Verify optimized percentile calculation matches rebuild.

### Commands

```bash
# Run indexing parity tests
python -m pytest tests/test_bank_indexing.py -v

# Expected: incremental marks == rebuild marks, no 4x sorted() calls
```

### Expected Outcome

- `marks[T]` from incremental additions matches `marks[T]` from `rebuild()` exactly
- `_sorted_dy` and `_sorted_dx` maintained via `bisect.insort()`

---

## Validation Scenario 8: CI Lint Integration (FR-010)

**Purpose**: Verify ruff check passes in CI.

### Commands

```bash
# Local verification
ruff check .

# Expected: 0 errors, 0 warnings (or only pre-existing accepted warnings)
```

### Expected Outcome

- `ruff check .` exits with code 0
- CI workflow includes a dedicated `lint` job before test matrix

---

## Full Regression Suite

```bash
# Run all tests
python -m pytest tests/ -v --tb=short

# Expected: 270+ passed (262 existing + new tests), 0 failed
# Windows 3.10 without Tk: GUI tests skipped, all others pass
```

---

## References

- Data model: [data-model.md](data-model.md)
- Research decisions: [research.md](research.md)
- Feature specification: [spec.md](spec.md)
