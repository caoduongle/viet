# Data Model & Schema Specifications: Letter Assembly Quality

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](./spec.md)  
**Status**: Completed  

---

## 1. Domain Entities & Schema Definitions

### 1.1 Bank Letter Sample (`BankLetterSample`)

Represents an individual character sample stored in `bank.letters[char]`. Extends the legacy `{w, s}` structure with typographical metrics and boundary contour classes.

```python
from dataclasses import dataclass
from typing import Literal

ContourType = Literal["CURVED", "STRAIGHT", "OPEN"]
CharCategory = Literal["x_height", "ascender", "descender", "uppercase", "digit", "punct", "symbol"]

@dataclass(frozen=True)
class BankLetterSample:
    s: list[list[tuple[float, float]]]  # List of vector strokes
    w: float                            # Bounding-box width (max_x - min_x)
    h: float                            # Bounding-box height (max_y - min_y)
    lsb: float                          # Left Side Bearing (whitespace margin on left)
    rsb: float                          # Right Side Bearing (whitespace margin on right)
    adv: float                          # Advance width (w + lsb + rsb)
    category: CharCategory              # Classification for normalization
    left_contour: ContourType           # Contour shape of the left edge
    right_contour: ContourType          # Contour shape of the right edge
    baseline_y: float = 0.0             # Baseline anchor (y=0)
```

**JSON Serialization in `.json.gz` (Schema v4)**:
```json
{
  "letters": {
    "a": [
      {
        "s": [[[0.2, -4.8], [1.1, -4.9], ...]],
        "w": 5.0,
        "h": 4.9,
        "lsb": 0.4,
        "rsb": 0.5,
        "adv": 5.9,
        "cat": "x_height",
        "lc": "CURVED",
        "rc": "STRAIGHT"
      }
    ]
  }
}
```

*Backward Compatibility Note*: If `lsb`, `rsb`, `adv`, `cat`, `lc`, `rc` are absent (legacy v3 or v4 initial samples), the engine computes default fallback metrics at load time: `lsb = 0.1 * xh`, `rsb = 0.1 * xh`, `adv = w + lsb + rsb`, and categorizes contour types based on Unicode character lookup tables.

---

### 1.2 Bank Tone Mark Sample (`BankMarkSample`)

Represents an isolated Vietnamese tone mark stored in `bank.marks[tone_key]`. May originate from automatic word harvesting (`_src: word`) or directly from `hw3` standalone tone mark cells (`_src: "standalone"`).

```python
@dataclass(frozen=True)
class BankMarkSample:
    s: list[list[tuple[float, float]]]  # Stroke(s) forming the tone mark (centered at origin)
    dx: float                           # Horizontal offset relative to vowel centroid
    dy: float                           # Vertical offset relative to vowel top/bottom
    zone: Literal["ABOVE", "BELOW"]     # Vertical placement zone (ABOVE for sắc/huyền/hỏi/ngã, BELOW for nặng)
    tone_key: str                       # Unicode combining tone mark (config.TONES)
    src: str = "standalone"             # Origin: "standalone" (from hw3 grid) or source word
```

---

### 1.3 Assembled Word Layout (`AssembledWordLayout`)

Intermediate domain layout representation produced during word synthesis prior to document canvas emission.

```python
@dataclass
class PositionedGlyph:
    char: str
    strokes: list[list[tuple[float, float]]]
    bbox: tuple[float, float, float, float]  # (min_x, min_y, max_x, max_y)
    origin_x: float
    origin_y: float
    advance: float

@dataclass
class AssembledWordLayout:
    text: str
    glyphs: list[PositionedGlyph]
    marks: list[PositionedGlyph]
    total_width: float
    max_ascender: float
    max_descender: float
    min_clearance: float
    max_overlap_ratio: float
```

---

### 1.4 Grid Template Specification (`GridTemplateHW3`)

Defines the physical layout and reference coordinate guidelines for collection sheets.

```python
@dataclass(frozen=True)
class GridTemplateHW3:
    format_tag: str = "hw3"
    page_width: float = 595.28          # A4 width in pt
    page_height: float = 841.89         # A4 height in pt
    columns: int = 4
    rows: int = 16
    cell_width: float = 128.0
    cell_height: float = 46.0
    baseline_offset: float = 34.0       # Distance from cell top to baseline
    x_height: float = 8.6               # Calibrated from reference note (pt)
    ascender_height: float = 14.0       # Reference line for ascenders
    descender_depth: float = 10.0       # Reference line for descenders
    margin_left: float = 12.0           # Left margin boundary within cell
    margin_right: float = 12.0          # Right margin boundary within cell
```

---

### 1.5 Ink Measurement Profile (`InkMeasurementProfile`)

Output entity produced by `tools/measure_ink.py` representing quantitative handwriting characteristics.

```python
@dataclass
class InkMeasurementProfile:
    source_file: str
    sample_count: int
    median_x_height: float
    pen_thickness: float
    pen_to_xh_ratio: float
    median_letter_gap: float
    median_word_gap: float
    max_bbox_overlap_ratio: float
    min_stroke_clearance: float
    x_height_std_dev: float
    missing_characters: list[str]
```

---

## 2. Validation Rules & Invariants

1. **Clearance Floor Invariant**: For any two adjacent glyphs $G_i, G_{i+1}$ in `AssembledWordLayout`:
   $$\min_{\mathbf{p} \in G_i, \mathbf{q} \in G_{i+1}} \|\mathbf{p} - \mathbf{q}\|_2 \ge 0.8 \times \text{pen\_thickness}$$
2. **Bounding Box Overlap Invariant**:
   $$\text{overlap\_x}(G_i, G_{i+1}) \le 0.10 \times \min(\text{width}(G_i), \text{width}(G_{i+1}))$$
3. **x-Height Normalization Bound**:
   $$\left|\frac{\text{median\_x\_height} - xh_{\text{target}}}{xh_{\text{target}}}\right| \le 0.10$$
4. **Pen Thickness Ratio Bound**:
   $$\left|\frac{\text{pen\_to\_xh\_ratio} - R_{\text{target}}}{R_{\text{target}}}\right| \le 0.15$$
5. **Golden Master Byte Parity**: When `assemble_letters=False`, SHA-256 output hashes for test suites MUST match expected master hashes with 100% bitwise invariance.
