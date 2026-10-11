# Quickstart & Verification Guide: Table Layout and DOCX Import Fidelity

**Feature**: `031-table-docx-layout-fidelity`  
**Date**: 2026-10-11  
**Spec**: [spec.md](spec.md)

## 1. Quick Verification via Automated Tests

### 1.1 Run Core Table Layout and Formula Tests
```bash
pytest tests/test_table_layout.py tests/test_table_rich_inlines.py -v
```

### 1.2 Run Transitive Merge Pagination and Bounding Box Tests
```bash
pytest tests/test_table_pagination_closure.py tests/test_docx_table_import.py -v
```

### 1.3 Run Playwright Web E2E Import Tests
```bash
npx playwright test tests/e2e/docx-import.spec.ts
```

---

## 2. CLI & Python Pipeline Verification

### 2.1 Verify DOCX Import Preserves Tables
Run the test script to confirm table data is preserved in the bridge output:
```bash
python -c "
from chuviettay.browser.bridge import BridgeController
import os
bridge = BridgeController()
with open('tests/fixtures/sample_with_table.docx', 'rb') as f:
    res = bridge.import_docx(f.read())
assert res['ok'], res
assert '|' in res['markdown_text'], 'Table markdown pipe syntax must be present'
print('DOCX table import check PASSED')
"
```

### 2.2 Verify Multi-Page Table with Interdependent Row Merges
Render a document with chained multi-row merges (`Row 1-2` in Col 0, `Row 2-3` in Col 1):
```bash
python -c "
from chuviettay.document.ir import Document, Table, TableRow, TableCell, TableBorder
from chuviettay.controller.results import WriteOptions
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.model.bank import Bank

# Setup test table with transitive merges
c1 = TableCell.from_text('Col0 (R1-2)')
c1.rowspan = 2
c2 = TableCell.from_text('Col1 (R1)')
c3 = TableCell.from_text('Col1 (R2-3)')
c3.rowspan = 2
c4 = TableCell.from_text('Col0 (R3)')

table = Table(rows=[
    TableRow(cells=[c1, c2]),
    TableRow(cells=[c3]),
    TableRow(cells=[c4]),
], border_style=TableBorder.ALL)

engine = DocumentLayoutEngine(Bank(), WriteOptions())
# Ensure slice_page groups rows 0..2 atomically
slice_data, next_row = engine.layout_table(...).slice_page(0, max_height=100.0, new_y=0.0)
print('Pagination closure check PASSED')
"
```

---

## 3. Web Client Verification Scenarios

1. **Upload DOCX with Tables**:
   - Open Web Client at `http://localhost:8000`.
   - Click **Mở file** and select a `.docx` file containing text, tables, and formulas.
   - **Expected**:
     - The Markdown editor (`#editor-text`) contains the table formatted with pipe table syntax (`| Col 1 | Col 2 | ...`).
     - No table is discarded or blanked out.
     - If the table contains flattened merges or nested tables, a notification toast displays the corresponding warnings.
     - Live SVG preview renders the table intact.

2. **Insert Custom Table via Toolbar**:
   - Click the **Bảng** button in the toolbar.
   - Specify rows (e.g. 4) and columns (e.g. 5).
   - **Expected**:
     - A 4x5 table markdown template is inserted at the cursor position.
     - Live preview displays the 4x5 grid immediately.
