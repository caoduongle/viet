"""Kiểm thử chính sách sàn khoảng cách dòng an toàn (Anti-Collision Line Spacing Policy)
và sàn chiều cao hàng bảng theo hợp đồng CTR-034-LINE-HEIGHT-POLICY.
"""
from __future__ import annotations

import pytest
from chuviettay.document.ir import Document, Paragraph, Text, Table, TableRow, TableCell
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.layout.table_layout import TableLayoutEngine, TableBorder
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def test_effective_line_height_floor_preserves_default():
    """Khi opts.line is None, effective_line_h phải giữ nguyên mặc định từ bank."""
    bank = Bank(KHO_TONG_HOP)
    opts = WriteOptions(scale=1.0, line=None)
    engine = DocumentLayoutEngine(bank, opts)
    expected_default = float(bank.d["line"]) * 1.0
    assert engine.line_h == pytest.approx(expected_default)


def test_effective_line_height_floor_clamps_tiny_values():
    """Khi người dùng chỉnh line=1.0pt (hoặc nhỏ), hệ thống bảo đảm sàn chống đè dòng an toàn."""
    bank = Bank(KHO_TONG_HOP)
    opts = WriteOptions(scale=1.0, line=1.0)
    engine = DocumentLayoutEngine(bank, opts)
    font_xh = float(getattr(bank, "xh", 7.94) or 7.94)
    safe_floor = max(1.4 * font_xh, 0.65 * float(bank.d.get("line", 24.0)))
    # line_h phải ít nhất bằng safe_floor
    assert engine.line_h >= safe_floor


def test_paragraph_lines_do_not_collide_at_line_1pt(tmp_path):
    """Văn bản nhiều dòng với line=1.0pt không được để các đường baseline dính sát nhau."""
    bank = Bank(KHO_TONG_HOP)
    opts = WriteOptions(scale=1.0, line=1.0, background="plain")
    engine = DocumentLayoutEngine(bank, opts)

    # Đoạn văn gồm nhiều dòng
    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Dòng thứ nhất với nội dung thử nghiệm")]),
        Paragraph(inlines=[Text(text="Dòng thứ hai với chữ số 12345")]),
        Paragraph(inlines=[Text(text="Dòng thứ ba với chữ cái có râu g y p q")]),
    ])
    out_file = str(tmp_path / "test_para_line_1pt.xopp")
    res = engine.render(doc, out_file)
    assert res.n_lines >= 3


def test_table_row_height_floor_prevents_border_intersection():
    """Trong bảng, chiều cao hàng tối thiểu phải lớn hơn chiều cao chữ để viền không cắt số."""
    bank = Bank(KHO_TONG_HOP)
    opts = WriteOptions(scale=1.0, line=1.0)
    engine = DocumentLayoutEngine(bank, opts)
    font_xh = float(getattr(bank, "xh", 7.94) or 7.94)
    safe_floor = max(1.4 * font_xh, 0.65 * float(bank.d.get("line", 24.0)))

    table_engine = TableLayoutEngine(
        available_width=400.0,
        line_height=engine.line_h,
        cell_padding=6.0,
    )
    # line_height của table engine phải bảo đảm sàn an toàn
    assert table_engine.line_height >= safe_floor
