# Research: GUI Test Exception Scope Refinement, Tk Probe Contract Alignment, Server-Side Object Clarification, and CI Maintenance

**Feature**: 006-test-quality-and-maintenance | **Date**: 2026-09-29

---

## 1. GUI Test Exception Scope: Narrowing from `Exception` to `tkinter.TclError`

### Problem
In `tests/test_gui.py`, `MainWindow` construction and the `app` fixture wrapped initialization with:
```python
except Exception as e:
    pytest.skip(f"Không thể khởi tạo hoặc cập nhật MainWindow ({e})")
```
This catches all subclasses of `Exception`, including `AttributeError`, `TypeError`, `ValueError`, `KeyError`, and `BankError`. If a developer introduces a defect in `AppController`, `Bank`, `WriteTab`, or `TeachTab`, the test suite silently converts the failure into `SKIPPED`, resulting in a false-green CI run.

### Decision
Catch strictly `tkinter.TclError` (and import `tkinter as tk` locally if needed):
```python
except tk.TclError as e:
    pytest.skip(f"Lỗi runtime Tk/Tcl khi khởi tạo hoặc cập nhật MainWindow ({e})")
```
If `tkinter` is not available at all, the module-level probe `is_tk_usable()` already marks all tests with `pytest.mark.gui` as skipped before test execution. Therefore, within the test body, the only legitimate reason to skip is a low-level Tcl/Tk runtime error (e.g. missing script file, headless display missing `$DISPLAY`, or font failure). All application logic errors will propagate and fail the test.

### Alternatives Considered
- *Custom exception wrapper*: Over-engineering; `tkinter.TclError` is the standard exception raised by the Python Tkinter C binding.
- *Removing try-except entirely*: Would cause crashes on partially configured Tk environments (such as the Windows Python 3.11 runner that tripped on `listbox.tcl`). The targeted `except tk.TclError` gives the exact resilience needed without hiding application bugs.

---

## 2. Tk/Tcl Runtime Probe: Explicit `$tcl_library/init.tcl` Validation

### Problem
The specification for feature 005 stated that the probe must verify `init.tcl`, `tk.tcl`, and `listbox.tcl`. The existing implementation in `tests/conftest.py` checked `$tk_library` for `tk.tcl`, `listbox.tcl`, `button.tcl`, and `entry.tcl`, but relied on `tk.Tk()` to load `init.tcl` implicitly.

### Decision
Explicitly probe `$tcl_library` for `init.tcl`:
```python
# 1. Thẩm tra tệp script Tcl cốt lõi (init.tcl)
try:
    tcl_lib = root.tk.eval("set tcl_library")
    init_path = os.path.join(tcl_lib, "init.tcl")
    if not os.path.exists(init_path):
        root.tk.eval("source [file join $tcl_library init.tcl]")
except Exception as tcl_err:
    raise RuntimeError(f"Thiếu hoặc không thể nạp tệp thư viện Tcl init.tcl ({tcl_err})") from tcl_err

# 2. Thẩm tra các tệp script Tk cốt lõi (tk.tcl, listbox.tcl, button.tcl, entry.tcl)
try:
    tk_lib = root.tk.eval("set tk_library")
    for req_script in ("tk.tcl", "listbox.tcl", "button.tcl", "entry.tcl"):
        script_path = os.path.join(tk_lib, req_script)
        if not os.path.exists(script_path):
            root.tk.eval(f"source [file join $tk_library {req_script}]")
except Exception as script_err:
    raise RuntimeError(f"Thiếu hoặc không thể nạp tệp thư viện Tk ({script_err})") from script_err
```
This aligns the codebase 1:1 with the architectural specification.

---

## 3. Git History Sanitization vs. Remote Platform Object Caching

### Problem
After rewriting branch history with `git filter-branch` (or `git-filter-repo`), all commits in the branch ref history (`refs/heads/main`) are completely free of the sensitive blobs. However, on remote platforms like GitHub, previously pushed commit objects remain accessible via direct SHA URL or GitHub Commit API until GitHub's server-side garbage collection cleans unreferenced objects or the repository owner requests a cache purge via GitHub Support.

Claiming that "all old objects have immediately vanished from GitHub storage" is technically inaccurate.

### Decision
Update all operational documentation and script output to clearly distinguish:
1. **Branch Ref Ancestry**: 100% sanitized. `git log --all` and branch clones have 0 references to purged blobs.
2. **Remote Object Database Caching**: Remote hosting platforms (GitHub) maintain loose objects until repository GC runs. Users needing immediate server-side cache eviction should contact GitHub Support to run `git gc --prune=now` on the server repository.

---

## 4. Documentation Discrepancy & Test Count Reconciliation

### Findings
- In `specs/005-ci-tk-and-integrity-alignment/quickstart.md`, the 50-save benchmark was mistakenly referenced as `SC-004` instead of `SC-003`.
- In `README.md`, line 175 stated "Hơn 210 ca kiểm thử tự động", whereas the test suite currently contains 248 tests (243 passed, 5 skipped on headless). Updating this to "Hơn 240 ca kiểm thử tự động" reflects accurate, up-to-date metrics.

---

## 5. CI Workflow Maintenance & GitHub Actions Versions

### Findings
- `.github/workflows/ci.yml` currently specifies:
  - `actions/checkout@v4` (stable, Node 20)
  - `actions/setup-python@v5` (stable, Node 20, built-in pip caching)
  - `softprops/action-gh-release@v2` (stable)
- These versions are currently the recommended stable releases across GitHub Actions runners. We verify that all pin configurations and dependency caching paths (`requirements-dev.txt`) remain fully functional.
