# Tasks: Paper Sizes, Page Margins & Native XOPP Backgrounds

**Feature Branch**: `011-paper-size-and-background` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish core data types, paper sizing standards, and unit conversion utilities.

- [X] T001 Create `chuviettay/document/page_format.py` defining `PaperSize`, `PageBackground`, `PageFormat`, `PAPER_SIZES`, `VALID_BACKGROUND_STYLES`, and `parse_length`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and data transfer interfaces that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Add `page_open_xml` to `chuviettay/model/xopp.py` for dynamic page/background XML while strictly preserving `xopp.PAGE_OPEN`
- [X] T003 Update `WriteOptions` in `chuviettay/model/composer.py` with paper/background fields, validation, and `resolve_page_format()`
- [X] T004 Update `PageBuffer` in `chuviettay/layout/stream.py` to accept `default_background` and support per-page dimensions & backgrounds via `xopp.page_open_xml`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Native Paper Sizes, Orientations & Content Margins (Priority: P1) 🎯 MVP

**Goal**: Enable standardized paper formats (A5, A4, A3, Letter, Legal, 16:9, 4:3, Custom), orientation swapping, and margins in DocumentLayoutEngine without fixed MAXH bounds.

**Independent Test**: Render an A4 portrait document and verify all pages in `.xopp` have exact dimensions `width="595.28" height="841.89"`, text starts at `x0 = margin_left`, and page breaks occur before reaching `height - margin_bottom`.

### Tests for User Story 1
- [X] T005 [P] [US1] Create unit tests for `PaperSize`, orientations, margins, and `parse_length` in `tests/test_page_format.py`
- [X] T006 [P] [US1] Add integration test for A4, A3, A5, and custom paper pagination in `tests/test_document_pipeline.py`

### Implementation for User Story 1
- [X] T007 [US1] Decouple `self.x0`, `self.width`, and `self.line_h` in `DocumentLayoutEngine.__init__` in `chuviettay/layout/engine.py` using `PageFormat`
- [X] T008 [US1] Update `DocumentLayoutEngine.render` in `chuviettay/layout/engine.py` to paginate based on `page_format.max_page_y`, initialize `cur_y = page_format.content_top`, fix table break condition to `cur_y > content_top`, and set exact page dimensions on every page

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Native XOPP Background Styles & Grid Configuration (Priority: P1) 🎯 MVP

