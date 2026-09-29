# Phase 0 Research: Table Occupancy Grid, Single-Pipeline Architecture, and Math Root Stroke Deduplication

**Feature Branch**: `009-table-and-math-layout-fixes`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md)

## Executive Summary

This research resolves the two critical defects (P0) and architectural debts (P1) identified during review of commit `8b4aae0bf83c7bca7c45d60c668333c071dd3b87`:
1. **Math Root Radical Stroke Duplication (P0)**: Eliminate character and stroke double-rendering in `RootNode` measurement within `chuviettay/layout/math_layout.py`.
2. **Table Multi-Row Merged Cells (`rowspan`) (P0)**: Replace rudimentary per-row column indexing with a canonical 2D cell occupancy grid (`grid[row][col]`), preventing cell overlaps and horizontal misalignment when `rowspan > 1`.
3. **Table Layout Pipeline Unification (P1)**: Consolidate table geometry, text wrapping, and pagination slicing into `TableLayoutEngine` as the single source of truth, removing redundant layout code from `DocumentLayoutEngine.render()`.
4. **Testing & Verification Hardening (P1/P2)**: Expand test suites with merged-cell geometry assertions, mathematical glyph stroke count verifications, headless test collection guards, and end-to-end sample document conversion (`sample.txt`, `sample.md`, `sample.docx`) to `.xopp`.

---

## 1. Mathematical Root Node Layout & Glyph Deduplication (P0)

### 1.1 Problem Analysis
In `chuviettay/layout/math_layout.py`, lines 339–356:
```python
# Đoạn mã gặp lỗi:
strokes = list(rad_item.strokes)
glyphs = list(rad_item.glyphs)

# Vẽ nét dấu căn (radical_pts)
strokes.append(PositionedStroke(points=radical_pts, width=1.41 * eff_scale))

# Dời radicand sang phải dấu căn:
for g in rad_item.glyphs:
    glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + sign_w, y=g.y, scale=g.scale))
for s in rad_item.strokes:
    strokes.append(PositionedStroke(points=[(pt[0] + sign_w, pt[1]) for pt in s.points], width=s.width, color=s.color))
```
Because `strokes` and `glyphs` initially copy `rad_item.strokes` and `rad_item.glyphs`, the original unshifted characters remain at $x = 0$, and then the shifted characters are appended at $x + \text{sign\_w}$. For an expression such as $\sqrt{x^2+1}$, this results in:
- Characters $x, 2, +, 1$ being rendered twice: once at the root origin and once under the horizontal bar.
- Doubled vector strokes and bloated file size.
- Visual ghosting and stroke collisions.

### 1.2 Architectural Decision
- **Decision**: Initialize `glyphs = []` and `strokes = []`. Append the radical sign stroke to `strokes`. If `node.degree` is present (for nth-root $\sqrt[n]{x}$), measure and position the degree glyphs/strokes above the hook. Then, append *only* the horizontally shifted `rad_item.glyphs` and `rad_item.strokes` (offset by `sign_w`).
- **Rationale**: Completely prevents duplication while preserving exact horizontal positioning under the radical bar.
- **Alternatives Considered**:
  - *Modifying `rad_item` in-place*: Rejected because `rad_item` may be shared or referenced higher in the AST stack; immutability or fresh construction is substantially safer.

---

## 2. Table Merged Cells: 2D Occupancy Grid (P0)

### 2.1 Problem Analysis
In `chuviettay/layout/engine.py` (lines 357–430) and `chuviettay/layout/table_layout.py` (lines 185–215):
```python
# Cả hai nơi đều lặp qua từng hàng và reset c_curr = 0:
for r_idx, row in enumerate(padded_rows):
    c_curr = 0
    for cell in row.cells:
        cs = max(1, getattr(cell, "colspan", 1))
        cell_x = self.x0 + sum(col_widths[:c_curr])
        ...
        c_curr += cs
```
Consider a table:
```text
Row 0: [ Cell A (rowspan=2) ] [ Cell B ]
Row 1: [ Cell C ]
```
When Row 1 is processed, `c_curr` starts at `0`. Cell C is placed at column 0 with $x = x_0$, directly on top of Cell A.
Furthermore, the number of logical columns on Row 1 does not equal the physical number of cells in `row.cells`.

