# Quickstart & Validation Guide: Table Merged Cells & Math Root Fixes

**Feature Branch**: `009-table-and-math-layout-fixes`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This guide provides step-by-step commands to validate the table occupancy grid, single-pipeline table layout, math root stroke deduplication, and end-to-end document conversion.

---

## 1. Prerequisites

Ensure Python 3.10+ and testing dependencies are installed:
```bash
pip install -r requirements-dev.txt
# Hoặc cài đặt đầy đủ tài liệu hỗ trợ:
pip install -e .[docs]
```

---

## 2. Automated Regression Tests

### 2.1 Validate Math Root Deduplication & Stroke Count
Run the targeted math layout tests to confirm that $\sqrt{x^2+1}$ does not duplicate glyphs and produces positive vector strokes:
```bash
pytest tests/test_math_layout.py -v
```
**Expected Outcome**:
- `test_math_layout_root_deduplication`: PASSED (asserts exact glyph count, offset $\ge sign\_w$, zero unshifted duplicates).
- `test_math_layout_text_node_handwriting_strokes`: PASSED (asserts `total_glyph_strokes > 0` for expressions like $x^2+1$, $\sqrt{x}$, $\frac{x+1}{2}$).

### 2.2 Validate Table Merged Cells & Occupancy Grid
Run the targeted table layout tests to confirm `colspan`, `rowspan`, and internal border suppression:
```bash
pytest tests/test_table_layout.py -v
```
**Expected Outcome**:
- `test_table_occupancy_grid_rowspan`: PASSED (cells on row 1 skip column occupied by row 0 rowspan cell, zero overlapping bounds).
- `test_table_merged_cell_border_suppression`: PASSED (interior dividing lines within merged rectangular areas are omitted).

### 2.3 Run Entire Test Suite (with Collection Safety)
```bash
pytest -v
```
**Expected Outcome**:
- All active tests pass deterministically.
- Headless environments cleanly skip GUI tests without `ModuleNotFoundError: No module named 'tkinter'`.

---

## 3. End-to-End Sample Document Conversion

Test the CLI conversion pipeline using representative multi-format documents:

### 3.1 Plain Text Conversion (Vietnamese Diacritics & Empty Lines)
```bash
python -m chuviettay tests/fixtures/sample.txt --out sample_txt.xopp
```
- Verify that `sample_txt.xopp` is created.
- Verify paragraph vertical spacing and empty line preservation.

### 3.2 Markdown Conversion (Tables, Merged Cells, and Math)
```bash
python -m chuviettay tests/fixtures/sample.md --out sample_md.xopp
```
- Verify table layout with alignments.
- Verify inline math (e.g. $E = mc^2$) and block math formulas ($\sqrt{x^2+1}$).

### 3.3 Word Document Conversion (DOCX Tables & OMML Equations)
```bash
python -m chuviettay tests/fixtures/sample.docx --out sample_docx.xopp
```
- Verify imported DOCX tables with merged cells render without coordinate collision.
