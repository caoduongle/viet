# Contract: Natural Math Accent Placement & Bounded Ascent Metrics

**Contract ID**: `CTR-034-MATH-ACCENT-PLACEMENT`  
**Target Modules**: [`chuviettay/layout/math_layout.py`](file:///d:/viet/app/chuviettay/layout/math_layout.py), [`chuviettay/layout/vector_glyphs.py`](file:///d:/viet/app/chuviettay/layout/vector_glyphs.py)

---

## 1. Specification

### 1.1 Placement Offsets
For an `Accent` node placed above base element `base`:
- `xh = self.xh * eff`
- `wb = max(base.size.width, 1.0 * eff)`

| Accent Kind | Command | Optical Gap | Polyline Height | Visual Placement |
| :--- | :--- | :--- | :--- | :--- |
| `bar` | `\bar`, `\overline` | $0.08 \times xh$ | $0.16 \times xh$ | Straight horizontal segment directly above glyph top |
| `hat` | `\hat`, `\widehat` | $0.06 \times xh$ | $0.28 \times xh$ | Compact chevron centered above base |
| `tilde` | `\tilde`, `\widetilde` | $0.06 \times xh$ | $0.24 \times xh$ | Compact sine wave above base |
| `dot` | `\dot` | $0.08 \times xh$ | $0.20 \times xh$ | Single circular point centered above base |
| `ddot` | `\ddot` | $0.08 \times xh$ | $0.20 \times xh$ | Two points horizontally spaced |
| `vec` | `\vec` | $0.10 \times xh$ | $0.35 \times xh$ | Compact horizontal arrow above base |

### 1.2 Coordinate Calculation
```python
if kind in _UNDER_ACCENTS:
    y0 = base.size.descent + gap
    descent = y0 + height
    ascent = base.size.ascent
else:
    y0 = -(base.size.ascent + gap + height)
    # Tinh chỉnh ascent báo về layout để tránh làm phình extra_top
    ascent = -y0
```

### 1.3 Invariants
1. For variable symbols ($\bar{x}, \hat{x}, \bar{y}$), the distance between the topmost point of the base letter and the accent stroke MUST satisfy:
   $$0.05 \times xh \le d_{\text{gap}} \le 0.20 \times xh$$
2. Accented lowercase characters MUST NOT cause an artificial line jump exceeding $0.3 \times \text{line\_height}$.
