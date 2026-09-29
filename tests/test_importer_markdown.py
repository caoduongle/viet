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


def test_markdown_ordered_list_custom_start():
    """Kiểm tra danh sách có thứ tự bắt đầu từ một số khác 1 bảo toàn đúng start."""
    importer = MarkdownImporter()
    md = "4. Bước bốn\n5. Bước năm"
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 1
    assert isinstance(doc.blocks[0], ListBlock)
    list_blk = doc.blocks[0]
    assert list_blk.ordered is True
    assert list_blk.start == 4
    assert len(list_blk.items) == 2


def test_markdown_ordered_list_split_by_table():
    """Kiểm tra danh sách có thứ tự bị ngắt quãng bởi bảng không thụt lề bảo toàn đúng số đánh dấu 1..3 và 4..5."""
    importer = MarkdownImporter()
    md = """1. Sau `.query()`
2. heavy
3. Theo loài:

| species | n | p_heavy | mean_depth |
|---|---|---|---|
| Chinstrap | 4 | 0 | 18.825 |

4. Vẫn giống nếu...
5. Tương tự..."""
    res = importer.import_text(md)
    doc = res.document
    assert len(doc.blocks) == 3

    # Khối 1: List 1..3
    assert isinstance(doc.blocks[0], ListBlock)
    assert doc.blocks[0].ordered is True
    assert doc.blocks[0].start == 1
    assert len(doc.blocks[0].items) == 3

    # Khối 2: Table
    assert isinstance(doc.blocks[1], Table)

    # Khối 3: List 4..5 (Không bị reset về 1)
    assert isinstance(doc.blocks[2], ListBlock)
    assert doc.blocks[2].ordered is True
    assert doc.blocks[2].start == 4
    assert len(doc.blocks[2].items) == 2


def test_markdown_ordered_list_resilient_attributes():
    """Kiểm tra trích xuất start an toàn trước các cấu trúc dữ liệu attrs và giá trị phi số."""
    importer = MarkdownImporter()

    class DummyToken:
        def __init__(self, attrs=None):
            self.attrs = attrs

        def attrGet(self, name):
            if isinstance(self.attrs, dict):
                return self.attrs.get(name)
            return None

    # 1. Dictionary với chuỗi số
    tok_dict = DummyToken(attrs={"start": "12"})
    assert importer._extract_list_start(tok_dict) == 12

    # 2. Danh sách các cặp key-value
    tok_list = DummyToken(attrs=[("start", 7)])
    assert importer._extract_list_start(tok_list) == 7

    # 3. Giá trị phi số hoặc rác
    tok_invalid = DummyToken(attrs={"start": "invalid_value"})
    assert importer._extract_list_start(tok_invalid) == 1

    # 4. Token không có attrs
    tok_none = DummyToken(attrs=None)
    assert importer._extract_list_start(tok_none) == 1

