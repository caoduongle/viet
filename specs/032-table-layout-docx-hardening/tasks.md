# Tasks: Table Layout Robustness, Geometry Scaling & DOCX Import Hardening

**Input**: Design documents from `specs/032-table-layout-docx-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)

---

## Phase 1: Setup & Foundational (Prerequisites)

**Purpose**: Test fixtures and core layout metadata shared across all table user stories

- [X] T001 [Foundational] Implement geometric test verification helper in `tests/test_xopp_geometry_helper.py` to unpack `.xopp` documents and assert stroke coordinates against bounding boxes and printable vertical bounds ($y \le \text{page\_height} - 60.0$)
- [X] T002 [Foundational] Define table continuation metadata and pagination diagnostic structures in `chuviettay/layout/table_layout.py`

---

## Phase 2: User Story 1 - Safe Table Pagination & Boundary Clamping (Priority: P1) 🎯 MVP

**Goal**: Guarantee table pagination never pushes stroke coordinates beyond the printable page boundary, deferring groups that do not fit the active page to a fresh page, and cleanly partitioning oversized groups with closed border caps.

**Independent Test**: Run `tests/test_table_pagination_closure.py` and verify all table stroke coordinates satisfy $y \le \text{page\_height} - 60.0$, with strictly monotonic pagination progression.

### Tests for User Story 1

- [X] T003 [P] [US1] Author regression tests in `tests/test_table_pagination_closure.py` asserting: (1) merged group exceeding remaining page space defers to next page; (2) group exceeding full page height partitions with valid borders; (3) 100% of generated strokes lie within printable vertical limits

### Implementation for User Story 1

- [X] T004 [US1] Update `TableLayoutData.slice_page` in `chuviettay/layout/table_layout.py`:
  - Add `can_defer_to_next_page: bool = True` parameter
  - If `curr_h == 0 and needed_h > max_height` and `can_defer_to_next_page`: return empty slice `(empty_data, start_row_idx)` to allow caller to break page
  - On fresh page (`not can_defer_to_next_page`): partition underlying rows to fit `max_height`, clamp single oversized rows, and emit continuation cells for spanning cells
- [X] T005 [US1] Update table pagination loop in `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py`:
  - Pass `can_defer_to_next_page = (cur_y > pf.content_top)` to `slice_page`
  - Clamp cell text line rendering: do not render any line whose `baseline_y > max_page_y`
  - Handle continuation across multiple pages with valid closed border caps
- [X] T006 [US1] Run `tests/test_table_pagination_closure.py` to confirm zero stroke overflow beyond page bottom margin

**Checkpoint**: User Story 1 (P1 MVP) is completely functional and verified with stroke coordinate assertions.

---

## Phase 3: User Story 2 - Math Formula Vertical Metrics Scaling Synchronization (Priority: P1)

**Goal**: Synchronize math formula ascent and descent with handwriting scale factor ($S \times \text{scale\_mult}$) in table cells, expanding row heights dynamically and eliminating formula collisions with cell horizontal borders.

**Independent Test**: Run `tests/test_table_rich_inlines.py` across multiple scale factors ($S=0.5, 1.0, 1.5$, and `--auto-xh`) and assert that measured row heights expand proportionally and zero formula strokes intersect top/bottom cell borders.

### Tests for User Story 2

- [X] T007 [P] [US2] Update and expand unit tests in `tests/test_table_rich_inlines.py` testing tall formulas (fractions, square roots, integrals) in table cells under scales $S=0.5, 1.0, 1.5$ and `--auto-xh`, verifying formula strokes stay strictly within cell vertical bounds

### Implementation for User Story 2

- [X] T008 [US2] Update `cell_inlines_formatter` in `chuviettay/layout/engine.py`:
  - Scale `item_asc = ext_asc * self.S * scale_mult` and `item_desc = ext_desc * self.S * scale_mult` when fetching from `self._math_extent`
  - Synchronize `extra_t = max(0.0, cur_asc - 0.7 * self.line_h)` and `extra_b = max(0.0, cur_desc - 0.3 * self.line_h)` to compute `line_h_tot` consistently in points
- [X] T009 [US2] Run `tests/test_table_rich_inlines.py` to confirm formula row height expansion and zero border collisions

**Checkpoint**: Formulas in table cells scale harmoniously with handwriting scale, preserving proper cell margins.

---

## Phase 4: User Story 3 - Long Unbroken Token Wrapping in Live Table Pipeline (Priority: P2)

**Goal**: Automatically break long URLs, file paths, hashes, and unbroken strings across character boundaries inside table cells, preventing horizontal bleed across column borders.

**Independent Test**: Run `tests/test_table_wrapping_pipeline.py` with 60+ character unbroken strings and verify strings wrap onto multiple lines inside the cell, with all stroke coordinates satisfying $x \le \text{cell\_x} + \text{col\_w}$.

### Tests for User Story 3

- [X] T010 [P] [US3] Author integration test `tests/test_table_wrapping_pipeline.py` testing live document table rendering with long URLs, hashes, and unbreakable strings, asserting wrapped line count $> 1$ and stroke coordinate containment

### Implementation for User Story 3

- [X] T011 [US3] Implement character-level token wrapping in `cell_inlines_formatter` in `chuviettay/layout/engine.py`:
  - When a text token has width $w > \text{usable\_w}$, subdivide the string into character slices whose individual widths $\le \text{usable\_w}$
  - Emit each slice as a wrapped line item within the cell, preserving standard word-space wrapping for normal words
- [X] T012 [US3] Run `tests/test_table_wrapping_pipeline.py` to confirm long tokens wrap cleanly inside cell boundaries

**Checkpoint**: Table cells wrap unbroken tokens safely without column border overflow.

---

## Phase 5: User Story 4 - DOCX Table Column Alignment & Nested Block Order (Priority: P2)

**Goal**: Reconstruct DOCX table columns using a 2D occupancy grid in `bridge.py` (supporting `colspan` and `rowspan`), and preserve document block order in `docx_importer.py` when cells contain alternating paragraphs and nested tables.

**Independent Test**: Run `tests/test_docx_table_occupancy.py` and `tests/test_docx_nested_table_order.py`, asserting correct logical column count and preserved block sequence ($A \to \text{Nested Table} \to B$).

### Tests for User Story 4

- [X] T013 [P] [US4] Author tests in `tests/test_docx_table_occupancy.py` (verifying 2D occupancy grid column calculation and placeholder padding) and `tests/test_docx_nested_table_order.py` (verifying document order for paragraphs and nested tables)

### Implementation for User Story 4

- [X] T014 [US4] Update table-to-Markdown serialization in `chuviettay/browser/bridge.py`:
  - Implement 2D occupancy grid mapping logical rows and columns
  - Compute `num_cols = max_logical_columns` across all rows
  - Output cell Markdown text at its logical origin column, and fill spanned positions with empty cell padding `" "`
- [X] T015 [US4] Update cell content extraction in `chuviettay/importer/docx_importer.py`:
  - Iterate `c._tc.iterchildren()` (with `c.iter_inner_content()` check) to parse `<w:p>` and `<w:tbl>` in encounter order
  - Add recursion guard (depth $\le 5$) for nested tables
- [X] T016 [US4] Run `tests/test_docx_table_occupancy.py` and `tests/test_docx_nested_table_order.py` to confirm alignment and order fidelity

**Checkpoint**: DOCX tables import with correct column alignment and true nested block order.

---

## Phase 6: User Story 5 - Web Table Modal Header Controls & Geometric Verification Gates (Priority: P3)

**Goal**: Respect the "Has header row" checkbox in the web table insertion modal, and ensure Playwright E2E and unit tests validate rendered table strokes.

**Independent Test**: Run web unit tests and Playwright E2E tests, verifying that unchecking the header checkbox creates a valid headerless Markdown table representation.

### Implementation for User Story 5

- [X] T017 [P] [US5] Update `btnConfirmTable` click handler in `webapp/js/write.js`:
  - When `hasHeader` is false, generate headerless Markdown table representation with blank header row `|   |   |` and delimiter `:---`
- [X] T018 [US5] Run web unit tests `npm run test:unit` and Playwright tests `npx playwright test tests/e2e/docx-import.spec.ts tests/e2e/write.spec.ts`

**Checkpoint**: Web table modal accurately reflects user header options with full E2E validation.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, architectural compliance, and full-suite verification

- [X] T019 [P] Update `README.md` and `CHANGELOG.md` with table pagination, formula scaling, token wrapping, and DOCX occupancy hardening notes
- [X] T020 [P] Run `tests/test_architecture.py` to verify strict compliance with MVC dependency boundaries
- [X] T021 [P] Run `tests/test_golden_master_real_path.py` to verify bit-exact SHA-256 hash preservation for Plain paper
- [X] T022 Run complete Python test suite (`py -3.12 -m pytest -q --timeout=60`) and browser tests (`npm run test:browser`)
- [X] T023 Execute runnable validation scenarios from `quickstart.md` to confirm end-to-end parity

---

## Dependencies & Execution Order

### Phase Dependencies
```
Phase 1: Setup & Foundational
       │
       ├────────────────────────┬────────────────────────┐
       ▼                        ▼                        ▼
