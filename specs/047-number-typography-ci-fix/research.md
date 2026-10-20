# Research & Architectural Decisions: Number Typography and CI Fallback Hardening

**Feature**: `047-number-typography-ci-fix` | **Date**: 2026-10-20

## 1. Vector Glyph Fallback for Minus (`-`) and Percent (`%`) in Number Contexts

### Problem
When rendering negative numbers (e.g. `"-25"`, `"-5"`) or percentage quantities (e.g. `"25%"`), `Writer.number()` queries the active handwriting bank for glyph samples via `bank.digits`, `bank.punct`, `bank.symbols`, or `bank.words`. In minimalist user banks, newly generated banks, or synthetic test fixtures (such as `tests/data/kho_mau_tong_hop.json.gz`), samples for `-` or `%` may not exist. When absent, `Writer.number()` records the character in `missing` and skips rendering it entirely, leading to missing operators and assertion failures in tests like `test_minus_and_percent_digit_normalization`.

### Decision
Enhance `Writer.number()` to incorporate fallback glyph resolution via `get_vector_glyph_fallback()` from `chuviettay.model.text_utils`:
1. When `ch == "-"` and no sample exists in `bank.digits`, `bank.punct`, `bank.symbols`, or `bank.words`:
   - Retrieve the vector fallback sample via `get_vector_glyph_fallback("-", xh)`.
   - The fallback sample provides a stroke at `y = -0.45 * xh` with width `0.5 * xh`.
   - Normalize it using `_normalize_digit_sample(fb_sample, "-")` to ensure vertical alignment at the mathematical center axis (`-0.45 * xh`).
   - Do NOT append `"-"` to `missing` when a valid vector fallback is generated.
2. When `ch == "%"` and no sample exists:
   - Provide a vector glyph fallback for `%` in `get_vector_glyph_fallback("%", xh)` with baseline `y = 0.0` and height `1.20 * xh`.
   - Normalize it using `_normalize_digit_sample(fb_sample, "%")` so it meets lining digit criteria (`abs(max_y) <= 0.08 * xh` and `1.05 * xh <= h <= 1.30 * xh`).
   - When `Writer.token("%")` is called, route single `%` through `Writer.number("%")`, utilizing the same normalized representation.

### Rationale
- Vector glyphs are native stroke arrays (`list[list[float]]`), matching the format of handwriting bank samples and requiring zero external dependencies.
- Centering the minus sign at `y = -0.45 * xh` matches mathematical typesetting standards (halfway up uppercase/digit height).
- Gracefully handling missing glyphs prevents document rendering failure on incomplete user banks.

### Alternatives Considered
- *Strict failure on missing punctuation*: Rejected because user handwriting banks often lack symbols, and dropping arithmetic operators ruins document readability.
- *Duplicating SVG path definitions*: Rejected because `get_vector_glyph_fallback()` already defines standard geometric strokes for mathematical and programming symbols in `text_utils.py`.

---

## 2. Optical Comma Spacing Harmony in Decimal Numbers

### Problem
In `Writer.number()`, decimal separators (`ch in ",."`) were advanced by `p_w` derived from `_normalize_punct_sample(g)`. In handwriting banks, punctuation instances typically record an advance width `w` intended for sentence spacing (e.g. `w = 4.0` in `kho_mau_tong_hop.json.gz`), which includes generous trailing space.
In decimal numbers (e.g. `"0,39"`, `"0,0278"`), applying sentence-level advance caused the post-comma gap (`gap_after_comma`) to expand to `4.7`, violating the required harmony bound of `[0.08 * xh, 0.14 * xh]` (`0.56 .. 0.98` for `xh = 7.0`).

### Decision
In `Writer.number()`, decouple numeric decimal separator advance from sentence punctuation padding:
1. Determine the optical bounding box width of the comma/period stroke:
   `glyph_w = (max_x - min_x)` of the normalized stroke `p_st`.
2. Advance the cursor strictly by:
   `x += p_gap + glyph_w + 0.10 * xh`
3. With subsequent digits placed at `x_next = x` (since `first = True` zeroes the subsequent `dgap`), the physical gap between the comma's right bounding edge and the next digit's left edge is exactly:
   `gap_after_comma = (x_before + p_gap + glyph_w + 0.10 * xh) - (x_before + p_gap + glyph_w) = 0.10 * xh`
