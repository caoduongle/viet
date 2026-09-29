# Feature Specification: Paper Sizes, Page Templates & Native XOPP Backgrounds

**Feature Branch**: `011-paper-size-and-background`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User request: "Chọn loại giấy gồm 2 lựa chọn độc lập: Khổ giấy (A5, A4, A3, Letter, Legal, 16:9, 4:3, Tùy chỉnh) + Chiều giấy (Dọc, Ngang), và Kiểu giấy/nền (Trắng, Dòng kẻ, Dòng kẻ + lề, Ô li, Chấm, Isometric, Khuông nhạc) ghi trực tiếp vào thẻ XML background của .xopp (ví dụ config='r1=14.17' cho ô li 5mm). Tách biệt kích thước trang và lề trang (margins) khỏi bề rộng chữ viết tay. Hỗ trợ đầy đủ trên cả DocumentLayoutEngine, PageBuffer, CLI và GUI."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Native Paper Sizes, Orientations & Content Margins (Priority: P1) 🎯 MVP

As a student, teacher, or professional writing notes, I want to choose standard paper sizes (such as A4, A3, A5, US Letter, US Legal, 16:9, 4:3, or custom dimensions) and page orientations (Portrait or Landscape), so that my generated Xournal++ document matches the physical or digital paper dimensions I need.

**Why this priority**: Currently, `DocumentLayoutEngine` uses an arbitrary `MAXH = 3000.0 pt` and sets page width directly from handwriting text width (`x0 + width + 20`). Without genuine paper sizes, documents do not paginate realistically for A4 or Letter, and cannot be printed or viewed in standard notebook aspect ratios.

**Independent Test**: Configure `paper="a4", orientation="portrait"`, render a document, and verify that all generated pages in `.xopp` have exact dimensions `width="595.28" height="841.89"`, text starts at `x0 = margin_left`, and page breaks occur cleanly before reaching `height - margin_bottom`.

**Acceptance Scenarios**:
1. **Given** `paper="a4", orientation="portrait"`, **When** document is rendered, **Then** XML `<page>` tags have `width="595.28"` and `height="841.89"`.
2. **Given** `paper="a4", orientation="landscape"`, **When** document is rendered, **Then** XML `<page>` tags have `width="841.89"` and `height="595.28"`.
3. **Given** `paper="a3", orientation="portrait"`, **When** document is rendered, **Then** XML `<page>` tags have `width="841.89"` and `height="1190.55"`.
4. **Given** `paper="custom", paper_width=500.0, paper_height=700.0`, **When** document is rendered, **Then** XML `<page>` tags have `width="500.0"` and `height="700.0"`.
5. **Given** standard content margins (`left=36pt, right=36pt, top=40pt, bottom=40pt`), **When** content wraps, **Then** usable text width is strictly bounded by `page_width - margin_left - margin_right`.

---

### User Story 2 - Native XOPP Background Styles & Grid Configuration (Priority: P1) 🎯 MVP

As a user taking notes, I want the background of my note pages to feature standard patterns (Plain white, Lined/Ruled, Ruled with vertical margin line, Graph/Grid ô li, Dotted, Isometric graph, or Music staves) with adjustable spacing (e.g. 5mm ô li), rendered natively by Xournal++ rather than drawn as heavy vector pen strokes.

**Why this priority**: Native XOPP background tags allow Xournal++ to render high-performance, crisp backgrounds while keeping the `.xopp` file tiny and keeping handwriting strokes distinct from background lines.

**Independent Test**: Configure `background="graph", background_spacing=14.17` (5mm), render a document, and assert that each `<page>` contains `<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>` with zero artificial vector strokes drawn for the background grid.

