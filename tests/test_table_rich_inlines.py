"""Kiểm thử bố cục các phần tử nội dòng (toán học, ký hiệu, ngắt dòng) bên trong ô bảng."""
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, MathInline, Paragraph, Symbol, Table, TableBorder, TableCell, TableRow, Text
from chuviettay.layout.engine import DocumentLayoutEngine


def test_table_cell_with_math_inline_and_symbols(tiny_bank, tmp_path):
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["giá"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]
    tiny_bank.words["trị"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 15.0}]

    cell = TableCell(blocks=[
        Paragraph(inlines=[
            Text("giá trị"),
            MathInline(latex="x^2"),
            Symbol(symbol="≤"),
            Text("10"),
        ])
    ])
    table = Table(
        rows=[TableRow(cells=[cell])],
        border_style=TableBorder.ALL,
    )
    doc = Document(blocks=[table])
    out = str(tmp_path / "table_math.xopp")

    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_tables == 1
    assert res.n_strokes > 4, "Phải sinh cả nét viền bảng và các nét chữ, toán học bên trong ô"
