# Quickstart: Document IR, Multi-Format Importers, Layout Engine & Math/Table Rendering

**Feature**: `007-document-ir-and-importers`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Prerequisites & Environment Setup

Run with Python 3.10+ (recommended: Python 3.12).

### 1.1 Core Development Environment
```powershell
py -3.12 -m pip install -e ".[dev]"
```

### 1.2 Full Document Extras (Markdown & DOCX)
```powershell
py -3.12 -m pip install -e ".[dev,docs]"
```

Verify installed packages:
```powershell
py -3.12 -c "import markdown_it, docx; print('Docs dependencies available!')"
```

---

## 2. Validation Scenarios

### Scenario 1: Golden-Master Backward Compatibility Guarantee
Prove that existing text rendering and golden-master SHA-256 outputs are 100% unaffected.

```powershell
py -3.12 -m pytest tests/test_golden_master.py -v
```
**Expected Outcome**: All 4 golden-master test cases pass with identical SHA-256 hashes.

---

### Scenario 2: Plaintext Import & Document IR
Verify that `.txt` documents import cleanly into `Document` IR and render into `.xopp`.

```powershell
py -3.12 -m pytest tests/test_importer_txt.py -v
```
**Expected Outcome**:
- Plain text is parsed into `Paragraph` blocks containing `Text` inline tokens.
- Controller renders document to `.xopp` matching expected stroke count.

---

### Scenario 3: Markdown Import with GFM Tables & LaTeX Math
Verify that Markdown documents containing headings, lists, tables, and math expressions render without executing raw HTML.

```powershell
py -3.12 -m pytest tests/test_importer_markdown.py -v
```
**Expected Outcome**:
- Headings are parsed with appropriate levels (1 to 6).
- GFM tables parse into `Table` blocks with matching column alignments.
- Inline math (`$...$`) and block math (`$$...$$`) parse into `MathInline` and `MathBlock`.
- Raw HTML tags like `<script>` are stripped or sanitized.

---

### Scenario 4: DOCX Import with Sequential Content & OMML Formulas
Verify that `.docx` files preserve exact paragraph and table sequence via `iter_inner_content()`, convert OMML math expressions, and flag unsupported images.

```powershell
py -3.12 -m pytest tests/test_importer_docx.py -v
```
**Expected Outcome**:
- Paragraphs and tables maintain document sequence.
- OMML math equations parse into `MathNode` AST.
- Embedded drawings and images are logged in `ImportResult.unsupported`.

---

### Scenario 5: Table Layout & Vector Stroke Border Rendering
Verify that tables calculate column widths, wrap cell text, and draw crisp stroke borders (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`).

```powershell
py -3.12 -m pytest tests/test_table_layout.py -v
```
**Expected Outcome**:
- Column widths adjust according to cell text length.
- Cells wrap multi-line text cleanly.
- Vector borders render with exact coordinates in `.xopp`.

---

### Scenario 6: Math Layout & Baseline Typographic Alignment
Verify that mathematical formulas align typographically on baselines and reserve space for missing symbols.

```powershell
py -3.12 -m pytest tests/test_math_layout.py -v
```
**Expected Outcome**:
- Fractions display numerator, fraction line, and denominator centered on math axis.
- Exponents and indices position with proportional scale and baseline offsets.
- Missing symbols produce placeholder bounding box `[ symbol ]` without breaking layout geometry.

---

### Scenario 7: Schema v3 Migration & Bank Symbol Management
Verify that legacy v2 bank dictionaries automatically upgrade to v3 with a `"symbols": {}` section.

```powershell
py -3.12 -m pytest tests/test_schema_v3.py -v
```
**Expected Outcome**:
- v2 bank files load cleanly and validate as v3 in memory.
- Added symbol samples save and reload without data corruption.

---

### Scenario 8: CLI Multi-Format Execution
Verify that the CLI auto-detects formats and processes multi-format files.

```powershell
# Auto-detect text file
py -3.12 hw_note.py write tests/fixtures/sample.txt -o test_txt.xopp

# Auto-detect markdown file
py -3.12 hw_note.py write tests/fixtures/sample.md -o test_md.xopp

# Auto-detect docx file
py -3.12 hw_note.py write tests/fixtures/sample.docx -o test_docx.xopp
```
**Expected Outcome**: All three commands complete with exit code 0 and emit structural summaries to stdout.

---

### Scenario 9: Math AST Stroke Generation (Variables and Digits) (Iteration 2)
Verify that mathematical formulas containing algebraic variables and numbers (e.g. $x^2 + y^2 = 10$) generate real handwritten strokes.

```powershell
py -3.12 -m pytest tests/test_math_ast_strokes.py -v
```
**Expected Outcome**:
- Text nodes generate non-zero `PositionedGlyph` strokes for all known variables and digits in the bank.
- Standard operators (`+`, `-`, `=`, `/`) render handwritten strokes or clean synthetic vector strokes.

---

### Scenario 10: Inline Math Single-Scaling Invariant (Iteration 2)
Verify that inline math formulas inside headings or custom-scale lines scale uniformly with surrounding text without quadratic double-scaling.

```powershell
py -3.12 -m pytest tests/test_math_scaling.py -v
```
**Expected Outcome**:
- Formula width and height scale proportionally by `scale_mult` matching adjacent text.
- Heading 1 containing inline math scales math uniformly by 1.4x without quadratic enlargement.

---

### Scenario 11: Rich Table Cells with Inlines & Alignment (Iteration 2)
Verify that table cells render math formulas, symbols, and linebreaks inside cell boundaries, and respect column alignments (`left`, `center`, `right`).

```powershell
py -3.12 -m pytest tests/test_table_rich_inlines.py tests/test_table_alignments.py -v
```
**Expected Outcome**:
- `MathInline` inside a cell generates strokes bounded within the cell width and height.
- Content is horizontally aligned according to `col_alignments`.

---

### Scenario 12: Merged Table Cells (`colspan` & `rowspan`) (Iteration 2)
Verify that merged cells span columns and rows properly and do not have interior grid lines drawn across them.

```powershell
py -3.12 -m pytest tests/test_table_merged_cells.py -v
```
**Expected Outcome**:
- Merged cell width equals the sum of spanned column widths.
- Interior horizontal and vertical borders are suppressed in spanned areas.

---

### Scenario 13: Plaintext Pipeline & Empty Line Spacing (Iteration 2)
Verify that `.txt` files preserve blank lines as vertical paragraph spacing.

```powershell
py -3.12 -m pytest tests/test_txt_unified_pipeline.py -v
```
**Expected Outcome**:
- Empty lines produce vertical spacing between paragraphs.
- `ctl.write_text()` remains byte-for-byte identical to golden master.

---

### Scenario 14: Streaming PageBuffer Memory Scaling (Iteration 2)
Verify that `DocumentLayoutEngine.render()` streams pages directly to disk via `PageBuffer`.

```powershell
py -3.12 -m pytest tests/test_page_buffer_stream.py -v
```
**Expected Outcome**:
- Multi-page documents emit completed XML sequentially.
- Memory remains constant regardless of page count.

---

### Scenario 15: Strict Format Validation & Diagnostics (Iteration 2)
Verify that unknown file formats are rejected immediately and unsupported OMML tags are recorded in diagnostics.

```powershell
py -3.12 -m pytest tests/test_format_validation.py tests/test_docx_omml_diagnostics.py -v
```
**Expected Outcome**:
- Passing `.pdf` or `.xlsx` raises `UnsupportedFormatError`.
- OMML matrices and limit structures are logged in `ImportResult.unsupported`.

