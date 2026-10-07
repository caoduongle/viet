# Data Model & Typography Geometry: Punctuation & Digit Spacing

**Feature**: `030-punctuation-spacing-alignment`  
**Date**: 2026-10-07

## 1. Entities & Data Structures

### `NormalizedPunctuation`
Biểu diễn mẫu nét dấu câu đã được chuẩn hóa gốc tọa độ về `0.0`.

```python
class NormalizedPunctuation:
    strokes: list[Stroke]  # Các nét đã dịch sao cho min_x = 0.0
    width: float          # Bounding box width: max_x - min_x
    ascent: float         # -min_y
    descent: float        # max_y
    original_w: float     # Giá trị w gốc (nếu có)
```

**Quy tắc biến đổi**:
- `min_x = min(pt for st in raw_strokes for pt in st[0::2])`
- `strokes = [shift(st, -min_x, 0.0) for st in raw_strokes]`
- `width = max(pt for st in strokes for pt in st[0::2])`

### `DigitSpacingConfig`
Mô hình quy định dải khoảng cách hợp lệ giữa 2 chữ số liên tiếp trong cùng một số:

```python
@dataclass(frozen=True)
class DigitSpacingConfig:
    min_gap_ratio: float = 0.08   # 0.08 * xh (~0.64 pt khi xh=7.94)
    max_gap_ratio: float = 0.22   # 0.22 * xh (~1.75 pt khi xh=7.94)
    default_gap_ratio: float = 0.14 # 0.14 * xh (~1.11 pt khi xh=7.94)
```

## 2. Token Placement Geometry

### Gắn Dấu Câu Đuôi (`trail punctuation`)
Khi ghép một token có phần thân `core` (từ hoặc số) và đuôi `trail` (dấu câu):
- `placed_core_strokes`: Danh sách nét của `core` đã được định vị tại `x = 0.0`.
- `core_max_x`: `max(pt for st in placed_core_strokes for pt in st[0::2])` nếu có nét, ngược lại `core_w`.
- `current_x = max(core_w, core_max_x) + clearance_gap`:
  - `clearance_gap = max(pen_w * 0.8, 0.18 * xh)` đối với dấu câu đầu tiên trong `trail`.
  - Đối với các dấu câu tiếp theo trong `trail` (như `...`, `?!`): `gap = 0.10 * xh`.
- Với mỗi ký tự dấu câu `ch`:
  - Lấy mẫu và chuẩn hóa: `norm_punct = normalize_punct(g)`
  - Đặt nét: `trail_strokes.extend([shift(st, current_x, 0.0) for st in norm_punct.strokes])`
  - Bước tiến: `current_x += norm_punct.width + 0.12 * xh`

### Gắn Dấu Câu Mở Đầu (`lead punctuation`)
- `current_x = 0.0`
- Với mỗi ký tự dấu mở `ch`:
  - `norm_punct = normalize_punct(g)`
  - Đặt nét: `lead_strokes.extend([shift(st, current_x, 0.0) for st in norm_punct.strokes])`
  - Bước tiến: `current_x += norm_punct.width + 0.15 * xh`
- Phần `core` tiếp theo sẽ bắt đầu tại `x = current_x`.

## 3. Ghép Chữ Số (`Writer.number`)
- Với chữ số đầu tiên: `x = 0.0`.
- Với các chữ số tiếp theo:
  - Tính `dgap`:
    - Nếu có `b.d["dgaps"]`: chọn ngẫu nhiên một giá trị `g_raw`. Chuẩn hóa: `dgap = clamp(g_raw * (xh / 7.94), 0.08 * xh, 0.22 * xh)`.
    - Nếu không có: `dgap = 0.14 * xh`.
  - Nét chữ số thứ `k` được đặt tại: `x + dgap`.
  - Cập nhật: `x = x + dgap + digit_w`.
