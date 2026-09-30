# Feature Specification: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Feature Branch**: `013-docx-fidelity-replacement`

**Created**: 2026-09-30

**Updated**: 2026-09-30 (P0/P1 Refinements: Zero Fixture Bleed, Comprehensive Shape Whiteout, Mixed-Inline Spatial Segmentation)

**Status**: Draft

**Input**: User feedback & specification refinement:
1. P0: Production path MUST NEVER fall back to test fixtures (`sample_fidelity_data.json` or `sample_background.pdf`). If neither Microsoft Word nor LibreOffice is available, the system must fail fast with a clear, actionable error instructing the user to install Microsoft Word or use Semantic Mode (`--mode semantic`).
2. P1: Whiteout transformation must comprehensively whiten text inside DrawingML textboxes, shapes, canvas objects, and nested table cells, eliminating printed text bleed-through.
3. P1: Paragraphs containing inline images (`text -> image -> text`) must be segmented into distinct spatial bounding boxes so handwritten strokes never overwrite embedded images.
4. Key Entity Clarification: `ImageBox` represents spatial geometry and exclusion bounds, while the visual image assets are preserved losslessly in the background layer.

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
4. **Given** a paragraph with an inline image positioned between two text segments (`text -> image -> text`), **When** rendered, **Then** strokes are placed in the text regions before and after the image without crossing into the image's bounding box.

---

### User Story 2 - Complete Non-Text Graphic Element Preservation & Clean Whiteout (Priority: P1) 🎯 MVP

As a user whose document includes figures, charts, photos, drawing shapes, and graphical borders, I want all embedded images and visual elements to remain in their original positions and visual quality, and all printed text (including text inside shapes and nested tables) to be completely whited out in the background, so that diagrams and formulas are clearly visible directly beneath or beside the handwritten text without ghosting or printed text bleed-through.

**Why this priority**: Documents like problem sets and technical reports rely heavily on illustrations (e.g. Figure 1, Figure 2, histograms, coordinate graphs). Dropping or relocating images renders the annotated document useless. Printed text bleed-through creates visual clutter and illegibility.

**Independent Test**: Process a document containing 19 inline PNG images, 8 tables, and drawing shapes. Verify that all 19 images and 8 table layouts are preserved in the output at their exact visual positions, and that all printed text is 100% neutralized in the background layer.

**Acceptance Scenarios**:

1. **Given** a document with 19 embedded inline images, **When** processed in Fidelity Mode, **Then** 100% of the images are preserved in the output at their exact document coordinates.
2. **Given** Figure 18 positioned between a data table and questions 5–7, **When** processed, **Then** the spatial sequence (Table $\to$ Figure 18 $\to$ Questions 5–7) is preserved without reordering.
3. **Given** non-text graphical elements (table borders, shading, charts, shapes), **When** output is generated, **Then** they appear intact in the background layer without pixelation or visual corruption.
4. **Given** text inside DrawingML textboxes, shapes, or nested table cells, **When** processed by Whiteout transform, **Then** all printed characters are converted to white (`#FFFFFF`) while maintaining original geometry.

---

### User Story 3 - Distinct Mode Selection & Strict Production Dependency Enforcement (Priority: P2)

As a user or automated system, I want to choose between Semantic Mode (free-flowing text across chosen paper sizes and lined grids) and Fidelity Mode (fixed-page layout preserving source geometry and images), and I want the system to fail fast with clear instructions if required conversion tools are missing rather than silently using placeholder sample data.

**Why this priority**: Both modes serve distinct use cases. Semantic mode allows re-paginating DOCX onto A3/A4/Ô Li graph paper, whereas Fidelity mode guarantees 1:1 visual fidelity to the original file. Silently falling back to dummy fixture data when conversion tools are absent corrupts user documents and produces invalid outputs.

