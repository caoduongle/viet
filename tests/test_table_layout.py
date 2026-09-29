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


def test_table_occupancy_grid_rowspan():
    """Kiểm tra ô rowspan=2 chiếm chỗ trên cả 2 hàng, hàng sau phải tự dịch sang cột trống."""
    # Bảng:
    # Hàng 0: [ Cell A (rowspan=2) ] [ Cell B ]
    # Hàng 1: [ Cell C ]
    cell_a = TableCell.from_text("Cell A")
    cell_a.rowspan = 2
    cell_b = TableCell.from_text("Cell B")
    cell_c = TableCell.from_text("Cell C")

    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=200.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=20.0)

    # Bảng phải có 2 cột
    assert len(layout.col_widths) == 2

    # Hàng 0 có 2 ô: Cell A (col=0), Cell B (col=1)
    row0_cells = layout.cells[0]
    assert len(row0_cells) == 2
    laid_a = row0_cells[0]
    laid_b = row0_cells[1]
    assert laid_a.col == 0 and laid_a.row == 0
    assert laid_b.col == 1 and laid_b.row == 0

    # Hàng 1 chỉ có Cell C, và Cell C PHẢI ở col=1 (không được ở col=0)
    row1_cells = layout.cells[1]
    assert len(row1_cells) == 1
    laid_c = row1_cells[0]
    assert laid_c.col == 1 and laid_c.row == 1, f"Cell C bị xếp nhầm vào col={laid_c.col}"

    # Toạ độ X của Cell C phải trùng với toạ độ X của Cell B (cột 1)
    assert laid_c.x == laid_b.x
    assert laid_c.x > laid_a.x

    # Chiều cao của Cell A phải bằng tổng chiều cao 2 hàng
    expected_h = layout.row_heights[0] + layout.row_heights[1]
    assert laid_a.height == expected_h


def test_table_merged_cell_border_suppression():
    """Kiểm tra đường kẻ ngang bên trong ô rowspan=2 bị triệt tiêu."""
    cell_a = TableCell.from_text("A")
    cell_a.rowspan = 2
    cell_b = TableCell.from_text("B")
    cell_c = TableCell.from_text("C")

    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=200.0, line_height=20.0)
    layout = engine.layout_table(table, x0=0.0, y0=0.0)

    strokes = engine.generate_border_strokes(layout, TableBorder.ALL)
    # Tìm đường kẻ ngang phân cách giữa hàng 0 và hàng 1 (y = row_heights[0])
    div_y = layout.row_heights[0]
    horiz_divs = [s for s in strokes if s.points[0][1] == div_y and s.points[1][1] == div_y]

    # Chỉ có duy nhất 1 đoạn kẻ ngang ở cột 1 (từ col_widths[0] đến tổng width), không được kẻ qua cột 0
    assert len(horiz_divs) == 1
    p1, p2 = horiz_divs[0].points
    assert p1[0] >= layout.col_widths[0] - 0.01
    assert p2[0] <= layout.width + 0.01


def test_table_layout_data_slice_page():
    """Kiểm tra phân trang slice_page của TableLayoutData tuân thủ gắn kết rowspan và tiến trình đơn điệu."""
    cell_a = TableCell.from_text("A")
    cell_a.rowspan = 2
    cell_b = TableCell.from_text("B")
    cell_c = TableCell.from_text("C")
    cell_d = TableCell.from_text("D")
    cell_e = TableCell.from_text("E")

    # Bảng 3 hàng: hàng 0+1 có ô rowspan=2, hàng 2 là hàng đơn
    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c]),
            TableRow(cells=[cell_d, cell_e]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=200.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=50.0)

    # 1. Cắt với max_height đủ cho cả cụm 2 hàng đầu
    h_2rows = layout.row_heights[0] + layout.row_heights[1]
    slice1, next_row = layout.slice_page(0, max_height=h_2rows + 5.0, new_y=100.0)
    assert next_row == 2
    assert len(slice1.row_heights) == 2
    assert slice1.y == 100.0

    # 2. Cắt hàng cuối cùng
    slice2, next_row2 = layout.slice_page(next_row, max_height=100.0, new_y=100.0)
    assert next_row2 == 3
    assert len(slice2.row_heights) == 1

    # 3. Quá số hàng -> trả về rỗng
    slice_empty, next_row3 = layout.slice_page(3, max_height=100.0, new_y=100.0)
    assert next_row3 == 3
    assert len(slice_empty.row_heights) == 0


