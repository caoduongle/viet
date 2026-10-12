# Tasks: Table Pagination, Line Spacing Anti-Collision, Math Accents, and Geometry Hardening

**Feature**: `034-table-pagination-and-wrapping-hardening`  
**Input**: Design documents from `specs/034-table-pagination-and-wrapping-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)  
**Status**: Ready for Implementation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify repository baseline and create initial test scaffolds.

- [x] T001 Inspect and verify test baseline on branch `034-table-pagination-and-wrapping-hardening` across `tests/test_architecture.py` and `tests/test_golden_master_real_path.py`
- [x] T002 [P] Create test scaffold for line spacing policy in `tests/test_line_spacing_policy.py`
- [x] T003 [P] Create test scaffold for math accent placement in `tests/test_math_accent_placement.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure functions that MUST be completed before User Story implementation.

**⚠️ CRITICAL**: All user stories depend on these foundational modules.

- [x] T004 Implement `resolve_effective_line_height` helper and `LineHeightPolicy` logic in `chuviettay/layout/engine.py` per `CTR-034-LINE-HEIGHT-POLICY`
- [x] T005 [P] Implement `_partition_long_token_linear` pure measurement helper with $O(N)$ prefix accumulators and `min_chars=1` guard in `chuviettay/layout/engine.py`
- [x] T006 [P] Implement `reindex_rows()` in `chuviettay/layout/table_layout.py` updating `cell.row` and `rowspan` across dynamic slice insertions per `CTR-034-TABLE-CONTINUATION-AND-PAGINATION`

**Checkpoint**: Foundational helpers ready — User Story implementation can proceed in parallel.

---

## Phase 3: User Story 1 - Lossless Bottom-Margin Overflow Protection & Remainder Rollover (Priority: P1) 🎯 MVP

**Goal**: Ensure zero lines are dropped when table cells reach the page bottom margin by implementing active continuation remainder rollover.

**Independent Test**: Render a table cell with 40 numbered lines near the bottom margin. Assert that 100% of numbered lines are rendered across the page sequence with zero dropped or duplicate lines.

### Tests for User Story 1
- [x] T007 [P] [US1] Write test verifying 100% of cell lines are preserved without being dropped when hitting `max_page_y` in `tests/test_table_pagination_closure.py`

### Implementation for User Story 1
- [x] T008 [US1] Update `partition_cell_lines_by_height()` in `chuviettay/layout/table_layout.py` to account for descent, padding, and jitter tolerance in slice heights
- [x] T009 [US1] Replace silent `break` at `line_bottom_y > max_page_y` in `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py` with `ContinuationRemainder` rollover to continuation row on next page
- [x] T010 [US1] Add downscaling and structured warning fallback for indivisible oversized math/atomic blocks exceeding total page height in `chuviettay/layout/engine.py`

**Checkpoint**: User Story 1 functional and verifiable independently.

---

## Phase 4: User Story 2 - Anti-Collision Line Spacing & Table Row Height Floor (Priority: P1)

**Goal**: Guarantee that configuring custom small line spacing (e.g. `1.0pt`) enforces a physical anti-collision floor so text lines never collide and table borders never intersect numbers.

**Independent Test**: Set `line=1.0pt` and render multi-line paragraphs and tables. Assert that paragraph line baselines are separated by at least `safe_line_floor`, table row heights are $\ge \text{safe\_line\_floor} + 2 \times \text{cell\_padding}$, and zero horizontal borders intersect text bounding boxes.

### Tests for User Story 2
- [x] T011 [P] [US2] Write unit and integration tests in `tests/test_line_spacing_policy.py` verifying no text overlap and no border intersection when `opts.line = 1.0pt` and `0.1pt`

### Implementation for User Story 2
- [x] T012 [US2] Integrate `resolve_effective_line_height` into `DocumentLayoutEngine.__init__` and `render()` in `chuviettay/layout/engine.py` enforcing `safe_line_floor`
- [x] T013 [US2] Enforce `safe_line_floor + 2 * cell_padding` row height floor in `TableLayoutEngine` and `layout_table()` in `chuviettay/layout/table_layout.py`
- [x] T014 [US2] Update cell baseline calculation `baseline_y` in `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py` to prevent glyphs from crossing upper/lower cell boundaries

