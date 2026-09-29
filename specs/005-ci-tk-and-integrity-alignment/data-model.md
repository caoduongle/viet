# Data Model: CI Environment Hardening, Tk/Tcl Probing, and Data Integrity Alignment

**Feature Branch**: `005-ci-tk-and-integrity-alignment` | **Date**: 2026-09-29

---

## Entity: Bank Model Mutations & Drop Invariants

### Fields

| Field | Type | Description | Invariant / Behavior in Feature 005 |
|---|---|---|---|
| `words` | `dict[str, list[dict]]` | Active word samples | Target of `drop(word)`. Only words present in `words` trigger tombstone creation. |
| `_generation` | `int` | Monotonic mutation counter | Incremented **only** when an existing word is actually dropped (`len(samples) > 0`). Never incremented on non-existent drops. |
| `_tombstones` | `dict[str, dict]` | Structured tombstone records | Keyed by word label. Values: `{"deleted_at": float, "generation": int}`. Unaltered when dropping non-existent words. |
| `pen.color` | `str` | Hex color string | Strictly validated via `re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?")`. |

---

## State Transition: `Bank.drop(word)`

```mermaid
flowchart TD
    A["Bank.drop(word)"] --> B{"word in self.words?"}
    B -- No --> C["Return 0 (No-op: no tombstone, no generation increment)"]
    B -- Yes --> D["Increment self._generation"]
    D --> E["Record tombstone in self._tombstones"]
    E --> F["Pop samples from self.words"]
    F --> G["Prune self.tl substitution index"]
    G --> H["Remove harvested marks from self._raw_marks"]
    H --> I["Refresh self.marks via _refresh_tone_marks()"]
    I --> J["Return count of removed samples"]
```

---

## Entity: Tk/Tcl Runtime Diagnostic State (`conftest.py`)

| Field | Type | Description |
|---|---|---|
| `_tk_usable_cached` | `bool \| None` | Cached result of the deep runtime probe (`None` before probe, `True`/`False` after). |
| `_tk_unusable_reason` | `str` | Detailed failure reason (exception string or missing script filename) if unusable. |

### Probe Lifecycle

```mermaid
flowchart TD
    A["is_tk_usable() called"] --> B{"Cached != None?"}
    B -- Yes --> C["Return cached bool"]
    B -- No --> D["try: import tkinter, ttk"]
    D -- Exception --> FAIL["_tk_usable_cached = False, record reason"]
    D -- Success --> E["root = tk.Tk()"]
    E -- Exception --> FAIL
    E -- Success --> F["Probe required scripts: init.tcl, tk.tcl, listbox.tcl"]
    F -- Script Missing/Error --> FAIL
    F -- Scripts OK --> G["Instantiate widgets: ttk.Notebook, ttk.Button, tk.Listbox"]
    G -- Exception --> FAIL
    G -- Success --> H["root.update_idletasks(); root.update()"]
    H -- Exception --> FAIL
    H -- Success --> PASS["_tk_usable_cached = True; root.destroy()"]
    FAIL --> RET["Return False"]
    PASS --> RETT["Return True"]
```
