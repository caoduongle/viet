# Research & Architectural Decisions: High-Fidelity Letter Assembly Quality

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](./spec.md)  
**Status**: Completed  

---

## Executive Summary & Root Cause Findings

Investigation of the attached dataset (`local data/kho_mau_ky_tu.json.gz`, `local data/luoi_ky_tu_de_viet.xopp`, `local data/2026-09-20-Note-17-02.xopp`, `local data/anhloi.png`) and the commit history (`c00ec69`) established five fundamental root causes for synthesis defects:

1. **Advance Subtraction Overlap (`w - overlap`)**: `Writer.assemble_word` advanced character positions using `advance = max(0.2*xh, w - overlap)`. Because raw letter samples store bounding box width without side padding, subtracting overlap forced each subsequent character's bounding box into the preceding character's bounding box. With a 1.41pt pen on 3.5pt-wide glyphs, this eliminated any whitespace gap and caused immediate stroke intersections.
2. **Ink Pooling ("Cục mực") due to Extreme Pen/Height Ratio**: Raw letter samples in the grid were drawn with small physical heights (3.4–5.4pt) using a 1.41pt pen. This created an abnormal pen-to-height ratio of 26%–41% (compared to ~16% in authentic note writing). Without stroke thickness scaling or x-height normalization, scaling up coordinates failed to restore realistic stroke proportions.
3. **Uneven Baseline and Mismatched Letter Heights**: In the raw collection grid, different letters varied wildly in height (e.g. `a, u, o` ≈ 3.4–3.8pt while `v, n, c` ≈ 5.4pt). Assembled words had jagged baselines and jarring visual rhythm.
4. **Investigation of Missing Accented Words vs Error Image (Item 3.6 Resolution)**:
   - `kho_mau_ky_tu.json.gz` contains 178 single-character keys in `words` (Schema v3), containing base letters AND all precomposed accented Vietnamese letters (`à, á, â, ã, è, é... ớ, ờ, ở, ỡ, ợ, ụ, ủ, ứng, ừ...`), but `marks` has 0 tone marks.
   - In commit `c00ec69`, `split_letters` was implemented to strip tone marks (`unaccented = strip_tone(word)`), and `assemble_word` strictly required `self.b.marks.get(T)`. When running `c00ec69` on `kho_mau_ky_tu.json.gz`, all 28 accented words in `accept_sample.txt` were dropped and left blank.
   - The error image `anhloi.png` showed all accented words ("Lời", "giải", "Phần", "Bài", "Chạy"...) because it was generated from a prototype that mapped characters directly without stripping tones (`for ch in word: lib = bank.words.get(ch)`).
   - In addition, legacy `find_tone` used hardcoded thresholds calibrated to `xh=7`, failing on 28/120 accented letters when attempting to harvest tone marks from small handwriting samples.
5. **Collection Grid Ambiguity**: The existing 206-cell grid lacked side margins, ascender/descender guidelines, and Vietnamese font support for accented labels.

---

## Detailed Research Decisions

### Decision 1: Boundary Contour Kerning & Stroke Clearance Floor

**Context**: Replacing `advance = max(0.2*xh, w - overlap)` to prevent touching and overlapping letters.

**Decision**:
1. Calculate Left Side Bearing (`lsb`) and Right Side Bearing (`rsb`) for each character during ingestion/migration.
2. Classify character lateral boundaries into contour types:
   - `CURVED`: `o, c, e, d, q` (outer curve allows closer optical spacing).
   - `STRAIGHT`: `l, i, n, m, u, h, b, k` (vertical stems require standard optical separation).
   - `OPEN` / `SLANTED`: `r, v, w, x, y, t` (open diagonals provide natural negative space).
3. Compute advance between character $A$ and character $B$:
   $$\text{advance} = A.\text{w} + A.\text{rsb} + \text{contour\_pair\_gap}(A.\text{right}, B.\text{left}) + B.\text{lsb}$$
4. Enforce an invariant physical clearance floor:
   $$\text{min\_distance}(\text{strokes}(A), \text{strokes}(B)) \ge k \times \text{pen\_thickness} \quad (k \approx 0.8)$$
   If post-placement distance is less than the clearance floor, shift $B$ rightward until the constraint is satisfied.
