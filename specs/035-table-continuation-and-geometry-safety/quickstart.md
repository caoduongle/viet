# Quickstart Validation Guide: Table Continuation, Rowspan Stability, and Geometry Safety

**Feature**: [035-table-continuation-and-geometry-safety](spec.md)  
**Date**: 2026-10-13  
**Status**: Draft  

---

## Prerequisites

- Python 3.10+ virtual environment activated.
- Dependencies installed (`pytest`, `numpy`, `pillow`, etc.).

---

## 1. Quick Validation Commands

Run the test suite to verify all core features:

```powershell
# 1. Architecture compliance (MVC pattern & clean imports)
pytest tests/test_architecture.py

# 2. Table pagination, rowspan, and labeled line continuation
pytest tests/test_table_pagination_closure.py

# 3. Whole-word token wrapping and deterministic complexity
pytest tests/test_table_wrapping_pipeline.py

# 4. Anti-collision line spacing and auto_xh scaling
pytest tests/test_line_spacing_policy.py
```

---

## 2. End-to-End Scenarios

### Scenario 1: Multi-Page Continuation with Labeled Lines (`LINE_0001` .. `LINE_0060`)
- **Action**: Render a table spanning 3+ pages where Column 0 contains 60 labeled lines (`LINE_0001` to `LINE_0060`) and Column 1 has merged rows (`rowspan=3`).
- **Validation**:
  - Parse output `.xopp` XML or collect rendered line tokens.
  - Assert that all 60 identifiers appear in strict sequential order with zero dropped or duplicate lines.
  - Assert that zero stroke points exceed printable page bottom ($y \le \text{max\_page\_y}$).

### Scenario 2: Indivisible Tall Block Clamping & Truthful Warnings
- **Action**: Render a table cell containing a formula or tall block exceeding the full printable page height.
- **Validation**:
  - Assert the element is scaled down and physically clamped: $y_{\text{stroke}} \le \text{max\_page\_y}$.
  - Assert the warning explicitly reports downscaling factor and clamping.

### Scenario 3: Non-Overlapping Rowspan & Border Alignment
- **Action**: Render a multi-page table with tall cells adjacent to `rowspan > 1` cells.
- **Validation**:
  - Assert that `BorderLookupGrid` produces zero spurious interior divider lines inside merged cells on all pages.

### Scenario 4: Whole-Word Pre-composed Wrapping & Deterministic Complexity
- **Action**: Wrap words present in `bank.words` into table columns.
- **Validation**:
  - Assert words fitting column width are preserved as single units.
  - Assert `_partition_long_token_linear` runs in $O(N)$ with invocation counts $\le N$.

### Scenario 5: Synchronized `auto_xh` and Anti-Collision Line Spacing
- **Action**: Render document with `auto_xh=True` and `line=1.0pt`.
- **Validation**:
  - Assert that `engine.line_h >= safe_line_floor + 1.0pt`.
  - Assert zero physical overlap between consecutive lines.
