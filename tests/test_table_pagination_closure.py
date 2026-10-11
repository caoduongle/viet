"""Kiểm thử tính đúng đắn của phân trang bảng khi có ô gộp liên kết (transitive closure) và ô quá khổ."""
import pytest

from chuviettay.document.ir import Table, TableBorder, TableCell, TableRow
from chuviettay.layout.table_layout import TableLayoutEngine, TableLayoutData


def test_transitive_row_merge_closure_stays_together():
    """
    Kiểm tra bao đóng liên kết ô gộp:
    Hàng 0: Ô A (rowspan=2, col=0), Ô B (rowspan=1, col=1)
    Hàng 1: Ô C (rowspan=2, col=1)
    Hàng 2: Ô D (rowspan=1, col=0)
    Hàng 3: Ô E (rowspan=1, col=0), Ô F (rowspan=1, col=1)
    Ô A liên kết hàng 0-1, Ô C liên kết hàng 1-2 => Hàng 0, 1, 2 tạo thành 1 nhóm nguyên tử [0, 2].
    """
    cell_a = TableCell.from_text("Cell A")
    cell_a.rowspan = 2
    cell_b = TableCell.from_text("Cell B")
    cell_c = TableCell.from_text("Cell C")
    cell_c.rowspan = 2
    cell_d = TableCell.from_text("Cell D")
    cell_e = TableCell.from_text("Cell E")
    cell_f = TableCell.from_text("Cell F")

    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c]),
            TableRow(cells=[cell_d]),
            TableRow(cells=[cell_e, cell_f]),
        ],
        border_style=TableBorder.ALL,
    )

    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=10.0)

    # Giả sử chiều cao còn lại của trang chỉ đủ chứa 2 hàng, nhưng nhóm [0, 2] cần 3 hàng.
    # Vì trang mới bắt đầu (curr_h == 0), thuật toán phải lấy toàn bộ nhóm [0, 2] để không xé rách ô C.
    h_two_rows = sum(layout.row_heights[0:2]) + 5.0
    slice_data, next_row = layout.slice_page(start_row_idx=0, max_height=h_two_rows, new_y=10.0)

    assert next_row == 3, f"Bao đóng [0, 2] phải được giữ nguyên vẹn, next_row phải là 3, nhận được {next_row}"
    assert len(slice_data.row_heights) == 3


def test_pagination_breaks_before_group_if_page_has_content():
    """
    Nếu trang đã có nội dung (curr_h > 0), gặp nhóm gộp không vừa max_height thì phải dừng ngay trước nhóm gộp.
    """
    cell_r0_a = TableCell.from_text("R0A")
    cell_r0_b = TableCell.from_text("R0B")

    # Nhóm gộp hàng 1-2
    cell_r1_a = TableCell.from_text("R1A")
    cell_r1_a.rowspan = 2
    cell_r1_b = TableCell.from_text("R1B")
    cell_r2_b = TableCell.from_text("R2B")

    table = Table(
        rows=[
            TableRow(cells=[cell_r0_a, cell_r0_b]),
            TableRow(cells=[cell_r1_a, cell_r1_b]),
            TableRow(cells=[cell_r2_b]),
        ],
        border_style=TableBorder.ALL,
    )

    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=10.0)

    # Đủ chỗ cho hàng 0, nhưng không đủ cho hàng 0 + cả nhóm [1, 2]
    h_avail = layout.row_heights[0] + layout.row_heights[1] - 5.0
    slice_data, next_row = layout.slice_page(start_row_idx=0, max_height=h_avail, new_y=10.0)

    assert next_row == 1, f"Phải dừng sau hàng 0, chuyển nhóm [1, 2] sang trang mới. Nhận được next_row={next_row}"
    assert len(slice_data.row_heights) == 1


def test_oversized_group_forward_progression_no_hang():
    """
    Nếu một hàng hoặc cụm hàng cao hơn toàn bộ max_height của trang:
    slice_page vẫn phải tiến lên ít nhất (next_row > start_row_idx), không được treo hoặc loop vô hạn.
    """
    cell_a = TableCell.from_text("Very Tall Row A")
    cell_b = TableCell.from_text("Very Tall Row B")

    table = Table(
        rows=[
            TableRow(cells=[cell_a]),
            TableRow(cells=[cell_b]),
        ],
        border_style=TableBorder.ALL,
    )

    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=10.0)

    # max_height cực nhỏ (ví dụ 5.0), nhỏ hơn bất kỳ hàng nào
    slice_data, next_row = layout.slice_page(start_row_idx=0, max_height=5.0, new_y=10.0)
    assert next_row > 0, "Bắt buộc phải tiến trình, không được trả về next_row == 0"
    assert len(slice_data.row_heights) >= 1