Phase 2: US1 (Pagination)  Phase 3: US2 (Math Metrics) Phase 4: US3 (Token Wrapping)
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
                   Phase 5: US4 (DOCX Occupancy & Order)
                                │
                                ▼
                   Phase 6: US5 (Web Modal & E2E)
                                │
                                ▼
                   Phase 7: Polish & Final Gates
```

### Parallel Opportunities
- **Setup & Foundational**: `T001` (test helper) and `T002` (data structures) can run in parallel.
- **User Story 1**: `T003` (test) runs first, then `T004` (`table_layout.py`) and `T005` (`engine.py`).
- **User Story 2**: `T007` (test) runs in parallel with US1 tests; `T008` implements formula scaling.
- **User Story 3**: `T010` (test) can run in parallel; `T011` implements token wrapping.
- **User Story 4**: `T013` (test) can run in parallel; `T014` (`bridge.py`) and `T015` (`docx_importer.py`) touch independent files and can run in parallel.
- **User Story 5**: `T017` (`write.js`) can run in parallel with Python tasks.
- **Polish**: `T019`, `T020`, `T021` can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Foundational: test helper and continuation structures).
2. Complete Phase 2 (User Story 1: pagination boundary clamping).
3. Validate: `tests/test_table_pagination_closure.py` passes, 100% strokes within page boundaries.

### Incremental Delivery
1. Add Phase 3 (User Story 2: Math formula scaling) -> Verify `test_table_rich_inlines.py` at scales 0.5, 1.0, 1.5.
2. Add Phase 4 (User Story 3: Long token wrapping) -> Verify `test_table_wrapping_pipeline.py`.
3. Add Phase 5 (User Story 4: DOCX occupancy grid and nested order) -> Verify `test_docx_table_occupancy.py`.
4. Add Phase 6 (User Story 5: Web table modal header control) -> Verify `write.js` and Playwright E2E.
5. Final Polish & full test gate (`pytest`, `ruff`, Golden Master, architecture).
