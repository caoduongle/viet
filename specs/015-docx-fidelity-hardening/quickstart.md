# Quickstart Validation Guide: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Feature**: `015-docx-fidelity-hardening`  
**Date**: 2026-09-30  
**Status**: Ready  

---

## 1. Prerequisites

- Python 3.10+ virtual environment activated.
- Project dependencies installed:
  ```bash
  pip install -e .
  pip install -r requirements-dev.txt
  ```

---

## 2. Validation Scenario 1: Cross-Platform Converter Cache

Prove that `is_word_available()` caches `False` deterministically on non-Windows platforms.

### Execution Command:
```bash
pytest tests/test_fidelity_pdf_first.py -k "test_r6_converter_availability_caching" -vv
```

### Expected Output:
- `1 passed`
- On Linux/macOS or simulated non-Windows, `FidelityConverter._word_available_cache` is `False` after calling `is_word_available()`.

---

## 3. Validation Scenario 2: Native OpenXML Surgical Whiteout & Preservation

Verify that `WhiteoutBackgroundGenerator.create_whiteout_docx` whitens text while preserving media assets bit-for-bit without `python-docx` full document re-serialization.

### Execution Command:
```bash
pytest tests/test_docx_fidelity.py -k "whiteout" -vv
```

### Verification Criteria:
- Text runs (`<w:r>` and `<a:r>`) contain `#FFFFFF` color values.
- Embedded media (`word/media/*.png`), shapes, and relationship files (`_rels/`) match original checksums.
- No `python-docx` whole-document save side-effects.

---

## 4. Validation Scenario 3: GUI Mode State Locking

Verify that switching modes in `WriteTab` properly disables/enables layout controls.

### Execution Command:
```bash
pytest tests/test_gui_write_tab.py -vv
```

### Interactive Test:
1. Launch GUI:
   ```bash
   python hw_gui.py
   ```
2. Navigate to "Viết văn bản" (Write Tab).
3. Toggle "Chế độ DOCX" from "Tự do (Semantic)" to "Khóa bố cục & ảnh (Fidelity)".
4. Check that Khổ giấy, Chiều giấy, Nền giấy, Khoảng cách (mm), and "Cỡ..." are disabled.
5. Switch back to "Tự do (Semantic)" and verify they are re-enabled.

---

## 5. Validation Scenario 4: Full Test Suite Regression Check

Ensure all 472+ tests pass with zero regressions:

### Execution Command:
```bash
pytest -vv --timeout=30
```

### Expected Outcome:
- All 472+ tests pass cleanly.
