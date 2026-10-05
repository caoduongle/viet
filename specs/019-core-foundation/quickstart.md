# Quickstart Validation Guide: P1 — Core Foundation & Ecosystem Harmonization

**Feature**: `019-core-foundation`  
**Date**: 2026-10-05  

This guide provides end-to-end validation procedures for verifying all Phase 1 capabilities.

---

## 1. Prerequisites

- Python 3.10+ (tested on Python 3.12).
- Dependencies installed: `pytest`, `pytest-timeout`, `ruff`, `python-docx`, `markdown-it-py`, `mdit-py-plugins`.
- Terminal encoding set to UTF-8 (`PYTHONUTF8=1`).

---

## 2. Validation Scenarios

### Scenario 1: Verify Schema v4 Single Source of Truth (Q3)

Verify that all generator scripts and schema constants align to Schema Version 4:

```bash
# 1. Kiểm tra hằng số CURRENT_VERSION trong bank_schema.py
python -c "from chuviettay.model.bank_schema import CURRENT_VERSION; assert CURRENT_VERSION == 4"

# 2. Kiểm tra script sinh kho tổng hợp xuất đúng schema v4
python scripts/gen_synthetic_bank.py --out test_synth_v4.json.gz
python -c "import gzip, json; d = json.loads(gzip.decompress(open('test_synth_v4.json.gz', 'rb').read())); assert d['schema_version'] == 4"
rm test_synth_v4.json.gz
```

Expected outcome: All version checks pass cleanly with schema version equal to 4.

---

### Scenario 2: Real-Path Layout Engine Migration (Q2)

Verify that all layout tests run through `DocumentLayoutEngine` and deprecated composer functions are removed:

```bash
# Chạy bộ test composer và chất lượng ghép chữ đã chuyển đổi
pytest tests/test_composer.py tests/test_letter_assembly_quality.py -v

# Xác nhận Step 0 real-path golden master xanh 100%
pytest tests/test_golden_master_real_path.py -v
```

Expected outcome: 100% passed without accessing deprecated `compose_document`.

---

### Scenario 3: Quantitative Acceptance Testing with Synthetic Letters (Q4)

Verify that the acceptance suite runs ink measurement metrics against synthetic letters:

```bash
# Chạy bộ test nghiệm thu định lượng
pytest tests/test_acceptance_metrics.py -v
```

Expected outcome:
- 0 missing words on `accept_sample.txt`.
- Min stroke clearance >= 0.8x pen thickness.
- Max bounding box overlap <= 10.0%.
- Median x-height within 7.94 pt ± 10%.
- Pen-to-x-height ratio within 0.15–0.20.

---

### Scenario 4: HW3 Practice Grid with f, j, w, z (F3)

Export an `hw3` practice sheet and verify that it contains 85 cells including foreign Latin letters:

```bash
# Xuất tờ lưới ký tự mẫu
python hw_note.py grid -o test_grid_hw3.xopp

# Kiểm tra sự hiện diện của f, j, w, z trong XML
python -c "
import gzip
xml = gzip.decompress(open('test_grid_hw3.xopp', 'rb').read()).decode('utf-8')
for ch in ['f', 'j', 'w', 'z', 'F', 'J', 'W', 'Z']:
    assert f'>{ch}<' in xml or f'>{ch} <' in xml, f'Thiếu chữ cái {ch} trong tờ lưới!'
print('Đã xác nhận đầy đủ 8 chữ cái f, j, w, z (hoa/thường).')
"
rm test_grid_hw3.xopp
```

Expected outcome: Grid generates 85 character cells and validates successfully.

---

### Scenario 5: Default Bank Path Resolution for Pip (F4)

Verify that `default_bank_path()` resolves to standard OS user directory when local file is absent:

```bash
python -c "
from chuviettay import paths
from unittest.mock import patch
print('Local portable path:', paths.default_bank_path())
with patch('os.path.exists', return_value=False):
    p = paths.default_bank_path()
    print('User data fallback path:', p)
    assert 'chuviettay' in p.lower()
print('Phân giải đường dẫn kho mẫu hoàn toàn chính xác.')
"
```

Expected outcome: Resolves to `%APPDATA%\chuviettay` on Windows or equivalent standard OS path on Linux/macOS.

---

### Scenario 6: Xournal++ Background Style Compliance (F7)

Verify that background styles map accurately to native Xournal++ format:

```bash
python -c "
from chuviettay.document.page_format import PageBackground
assert 'isograph' in PageBackground(style='iso_graph').to_xml()
assert 'isodotted' in PageBackground(style='iso_dotted').to_xml()
assert 'staves' in PageBackground(style='music').to_xml()
print('Ánh xạ kiểu nền Xournal++ XML hoàn toàn chính xác.')
"
```

Expected outcome: XML attributes match native Xournal++ format (`isograph`, `isodotted`, `staves`).

---

### Scenario 7: Full Quality Gates & Baseline Repro

```bash
# 1. Kiểm tra linter
ruff check .

# 2. Toàn bộ test suite
pytest -q --timeout=90 -p no:cacheprovider

# 3. Kịch bản kiểm chứng baseline
python repro_viet_baseline.py --repo . --with-pip --only F4
```

Expected outcome: Linter clean, all tests pass, F4 reports `[ĐÃ SỬA]`.
