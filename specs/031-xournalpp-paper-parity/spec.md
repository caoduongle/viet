# Feature Specification: Xournal++ Paper Background and Geometry Parity

**Feature Branch**: `031-xournalpp-paper-parity`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Làm cho file .xopp và các loại giấy của repo caoduongle/viet giống Xournal++. Mục 1: Sửa nền PDF (lỗi thật - pageno 1-based, domain absolute, filename trần, loại bỏ relative). Mục 2: Viết lại bản xem trước giấy trong webapp/js/paper.js (dùng chung renderPageSvgString/Element, config thẻ background r1, m1, lw, f1, f2, af1, af2, rm, bli, blw, ruled, lined m1 âm, graph, dotted, isograph, isodotted, staves, màu sáng/tối). Mục 3: Căn dòng viết tay vào dòng kẻ giấy (WriteOptions.snap_to_ruling, pitch theo r1, baseline snapping y=80+k*pitch, ngắt trang pageHeight-60, lề lined m1, plain giữ nguyên 100% golden master). Mục 4: Đồng bộ PageBackground ở chuviettay/model/xopp.py và hỗ trợ cấu hình đầy đủ (to_xml config, sửa m1 âm, BACKGROUND_PRESETS, CLI flags). Mục 5: Đồng bộ danh mục khổ giấy và loại giấy trên web và Tkinter (get_page_catalog, dropdowns, màu giấy và tương phản nét)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PDF Background Page Indexing and Specification Parity (Priority: P1)

Users opening exported `.xopp` documents containing PDF backgrounds in Xournal++ need the PDF pages and document references to open seamlessly without page indexing mismatch errors or invalid domain parse rejections.

**Why this priority**: In Xournal++, `domain="relative"` is completely unrecognized and causes parser errors or failure to attach the PDF background. Furthermore, Xournal++ defines `pageno` as 1-based (`page_index + 1`). Generating 0-based `pageno` or invalid `domain` directly corrupts user documents upon loading in Xournal++.

**Independent Test**: Generate a `.xopp` file referencing a multi-page PDF background (including page 0 / first page). Verify the generated XML contains `domain="absolute"`, `pageno="1"` for the initial page, and that no instances of `domain="relative"` exist anywhere in codebase or output.

**Acceptance Scenarios**:

1. **Given** a document with a PDF background at page index `0`, **When** the `.xopp` background XML is generated, **Then** `pageno` is written as `"1"` (1-based) and `domain` is written as `"absolute"`.
2. **Given** any PDF background export across single-page or multi-page documents, **When** serialized to `.xopp`, **Then** the PDF filename is emitted as a bare relative filename (which Xournal++ resolves relative to the `.xopp` file location) or explicit path with `domain="absolute"`, and `domain="relative"` is never produced.
3. **Given** an automated verification of codebase and test suites, **When** searching for `domain="relative"`, **Then** exactly zero occurrences are found across all packages and test cases.

---

### User Story 2 - Paper Background Geometry and High-Fidelity Web SVG Rendering (Priority: P1)

Users designing and reviewing handwritten notes in the web application need the on-screen paper preview to visually and geometrically match official Xournal++ paper styles across all ruling varieties (Ruled, Lined, Graph, Dotted, Isometric Graph, Isometric Dotted, and Music Staves).

**Why this priority**: Visual discrepancy between web preview and exported `.xopp` files frustrates users, leads to misaligned layout expectations, and diminishes handwriting realism. Consolidating SVG rendering into a unified pipeline eliminates code duplication between SVG string generation and DOM element rendering.

**Independent Test**: Load web preview with various paper types and background configs (`r1`, `m1`, `lw`, `bli`, `blw`, `rm`, `f1`, `f2`). Verify rendered SVG elements (lines, circles, paths) match exact coordinate bounds, line counts, spacing, and styling of Xournal++ views.

**Acceptance Scenarios**:

