# Data Model & Typography Geometry: Natural Number & Fraction Layout

**Feature**: `045-natural-number-fraction-layout`  
**Date**: 2026-10-20

## 1. Entities & Data Structures

### `NormalizedDigitGlyph`
Biểu diễn mẫu chữ số đã được chuẩn hóa đồng bộ về đường cơ sở (`baseline y = 0`), biên ngang bắt đầu từ `x = 0`, và tỷ lệ chiều cao đồng nhất theo chuẩn chữ số đồng cao (lining figures).

```python
@dataclass
class NormalizedDigitGlyph:
    strokes: list[Stroke]  # Nét đã dịch sao cho min_x = 0.0 và max_y = 0.0 (hoặc tâm -0.45*xh cho '-')
    advance_width: float  # Độ rộng tiến quang học của chữ số: (raw_max_x - raw_min_x) * scale_x
    visual_width: float   # Bề rộng thực của nét (max_x - min_x)
    height: float         # Chiều cao thực sau chuẩn hóa (max_y - min_y)
    scale_x: float        # Hệ số co giãn ngang
    scale_y: float        # Hệ số co giãn dọc chuẩn hóa chiều cao
```

**Quy tắc biến đổi hình học**:
1. Lấy tọa độ cực biên từ `raw_strokes`:
   - `raw_min_x = min(pt for st in raw_strokes for pt in st[0::2])`
   - `raw_max_x = max(pt for st in raw_strokes for pt in st[0::2])`
   - `raw_min_y = min(pt for st in raw_strokes for pt in st[1::2])`
   - `raw_max_y = max(pt for st in raw_strokes for pt in st[1::2])`
2. Phân loại ký tự:
   - **Trường hợp `ch == "-"` (dấu âm trong `bank.digits`)**:
     - `dx = -raw_min_x`
     - `mid_y = (raw_min_y + raw_max_y) / 2.0`
     - `dy = -0.45 * xh - mid_y` (căn tâm dọc tại trục toán học `-0.45 * xh`)
     - `scale_x = scale_y = 1.0`
   - **Trường hợp chữ số `"0"`–`"9"` và `"%"`**:
     - `dx = -raw_min_x`
     - `dy = -raw_max_y` (chân chữ số chạm đúng baseline `y = 0.0`)
     - Chiều cao mục tiêu: `target_h = 1.20 * xh`
     - `sample_h = raw_max_y - raw_min_y`
     - Nếu `sample_h > 1e-3` và (`sample_h < 1.14 * xh` hoặc `sample_h > 1.26 * xh`):
       - `scale_y = clamp(target_h / sample_h, 0.35, 1.85)`
       - `scale_x = clamp(scale_y ** 0.5, 0.75, 1.30)`
     - Ngược lại: `scale_x = scale_y = 1.0`
3. Sinh nét chuẩn hóa và độ rộng tiến:
   - `norm_strokes = [[round((pt + dx) * scale_x, 2) if i % 2 == 0 else round((pt + dy) * scale_y, 2) for i, pt in enumerate(st)] for st in raw_strokes]`
   - `bbox_w = (raw_max_x - raw_min_x) * scale_x`
   - `advance_width = bbox_w if bbox_w > 1e-3 else float(raw_w)` (không cộng lề phụ vào `advance_width` để khoảng hở giữa 2 chữ số bằng đúng `dgap`).

---

### `DigitSpacingModel`
Mô hình quy định dải khoảng cách an toàn và tự nhiên giữa các chữ số và quanh dấu thập phân.

```python
@dataclass(frozen=True)
class DigitSpacingModel:
    min_dgap_ratio: float = 0.10     # 0.10 * xh (~0.79 pt khi xh=7.94)
    max_dgap_ratio: float = 0.18     # 0.18 * xh (~1.43 pt khi xh=7.94)
    default_dgap_ratio: float = 0.12 # 0.12 * xh (~0.95 pt khi xh=7.94)
    decimal_pre_gap_ratio: float = 0.08  # Khoảng hở trước dấu phẩy thập phân
    decimal_post_gap_ratio: float = 0.10 # Khoảng hở sau dấu phẩy thập phân
```

**Quy tắc áp dụng trong `Writer.number(s)`**:
- Với ký tự đầu tiên: `x = 0.0`.
- Với các chữ số liên tiếp:
  - Nếu `b.d["dgaps"]` tồn tại: chọn giá trị `g` và chuẩn hóa:
    `dgap = clamp(float(g) * (xh / 7.94), min_dgap_ratio * xh, max_dgap_ratio * xh)`
  - Nếu không có: `dgap = default_dgap_ratio * xh`.
