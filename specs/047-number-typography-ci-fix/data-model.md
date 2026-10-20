# Data Model: Number Typography and CI Fallback Hardening

**Feature**: `047-number-typography-ci-fix` | **Date**: 2026-10-20

## Overview
This document defines the core data entities, geometric structures, and validation rules governing numeric typography, fallback glyph synthesis, and test bank fixtures in `chuviettay`.

---

## 1. Entities

### 1.1 NumberLayoutContext
Represents the transient typographic context used when assembling a numeric token (matching `NUMRE = re.compile(r"^[+-]?\d+(?:[,.]\d+)*(?:%)?$")`).

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `text` | `str` | Normalized string representation of the number | Must match `NUMRE` |
| `xh` | `float` | Base x-height of the handwriting style | `xh > 0.0` (default `7.94`) |
| `first` | `bool` | Flag indicating whether the cursor is at the first character | Boolean |
| `is_hyphen` | `bool` | True if the current character is `-` or precedes immediately after `-` | Used to halve inter-digit spacing |
| `p_gap` | `float` | Gap preceding a decimal separator (`0.08 * xh` if not first, else `0.0`) | `0.0 <= p_gap <= 0.12 * xh` |
| `cursor_x` | `float` | Horizontal coordinate accumulator for stroke placement | `cursor_x >= 0.0` |

### 1.2 OpticalGlyphMetrics
Represents the physical geometric boundary of a rendered glyph or stroke collection, computed purely from point coordinates rather than recorded font metadata.

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `min_x` | `float` | Leftmost horizontal stroke coordinate | Normalized to `0.0` upon alignment |
| `max_x` | `float` | Rightmost horizontal stroke coordinate | `max_x >= min_x` |
| `min_y` | `float` | Topmost vertical coordinate (negative upwards) | `min_y < max_y` |
| `max_y` | `float` | Bottommost vertical coordinate (baseline at `0.0`) | Baseline: `abs(max_y) <= 0.08 * xh` |
| `glyph_w` | `float` | Optical visual width (`max_x - min_x`) | `glyph_w >= 0.0` |
| `glyph_h` | `float` | Optical visual height (`max_y - min_y`) | `1.05 * xh <= glyph_h <= 1.30 * xh` for digits/% |

### 1.3 VectorGlyphFallback
Defines the fallback geometric definition for characters missing from the handwriting bank (e.g. `-`, `%`).

| Attribute | Type | Description | Target Specification |
| :--- | :--- | :--- | :--- |
| `s` | `list[list[float]]` | Polyline stroke point array `[[x0, y0, x1, y1, ...]]` | Scaled to match current `xh` |
| `w` | `float` | Natural advance width | `-`: `0.5 * xh`; `%`: `0.8 * xh` |
| `mid_y` | `float` | Vertical center coordinate | `-`: `-0.45 * xh` (tolerance `0.15 * xh`) |
| `baseline_y` | `float` | Lowest stroke point | `%`: `0.0` (tolerance `0.08 * xh`) |

### 1.4 SyntheticBankFixture
Defines the structure of the anonymized fallback handwriting bank stored in `tests/data/kho_mau_tong_hop.json.gz`.

| Section | Content | Requirement |
| :--- | :--- | :--- |
| `schema_version` | `str` / `int` | Valid schema version identifier |
| `xh` | `float` | Reference x-height (`7.0`) |
| `digits` | `dict[str, list[dict]]` | Must contain samples for `'0'` through `'9'` |
| `punct` | `dict[str, list[dict]]` | Must contain samples for `'-'`, `','`, `'.' `, `'!'`, `'?'`, `'('`, `')'`, `'%'` |
| `symbols` | `dict[str, list[dict]]` | Mathematical comparison and operator symbols |
| `words` | `dict[str, list[dict]]` | Anonymized calibration words |

---

## 2. Invariants & Validation Rules

1. **INV-001 (Minus Centering)**:
   For any minus sign rendered within `Writer.number()`, the midpoint `(min_y + max_y) / 2.0` MUST satisfy:
   `abs(mid_y - (-0.45 * xh)) <= 0.15 * xh`
   and `max_y < -0.10 * xh` (cannot drag onto the baseline).

2. **INV-002 (Percentage Normalization)**:
   For any percentage symbol rendered via `Writer.number()` or `Writer.token("%")`:
   `abs(max_y) <= 0.08 * xh` (baseline contact)
   `1.05 * xh <= (max_y - min_y) <= 1.30 * xh` (digit lining height).

3. **INV-003 (Decimal Comma Clearance)**:
   In any decimal sequence (e.g. `0,39`), the gap between the comma's right bounding edge and the following digit's left bounding edge MUST satisfy:
   `0.08 * xh <= gap_after_comma <= 0.14 * xh`.

4. **INV-004 (Measurement Parity)**:
   For any numeric string `S` matching `NUMRE`:
   `abs(Writer.measure_text_width(S) - Writer.number(S)[1]) <= 0.05 * xh`.

5. **INV-005 (Zero Missing Operator Invariant)**:
   When rendering numbers matching `NUMRE` on any bank with standard digits, `missing` returned by `Writer.number()` MUST NOT contain `'-'` or `'%'`.