1. **Given** a Ruled or Lined paper selection with row spacing `r1` (default `24.0pt`), **When** rendered in the web preview, **Then** horizontal lines are generated strictly within the vertical range `[80.0, pageHeight - 60.0]` at coordinates `y = 80.0 + i * r1`.
2. **Given** a Lined paper selection with margin parameter `m1` (default `72.0pt`), **When** rendered, **Then** a vertical margin line is drawn from `y = 0` to `pageHeight` at `x = m1`; if `m1 < 0`, the margin line is drawn at `x = pageWidth + m1`.
3. **Given** a Graph paper selection, **When** rendered, **Then** grid lines are drawn with spacing `r1` (default `14.17pt` / 5mm); if `m1 > 0`, side margins of `m1` are preserved; if `rm=1`, margins are rounded to grid increments; if `bli > 0`, every `bli`-th line is styled with bold width `blw` (default `1.5pt`), while other lines use width `lw` (default `0.5pt`).
4. **Given** a Dotted paper selection, **When** rendered, **Then** dots are drawn at grid intersections at step `r1` with diameter / stroke width `1.5pt` and round line caps.
5. **Given** an Isometric Graph or Isometric Dotted paper selection, **When** rendered, **Then** grid points and lines adhere to isometric geometry (`xstep = sqrt(3)/2 * r1`, `ystep = r1 / 2`, margin = `r1`) centered on the page canvas.
6. **Given** a Music Staves paper selection, **When** rendered, **Then** 5-line musical staves are drawn with 5pt interline spacing, 40pt inter-staff separation, 50pt left and right margins, starting at `y = 80.0` and ending before `pageHeight - 60.0`, with staff step matching Xournal++ geometry (`STAVES_SPACING + staffHeight + 4 * lw`).
7. **Given** dark paper backgrounds (e.g. `#1e1e1e`), **When** paper lines are rendered without explicit custom colors, **Then** default contrast line colors automatically switch to Xournal++ dark theme defaults (`#434343` for rulings/grids, `#220080` for lined margin, `#ffffff` for staves).

---

### User Story 3 - Adaptive Baseline Snapping to Ruling Lines (Priority: P1)

Users composing handwritten text on Ruled and Lined paper need the synthesized handwriting baselines to naturally align ("snap") to the visible ruling lines, so that text rests neatly upon the lines without floating or crossing through them awkwardly.

**Why this priority**: One of the primary aesthetic values of ruled paper is handwriting resting on the lines. Unaligned text looks disorderly and unnatural. Crucially, this snapping must not disturb plain paper layout, preserving existing regression baselines and golden master test invariance.

**Independent Test**: Generate handwritten documents with `snap_to_ruling = True` on Ruled paper with varying font sizes and line heights. Verify that first baselines snap to the first ruling `y = 80 + k * r1 >= natural_y`, successive lines step by multiples of `r1`, and text on Plain paper remains 100% byte/hash-identical to the golden master.

**Acceptance Scenarios**:

1. **Given** `WriteOptions(snap_to_ruling=True)` and a `ruled` or `lined` background with ruling step `r1`, **When** laying out lines of text, **Then** the vertical step (`pitch`) between lines equals `r1 * max(1, round(line_height / r1))`.
2. **Given** text lines laid out with ruling snapping, **When** placing the first line, **Then** its baseline rests precisely at the first available ruling `y = 80.0 + k * r1` below the requested top margin.
3. **Given** subsequent text lines on ruled paper, **When** checking page capacity, **Then** a page break occurs whenever the next line baseline would exceed `pageHeight - 60.0`.
4. **Given** a `lined` background with vertical margin `m1 > 0`, **When** text is positioned, **Then** the content left margin starts to the right of the margin line (`x > m1`), unless intentionally overridden. If `m1 < 0`, right margin bounds text at `x <= pageWidth + m1`.
5. **Given** a `plain`, `graph`, `dotted`, or `staves` background, or `snap_to_ruling=False`, **When** text layout is performed, **Then** layout engine uses natural continuous coordinates without snapping, and the Plain background golden-master test (`test_golden_master.py`) produces the exact unchanged hash.

---

### User Story 4 - Declarative PageBackground XML Configuration & Presets (Priority: P2)

Users configuring paper styles via Python API or command-line interface need full support for all Xournal++ background configuration parameters and template presets (e.g., Narrow Lined, College Lined, 5mm Graph).

**Why this priority**: Enables precise document customization and 1:1 interchange with Xournal++ templates without manual attribute hacking or XML editing.

**Independent Test**: Construct `PageBackground` instances with customized `r1`, `m1` (including negative values), `lw`, `f1`, `f2`, `rm`, `bli`, `blw`. Verify serialized XML matches Xournal++ `config="key=val;..."` format, and verify negative `m1` passes validation without schema errors.

**Acceptance Scenarios**:

1. **Given** a `PageBackground` configured with non-default geometry or styling attributes, **When** `to_xml()` is called, **Then** attributes are serialized into the `config` attribute formatted as key-value pairs separated by semicolons (e.g. `config="r1=18.0;m1=72.0"`).
2. **Given** a negative margin value `m1 = -72.0` (representing a 1-inch right margin), **When** processed by `WriteOptions.validate()`, CLI arguments, or `PageBackground.to_xml()`, **Then** it is recognized as a valid right-hand margin rather than raising an invalid dimension error.
3. **Given** the standard preset catalog `BACKGROUND_PRESETS`, **When** a user specifies `--bg-preset lined_college` or `--bg-preset graph_5mm`, **Then** the system automatically applies the correct background type, `r1`, `m1`, and grid parameters matching `pagetemplates.ini.in`.
4. **Given** CLI flags `--bg-r1`, `--bg-m1`, and `--bg-color`, **When** supplied alongside or without a preset, **Then** the explicit flags properly override default preset parameters.