**Acceptance Scenarios**:
1. **Given** `background="plain"`, **When** page is generated, **Then** XML contains `<background type="solid" color="#ffffffff" style="plain"/>`.
2. **Given** `background="graph", background_spacing=14.17`, **When** page is generated, **Then** XML contains `<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>`.
3. **Given** `background="ruled", background_spacing=24.0`, **When** page is generated, **Then** XML contains `<background type="solid" color="#ffffffff" style="ruled" config="r1=24.0"/>` (or `lined`).
4. **Given** `background="ruled_margin", background_spacing=24.0`, **When** page is generated, **Then** XML contains `<background type="solid" color="#ffffffff" style="ruled" config="r1=24.0"/>` with vertical margin line attribute.
5. **Given** `background="dotted"` or `background="iso_graph"` or `background="music"`, **When** page is generated, **Then** XML contains the respective style and spacing configuration.

---

### User Story 3 - CLI Selection of Paper Sizes & Backgrounds (Priority: P2)

As a command-line user or script author, I want to pass flags like `--paper a4 --background graph --background-spacing 5mm` to `hw_note.py write`, so that I can batch-convert documents into formatted notebooks from terminal or automated scripts.

**Why this priority**: Provides full headless automation and parity between CLI and GUI workflows.

**Independent Test**: Run `python hw_note.py write sample.md -o output.xopp --paper a4 --background graph` and verify the output `.xopp` file.

**Acceptance Scenarios**:
1. **Given** CLI arguments `--paper a4 --orientation portrait --background graph`, **When** executed, **Then** output `.xopp` is created with A4 dimensions and graph background.
2. **Given** CLI argument `--background-spacing 5mm`, **When** parsed, **Then** `5mm` is accurately converted to points ($\approx 14.17\text{ pt}$).
3. **Given** CLI argument `--paper custom --paper-width 210mm --paper-height 297mm`, **When** parsed, **Then** dimensions are converted to A4 points.

---

### User Story 4 - GUI Interactive Paper & Background Controls (Priority: P2)

As an interactive GUI user in the "Viết chữ" tab, I want a dedicated "Trang & Nền giấy" control section with dropdowns for paper size, orientation, background style, spacing, and a custom paper dialog, so that I can visually configure my notebook before exporting.

**Why this priority**: Matches the user experience of desktop Xournal++ page setup in an intuitive, accessible layout.

**Independent Test**: Open GUI, select "Khổ giấy: A4", "Nền: Ô li", verify that the generated file contains A4 graph background.

**Acceptance Scenarios**:
1. **Given** GUI WriteTab, **When** viewed, **Then** a "Trang & Nền giấy" section displays dropdowns for Khổ giấy, Chiều giấy, Nền giấy, and Khoảng cách.
2. **Given** selection of "Tùy chỉnh...", **When** clicked, **Then** a modal dialog prompts for width and height in centimeters or millimeters.
3. **Given** selection of "Ô li", **When** selected, **Then** default spacing automatically updates to 5 mm (14.17 pt).

---

### User Story 5 - Backward Compatibility & System Integrity (Priority: P3)

Existing workflows, non-document text writes, calibration grid generators (`make_grid`, `check`, `seed`), and legacy scripts must continue to function without disruption.

**Why this priority**: Prevents regressions across the existing 339 automated tests and maintains golden-master integrity.

**Independent Test**: Run full test suite `pytest -v` and confirm 100% pass rate.

**Acceptance Scenarios**:
1. **Given** legacy calls without paper options, **When** executed, **Then** system defaults safely to A4 portrait plain without error.
2. **Given** `xopp.make_grid()`, **When** called for learning/check/seed, **Then** grid generation uses its specialized calibration layout unchanged.

---

### Edge Cases

