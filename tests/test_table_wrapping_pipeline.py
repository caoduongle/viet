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

    # 3. Kiểm tra ranh giới từng ô (US4 - T014):
    # Cột 0 chứa 'Mo ta' phải nằm trong [x0, divider_x]
    # Cột 1 chứa URL và Hash phải nằm hoàn toàn trong [divider_x, max_table_x]
    from chuviettay.layout.table_layout import TableLayoutEngine
    t_engine = TableLayoutEngine(engine.width, engine.line_h)
    col_widths = t_engine.compute_column_widths(table)
    divider_x = engine.x0 + col_widths[0]

    # Các nét sau nét viền bảng là nét nội dung chữ
    content_strokes = pages_strokes[0][7:]
    for s_idx, stroke in enumerate(content_strokes):
        xs = [pt[0] for pt in stroke]
        min_s_x, max_s_x = min(xs), max(xs)
        if min_s_x >= divider_x - 1.0:
            # Nét thuộc cột 1 (URL/hash)
            assert max_s_x <= max_table_x, f"Nét {s_idx} của cột 1 tràn qua mép phải: {max_s_x} > {max_table_x}"
            assert min_s_x >= divider_x - 1.0, f"Nét {s_idx} của cột 1 lấn sang cột 0: {min_s_x} < {divider_x}"
        else:
            # Nét thuộc cột 0 ('Mo ta')
            assert max_s_x <= divider_x + 1.0, f"Nét {s_idx} của cột 0 lấn sang cột 1: {max_s_x} > {divider_x}"
            assert min_s_x >= engine.x0 - 1.0, f"Nét {s_idx} của cột 0 tràn ra lề trái: {min_s_x} < {engine.x0}"


def test_writer_state_invariance_during_token_width_measurement(tiny_bank):
    """Kiểm tra US3 (T012): Hàm đo measure_text_width() là hàm đo thuần (pure),
    tuyệt đối KHÔNG thay đổi trạng thái sinh nét của Writer:
    writer.counts, writer.last, writer.assembled không bị biến đổi khi thử đo các token/tiền tố dài."""
    import random
    from chuviettay.model.writer import Writer

    rnd = random.Random(42)
    writer = Writer(tiny_bank, rnd, jitter=0.0, loose_case=False, space=1.0)

    # Đưa writer vào một trạng thái ban đầu có các từ đã sinh
    writer.counts["test"] = 3
    writer.last["test"] = 1
    writer.assembled = ["test_assembled"]

    initial_counts = dict(writer.counts)
    initial_last = dict(writer.last)
    initial_assembled = list(writer.assembled)

    long_token = "https://example.com/very/long/unbroken/path/123456"

    # Đo thử độ rộng của rất nhiều tiền tố
    for k in range(1, len(long_token) + 1):
        cand = long_token[:k]
        w = writer.measure_text_width(cand)
        assert w >= 0.0

    # Khẳng định tuyệt đối bất biến trạng thái:
    assert writer.counts == initial_counts, "writer.counts bị thay đổi sau khi đo measure_text_width"
    assert writer.last == initial_last, "writer.last bị thay đổi sau khi đo measure_text_width"
    assert writer.assembled == initial_assembled, "writer.assembled bị thay đổi sau khi đo measure_text_width"