---

### User Story 5 - Unified Page Catalog and Cross-Platform UI Synchronization (Priority: P2)

Users interacting with the web application and desktop GUI need a consistent, unified selection of standard paper dimensions (A3, A4, A5, Letter, Legal, 16:9, 4:3, Custom) and paper styling presets, sourced from a single source of truth.

**Why this priority**: Eliminating divergent, hardcoded paper dimension lists across Python core, Web frontend, and Tkinter UI prevents subtle rendering differences and simplifies maintenance.

**Independent Test**: Query `get_page_catalog()` and verify that web dropdowns and Tkinter dropdown menus populate all supported page formats, presets, and paper tones (White, Ivory, Pastel Blue, Dark).

**Acceptance Scenarios**:

1. **Given** `get_page_catalog()`, **When** invoked, **Then** it returns structured definitions of all standard paper formats with precise point dimensions, paper style presets, and recommended background colors.
2. **Given** the web application interface, **When** opening paper format or background type selectors, **Then** the options match the unified catalog and allow live preview switching.
3. **Given** a user changing the paper background color (e.g., Ivory `#ffffc8` or Dark `#1e1e1e`), **When** rendered, **Then** line stroke colors automatically adapt for optimal contrast in accordance with Xournal++ visual standards.

---

### Edge Cases