5. Cap bounding box overlap to $\le 10\%$ of $\min(\text{width}(A), \text{width}(B))$.

**Rationale**:
Side bearings combined with contour categories provide professional typographical spacing. The physical stroke clearance floor guarantees mathematically that no two letters can ever touch or blur into an ink blob regardless of glyph quirks or jitter.

**Alternatives Considered**:
- *Convex Hull Kerning*: Accurately models exact stroke contours but has $O(N^2)$ point-checking overhead per character pair and requires external computational geometry libraries (violating the zero-dependency rule).
- *Simple Constant Margin Floor*: Adding a fixed constant gap (e.g. +2pt) works for straight letters but makes curved letters like `oo` look disconnected.

---

### Decision 2: Target x-Height Normalization & Dynamic Stroke Scaling

**Context**: Eliminating "cục mực" (ink pooling) and jagged letter heights.

**Decision**:
1. Measure the authentic median x-height ($xh_{\text{target}}$) and pen-to-x-height ratio ($R_{\text{target}} \approx 0.16$) from `2026-09-20-Note-17-02.xopp` using `tools/measure_ink.py` in Phase 0.
2. Group characters into normalization classes:
   - `X_HEIGHT`: `a, c, e, m, n, o, r, s, u, v, x, z, ă, â, ê, ô, ơ, ư`
   - `ASCENDER`: `b, d, h, k, l, t, đ`
   - `DESCENDER`: `g, p, q, y`
   - `UPPERCASE`: `A-Y`
   - `PUNCT_SYM`: `. , ; : ! ? - ( ) _ >= <`
3. Normalize each letter sample:
   - Scale factor: $s_y = \frac{xh_{\text{target}}}{h_{\text{sample}}}$.
   - Uniform scaling $s_x = s_y$ to preserve aspect ratio.
   - Translate strokes so baseline sits at $y = 0$.
4. When rendering at document scale factor $S$:
   $$\text{effective\_pen\_width} = \text{base\_pen} \times S \times \frac{R_{\text{target}}}{\text{raw\_ratio}}$$
   ensuring the visual stroke weight remains in harmony with note handwriting.

**Rationale**:
Uniform scaling with baseline anchoring aligns characters neatly along the reading line while preserving the writer's authentic personal slant and aspect ratio. Dynamic stroke scaling prevents letters from thickening into blobs when rendered at small scale.

**Alternatives Considered**:
- *Independent X/Y Scaling*: Stretches letters to uniform width and height. Rejected because it destroys personal handwriting style and introduces severe geometric distortion.
- *Strict Box Bounding*: Scaling all letters to fit an arbitrary bounding box. Rejected because ascenders (`h, l`) and descenders (`g, y`) must extend beyond x-height.

---

### Decision 3: Dual-Path Vietnamese Assembly & Grid-Aware Tone Extraction

**Context**: Restoring assembly for accented Vietnamese words while supporting both decomposed tone marks and precomposed glyphs.

**Decision**:
1. **Dual-Path Assembly Cascade**:
   - *Path 1 (Precomposed Glyph Match)*: If an accented character (e.g., `ờ`, `à`, `ạ`, `é`) exists directly in `bank.letters` or `bank.words`, use its handwritten sample directly. This ensures immediate 100% coverage for the 178 precomposed samples in the user's existing bank.
   - *Path 2 (Decomposed Base + Tone Mark)*: If no precomposed sample exists, split into unaccented base vowel and tone mark $T \in \{/, \backslash, ?, \sim, .\}$. Look up base vowel in `bank.letters` and tone mark in `bank.marks`.
2. **Grid-Aware Migration (`scripts/migrate_letter_bank.py`)**:
   - Since the collection grid specifies the exact label for every cell (e.g. cell `á`), the migration utility does not rely on fragile heuristic geometry.
   - It isolates the base vowel stroke(s) and tone mark stroke(s) using relative height partitions based on the sample's actual height, populating both `bank.letters` and `bank.marks` with calibrated offsets $(\Delta x, \Delta y)$.
