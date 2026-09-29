"""Kiểm thử bộ nạp tài liệu MarkdownImporter."""
import pytest

pytest.importorskip("markdown_it", reason="Cần cài đặt markdown-it-py để chạy kiểm thử định dạng Markdown")
pytest.importorskip("mdit_py_plugins", reason="Cần cài đặt mdit-py-plugins để chạy kiểm thử định dạng Markdown")

from chuviettay.document.ir import Heading, ListBlock, MathBlock, MathInline, Paragraph, Table, Text
from chuviettay.importer.dependency import OptionalDependencyError
from chuviettay.importer.markdown_importer import MarkdownImporter



def test_markdown_headings():
    importer = MarkdownImporter()
    md = "# Tiêu đề 1\n## Tiêu đề 2\n### Tiêu đề 3"
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 3
    assert isinstance(doc.blocks[0], Heading)
    assert doc.blocks[0].level == 1
    assert doc.blocks[0].inlines[0].text == "Tiêu đề 1"
    assert doc.blocks[1].level == 2
    assert doc.blocks[2].level == 3


def test_markdown_paragraph_and_lists():
    importer = MarkdownImporter()
    md = "Đây là một đoạn văn.\n\n- Mục 1\n- Mục 2\n\n1. Thứ nhất\n2. Thứ hai"
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 3
    assert isinstance(doc.blocks[0], Paragraph)
    assert doc.blocks[0].inlines[0].text == "Đây là một đoạn văn."

    # Bullet list
    assert isinstance(doc.blocks[1], ListBlock)
    assert not doc.blocks[1].ordered
    assert len(doc.blocks[1].items) == 2

    # Numbered list
    assert isinstance(doc.blocks[2], ListBlock)
    assert doc.blocks[2].ordered
    assert len(doc.blocks[2].items) == 2


def test_markdown_gfm_table():
    importer = MarkdownImporter()
    md = """
| Cột 1 | Cột 2 |
| :--- | :---: |
| Dòng 1 | Giá trị 1 |
| Dòng 2 | Giá trị 2 |
"""
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 1
    table = doc.blocks[0]
    assert isinstance(table, Table)
    assert len(table.rows) == 3  # 1 header + 2 body rows
    assert table.col_alignments == ["left", "center"]
    # Check cell text
    assert table.rows[0].cells[0].blocks[0].inlines[0].text == "Cột 1"
    assert table.rows[1].cells[1].blocks[0].inlines[0].text == "Giá trị 1"


def test_markdown_math_syntax():
    importer = MarkdownImporter()
    md = "Phương trình $a^2 + b^2 = c^2$ nội dòng.\n\n$$\\frac{-b \\pm \\sqrt{\\Delta}}{2a}$$"
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 2

    # Paragraph with inline math
    p = doc.blocks[0]
    assert isinstance(p, Paragraph)
    assert any(isinstance(n, MathInline) for n in p.inlines)
    math_inline = [n for n in p.inlines if isinstance(n, MathInline)][0]
    assert math_inline.latex == "a^2 + b^2 = c^2"

    # Block math
    mb = doc.blocks[1]
    assert isinstance(mb, MathBlock)
    assert "\\frac{-b \\pm \\sqrt{\\Delta}}{2a}" in mb.latex


def test_markdown_raw_html_sanitized():
    importer = MarkdownImporter()
    md = "Xin chào <script>alert('xss')</script> thế giới <div style='color:red'>!</div>"
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 1
    p = doc.blocks[0]
    full_text = "".join(n.text for n in p.inlines if isinstance(n, Text))
    assert "<script>" not in full_text
    assert "</script>" not in full_text
    assert "<div" not in full_text
    assert "Xin chào" in full_text
    assert "thế giới" in full_text


def test_markdown_importer_missing_dependency(monkeypatch):
    import chuviettay.importer.markdown_importer as mod

    def fake_require(name, feature_desc="", extra="docs"):
        raise OptionalDependencyError("Thiếu thư viện", package_name=name)

    monkeypatch.setattr(mod, "require_dependency", fake_require)

    with pytest.raises(OptionalDependencyError):
        importer = MarkdownImporter()
        importer.import_text("# Test")
