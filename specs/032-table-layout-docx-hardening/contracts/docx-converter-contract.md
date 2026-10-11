# Contract: DOCX Table Conversion & Importer Order

**Modules**: `chuviettay/browser/bridge.py` & `chuviettay/importer/docx_importer.py`

---

## 1. DOCX to Markdown Occupancy Grid Contract (`bridge.py`)

### Input
- `b: Table` with rows and cells from `DocxImporter`.
- Cells may have `colspan >= 1` and `rowspan >= 1`.

### Behavior
1. Calculate logical table dimensions:
   ```python
   grid: list[list[Any]] = []
   for r_idx, row in enumerate(b.rows):
       # Map cell into first unassigned slot in grid
       # Fill grid[r_idx .. r_idx+rowspan-1][c_slot .. c_slot+colspan-1]
   num_cols = max(len(row) for row in grid)
   ```
2. For each row $r$:
   - For column $c \in [0, \text{num\_cols}-1]$:
     - If `grid[r][c]` is the origin of a cell: output extracted cell Markdown text.
     - If `grid[r][c]` is part of a span from another cell: output `" "` (empty placeholder).
     - If slot is empty: output `" "`.
3. Output header delimiter line with `num_cols` column alignment markers.

---

## 2. DOCX Cell Block Document Order Contract (`docx_importer.py`)

### Input
- `c: docx.table._Cell` representing an individual table cell in python-docx.

### Behavior
- Instead of calling `c.paragraphs` followed by `c.tables`, iterate over `c._tc.iterchildren()`:
  - If child is `<w:p>`: parse as paragraph block `Paragraph`.
  - If child is `<w:tbl>`: parse as nested table `Table`.
- Append each block to `cell_blocks` in encounter order.
- Guarantees: Given XML `<w:p>A</w:p><w:tbl>...</w:tbl><w:p>B</w:p>`, `cell_blocks` contains `[Paragraph(A), Table(...), Paragraph(B)]`.
