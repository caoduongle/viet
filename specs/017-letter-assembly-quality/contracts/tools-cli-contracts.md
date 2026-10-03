# Contract: Tools & CLI Interfaces

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](../spec.md)  
**Status**: Active  

---

## 1. CLI Synthesis Commands (`hw_note.py`)

### 1.1 Extended Options for `write`

```bash
python hw_note.py [--bank BANK_PATH] write -f INPUT_FILE -o OUTPUT_XOPP [OPTIONS]
```

**New & Updated Flags**:
- `--assemble`: Enable dynamic letter-level fallback synthesis.
- `--letter-gap FLOAT`: Multiplier for inter-letter kerning clearance (default: `1.0`).
- `--target-xh FLOAT`: Explicit target x-height in points (e.g. `8.6`).
- `--auto-xh`: Automatically scale character heights to align with authentic handwriting profile.
- `--pen-clearance FLOAT`: Minimum stroke clearance floor as a fraction of pen thickness (default: `0.8`).

---

## 2. Bank Migration Tool (`scripts/migrate_letter_bank.py`)

```bash
python scripts/migrate_letter_bank.py --in INPUT_BANK.json.gz --out OUTPUT_BANK.json.gz [--grid GRID.xopp] [--target-xh FLOAT]
```

**Behavior**:
- Reads legacy bank (v1, v2, v3).
- Extracts single-character entries from `words` into `letters` (Schema v4).
- Calculates `lsb`, `rsb`, and contour categories.
- Normalizes x-height to `--target-xh` (default: 8.6).
- If `--grid` is supplied, extracts decomposed tone marks into `marks` using cell label information.
- Writes to `--out` atomically. **Never mutates `--in`**.

---

## 3. Ink Measurement Tool (`tools/measure_ink.py`)

```bash
python tools/measure_ink.py INPUT.xopp [--page INT] [--json]
```

**Outputs**:
- Statistical distribution of stroke heights and median x-height.
- Ratio of pen thickness to x-height.
- Median horizontal inter-letter and inter-word distances.
- Maximum and average adjacent bounding-box overlap ratio.
- Minimum stroke clearance floor violations.
- Standard deviation of lowercase x-height glyphs.

---

## 4. Visual Renderer Tool (`tools/render_xopp.py`)

```bash
python tools/render_xopp.py INPUT.xopp PAGE_IDX OUTPUT.png [--scale FLOAT] [--crop X0 Y0 X1 Y1]
```

**Behavior**:
- Parses Xournal++ XML from compressed or uncompressed `.xopp`.
- Renders vector strokes with exact line widths, colors, and line joins via Pillow.
- Allows optional cropping to specific lines or bounding boxes.
- Emits high-resolution PNG for automated regression analysis and visual inspection.