**Checkpoint**: User Stories 1 and 2 functional and verifiable independently.

---

## Phase 5: User Story 3 - Natural Math Accent Positioning & Compact Ascent Metrics (Priority: P2)

**Goal**: Anchor mathematical accents ($\bar{x}, \hat{x}, \tilde{x}, \vec{x}$) tightly and naturally above base glyph tops without floating high in the air or inflating line ascent metrics.

**Independent Test**: Render accented expressions ($\bar{x}, \hat{x}, \bar{y}, \vec{x}$). Verify that optical gap $y_{\text{accent}} - y_{\text{base\_top}}$ is between $0.05 \times xh$ and $0.20 \times xh$, and that line `extra_top` does not expand excessively.

### Tests for User Story 3
- [x] T015 [P] [US3] Write tests in `tests/test_math_accent_placement.py` verifying gap $0.05 \times xh \le d_{\text{gap}} \le 0.20 \times xh$ for $\bar{x}, \hat{x}, \tilde{x}, \vec{x}$

### Implementation for User Story 3
- [x] T016 [US3] Update `_m_Accent` in `chuviettay/layout/math_layout.py` with tight optical gaps ($0.06 - 0.10 \times xh$) and proportional polyline heights per `CTR-034-MATH-ACCENT-PLACEMENT`
- [x] T017 [US3] Adjust polyline offsets in `accent_polylines()` in `chuviettay/layout/vector_glyphs.py` to anchor overbars and hats tightly above base glyphs
- [x] T018 [US3] Bound `ascent` metric of lowercase accented symbols in `chuviettay/layout/math_layout.py` to avoid inflating `extra_top` in `engine.py`

**Checkpoint**: User Stories 1, 2, and 3 functional and verifiable independently.

---

## Phase 6: User Story 4 - Row Index & Rowspan Synchronization for Dynamic Continuation Rows (Priority: P2)

**Goal**: Maintain exact row indices and multi-row spans (`rowspan`) when rows are dynamically split across page boundaries, preventing broken table borders and grid lookup errors.

**Independent Test**: Render a table spanning 3+ pages combining tall splitting rows and overlapping `rowspan=3` cells. Assert zero index errors and verify that borders match cell boundaries and never cross merged cells.

### Tests for User Story 4
- [x] T019 [P] [US4] Write test in `tests/test_table_pagination_closure.py` combining tall rows (splitting over 3+ pages) and intersecting `rowspan > 1` cells, asserting border alignment and zero index crashes

### Implementation for User Story 4
- [x] T020 [US4] Update dynamic row splitting in `TableLayoutData.slice_page()` in `chuviettay/layout/table_layout.py` to call `reindex_rows()` and adjust active `rowspan` ranges across insertion points
- [x] T021 [US4] Map `cell.row` in `sliced_cells` to local slice row indices $r_{\text{offset}}$ in `TableLayoutData.slice_page()` in `chuviettay/layout/table_layout.py` so `BorderLookupGrid` masks merged areas accurately

**Checkpoint**: User Stories 1 through 4 functional and verifiable independently.

---

## Phase 7: User Story 5 - Single-Pass Zero-Mutation Token Splitting with O(N) Prefix Measurement (Priority: P2)

**Goal**: Split long unbroken tokens in $O(N)$ linear time without repeatedly synthesizing candidate strokes or polluting `Writer` state.

**Independent Test**: Wrap a 500-character URL. Assert linear execution time ($< 5\text{ms}$) and verify `writer.assembled` and `writer.counts` are unchanged during candidate width measurement.

### Tests for User Story 5
- [x] T022 [P] [US5] Write test in `tests/test_table_wrapping_pipeline.py` asserting linear execution time and asserting `writer.assembled` and `writer.counts` remain unmodified during width measurement

### Implementation for User Story 5
- [x] T023 [US5] Replace quadratic loop in `_layout_inlines()` in `chuviettay/layout/engine.py` with `_partition_long_token_linear` calling pure measurement
- [x] T024 [US5] Ensure stroke synthesis `self.wr.token()` is called strictly ONCE per finalized token chunk in `chuviettay/layout/engine.py`

**Checkpoint**: User Stories 1 through 5 functional and verifiable independently.

---

