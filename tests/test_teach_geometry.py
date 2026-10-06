"""Kiểm thử chuviettay.controller.teach_geometry (thay đổi lõi 3.2).
Đảm bảo các phép quy đổi pixel -> đơn vị kho mẫu và hằng số hình học canvas
hoàn toàn độc lập với Tkinter, không làm thay đổi kết quả tính toán so với trước đây.
"""
from __future__ import annotations

import pytest

from chuviettay.controller.teach_geometry import (
    BASE_PX,
    CANVAS_H,
    CANVAS_W,
    MIN_POINT_DIST,
    ZOOM,
    filter_stroke_points,
    strokes_to_bank_units,
)


def test_constants():
    """Kiểm tra giá trị các hằng số hình học chuẩn của canvas dạy từ."""
    assert ZOOM == 10.0
    assert BASE_PX == 170
    assert CANVAS_W == 760
    assert CANVAS_H == 230
    assert MIN_POINT_DIST == 2.5


def test_strokes_to_bank_units_single_stroke():
    """Kiểm tra quy đổi 1 nét: gốc x = điểm trái nhất, gốc y = BASE_PX."""
    strokes = [[(100.0, float(BASE_PX)), (100.0 + 10.0 * ZOOM, float(BASE_PX) - 5.0 * ZOOM)]]
    rel, w = strokes_to_bank_units(strokes, 1.0)
    assert rel == [[0.0, 0.0, 10.0, -5.0]]
    assert w == 10.0


def test_strokes_to_bank_units_scale():
    """Kiểm tra nhân hệ số cỡ tay scale."""
    strokes = [[(0.0, float(BASE_PX)), (10.0 * ZOOM, float(BASE_PX) - 5.0 * ZOOM)]]
    rel, w = strokes_to_bank_units(strokes, 2.0)
    assert rel == [[0.0, 0.0, 20.0, -10.0]]
    assert w == 20.0


def test_strokes_to_bank_units_multiple_strokes_leftmost():
    """Kiểm tra gốc x là điểm cực trái trong toàn bộ các nét."""
    strokes = [
        [(50.0, float(BASE_PX)), (60.0, float(BASE_PX))],
        [(30.0, float(BASE_PX)), (40.0, float(BASE_PX))],
    ]
    rel, w = strokes_to_bank_units(strokes, 1.0)
    assert rel[0][0] == 2.0
    assert rel[1][0] == 0.0
    assert w == 3.0


def test_strokes_to_bank_units_empty_raises():
    """Quy đổi khi không có nét nào phải ném ValueError."""
    with pytest.raises(ValueError, match="Chưa có nét nào"):
        strokes_to_bank_units([], 1.0)


def test_filter_stroke_points():
    """Lọc điểm: bỏ qua điểm có khoảng cách Euclid < MIN_POINT_DIST so với điểm trước."""
    raw_points = [
        (10.0, 10.0),
        (11.0, 10.0),  # dist 1.0 < 2.5 -> bỏ qua
        (12.0, 10.0),  # dist 2.0 < 2.5 từ (10, 10) -> bỏ qua
        (13.0, 10.0),  # dist 3.0 >= 2.5 từ (10, 10) -> giữ lại
        (13.0, 12.0),  # dist 2.0 < 2.5 từ (13, 10) -> bỏ qua
        (13.0, 13.0),  # dist 3.0 >= 2.5 từ (13, 10) -> giữ lại
    ]
    filtered = filter_stroke_points(raw_points, min_dist=MIN_POINT_DIST)
    assert filtered == [(10.0, 10.0), (13.0, 10.0), (13.0, 13.0)]


def test_view_reexport_matches():
    """view.word_canvas phải re-export các hằng số và hàm giống hệt teach_geometry."""
    from tests import conftest
    if not conftest.is_tk_usable():
        pytest.skip(f"Môi trường Tk/Tcl không khả dụng ({conftest._tk_unusable_reason})")
    from chuviettay.view import word_canvas as wc

    assert wc.ZOOM == ZOOM
    assert wc.BASE_PX == BASE_PX
    assert wc.CANVAS_W == CANVAS_W
    assert wc.CANVAS_H == CANVAS_H
    assert wc.MIN_POINT_DIST == MIN_POINT_DIST
    assert wc.strokes_to_bank_units is strokes_to_bank_units
