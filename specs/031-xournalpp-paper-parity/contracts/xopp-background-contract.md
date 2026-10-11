# Interface Contract: XOPP Background XML and Geometry Specification

**Feature Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11
**Spec**: [spec.md](../spec.md)

This contract defines the format of `.xopp` `<background>` XML elements and the geometrical drawing contracts implemented in both Python core export and Web SVG rendering.

---

## 1. Background XML Schemas

### Solid Color & Generated Ruling Paper
```xml
<background type="solid" color="#ffffffff" style="lined" config="r1=24,m1=72"/>
```

- **`type`**: Always `"solid"`.
- **`color`**: 8-character hex `#rrggbbaa` or 6-character `#rrggbb`.
- **`style`**: One of:
  - `"plain"`: Blank page
  - `"ruled"`: Horizontal ruling lines
  - `"lined"`: Horizontal ruling lines with vertical margin line
  - `"graph"`: Orthogonal grid
  - `"dotted"`: Grid intersection dots
  - `"isograph"` / `"iso_graph"`: Isometric triangular grid
  - `"isodotted"` / `"iso_dotted"`: Isometric grid dots
  - `"staves"`: Musical 5-line staves
- **`config`**: Key-value pairs separated by commas (`,`) or semicolons (`;`):
  - `r1=<float>`: Pitch / grid step in points.
  - `m1=<float>`: Margin offset in points. Negative values indicate offset from right boundary (`x = pageWidth + m1`).
  - `lw=<float>`: Line width in points (default: `0.5`).
  - `f1=<hex>`: Foreground primary line color (e.g. `40a0ff` without `#` in Xournal++, or `#40a0ff`).
  - `f2=<hex>`: Foreground secondary margin line color (e.g. `ff0080`).
  - `rm=1`: Round margin to nearest grid boundary.
  - `bli=<int>`: Bold line interval (e.g. `5`).
  - `blw=<float>`: Bold line stroke width (default: `1.5`).

### PDF Referenced Background
```xml
<background type="pdf" domain="absolute" filename="document.pdf" pageno="1"/>
```

- **`type`**: Always `"pdf"`.
- **`domain`**: Strictly `"absolute"`.
- **`filename`**: Bare filename without directory prefix (Xournal++ resolves relative to `.xopp` file location).
- **`pageno`**: 1-based string or integer (`"1"`, `"2"`, ...).

---

## 2. Geometrical Bounds Contract

### Ruled / Lined
- Horizontal lines: $y = 80.0 + i \cdot r_1$ for all integers $i \ge 0$ satisfying $80.0 \le y \le \text{pageHeight} - 60.0$.
- Lined vertical margin line: $x = m_1$ (if $m_1 > 0$) or $x = \text{pageWidth} + m_1$ (if $m_1 < 0$) running from $y = 0$ to $y = \text{pageHeight}$.

### Graph
- If $m_1 = 0$: Grid lines extend from edge to edge ($x \in [0, \text{pageWidth}], y \in [0, \text{pageHeight}]$).
- If $m_1 > 0$: Grid starts at $x = m_1$ and ends at $\text{pageWidth} - m_1$; starts at $y = m_1$ and ends at $\text{pageHeight} - m_1$.
- Bold lines: Any line where $(\text{index} \pmod{bli}) == 0$ is drawn with width $blw$.

### Staves
- Number of lines per staff: 5.
- Inter-line spacing: $5.0\,\text{pt}$.
- Inter-staff spacing: $40.0\,\text{pt}$.
- Staff step: $V_{\text{step}} = 40.0 + 20.5 + 4 \cdot lw = 62.5\,\text{pt}$.
- Horizontal span: $x \in [50.0, \text{pageWidth} - 50.0]$.
- Vertical range: Top staff starts at $y = 80.0$, subsequent staves start at $y = 80.0 + k \cdot 62.5$ provided the 5th line does not exceed $\text{pageHeight} - 60.0$.
