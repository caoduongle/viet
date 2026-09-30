# Tasks: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Feature**: `015-docx-fidelity-hardening`  
**Input**: Design artifacts from `specs/015-docx-fidelity-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize environment and verify test baseline.

- [X] T001 Verify virtual environment and existing test suite baseline via `pytest --timeout=30 tests/test_fidelity_pdf_first.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared utilities and XML namespace constants required across user stories.

**⚠️ CRITICAL**: Must complete before implementing whiteout and converter features.

- [X] T002 Inspect and configure standard OpenXML namespaces and target XML part definitions (`word/document.xml`, `word/header*.xml`, `word/footer*.xml`, `word/footnotes*.xml`, `word/endnotes*.xml`, `word/comments*.xml`) in `chuviettay/fidelity/background.py`

**Checkpoint**: Foundation ready - user story implementation can begin.

---

## Phase 3: User Story 1 - Consistent Converter Availability Caching Across Platforms (Priority: P1) 🎯 MVP

**Goal**: Resolve Linux CI failure by ensuring `FidelityConverter.is_word_available()` sets `cls._word_available_cache = False` on non-Windows platforms, providing idempotent cache behavior across all operating systems.

**Independent Test**:
```bash
pytest tests/test_fidelity_pdf_first.py -k "test_r6_converter_availability_caching" -vv
```

### Tests for User Story 1 🧪
- [X] T003 [US1] Update `test_r6_converter_availability_caching` in `tests/test_fidelity_pdf_first.py` to assert non-Windows caching invariants (`_word_available_cache is False` after first call)

### Implementation for User Story 1
- [X] T004 [US1] Implement cross-platform availability caching in `chuviettay/fidelity/converter.py` by checking `cls._word_available_cache is not None` first, then assigning `cls._word_available_cache = False` prior to returning `False` on non-Windows (`sys.platform != "win32"`)
- [X] T005 [US1] Verify converter caching passes on all platforms via `pytest tests/test_fidelity_pdf_first.py -k "test_r6"`

**Checkpoint**: User Story 1 complete. Linux CI failure is eliminated.

---

## Phase 4: User Story 2 - Fidelity Mode-Aware GUI Controls & Layout Parameter Locking (Priority: P1) 🎯 MVP

**Goal**: Automatically lock and disable paper size, orientation, background grid, and spacing controls when the user selects "Khóa bố cục & ảnh (Fidelity)" in the Write tab, and restore them when returning to "Tự do (Semantic)".

**Independent Test**:
```bash
pytest tests/test_gui_document.py -k "test_gui_mode_changed_locks_paper_options" -vv
```

### Tests for User Story 2 🧪
- [X] T006 [P] [US2] Write unit test `test_gui_mode_changed_locks_paper_options` in `tests/test_gui_document.py` verifying state toggling (`disabled` vs `readonly`/`normal`) for `cb_paper`, `btn_paper_custom`, `cb_ori`, `cb_bg`, and `entry_spacing`

### Implementation for User Story 2
- [X] T007 [US2] Store instance references for `self.btn_paper_custom` (Button "Cỡ...") and `self.entry_spacing` (Entry "Khoảng cách") in `_build_options()` in `chuviettay/view/write_tab.py`
- [X] T008 [US2] Implement `_on_mode_changed(self, event=None)` handler, bind `<<ComboboxSelected>>` to `self.cb_mode`, add trace to `self.v_mode`, and initialize control states at the end of `_build_options()` in `chuviettay/view/write_tab.py`
- [X] T009 [US2] Verify GUI mode switching behavior by running `pytest tests/test_gui_document.py -k "mode_changed"`

**Checkpoint**: User Story 2 complete. GUI cleanly communicates Fidelity layout locking.

---

## Phase 5: User Story 3 - Non-Destructive OpenXML Surgical Text Whiteout (Priority: P1) 🎯 MVP

**Goal**: Replace whole-document `python-docx` load/save in `WhiteoutBackgroundGenerator.create_whiteout_docx` with direct ZIP archive stream processing and surgical text run whitening, preserving 100% of images, charts, SmartArt, shapes, and relationships byte-for-byte.

**Independent Test**:
```bash
pytest tests/test_docx_fidelity.py -k "whiteout" -vv
```

### Tests for User Story 3 🧪
- [X] T010 [P] [US3] Add unit test `test_whiteout_preserves_non_text_parts_checksum` in `tests/test_docx_fidelity.py` verifying SHA256 checksum identity of embedded media files (`word/media/*`) and XML run color whitening (`#FFFFFF`)

