"""Kiểm thử tích hợp luồng Document IR: Importer -> Layout Engine -> .xopp."""
import gzip
import os
import xml.etree.ElementTree as ET
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.importer.txt_importer import TxtImporter


def test_write_document_from_ir(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="xin chào bạn")]),
        Paragraph(inlines=[Text(text="ba bà chào")]),
    ])

    out = str(tmp_path / "doc_test.xopp")
    opts = WriteOptions(seed=42)
    res = ctl.write_document(doc, opts, out)

    assert res.n_lines >= 2
    assert res.n_strokes > 0

    # Kiểm tra tính hợp lệ của file XML đã nén
    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    assert root.tag == "xournal"
    pages = root.findall("page")
    assert len(pages) >= 1
    layer = pages[0].find("layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    assert len(strokes) > 0


def test_write_document_from_txt_importer(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    importer = TxtImporter()
    import_res = importer.import_text("xin ba bà\n\nxin chào")
    out = str(tmp_path / "txt_importer_test.xopp")
    res = ctl.write_document(import_res.document, WriteOptions(seed=7), out)

    assert res.n_lines >= 2
    assert res.n_strokes > 0


def test_write_empty_document(tiny_bank_path, tmp_path):
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[])
    out = str(tmp_path / "empty.xopp")
    res = ctl.write_document(doc, WriteOptions(), out)

    assert res.n_lines == 0
    assert res.n_strokes == 0
    # Phải có 1 trang giấy trắng hợp lệ
    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    pages = root.findall("page")
    assert len(pages) == 1


def test_write_document_with_table(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import Table, TableBorder, TableCell, TableRow
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Bảng điểm danh:")]),
        Table(
            rows=[
                TableRow(cells=[TableCell.from_text("Tên"), TableCell.from_text("Chào")]),
                TableRow(cells=[TableCell.from_text("ba"), TableCell.from_text("bà")]),
            ],
            border_style=TableBorder.ALL,
        ),
    ])

    out = str(tmp_path / "table_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    layer = root.find("page/layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    # Phải có cả nét viền và nét chữ
    assert len(strokes) >= 6


def test_write_document_with_math_block(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import MathBlock
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[Text(text="Công thức nghiệm:")]),
        MathBlock(latex="x = \\frac{-b}{2a}"),
    ])

    out = str(tmp_path / "math_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    layer = root.find("page/layer")
    assert layer is not None
    strokes = layer.findall("stroke")
    assert len(strokes) >= 1


def test_write_document_with_list_block(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import ListBlock
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        ListBlock(
            ordered=True,
            items=[
                [Paragraph(inlines=[Text(text="mục thứ nhất")])],
                [Paragraph(inlines=[Text(text="mục thứ hai")])],
            ],
            start=1,
        ),
        ListBlock(
            ordered=False,
            items=[
                [Paragraph(inlines=[Text(text="gạch đầu dòng A")])],
                [Paragraph(inlines=[Text(text="gạch đầu dòng B")])],
            ],
        ),
    ])

    out = str(tmp_path / "list_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_lines >= 4
    assert res.n_strokes > 0


def test_write_document_with_inline_math_and_symbols(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import MathInline, Symbol
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    doc = Document(blocks=[
        Paragraph(inlines=[
            Text(text="xin chào"),
            MathInline(latex="\\Delta = b^2 - 4ac"),
            Symbol(symbol="≤"),
            Text(text="1"),
        ])
    ])

    out = str(tmp_path / "inline_math_pipeline.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_strokes > 0
    assert "≤" in res.missing_symbols
    assert res.missing_symbols["≤"] >= 1


def test_write_document_table_pagination(tiny_bank_path, tmp_path):
    from chuviettay.document.ir import Table, TableBorder, TableCell, TableRow
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    # Bảng 5 hàng với khoảng cách dòng 800pt -> tổng chiều cao > 3000pt (MAXH) -> ngắt trang
    rows = [TableRow(cells=[TableCell.from_text(f"xin {i}"), TableCell.from_text(f"ba {i}")]) for i in range(5)]
    doc = Document(blocks=[Table(rows=rows, border_style=TableBorder.ALL)])

    out = str(tmp_path / "paginated_table.xopp")
    res = ctl.write_document(doc, WriteOptions(line=800, seed=12), out)
    assert res.n_tables == 1
    assert res.n_strokes > 0

    raw = gzip.decompress(open(out, "rb").read())
    root = ET.fromstring(raw)
    pages = root.findall("page")
    assert len(pages) > 1, "Bảng lớn vượt quá chiều cao trang phải được chia thành nhiều trang"
    for p in pages:
        layer = p.find("layer")
        assert layer is not None
        strokes = layer.findall("stroke")
        assert len(strokes) > 0, "Mỗi trang phải có nét viền và nội dung ô"


def test_write_document_split_ordered_list_numbering(tiny_bank_path, tmp_path):
    """Kiểm thử tích hợp: danh sách có thứ tự bị ngắt bởi bảng giữ nguyên số thứ tự 1..5 trong pipeline Document."""
    pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
    from chuviettay.importer.markdown_importer import MarkdownImporter
    importer = MarkdownImporter()
    md = """1. Mục một
2. Mục hai
3. Mục ba

| Cột A | Cột B |
|---|---|
| A | B |

4. Mục bốn
5. Mục năm"""
    res_import = importer.import_text(md)
    doc = res_import.document
    assert len(doc.blocks) == 3
    assert doc.blocks[0].start == 1
    assert doc.blocks[2].start == 4

    ctl = AppController(tiny_bank_path)
    ctl.load_bank()
    out = str(tmp_path / "split_list.xopp")
    res = ctl.write_document(doc, WriteOptions(seed=12), out)
    assert res.n_lines >= 5
    assert res.n_strokes > 0
    assert os.path.exists(out)


