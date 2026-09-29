# Contract: Table Layout Engine & Document Layout Integration

**Feature Branch**: `009-table-and-math-layout-fixes`
**Date**: 2026-09-30
**Spec**: [spec.md](../spec.md)

## 1. Purpose

This contract establishes the unified interface between `TableLayoutEngine` and `DocumentLayoutEngine`. `TableLayoutEngine` serves as the sole authority for cell measurement, occupancy grid resolution, multi-page table slicing, and border stroke generation.

---

## 2. API Signatures

### 2.1 `TableLayoutEngine.layout_table`

```python
def layout_table(
    self,
    table: Table,
    x0: float,
    y0: float,
    cell_inlines_formatter: Callable[[TableCell, float], list[list[tuple[float, list[Stroke], float]]]] | None = None,
) -> TableLayoutData:
    """
    Computes table geometry with a 2D occupancy grid respecting colspan and rowspan.
    
    Parameters:
    - table: Document IR Table block.
    - x0: Left horizontal coordinate origin.
    - y0: Top vertical coordinate origin.
    - cell_inlines_formatter: Optional callback formatting cell blocks (paragraphs, math)
      into wrapped line items: (start_x_rel, strokes, width). If None, uses fallback wrap_cell_text.
      
    Returns:
    - TableLayoutData containing resolved column widths, row heights, and placed LaidOutCells.
    """
```

### 2.2 `TableLayoutEngine.generate_border_strokes`

```python
def generate_border_strokes(
    self,
    data: TableLayoutData,
    style: TableBorder,
) -> list[PositionedStroke]:
    """
    Generates border vector strokes for the table (or page slice).
    
    Invariants:
    - Suppresses internal grid lines inside any merged cell (colspan > 1 or rowspan > 1).
    - Preserves outer perimeter borders for OUTER, ALL, and HORIZONTAL styles.
    """
```

### 2.3 `TableLayoutData.slice_page`

```python
def slice_page(
    self,
    start_row_idx: int,
    max_height: float,
    new_y: float,
) -> tuple[TableLayoutData, int]:
    """
    Extracts a vertical slice of the table that fits within max_height for multi-page streaming.
    
    Returns:
    - (slice_data, next_row_idx): TableLayoutData representing the page slice,
      and index of the first row for the subsequent page.
    """
```

---

## 3. Behavioral Guarantees

1. **Deterministic Cell Placement**:
   - For any cell $k$ on row $r$, its column index $c$ is the smallest non-negative integer $\ge c_{\text{prev}} + \text{colspan}_{\text{prev}}$ such that $\text{grid}[r][c]$ is unoccupied.
2. **Non-Overlapping Bounds**:
   - For all cells $A \ne B$ in `data.cells`, their bounding rectangles $[A.x, A.x + A.width) \times [A.y, A.y + A.height)$ do not overlap.
3. **Exact Bounding Dimensions**:
   - Total table width equals $\sum \text{col\_widths}$.
   - Total table height equals $\sum \text{row\_heights}$.
4. **Border Suppression Integrity**:
   - If a cell spans columns $c_1 \dots c_2$ and rows $r_1 \dots r_2$, no horizontal border strokes are generated at row boundaries $r \in (r_1, r_2)$ within $[x_{c_1}, x_{c_2+1}]$, and no vertical border strokes are generated at column boundaries $c \in (c_1, c_2)$ within $[y_{r_1}, y_{r_2+1}]$.
