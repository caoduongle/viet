# Quickstart Validation Guide: Table Layout Robustness & DOCX Hardening

**Feature Branch**: `032-table-layout-docx-hardening` | **Date**: 2026-10-11
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This runnable guide verifies the 5 primary objectives of this feature end-to-end.

---

## 1. Prerequisites

Activate environment and confirm dependencies:
```bash
py -3.12 -m pip install -r requirements-dev.txt
npm install
```

---

## 2. Validation Scenarios

### Scenario 1: Table Pagination Boundary & Merged Group Clamping
Validate that oversized merged row groups and tall single rows never push stroke points beyond the printable page boundary (`y <= page_height - margin_bottom`).

```bash
# Run targeted pagination test with geometric stroke boundary validation
py -3.12 -m pytest tests/test_table_pagination_closure.py -v
```
**Expected Outcome**: All slices make strictly monotonic forward progress, and 100% of generated strokes satisfy $y \le \text{page\_height} - 60.0$.

---

### Scenario 2: Math Formula Metrics Scaling in Table Cells
Validate that formula ascent and descent scale with the effective scale factor ($S \times \text{scale\_mult}$) and that tall formulas (fractions, square roots, integrals) do not collide with cell horizontal borders across scales ($0.5, 1.0, 1.5$, and `--auto-xh`).

```bash
# Run rich table inline formula test with bounding box assertions
py -3.12 -m pytest tests/test_table_rich_inlines.py -v
```
**Expected Outcome**: Measured row height expands proportionally to $S \times \text{formula\_height}$, and zero formula strokes intersect top/bottom borders.

---

### Scenario 3: Long Unbroken Token Character Wrapping in Live Rendering Pipeline
Validate that URLs and technical strings exceeding column width wrap across character boundaries in the actual document rendering pipeline, with all strokes staying inside column width.

```bash
# Run cell token wrapping integration test
py -3.12 -m pytest tests/test_table_wrapping_pipeline.py -v
```
**Expected Outcome**: Long tokens wrap into multiple lines within the cell; maximum stroke $x \le \text{cell\_x} + \text{col\_w}$.

---

### Scenario 4: DOCX Table Occupancy Grid & Nested Block Order
Validate that DOCX tables with merged cells calculate logical column count correctly, and that nested tables within cells retain true document sequence.

```bash
# Run DOCX table and nested block ordering tests
py -3.12 -m pytest tests/test_docx_table_occupancy.py tests/test_docx_nested_table_order.py -v
```
**Expected Outcome**: Generated Markdown table has correct column count; nested tables appear strictly between preceding and following paragraphs.

---

### Scenario 5: Web Modal Headerless Table Insertion & E2E Tests
Validate that unchecking "Has header row" inserts a headerless Markdown table, and run Playwright E2E tests.

```bash
# Run web client unit and E2E tests
npm run test:unit
npx playwright test tests/e2e/docx-import.spec.ts tests/e2e/write.spec.ts
```
**Expected Outcome**: Table insertion produces headerless table representation; Playwright tests pass cleanly.

---

### Scenario 6: Full Test Suite & Architectural Integrity Gate
```bash
# Run architecture verification
py -3.12 -m pytest tests/test_architecture.py -v

# Run golden master invariant
py -3.12 -m pytest tests/test_golden_master_real_path.py -v

# Run complete pytest suite
py -3.12 -m pytest -q --timeout=60
```
**Expected Outcome**: Zero architecture violations, Golden Master hash bit-exact match, and 1,230+ tests passing.
