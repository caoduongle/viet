"""Kiểm thử tính toàn vẹn hình học phân trang bảng và an toàn Bounding Box (P1/P2).

Bao gồm:
1. Ô rowspan=4 chứa 80 dòng trải qua 4+ trang, bảo đảm 100% dòng dữ liệu không bị rơi rụng
   và các ô khác cùng cột ở hàng sau không bị ghi đè.
2. Đối tượng TableCell trong Document IR không bị gán bẩn trường layout.
3. Không làm bẹt nét chữ ở mép trang (không dồn các điểm đáy thành đoạn collinear ngang).
"""
from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Table, TableBorder, TableCell, TableRow
from chuviettay.layout.engine import DocumentLayoutEngine, TokenBox
from tests.test_letter_assembly_quality import _create_quality_test_bank
from tests.test_xopp_geometry_helper import assert_all_strokes_within_page_bounds


def test_rowspan_continuation_80_lines_no_overwrite(tmp_path):
    """Kiểm tra ô rowspan=4 với 80 dòng qua 4+ trang:
    - 100% dòng xuất hiện tuần tự đầy đủ.
    - Không ghi đè nội dung sang ô khác cùng cột (Cot 1 Hang 1, Cot 1 Hang 2, Cot 1 Hang 3).
    - TableCell trong Document IR không bị gán bẩn trường source_cell_id.
    """
    bank = _create_quality_test_bank(tmp_path)

    raw_lines = [f"DONG_{i:04d} du lieu dong {i}" for i in range(1, 81)]
    cell_span4 = TableCell.from_text("\n".join(raw_lines))
    cell_span4.rowspan = 4

    cell_r0_c1 = TableCell.from_text("Cot A")
    cell_r1_c1 = TableCell.from_text("Cot B")
    cell_r2_c1 = TableCell.from_text("Cot C")
    cell_r3_c1 = TableCell.from_text("Cot D")

    table = Table(
        rows=[
            TableRow(cells=[cell_span4, cell_r0_c1]),
            TableRow(cells=[cell_r1_c1]),
            TableRow(cells=[cell_r2_c1]),
            TableRow(cells=[cell_r3_c1]),
        ],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_80_lines.xopp")

    opts = WriteOptions(
        paper="custom",
        paper_width=250.0,
        paper_height=300.0,
        margin_top=25.0,
        margin_bottom=25.0,
        line=22.0,
        jitter=0.0,
    )
    recorded_tokens: list[TokenBox] = []
    engine = DocumentLayoutEngine(
        bank,
        opts,
        token_layout_callback=recorded_tokens.append,
    )
    res = engine.render(doc, out_file)

    # 1. Phân trang trải qua ít nhất 4 trang
    assert res.n_pages >= 4, f"Bảng 80 dòng phải phân trang qua ít nhất 4 trang, nhận được {res.n_pages}"

    # 2. Toàn bộ 80 nhãn DONG_0001 .. DONG_0080 xuất hiện đầy đủ, đúng thứ tự
    tokens_seen = [b.token for b in recorded_tokens]
    matched_labels = []
    for t in tokens_seen:
        m = re.match(r"DONG_\d{4}", t)
        if m and (not matched_labels or matched_labels[-1] != m.group(0)):
            matched_labels.append(m.group(0))

    expected_labels = [f"DONG_{i:04d}" for i in range(1, 81)]
    assert matched_labels == expected_labels, (
        f"Kỳ vọng đủ 80 nhãn từ DONG_0001 đến DONG_0080. Nhận được {len(matched_labels)} nhãn."
    )

    # 3. Các ô cùng cột ở các hàng kế tiếp không bị ghi đè nội dung
    assert "A" in tokens_seen, "Cot A phải xuất hiện"
    assert "B" in tokens_seen, "Cot B phải xuất hiện, không bị ghi đè"
    assert "C" in tokens_seen, "Cot C phải xuất hiện, không bị ghi đè"
    assert "D" in tokens_seen, "Cot D phải xuất hiện, không bị ghi đè"

    # 4. Kiểm tra Document IR TableCell không bị gán bẩn trường source_cell_id
    assert getattr(cell_span4, "source_cell_id", None) is None, "cell_span4 không được bị gán source_cell_id vào IR"
    assert getattr(cell_r1_c1, "source_cell_id", None) is None, "cell_r1_c1 không được bị gán source_cell_id vào IR"

    # 5. Tất cả nét nằm trong trang
    assert_all_strokes_within_page_bounds(out_file, max_y=300.0 - 25.0 + 1e-3, min_y=25.0 - 5.0)


def test_bounding_box_anti_squash_no_degenerate_collinear(tmp_path):
    """Kiểm tra nét chữ sát mép trang không bị kẹp bẹt thành đoạn ngang collinear."""
    bank = _create_quality_test_bank(tmp_path)

    # Dòng chữ dài có đuôi ký tự như 'p', 'y', 'g'
    table = Table(
        rows=[
            TableRow(cells=[TableCell.from_text("Dong 1: p y g")]),
            TableRow(cells=[TableCell.from_text("Dong 2: p y g rat dai")]),
        ],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out_file = str(tmp_path / "table_anti_squash.xopp")

    opts = WriteOptions(
        paper="custom",
        paper_width=300.0,
        paper_height=250.0,
        margin_top=25.0,
        margin_bottom=25.0,
        line=25.0,
        jitter=0.0,
    )
    engine = DocumentLayoutEngine(bank, opts)
    engine.render(doc, out_file)

    # Đọc tệp XOPP và phân tích các nét
    with gzip.open(out_file, "rb") as f:
        xml_bytes = f.read()
    root = ET.fromstring(xml_bytes)

    max_allowed_y = 250.0 - 25.0
    for stroke_el in root.iter("stroke"):
        raw_pts = stroke_el.text.strip().split()
        coords = [float(x) for x in raw_pts]
        ys = coords[1::2]
        # Không có nét nào vượt quá mép trang
        assert all(y <= max_allowed_y + 1e-3 for y in ys)

        # Kiểm tra không có hiện tượng dồn điểm bẹt dí:
        # Nếu có từ 3 điểm trở lên chạm đúng max_allowed_y một cách nhân tạo
        clamped_points = [y for y in ys if abs(y - max_allowed_y) < 1e-4]
        assert len(clamped_points) <= 1, (
            f"Phát hiện {len(clamped_points)} điểm bị ép bẹt collinear tại mép trang y={max_allowed_y}!"
        )
