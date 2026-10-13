# Implementation Tasks: Table Continuation, Rowspan Stability, and Geometry Safety Hardening

**Feature**: [035-table-continuation-and-geometry-safety](spec.md)  
**Date**: 2026-10-13  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify clean baseline, tooling, and test fixtures before code modifications.

- [X] T001 Review and align active feature branch `035-table-continuation-and-geometry-safety` and verify baseline test suite in `tests/test_architecture.py` and `tests/test_table_pagination_closure.py`
- [X] T002 [P] Configure helper utilities for XML inspection and sequential token extraction in `tests/conftest.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model properties that MUST be complete before user stories can begin.

**⚠️ CRITICAL**: Foundational tasks must complete before user story logic branches are altered.

- [X] T003 [P] Add `source_cell_id: int | None = None` attribute to `TableCell` in `chuviettay/document/ir.py`
- [X] T004 [P] Add `source_cell_id: int | None = None` attribute to `LaidOutCell` in `chuviettay/layout/table_layout.py`
- [X] T005 Assign deterministic sequential `source_cell_id` per table (`cell_seq = r * 1000 + c`) in `TableLayoutEngine.layout_table()` in `chuviettay/layout/table_layout.py`

**Checkpoint**: Foundation ready — `source_cell_id` is available on all table cell representations.

---

## Phase 3: User Story 1 - Physical Stroke Boundary Clamping & Guaranteed Page Containment (Priority: P1) 🎯 MVP

**Goal**: Guarantee 100% of rendered stroke coordinates satisfy $y \le y_{\text{max\_page\_y}}$, downscale oversized indivisible elements at the top of a page, and record truthful diagnostic warnings.

**Independent Test**: Render an oversized atomic formula/cell at the top of a fresh page. Verify that 100% of stroke points satisfy $y \le \text{max\_page\_y}$ and the system logs an accurate downscaling notice.

### Tests for User Story 1
- [X] T006 [P] [US1] Add test for atomic oversized formula downscaling and physical coordinate clamping in `tests/test_table_pagination_closure.py`

### Implementation for User Story 1
- [X] T007 [P] [US1] Add `max_y: float | None = None` parameter and hard $y$-coordinate bounding (`py = min(py, max_y)`) in `_render_text_line()` in `chuviettay/layout/engine.py`
- [X] T008 [US1] Implement proportional downscaling (`scale_mult`) and physical clamping for top-of-page oversized elements and emit truthful diagnostic warning in `chuviettay/layout/engine.py`

**Checkpoint**: User Story 1 complete — zero ink can bleed past `max_page_y` and all warnings accurately reflect physical clamping.

---

## Phase 4: User Story 2 - Stable Cell Identity Tracking for Multi-Page Rowspan Continuation (Priority: P1)

**Goal**: Track continuation cells across 3+ page slices back to their unique origin `source_cell_id`, preventing lost or corrupted lines when `rowspan > 1` cells overflow page boundaries.

**Independent Test**: Render a 4-page table where Column 0 has a cell with `rowspan=4` and 60 text lines. Verify 100% of lines are preserved across pages in exact sequence with zero corrupted adjacent cells.

### Tests for User Story 2
- [X] T009 [P] [US2] Add integration test for multi-page table continuation across 3+ pages with `rowspan > 1` in `tests/test_table_pagination_closure.py`

### Implementation for User Story 2
- [X] T010 [P] [US2] Preserve `source_cell_id` on all slice cells and continuation cells created in `TableLayoutData.slice_page()` in `chuviettay/layout/table_layout.py`
- [X] T011 [US2] Replace row-index reconstruction (`actual_r = curr_row_idx + laid_cell.row`) with persistent `source_cell_id` matching in `DocumentLayoutEngine` in `chuviettay/layout/engine.py`
- [X] T012 [US2] Update `next_row` progression logic for continuation cells to prevent repeating completed rows or skipping pending rows in `chuviettay/layout/engine.py`

**Checkpoint**: User Story 2 complete — multi-page tables with deep `rowspan` continuations preserve 100% of content.

---

## Phase 5: User Story 3 - Non-Overlapping Rowspan Partitioning & Border Alignment (Priority: P2)

**Goal**: Partition `rowspan` ranges explicitly between origin slice (`rowspan=1`) and continuation slice (`rowspan=max(1, cell.rowspan)`) during dynamic row splitting, ensuring disjoint grid occupancy and clean border lines.

**Independent Test**: Render a table with tall merged cells split across pages. Verify that cell occupancy grid is non-conflicting and `BorderLookupGrid` produces zero interior divider lines inside merged cells.

### Tests for User Story 3
- [X] T013 [P] [US3] Add test for border alignment and non-overlapping cell grid occupancy when dynamic row splitting occurs in `tests/test_table_pagination_closure.py`

### Implementation for User Story 3
- [X] T014 [US3] Partition `rowspan` explicitly (`c1.rowspan = 1`, `c2.rowspan = max(1, cell.rowspan)`) during dynamic row splitting in `TableLayoutData.slice_page()` in `chuviettay/layout/table_layout.py`
- [X] T015 [US3] Verify `BorderLookupGrid.from_cells()` accurately masks interior dividers using partitioned spans in `chuviettay/layout/table_layout.py`

**Checkpoint**: User Story 3 complete — dynamic row splitting creates strictly disjoint row spans with seamless borders.

---

## Phase 6: User Story 4 - Whole-Word Aware Hybrid Token Wrapping (Priority: P2)

**Goal**: Inspect whole-word models (`bank.words`) and `TOKRE` core matches in `Writer.measure_text_width()` before falling back to character advance splitting, and handle token wrapping in $O(N)$ linear time without mutating synthesizer state.

**Independent Test**: Wrap text containing words present in `bank.words` into table columns. Verify words fitting the column remain unbroken while oversized tokens wrap linearly without state leakage.

### Tests for User Story 4
- [X] T016 [P] [US4] Add test verifying pre-composed words from `bank.words` remain unbroken when fitting columns in `tests/test_table_wrapping_pipeline.py`

### Implementation for User Story 4
- [X] T017 [US4] Update `Writer.measure_text_width()` to inspect `self.b.words` and `TOKRE` core matches in `chuviettay/model/writer.py`
- [X] T018 [US4] Ensure `_layout_inlines()` in `chuviettay/layout/engine.py` accommodates minor optical width adjustments in a single pass without trial re-generation loops

**Checkpoint**: User Story 4 complete — whole-word models are preserved during wrapping without writer state corruption.

---

## Phase 7: User Story 5 - Synchronized Line Height and Character Sizing under Auto-Scale (Priority: P2)

**Goal**: Finalize effective scale `self.S` and `self.effective_wscale` before resolving line height `self.line_h`, ensuring safe anti-collision floors scale proportionally with character size under `auto_xh`.

**Independent Test**: Render documents with `auto_xh=True` and `line=1.0pt`. Verify adjacent lines and table borders maintain safe physical clearance proportional to target glyph height.

### Tests for User Story 5
- [X] T019 [P] [US5] Add test for `auto_xh` with small line spacing (`line=1.0pt`) asserting anti-collision clearance in `tests/test_line_spacing_policy.py`

### Implementation for User Story 5
- [X] T020 [US5] Reorder initialization in `DocumentLayoutEngine.__init__` in `chuviettay/layout/engine.py` to finalize `self.S` and `self.effective_wscale` prior to invoking `resolve_effective_line_height`

**Checkpoint**: User Story 5 complete — character scaling and vertical line clearance floors are harmoniously synchronized.

---

## Phase 8: User Story 6 - Labeled Content Verification & Deterministic CI Testing (Priority: P3)

**Goal**: Verify 100% content preservation using unique sequential line identifiers (`LINE_0001` .. `LINE_0060`) and replace environmental wall-clock thresholds with call-count invariants.

**Independent Test**: Run the test suite on any environment. Confirm that multi-page tests verify ordered sets of labeled line identifiers and wrapping benchmarks assert call-count invariants deterministically.

### Implementation & Tests for User Story 6
- [X] T021 [P] [US6] Add deterministic integration test verifying exact presence and monotonic sequence of `LINE_0001` .. `LINE_0060` across a 4-page table in `tests/test_table_pagination_closure.py`
- [X] T022 [P] [US6] Replace wall-clock threshold assertion (`assert t_elapsed < 0.010`) with `char_width_measurer` call-count invariant in `tests/test_table_wrapping_pipeline.py`

**Checkpoint**: User Story 6 complete — test assertions provide undeniable mathematical proof of content preservation and linear scaling.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, regression testing, and quality assurance.

- [X] T023 [P] Run full test suite including `tests/test_architecture.py` and `tests/test_golden_master_real_path.py` to verify zero regressions across the codebase
- [X] T024 [P] Execute all validation scenarios defined in `specs/035-table-continuation-and-geometry-safety/quickstart.md`
- [X] T025 Clean up temporary debug code, preserve docstrings, and synchronize feature documentation

---

## Dependencies & Execution Order

### Phase Dependencies

```
[Phase 1: Setup] ─────────────┐
                              ▼
                   [Phase 2: Foundational]
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   [Phase 3: US1]       [Phase 4: US2]       [Phase 5: US3]
   (Physical Clamping)  (Cell Identity)      (Rowspan Part.)
         │                    │                    │
         ├────────────────────┴────────────────────┤
         ▼                                         ▼
   [Phase 6: US4]                            [Phase 7: US5]
   (Whole-Word Wrapping)                     (auto_xh Sync)
         │                                         │
         └────────────────────┬────────────────────┘
                              ▼
                        [Phase 8: US6]
                   (Deterministic CI & Tests)
                              │
                              ▼
                        [Phase 9: Polish]
