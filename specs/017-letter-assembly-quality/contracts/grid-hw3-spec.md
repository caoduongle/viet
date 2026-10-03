# Contract: Handwriting Grid Template Specification (`hw3`)

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](../spec.md)  
**Status**: Active  

---

## 1. Overview & Header Identification

The `hw3` format extends the printable Xournal++ handwriting collection template. The ingestion engine identifies template format by reading the metadata tag embedded in the first layer:
- `hw2`: Legacy 206-cell grid with baseline and x-height.
- `hw3`: Enhanced collection grid with 4 reference guide rules, 2 vertical margin boundaries, and explicit Vietnamese instructions.

---

## 2. Cell Geometry & Reference Guidelines

Each cell is a rectangular capture area with the following coordinate definitions relative to the top-left corner of the cell $(x_0, y_0)$:

| Guideline | Offset from Cell Top | Meaning | Visual Style in XML |
|---|---|---|---|
| **Ascender Line** | $y_0 + 20.0\,\text{pt}$ | Max height for $b, d, h, k, l, \text{Capitals}$ | `#e0e0e0`, width 0.5, dashed |
| **x-Height Line** | $y_0 + 25.4\,\text{pt}$ | Target top of lowercase vowels & consonants | `#c8c8c8`, width 0.75, solid |
| **Baseline** | $y_0 + 34.0\,\text{pt}$ | Ground line where letters sit ($y = 0$) | `#a0a0a0`, width 1.0, solid |
| **Descender Line** | $y_0 + 44.0\,\text{pt}$ | Lower limit for $g, p, q, y$ | `#e0e0e0`, width 0.5, dashed |
| **Left Margin** | $x_0 + 12.0\,\text{pt}$ | Left margin boundary | `#d8d8d8`, width 0.5, vertical |
| **Right Margin** | $x_0 + 116.0\,\text{pt}$ | Right margin boundary | `#d8d8d8`, width 0.5, vertical |

---

## 3. Cell Ingestion Contract

When the learning command processes an `hw3` cell:
1. Filter out all strokes whose color matches guideline markers (`#a0a0a0`, `#c8c8c8`, `#d8d8d8`, `#e0e0e0`).
2. Calculate Left Side Bearing: $\text{lsb} = \max(0.0, \min(x) - (x_0 + 12.0))$.
3. Calculate Right Side Bearing: $\text{rsb} = \max(0.0, (x_0 + 116.0) - \max(x))$.
4. Calculate Baseline Alignment: $\Delta y = y_{\text{baseline}} - \text{base\_point}$.
5. Warn if strokes cross outer cell boundaries or if stroke count is 0.
