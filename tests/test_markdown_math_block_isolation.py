"""Kiểm thử tự động cho tính năng nhận diện khối công thức toán display trên dòng mới
và ngăn ngừa đè nét cận bên của toán tử lớn (053-markdown-math-block-isolation).
"""
from __future__ import annotations

import pytest

from chuviettay.document.ir import MathBlock, MathInline, Paragraph, Table, Text
from chuviettay.importer.markdown_importer import MarkdownImporter
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math.parser import parse_latex_math
from chuviettay.model.bank import Bank


@pytest.fixture
def importer() -> MarkdownImporter:
    return MarkdownImporter()


# ==============================================================================
# Phase 3 / US1: Nhận diện MathBlock trên dòng mới không cần dòng trống (Ảnh 2)
# ==============================================================================

def test_newline_math_block_basic(importer: MarkdownImporter):
    """Ảnh 2: a\\n$$...$$ phải tạo ra Paragraph('a') và MathBlock(...)."""
    text = "a\n$$\\sum_{j=1}^9 P(D = j) = 1$$\nb"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 3
    assert isinstance(blocks[0], Paragraph)
    assert blocks[0].inlines[0].text == "a"

    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "\\sum_{j=1}^9 P(D = j) = 1"

    assert isinstance(blocks[2], Paragraph)
    assert blocks[2].inlines[0].text == "b"


def test_newline_math_block_multiple_consecutive(importer: MarkdownImporter):
    """Nhiều khối $$...$$ liên tiếp trên các dòng riêng biệt không có dòng trống."""
    text = "Dòng 1\n$$x = 1$$\n$$y = 2$$\nDòng 2"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 4
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "x = 1"
    assert isinstance(blocks[2], MathBlock)
    assert blocks[2].latex == "y = 2"
    assert isinstance(blocks[3], Paragraph)


def test_newline_math_block_multiline(importer: MarkdownImporter):
    """Khối toán mở $$ ở 1 dòng và đóng $$ ở dòng khác."""
    text = "Tiêu đề\n$$\nx = 1\ny = 2\n$$\nKết thúc"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 3
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[1], MathBlock)
    assert "x = 1" in blocks[1].latex
    assert isinstance(blocks[2], Paragraph)


def test_newline_math_block_in_list(importer: MarkdownImporter):
    """Khối toán $$...$$ thụt lề trong danh sách không bị văng ra ngoài."""
    text = "- Mục 1\n  $$x = 1$$\n- Mục 2"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 1
    # Danh sách vẫn là 1 ListBlock duy nhất có 2 items
    list_blk = blocks[0]
    assert hasattr(list_blk, "items")
    assert len(list_blk.items) == 2


def test_gfm_table_math_not_broken(importer: MarkdownImporter):
    """Bảng GFM chứa $$ trong ô không được chèn dòng trống làm hỏng bảng."""
    text = "| Col 1 | Col 2 |\n|---|---|\n| a | $$\\sum_{i=1}^n x_i$$ |"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 1
    assert isinstance(blocks[0], Table)
    # Bảng gồm 2 hàng: hàng tiêu đề và hàng dữ liệu
    assert len(blocks[0].rows) == 2


# ==============================================================================
# Phase 5 / US3: Dấu hai chấm dẫn nhập và các trường hợp biên cú pháp
# ==============================================================================

def test_colon_preceded_math_block(importer: MarkdownImporter):
    """ta có:$$...$$ được tách thành Paragraph('ta có:') và MathBlock(...)."""
    text = "ta có:$$\\sum_{j=1}^9 P(D = j) = 1$$"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 2
    assert isinstance(blocks[0], Paragraph)
    assert "ta có:" in blocks[0].inlines[0].text
    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "\\sum_{j=1}^9 P(D = j) = 1"


def test_trailing_punctuation_math_block(importer: MarkdownImporter):
    """$$...$$, với dấu phẩy hoặc chấm bám liền sau $$."""
    text = "$$\\sum_{j=1}^9 x_j = 1$$, với mọi j."
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 2
    assert isinstance(blocks[0], MathBlock)
    assert blocks[0].latex == "\\sum_{j=1}^9 x_j = 1"
    assert isinstance(blocks[1], Paragraph)


def test_unclosed_math_delimiter_safe(importer: MarkdownImporter):
    """Công thức dở dang chưa đóng $$ không làm treo trình phân tích."""
    text = "a\n$$\\sum_{j=1}^9"
    res = importer.import_text(text)
    blocks = res.document.blocks
    assert len(blocks) >= 1