def test_table_combined_2x2_merged_cells_and_border_suppression():
    """Kiểm tra ô gộp kết hợp cả colspan=2 và rowspan=2 (khối 2x2) trong bảng 3x3."""
    # Bảng 3 hàng, 3 cột:
    # Hàng 0: [ M2x2 (colspan=2, rowspan=2) ] [ TopRight ]
    # Hàng 1: [ MidRight ]
    # Hàng 2: [ BotLeft ] [ BotMid ] [ BotRight ]
    m2x2 = TableCell.from_text("M2x2")
    m2x2.colspan = 2
    m2x2.rowspan = 2

    top_right = TableCell.from_text("TR")
    mid_right = TableCell.from_text("MR")
    bot_left = TableCell.from_text("BL")
    bot_mid = TableCell.from_text("BM")
    bot_right = TableCell.from_text("BR")

    table = Table(
        rows=[
            TableRow(cells=[m2x2, top_right]),
            TableRow(cells=[mid_right]),
            TableRow(cells=[bot_left, bot_mid, bot_right]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=20.0)

    # 1. Kiểm tra số cột và kích thước
    assert len(layout.col_widths) == 3
    assert len(layout.row_heights) == 3

    # Ô M2x2 phải nằm ở col=0, row=0, chiếm 2 cột, 2 hàng
    laid_m2x2 = layout.cells[0][0]
    assert laid_m2x2.col == 0 and laid_m2x2.row == 0
    assert laid_m2x2.colspan == 2 and laid_m2x2.rowspan == 2
    assert laid_m2x2.width == layout.col_widths[0] + layout.col_widths[1]
    assert laid_m2x2.height == layout.row_heights[0] + layout.row_heights[1]

    # Ô MidRight ở hàng 1 phải được đặt vào col=2
    laid_mr = layout.cells[1][0]
    assert laid_mr.col == 2 and laid_mr.row == 1
    assert laid_mr.x == 10.0 + layout.col_widths[0] + layout.col_widths[1]

    # Hàng 2 có 3 ô tương ứng với col 0, 1, 2
    assert len(layout.cells[2]) == 3
    for exp_c, cell in enumerate(layout.cells[2]):
        assert cell.col == exp_c
        assert cell.row == 2

    # 2. Khẳng định KHÔNG có bất kỳ cặp ô nào bị đè toạ độ lên nhau (non-overlapping bounding boxes)
    all_cells: list[LaidOutCell] = [c for r in layout.cells for c in r]
    for i in range(len(all_cells)):
        for j in range(i + 1, len(all_cells)):
            c1, c2 = all_cells[i], all_cells[j]
            overlap_x = max(0.0, min(c1.x + c1.width, c2.x + c2.width) - max(c1.x, c2.x))
            overlap_y = max(0.0, min(c1.y + c1.height, c2.y + c2.height) - max(c1.y, c2.y))
            assert overlap_x <= 0.001 or overlap_y <= 0.001, (
                f"Phát hiện ô chồng lấn: ô({c1.row},{c1.col}) và ô({c2.row},{c2.col})"
            )

    # 3. Kiểm tra triệt tiêu viền bên trong ô 2x2
    strokes = engine.generate_border_strokes(layout, TableBorder.ALL)
    # Đường phân cách ngang giữa hàng 0 và 1 (y = y0 + row_heights[0])
    div_y = 20.0 + layout.row_heights[0]
    horiz_in_m2x2 = [
        s for s in strokes
        if abs(s.points[0][1] - div_y) < 0.01 and abs(s.points[1][1] - div_y) < 0.01
        and s.points[0][0] < 10.0 + layout.col_widths[0] + layout.col_widths[1] - 0.01
    ]
    # Phải bị triệt tiêu hoàn toàn bên trong ô M2x2 (không có đoạn nào vẽ qua vùng cột 0-1)
    assert len(horiz_in_m2x2) == 0, "Lỗi viền: đường chia ngang vẫn bị vẽ xuyên qua ô 2x2"



