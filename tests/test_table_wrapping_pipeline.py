"""Kiểm thử tích hợp cho cơ chế bẻ token dài (URL, mã hash, chuỗi không dấu cách)
ngay trong pipeline kết xuất bảng của DocumentLayoutEngine.
"""
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Paragraph, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from tests.test_xopp_geometry_helper import (
    assert_all_strokes_within_page_bounds,
    extract_xopp_pages_strokes,
)


def test_table_long_url_and_hash_wrapping_in_real_pipeline(tiny_bank, tmp_path):
    """Kiểm tra một chuỗi URL dài và chuỗi mã hash dài trong ô bảng hẹp được bẻ nhiều dòng
    và 100% toạ độ nét vẽ nằm trong ranh giới chiều rộng của cột.
    """
    from tests.conftest import _inst
    # Bổ sung mẫu nét cho các chữ cái thông dụng trong URL/hash
    for ch in "abcdefghijklmnopqrstuvwxyz":
        tiny_bank.letters[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
    for ch in "0123456789":
        tiny_bank.digits[ch] = [_inst(4.0, [[0, 0, 2, -6, 4, 0]])]
    for ch in ":/.":
        tiny_bank.punct[ch] = [_inst(2.0, [[0, 0, 1, 1]])]

    long_url = "https://example.com/very/long/unbroken/path/to/handwritten/document/pipeline"
    long_hash = "abcdef0123456789abcdef0123456789abcdef0123456789"

    cell_url = TableCell(blocks=[Paragraph(inlines=[Text(long_url)])])
    cell_hash = TableCell(blocks=[Paragraph(inlines=[Text(long_hash)])])
    cell_normal = TableCell(blocks=[Paragraph(inlines=[Text("Mo ta")])])

    table = Table(
        rows=[
            TableRow(cells=[cell_normal, cell_url]),
            TableRow(cells=[cell_normal, cell_hash]),
        ],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_wrapped_url.xopp")

    # Đặt độ rộng khả dụng hẹp (ví dụ width=300 pt) để ép cột URL/hash hẹp (~150 pt)
    # Trong khi token dài > 400 pt nếu không bẻ dòng
    opts = WriteOptions(width=280.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out_file)

    assert res.n_tables == 1
    # Số dòng kết xuất phải > 2 (vì URL và hash mỗi cái phải ngắt thành >= 3 dòng)
    assert res.n_lines >= 6, f"URL và hash phải ngắt thành nhiều dòng, nhận được {res.n_lines} dòng"

    # 1. 100% nét vẽ nằm trong lề trang in
    assert_all_strokes_within_page_bounds(out_file, max_y=841.89 - 60.0, min_y=40.0)

    # 2. Toạ độ x tối đa của tất cả các nét trong bảng không được vượt quá margin_left + width
    pages_strokes = extract_xopp_pages_strokes(out_file)
    assert len(pages_strokes) == 1
    max_table_x = engine.x0 + engine.width + 5.0
    for s_idx, stroke in enumerate(pages_strokes[0]):
        for pt in stroke:
            x, y = pt
            assert x <= max_table_x, (
                f"Nét {s_idx} có toạ độ x={x:.2f} tràn ra ngoài ranh giới cột bảng ({max_table_x:.2f} pt)"
            )