### 2.2 Architectural Decision
- **Decision**: Implement a canonical 2D occupancy grid:
  ```python
  grid: list[list[LaidOutCell | None]] = [[None] * num_cols for _ in range(num_rows)]
  ```
  For each row $r$ from $0$ to $\text{num\_rows} - 1$:
  - Maintain an active column cursor $c = 0$.
  - For each cell in `row.cells`:
    - While $c < \text{num\_cols}$ and `grid[r][c] is not None`: increment $c$ (skip cells occupied by previous rows' `rowspan`).
    - If $c \ge \text{num\_cols}$: break (or handle row overflow defensively).
    - Determine effective $cs = \min(\text{cell.colspan}, \text{num\_cols} - c)$ and $rs = \min(\text{cell.rowspan}, \text{num\_rows} - r)$.
    - Place `LaidOutCell` at grid position $(r, c)$ with span $(rs, cs)$.
    - Mark all cells in the rectangular span as occupied:
      ```python
      for dr in range(rs):
          for dc in range(cs):
              grid[r + dr][c + dc] = laid_out_cell
      ```
    - Advance $c$ by $cs$.
- **Rationale**:
  - Standard algorithmic approach for HTML/CSS, DOCX, and PDF table layout.
  - Automatically handles any combination of `colspan`, `rowspan`, jagged rows, and sparse matrices.
- **Alternatives Considered**:
  - *Heuristic skip counter*: Rejected because multi-row spanning across non-adjacent columns (e.g. columns 0 and 2 both spanning while column 1 does not) quickly leads to fragile edge cases.

---

## 3. Table Layout Pipeline Unification (P1)

### 3.1 Problem Analysis
Currently, table layout is implemented twice:
- `TableLayoutEngine.layout_table()`: used for standalone measurement and border stroke generation.
- `DocumentLayoutEngine.render()`: implements its own inline formatting, wrapping, row height accumulation, page break splitting, and cell placement.
This violates the Single Responsibility Principle and Constitution Principle IV (Loose Coupling & High Cohesion), creating dual-maintenance overhead.

### 3.2 Architectural Decision
- **Decision**: Centralize all table geometry in `TableLayoutEngine`:
  1. `TableLayoutEngine.layout_table(table, x0, y0, cell_measurer=None) -> TableLayoutData`:
     - Computes column widths (`compute_column_widths`).
     - Builds occupancy grid and places cells at resolved $(x, y, \text{width}, \text{height})$.
     - Wraps text or invokes `cell_measurer` to format rich inlines (text + math).
     - Calculates precise row heights based on cell content.
  2. For document pagination in `DocumentLayoutEngine`:
     - Slices rows that fit on the current page (`slice_table_for_page`).
     - Generates border strokes via `TableLayoutEngine.generate_border_strokes(slice_data, table.border_style)`.
     - Emits rendered strokes for text and math directly from the sliced `LaidOutCell` objects.
- **Rationale**:
  - Single source of truth.
  - Fixes in `TableLayoutEngine` immediately benefit both unit tests and actual document rendering.

---

## 4. Stroke Bank Handwriting Verification for TextNode (P1)

### 4.1 Problem Analysis
Prior tests in `tests/test_math_layout.py` only asserted:
```python
assert layout_item.size.width > 0
assert layout_item.size.height > 0
```
This is a weak assertion; an engine returning blank bounding boxes would pass.

### 4.2 Architectural Decision
- **Decision**: Add assertions verifying:
  ```python
  assert len(layout_item.glyphs) > 0
  total_strokes = sum(len(g.strokes) for g in layout_item.glyphs)
  assert total_strokes > 0
  ```
  Test key representative expressions:
  - Simple variable and constant: $x^2 + 1$
  - Square root: $\sqrt{x}$, $\sqrt{x^2 + 1}$
  - Fraction: $\frac{x + 1}{2}$
  - Subscript/superscript: $x_i^2$
- **Rationale**: Ensures handwriting synthesis truly traverses from Math AST $\to$ TextNode $\to$ StrokeBankWriter $\to$ PositionedGlyph vector strokes.

---

## 5. Headless GUI Import Guard Hardening (CI Resilience)

### 5.1 Problem Analysis
In `tests/test_gui_document.py`, line 4 imported:
```python
from tkinter import filedialog, messagebox
```
before calling `conftest.is_tk_usable()`. In headless or non-Tk Python installations, pytest fails during module collection with `ModuleNotFoundError: No module named 'tkinter'`.

### 5.2 Architectural Decision
- **Decision**: Move Tkinter imports behind `if not conftest.is_tk_usable(): pytest.skip(...)`, matching `tests/test_gui.py`.
- **Rationale**: Guarantees 0 collection crashes across all environments.

---

## 6. End-to-End Sample Document Generation & XOPP Verification (P2)

### 6.1 Test Documents
Prepare/validate three fixture files:
1. `tests/fixtures/sample.txt`: Plain text with Vietnamese diacritics, numbered items, and preserved empty lines.
2. `tests/fixtures/sample.md`: Markdown with headers, bold/italic, lists, table with alignment, and inline/block LaTeX math.
3. `tests/fixtures/sample.docx`: Word document with formatted paragraphs, styled tables with merged cells (`colspan` & `rowspan`), and OMML math equations.

### 6.2 Verification Metric
- Verify `.xopp` archive generation (`gzip` XML).
- Confirm zero crashes, valid XML structure, non-overlapping table coordinates, and clean math stroke outputs.
