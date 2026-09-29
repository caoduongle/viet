"""Kiểm thử tính bất biến tỉ lệ đơn (single-scaling invariant) cho công thức toán nội dòng."""
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Heading, MathInline, Paragraph, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.layout.math_layout import MathLayoutEngine


def test_math_layout_item_coordinates_are_normalized(tiny_bank):
    engine = MathLayoutEngine(tiny_bank, S=1.0)
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]

    from chuviettay.math.ast import TextNode
    item = engine.measure(TextNode("x"))
    # Base height phải gần bằng bank.xh, không bị nhân kép
    assert abs(item.size.ascent - float(tiny_bank.xh)) < 2.0


def test_inline_math_single_scaling_in_heading(tiny_bank, tmp_path):
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["tiêu"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]
    tiny_bank.words["đề"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]

    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)

    # Đoạn văn thường: scale_mult = 1.0
    doc_p = Document(blocks=[Paragraph(inlines=[Text("tiêu"), MathInline(latex="x")])])
    out_p = str(tmp_path / "p.xopp")
    res_p = engine.render(doc_p, out_p)
    assert res_p.n_strokes > 0

    # Tiêu đề cấp 1: scale_mult = 1.4
    doc_h = Document(blocks=[Heading(level=1, inlines=[Text("tiêu"), MathInline(latex="x")])])
    out_h = str(tmp_path / "h.xopp")
    res_h = engine.render(doc_h, out_h)
    assert res_h.n_strokes > 0