- **Landscape vs Portrait Swap**: When orientation is `landscape`, width is always `max(w, h)` and height is `min(w, h)`.
- **Zero or Negative Dimensions**: Custom dimensions $\le 0$ must raise a validation error before layout.
- **Unit Parsing**: Supports `mm`, `cm`, `pt`, `in` units (e.g. `5mm` $\to 14.17$, `1in` $\to 72.0$). Plain numbers default to points (`pt`).
- **Very Small Paper (e.g. Custom 50x50pt)**: Content width must remain at least 20pt to prevent negative or infinite layout loops.
- **Table / Math Block Larger Than Page Height**: Document layout engine must gracefully handle elements taller than page height by placing them on a new page without crashing.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated module [`chuviettay/document/page_format.py`](chuviettay/document/page_format.py) defining:
  - `PaperSize`: dataclass with `name`, `width` (pt), `height` (pt).
  - `PageBackground`: dataclass with `style` (plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music), `spacing` (pt), `margin` (pt), `color` (hex string).
  - Predefined dictionary `PAPER_SIZES` supporting `a5`, `a4`, `a3`, `letter`, `legal`, `16:9`, `4:3`.
- **FR-002**: `WriteOptions` MUST include fields:
  - `paper: str = "a4"`
  - `orientation: str = "portrait"`
  - `paper_width: float | None = None`
  - `paper_height: float | None = None`
  - `margin_left: float = 36.0`
  - `margin_right: float = 36.0`
  - `margin_top: float = 40.0`
  - `margin_bottom: float = 40.0`
  - `background: str = "plain"`
  - `background_spacing: float | None = None`
  - `background_margin: float | None = None`
  - `background_color: str = "#ffffffff"`
- **FR-003**: `PageBuffer` MUST accept `page_w`, `page_h`, and `background: PageBackground | None` and write native XML:
  `<page width="{w}" height="{h}">\n<background type="solid" color="{c}" style="{s}" {config}/>\n<layer>`
- **FR-004**: `DocumentLayoutEngine` MUST calculate:
  - `page_w`, `page_h` from resolved paper size and orientation.
  - `usable_w = page_w - margin_left - margin_right`.
  - `max_page_y = page_h - margin_bottom`.
  - Text starting coordinate `x0 = margin_left`, `y0 = margin_top`.
- **FR-005**: CLI parser MUST support `--paper`, `--orientation`, `--paper-width`, `--paper-height`, `--background`, `--background-spacing`, `--background-color`.
- **FR-006**: Unit converter MUST parse string representations with units: `mm` ($1\text{mm} = 72/25.4\text{ pt} \approx 2.83465\text{ pt}$), `cm` ($28.3465\text{ pt}$), `in` ($72.0\text{ pt}$), and `pt`.
- **FR-007**: GUI WriteTab MUST provide interactive dropdowns and entry fields for paper size, orientation, background style, and spacing, plus a custom size dialog.

---

### Key Entities

- **`PaperSize`**: Immutable definition of standard physical page bounds in typography points.
- **`PageBackground`**: Specification for Xournal++ native background rendering layer (style, color, spacing config).
- **`PageFormat`**: Resolved configuration combining paper size, orientation, margins, and background.
- **`PageBuffer`**: Streaming XML writer outputting native `<page>` and `<background>` tags.
- **`DocumentLayoutEngine`**: Engine orchestrating block layout constrained within page dimensions and margins.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated pages in `.xopp` output reflect the exact requested paper dimensions (e.g. A4 = 595.28 x 841.89 pt).
- **SC-002**: Generated `.xopp` files contain valid native `<background .../>` XML tags that load and render in Xournal++ without creating extra vector strokes.
- **SC-003**: 0 crashes when changing paper sizes, orientations, or background styles across all document types (TXT, Markdown, DOCX).
- **SC-004**: 100% pass rate across the full automated test suite with zero regressions on existing tests.

---

## Assumptions

- Dimensions follow Desktop Publishing standards ($1 \text{ inch} = 72 \text{ pt}$, $1 \text{ mm} \approx 2.83465 \text{ pt}$).
- Xournal++ background styles `plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `music` are supported natively via the `<background>` XML element with attribute `config="r1=<spacing_pt>"`.
- Default margins are set to 0.5 inch (36 pt) horizontally and 40 pt vertically, leaving ample writing room while preventing text from clipping to the page edges.
