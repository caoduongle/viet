# Interface Contract: Page Format, CLI Flags & XOPP Backgrounds

**Feature Branch**: `011-paper-size-and-background` | **Date**: 2026-09-30 | **Spec**: [spec.md](../spec.md)

---

## 1. Python Public API Contract (`chuviettay.document.page_format`)

### 1.1 Dataclasses & Types

```python
from dataclasses import dataclass, field

VALID_BACKGROUND_STYLES = {
    "plain", "lined", "ruled", "graph", "dotted", "iso_graph", "iso_dotted", "music"
}

@dataclass(frozen=True)
class PaperSize:
    name: str
    width: float   # in PostScript points (1 pt = 1/72 inch)
    height: float  # in PostScript points

@dataclass(frozen=True)
class PageBackground:
    style: str = "plain"               # must belong to VALID_BACKGROUND_STYLES
    spacing: float | None = None       # in pt (e.g. 14.17 pt for 5mm grid)
    margin: float | None = None        # in pt (left vertical margin line for ruled paper)
    color: str = "#ffffffff"           # Hex RGBA color string

    def to_xml(self) -> str:
        """Returns standard XOPP <background> XML tag."""

@dataclass(frozen=True)
class PageFormat:
    paper: PaperSize
    orientation: str = "portrait"      # "portrait" | "landscape"
    margin_left: float = 36.0          # in pt
    margin_right: float = 36.0         # in pt
    margin_top: float = 40.0           # in pt
    margin_bottom: float = 40.0        # in pt
    background: PageBackground = field(default_factory=PageBackground)

    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...
    @property
    def usable_width(self) -> float: ...
    @property
    def usable_height(self) -> float: ...
    @property
    def content_top(self) -> float: ...
    @property
    def max_page_y(self) -> float: ...
```

### 1.2 Constants & Conversion Functions

```python
PAPER_SIZES: dict[str, PaperSize] = {
    "a5": PaperSize("A5", 419.53, 595.28),
    "a4": PaperSize("A4", 595.28, 841.89),
    "a3": PaperSize("A3", 841.89, 1190.55),
    "letter": PaperSize("US Letter", 612.00, 792.00),
    "legal": PaperSize("US Legal", 612.00, 1008.00),
    "16:9": PaperSize("16:9", 841.89, 473.56),
    "4:3": PaperSize("4:3", 792.00, 594.00),
}

def parse_length(val: str | float | int, default_unit: str = "pt") -> float:
    """Parse numeric values with optional units (mm, cm, in, pt) into PostScript points.
    Raises ValueError on negative, invalid, infinite, or non-numeric strings.
    """
```

---

## 2. Low-Level XML Emission Contract (`chuviettay.model.xopp`)

### 2.1 Function `page_open_xml`

```python
def page_open_xml(page_w: float, page_h: float, background: PageBackground | None = None) -> str:
    """Returns XML string to open a page:
    <page width="{page_w}" height="{page_h}">
    <background type="solid" color="{color}" style="{style}" {config}/>
    <layer>
    """
```

### 2.2 Preservation of `xopp.PAGE_OPEN`
For 100% byte-for-byte SHA256 parity with legacy golden tests (`test_golden_master.py`), the constant `PAGE_OPEN` remains untouched:
```python
PAGE_OPEN = ('<page width="%s" height="%s">\n'
             '<background type="solid" color="#ffffffff" style="plain"/>\n<layer>')
```

---

## 3. Streaming Page Buffer Contract (`chuviettay.layout.stream.PageBuffer`)

```python
class PageBuffer:
    def __init__(
        self,
        out_path: str,
        page_w: float,
        default_page_h: float = MAXH,
        default_background: PageBackground | None = None,
    ): ...

    def append_page(
        self,
        page_strokes: list[str],
        page_h: float | None = None,
        page_w: float | None = None,
        background: PageBackground | None = None,
    ) -> None: ...
```

---

## 4. Layout Engine Decoupling Contract (`chuviettay.layout.engine.DocumentLayoutEngine`)

- `page_format = self.opts.resolve_page_format()`
- `self.x0 = page_format.margin_left`
- `self.width = min(self.opts.width, page_format.usable_width) if self.opts.width is not None else page_format.usable_width`
- `cur_y` starts at `page_format.content_top`
- `max_page_y = page_format.max_page_y`
- Page boundary checks:
  - Table pagination break condition: `if avail_h < self.line_h + 2 * table_engine.cell_padding and cur_y > content_top:` (preventing infinite loop on fresh pages).
  - Every page appended to `PageBuffer` uses explicit `page_w=page_format.width, page_h=page_format.height, background=page_format.background`.

---

## 5. CLI Command Schema Contract (`hw_note.py write`)

| Flag | Argument Type | Default | Description |
|---|---|---|---|
| `--paper` | Choice: `a5`, `a4`, `a3`, `letter`, `legal`, `16:9`, `4:3`, `custom` | `a4` | Paper size format |
| `--orientation` | Choice: `portrait`, `landscape` | `portrait` | Page orientation |
| `--paper-width` | Length string (e.g. `210mm`, `595pt`) | `None` | Width for custom paper |
| `--paper-height` | Length string (e.g. `297mm`, `842pt`) | `None` | Height for custom paper |
| `--background` | Choice: `plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `music` | `plain` | Native XOPP background style |
| `--background-spacing` | Length string (e.g. `5mm`, `14.17pt`, `24pt`) | `None` | Grid / ruling spacing |
| `--background-color` | Hex string (e.g. `#ffffffff`) | `#ffffffff` | Solid background color |

---

## 6. GUI WriteTab Contract

The WriteTab UI contains a LabelFrame titled **"Trang & Nền giấy"**:
- **Khổ giấy**: Combobox (`A4 (210×297 mm)`, `A5 (148×210 mm)`, `A3 (297×420 mm)`, `US Letter`, `US Legal`, `16:9`, `4:3`, `Tùy chỉnh...`).
- **Chiều giấy**: Combobox: `Dọc (Portrait)`, `Ngang (Landscape)`.
- **Nền giấy**: Combobox: `Trắng (Plain)`, `Dòng kẻ (Ruled)`, `Dòng kẻ + lề`, `Ô li (Graph)`, `Chấm (Dotted)`, `Isometric`, `Khuông nhạc (Music)`.
- **Khoảng cách (mm)**: Entry displaying current spacing in mm (e.g. `5.0` for ô li, `8.0` for dòng kẻ).
- **Custom Paper Dialog**: Modal dialog with Width, Height, and unit selector (mm / cm / pt).
- **Text-to-Document Pipeline**: When writing text directly from the text box, convert text via `TxtImporter().import_text(text).document` and dispatch to `ctl.write_document` to ensure paper size and background settings take effect.
