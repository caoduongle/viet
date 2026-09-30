# Quickstart Validation Guide: Unified Pipeline & Margin Boundaries

**Feature**: `012-unify-write-text-pipeline` | **Date**: 2026-09-30

---

## 1. Scenario 1: Direct Text API Call with A3 Landscape & Graph Background

Verify that `controller.write_text()` outputs exact A3 dimensions and background tags:

```python
from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
import gzip

ctl = AppController("bank.json.gz")
ctl.load_bank()

opts = WriteOptions(
    paper="a3",
    orientation="landscape",
    background="graph",
    background_spacing=14.17,  # 5mm
    seed=1
)

out_file = "test_direct_a3.xopp"
ctl.write_text("Chào buổi sáng từ direct text", opts, out_file)

raw = gzip.decompress(open(out_file, "rb").read()).decode("utf-8")
assert '<page width="1190.55" height="841.89">' in raw
assert 'style="graph"' in raw
assert 'config="r1=14.17"' in raw
print("Scenario 1: SUCCESS")
```

---

## 2. Scenario 2: Margin Bound Validation Rejection

Verify that invalid margin configurations raise `ValueError`:

```python
import pytest
from chuviettay.controller.results import WriteOptions

# Horizontal overflow: 350 + 300 = 650 pt > A4 width (595.28 pt)
opts_horiz = WriteOptions(paper="a4", margin_left=350.0, margin_right=300.0)
with pytest.raises(ValueError, match="nhỏ hơn bề ngang trang"):
    opts_horiz.validate()

# Vertical overflow: 500 + 400 = 900 pt > A4 height (841.89 pt)
opts_vert = WriteOptions(paper="a4", margin_top=500.0, margin_bottom=400.0)
with pytest.raises(ValueError, match="nhỏ hơn bề dọc trang"):
    opts_vert.validate()

print("Scenario 2: SUCCESS")
```

---

## 3. Scenario 3: GUI Direct-Text Regression Test

Run the fortified GUI tests:
```powershell
pytest tests/test_gui_document.py -v
```

Expected outcome:
- `test_gui_write_tab_paper_and_background_options` verifies direct text entry with `current_doc is None` renders with exact A3 landscape dimensions and graph background.

---

## 4. Scenario 4: Full Automated Regression

Verify full system test matrix and linting:
```powershell
ruff check .
pytest -v --timeout=60
```
Expected outcome: All tests pass, 0 regressions.
