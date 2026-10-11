# Tasks: Xournal++ Paper Background and Geometry Parity

**Input**: Design documents from `specs/031-xournalpp-paper-parity/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)

---

## Phase 1: Setup & Foundational (Prerequisites)

**Purpose**: Core model extensions and length parsing enhancements that underpin all user stories

- [X] T001 [Foundational] Extend `parse_length` with `allow_negative: bool = False` in `chuviettay/document/page_format.py` to support negative margins
- [X] T002 [Foundational] Enhance `PageBackground` dataclass and `to_xml()` in `chuviettay/document/page_format.py` with Xournal++ attributes (`r1`, `m1`, `lw`, `f1`, `f2`, `af1`, `af2`, `rm`, `bli`, `blw`), negative $m_1$ serialization, and comma-separated `config`
- [X] T003 [P] [Foundational] Re-export `PageBackground` and `BACKGROUND_PRESETS` in `chuviettay/controller/results.py` to maintain MVC architectural boundaries

---

## Phase 2: User Story 1 - PDF Background Page Index and Domain Parity (Priority: P1) 🎯 MVP

**Goal**: Fix PDF background XML in `.xopp` to use 1-based `pageno`, enforce `domain="absolute"`, sanitize filenames, and eliminate all `domain="relative"` references.

**Independent Test**: Generate `.xopp` files with PDF backgrounds, assert `pageno="1"` for page index 0, verify `domain="absolute"`, and assert `git grep 'domain="relative"'` returns 0 results.

### Tests for User Story 1

- [X] T004 [P] [US1] Add unit tests in `tests/test_docx_fidelity.py` asserting `pageno="1"` for page index 0, `domain="absolute"`, and bare relative filenames

### Implementation for User Story 1

- [X] T005 [US1] Update `pdf_background_xml` in `chuviettay/model/xopp.py` to default `domain="absolute"`, sanitize filenames using `os.path.basename`, and document 1-based `pageno`
- [X] T006 [US1] Update `chuviettay/fidelity/engine.py` to pass `page_index + 1` and `domain="absolute"` with bare filename
- [X] T007 [US1] Update existing assertions in `tests/test_docx_fidelity.py` (lines ~110, 261-265) to match 1-based index and verify 0 occurrences of `domain="relative"` across repo

**Checkpoint**: PDF background generation matches Xournal++ specification completely; passes all docx fidelity tests.

---

## Phase 3: User Story 2 - Paper Background Geometry & Web SVG Rendering (Priority: P1)

**Goal**: Unify SVG paper rendering in `webapp/js/paper.js` and reproduce Xournal++ geometry (Ruled/Lined with header 80/footer 60, negative $m_1$, Graph with margins and bold intervals, Dotted, Isometric Graph/Dotted, and 5-line Staves with light/dark contrast colors).

**Independent Test**: Load paper backgrounds in web preview and assert exact line coordinates, bounds, line counts, and stroke colors matching Xournal++ views.

### Tests for User Story 2

- [X] T008 [P] [US2] Update E2E test `tests/e2e/paper-geometry.spec.ts` to assert Xournal++ stroke colors (`#40a0ff`, `#ff0080`), header/footer bounds, and negative $m_1$ rendering

### Implementation for User Story 2

- [X] T009 [US2] Implement unified `renderBackgroundSvg(bg, width, height)` in `webapp/js/paper.js` reproducing Xournal++ geometry formulas (Ruled/Lined bounds `[80, height - 60]`, negative $m_1$, Graph margins & `bli`/`blw`, Dotted, Isometric centered steps, and 5-line Staves step $62.5\,\text{pt}$)
- [X] T010 [US2] Update `parseBackgroundNode()` in `webapp/js/paper.js` to parse `config` splitting on both commas and semicolons, parsing `r1`, `m1`, `lw`, `bli`, `blw`, `rm`, `f1`, `f2`
- [X] T011 [US2] Refactor `renderPageSvgString` and `renderPageSvgElement` in `webapp/js/paper.js` to delegate background drawing to `renderBackgroundSvg`
- [X] T012 [US2] Implement automatic light/dark contrast color derivation in `webapp/js/paper.js` (`#40a0ff`/`#ff0080` for light paper, `#434343`/`#220080` for dark paper, `#000000`/`#ffffff` for staves)

