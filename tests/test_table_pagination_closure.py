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

    # 1. Khi chiều cao đủ chứa cả 3 hàng, toàn bộ nhóm bao đóng [0, 2] phải được giữ nguyên vẹn
    h_three_rows = sum(layout.row_heights[0:3]) + 5.0
    slice_data, next_row = layout.slice_page(start_row_idx=0, max_height=h_three_rows, new_y=10.0)
    assert next_row == 3, f"Bao đóng [0, 2] phải được giữ nguyên vẹn khi đủ chỗ, next_row phải là 3, nhận được {next_row}"
    assert len(slice_data.row_heights) == 3

    # 2. Khi trang trắng (can_defer_to_next_page=False) mà chiều cao chỉ đủ 2 hàng:
    # Chiến lược tiếp nối có kiểm soát cắt tại hàng 2, tránh tràn ra ngoài trang
    h_two_rows = sum(layout.row_heights[0:2]) + 5.0
    slice_data_c, next_row_c = layout.slice_page(
        start_row_idx=0, max_height=h_two_rows, new_y=10.0, can_defer_to_next_page=False
    )
    assert next_row_c == 2, f"Tiếp nối có kiểm soát phải kẹp vừa trang (2 hàng), nhận được {next_row_c}"
    assert len(slice_data_c.row_heights) == 2


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


def test_pagination_group_defers_to_next_page_when_not_fitting_remainder():
    """Khi trang đã có nội dung (can_defer_to_next_page=True), nhóm gộp không vừa phải hoãn sang trang sau."""
    cell_a = TableCell.from_text("Row 0 Spanning")
    cell_a.rowspan = 2
    cell_b = TableCell.from_text("Row 0 B")
    cell_c = TableCell.from_text("Row 1 C")

    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c]),
        ],
        border_style=TableBorder.ALL,
    )
    engine = TableLayoutEngine(available_width=300.0, line_height=20.0)
    layout = engine.layout_table(table, x0=10.0, y0=200.0)

    # Chiều cao nhóm [0, 1]
    group_h = sum(layout.row_heights[0:2])
    # Giả sử trang chỉ còn trống 0.5 * group_h
    slice_data, next_row = layout.slice_page(
        start_row_idx=0,
        max_height=group_h * 0.5,
        new_y=200.0,
        can_defer_to_next_page=True,
    )
    # Vì can_defer_to_next_page=True, slice_page phải trả về rỗng để engine chuyển trang
    assert next_row == 0, f"Phải hoãn sang trang tiếp theo (next_row=0), nhận được {next_row}"
    assert len(slice_data.cells) == 0


def test_render_table_strokes_within_printable_bounds(tmp_path, tiny_bank):
    """Kiểm tra tích hợp: 100% toạ độ nét vẽ của bảng nhiều trang nằm trong giới hạn trang in."""
    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, Paragraph, Text
    from chuviettay.layout.engine import DocumentLayoutEngine
    from tests.test_xopp_geometry_helper import assert_all_strokes_within_page_bounds

    # Tạo bảng lớn với các ô gộp và nội dung nhiều dòng (30 hàng để đảm bảo > 1 trang)
    rows = []
    for r in range(30):
        if r % 3 == 0:
            c1 = TableCell.from_text(f"Spanning Cell at row {r}\nLine 2\nLine 3")
            c1.rowspan = 3
            c2 = TableCell.from_text(f"Normal cell {r}")
            rows.append(TableRow(cells=[c1, c2]))
        else:
            c2 = TableCell.from_text(f"Normal cell {r}\nExtra details")
            rows.append(TableRow(cells=[c2]))

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Văn bản mở đầu đoạn")]),
        Table(rows=rows, border_style=TableBorder.ALL),
    ])

    out_file = str(tmp_path / "table_paginated.xopp")
    opts = WriteOptions(line=22.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out_file)

    assert res.n_pages >= 2, f"Bảng lớn phải phân trang ra >= 2 trang, nhận được {res.n_pages}"
    # Khẳng định 100% toạ độ nét nằm trong lề trang in [40, 841.89 - 60.0]
    assert_all_strokes_within_page_bounds(out_file, max_y=841.89 - 60.0, min_y=40.0 - 5.0)