**Independent Test**: Execute the command-line interface and GUI with `--mode semantic` and `--mode fidelity`. Confirm that `--mode semantic` uses `DocumentLayoutEngine` with user-selected paper grids, while `--mode fidelity` activates the fixed-layout engine. Test on an environment without Word or LibreOffice to ensure an immediate, actionable error is raised without generating dummy files.

**Acceptance Scenarios**:

1. **Given** a user selecting Fidelity Mode in the GUI or CLI on a machine with Microsoft Word or LibreOffice, **When** processing starts, **Then** the system engages the fixed-layout replacement pipeline.
2. **Given** a user selecting Semantic Mode, **When** processing starts, **Then** the system engages the existing `DocumentLayoutEngine` reflow pipeline.
3. **Given** an environment without Microsoft Word or LibreOffice, **When** Fidelity Mode is invoked on a DOCX document, **Then** the system halts immediately and raises a descriptive error explaining that Word or LibreOffice is required, without copying or using test fixtures.
4. **Given** an attempt to invoke Fidelity Mode on non-DOCX input (plain text or markdown), **When** validated, **Then** the system halts with clear guidance directing the user to `--mode semantic`.

---

### User Story 4 - Multi-Page Annotation Viewer Compatibility (Priority: P3)

As a student or instructor opening the generated `.xopp` file in Xournal++, I want the document to load seamlessly with its background pages and overlay handwriting layers, so that I can inspect, further annotate, or export the document to PDF.

**Why this priority**: Xournal++ is the primary downstream consumer for `.xopp` files. Background attachments must comply with standard multi-page background references so users do not encounter blank pages or missing assets.

**Independent Test**: Open the generated output file in Xournal++ (or parse the XML package against Xournal++ format specifications). Confirm that each page references its corresponding background page number (`<background type="pdf" pageno="N"/>` or embedded raster/vector equivalent) and that handwritten stroke layers overlay accurately.

**Acceptance Scenarios**:

1. **Given** a multi-page output package, **When** inspected, **Then** each page in `.xopp` contains a valid `<background>` definition matching the page index with portable relative file references.
2. **Given** the generated output file, **When** opened in Xournal++, **Then** all handwritten strokes appear crisp in the foreground layer on top of the original non-text visual content.

---

### Edge Cases

- **Host without Word or LibreOffice**: System must raise a clear, fatal error in production rather than silently loading test fixture data.
- **Variable Font Sizes & Line Heights**: When the source document uses compact text (e.g. 8pt or 9pt) or condensed table columns, the handwriting generator must scale stroke size proportionally to fit within the text bounding box without overlapping adjacent rows.
- **Paragraphs with Interleaved Images (`text -> image -> text`)**: Paragraphs containing inline images must segment into discrete bounding boxes so text flow does not overwrite graphic figures.
- **DrawingML Shapes and Text Boxes**: Text frames inside DrawingML elements (`w:txBody`, `w:drawing`, `v:textbox`) must have their font color neutralized to white (`#FFFFFF`) to prevent printed text ghosting.
- **Nested Tables**: Tables inside table cells must have all paragraph runs whited out alongside root table cells.
- **Empty or Whitespace-Only Paragraphs**: Spacer lines must be preserved geometrically without generating extraneous strokes or missing-character warnings.
- **Non-Text Background Packaging**: The companion PDF background must use relative domain references (`domain="relative"`) in the `.xopp` file to ensure portability when the document folder is moved or shared.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated Fidelity Replacement Mode distinct from the existing Semantic Reflow Mode.
- **FR-002**: System MUST accept DOCX documents and extract fixed-page layout structures containing geometric bounding boxes for all text blocks, lines, and non-text elements.
- **FR-003**: System MUST preserve 100% of embedded images (PNG, JPEG, etc.) and graphic figures at their exact spatial locations on their corresponding pages in the background layer.
- **FR-004**: System MUST preserve the exact page count and dimensions of the source document in Fidelity Mode (e.g. 19 pages remain 19 pages).
- **FR-005**: System MUST fit handwritten strokes into the extracted bounding box of each text element, adjusting stroke scale and respecting paragraph alignment (`left`, `center`, `right`) to prevent boundary overflow.
- **FR-006**: System MUST retain tables, cell borders, shading, and diagrammatic line art in the visual background layer.
- **FR-007**: System MUST generate output compatible with Xournal++ (`.xopp`), linking each page to its corresponding background page index via relative path references.
- **FR-008**: System MUST allow users to select between Fidelity Mode and Semantic Mode via both the CLI (e.g. `--mode fidelity | --mode semantic`) and GUI options.
- **FR-009**: System MUST report accurate statistics for Fidelity Mode processing, including total pages processed, text blocks replaced, and images preserved.
- **FR-010**: System MUST validate input documents and reject non-DOCX formats in Fidelity Mode with actionable user guidance.
- **FR-011 (P0)**: Production conversion pipelines MUST NOT use test fixture files as fallback data under any circumstances. If neither Microsoft Word nor LibreOffice is functional on the host environment, the system MUST raise an explicit, actionable error explaining the dependency requirement.
- **FR-012 (P1)**: The whiteout background generator MUST neutralize all printed text to `#FFFFFF` across standard paragraphs, table cells (including nested tables), headers, footers, and DrawingML/textbox shapes (`w:drawing`, `w:txBody`, `w:pict`, `v:textbox`).
- **FR-013 (P1)**: When an inline image is embedded within a paragraph, the layout engine MUST segment the paragraph into discrete bounding boxes preceding and succeeding the image, preventing handwriting strokes from colliding with or crossing over the image boundary.

