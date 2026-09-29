# Data Model & Contracts: Test Quality, Tk Probe Contract, and Maintenance

**Feature**: 006-test-quality-and-maintenance | **Date**: 2026-09-29

---

## 1. Entities

### GUI Test Skip Guard
- **Type**: Exception boundary
- **Location**: `tests/test_gui.py` (`MainWindow` initialization and `app` fixture)
- **Allowed Exception**: `tkinter.TclError`
- **Behavior**:
  - Catches: `tkinter.TclError` when Tk GUI subsystem cannot allocate windows or load Tcl widgets.
  - Re-raises / Propagates: `Exception`, `AttributeError`, `TypeError`, `ValueError`, `KeyError`, `BankError`, `AssertionError`.
  - Effect: Converts platform GUI impossibility to `pytest.skip(...)`, while failing test on application logic regressions.

### Tk/Tcl Runtime Probe
- **Type**: Diagnostic probe function
- **Location**: `tests/conftest.py` (`is_tk_usable()`)
- **Probed Resources**:
  - `$tcl_library/init.tcl`: Tcl core script
  - `$tk_library/tk.tcl`: Tk core script
  - `$tk_library/listbox.tcl`: Listbox widget script
  - `$tk_library/button.tcl`: Button widget script
  - `$tk_library/entry.tcl`: Entry widget script
- **Output**: `bool` (cached), with diagnostic string in `_tk_unusable_reason`.

### Purge Operational Notice
- **Type**: User/Admin console output contract
- **Location**: `scripts/purge_git_history.ps1`, `scripts/purge_git_history.sh`
- **Output Components**:
  - `Branch Ancestry`: Clean (zero references to purged blobs in `git log --all`).
  - `Backup Bundle`: Absolute path to standalone `.bundle` file.
  - `Remote Caching Notice`: Explicit disclaimer that remote platforms (GitHub) maintain unreachable objects by direct SHA until backend GC or GitHub Support request.
  - `Force Push Instructions`: `git push --force --mirror origin`.

---

## 2. Interface Contracts

### `tests/conftest.py` Probe Contract
```python
def is_tk_usable() -> bool:
    """Returns True only if:
    1. tkinter and tkinter.ttk can be imported.
    2. tk.Tk() can be instantiated.
    3. $tcl_library/init.tcl exists or can be sourced.
    4. $tk_library/{tk.tcl, listbox.tcl, button.tcl, entry.tcl} exist or can be sourced.
    5. ttk.Notebook, ttk.Button, tk.Listbox, tk.Canvas can be rendered.
    6. root.update_idletasks() and root.update() succeed without TclError.
    """
```

### `tests/test_gui.py` Guard Contract
```python
try:
    w = MainWindow(...)
    w.withdraw()
    w.update()
except tk.TclError as e:
    pytest.skip(f"Lỗi runtime Tk/Tcl khi khởi tạo hoặc cập nhật MainWindow ({e})")
```
*(No `except Exception` permitted)*.
