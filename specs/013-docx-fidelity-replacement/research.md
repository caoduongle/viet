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
   - In-place replacement: handwritten strokes are scaled and fitted directly into original text bounding boxes.
   - Outputs a multi-page `.xopp` document referencing the companion background.

### Rationale
Attempting to force fixed-layout replacement into `DocumentLayoutEngine` compromises both paradigms: semantic reflow needs dynamic wrapping and flexible pagination, while fidelity replacement strictly forbids reflow and requires geometric coordinate locking. Separating them maintains high cohesion and loose coupling (Constitution Principle IV).

---

## 2. Production Fail-Fast vs. Fixture Mocking (P0)

### Decision
- **Production Path**:
  When converting DOCX to PDF or extracting spatial coordinates, the system checks for Microsoft Word COM (on Windows) and LibreOffice (on Linux/macOS). If neither tool is available, the system immediately raises:
  ```python
  raise RuntimeError(
      "Fidelity Mode yêu cầu Microsoft Word (Windows) hoặc LibreOffice (Linux/macOS) để xử lý bố cục cố định. "
      "Vui lòng cài đặt Microsoft Word hoặc sử dụng chế độ Semantic Mode (--mode semantic)."
  )
  ```
  **Zero fixture fallback**: Production code must NEVER copy `sample_fidelity_data.json` or `sample_background.pdf` when processing user documents.
- **Testing Path**:
  In automated tests (e.g. CI environments without Word/LibreOffice), unit tests explicitly test parsing using `SpatialTextExtractor.load_from_data(fixture_json)` or mock/monkeypatch `FidelityConverter` methods.

### Rationale
Silently falling back to a 2-page sample fixture when a user runs a real 19-page document produces corrupted, truncated, or nonsensical output. A clear fail-fast error with user guidance preserves data integrity.

---

## 3. Comprehensive Whiteout for DrawingML, Textboxes, and Shapes (P1)

### Decision
`WhiteoutBackgroundGenerator` operates directly on OpenXML elements to neutralize all printed text to `#FFFFFF` while preserving shapes, borders, and images:
1. **Standard Paragraphs & Inlines**: Iterate `doc.paragraphs` and set each run's font color to `#FFFFFF`.
2. **Tables & Nested Tables**: Recursively traverse all `tbl.rows` and `cell.paragraphs`, plus any nested tables (`cell.tables`).
3. **DrawingML Text & Shapes**: Deeply inspect OpenXML elements containing text frames:
   - `w:drawing//w:r`, `w:drawing//a:t`, `w:drawing//w:txBody`
   - `w:pict//v:textbox//w:r`, `v:shape//v:textbox`
   - Set font color element `<w:rPr><w:color w:val="FFFFFF"/></w:rPr>` or DrawingML text run fill `<a:rPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:rPr>`.
4. **Headers and Footers**: Whiten all text across header/footer paragraphs.

### Rationale
Many documents (such as problem sets and technical documentation) place problem numbers, legends, or callouts inside shapes or text boxes. Whitenening only standard paragraph runs leaves shape text visible in black, creating double-text ghosting beneath handwritten strokes.

---

## 4. Mixed-Inline Spatial Segmentation (`Text -> Image -> Text`) (P1)

### Decision
When an inline shape/image is embedded inside a paragraph:
- Word COM / OpenXML extraction detects the character offset and spatial bounds of the inline shape.
- The paragraph is segmented into ordered spatial fragments:
  1. `TextBox` for text preceding the inline image.
  2. `ImageBox` for the image geometry (used as a spatial exclusion boundary).
  3. `TextBox` for text following the inline image.
- `FidelityLayoutEngine` renders strokes into the preceding and succeeding `TextBox`es independently, ensuring handwritten strokes never collide with or overwrite the embedded graphic.

---

## 5. ImageBox Role: Geometric Exclusion & Verification

### Decision
Clarify that `ImageBox` in `FixedDocument` represents geometric bounding metadata and spatial exclusion:
- In `.xopp`, visual display of graphics is rendered by the companion background PDF.
- `ImageBox` provides the layout engine with coordinates of non-text regions to prevent text stroke collision and enable verification statistics (`n_images` in `WriteResult`).
