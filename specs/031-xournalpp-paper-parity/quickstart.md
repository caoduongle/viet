# Quickstart Validation Guide: Xournal++ Paper Background and Geometry Parity

**Feature Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11
**Spec**: [spec.md](spec.md)

This runnable guide verifies the 5 primary objectives of this feature end-to-end.

---

## 1. Prerequisites

Activate environment and confirm dependencies:
```bash
py -3.12 -m pip install -r requirements-dev.txt
npm install
```

---

## 2. Validation Scenarios

### Scenario 1: PDF Background Domain and 1-Based Pageno Check
Validate that generated `.xopp` documents use `pageno="1"` (for page 0), `domain="absolute"`, and that `domain="relative"` is completely absent.

```bash
# Run targeted unit tests
py -3.12 -m pytest tests/test_docx_fidelity.py -k "pdf_background" -v

# Codebase audit: must return 0 results
git grep 'domain="relative"'
```
**Expected Outcome**: Tests pass cleanly, grep returns empty.

---

### Scenario 2: Web Preview Geometry Verification
Validate that web SVG background generation correctly renders Ruled, Lined (including negative $m_1$), Graph, Dotted, Isometric, and Staves with proper line counts, bounds, and contrast colors.

```bash
# Run Playwright / Web unit tests
npm run test:unit
```
**Expected Outcome**: Web SVG tests pass, asserting line coordinates $y \in [80, \text{height}-60]$, staff spacing, and negative margin $x = \text{width} + m_1$.

---

### Scenario 3: Baseline Ruling Snapping and Golden Master Invariance
Verify that text lines snap baselines to $y = 80 + k \cdot \text{pitch}$ on ruled paper while preserving byte-identical output for plain paper.

```bash
# Verify golden master plain paper hash unchanged
py -3.12 -m pytest tests/test_golden_master.py -v

# Verify ruling snapping logic on ruled and lined paper
py -3.12 -m pytest tests/test_paper_ruling_snap.py -v
```
**Expected Outcome**: Golden master hash is identical. Snapping test confirms baselines match $80 + k \cdot r_1$.

---

### Scenario 4: PageBackground XML Serialization and Preset Catalog
Verify XML config attribute format, negative $m_1$ support, and CLI preset parameters.

```bash
# Verify PageBackground serialization and negative margin
py -3.12 -m pytest tests/test_paper_size_background.py -v

# Test CLI with background presets and overrides
py -3.12 -m chuviettay write "Thử nghiệm giấy ô li" --bg-preset lined_college --bg-m1 "-72pt" -o test_preset.xopp
```
**Expected Outcome**: File `test_preset.xopp` contains `<background ... style="lined" config="...m1=-72.0..."/>`.

---

### Scenario 5: Full Test Suite Green Gate
```bash
py -3.12 -m pytest -q --timeout=60
```
**Expected Outcome**: All 1,200+ unit and integration tests pass with zero failures.
