"""Kiểm thử tính đúng đắn của việc phục hồi số cột và toạ độ cột logic (occupancy grid)
khi chuyển đổi bảng IR sang bảng Markdown trong chuviettay/browser/bridge.py.
"""
from chuviettay.browser.bridge import BrowserBridge
from chuviettay.document.ir import Document, Paragraph, Table, TableBorder, TableCell, TableRow, Text


def test_markdown_table_occupancy_grid_recovers_logical_columns_with_colspan():
    """Kiểm tra bảng có ô gộp colspan=2 ở hàng đầu và 3 cột ở hàng thứ hai:
    Hàng 0: Ô A (colspan=2), Ô B (colspan=1) -> Tổng số cột logic là 3, không phải 2.
    Hàng 1: Ô C, Ô D, Ô E -> 3 cột logic.
    Bảng Markdown sinh ra phải có đúng 3 cột và Ô B phải nằm ở cột 3 (| A |   | B |).
    """
    cell_a = TableCell(blocks=[Paragraph(inlines=[Text("A")])], colspan=2)
    cell_b = TableCell(blocks=[Paragraph(inlines=[Text("B")])], colspan=1)
    cell_c = TableCell(blocks=[Paragraph(inlines=[Text("C")])], colspan=1)
    cell_d = TableCell(blocks=[Paragraph(inlines=[Text("D")])], colspan=1)
    cell_e = TableCell(blocks=[Paragraph(inlines=[Text("E")])], colspan=1)

    table = Table(
        rows=[
            TableRow(cells=[cell_a, cell_b]),
            TableRow(cells=[cell_c, cell_d, cell_e]),
        ],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])

    bridge = BrowserBridge(None)
    # Giả lập luồng serialize markdown_text từ document trong bridge
    # Gọi hàm trích xuất của bridge qua method hoặc tái hiện logic bridge
    # Bridge._convert_document_to_markdown hoặc qua export
    result = bridge._document_to_markdown_dict(doc)

    md = result["markdown_text"]
    lines = [ln.strip() for ln in md.splitlines() if ln.strip()]

    # Phải có ít nhất 3 dòng: Header, Delimiter, Row 2
    assert len(lines) >= 3, f"Bảng Markdown phải có ít nhất 3 dòng, nhận được: {lines}"

    # Dòng tiêu đề: | A |   | B |
    header_cols = [c.strip() for c in lines[0].strip("|").split("|")]
    assert len(header_cols) == 3, f"Số cột tiêu đề phải là 3, nhận được {len(header_cols)}: {header_cols}"
    assert header_cols[0] == "A"
    assert header_cols[1] == ""  # Đệm ô trống do A chiếm colspan=2
    assert header_cols[2] == "B"

    # Dòng phân cách: 3 cột căn lề
    delim_cols = [c.strip() for c in lines[1].strip("|").split("|")]
    assert len(delim_cols) == 3

    # Dòng dữ liệu thứ hai: | C | D | E |
    data_cols = [c.strip() for c in lines[2].strip("|").split("|")]
    assert len(data_cols) == 3
    assert data_cols == ["C", "D", "E"]


def test_markdown_table_occupancy_all_rows_have_colspan():
    """Kiểm tra bảng mà tất cả các hàng đều chứa ô gộp (len(r.cells) == 1 trong khi colspan=3).
    Bảng Markdown sinh ra phải có đủ 3 cột logic.
    """
    cell_wide = TableCell(blocks=[Paragraph(inlines=[Text("Tieu de rong")])], colspan=3)
    table = Table(
        rows=[TableRow(cells=[cell_wide])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    bridge = BrowserBridge(None)
    result = bridge._document_to_markdown_dict(doc)

    md = result["markdown_text"]
    lines = [ln.strip() for ln in md.splitlines() if ln.strip()]
    assert len(lines) >= 2

    header_cols = [c.strip() for c in lines[0].strip("|").split("|")]
    assert len(header_cols) == 3, f"Số cột tiêu đề phải là 3 dù chỉ có 1 ô colspan=3, nhận được {len(header_cols)}"
    assert header_cols[0] == "Tieu de rong"
    assert header_cols[1] == ""
    assert header_cols[2] == ""
