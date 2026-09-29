"""Kiểm thử tích hợp bộ đệm luồng PageBuffer phát trực tiếp các trang ra file .xopp."""
import gzip
import xml.etree.ElementTree as ET
import pytest

from chuviettay.controller.results import WriteOptions
from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.layout.engine import DocumentLayoutEngine
from chuviettay.layout.stream import PageBuffer


def test_page_buffer_context_manager(tmp_path):
    out = str(tmp_path / "stream_test.xopp")
    with PageBuffer(out, page_w=500.0, default_page_h=1000.0) as pb:
        pb.append_page(["<stroke/>"])
        pb.append_page(["<stroke/>", "<stroke/>"])
        assert pb.n_pages == 2

    assert (tmp_path / "stream_test.xopp").exists()

    with gzip.open(out, "rb") as f:
        root = ET.fromstring(f.read())
    pages = root.findall(".//page")
    assert len(pages) == 2


def test_document_layout_engine_streams_multi_page(tiny_bank, tmp_path):
    # Tạo tài liệu có nhiều đoạn văn vượt quá chiều cao 1 trang
    blocks = [Paragraph(inlines=[Text(f"Dòng văn bản thứ {i}")]) for i in range(150)]
    doc = Document(blocks=blocks)

    out = str(tmp_path / "multipage_stream.xopp")
    opts = WriteOptions(scale=1.0, jitter=0.0, line=30.0)
    engine = DocumentLayoutEngine(tiny_bank, opts)
    res = engine.render(doc, out)

    assert res.n_lines >= 150
    assert (tmp_path / "multipage_stream.xopp").exists()

    with gzip.open(out, "rb") as f:
        root = ET.fromstring(f.read())
    pages = root.findall(".//page")
    # Phải có ít nhất 2 trang
    assert len(pages) >= 2
    for p in pages:
        strokes = p.findall(".//stroke")
        assert len(strokes) > 0
