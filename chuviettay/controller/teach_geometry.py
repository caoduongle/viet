"""Quy chuẩn hình học và phép quy đổi nét vẽ cho giao diện dạy chữ (WordCanvas & Web Canvas).

Tách ra từ chuviettay.view.word_canvas (thay đổi lõi 3.2) để:
  1. Loại bỏ phụ thuộc vào Tkinter: có thể nạp an toàn trong Pyodide / Web Worker.
  2. Giữ nguyên duy nhất MỘT nguồn sự thật (Single Source of Truth) cho các hằng số canvas
     và thuật toán quy đổi pixel -> đơn vị kho mẫu.
  3. Cung cấp thông số cấu hình canvas qua Browser Bridge cho Web Client mà không cần hard-code.
"""
from __future__ import annotations

ZOOM: float = 10.0            # px trên màn hình cho mỗi "đơn vị" trong kho mẫu
BASE_PX: int = 170            # vị trí dòng kẻ chân chữ (đường cơ sở) trên canvas, tính bằng px
CANVAS_W: int = 760           # chiều rộng vùng vẽ chuẩn (px)
CANVAS_H: int = 230           # chiều cao vùng vẽ chuẩn (px)
MIN_POINT_DIST: float = 2.5   # khoảng cách tối thiểu giữa 2 điểm liên tiếp (px)

PxStroke = list[tuple[float, float]]   # một nét: các điểm (x, y) theo pixel màn hình


def strokes_to_bank_units(strokes: list[PxStroke], scale: float) -> tuple[list[list[float]], float]:
    """Đổi các nét vẽ (pixel) sang đơn vị kho mẫu: gốc x = điểm trái nhất, gốc y = dòng
    kẻ chân chữ (BASE_PX), chia ZOOM rồi nhân hệ số cỡ tay `scale`.
    -> (danh sách nét phẳng [x0,y0,x1,y1,...], độ rộng). Công thức chuẩn giữ nguyên từ gốc."""
    if not strokes:
        raise ValueError("Chưa có nét nào để quy đổi.")
    xs = [x for st in strokes for (x, _y) in st]
    left_px, right_px = min(xs), max(xs)
    rel: list[list[float]] = []
    for st in strokes:
        flat: list[float] = []
        for (x, y) in st:
            flat.append(round((x - left_px) / ZOOM * scale, 2))
            flat.append(round((y - BASE_PX) / ZOOM * scale, 2))
        rel.append(flat)
    width = round((right_px - left_px) / ZOOM * scale, 2)
    return rel, width


def filter_stroke_points(
    points: list[tuple[float, float]],
    min_dist: float = MIN_POINT_DIST,
) -> list[tuple[float, float]]:
    """Lọc bớt các điểm vẽ quá gần điểm trước đó (khoảng cách Euclid < min_dist)
    để giảm dung lượng dữ liệu và làm mượt nét."""
    if not points:
        return []
    filtered = [points[0]]
    min_dist_sq = min_dist ** 2
    for p in points[1:]:
        lx, ly = filtered[-1]
        if (p[0] - lx) ** 2 + (p[1] - ly) ** 2 >= min_dist_sq:
            filtered.append(p)
    return filtered
