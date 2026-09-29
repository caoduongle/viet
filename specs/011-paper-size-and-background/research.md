# Research: Paper Sizes, Page Margins & Native XOPP Backgrounds

**Feature Branch**: `011-paper-size-and-background`
**Date**: 2026-09-30
**Spec**: [spec.md](spec.md)

---

## 1. Investigation of Xournal++ Background Architecture

### 1.1 Native XOPP Background Elements
In the Xournal++ `.xopp` XML format, each `<page>` element contains a `<background>` element defining the page background.
Standard structure:
```xml
<page width="595.28" height="841.89">
<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>
<layer>
  <!-- Only handwriting strokes here -->
</layer>
</page>
```

### 1.2 Supported Xournal++ Background Styles & Attributes
According to Xournal++ source code and documentation:
1. **`plain`**: Blank page without lines or grid.
   - Tag: `<background type="solid" color="#ffffffff" style="plain"/>`
2. **`lined` / `ruled`**: Horizontal ruling lines.
   - Tag: `<background type="solid" color="#ffffffff" style="lined" config="r1=24.0"/>`
3. **`ruled` with vertical line / margin**: Horizontal ruling lines plus a vertical left margin line.
   - Tag: `<background type="solid" color="#ffffffff" style="ruled" config="r1=24.0,m1=72.0"/>` (or `style="ruled"` with margin config)
4. **`graph`**: Rectangular / square grid (ô li / kẻ ô).
   - Tag: `<background type="solid" color="#ffffffff" style="graph" config="r1=14.17"/>`
   - Spacing: 5 mm = 14.1732 pt.
5. **`dotted`**: Dotted grid points.
   - Tag: `<background type="solid" color="#ffffffff" style="dotted" config="r1=14.17"/>`
6. **`iso_graph`** (or `isometric_graph`): Isometric triangular grid.
   - Tag: `<background type="solid" color="#ffffffff" style="iso_graph" config="r1=14.17"/>`
7. **`iso_dotted`** (or `isometric_dotted`): Isometric dotted grid.
   - Tag: `<background type="solid" color="#ffffffff" style="iso_dotted" config="r1=14.17"/>`
8. **`music`**: Music manuscript staves.
   - Tag: `<background type="solid" color="#ffffffff" style="music"/>`

### 1.3 Key Benefits of Native Background Tags vs Hand-drawn Strokes
- **File size**: 0 bytes of extra stroke data; background is rendered in real time by Xournal++ GPU/cairo shaders.
- **Visual fidelity**: Infinite zoom without pixelation; lines stay faint and sharp.
- **Separation of concerns**: Handwriting strokes can be erased, moved, or lasso-selected in Xournal++ without accidentally selecting background grid lines.

---

## 2. Paper Sizing & Typography Standards

### 2.1 Standard Dimensions (PostScript / PDF Points, 72 pt = 1 inch)
| Paper Format | Width (mm) | Height (mm) | Width (pt) | Height (pt) |
|---|---|---|---|---|
| **A5** | 148 | 210 | 419.53 | 595.28 |
| **A4** | 210 | 297 | 595.28 | 841.89 |
| **A3** | 297 | 420 | 841.89 | 1190.55 |
| **US Letter** | 215.9 | 279.4 | 612.00 | 792.00 |
| **US Legal** | 215.9 | 355.6 | 612.00 | 1008.00 |
| **16:9** | ~297 | ~167 | 841.89 | 473.56 |
| **4:3** | ~279.4 | ~209.5 | 792.00 | 594.00 |

### 2.2 Orientation Dynamics
- **Portrait**: Vertical orientation. `width = min(w, h)`, `height = max(w, h)`.
- **Landscape**: Horizontal orientation. `width = max(w, h)`, `height = min(w, h)`.
*(Exception: Screens like 16:9 have landscape as their natural basis, but portrait orientation flips them to 9:16).*

### 2.3 Unit Parsing & Conversion
Users and CLI scripts may specify dimensions in various units:
- `pt`: Direct points ($1 \text{ pt} = 1.0$).
- `mm`: Millimeters ($1 \text{ mm} = 72 / 25.4 \approx 2.83464567 \text{ pt}$).
- `cm`: Centimeters ($1 \text{ cm} = 10 \text{ mm} \approx 28.3464567 \text{ pt}$).
- `in`: Inches ($1 \text{ in} = 72.0 \text{ pt}$).

A robust helper `parse_length(val: str | float | int, default_unit="pt") -> float` ensures seamless parsing of values like `"5mm"`, `"21cm"`, `"8.5in"`, or `14.17`.

---

## 3. Layout Architecture Decoupling (Paper Dimensions vs Margins)

### 3.1 Deficiencies in Current Layout Engine
In `chuviettay/layout/engine.py`:
- `page_w = self.x0 + self.width + 20`
- `max_page_y = MAXH - 40.0` where `MAXH = 3000.0 pt`
- `pb = PageBuffer(out_path, page_w, default_page_h=MAXH)`

Consequences:
- The page height is always ~3000 pt regardless of content or paper choice.
- The page width is tied to handwriting width instead of standardized paper.
- A4/A3/Letter cannot paginate properly.

### 3.2 Target Layout Engine Architecture
Decouple page geometry from content layout:
```python
# In DocumentLayoutEngine:
page_format = self.opts.resolve_page_format()

page_w = page_format.width
page_h = page_format.height
content_left = page_format.margin_left
content_right = page_format.margin_right
content_top = page_format.margin_top
content_bottom = page_format.margin_bottom

usable_w = page_w - content_left - content_right
max_page_y = page_h - content_bottom
cur_y = content_top
x0 = content_left
```
When `cur_y + block_h > max_page_y`:
- Calls `new_page()`:
  - Appends current page to `PageBuffer` with dimensions `(page_w, page_h)` and background config.
  - Resets `cur_y = content_top`.

---

## 4. Component Roadmap & Strategy

1. **`chuviettay/document/page_format.py`**:
   - Create dataclasses `PaperSize`, `PageBackground`, `PageFormat`.
   - Define `PAPER_SIZES` and `parse_length()`.
2. **`chuviettay/model/composer.py`**:
   - Extend `WriteOptions` with paper, orientation, margins, and background fields.
   - Add `WriteOptions.resolve_page_format()`.
3. **`chuviettay/model/xopp.py`**:
   - Add `page_open_xml(page_w, page_h, background)` generating valid XOPP background XML.
4. **`chuviettay/layout/stream.py`**:
   - Update `PageBuffer` to record background and apply per-page dimensions.
5. **`chuviettay/layout/engine.py`**:
   - Consume resolved `PageFormat`, apply margins and realistic pagination.
6. **`chuviettay/cli.py`**:
   - Expose flags `--paper`, `--orientation`, `--background`, `--background-spacing`.
7. **`chuviettay/view/write_tab.py`**:
   - Add "Trang & Nền giấy" controls in GUI.
8. **Tests**:
   - Unit tests for `page_format.py`.
   - Tests for `PageBuffer` background XML.
   - Tests for `DocumentLayoutEngine` pagination on A4, A3, Letter, and Custom paper.