**Checkpoint**: Web SVG preview renders all paper types identically to Xournal++, with unified codebase and zero duplication.

---

## Phase 4: User Story 3 - Adaptive Baseline Snapping to Ruling Lines (Priority: P1)

**Goal**: Align handwritten text baselines to horizontal ruling lines ($y = 80 + k \cdot \text{pitch}$) on Ruled/Lined paper, break pages before footer ($y > \text{height} - 60$), clamp to lined margins, and preserve 100% hash invariance for Plain paper.

**Independent Test**: Run `tests/test_golden_master_real_path.py` (hashes must match bit-exact) and verify baseline coordinates on Ruled paper match $80 + k \cdot r_1$.

### Tests for User Story 3

- [X] T013 [P] [US3] Create `tests/test_paper_ruling_snap.py` testing baseline snapping on Ruled/Lined paper across font sizes ($12\,\text{pt}, 24\,\text{pt}, 36\,\text{pt}$) and verifying Plain paper bypass

### Implementation for User Story 3

- [X] T014 [US3] Add `snap_to_ruling: bool = True` to `WriteOptions` in `chuviettay/model/composer.py`
- [X] T015 [US3] Implement baseline ruling snapping in `DocumentLayoutEngine.render()` in `chuviettay/layout/engine.py`:
  - Enforce condition: `self.opts.snap_to_ruling and self.page_format.background.style in ("ruled", "lined")`
  - Snap first baseline: smallest $y = 80.0 + k \cdot r_1 \ge \text{content\_top} + \text{eff\_line\_h}$
  - Step baselines by $\text{pitch} = r_1 \cdot \max(1, \text{round}(\text{eff\_line\_h} / r_1))$
  - Trigger page break when next baseline exceeds $\text{pageHeight} - 60.0$
  - Clamp left bounds $x \ge m_1 + 8.0$ for $m_1 > 0$ and right bounds $x \le \text{pageWidth} + m_1 - 8.0$ for $m_1 < 0$
  - Isolate Plain background: maintain exact legacy continuous layout path when snapping is disabled or background is not ruled/lined
- [X] T016 [US3] Run `tests/test_golden_master_real_path.py` to confirm zero hash changes for plain paper

**Checkpoint**: Text rests naturally on ruled lines; Plain paper golden master test remains 100% green.

---

## Phase 5: User Story 4 - PageBackground Presets & CLI Parity (Priority: P2)

**Goal**: Support standard Xournal++ templates (`BACKGROUND_PRESETS`), validate negative $m_1$, and expose CLI flags (`--bg-preset`, `--bg-r1`, `--bg-m1`, `--bg-color`, `--no-snap-ruling`).

**Independent Test**: Run `chuviettay write` with `--bg-preset lined_college --bg-m1 "-72pt"`, assert generated XML contains `<background ... style="lined" config="...m1=-72.0..."/>`.

### Tests for User Story 4

- [X] T017 [P] [US4] Add unit tests in `tests/test_paper_size_background.py` for `BACKGROUND_PRESETS` catalog, negative $m_1$ validation, and XML config generation

### Implementation for User Story 4

