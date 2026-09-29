# Quickstart Validation Guide: CI Environment Hardening and Data Integrity Alignment

**Feature**: 005-ci-tk-and-integrity-alignment | **Date**: 2026-09-29

---

## Prerequisites

- Python 3.10+ installed
- Working directory: repository root (`d:\viet\app`)
- Dependencies installed: `pip install -e ".[dev]"`

---

## Validation Scenario 1: Deep Tk/Tcl Runtime Probing & GUI Test Skipping

**Purpose**: Verify that incomplete or broken Tk/Tcl environments cleanly skip all GUI tests without uncaught crashes.

### Commands

```bash
# Run GUI tests
pytest tests/test_gui.py -v

# Run the specific typo startup test
pytest tests/test_gui.py -k "bank_sai" -v
```

### Expected Outcome
- On environments without Tk or missing critical Tcl scripts (`listbox.tcl`): all tests in `tests/test_gui.py` are reported as `SKIPPED` with an informative reason.
- On working Tk environments: tests execute and pass cleanly.
- 0 failed tests, 0 uncaught `TclError` exceptions.

---

## Validation Scenario 2: Reconciled 50-Save Large-Bank Benchmark (SC-004)

**Purpose**: Verify sub-second interactive save latency across 50 consecutive additions on a $\ge 5,000$ sample profile.

### Commands

```bash
# Run large-bank benchmark test
pytest tests/test_bank.py -k "benchmark_large" -v -s
```

### Expected Outcome
- Generates a synthetic bank with 5,000 samples.
- Executes 50 consecutive `add_sample_incremental()` + `save()` operations.
- Asserts:
  - Average latency $< 1.0\text{s}$
  - Maximum latency $< 2.0\text{s}$
  - Total elapsed time $< 30.0\text{s}$
- Test passes cleanly.

---

## Validation Scenario 3: Non-Existent Word Drop Does Not Create Dead Tombstone

**Purpose**: Verify `Bank.drop(word)` returns 0 and does not mutate `_tombstones` or `_generation` when dropping an absent word.

### Commands

```bash
# Run drop tests
pytest tests/test_bank.py -k "drop" -v
```

### Expected Outcome
- Calling `bank.drop("unknown_word")` returns 0.
- `bank._tombstones` does not contain "unknown_word".
- `bank._generation` is unchanged.

---

## Validation Scenario 4: Strict Color Hex Matching with `re.fullmatch`

**Purpose**: Verify `pen.color` strictly validates hex format without allowing trailing garbage characters.

### Commands

```bash
# Run schema tests
pytest tests/test_schema.py -k "pen_color" -v
```

### Expected Outcome
- `#000000`, `#ffffff`, `#000000ff` pass.
- `#000000\nextra`, `red`, `#123` raise `BankValidationError`.

---

## Validation Scenario 5: Full Regression Suite

```bash
pytest -v
ruff check .
```

### Expected Outcome
- `ruff check .` exits 0 (All checks passed!).
- `pytest -v` passes 100% (239+ passed on headless environment, $\ge 280$ passed on full Tk runners).
