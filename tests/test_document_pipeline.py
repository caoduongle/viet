"""Kiểm thử tích hợp luồng Document IR: Importer -> Layout Engine -> .xopp."""
import gzip
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

