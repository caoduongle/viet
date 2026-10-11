# Data Model: Xournal++ Paper Background and Geometry Parity

**Feature Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11
**Spec**: [spec.md](spec.md)

This document formalizes the entities, properties, data structures, and invariants for Xournal++ paper styles, background XML serialization, baseline snapping, and UI catalogs.

---

## 1. PageBackground

Represents background styling and ruling parameters for a document page in accordance with Xournal++ `<background>` specification.

### Attributes
- `style: str` (Default: `"plain"`)
  - Allowed values: `"plain"`, `"ruled"`, `"lined"`, `"graph"`, `"dotted"`, `"iso_graph"`, `"iso_dotted"`, `"staves"`, `"pdf"`.
- `color: str` (Default: `"#ffffffff"`)
  - 8-digit RGBA or 6-digit RGB hex string.
- `spacing: float | None` (alias: `r1`)
  - Ruling pitch or grid interval in points ($pt$).
  - Defaults: $24.0$ for `ruled`/`lined`; $14.1732$ ($5\,\text{mm}$) for `graph`/`dotted`/`iso_graph`/`iso_dotted`.
- `margin: float | None` (alias: `m1`)
  - Margin offset in points ($pt$).
  - For `lined`: positive value ($72.0$) indicates distance from left edge; negative value ($-72.0$) indicates offset from right edge ($x = \text{pageWidth} + m_1$).
  - For `graph`: positive value indicates margin on all 4 sides.
- `line_width: float | None` (alias: `lw`, Default: `0.5`)
  - Stroke width in points for standard ruling/grid lines.
- `primary_color: str | None` (alias: `f1`)
  - Hex color for primary ruling lines (e.g. dodgerblue `#40a0ff`).
- `secondary_color: str | None` (alias: `f2`)
  - Hex color for secondary/margin lines (e.g. deeppink `#ff0080`).
- `round_margin: bool | None` (alias: `rm`)
  - Whether graph margins are rounded to grid increments.
- `bold_line_interval: int | None` (alias: `bli`)
  - Interval (e.g. `5`) for drawing prominent bold grid lines.
- `bold_line_width: float | None` (alias: `blw`, Default: `1.5`)
  - Stroke width for bold grid lines.

### Methods & Serialization
- `to_xml() -> str`:
  - Returns `<background type="solid" color="..." style="..." config="..."/>` or `<background type="pdf" domain="absolute" filename="..." pageno="..."/>`.
  - Config string joins non-default attributes as key-value pairs (e.g. `config="r1=18,m1=72"` or `config="m1=-72"`).

---

## 2. PdfBackgroundReference

Represents an attached or referenced PDF background page.

### Attributes
- `filename: str`: Bare relative filename of the referenced PDF document.
- `pageno: int`: 1-based page number (1 for first page, 2 for second page).
- `domain: str`: `"absolute"` (mandatory in Xournal++ for filesystem-relative references).

---

## 3. BackgroundPreset

Predefined background template matching Xournal++ `pagetemplates.ini.in`.

### Schema
```python
@dataclass(frozen=True)
class BackgroundPreset:
    id: str                       # e.g., "lined_college", "graph_5mm"
    name: str                     # Human-readable title
    style: str                    # "plain", "ruled", "lined", "graph", etc.
    spacing: float | None = None  # r1
    margin: float | None = None   # m1
    bold_interval: int | None = None  # bli
    bold_width: float | None = None   # blw
    round_margin: bool | None = None  # rm
```

### Registered Presets
- `plain`: Style `plain`
- `ruled`: Style `ruled`, $r_1 = 24.0$
- `lined`: Style `lined`, $r_1 = 24.0$, $m_1 = 72.0$
- `lined_narrow`: Style `lined`, $r_1 = 18.0$, $m_1 = 72.0$
- `lined_college`: Style `lined`, $r_1 = 20.0$, $m_1 = 72.0$
- `lined_wide`: Style `lined`, $r_1 = 24.0$, $m_1 = 72.0$
- `graph`: Style `graph`, $r_1 = 14.1732$
- `graph_5mm`: Style `graph`, $r_1 = 14.1732$
- `graph_grid`: Style `graph`, $r_1 = 14.1732$, $bli = 5$, $blw = 1.5$
- `dotted`: Style `dotted`, $r_1 = 14.1732$
- `iso_graph`: Style `iso_graph`, $r_1 = 14.1732$
- `iso_dotted`: Style `iso_dotted`, $r_1 = 14.1732$
- `staves`: Style `staves`

---

## 4. SnappingMetrics & Layout State

Encapsulates state during handwritten text synthesis when snapping to ruling lines.

### Attributes
- `snap_to_ruling: bool`: Flag enabled on `ruled` and `lined` backgrounds.
- `r1: float`: Ruling line pitch (typically $24.0\,\text{pt}$).
- `m1: float`: Margin line position.
- `first_baseline_y: float`: Smallest $y = 80.0 + k \cdot r_1$ below requested top margin.
- `pitch: float`: $r_1 \cdot \max(1, \text{round}(\text{eff\_line\_h} / r_1))$.
- `page_break_threshold: float`: $\text{pageHeight} - 60.0$.
- `text_left_bound: float`: $m_1 + 8.0$ if $m_1 > 0$ else `margin_left`.
- `text_right_bound: float`: $\text{pageWidth} + m_1 - 8.0$ if $m_1 < 0$ else $\text{pageWidth} - \text{margin\_right}$.

---

## 5. PageCatalog

Data structure returned by `get_page_catalog()`.

### Structure
```python
{
    "sizes": {
        "a4": {"name": "A4", "width": 595.28, "height": 841.89},
        "a3": {"name": "A3", "width": 841.89, "height": 1190.55},
        "a5": {"name": "A5", "width": 419.53, "height": 595.28},
        "letter": {"name": "Letter", "width": 612.00, "height": 792.00},
        "legal": {"name": "Legal", "width": 612.00, "height": 1008.00},
        "16:9": {"name": "16:9 Presentation", "width": 841.89, "height": 473.56},
        "4:3": {"name": "4:3 Presentation", "width": 792.00, "height": 594.00},
    },
    "presets": { ... },   # Maps preset ID to BackgroundPreset dictionary
    "tones": [
        {"id": "white", "name": "Trắng", "color": "#ffffffff", "dark": False},
        {"id": "ivory", "name": "Vàng ngà", "color": "#ffffc8ff", "dark": False},
        {"id": "blue", "name": "Xanh nhạt", "color": "#e8f4f8ff", "dark": False},
        {"id": "dark", "name": "Tối", "color": "#1e1e1eff", "dark": True},
    ]
}
```
