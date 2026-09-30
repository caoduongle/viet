# Feature Specification: Unify Direct Text Input into Document IR Pipeline & Margin Validation

**Feature Branch**: `012-unify-write-text-pipeline`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User request: "Feature khổ giấy/nền giấy đã được triển khai khá đầy đủ, và CI hiện tại pass toàn bộ matrix. Tuy nhiên mình vẫn thấy một lỗi quan trọng ở đường đi GUI khi nhập trực tiếp, cần sửa trước khi coi feature này hoàn chỉnh. GUI gõ/dán text trực tiếp (current_doc is None) gọi ctl.write_text(...) nhưng write_text() hiện vẫn gọi composer.write_document(...) và composer.compose_document() cũ dùng MAXH, bank.d['width'], bank.d['x0'], xopp.PAGE_OPEN thay vì PageFormat và PageBackground. Cho write_text() trở thành wrapper của Document IR pipeline để toàn bộ văn bản (TXT trực tiếp, Markdown, DOCX) đi qua một layout pipeline duy nhất (DocumentLayoutEngine -> PageFormat -> Background -> PageBuffer -> XOPP). Thêm validation margin_left + margin_right >= page_width và margin_top + margin_bottom >= page_height trong WriteOptions.validate(). Cập nhật test_gui_write_tab_paper_and_background_options() để assert app.write_tab.current_doc is None trước khi do_write() và kiểm tra output XML."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Direct Text Input Uses Unified Document IR Pipeline & Paper Settings (Priority: P1) 🎯 MVP

As a user typing or pasting text directly into the GUI or calling `controller.write_text()`, I want the output `.xopp` document to strictly adhere to my selected paper size (A4, A3, Letter, etc.), orientation (portrait, landscape), page margins, and background grid (ô li graph, ruled, etc.), rather than falling back to the legacy fixed `MAXH=3000` / plain background format.

**Why this priority**: Direct text entry is the primary and most frequent workflow in the GUI tab "Viết chữ". Maintaining a split architecture where imported files use `DocumentLayoutEngine` while direct text uses the legacy composer creates inconsistent document outputs, regressions in paper formatting, and duplicate maintenance burdens.

**Independent Test**: Call `controller.write_text("Chào buổi sáng", opts, "out.xopp")` with `opts.paper="a3", opts.orientation="landscape", opts.background="graph", opts.background_spacing=14.17` (5mm). Verify that the output `.xopp` file contains `<page width="1190.55" height="841.89">` and `<background ... style="graph" config="r1=14.17"/>`, without falling back to legacy single-page MAXH coordinates.

**Acceptance Scenarios**:

1. **Given** direct text input via `controller.write_text(text, opts, out_path)`, **When** executed, **Then** text is structured into Document IR and rendered via `DocumentLayoutEngine(bank, opts).render()`.
2. **Given** direct text input in GUI "Viết chữ" tab with `current_doc is None`, **When** the user clicks "Tạo file viết tay (.xopp)...", **Then** the output document uses the selected paper dimensions, orientation, and background style.
3. **Given** multi-paragraph direct text containing blank lines (`\n\n`), **When** rendered via `write_text()`, **Then** paragraph spacing and empty line preservation behave identically to standard Document IR paragraph layout.
4. **Given** legacy `composer.compose_document()`, **When** inspected, **Then** it is marked as deprecated or isolated to avoid accidental invocation in modern document flows.

---

### User Story 2 - Strict Margin Boundary Validation (Priority: P1) 🎯 MVP

As a user configuring custom paper margins, I want the system to immediately reject invalid margin configurations where the sum of margins meets or exceeds the paper dimensions (e.g. `margin_left + margin_right >= page_width` or `margin_top + margin_bottom >= page_height`), so that the layout engine is protected from degenerate states and unexpected content overflow.

**Why this priority**: Currently, `WriteOptions.validate()` allows margin configurations where `margin_left + margin_right >= width`, causing `PageFormat.usable_width` to clamp to a minimal fallback (`20.0 pt`), which causes text wrapping anomalies and unusable layouts. Early validation at the domain boundary prevents runtime defects.

**Independent Test**: Construct `WriteOptions(paper="a4", margin_left=400.0, margin_right=300.0)` where `margin_left + margin_right = 700.0 > 595.28`. Call `opts.validate()`. Assert that a descriptive `ValueError` is raised.

**Acceptance Scenarios**:

1. **Given** `WriteOptions` where `margin_left + margin_right >= page_width`, **When** `validate()` is called, **Then** it raises `ValueError` with a clear explanation of the page width and margin sum.
2. **Given** `WriteOptions` where `margin_top + margin_bottom >= page_height`, **When** `validate()` is called, **Then** it raises `ValueError` with a clear explanation of the page height and margin sum.
3. **Given** custom paper dimensions (`paper="custom", paper_width=200, paper_height=200`), **When** margins exceed `200 pt`, **Then** validation fails with a helpful error message.
4. **Given** valid standard margins on A4 (`left=36, right=36, top=40, bottom=40`), **When** `validate()` is called, **Then** validation passes without error.

---

### User Story 3 - GUI Direct-Text End-to-End Regression Verification (Priority: P2)

As a developer and automated test runner, I want test suites to specifically exercise the GUI direct-text path (`write_tab.current_doc is None`) with paper and background options, ensuring that direct text entry never silently regresses to the legacy layout engine.

