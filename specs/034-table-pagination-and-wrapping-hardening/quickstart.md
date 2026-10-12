# Quickstart & Verification Guide: Table Pagination, Line Spacing, and Accent Hardening

**Feature**: `034-table-pagination-and-wrapping-hardening`  
**Date**: 2026-10-12

---

## 1. Overview

This guide provides runnable test commands and validation procedures to verify all 7 User Stories in Feature 034:
- Zero content dropped at bottom margins
- Anti-collision line spacing floor (`line=1.0pt`) in text and tables
- Natural math accent placement ($\bar{x}, \hat{x}$)
- Synchronized row indices and spans for continuation slices
- Linear $O(N)$ zero-mutation token wrapping
- Retention of blank lines in cells
- Strict geometric containment and exact line count verification

---

## 2. Test Execution Commands

### 2.1 Run Regression Baseline
Ensure that existing tests continue to pass cleanly without architectural or golden master regressions:
```powershell
pytest tests/test_architecture.py tests/test_golden_master_real_path.py -v
```

### 2.2 Verify Line Spacing Anti-Collision Floor (Scenario 1)
Verify that setting `line=1.0` in both paragraph text and table cells enforces the safe physical floor:
```powershell
pytest tests/test_line_spacing_policy.py -v
```
**Expected Outcome**:
- Paragraph line baselines are separated by at least `safe_line_floor`.
- Zero glyph collisions between consecutive lines.
- In tables, row heights are $\ge \text{safe\_line\_floor} + 2 \times \text{cell\_padding}$.
- Zero horizontal border strokes intersect cell text bounding boxes.

### 2.3 Verify Natural Math Accent Positioning (Scenario 2)
Verify that mathematical accents ($\bar{x}, \hat{x}, \tilde{x}, \vec{x}$) sit directly above base symbols:
```powershell
pytest tests/test_math_accent_placement.py -v
```
**Expected Outcome**:
- Gap between glyph top and overbar is between $0.05 \times xh$ and $0.20 \times xh$.
- Accented variables do not cause artificial baseline jumps in normal paragraphs or tables.

### 2.4 Verify Lossless Bottom-Margin Overflow & Slicing (Scenario 3 & 4)
Verify that dense multi-page tables (40+ and 80+ lines) retain 100% of lines across page transitions:
```powershell
pytest tests/test_table_pagination_closure.py -v
```
**Expected Outcome**:
- 100% of lines are rendered across pages with exact-count assertions ($N_{\text{rendered}} == N_{\text{expected}}$).
- Zero lines are dropped when hitting `max_page_y`.
- Continuation rows maintain synchronized row indices and span alignment.

### 2.5 Verify Single-Pass Zero-Mutation Token Wrapping (Scenario 5)
Verify that long URLs and technical tokens wrap in linear time without mutating synthesizer state:
```powershell
pytest tests/test_table_wrapping_pipeline.py -v
```
**Expected Outcome**:
- Wraps long tokens in $O(N)$ linear time.
- `writer.assembled` and `writer.counts` are unchanged during candidate width measurement.

### 2.6 Full Suite Verification
Run the entire automated test suite to ensure comprehensive green status:
```powershell
pytest -q
```
