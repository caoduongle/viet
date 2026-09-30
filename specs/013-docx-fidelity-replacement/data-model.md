# Data Model: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30

---

## 1. Domain Entities

### `SpatialBox` (Abstract Base)
Base class for all geometric objects located on a fixed page.
- `x: float`: Horizontal coordinate from top-left (in points, $1\text{ pt} = 1/72\text{ in}$).
- `y: float`: Vertical coordinate from top-left (in points).
- `width: float`: Horizontal span (in points).
- `height: float`: Vertical span (in points).
- `z_index: int`: Stacking order on the page.

### `TextBox(SpatialBox)`
Represents an individual text span, line, or paragraph cell with locked coordinates.
- `text: str`: Raw text content to be converted into handwriting.
- `font_size: float`: Original font size in points (used to calibrate stroke thickness and line height).
- `font_family: str`: Original font name.
- `align: str`: Alignment (`left`, `center`, `right`, `justify`).
- `line_spacing: float`: Vertical line pitch.
- `is_heading: bool`: Whether the text is marked as a title/heading.

### `ImageBox(SpatialBox)`
Represents an embedded graphic illustration, chart, or figure.
- `image_id: str`: Unique resource identifier (e.g. `rId5`).
- `image_filename: str`: Target filename inside the package (e.g. `image1.png`).
- `image_bytes: bytes`: Raw image data.
- `format: str`: Image mime type (`image/png`, `image/jpeg`).
- `caption: str | None`: Associated figure caption text (if any).

### `TableGeometry(SpatialBox)`
Represents structural table cell boundaries and shading.
- `rows: int`: Number of rows.
- `cols: int`: Number of columns.
- `cell_boxes: list[SpatialBox]`: Coordinate bounding boxes of each cell.
- `border_strokes: list[Stroke]`: Border line vectors.

### `FixedPage`
Represents an immutable single page in the document.
- `page_index: int`: 0-indexed page sequence number.
- `width: float`: Page width in points (e.g. `595.28` for A4).
- `height: float`: Page height in points (e.g. `841.89` for A4).
- `background_path: str`: Relative or absolute path to the non-text companion background PDF/asset.
- `boxes: list[SpatialBox]`: Ordered collection of spatial elements on this page.

### `FixedDocument`
Represents the complete multi-page document structure.
- `source_path: str`: Path to the original `.docx` file.
- `pages: list[FixedPage]`: Ordered list of fixed pages.
- `total_pages: int`: Count of pages (`len(pages)`).
- `background_pdf_path: str | None`: Companion background PDF path.

---

## 2. Configuration & Execution Entities

### `WriteMode` (Enum)
```python
from enum import Enum

class WriteMode(str, Enum):
    SEMANTIC = "semantic"  # Document IR -> DocumentLayoutEngine reflow
    FIDELITY = "fidelity"  # FixedPage geometry -> in-place text replacement
```

### `WriteOptions` Extensions
- `mode: WriteMode = WriteMode.SEMANTIC`: Selected operational mode.
- `keep_background_pdf: bool = True`: Whether to retain the companion background PDF beside the `.xopp` file.

### `FidelityResult` (Specialized or wrapped in `WriteResult`)
- `out_path: str`: Generated `.xopp` file path.
- `background_pdf_path: str`: Companion background PDF file path.
- `total_pages: int`: Total number of pages processed (e.g. 19).
- `n_boxes_replaced: int`: Count of text boxes converted to handwriting.
- `n_images_preserved: int`: Count of embedded images kept in place (e.g. 19).
- `n_strokes: int`: Total handwritten strokes generated.
- `missing_tokens: dict[str, int]`: Untracked characters or missing handwriting samples.
