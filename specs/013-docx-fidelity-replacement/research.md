# Research & Technical Decisions: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30

---

## 1. Dual Mode Architecture: Semantic vs. Fidelity

### Decision
Separate the DOCX processing pipeline into two explicit, decoupled modes:
1. **Semantic Mode (`DocumentLayoutEngine`)**:
   - Parses DOCX into the semantic `Document` IR (`Paragraph`, `Table`, `Heading`, `MathBlock`).
   - Reflows and repaginates content freely across user-specified paper sizes (A4, A3, Letter) and backgrounds (Ô Li, Ruled, Plain).
   - Ideal for plain notes, essays, and re-styled documents.
2. **Fidelity Mode (`FixedLayoutEngine`)**:
   - Locks document geometry, page count, and dimensions.
   - Extracts `FixedPage` containing exact spatial bounding boxes for `TextBox`, `ImageBox`, and `TableGeometry`.
   - Generates a non-text visual background (preserving 100% of images, diagrams, and table borders).
   - In-place replacement: handwritten strokes are scaled and fitted directly into the original text bounding boxes.
   - Outputs a multi-page `.xopp` document referencing the companion background.

### Rationale
Attempting to force fixed-layout replacement into `DocumentLayoutEngine` compromises both paradigms: semantic reflow needs dynamic wrapping and flexible pagination, while fidelity replacement strictly forbids reflow and requires geometric coordinate locking. Separating them maintains high cohesion and loose coupling (Constitution Principle IV).

### Alternatives Considered
- *Overloading `DocxImporter` with geometric coordinates*: Rejected because `Document` IR is designed for fluid block-level document flows, not coordinate-based fixed rendering.
- *Full bitmap rasterization of pages*: Rejected because rasterizing text and images degrades vector quality, bloats file sizes, and fails the requirement to replace only text with handwriting.

---

## 2. Non-Text Background Generation & Text Erasure

### Decision
To create the clean visual background preserving images, charts, and table borders without printed text ghosting:
1. **Whiteout Run Transform (DOCX-level)**:
   - Create a sanitized background copy of the DOCX where all text runs (`w:r/w:t`) have their font color set to white (`w:color w:val="FFFFFF"`).
   - This preserves 100% of line heights, character spacing, paragraph margins, table dimensions, and image anchors without shifting layout geometry by even 1 pt.
2. **Fixed-Layout Rendering**:
   - Convert the whiteout DOCX into a companion background PDF (`problem_set_03_handwriting_background.pdf`).
   - On Windows: Uses native Word COM automation (Office 16 detected and verified via PowerShell in <5s) or fallback CLI converters.
   - On Linux/macOS: Uses headless LibreOffice (`soffice --headless --convert-to pdf`) if available, or direct high-fidelity SVG/PDF extraction.
3. **XOPP Native Background Reference**:
   - In the output `.xopp` XML:
     ```xml
     <page width="595.28" height="841.89">
       <background type="pdf" domain="absolute" filename="problem_set_03_handwriting_background.pdf" pageno="0"/>
       <layer>
         <!-- Handwritten strokes positioned at exact text coordinates -->
       </layer>
     </page>
     ```

### Rationale
Setting text color to white within the native layout engine is mathematically superior to post-hoc bounding box redaction:
- Zero edge artifacts or clipping around table borders.
- Preserves identical font metrics, line wraps, and object anchor points.
- Extremely fast and resilient across complex multi-column documents.

### Alternatives Considered
- *Post-render PDF text redaction*: Requires heavy external C/C++ libraries (like Poppler or MuPDF) which are not part of the standard Python distribution and are difficult to deploy cross-platform.
- *Drawing white opaque rectangles in XOPP*: Xournal++ strokes are rendered on top of the background; while opaque strokes can cover text, complex background shading or adjacent lines may be inadvertently obscured.

---

## 3. Spatial Text Box Extraction & Handwriting Fitting

### Decision
Represent fixed-layout pages through spatial structures:
- `FixedPage(page_index: int, width: float, height: float, boxes: list[SpatialBox])`
- `TextBox(x: float, y: float, width: float, height: float, text: str, font_size: float, align: str)`
- `ImageBox(x: float, y: float, width: float, height: float, rel_id: str, image_bytes: bytes)`

For each `TextBox`:
1. Calculate target baseline $Y$ and available horizontal span $W$.
2. Scale handwriting token widths: if the handwritten text would exceed $W$, calculate scale factor $S = \min(S_{default}, W / W_{natural})$.
3. Position strokes using `Writer.token()` within $(X, Y, X + W, Y + H)$ without triggering line wrapping to new lines.

### Rationale
Ensures handwritten text never overflows table cell boundaries, never collides with adjacent columns, and fits naturally within the original printed line boundaries.

---

## 4. CLI & GUI Integration Contract

### Decision
- **CLI**:
  - `python -m chuviettay write doc.docx -o out.xopp --mode fidelity` (or `--mode semantic`).
  - Default for DOCX when images are present can suggest or default to `--mode fidelity` when requested.
- **Controller**:
  - `AppController.write_docx_fidelity(docx_path: str, opts: WriteOptions, out_path: str) -> WriteResult`
- **GUI**:
  - "Chế độ xử lý DOCX": Combobox offering `Giữ nguyên bố cục & ảnh (Fidelity)` vs `Tái dàn trang (Semantic)`.
