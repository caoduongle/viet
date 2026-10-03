# Quickstart Validation Guide: Letter Assembly Quality

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](./spec.md)  
**Status**: Active  

---

## Prerequisites

1. Python 3.10+ installed with developer dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
2. Acceptance test fixture verified at [`tests/data/accept_sample.txt`](../../tests/data/accept_sample.txt).
3. Private test data placed in `local_data/` (or `local data/`, ignored by git):
   - `kho_mau_ky_tu.json.gz`
   - `luoi_ky_tu_de_viet.xopp`
   - `2026-09-20-Note-17-02.xopp`

---

## Validation Scenario 1: Baseline Ink Measurement (Phase 0)

Measure authentic reference handwriting metrics from the user's authentic note:

```bash
python tools/measure_ink.py "local data/2026-09-20-Note-17-02.xopp" --json > docs/do_luong_ban_goc.json
```

**Expected Outcome**:
- Emits structured metrics report: median x-height, pen-to-x-height ratio (~0.16), inter-letter gaps, and group height distributions.

---

## Validation Scenario 2: Visual Rendering Verification

Render page 0 of the note or test output to PNG:

```bash
python tools/render_xopp.py "local data/2026-09-20-Note-17-02.xopp" 0 /tmp/note_page0.png --scale 2.0
```

**Expected Outcome**:
- PNG image generated showing crisp strokes matching Xournal++ display.

---

## Validation Scenario 3: Bank Migration & Normalization (Phase 1)

Migrate legacy v3 single-letter bank to Schema v4 with normalized metrics and side bearings:

```bash
python scripts/migrate_letter_bank.py \
  --in "local data/kho_mau_ky_tu.json.gz" \
  --grid "local data/luoi_ky_tu_de_viet.xopp" \
  --out "local data/kho_mau_v4.json.gz" \
  --target-xh 8.6
```

**Expected Outcome**:
- Creates `kho_mau_v4.json.gz` without modifying the original bank.
- Populates `letters` with normalized bounding boxes, `lsb`, `rsb`, and `adv`.
- Populates `marks` with harvested tone marks.
- Reports zero data loss across the 178 initial keys.

---

## Validation Scenario 4: High-Fidelity Word Synthesis (Phase 2)

Synthesize the acceptance standard text using the upgraded letter assembly engine:

```bash
python hw_note.py --bank "local data/kho_mau_v4.json.gz" write \
  -f tests/data/accept_sample.txt \
  -o /tmp/accept_output.xopp \
  --assemble \
  --seed 1
```

**Expected Outcome**:
- All words ("Lời giải", "pipeline", "penguins", "body_mass_g", "Điều kiện lọc"...) synthesized with valid strokes.
- Zero silent missing-character omissions.
- Adjacent characters maintain clear visual separation without touching or overlapping blobs.

---

## Validation Scenario 5: Golden Master Byte Parity & Regression Suite (Phase 5)

Verify that legacy whole-word synthesis remains 100% byte-for-byte identical:

```bash
pytest tests/test_golden_master.py -v
pytest tests/test_letter_assembly.py -v
pytest --timeout=30
```

**Expected Outcome**:
- All golden master tests pass with 0 byte change.
- New invariant unit tests verify stroke clearance floor $\ge 0.8 \times \text{pen\_thickness}$ and bounding box overlap $\le 10\%$.