## Phase 8: User Story 6 - High-Fidelity Retention of Intentional Empty Lines in Cells (Priority: P2)

**Goal**: Preserve intentional blank lines and empty paragraphs in table cells with proper vertical height.

**Independent Test**: Render a table cell with "Line 1\n\nLine 3". Verify that the cell height reflects 3 logical lines and that the middle line contributes vertical line height without phantom strokes.

### Tests for User Story 6
- [x] T025 [P] [US6] Write test in `tests/test_table_rich_inlines.py` verifying that cells with `\n\n` intentional blank lines retain empty lines with proper vertical line heights

### Implementation for User Story 6
- [x] T026 [US6] Update `cell_inlines_formatter()` and `flush_cur_line()` in `chuviettay/layout/engine.py` to preserve empty line entries and assign `LineVerticalMetrics(height=self.line_h)`

**Checkpoint**: User Stories 1 through 6 functional and verifiable independently.

---

## Phase 9: User Story 7 - Stroke Geometry Boundary Containment & Invariant Verification (Priority: P3)

**Goal**: Guarantee that 100% of generated stroke points stay within cell column boundaries and printable page margins, backed by exact-count line assertions.

**Independent Test**: Render multi-page tables with jitter enabled and disabled. Execute geometric containment assertions and exact-count assertions ($N_{\text{rendered}} == N_{\text{expected}}$).

### Tests for User Story 7
- [x] T027 [P] [US7] Update `tests/test_table_pagination_closure.py` to enforce exact-count assertions ($res.n\_lines == expected$) with distinct line identifiers across 35 and 75 lines
- [x] T028 [P] [US7] Implement post-transformation stroke point bounding box check across cell columns and page margins in `tests/test_table_rich_inlines.py` and `tests/test_table_wrapping_pipeline.py`

**Checkpoint**: All 7 User Stories fully implemented and testable.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, architectural compliance, and regression safety.

- [x] T029 [P] Run architecture check `pytest tests/test_architecture.py` to ensure zero MVC violations
- [x] T030 [P] Run Golden Master regression `pytest tests/test_golden_master_real_path.py` to guarantee bit-exact invariant preservation
- [x] T031 Execute full automated test suite `pytest -q` and quickstart scenarios in `specs/034-table-pagination-and-wrapping-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS all User Stories**.
- **User Stories (Phase 3 to 9)**:
  - Phase 3 (US1) and Phase 4 (US2) can run in parallel once Phase 2 is complete.
  - Phase 5 (US3), Phase 6 (US4), Phase 7 (US5), Phase 8 (US6), Phase 9 (US7) can proceed independently.
- **Polish (Phase 10)**: Depends on all User Story phases being complete.

### Parallel Opportunities
- All tasks marked `[P]` (T002, T003, T005, T006, T007, T011, T015, T019, T022, T025, T027, T028, T029, T030) can be executed concurrently without file conflicts.
- Contract/scaffold tests can run in parallel prior to implementation.

---

## Parallel Example: User Story 1 & User Story 2

```bash
# Launch tests for US1 and US2 in parallel:
Task T007: "tests/test_table_pagination_closure.py"
Task T011: "tests/test_line_spacing_policy.py"

# Implement US2 line height policy alongside US1 remainder rollover:
Task T012: "chuviettay/layout/engine.py" (resolve_effective_line_height)
Task T008: "chuviettay/layout/table_layout.py" (partition_cell_lines_by_height)
```

---

## Implementation Strategy

### MVP First (Phases 1, 2, and 3 - User Story 1)
1. Complete Phase 1 (Baseline checks)
2. Complete Phase 2 (Foundational helpers)
3. Complete Phase 3 (US1 - Lossless bottom margin remainder rollover)
4. **VALIDATE MVP**: Verify no text is dropped at page breaks.

### Incremental Delivery
1. Add US2: Anti-collision line spacing (`1.0pt` safe floor)
2. Add US3: Natural math accent anchoring ($\bar{x}, \hat{x}$)
3. Add US4: Multi-page table row index and `rowspan` synchronization
4. Add US5: Single-pass zero-mutation linear token wrapping
5. Add US6: Empty lines retention in cells
6. Add US7: Invariant geometric bounding box verification
7. Execute Polish & Golden Master regression (100% green).
