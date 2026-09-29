# Quickstart Validation Guide: Paper Sizes & Native Backgrounds

**Feature Branch**: `011-paper-size-and-background` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

This guide provides runnable scenarios to verify end-to-end functionality of paper formatting, orientations, margins, and native XOPP XML backgrounds.

---

## 1. Prerequisites & Environment Setup

Verify the Python environment and ensure current test suite passes:
```powershell
# Verify Python
python --version

# Run full existing test suite
pytest -v --timeout=30
```

---

## 2. Unit & Contract Verification Scenarios

### Scenario 1: Page Format & Unit Parsing
Run the dedicated test suite for `page_format.py`:
```powershell
pytest tests/test_page_format.py -v
```
**Expected Outcome**:
- `parse_length` converts `"5mm"`, `"21cm"`, `"8.5in"`, `14.17` accurately into PostScript points.
- `PaperSize` definitions match ISO 216 and US standards.
- Landscape orientation swaps width and height correctly (`width = max(w, h)`, `height = min(w, h)`).
- `PageBackground.to_xml()` outputs valid XOPP tags with `config="r1=..."`.

---

## 3. End-to-End CLI Verification Scenarios

### Scenario 2: Writing A4 Portrait Document with 5mm Ô Li Background
Create a test markdown file:
```markdown
# Tiêu đề bài viết

Đây là đoạn văn bản mẫu trên nền giấy ô li A4 5mm.
```
Run the CLI command:
```powershell
python hw_note.py write test.md -o output_a4_grid.xopp --paper a4 --orientation portrait --background graph --background-spacing 5mm
```
**Verification**:
Inspect the uncompressed XML output:
```powershell
python -c "import gzip; print(gzip.open('output_a4_grid.xopp', 'rt', encoding='utf-8').read()[:300])"
```
**Expected XML Attributes**:
- `<page width="595.28" height="841.89">`
- `<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>`
- Handwriting strokes follow inside `<layer>`, with no background grid lines drawn as strokes.

---

### Scenario 3: Writing A3 Landscape Document with Ruled Lines
Run the CLI command:
```powershell
python hw_note.py write test.md -o output_a3_ruled.xopp --paper a3 --orientation landscape --background ruled --background-spacing 8mm
```
**Verification**:
```powershell
python -c "import gzip; print(gzip.open('output_a3_ruled.xopp', 'rt', encoding='utf-8').read()[:300])"
```
**Expected XML Attributes**:
- `<page width="1190.55" height="841.89">`
- `<background type="solid" color="#ffffffff" style="ruled" config="r1=22.68"/>`

---

### Scenario 4: Custom Dimensions
Run the CLI command:
```powershell
python hw_note.py write test.md -o output_custom.xopp --paper custom --paper-width 150mm --paper-height 200mm --background dotted
```
**Expected XML Attributes**:
- `<page width="425.20" height="566.93">`
- `<background type="solid" color="#ffffffff" style="dotted"/>`

---

## 4. Regression & Linter Verification

Ensure no formatting or regression issues across the entire project:
```powershell
# Linting check
ruff check .

# Full test suite execution
pytest -v --timeout=30
```
**Expected Outcome**: All tests pass, 0 lint errors, 0 regressions.