- **Negative `m1` margin**: `m1 < 0` denotes a right margin (`x = pageWidth + m1`). Validation routines must accept `-pageWidth < m1 < 0` while rejecting values that place the margin outside the page canvas.
- **`m1 = 0` vs `m1 > 0`**: In Graph paper, `m1 = 0` means no margin (grid spans edge to edge), whereas `m1 > 0` leaves margins on all four sides. In Lined paper, `m1 = 0` places the line at `x = 0`.
- **Tiny page heights**: If page height is less than `HEADER (80) + FOOTER (60) = 140pt`, no horizontal lines should be drawn and pagination must avoid division by zero or negative bounding loops.
- **Fractional `r1` grid steps**: Standard metric grids use `r1 = 14.1732pt` (5mm). Floating-point loops must use proper boundary tolerance (`floor`/`ceil` with epsilon) to prevent missing or extraneous border lines.
- **Oversized handwriting lines exceeding `r1`**: If a handwritten line has a height of `35pt` on paper with `r1 = 24pt`, pitch snapping must advance by `r1 * round(35 / 24) = 48pt` (2 grid steps) so the next baseline remains strictly aligned to a ruling line.
- **Multi-line math or table cells on ruled paper**: Snapping applies to normal text lines; table interior cells retain cell padding and baseline metrics without forcing external ruling misalignment.
- **Golden master invariance**: Plain background rendering must never invoke snapping logic or alter stroke coordinate generation, guaranteeing bit-exact output hashes for `test_golden_master.py`.
- **Dark mode theme contrast**: When background color luminance is below 0.5 (or `#1e1e1e`), default ruling strokes switch from light dodger blue `#40a0ff` to dark slate gray `#434343`, and lined margins switch from deep pink `#ff0080` to midnight blue `#220080`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `.xopp` generator (`chuviettay/model/xopp.py`) and fidelity engine (`chuviettay/fidelity/engine.py`) MUST format PDF background `pageno` attributes as 1-based integers (`page_index + 1`).
- **FR-002**: All PDF background elements in `.xopp` output MUST specify `domain="absolute"` and relative PDF filenames without path qualifiers, eliminating all occurrences of `domain="relative"`.
- **FR-003**: The web application (`webapp/js/paper.js`) MUST unify SVG paper background generation so that `renderPageSvgString` and `renderPageSvgElement` share a single background rendering implementation.
- **FR-004**: The paper background renderer MUST parse and apply all Xournal++ configuration attributes: `r1` (grid/line pitch), `m1` (margin offset), `lw` (line width), `f1` (primary stroke color), `f2` (secondary stroke color), `af1`, `af2`, `rm` (rounded margin flag), `bli` (bold line interval), and `blw` (bold line width).
- **FR-005**: Ruled and Lined paper backgrounds MUST generate horizontal lines only within `[80.0, pageHeight - 60.0]` at `y = 80.0 + i * r1`.
- **FR-006**: Lined paper backgrounds MUST draw a vertical margin line from `y = 0` to `y = pageHeight` at `x = m1` (or `x = pageWidth + m1` when `m1 < 0`).
- **FR-007**: Graph paper backgrounds MUST draw orthogonal grid lines at interval `r1`, respecting margin `m1` when positive, rounding margins when `rm=1`, and applying bold width `blw` every `bli` intervals.
- **FR-008**: Dotted paper backgrounds MUST draw circular dots at grid intersections at interval `r1` with diameter `1.5pt` and round caps.
- **FR-009**: Isometric Graph and Isometric Dotted backgrounds MUST calculate coordinate offsets using `xstep = sqrt(3)/2 * r1` and `ystep = r1 / 2`, with margins centered on the canvas.
- **FR-010**: Music Staves backgrounds MUST generate 5-line musical staves with 5pt line spacing, 40pt inter-staff gap, 50pt side margins, starting at `y = 80.0` and terminating before `pageHeight - 60.0`.
- **FR-011**: The layout engine (`chuviettay/layout/engine.py`) MUST support an optional `snap_to_ruling` flag in `WriteOptions` (default `True`), snapping text baselines to `y = 80.0 + k * pitch` on `ruled` and `lined` paper where `pitch = r1 * max(1, round(line_h / r1))`.
- **FR-012**: The layout engine MUST trigger a page break when the next snapped baseline exceeds `pageHeight - 60.0`.
- **FR-013**: The layout engine MUST restrict text left content bounds to `x > m1` for `lined` paper when `m1 > 0`, and clamp right bounds to `x <= pageWidth + m1` when `m1 < 0`.
- **FR-014**: Plain paper rendering and golden master test baselines MUST NOT undergo baseline snapping, preserving bit-exact hash equivalence in `tests/test_golden_master.py`.
- **FR-015**: The `PageBackground` model class MUST support all Xournal++ configuration keys and serialize them to XML as `config="k1=v1;k2=v2;..."`.
- **FR-016**: The layout configuration module MUST define standard `BACKGROUND_PRESETS` corresponding to `pagetemplates.ini.in` (`plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `staves`, `lined_narrow`, `lined_college`, `lined_wide`, `graph_5mm`, `graph_grid`).
- **FR-017**: The CLI interface MUST provide `--bg-preset`, `--bg-r1`, `--bg-m1`, and `--bg-color` options with support for negative `m1` values.
- **FR-018**: The system MUST provide a unified `get_page_catalog()` function consumed by Python CLI, Web frontend, and Tkinter UI for all supported page formats, presets, and color palettes.

### Key Entities

- **PageBackground**: Encapsulates paper background type (`plain`, `ruled`, `lined`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `staves`, `pdf`), background color, PDF references, and geometry attributes (`r1`, `m1`, `lw`, `f1`, `f2`, `rm`, `bli`, `blw`).
- **Background Preset**: Named predefined configuration specifying paper type, ruling intervals, margin offsets, and line styling (e.g. `lined_college`, `graph_5mm`).
- **Page Geometry Catalog**: Canonical catalog defining supported physical paper dimensions (A4, Letter, etc.) and paper background templates for cross-platform synchronization.
- **Ruling Pitch**: Computed vertical step between snapped baselines on ruled/lined paper, constrained to integer multiples of the ruling spacing `r1`.
- **Boundary Bounds (getIndexBounds)**: Calculation determining the exact integer indices of visible ruling lines and staves within margins and page bounds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated `.xopp` documents with PDF backgrounds load in Xournal++ with correct 1-based page alignment, and zero occurrences of `domain="relative"` remain in the codebase.
- **SC-002**: 100% geometrical parity between web SVG background preview and Xournal++ background rendering rules for all supported paper types (Ruled, Lined, Graph, Dotted, Isometric, Staves).
- **SC-003**: 100% of text baselines on Ruled and Lined paper align strictly to horizontal rulings (`y = 80 + k * pitch`) when `snap_to_ruling` is enabled.
- **SC-004**: 100% hash preservation for Plain background Golden Master tests (`test_golden_master.py`), with zero coordinate deviation.
- **SC-005**: All background configuration parameters (`r1`, `m1`, `lw`, `f1`, `f2`, `rm`, `bli`, `blw`, including negative `m1`) serialize to and deserialize from valid Xournal++ XML attributes without loss.
- **SC-006**: Web application and Tkinter UI paper format/preset selectors reflect 100% of options provided by `get_page_catalog()`.
- **SC-007**: 100% of existing unit, integration, architecture, and E2E test suites pass with zero regressions.

## Assumptions

- Xournal++ resolves bare relative filenames for PDF backgrounds relative to the parent directory containing the `.xopp` file itself.
- Standard 5mm metric graph paper corresponds to `14.1732pt` (72 pt / inch * 5mm / 25.4 mm).
- Text snapping to ruling lines is intended for body handwriting; formulas and tabular layouts inside cells maintain internal spacing while fitting within the line bounds.
- Snapping is only active when explicitly requested or enabled by default on `ruled` and `lined` paper; other paper types use natural continuous line layout.
- The web application has access to the page catalog data via Pyodide bridge or serialized JSON catalog representation.