---

### Key Entities

- **FixedDocument**: Represents a document with immutable page geometry and z-ordered visual elements.
- **FixedPage**: Represents an individual page with fixed width, height, companion background reference, and a collection of spatial elements.
- **TextBox**: A spatial element containing text content, bounding box `(x, y, width, height)`, font size, line spacing, and text alignment.
- **ImageBox**: A spatial element containing embedded image metadata and bounding box `(x, y, width, height)` used for spatial exclusion and verification; visual rendering of the graphic is preserved losslessly by the companion background PDF.
- **TableGeometry**: A spatial element defining table boundary dimensions, row/column counts, and cell coordinates.
- **BackgroundLayer**: The non-text visual representation (vector PDF) of a page containing images, table outlines, and graphical decorations with printed text neutralized to white.
- **WriteResult**: Outcome of a writing job, detailing output path, page count, stroke count, line count, missing tokens, and preserved image and table counts.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pages in the source document are preserved in the output (e.g. a 19-page input produces a 19-page output).
- **SC-002**: 100% of embedded images (e.g. all 19 images in Problem Set 03) appear in the output at their exact document positions.
- **SC-003**: 0% displacement or reordering of non-text elements (tables, charts, and figure captions maintain identical relative ordering).
- **SC-004**: Handwritten text strokes stay within 98% of the designated text bounding boxes without vertical clipping or horizontal collision with adjacent content.
- **SC-005**: 0% printed text ghosting or bleed-through in the background layer across all document body, shape, and table elements.
- **SC-006**: 0% dummy fixture fallback bleed in production environments lacking conversion tools (clean, fail-fast behavior with descriptive user messaging).
- **SC-007**: Generated multi-page output files open successfully in Xournal++ with synchronized background alignment on all pages.

---

## Assumptions

- Users requiring Fidelity Mode intend to preserve the exact visual appearance of their original document, replacing printed type with personal handwriting style.
- The companion background PDF preserves full vector precision and raster image quality directly from the original document renderer.
- For Semantic Mode, the existing `DocumentLayoutEngine` and `DocxImporter` continue to serve free-flow text reflow across customized paper sizes (A4, A3, Letter) and backgrounds (Ô Li, Ruled, Plain).
- In Fidelity Mode, background paper options (such as custom Ô Li grid lines) are disabled or deferred to the source document's native background, because the source document already defines its own page background and graphics.
