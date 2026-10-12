# Quickstart: Validation & Verification Guide

**Feature**: `specs/033-table-content-continuation-and-geometry`
**Date**: 2026-10-12

---

## 1. Prerequisites & Environment

Ensure Python 3.10+ virtual environment is active and dependencies are installed:

```bash
# Verify Python version
python --version

# Run full test suite baseline check
pytest -q
```

---

## 2. Validation Scenarios

### Scenario 1: Multi-Page Table Text Continuation (Zero Text Loss)

Run the multi-page continuation integration test verifying that all lines of a tall cell are rendered across page breaks:

```bash
pytest tests/test_table_pagination_closure.py -k "test_multi_page_content_continuation" -v
```

**Expected Outcome**:
- Table slices across $\ge 2$ pages.
- 100% of lines from the input cell are present across pages in sequential order.
- Zero dropped lines, zero duplicate lines.

---

### Scenario 2: True Stroke Geometry Boundary Containment

Run stroke geometry verification to ensure letter descenders, formulas, and jitter never protrude beyond printable boundaries:

```bash
pytest tests/test_table_rich_inlines.py -k "test_table_descender_and_math_boundary" -v
```

**Expected Outcome**:
- All stroke points $(x, y)$ satisfy $y \le \text{page\_height} - 60.0$.
- Strokes inside cells satisfy $y \le \text{cell.y} + \text{cell.height}$.
- Zero collisions with table borders.

---

### Scenario 3: Pure Geometric Width Measurement Without Writer Mutation

Verify that token wrapping measures widths without mutating `Writer` counters or random state:

```bash
pytest tests/test_table_wrapping_pipeline.py -k "test_writer_state_invariance" -v
```

**Expected Outcome**:
- `writer.counts`, `writer.last`, and `writer.assembled` are identical before and after candidate width measurements.
- `writer.token()` is invoked only once per finalized chunk.

---

### Scenario 4: Per-Cell Stroke Bounding Box Containment

Verify that table cells with long wrapped tokens and formulas maintain strict per-cell bounding boxes:

```bash
pytest tests/test_table_wrapping_pipeline.py tests/test_table_rich_inlines.py -v
```

**Expected Outcome**:
- All $(x, y)$ coordinates for cell strokes remain strictly within individual cell bounds $[x_{\min}, x_{\max}]$ and $[y_{\min}, y_{\max}]$.

---

### Scenario 5: Layout Warning Propagation

Verify warning propagation to `WriteResult` and the browser bridge:

```bash
pytest tests/test_table_pagination_closure.py -k "test_table_slice_warning_propagation" -v
```

**Expected Outcome**:
- Clamping/deferral warnings are captured in `WriteResult.warnings`.
- `BrowserBridge.write_text()` returns `warnings` in its result dictionary.

---

### Scenario 6: Golden Master & Architecture Verification

Ensure zero regressions on continuous text and MVC compliance:

```bash
pytest tests/test_golden_master_real_path.py tests/test_architecture.py -v
```

**Expected Outcome**:
- 100% bit-exact SHA-256 match for Plain paper.
- Zero MVC architectural violations.