3. **Collision-Free Tone Attachment**:
   - Vowel centroid: $cx = \frac{\text{bbox}[0] + \text{bbox}[2]}{2}$.
   - Lower tone (nặng): placed at $y = \max(0, \text{bottom}) + \Delta y$.
   - Upper tone (sắc, huyền, hỏi, ngã): placed above the vowel peak $\min(y) - \Delta y$.
   - Collision clearance: If neighboring character has an ascender within horizontal distance $< 0.5 \times xh$, adjust tone mark placement horizontally away from the ascender.
   - Dot suppression: If vowel is `i` or `j` and an upper tone is applied, the tittle stroke (identified by $y < -0.85 \times xh$ and small width) is omitted.

**Rationale**:
Dual-path assembly guarantees instant backward compatibility with precomposed single-letter banks while enabling future modular assembly from decomposed marks. Grid-aware migration eliminates the failure mode where 28 accented characters were unharvestable by legacy heuristic thresholding.

**Alternatives Considered**:
- *Strict Decomposed Only*: Forcing all words through base vowel + tone mark. Rejected because precomposed characters written by the user capture natural ligatures between vowel hats/horns and accents.

---

### Decision 4: Redesigned Collection Grid Template (`hw3`)

**Context**: Providing unambiguous guidelines on handwriting collection sheets.

**Decision**:
1. Introduce template identifier `hw3` (preserving full compatibility with legacy `hw2`/`hw2c`).
2. Implement 4 horizontal reference lines:
   - Baseline ($y = 0$)
   - x-height line ($y = -xh_{\text{target}}$)
   - Ascender guide line ($y = -asc$)
   - Descender guide line ($y = +desc$)
3. Implement 2 vertical margin boundaries per cell:
   - Left boundary and right boundary designating the inner writing box, allowing the learning engine to directly compute `lsb` and `rsb`.
4. Layout: 2–3 cells per letter (to capture natural handwriting variation) plus 15 high-frequency Vietnamese digraphs (`ng, nh, ch, tr, ph, th, kh, gi, qu, ươ, ưa, uy, ay, oa`).
5. Render cell prompt labels using vector glyph strokes or guaranteed system font fallback so unicode diacritics (`ă, â, đ, ê, ô, ơ, ư`) never render as square missing-glyph boxes (□).
6. Embed concise Vietnamese instructions directly on each page of the sheet.

**Rationale**:
Providing 4 guide lines and explicit vertical margins eliminates writer ambiguity and ensures that scanned or ingested handwriting is geometrically consistent from day one.

---

### Decision 5: Non-Destructive Migration & Strict Architecture Invariants

**Context**: Maintaining zero core dependencies, MVC separation, data safety, and golden-master byte parity.

**Decision**:
1. Migration script `scripts/migrate_letter_bank.py` outputs a new `.json.gz` file (e.g. `chu_cua_ban_v4.json.gz`), never mutating the input file.
2. In-memory Schema v4 migration in `chuviettay/model/bank_schema.py` loads legacy banks (v1–v3) transparently.
3. Multi-process concurrency safety: `letters` and `marks` participate in `merge_bank_dicts` under `FileLock` with generation tombstones.
4. Golden master byte invariance: `WriteOptions(assemble_letters=False)` retains 100% SHA-256 byte parity on whole-word synthesis benchmarks.
5. Zero core dependencies: All core model logic in `chuviettay/model` and `chuviettay/controller` strictly uses the Python standard library. Imaging libraries (Pillow, matplotlib) and scientific tools are restricted exclusively to `tools/` and optional test suites guarded by `pytest.importorskip`.

---

## Unknowns & Investigation Resolution Summary

| Item | Status | Finding & Resolution |
|---|---|---|
| **Advance overlap bug** | RESOLVED | Caused by `advance = max(0.2*xh, w - overlap)`. Replaced with side bearing + contour kerning + pen clearance floor. |
| **Ink pooling ("cục mực")** | RESOLVED | Caused by small sample height (3.5pt) drawn with 1.41pt pen. Resolved by x-height normalization and dynamic stroke width scaling. |
| **Accented words dropped** | RESOLVED | Caused by `c00ec69` requiring `marks[T]` while bank v3 had precomposed letters in `words`. Resolved by dual-path assembly (precomposed fallback + decomposed mark). |
| **Grid label square boxes (□)** | RESOLVED | Caused by default Tk/Xournal font lacking Vietnamese glyphs. Resolved by vector-rendered or verified unicode typography in `hw3`. |
| **Golden master parity** | RESOLVED | Guaranteed via default `assemble_letters=False`. |