### Implementation for User Story 3
- [X] T011 [US3] Implement native ZIP archive inspection, pass-through streaming for non-target parts, and safe temporary file writing in `WhiteoutBackgroundGenerator.create_whiteout_docx` in `chuviettay/fidelity/background.py`
- [X] T012 [US3] Implement surgical XML text whitening using `lxml.etree` with `resolve_entities=False, no_network=True`, schema-compliant child ordering (`r.insert(0, rPr)`), theme color removal, highlight/shading clearing, and DrawingML `<a:r>` fill replacement in `chuviettay/fidelity/background.py`
- [X] T013 [US3] Verify surgical whiteout functionality and non-text asset preservation via `pytest tests/test_docx_fidelity.py -k "whiteout"`

**Checkpoint**: User Story 3 complete. Whiteout protects complex OpenXML objects with 0 byte alterations.

---

## Phase 6: User Story 4 - Subprocess Invocation Hygiene & Execution Safety (Priority: P2)

**Goal**: Remove `shell=True` from `FidelityConverter._run_powershell_script`, executing `powershell.exe` directly via arguments array to enhance security and eliminate quoting inconsistencies.

**Independent Test**:
```bash
pytest tests/test_fidelity_pdf_first.py -k "test_run_powershell_script_hygiene" -vv
```

### Implementation for User Story 4
- [X] T014 [US4] Remove `shell=True` and resolve executable path via `shutil.which("powershell") or "powershell"` in `_run_powershell_script` in `chuviettay/fidelity/converter.py`
- [X] T015 [US4] Add unit test in `tests/test_fidelity_pdf_first.py` asserting `_run_powershell_script` invokes subprocesses with `shell=False`

**Checkpoint**: User Story 4 complete. PowerShell automation runs without shell wrapper.

---

## Phase 7: User Story 5 - Transparent Platform Capabilities & Accurate Documentation (Priority: P2)

**Goal**: Clarify platform support in documentation and error messages, explaining that spatial text extraction requires Word COM on Windows while LibreOffice provides PDF conversion.

**Independent Test**:
- Manual review of updated `README.md` and verification of error message wording in `converter.py` and `extractor.py`.

### Implementation for User Story 5
- [X] T016 [P] [US5] Update runtime error messages and docstrings in `chuviettay/fidelity/converter.py` and `chuviettay/fidelity/extractor.py` to clarify that spatial layout extraction requires Microsoft Word on Windows and recommend `--mode semantic` for other environments
- [X] T017 [P] [US5] Update `README.md` to document the platform capability matrix (Word COM on Windows vs LibreOffice for PDF background conversion) and recommend Semantic mode for headless Linux/macOS

**Checkpoint**: User Story 5 complete. Documentation and error messages are accurate and transparent.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Repository validation, code quality checks, and regression verification across all components.

- [X] T018 Run code style and lint checks via `ruff check chuviettay/ tests/`
- [X] T019 Run full test suite regression validation via `pytest -vv --timeout=30` (confirming all 472+ tests pass)
- [X] T020 Run quickstart validation scenarios defined in `specs/015-docx-fidelity-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**:
  - **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories. (Fixes Linux CI).
  - **User Story 2 (P1)**: Can start after Foundational (Phase 2). GUI layer change, completely independent.
  - **User Story 3 (P1)**: Can start after Foundational (Phase 2). Core background generator change, independent.
  - **User Story 4 (P2)**: Subprocess hygiene in `converter.py`. Can run after US1.
  - **User Story 5 (P2)**: Documentation and wording in `README.md` and error strings. Can run in parallel with any story.
- **Polish (Phase 8)**: Depends on completion of all user stories.

### Parallel Opportunities

- T006 [US2] (GUI test) and T010 [US3] (Whiteout test) can be written in parallel.
- User Story 1 (`converter.py`), User Story 2 (`write_tab.py`), and User Story 3 (`background.py`) operate on completely different source files and can be implemented in parallel.
- T016 and T017 (Documentation & error messages) can be drafted in parallel with technical implementation.

---

## Parallel Example: User Stories 1, 2, and 3

```bash
# Developer / Agent A: User Story 1 (Linux CI fix)
Task: T003 & T004 in chuviettay/fidelity/converter.py and tests/test_fidelity_pdf_first.py

# Developer / Agent B: User Story 2 (GUI mode locking)
Task: T006, T007 & T008 in chuviettay/view/write_tab.py and tests/test_gui_document.py

# Developer / Agent C: User Story 3 (OpenXML surgical whiteout)
Task: T010, T011 & T012 in chuviettay/fidelity/background.py and tests/test_docx_fidelity.py
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2 & 3)

1. Complete Phase 1: Setup & baseline verification (T001)
2. Complete Phase 2: Foundational OpenXML schema definitions (T002)
3. Complete Phase 3: User Story 1 (T003-T005) -> CI is GREEN on all platforms!
4. Complete Phase 4: User Story 2 (T006-T009) -> GUI UX is clean and locked!
5. Complete Phase 5: User Story 3 (T010-T013) -> 100% preservation of diagrams, shapes, and media!
6. Complete Phase 6 & 7: Subprocess hygiene & documentation (T014-T017)
7. Complete Phase 8: Final regression validation (T018-T020)
