# Interface Contract: Number Typography & Fallback Engine

**Feature**: `047-number-typography-ci-fix` | **Date**: 2026-10-20

## 1. `Writer.number(s: str, ...)` Contract

### Signature
```python
def number(
    self,
    s: str,
    k: int | None = None,
    context: SeedContext | None = None,
    _preserve_context: bool = False,
) -> tuple[list[Stroke], float, list[str]]:
    ...
```

### Preconditions
- `s` is a non-empty string adhering to `NUMRE` syntax (`^[+-]?\d+(?:[,.]\d+)*(?:%)?$`).
- `self.b` is an instance of `Bank`.

### Postconditions & Invariants
1. **Return Tuple**: `(strokes, total_width, missing)`
2. **Missing Characters (`missing`)**:
   - If `s` contains `-` and `self.b` lacks `-`, `Writer.number()` synthesizes a vector fallback minus. `missing` MUST NOT contain `'-'`.
   - If `s` contains `%` and `self.b` lacks `%`, `Writer.number()` synthesizes a vector fallback percent. `missing` MUST NOT contain `'%'`.
3. **Minus Sign Geometry**:
   - When `-` is present at index 0, its strokes are positioned such that:
     `abs(((min_y + max_y) / 2.0) - (-0.45 * xh)) <= 0.15 * xh`
     and `max_y < -0.10 * xh`.
4. **Decimal Separator Geometry**:
   - When `ch in ",."` is followed by a digit at index `d_idx + 1`:
     The geometric horizontal distance between the rightmost stroke point of the separator and the leftmost stroke point of the subsequent digit is within `[0.08 * xh, 0.14 * xh]`.
5. **Total Width (`total_width`)**:
   - Matches the actual span of rendered strokes plus appropriate trailing advance.

---

## 2. `Writer.measure_text_width(text: str, scale: float = 1.0) -> float` Contract

### Signature
```python
def measure_text_width(self, text: str, scale: float = 1.0) -> float:
    ...
```

### Invariants for Numeric Strings
For any string `text` where `NUMRE.match(text)` is truthy:
```python
strokes, rendered_w, _ = self.number(text)
measured_w = self.measure_text_width(text)
assert abs(measured_w - rendered_w) <= 0.05 * xh
```
This invariant MUST hold for:
- Pure integers (`"123"`, `"2026"`)
- Negative integers (`"-5"`, `"-25"`)
- Decimal numbers (`"0,39"`, `"0,0278"`, `"123,45"`)
- Negative decimals (`"-123,45"`)
- Percentage quantities (`"25%"`)

---

## 3. `get_vector_glyph_fallback(token: str, xh: float = 7.94) -> dict[str, Any] | None` Contract

### Signatures & Supported Tokens
```python
def get_vector_glyph_fallback(token: str, xh: float = 7.94) -> dict[str, Any] | None:
    ...
```

### Supported Fallback Tokens
1. `token == "-"`:
   - Stroke: Horizontal line centered at `y = -0.45 * xh`
   - Advance `w`: `0.5 * xh`
2. `token == "%"`:
   - Stroke: Diagonal bar from `(1.0 * xh * scale, -1.1 * xh)` to `(4.0 * xh * scale, 0.0)`, plus two loop dots
   - Baseline: `max_y` aligns with `0.0` (within `0.08 * xh`)
   - Height: `1.05 * xh <= h <= 1.30 * xh`
   - Advance `w`: `0.8 * xh`

---

## 4. Synthetic Bank Fixture Contract (`kho_mau_tong_hop.json.gz`)

### Requirements
The file `tests/data/kho_mau_tong_hop.json.gz` MUST contain:
1. `digits`: All characters `'0'` through `'9'`.
2. `punct`:
   - `"-"`: Valid stroke sample centered vertically.
   - `","`: Valid comma stroke with clean width (`w <= 2.0`).
   - `"."`: Valid period stroke with clean width (`w <= 2.0`).
   - `"%"`: Valid percent sample with baseline alignment.
   - `'!'`, `'?'`, `'('`, `')'`: Standard punctuation samples.