- Với dấu thập phân (`,` hoặc `.`):
  - Trước dấu thập phân: cộng `decimal_pre_gap_ratio * xh`.
  - Sau dấu thập phân: cộng `decimal_post_gap_ratio * xh`.
  - Chữ số kế tiếp sau dấu thập phân bắt đầu tại mốc này; các chữ số sau đó tiếp tục bước tiến bằng `dgap`.

---

### `CompactFractionGeometry`
Mô hình tính toán kích thước, khoảng hở quang học theo biên nét thực (`ink bounds`) và gạch phân số.

```python
@dataclass
class CompactFractionGeometry:
    child_scale: float       # Tỷ lệ co chữ số trong phân số (0.80 ở cấp ngoài; 0.78 khi lồng hoặc trong matrix/cases)
    clearance_gap: float     # Khoảng hở quang học từ biên nét tử/mẫu đến gạch phân số (0.20 * xh * eff)
    bar_overhang: float      # Độ dài gạch phân số nhô ra mỗi bên (0.18 * xh * eff)
    bar_y: float             # Tọa độ dọc của thanh gạch phân số (-math_axis)
    bar_thickness: float     # Bề dày nét gạch phân số (1.41 * eff)
```

**Quy tắc định vị phân số (`MathLayoutEngine._m_Fraction`)**:
1. Tính `num_item` và `den_item` với `child_scale = scale * (0.78 if (self._frac_level > 0 or self._matrix_level > 0) else 0.80)`.
2. Chiều rộng thanh gạch phân số:
   - `content_w = max(num_item.size.width, den_item.size.width)`
   - `overhang = (0.18 if node.bar else 0.08) * self.xh * eff`
   - `frac_w = content_w + 2.0 * overhang`
3. Trục toán học và định vị dọc theo biên nét thực (`ink bounds`):
   - `math_axis = 0.45 * self.xh * eff`
   - `gap = (0.20 if node.bar else 0.12) * self.xh * eff`
   - Đo biên dọc thực tế `(ink_top, ink_bot)` từ các nét (`glyphs` và `strokes`) của `num_item` và `den_item` (nếu rỗng thì fallback về `(-size.ascent, size.descent)`).
   - `num_x = (frac_w - num_item.size.width) / 2.0`
   - `num_y = -math_axis - gap - num_ink_bot`
   - `den_x = (frac_w - den_item.size.width) / 2.0`
   - `den_y = -math_axis + gap - den_ink_top`
4. Kích thước bounding box trả về:
   - `total_ascent = max(math_axis + gap + (num_ink_bot - num_ink_top), -num_y + num_item.size.ascent)`
   - `total_descent = max(gap + (den_ink_bot - den_ink_top) - math_axis, den_y + den_item.size.descent)`
   - `size = Size(width=frac_w, height=total_ascent + total_descent, ascent=total_ascent, descent=total_descent, baseline=total_ascent)`

---

## 2. Validation & Invariant Rules

| Rule ID | Mô tả bất biến | Tiêu chuẩn kiểm tra |
|---------|----------------|---------------------|
| **INV-001** | Chân chữ số bám baseline | Toàn bộ chữ số `"0"`–`"9"` sau chuẩn hóa có `abs(max_y) <= 0.08 * xh` |
| **INV-002** | Đồng nhất chiều cao chữ số | Chiều cao của chữ số `"0"`–`"9"` trong cùng một cấp scale nằm trong `[1.05 * xh, 1.30 * xh]`, độ lệch tối đa giữa chữ số cao nhất và thấp nhất `<= 12%` |
| **INV-003** | Giới hạn khoảng cách chữ số | Khoảng cách hở quang học giữa 2 nét chữ số liền kề nằm trong `[0.10 * xh, 0.20 * xh]` |
| **INV-004** | Liền mạch số thập phân | Chênh lệch giữa khoảng cách sau dấu phẩy thập phân và `dgap` không vượt quá `0.08 * xh` |
| **INV-005** | Khoảng cách gạch phân số | Khoảng hở quang học từ nét tử số/mẫu số đến gạch phân số (`node.bar=True`) nằm trong `[0.15 * xh, 0.25 * xh]` |
| **INV-006** | Độ vươn gạch phân số | Thanh gạch phân số (`node.bar=True`) chỉ nhô ra mỗi bên từ `0.15 * xh` đến `0.25 * xh` so với tử/mẫu |
