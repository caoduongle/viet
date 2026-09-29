# Quickstart Validation Guide: Test Quality, Tk Probe Contract, and Maintenance

**Feature**: 006-test-quality-and-maintenance | **Date**: 2026-09-29

---

## Prerequisites

- Python 3.10+ installed
- Working directory: repository root (`d:\viet\app`)
- Dependencies installed: `pip install -r requirements-dev.txt`

---

## Validation Scenario 1: Narrowed GUI Test Skip Guard Protects Test Sensitivity

**Purpose**: Verify that `MainWindow` guards catch `tkinter.TclError` for platform issues, but do NOT catch application errors (preventing false-green CI).

### Commands

```bash
# Run GUI resilience tests
pytest tests/test_gui_resilience.py -v

# Run GUI tests
pytest tests/test_gui.py -v
```

### Expected Outcome
- When `tkinter.TclError` is raised by Tk/Tcl platform failures, tests are skipped with `SKIPPED`.
- If an application logic error (`AttributeError`, `BankError`, `ValueError`) is raised, the guard does NOT catch it, and the test fails with `FAILED`.

---

## Validation Scenario 2: Tk/Tcl Probe Validates `init.tcl` and `listbox.tcl`

**Purpose**: Verify that `is_tk_usable()` in `tests/conftest.py` directly validates both `$tcl_library/init.tcl` and `$tk_library/listbox.tcl`.

### Commands

```bash
pytest tests/test_gui_resilience.py -k "is_tk_usable" -v
```

### Expected Outcome
- Probe queries both `$tcl_library` and `$tk_library`.
- Missing `init.tcl` or `listbox.tcl` triggers `is_tk_usable() == False`.

---

## Validation Scenario 3: Purge Scripts and Documentation Explain Remote Object Caching

**Purpose**: Confirm that `scripts/purge_git_history.ps1`, `scripts/purge_git_history.sh`, `README.md`, and `CHANGELOG.md` explicitly explain local branch history sanitization vs remote GitHub object caching.

### Commands

```bash
powershell.exe -ExecutionPolicy Bypass -File .\scripts\purge_git_history.ps1 -CheckOnly
```

### Expected Outcome
- The script output mentions that while branch history is sanitized, remote hosting servers like GitHub retain loose commit objects until backend GC or a GitHub Support request.

---

## Validation Scenario 4: Documentation Test Count and Numbering

**Purpose**: Verify that `README.md` reports "Hơn 240 ca kiểm thử tự động" and `specs/005-ci-tk-and-integrity-alignment/quickstart.md` references SC-003 for the benchmark.

### Commands

```bash
git grep -n "240" README.md
git grep -n "SC-003" specs/005-ci-tk-and-integrity-alignment/quickstart.md
```

### Expected Outcome
- Clean matches found; no outdated counts or wrong criteria references.

---

## Validation Scenario 5: Full Regression Suite & Linter

```bash
ruff check .
pytest -v
```

### Expected Outcome
- 0 lint errors.
- 100% test pass rate (243 passed, 5 skipped on headless environments, 0 failed).
