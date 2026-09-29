"""Kiểm thử bộ nạp tài liệu văn bản thuần TxtImporter."""
import pytest
from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.importer.txt_importer import TxtImporter


def test_txt_importer_single_paragraph():
    importer = TxtImporter()
    res = importer.import_text("Xin chào Việt Nam")
    assert isinstance(res.document, Document)
    assert len(res.document.blocks) == 1
    p = res.document.blocks[0]
    assert isinstance(p, Paragraph)
    assert len(p.inlines) == 1
    assert p.inlines[0].text == "Xin chào Việt Nam"
    assert res.warnings == []
    assert res.unsupported == []


def test_txt_importer_multiple_paragraphs():
    importer = TxtImporter()
    raw = "Đoạn một\n\nĐoạn hai dòng một\nĐoạn hai dòng hai"
    res = importer.import_text(raw)
    assert len(res.document.blocks) == 3
    assert res.document.blocks[0].inlines[0].text == "Đoạn một"
    assert res.document.blocks[1].inlines[0].text == "Đoạn hai dòng một"
    assert res.document.blocks[2].inlines[0].text == "Đoạn hai dòng hai"


def test_txt_importer_empty_text():
    importer = TxtImporter()
    res = importer.import_text("   \n\n   ")
    assert len(res.document.blocks) == 0


def test_txt_importer_import_file(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("Dòng 1\nDòng 2", encoding="utf-8")
    importer = TxtImporter()
    res = importer.import_file(str(f))
    assert len(res.document.blocks) == 2
    assert res.document.blocks[0].inlines[0].text == "Dòng 1"
    assert res.document.blocks[1].inlines[0].text == "Dòng 2"
