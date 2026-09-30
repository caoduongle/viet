# Feature Specification: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Feature Branch**: `013-docx-fidelity-replacement`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Pipeline hiện tại chưa thể làm đúng yêu cầu 'chỉ đổi text thành chữ viết tay, giữ nguyên toàn bộ bố cục + hình ảnh + vị trí hình ảnh'. Tệp problem_set_03_dap_an_ghi_chu.docx có 19 trang, 19 ảnh PNG nhúng (inline), 8 bảng, drawing/image... Hiện tại DocxImporter bỏ qua drawing và reflow toàn bộ text, làm mất 19 ảnh và làm xáo trộn bố cục. Cần tách rõ 2 chế độ: Semantic mode (Document IR reflow bình thường) và Fidelity mode (Fixed page layout giữ nguyên vị trí, render/convert ra fixed layout, giữ nguyên ảnh, biểu đồ, bảng ở background, chỉ thay text bằng handwriting strokes vào đúng bounding box, xuất ra XOPP kèm background)."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exact Layout & Geometry Preservation with In-Place Text Replacement (Priority: P1) 🎯 MVP

As a user with a structured document (such as a 19-page Problem Set exam or lecture notes containing equations, diagrams, and tables), I want to replace only the typed text with handwritten strokes while locking the document geometry, so that every paragraph, line, and word appears in its original spatial position without reflowing or shifting the total page count.

**Why this priority**: Users need completed handwritten assignments and annotated forms where the structure, spacing, and pagination are strictly bound by the source document. Reflowing text alters page counts, moves questions away from answer spaces, and violates formatting requirements.

**Independent Test**: Provide a multi-page document with known dimensions and line positions. Execute Fidelity Replacement. Verify that the output has the exact same page count (e.g. 19 pages) and that handwritten strokes are placed within the geometric bounding box of each corresponding text element without wrapping into unintended lines.

**Acceptance Scenarios**:

1. **Given** a 19-page document, **When** processed in Fidelity Mode, **Then** the output document contains exactly 19 pages with identical dimensions for each page.
2. **Given** a specific text block at page 2 with bounding box coordinates `(x, y, width, height)`, **When** rendered, **Then** the corresponding handwritten strokes are positioned within that exact coordinate region.
3. **Given** text lines within table cells or callout boxes, **When** replaced with handwriting, **Then** strokes do not overflow the cell boundaries or alter table dimensions.

---

### User Story 2 - Complete Non-Text Graphic Element Preservation (Priority: P1) 🎯 MVP

As a user whose document includes figures, charts, photos, and graphical borders, I want all 19 embedded images and visual elements to remain in their original positions and visual quality, so that diagrams and formulas are clearly visible directly beneath or beside the handwritten text.

**Why this priority**: Documents like problem sets and technical reports rely heavily on illustrations (e.g. Figure 1, Figure 2, histograms, coordinate graphs). Dropping or relocating images renders the annotated document useless.

**Independent Test**: Process a document containing 19 inline PNG images and 8 tables. Verify that all 19 images and 8 table layouts are preserved in the output at their exact visual positions, and that captions remain properly aligned with their respective images.

**Acceptance Scenarios**:

1. **Given** a document with 19 embedded inline images, **When** processed in Fidelity Mode, **Then** 100% of the images are preserved in the output at their exact document coordinates.
2. **Given** Figure 18 positioned between a data table and questions 5–7, **When** processed, **Then** the spatial sequence (Table $\to$ Figure 18 $\to$ Questions 5–7) is preserved without reordering.
3. **Given** non-text graphical elements (table borders, shading, charts), **When** output is generated, **Then** they appear intact in the background layer without pixelation or visual corruption.

---

### User Story 3 - Distinct Mode Selection: Semantic Reflow vs. Fidelity In-Place (Priority: P2)

As a user or automated system, I want to choose between Semantic Mode (free-flowing text across chosen paper sizes and lined grids) and Fidelity Mode (fixed-page layout preserving source geometry and images), so that I can use the tool both for informal drafting on digital notepad paper and for strict exam/worksheet completion.

**Why this priority**: Both modes serve distinct use cases. Semantic mode allows re-paginating DOCX onto A3/A4/Ô Li graph paper, whereas Fidelity mode guarantees 1:1 visual fidelity to the original file. Both must coexist cleanly without conflicting configurations.

**Independent Test**: Execute the command-line interface and GUI with `--mode semantic` and `--mode fidelity`. Confirm that `--mode semantic` uses `DocumentLayoutEngine` with user-selected paper grids, while `--mode fidelity` activates the fixed-layout engine and preserves original document pages and images.

**Acceptance Scenarios**:

1. **Given** a user selecting Fidelity Mode in the GUI or CLI, **When** processing starts, **Then** the system engages the fixed-layout replacement pipeline.
2. **Given** a user selecting Semantic Mode, **When** processing starts, **Then** the system engages the existing `DocumentLayoutEngine` reflow pipeline.
3. **Given** an invalid or unsupported option combination in Fidelity Mode (such as attempting to change the paper grid on a fixed-layout document), **When** validated, **Then** the system provides clear user guidance.

---

### User Story 4 - Multi-Page Annotation Viewer Compatibility (Priority: P3)