4. Because `0.10 * xh` lies squarely within `[0.08 * xh, 0.14 * xh]`, this guarantees optical harmony across all banks regardless of recorded `inst["w"]`.

### Rationale
- In typographic design, decimal punctuation is an inline separator between digits, not a grammatical clause break.
- Basing the advance on the optical stroke width `glyph_w` plus a fixed proportional fraction `0.10 * xh` provides robust, reproducible layout regardless of input font inconsistencies.

### Alternatives Considered
- *Modifying `_normalize_punct_sample` directly*: Rejected because `_normalize_punct_sample` is shared by `Writer.token()` for prose text punctuation; shrinking `effective_w` globally would compress sentence punctuation spacing.
- *Hardcoding pixel offsets*: Rejected because all layout rules in `chuviettay` must scale proportionally with `xh`.

---

## 3. Synchronization Between `measure_text_width()` and `Writer.number()`

### Problem
`Writer.measure_text_width()` provides ahead-of-time width estimation for text nodes and table cells.
In `test_measure_text_width_number_sync`, `measure_text_width("-5")` returned `9.212` while `number("-5")` returned `4.382` (diff `4.83 > 0.05 * xh`).
The desynchronization occurred because:
1. `measure_text_width("-5")` included the fallback advance width for `-` (`0.6 * xh` + gap), whereas `number("-5")` omitted `-` completely due to missing bank glyphs.
2. For decimal numbers, `measure_text_width()` added `cw = self.get_char_advance_width(ch)` which returned sentence advance `p_w` (4.0), whereas `number()` should use optical `glyph_w`.

### Decision
Synchronize `measure_text_width()` and `number()`:
1. For `-` in numbers:
   - Ensure `get_char_advance_width("-")` returns `0.5 * xh` when using vector fallback, matching the optical advance produced by `Writer.number()`.
2. For `,` and `.` in numbers:
   - In `measure_text_width()`, within the `NUMRE.match()` branch, compute the advance for `,` and `.` using the optical glyph width:
     ```python
     sample = lib[0] if lib else None
     glyph_w = (max_x - min_x) if sample else 0.2 * xh
     tot += p_gap + glyph_w + 0.10 * xh
     ```
3. This ensures the advance width computed during layout measurement perfectly mirrors the stroke placement in `Writer.number()`, keeping difference `<= 0.05 * xh`.

### Rationale
- Mathematical formula layout, inline text flow, and table column auto-sizing depend on exact width parity. Discrepancies lead to cell clipping or unwanted line wraps.

---

## 4. Synthetic Test Bank Integrity (`tests/data/kho_mau_tong_hop.json.gz`)

### Problem
According to `conftest.py` and Constitution Principle III, tests must never depend on uncommitted developer-local files (`local data/kho_mau_v4.json.gz`).
However, `tests/data/kho_mau_tong_hop.json.gz` was generated without `-` and `%` samples in `punct`, and with an uncalibrated comma `w = 4.0`.

### Decision
1. Update `scripts/gen_synthetic_bank.py`:
   - In `generate_synthetic_bank()`:
     - Add `"-"`: `make_sample(3.5, [[0.5, -xh * 0.45, 3.5, -xh * 0.45]])`.
     - Add `"%"`: `make_sample(5.0, [[1.0, -xh * 1.1, 4.0, 0.0], [1.5, -xh * 0.9, 1.8, -xh * 0.9], [3.2, -xh * 0.2, 3.5, -xh * 0.2]])`.
     - Calibrate `","`: `make_sample(1.5, [[1.0, 0.0, 1.0, 1.5]])`.
2. Re-run `scripts/gen_synthetic_bank.py` to regenerate `tests/data/kho_mau_tong_hop.json.gz`.
3. In `tests/test_number_fraction_typography.py` and `tests/test_system_hardening_feature_046.py`, ensure `sample_bank_v4` fixture reliably uses `tests/data/kho_mau_tong_hop.json.gz` when local data is absent, validating the exact environment executed by CI.

### Rationale
- Self-contained fixtures guarantee 100% reproducible test runs in CI and on any contributor's machine.
