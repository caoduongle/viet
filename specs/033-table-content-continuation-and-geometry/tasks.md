# Tasks: Table Content Continuation Across Pages, True Geometry Clamping & Layout Hardening

**Feature**: `specs/033-table-content-continuation-and-geometry`
**Date**: 2026-10-12
**Status**: Ready for Implementation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification and test environment validation

- [X] T001 Baseline verification of full pytest suite and golden master invariants across the repository

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model and measurement primitives required across all user stories

**⚠️ CRITICAL**: Must be completed before user story implementation begins

- [X] T002 Add `warnings: list[str] = field(default_factory=list)` to `WriteResult` in `chuviettay/model/composer.py`
- [X] T003 Verify `WriteResult` re-export in `chuviettay/controller/results.py` and backwards compatibility with existing callers
- [X] T004 Implement non-mutating `Writer.measure_text_width()` with `_char_width_cache` in `chuviettay/model/writer.py`

**Checkpoint**: Foundation ready - data structures and non-mutating measurement available.

---

## Phase 3: User Story 1 - Multi-Page Table Text Content Continuation (Priority: P1) 🎯 MVP

**Goal**: Guarantee 100% text line preservation across page breaks when tables have tall rows or rowspan cells, with zero dropped lines and zero duplicate lines.

**Independent Test**: Render a table cell containing 30 lines across multiple pages; assert all 30 lines appear in sequential order across generated pages with closed continuation borders.

### Tests for User Story 1
- [X] T005 [P] [US1] Integration tests for multi-page table text content preservation and dynamic row splitting in `tests/test_table_pagination_closure.py`

### Implementation for User Story 1
- [X] T006 [US1] Implement line partitioning and continuation cell line transfer in `TableLayoutData.slice_page()` in `chuviettay/layout/table_layout.py`
- [X] T007 [US1] Implement dynamic row splitting for oversized single rows and asymmetric multi-column cells in `chuviettay/layout/table_layout.py`
- [X] T008 [US1] Update `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py` to support multi-page row continuation without dropping lines

**Checkpoint**: User Story 1 complete - tables paginate across multiple pages with 100% text preservation.

---

## Phase 4: User Story 2 - True Stroke Geometry Boundary Containment (Priority: P1)

**Goal**: Prevent letter descenders, tall formulas, and handwriting jitter from protruding past printable page margins ($y \le \text{page\_height} - 60.0$) or cell borders.

**Independent Test**: Render documents with heavy descenders ("quốc gia") and multi-level formulas near page bottom; assert 100% of stroke points $(x, y)$ satisfy $y \le \text{max\_page\_y}$ and stay within cell vertical limits.

### Tests for User Story 2
- [X] T009 [P] [US2] Boundary clamping tests for descenders, formulas, and jitter in `tests/test_table_rich_inlines.py`

### Implementation for User Story 2
- [X] T010 [US2] Implement `effective_descent` and `line_bottom_y` calculation accounting for descenders, math metrics, and jitter in `chuviettay/layout/engine.py`
- [X] T011 [US2] Enforce page bottom margin and cell vertical boundary clamping in `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py`

**Checkpoint**: User Story 2 complete - true stroke geometry clamping active, no bleeding across margins or cell borders.

---

## Phase 5: User Story 3 - Pure Geometric Width Measurement Without Writer Mutation (Priority: P2)

**Goal**: Measure candidate token widths during character-level wrapping in $O(L)$ time without modifying `Writer.counts`, `Writer.last`, or `Writer.assembled`.

**Independent Test**: Measure long token candidate substrings; assert `writer.counts`, `writer.last`, and `writer.assembled` are identical before and after candidate width measurements.

### Tests for User Story 3
- [X] T012 [P] [US3] Unit test for Writer state invariance during token candidate measurement in `tests/test_table_wrapping_pipeline.py`

### Implementation for User Story 3
- [X] T013 [US3] Refactor `cell_inlines_formatter` in `chuviettay/layout/engine.py` to use `wr.measure_text_width()` for candidate prefixes and call `wr.token()` only for final chunks