**Goal**: Support native XJournal++ XML backgrounds (`plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `music` with configurable `spacing` and `margin`) without vector stroke overhead.

**Independent Test**: Configure `background="graph", background_spacing=14.17` (5mm), render document, and verify `<background ... style="graph" config="r1=14.17"/>` appears in `.xopp` XML with 0 artificial background strokes.

### Tests for User Story 2
- [X] T009 [P] [US2] Add unit tests for `PageBackground.to_xml()` (plain, graph, ruled, dotted, music, config string generation, style whitelist, color hex validation) in `tests/test_page_format.py`
- [X] T010 [P] [US2] Add test in `tests/test_document_pipeline.py` verifying generated `.xopp` contains native `<background .../>` XML and zero background strokes

### Implementation for User Story 2
- [X] T011 [US2] Integrate `page_format.background` into `DocumentLayoutEngine.render` in `chuviettay/layout/engine.py` passing it to `pb.append_page()`

**Checkpoint**: User Stories 1 AND 2 work together as a complete MVP notebook generator.

---

## Phase 5: User Story 3 - CLI Selection of Paper Sizes & Backgrounds (Priority: P2)

**Goal**: Allow command-line users to specify paper sizes, orientations, and background styles/spacing via CLI flags.

**Independent Test**: Run `python hw_note.py write test.md -o output.xopp --paper a4 --orientation landscape --background graph --background-spacing 5mm` and inspect generated XML.

### Tests for User Story 3
- [X] T012 [P] [US3] Add CLI parsing tests for `--paper`, `--orientation`, `--background`, `--background-spacing`, and unit strings in `tests/test_cli_format.py`

### Implementation for User Story 3
- [X] T013 [US3] Add CLI arguments (`--paper`, `--orientation`, `--paper-width`, `--paper-height`, `--background`, `--background-spacing`, `--background-color`) to `build_parser` in `chuviettay/cli.py`
- [X] T014 [US3] Update `_cmd_write` in `chuviettay/cli.py` to construct `WriteOptions` with paper/background options and route text / `-t` / stdin to `ctl.write_document` using `TxtImporter`

**Checkpoint**: CLI provides full headless access to paper formatting and backgrounds.

---

## Phase 6: User Story 4 - GUI Interactive Paper & Background Controls (Priority: P2)

**Goal**: Provide interactive GUI dropdowns for paper size, orientation, background style, spacing, and custom size dialog in WriteTab.

**Independent Test**: Launch GUI WriteTab in test mode, select A4 + Ô Li, write document, and verify generated file format.

### Tests for User Story 4
- [X] T015 [P] [US4] Add GUI tests for WriteTab paper dropdowns, background controls, and custom size dialog in `tests/test_gui_document.py`

### Implementation for User Story 4
- [X] T016 [US4] Add "Trang & Nền giấy" LabelFrame with dropdowns (Khổ giấy, Chiều giấy, Nền giấy, Khoảng cách) and Custom Paper dialog in `chuviettay/view/write_tab.py`
- [X] T017 [US4] Update `WriteTab.read_options` and `WriteTab.do_write` in `chuviettay/view/write_tab.py` to read paper/background settings and route direct text input to `ctl.write_document` via `TxtImporter`

**Checkpoint**: GUI matches CLI capabilities with full visual setup controls.

---

## Phase 7: User Story 5 - Backward Compatibility & System Integrity (Priority: P3)

**Goal**: Guarantee 100% backward compatibility for legacy callers, calibration generators, and byte-for-byte SHA256 tests.

**Independent Test**: Run `pytest tests/test_golden_master.py` and full test suite to confirm 100% pass rate.

### Verification Tasks
- [X] T018 [P] [US5] Run golden master regression verification with `pytest tests/test_golden_master.py`
- [X] T019 [US5] Verify calibration grid generation (`check`, `seed`, `make_grid`) operates unchanged without regressions in `tests/test_xopp.py`

**Checkpoint**: Full backward compatibility preserved across all existing features.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, linting, and final quality checks.

- [X] T020 [P] Validate runnable scenarios in `specs/011-paper-size-and-background/quickstart.md`
- [X] T021 Run code linter `ruff check .` and resolve any style/lint issues
- [X] T022 Run complete automated test suite `pytest -v --timeout=30` to ensure zero regressions

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2; integrates with US1 in `engine.py`.
- **User Story 3 (Phase 5)**: Depends on Phases 3 and 4.
- **User Story 4 (Phase 6)**: Depends on Phases 3 and 4.
- **User Story 5 (Phase 7)**: Depends on Phases 3 through 6.
- **Polish (Phase 8)**: Depends on all user stories completed.

### Parallel Opportunities
- Within Phase 3: T005 and T006 can run in parallel before T007/T008.
- Within Phase 4: T009 and T010 can run in parallel.
- Phases 5 and 6 can be developed in parallel once Phases 3 and 4 are complete.
- Polish tasks T020 and T021 can execute concurrently.

---

## Implementation Strategy

### MVP Scope (Phases 1, 2, 3, 4)
1. Complete Phase 1: `page_format.py` (Paper sizes, backgrounds, units).
2. Complete Phase 2: `xopp.py`, `WriteOptions`, `PageBuffer`.
3. Complete Phase 3: `DocumentLayoutEngine` geometry & pagination (User Story 1).
4. Complete Phase 4: Native background XML generation (User Story 2).
5. **Validate MVP**: Generate multi-page A4/A3 notebooks with 5mm ô li grids.

### Incremental Delivery
- Add Phase 5 (CLI flags) for automated scripts.
- Add Phase 6 (GUI WriteTab controls) for interactive users.
- Add Phase 7 & 8 (Backward compatibility & full test suite).