```

- **Phase 1 (Setup)**: No dependencies — executes immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories.
- **Phase 3 & 4 (P1 Stories)**: Depend on Phase 2 — deliver core MVP geometry safety and continuation tracking.
- **Phase 5, 6, 7 (P2 Stories)**: Depend on Phase 2 & foundational cell structures.
- **Phase 8 (P3 Story)**: Implements deterministic labeled tests validating all prior stories.
- **Phase 9 (Polish)**: Runs end-to-end regression validation.

---

## Parallel Opportunities

- **Foundational**: T003 (`ir.py`) and T004 (`table_layout.py`) can be implemented in parallel.
- **User Story 1**: T006 (Test) and T007 (`_render_text_line`) can proceed in parallel.
- **User Story 2**: T009 (Test) and T010 (`slice_page`) can proceed in parallel.
- **User Story 3**: T013 (Test) and T014 (`slice_page` partitioning) can proceed in parallel.
- **User Story 4**: T016 (Test) and T017 (`writer.py` measure) can proceed in parallel.
- **User Story 5**: T019 (Test) and T020 (`engine.py` `__init__`) can proceed in parallel.
- **User Story 6**: T021 (`test_table_pagination_closure.py`) and T022 (`test_table_wrapping_pipeline.py`) can proceed in parallel.

---

## Implementation Strategy

### MVP First (Phases 1, 2, and 3)
1. Complete Setup and Foundational properties (`source_cell_id`).
2. Implement User Story 1 (Physical Stroke Boundary Clamping).
3. Validate: Zero stroke coordinates exceed $y_{\text{max\_page\_y}}$ and warnings are truthful.

### Incremental Delivery
1. Add User Story 2: Stable cell identity tracking across multi-page continuations.
2. Add User Story 3: Non-overlapping `rowspan` partitioning and border alignment.
3. Add User Story 4: Whole-word aware token wrapping.
4. Add User Story 5: `auto_xh` and anti-collision floor synchronization.
5. Add User Story 6: Labeled identifier verification (`LINE_0001` .. `LINE_0060`) and deterministic CI complexity assertions.
6. Complete Phase 9: Golden master and architecture validation.