As a student or instructor opening the generated `.xopp` file in Xournal++, I want the document to load seamlessly with its background pages and overlay handwriting layers, so that I can inspect, further annotate, or export the document to PDF.

**Why this priority**: Xournal++ is the primary downstream consumer for `.xopp` files. Background attachments must comply with standard multi-page background references so users do not encounter blank pages or missing assets.

**Independent Test**: Open the generated output file in Xournal++ (or parse the XML package against Xournal++ format specifications). Confirm that each page references its corresponding background page number (`<background type="pdf" pageno="N"/>` or embedded raster/vector equivalent) and that handwritten stroke layers overlay accurately.

**Acceptance Scenarios**:

1. **Given** a multi-page output package, **When** inspected, **Then** each page in `.xopp` contains a valid `<background>` definition matching the page index.
2. **Given** the generated output file, **When** opened in Xournal++, **Then** all handwritten strokes appear crisp in the foreground layer on top of the original non-text visual content.

---

### Edge Cases

- **Variable Font Sizes & Line Heights**: When the source document uses compact text (e.g. 8pt or 9pt) or condensed table columns, the handwriting generator must scale stroke size proportionally to fit within the text bounding box without overlapping adjacent rows.
- **Inline Images vs. Anchor Shapes**: Documents may mix inline pictures and floating text wraps. The system must account for image dimensions so handwritten text never overwrites inline graphic content.
- **Empty or Whitespace-Only Paragraphs**: Spacer lines must be preserved geometrically without generating extraneous strokes or missing-character warnings.
- **Multi-Column Sections**: Multi-column text layouts must preserve column boundaries and vertical text flow without merging text across columns.
- **Non-Text Background Packaging**: When the background is stored as an associated document (e.g. companion PDF), the system must maintain relative path references and prevent dangling file pointers if files are moved.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated Fidelity Replacement Mode distinct from the existing Semantic Reflow Mode.
- **FR-002**: System MUST accept DOCX documents and extract fixed-page layout structures containing geometric bounding boxes for all text blocks, lines, and non-text elements.
- **FR-003**: System MUST preserve 100% of embedded images (PNG, JPEG, etc.) and graphic figures at their exact spatial locations on their corresponding pages.
- **FR-004**: System MUST preserve the exact page count and dimensions of the source document in Fidelity Mode (e.g. 19 pages remain 19 pages).
- **FR-005**: System MUST fit handwritten strokes into the extracted bounding box of each text element, adjusting stroke scale to prevent boundary overflow.
- **FR-006**: System MUST retain tables, cell borders, shading, and diagrammatic line art in the visual background layer.
- **FR-007**: System MUST generate output compatible with Xournal++ (`.xopp`), linking each page to its corresponding background page index.
- **FR-008**: System MUST allow users to select between Fidelity Mode and Semantic Mode via both the CLI (e.g. `--mode fidelity | --mode semantic`) and GUI options.
- **FR-009**: System MUST report accurate statistics for Fidelity Mode processing, including total pages processed, text blocks replaced, and images preserved.
- **FR-010**: System MUST validate input documents and gracefully alert the user if a document cannot be rendered into fixed layout.

---

### Key Entities

- **FixedDocument**: Represents a document with immutable page geometry and z-ordered visual elements.
- **FixedPage**: Represents an individual page with fixed width, height, background reference, and a collection of spatial elements.
- **TextBox**: A spatial element containing text content, bounding box `(x, y, width, height)`, font size, and text alignment.
- **ImageBox**: A spatial element containing embedded image data, format, and bounding box `(x, y, width, height)`.
- **BackgroundLayer**: The non-text visual representation (vector PDF or raster asset) of a page containing images, table outlines, and graphical decorations.
- **FidelityResult**: Outcome of a fidelity replacement job, detailing output paths, page count, stroke count, missing tokens, and preserved image count.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pages in the source document are preserved in the output (e.g. a 19-page input produces a 19-page output).
- **SC-002**: 100% of embedded images (e.g. all 19 images in Problem Set 03) appear in the output at their exact document positions.
- **SC-003**: 0% displacement or reordering of non-text elements (tables, charts, and figure captions maintain identical relative ordering).
- **SC-004**: Handwritten text strokes stay within 98% of the designated text bounding boxes without vertical clipping or horizontal collision with adjacent content.
- **SC-005**: Generated multi-page output files open successfully in Xournal++ with synchronized background alignment on all pages.

---

## Assumptions

- Users requiring Fidelity Mode intend to preserve the visual appearance of their original document, replacing printed type with personal handwriting style.
- When generating background layers for Fidelity Mode, the system will utilize a fixed-page rendering pipeline (such as vector PDF or high-resolution page assets) to maintain crisp image quality rather than downscaling to low-resolution bitmaps.
- For Semantic Mode, the existing `DocumentLayoutEngine` and `DocxImporter` continue to serve free-flow text reflow across customized paper sizes (A4, A3, Letter) and backgrounds (Ô Li, Ruled, Plain).
- In Fidelity Mode, background paper options (such as custom Ô Li grid lines) are disabled or deferred to the source document's native background, because the source document already defines its own page background and graphics.