def test_multi_page_content_continuation_preserves_all_lines(tmp_path, tiny_bank):
    """Kiểm tra P1: Hàng đơn lẻ hoặc ô bảng chứa rất nhiều dòng văn bản (35 dòng)
    khi vượt quá chiều cao trang in thì phải tiếp nối nội dung sang các trang sau,
    100% số dòng văn bản được bảo toàn đầy đủ, không bị cắt xén âm thầm.
    """
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
    for ch in "0123456789":
        if ch not in tiny_bank.digits:
            tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, Table, TableBorder, TableCell, TableRow
    from chuviettay.layout.engine import DocumentLayoutEngine
    from tests.test_xopp_geometry_helper import assert_all_strokes_within_page_bounds

    # Tạo ô chứa 35 dòng riêng biệt
    raw_lines = [f"Dong thu {i:02d} cua van ban bang" for i in range(35)]
    tall_cell = TableCell.from_text("\n".join(raw_lines))
    short_cell = TableCell.from_text("Cot ben phai")

    table = Table(
        rows=[TableRow(cells=[tall_cell, short_cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_tall_continuation.xopp")

    opts = WriteOptions(line=22.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)

    res = engine.render(doc, out_file)


    # 1. Bảng phải được phân bổ qua >= 2 trang
    assert res.n_pages >= 2, f"Ô 35 dòng phải tràn qua ít nhất 2 trang, nhận được {res.n_pages} trang"

    # 2. Toàn bộ 35 dòng của ô dài (cộng với 3 dòng của cột phụ) phải được kết xuất chính xác 38 dòng
    assert res.n_lines == 38, f"Toàn bộ 35 dòng của ô dài + 3 dòng cột phụ phải được bảo toàn chính xác, nhận được {res.n_lines} dòng"

    # 3. 100% nét vẽ nằm trong giới hạn trang in trên mọi trang
    assert_all_strokes_within_page_bounds(out_file, max_y=841.89 - 60.0, min_y=40.0 - 5.0)

    # 4. Cảnh báo chia tiếp nối hàng xuất hiện trong WriteResult.warnings (US5)
    assert len(res.warnings) >= 1
    assert any("tiếp nối sang trang sau" in w for w in res.warnings)


def test_multi_page_three_pages_continuation_preserves_all_lines(tmp_path, tiny_bank):
    """Kiểm tra P1 nâng cao: Một ô bảng chứa 75 dòng văn bản
    buộc phải chia tiếp nối qua ít nhất 3 trang in liên tiếp,
    100% số dòng văn bản được bảo toàn trên cả 3 trang."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
        if ch not in tiny_bank.digits:
            tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, Table, TableBorder, TableCell, TableRow
    from chuviettay.layout.engine import DocumentLayoutEngine
    from tests.test_xopp_geometry_helper import assert_all_strokes_within_page_bounds

    raw_lines = [f"Dong thu {i:02d} van ban rat dai" for i in range(75)]
    tall_cell = TableCell.from_text("\n".join(raw_lines))

    table = Table(
        rows=[TableRow(cells=[tall_cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_three_pages.xopp")

    opts = WriteOptions(line=22.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out_file)

    assert res.n_pages >= 3, f"Ô 75 dòng phải tràn qua ít nhất 3 trang, nhận được {res.n_pages} trang"
    assert res.n_lines == 75, f"Toàn bộ 75 dòng phải được bảo toàn chính xác, nhận được {res.n_lines} dòng"
    assert_all_strokes_within_page_bounds(out_file, max_y=841.89 - 60.0, min_y=40.0 - 5.0)


def test_table_slicing_warning_propagation_to_bridge_and_report(tmp_path, tiny_bank):
    """Kiểm tra US5 (T016, T017, T018): Cảnh báo khi một hàng quá cao vượt quá trang
    phải được truyền thành công đến WriteResult.warnings, BrowserBridge payload và write_report_lines."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
        if ch not in tiny_bank.digits:
            tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    from chuviettay.browser.bridge import BrowserBridge
    from chuviettay.formatting import write_report_lines

    bank_file = str(tmp_path / "bank.json.gz")
    tiny_bank.save(bank_file)

    raw_words = " ".join([f"tu{i} dai van ban bang" for i in range(180)])
    table_md = f"| Cot A | Cot B |\n|---|---|\n| {raw_words} | Phu |"

    bridge = BrowserBridge(bank_path=bank_file)
    bridge.init()
    res_dict = bridge.write_text(table_md, options={"line": 22.0}, fmt="md")

    assert res_dict["ok"] is True
    assert len(res_dict["warnings"]) >= 1, "Cảnh báo cắt/tiếp nối bảng phải có trong bridge response"
    assert any("tiếp nối" in w for w in res_dict["warnings"])

    from chuviettay.model.composer import WriteResult
    wr = WriteResult("test.xopp", 1, 10, 5, 0, warnings=res_dict["warnings"])
    report_lines = write_report_lines(wr)
    assert any("Cảnh báo" in line and "tiếp nối" in line for line in report_lines)


def test_tall_row_combined_with_multi_page_rowspan_and_borders(tmp_path, tiny_bank):
    """Kiểm tra US4 (T019): Bảng kết hợp hàng siêu cao chia tiếp nối qua 3+ trang
    và các ô rowspan vươn qua nhiều hàng, bảo đảm BorderLookupGrid sinh nét viền đúng,
    không văng lỗi IndexError và các ô sau không bị lệch chỉ số."""
    from tests.conftest import _inst
    for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
        if ch not in tiny_bank.letters:
            tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
        if ch not in tiny_bank.digits:
            tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]

    from chuviettay.controller.results import WriteOptions
    from chuviettay.document.ir import Document, Table, TableBorder, TableCell, TableRow
    from chuviettay.layout.engine import DocumentLayoutEngine

    # Hàng 0: Ô 1 (70 dòng), Ô 2 (rowspan=2)
    lines_70 = [f"Dong {i:02d} rat dai noi dung" for i in range(70)]
    cell_tall = TableCell.from_text("\n".join(lines_70))
    cell_span = TableCell.from_text("Nhan gop")
    cell_span.rowspan = 2

    # Hàng 1: Ô thường
    cell_short = TableCell.from_text("Ngan")

    # Hàng 2: Ô thường
    cell_h2 = TableCell.from_text("Hang 2 cuoi")

    table = Table(
        rows=[
            TableRow(cells=[cell_tall, cell_span]),
            TableRow(cells=[cell_short]),
            TableRow(cells=[cell_h2]),
        ],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_rowspan_3pages.xopp")

    opts = WriteOptions(line=22.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out_file)

    assert res.n_pages >= 3, f"Bảng phải phân bổ qua ít nhất 3 trang, nhận được {res.n_pages}"
    assert res.n_lines >= 70, "Toàn bộ dòng của ô cao phải được kết xuất"