**Why this priority**: Existing GUI tests checked paper dropdown values, but must be fortified with strict assertions on `write_tab.current_doc is None` and inspection of uncompressed XML output tags to guarantee end-to-end coverage of the unified pipeline.

**Independent Test**: Run `pytest tests/test_gui_document.py -v` (with mock/headless UI support) and verify that direct text entry generates the expected A3 landscape graph background XML.

**Acceptance Scenarios**:

1. **Given** `WriteTab` with typed text and no opened document (`current_doc is None`), **When** paper format is set to A3 landscape with Ô Li background and `do_write()` is executed, **Then** generated `.xopp` contains `<page width="1190.55" height="841.89">` and `style="graph"`.
2. **Given** automated GUI tests, **When** validating `do_write()`, **Then** an explicit assertion `assert app.write_tab.current_doc is None` is performed before writing.

---

### User Story 4 - Backward Compatibility & Verification Integrity (Priority: P3)

As a maintainer of the project, I want backward compatibility preserved for existing automated tests and legacy callers, while clearly isolating the legacy single-file algorithm verification from the modern unified pipeline.

**Why this priority**: Preserves existing test stability and adheres to Constitution Principle III (Comprehensive Automated Testing) and Principle IV (Loose Coupling).

**Independent Test**: Run `pytest -v` across all 355+ tests and confirm 100% pass rate.

**Acceptance Scenarios**:

1. **Given** existing CLI commands and test suites, **When** executed, **Then** all tests pass cleanly.
2. **Given** `test_golden_master.py` (which validates the exact SHA-256 byte output of the pre-MVC monolithic algorithm), **When** executed, **Then** it continues to verify the legacy composer algorithm deterministically.

---

### Edge Cases

- **Empty Text String**: `write_text("", opts, out)` must either raise a clear user-facing validation warning or produce a valid single-page document with configured paper dimensions.
- **Text with Multiple Consecutive Newlines (`\n\n\n`)**: Must be preserved as empty paragraphs and spacing in Document IR, without breaking pagination.
- **Custom Paper Margin Edge Cases**: When user specifies custom dimensions with units (e.g. `10cm` width) and margins in `pt`, validation must resolve dimensions and margins to the same unit (points) before comparing sums.
- **Landscape Orientation Margin Bounds**: Margin comparison must evaluate against effective page width and height after orientation swapping (e.g. A4 landscape width is `841.89` pt, height is `595.28` pt).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `AppController.write_text(text, opts, out_path)` MUST construct a `Document` IR (using `TxtImporter` or `Document([Paragraph(...)])`) and render via `DocumentLayoutEngine`.
- **FR-002**: Direct text entry from GUI `WriteTab.do_write()` when `current_doc is None` MUST route through `ctl.write_text(text, opts, out)` (or `ctl.write_document(TxtImporter().import_text(text).document, opts, out)`), ensuring all paper format and background options are applied.
- **FR-003**: `WriteOptions.validate()` MUST resolve the effective paper dimensions (accounting for orientation) and verify that `margin_left + margin_right < effective_width`, raising `ValueError` otherwise.
- **FR-004**: `WriteOptions.validate()` MUST verify that `margin_top + margin_bottom < effective_height`, raising `ValueError` otherwise.
- **FR-005**: `composer.compose_document()` MUST be marked as deprecated and retained only if needed for low-level backward compatibility verification.
- **FR-006**: `tests/test_gui_document.py` MUST assert `write_tab.current_doc is None` before executing `do_write()` and verify the resulting `.xopp` XML contains expected paper dimensions and background tags.
- **FR-007**: Unit tests in `tests/test_page_format.py` MUST test margin validation boundary conditions (equal, greater, valid).
- **FR-008**: Full test suite MUST maintain 100% pass rate with zero linting errors.

---

### Key Entities

- **WriteOptions**: Contains user options for text scaling, line height, paper template, orientation, margins, and background styling.
- **PageFormat**: Pure geometric representation of a page (width, height, content bounds, and native background configuration).
- **Document (IR)**: Intermediate Representation tree representing document blocks (Paragraphs, Headings, Tables, Math, Lists).
- **DocumentLayoutEngine**: The unified layout engine coordinating pagination, line wrapping, math formulas, tables, and streaming output to `PageBuffer`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of text rendering entry points (GUI direct typing, GUI direct pasting, CLI `-t`, CLI `-f`, CLI positional file, CLI stdin, API `write_text`, API `write_document`) pass through `DocumentLayoutEngine`.
- **SC-002**: Zero occurrences of legacy `MAXH=3000` or fallback dimensions in any modern text export workflow.
- **SC-003**: Margin configuration errors are caught immediately at `validate()` time before layout processing begins.
- **SC-004**: Automated test suite maintains 100% pass rate across all test targets.

---

## Assumptions

- Direct text entered in GUI is plain text and should be parsed into Document IR paragraphs preserving line breaks.
- Default margins (`left=36, right=36, top=40, bottom=40` pt) easily fit standard paper formats (A5, A4, A3, Letter, Legal, 16:9, 4:3) and only custom dimensions or extreme manual margin inputs trigger margin validation errors.
- `test_golden_master.py` was established to verify that the original monolithic `hw_note.py` math and handwriting placement algorithms did not regress during MVC extraction; keeping `composer.write_document` for legacy golden master verification preserves this guarantee without conflicting with the unified `DocumentLayoutEngine` pipeline.