**Checkpoint**: User Story 3 complete - token wrapping executes cleanly without polluting Writer state or incurring $O(n^2)$ overhead.

---

## Phase 6: User Story 4 - Cell-Level Stroke Bounding Box Containment & Visual Border Integrity (Priority: P2)

**Goal**: Strengthen automated tests to assert stroke containment within each individual cell bounding box ($[x_{\min}, x_{\max}]$ and $[y_{\min}, y_{\max}]$) and prevent border collisions.

**Independent Test**: Extract strokes from uncompressed `.xopp` XML; assert all cell strokes satisfy $x \in [\text{cell.x}, \text{cell.x} + \text{cell.width}]$ and $y \in [\text{cell.y}, \text{cell.y} + \text{cell.height}]$.

### Implementation & Test Strengthening for User Story 4
- [X] T014 [P] [US4] Add cell-level bounding box assertions $[x_{\min}, x_{\max}]$ and $[y_{\min}, y_{\max}]$ in `tests/test_table_wrapping_pipeline.py`
- [X] T015 [P] [US4] Add per-cell bounding box and formula-border separation assertions in `tests/test_table_rich_inlines.py`

**Checkpoint**: User Story 4 complete - per-cell geometric assertions enforced in automated test suite.

---

## Phase 7: User Story 5 - Layout Diagnostic Warning Propagation to WriteResult, CLI, and Web UI (Priority: P2)

**Goal**: Collect table slicing and boundary clamping warnings in `WriteResult.warnings` and surface them in the Web UI `#editor-warnings` container and CLI reports.

**Independent Test**: Trigger a table row clamping warning; assert warning string appears in `WriteResult.warnings`, `BrowserBridge.write_text()` response payload, and formatting report.

### Tests for User Story 5
- [X] T016 [P] [US5] Test warning propagation from table slicing to WriteResult and browser bridge in `tests/test_table_pagination_closure.py`

### Implementation for User Story 5
- [X] T017 [US5] Aggregate `slice_data.warnings` into `WriteResult.warnings` in `chuviettay/layout/engine.py`
- [X] T018 [US5] Merge `result.warnings` into bridge response payload in `chuviettay/browser/bridge.py` and formatting report in `chuviettay/formatting.py`

**Checkpoint**: User Story 5 complete - end-to-end warning propagation active across engine, bridge, and UI.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Regressions, architecture validation, and quality verification

- [X] T019 [P] Run golden master regression test `tests/test_golden_master_real_path.py` (verify bit-exact SHA-256 for table and plain paper)
- [X] T020 [P] Run architecture compliance test `tests/test_architecture.py` (verify zero MVC violations and zero forbidden print calls)
- [X] T021 Run full test suite `pytest -q` and quickstart scenarios in `specs/033-table-content-continuation-and-geometry/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1). BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2). Can execute sequentially or in parallel with US1.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2).
- **User Story 4 (Phase 6)**: Depends on US1, US2, and US3.
- **User Story 5 (Phase 7)**: Depends on US1 and Foundational (Phase 2).
- **Polish (Phase 8)**: Depends on all user stories being complete.

### Parallel Opportunities
- Within Phase 2: T002, T003, T004 can be implemented and validated rapidly.
- Across stories: T005, T009, T012, T014, T015, T016 (test tasks) can run in parallel.
- Polish phase: T019 and T020 can run in parallel.

---

## Implementation Strategy

### MVP Scope (Phase 1 to Phase 3)
1. Complete Setup (T001) and Foundation (T002, T003, T004).
2. Complete User Story 1 (T005, T006, T007, T008).
3. Validate: Tables split across pages with zero dropped text. This is the core P1 defect fix.

### Incremental Delivery (Phase 4 to Phase 8)
4. Add User Story 2 (T009, T010, T011): True stroke bottom geometry clamping.
5. Add User Story 3 (T012, T013): Pure non-mutating token wrapping measurement.
6. Add User Story 4 (T014, T015): Per-cell bounding box test tightening.
7. Add User Story 5 (T016, T017, T018): End-to-end warning propagation.
8. Polish & Quality Gates (T019, T020, T021): Golden master invariant verification and full regression suite.
