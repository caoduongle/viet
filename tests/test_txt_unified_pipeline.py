"""Kiểm thử chu trình xử lý tệp văn bản thuần (.txt) qua Document IR và bảo toàn dòng trống."""
import gzip
import xml.etree.ElementTree as ET
import pytest

from chuviettay.cli import main
from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Paragraph, Text
from chuviettay.importer.txt_importer import TxtImporter
from chuviettay.layout.engine import DocumentLayoutEngine


def test_txt_importer_preserves_blank_lines():
    raw_text = "Đoạn 1\n\nĐoạn 2\n\n\nĐoạn 3"
    importer = TxtImporter()
    res = importer.import_text(raw_text)

    blocks = res.document.blocks
    assert len(blocks) == 6
    assert isinstance(blocks[0], Paragraph) and blocks[0].inlines[0].text == "Đoạn 1"
    assert isinstance(blocks[1], Paragraph) and len(blocks[1].inlines) == 0
    assert isinstance(blocks[2], Paragraph) and blocks[2].inlines[0].text == "Đoạn 2"
    assert isinstance(blocks[3], Paragraph) and len(blocks[3].inlines) == 0
    assert isinstance(blocks[4], Paragraph) and len(blocks[4].inlines) == 0
    assert isinstance(blocks[5], Paragraph) and blocks[5].inlines[0].text == "Đoạn 3"


def test_document_layout_engine_empty_paragraph_spacing(tiny_bank, tmp_path):
    tiny_bank.words["A"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["B"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]

    importer = TxtImporter()

    # 1. Tài liệu không có dòng trống
    doc_tight = importer.import_text("A\nB").document
    out_tight = str(tmp_path / "tight.xopp")
    opts = WriteOptions(scale=1.0, jitter=0.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    engine.render(doc_tight, out_tight)

    # 2. Tài liệu có dòng trống ở giữa
    doc_spaced = importer.import_text("A\n\nB").document
    out_spaced = str(tmp_path / "spaced.xopp")
    engine2 = DocumentLayoutEngine(tiny_bank, opts)
    engine2.render(doc_spaced, out_spaced)

    def extract_y_coords(xopp_file):
        with gzip.open(xopp_file, "rb") as f:
            root = ET.fromstring(f.read())
        strokes = [s.text.strip().split() for s in root.findall(".//stroke") if len(s.text.strip().split()) == 6]
        return [float(st[1]) for st in strokes]

    ys_tight = extract_y_coords(out_tight)
    ys_spaced = extract_y_coords(out_spaced)

    assert len(ys_tight) == 2
    assert len(ys_spaced) == 2

    # y của "A" ở cả hai file là giống nhau
    assert abs(ys_tight[0] - ys_spaced[0]) < 1e-3

    # Khoảng cách giữa A và B trong bản có dòng trống phải lớn hơn bản không có dòng trống
    dist_tight = ys_tight[1] - ys_tight[0]
    dist_spaced = ys_spaced[1] - ys_spaced[0]
    assert dist_spaced > dist_tight + engine.line_h * 0.7


def test_cli_write_txt_file_uses_document_ir(tmp_path, tiny_bank_path, capsys):
    txt_file = tmp_path / "spacing.txt"
    txt_file.write_text("xin\n\nchào", encoding="utf-8")
    out_xopp = tmp_path / "out_spacing.xopp"

    ret = main([
        "--bank", str(tiny_bank_path),
        "write",
        "-f", str(txt_file),
        "-o", str(out_xopp),
        "--seed", "42",
    ])
    assert ret == 0
    assert out_xopp.exists()

    with gzip.open(str(out_xopp), "rb") as f:
        root = ET.fromstring(f.read())
    strokes = root.findall(".//stroke")
    assert len(strokes) > 0
