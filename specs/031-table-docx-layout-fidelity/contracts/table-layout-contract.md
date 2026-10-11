# Contract: Enhanced Table Layout Engine & Pagination Slicing

**Feature Branch**: `031-table-docx-layout-fidelity`
**Date**: 2026-10-11
**Spec**: [spec.md](../spec.md)

## 1. Purpose

This contract specifies enhancements to `TableLayoutEngine`, `TableLayoutData`, and `DocumentLayoutEngine` for safe multi-page table pagination across merged row closures, accurate vertical line metrics for math formulas, long token wrapping, and high-performance border stroke generation.

---

## 2. API Signatures & Data Contracts

### 2.1 `LineVerticalMetrics` & Formatter Output

```python
@dataclass
class LineVerticalMetrics:
    ascent: float    # Max height above baseline (max(0, -y_min))
    descent: float   # Max depth below baseline (max(0, y_max))
    width: float     # Total width of line elements
    height: float    # Effective line height: max(default_h, ascent + descent + line_spacing)

# Formatted line representation returned by cell_inlines_formatter:
# tuple[list[tuple[float, list[Stroke], float]], LineVerticalMetrics]
```

When rendering in `engine.py`:
- Baseline $Y$ position is computed as: $\text{cell\_cur\_y} + \text{line\_metrics.ascent}$.
- Next line starts at: $\text{cell\_cur\_y} += \text{line\_metrics.height}$.
- Clearance requirement: For all rendered strokes $(x_i, y_i)$,
  $\text{cell.x} + \text{padding} \le x_i \le \text{cell.x} + \text{cell.width} - \text{padding}$, and
  $\text{cell.y} + \text{padding} \le y_i \le \text{cell.y} + \text{cell.height} - \text{padding}$.

### 2.2 Transitive Row Group Closure in `TableLayoutData.slice_page`

```python
def slice_page(
    self,
    start_row_idx: int,
    max_height: float,
    new_y: float,
) -> tuple[TableLayoutData, int]:
    """
    Slices a continuous group of rows for a single page.
    
    Guarantees:
    1. Transitive Closure: If rows r_a and r_b are transitively connected by any sequence
       of multi-row merged cells, they belong to the same MergedRowGroup [group_start, group_end].
    2. Page Break Boundary: A page break NEVER splits rows within [group_start, group_end]
       when curr_h > 0.
    3. Strict Forward Progression: When curr_h == 0 at the top of a fresh page, the entire
       atomic group [group_start, group_end] is taken into the slice even if its height exceeds
       max_height. This ensures next_row = group_end + 1 > start_row_idx, guaranteeing forward
       progress, zero cell amputation, and zero risk of infinite pagination loops.
    """
```

### 2.3 Optimized Border Stroke Generation

```python
def generate_border_strokes(
    self,
    data: TableLayoutData,
    style: TableBorder = TableBorder.ALL,
    jitter: float = 0.0,
    seed: int | None = None,
) -> list[PositionedStroke]:
    """
    Generates border vector strokes using an O(R * C) precomputed occupancy/merge mask.
    Execution time for a 100x20 table must not exceed 50ms.
    """
```

### 2.4 Token Wrapping in `wrap_cell_text`

```python
def wrap_cell_text(
    self,
    text: str,
    max_w: float,
) -> list[str]:
    """
    Wraps text to fit within max_w.
    If a continuous word exceeds max_w, the word is broken at character boundaries
    so that no line exceeds max_w.
    """
```

---

## 3. Behavioral Invariants

1. **Formula Clearance**:
   Every math stroke bounding box within a cell is guaranteed to lie within the interior rectangle bounded by `cell.x + padding`, `cell.x + cell.width - padding`, `cell.y + padding`, and `cell.y + cell.height - padding`.
2. **Atomic Row Grouping**:
   If Cell 1 spans rows 1–2 in Col 0, and Cell 2 spans rows 2–3 in Col 1, the row group interval is $[1, 3]$. No page break may occur between row 1 and 2, or between row 2 and 3.
3. **Closed Border Perimeters**:
   Every page slice produced by `slice_page()` receives complete outer borders for `OUTER` and `ALL` styles without missing or open top/bottom frame lines.
