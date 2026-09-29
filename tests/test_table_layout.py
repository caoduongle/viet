"""Kiểm thử tính toán bố cục bảng và sinh nét vẽ viền bảng."""
import pytest

from chuviettay.document.ir import Paragraph, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.table_layout import TableLayoutEngine


def test_table_column_widths_proportional():
    table = Table(
        rows=[
            TableRow(cells=[TableCell.from_text("Ngắn"), TableCell.from_text("Dòng này dài hơn khá nhiều")]),
            TableRow(cells=[TableCell.from_text("A"), TableCell.from_text("B")]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=400.0, line_height=24.0)
    col_widths = engine.compute_column_widths(table)
    assert len(col_widths) == 2
    assert sum(col_widths) <= 400.0
    # Cột 2 phải rộng hơn cột 1 vì chứa text dài hơn
    assert col_widths[1] > col_widths[0]


def test_table_jagged_rows_padding():
    # Hàng 1 có 3 cột, hàng 2 có 1 cột
    table = Table(
        rows=[
            TableRow(cells=[TableCell.from_text("1"), TableCell.from_text("2"), TableCell.from_text("3")]),
            TableRow(cells=[TableCell.from_text("Duy nhất")]),
        ],
        border_style=TableBorder.OUTER,
    )
    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    padded_rows = engine.pad_jagged_rows(table)
    assert len(padded_rows[1].cells) == 3
    assert len(padded_rows[1].cells[1].blocks) == 0  # ô đệm rỗng


def test_table_border_strokes_generation():
    table = Table(
        rows=[
            TableRow(cells=[TableCell.from_text("A"), TableCell.from_text("B")]),
            TableRow(cells=[TableCell.from_text("C"), TableCell.from_text("D")]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=200.0, line_height=20.0)
    layout = engine.layout_table(table, x0=50.0, y0=50.0)

    # ALL có: 4 đường viền ngoài + 1 đường chia ngang + 1 đường chia dọc = 6 nét
    strokes_all = engine.generate_border_strokes(layout, TableBorder.ALL)
    assert len(strokes_all) == 6

    # OUTER chỉ có 4 đường bao
    strokes_outer = engine.generate_border_strokes(layout, TableBorder.OUTER)
    assert len(strokes_outer) == 4

    # HORIZONTAL: 2 đường bao trên dưới + 1 đường chia ngang = 3 nét
    strokes_horiz = engine.generate_border_strokes(layout, TableBorder.HORIZONTAL)
    assert len(strokes_horiz) == 3

    # NONE: 0 nét
    strokes_none = engine.generate_border_strokes(layout, TableBorder.NONE)
    assert len(strokes_none) == 0