- [X] T018 [US4] Define `BACKGROUND_PRESETS` in `chuviettay/document/page_format.py` matching `pagetemplates.ini.in` (`plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `staves`, `lined_narrow`, `lined_college`, `lined_wide`, `graph_5mm`, `graph_grid`)
- [X] T019 [US4] Update `WriteOptions.validate()` in `chuviettay/model/composer.py` to accept negative `background_margin` within $(-pageWidth, pageWidth)$
- [X] T020 [US4] Add CLI arguments in `chuviettay/cli.py` (`--bg-preset`, `--bg-r1`, `--bg-m1`, `--bg-color`, `--no-snap-ruling`) with robust handling of negative values (e.g. `--bg-m1=-72pt` or `--bg-m1 "-72pt"`)
- [X] T021 [US4] Update `tests/test_cli.py` to verify command-line invocation with background presets and negative margin flags

**Checkpoint**: CLI and options validation fully support Xournal++ templates and negative margins.

---

## Phase 6: User Story 5 - Unified Page Catalog & UI Synchronization (Priority: P2)

**Goal**: Provide single source of truth `get_page_catalog()` and synchronize dropdown options across Tkinter UI and Web client.

**Independent Test**: Verify `AppController.get_page_catalog()` returns all formats, presets, and color palettes, and that web/Tkinter dropdowns populate them dynamically.

### Tests for User Story 5

- [X] T022 [P] [US5] Add unit test in `tests/test_page_catalog.py` verifying catalog structure, paper sizes, presets, and color tones

### Implementation for User Story 5

- [X] T023 [US5] Implement `get_page_catalog()` in `chuviettay/document/page_format.py` and delegate via `AppController.get_page_catalog()` in `chuviettay/controller/app_controller.py`
- [X] T024 [US5] Update Tkinter write tab in `chuviettay/view/write_tab.py` to populate paper format and preset selectors from `AppController.get_page_catalog()`
- [X] T025 [US5] Update web application in `webapp/index.html` and `webapp/js/write.js` to render full paper presets and background tones with instant live preview

**Checkpoint**: Web and desktop interfaces dynamically synchronize all paper formats and styling presets from the unified catalog.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, architectural validation, and final full-suite verification

- [X] T026 [P] Update `README.md` and `CHANGELOG.md` with new paper presets, CLI flags, and Xournal++ parity details
- [X] T027 [P] Run `tests/test_architecture.py` to verify strict compliance with MVC dependency boundaries
- [X] T028 Run complete Python test suite (`py -3.12 -m pytest -q --timeout=60`) and Playwright tests (`npx playwright test`)
- [X] T029 Execute runnable validation scenarios from `quickstart.md` to confirm end-to-end parity

---

## Dependencies & Execution Order

### Phase Dependencies
```
Phase 1: Setup & Foundational
       │
       ├────────────────────────┬────────────────────────┐
       ▼                        ▼                        ▼
Phase 2: US1 (PDF Parity)  Phase 3: US2 (Web SVG)   Phase 4: US3 (Snapping)
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
                   Phase 5: US4 (Presets & CLI)
                                │
                                ▼
                   Phase 6: US5 (Unified UI Catalog)
                                │
                                ▼
                   Phase 7: Polish & Final Gates
```

### Parallel Opportunities
- **Setup & Foundational**: `T003` can run in parallel with `T001` and `T002`.
- **User Story 1**: `T004` (test) runs first, then `T005`, `T006`, `T007`.
- **User Story 2**: `T008` (test) can run in parallel; `T009`, `T010`, `T011`, `T012` modify `webapp/js/paper.js`.
- **User Story 3**: `T013` (test) runs in parallel; `T014`, `T015`, `T016` implement snapping.
- **User Story 4 & 5**: `T017` and `T022` test tasks can be authored in parallel.
- **Polish**: `T026` (docs) and `T027` (architecture check) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 & Foundational)
1. Complete Phase 1 (Foundational: length parsing and `PageBackground` attributes).
2. Complete Phase 2 (User Story 1: PDF background fix).
3. Validate: `tests/test_docx_fidelity.py` passes, `domain="relative"` eliminated.

### Incremental Delivery
1. Add Phase 3 (User Story 2: Web SVG preview parity) -> Verify web preview in browser.
2. Add Phase 4 (User Story 3: Ruling snapping) -> Verify `test_golden_master_real_path.py` and ruled alignment.
3. Add Phase 5 (User Story 4: Presets & CLI) -> Verify CLI `--bg-preset`.
4. Add Phase 6 (User Story 5: Unified UI catalog) -> Verify Web & Tkinter dropdowns.
5. Final Polish & full test gate.
