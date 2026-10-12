# Contract: Anti-Collision Line Spacing & Height Resolution

**Contract ID**: `CTR-034-LINE-HEIGHT-POLICY`  
**Target Modules**: [`chuviettay/layout/engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py), [`chuviettay/layout/table_layout.py`](file:///d:/viet/app/chuviettay/layout/table_layout.py), [`webapp/index.html`](file:///d:/viet/app/webapp/index.html)

---

## 1. Specification

### 1.1 Resolution Function
Given:
- `opts.line`: User-supplied line height parameter (float or None).
- `bank`: Loaded handwriting sample bank containing `bank.xh` and `bank.d["line"]`.
- `S`: Effective scale factor.

The engine MUST resolve `effective_line_h` as follows:
```python
font_xh = float(getattr(bank, "xh", 7.94) or 7.94)
default_bank_line = float(bank.d.get("line", 24.0)) * S
safe_line_floor = max(1.4 * font_xh * S, 0.65 * default_bank_line)

if opts.line is None:
    effective_line_h = default_bank_line
elif 0.0 < opts.line < safe_line_floor:
    # Người dùng nhập khoảng cách dòng nhỏ (ví dụ 1pt) -> coi là extra leading/inter-line gap
    effective_line_h = safe_line_floor + opts.line
else:
    effective_line_h = max(safe_line_floor, opts.line)
```

### 1.2 Invariants
1. For any `opts.line > 0.0`, `effective_line_h >= safe_line_floor`.
2. The vertical distance between consecutive baselines in paragraphs is at least `effective_line_h`.
3. In tables, `table_engine.line_height >= safe_line_floor`.
4. In tables, `min_row_height >= safe_line_floor + 2 * cell_padding`.
5. Horizontal border strokes MUST NEVER intersect with cell text bounding boxes.
