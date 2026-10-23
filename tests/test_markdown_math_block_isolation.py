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


def test_gfm_compact_table_math_first_cell(importer: MarkdownImporter):
    """[055] Bảng GFM compact không có | ở hai đầu, ô đầu tiên bắt đầu bằng $$ không bị xé dòng."""
    text = "Col | Val\n---|---\n$$x=1$$ | 2"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 1, f"Bảng compact bị xé thành nhiều block: {blocks}"
    assert isinstance(blocks[0], Table)
    table = blocks[0]
    assert len(table.rows) == 2
    # Hàng 1 (tiêu đề): Col, Val
    assert table.rows[0].cells[0].blocks[0].inlines[0].text == "Col"
    assert table.rows[0].cells[1].blocks[0].inlines[0].text == "Val"
    # Hàng 2 (dữ liệu): $$x=1$$, 2
    assert len(table.rows[1].cells) == 2


def test_math_block_containing_internal_pipe(importer: MarkdownImporter):
    """[055] Công thức display chứa ký tự | nội bộ ($$|x|=1$$) vẫn là MathBlock, không phải Table."""
    text = "$$\\int |x| dx = 1$$"
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 1
    assert isinstance(blocks[0], MathBlock)
    assert "\\int |x| dx = 1" in blocks[0].latex


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


# ==============================================================================
# Feature 054: Gia cố bảo vệ code fence, tính tuyến tính O(n) và CRLF
# ==============================================================================

def test_code_fence_preservation(importer: MarkdownImporter):
    """Bảo toàn 100% nội dung bên trong code fence (3, 4+ backticks và tildes)."""
    # 1. Code fence 3 backticks chứa prefix:$$...$$
    fence_3 = "```latex\nprefix:$$x=1$$\n```"
    isolated_3 = MarkdownImporter._isolate_display_math_blocks(fence_3)
    assert isolated_3 == fence_3

    # 2. Code fence 4 backticks
    fence_4 = "````markdown\nprefix:$$x=1$$\n```\nvan_ban\n````"
    isolated_4 = MarkdownImporter._isolate_display_math_blocks(fence_4)
    assert isolated_4 == fence_4

    # 3. Code fence tilde ~~~
    fence_tilde = "~~~math\nprefix:$$x=1$$\n~~~"
    isolated_tilde = MarkdownImporter._isolate_display_math_blocks(fence_tilde)
    assert isolated_tilde == fence_tilde

    # 4. Unclosed code fence ở cuối file
    fence_unclosed = "```python\nprefix:$$x=1$$\n"
    isolated_unclosed = MarkdownImporter._isolate_display_math_blocks(fence_unclosed)
    assert isolated_unclosed == fence_unclosed

    # 5. [055] Code fence 4 backticks chứa dòng 3 backticks và \[x=1\] qua _normalize_math_delimiters và import_text
    fence_nested = "````markdown\n```\n\\[x=1\\]\n````"
    assert MarkdownImporter._normalize_math_delimiters(fence_nested) == fence_nested
    res_fence = importer.import_text(fence_nested)
    assert not any(isinstance(b, MathBlock) for b in res_fence.document.blocks)


def test_code_span_preservation(importer: MarkdownImporter):
    """Đoạn mã nội dòng chứa $$ không bị nhận nhầm thành display math."""
    # 1. Đoạn mã 1 backtick
    code_span = "Sử dụng mã `prefix:$$x=1$$` để minh họa."
    isolated = MarkdownImporter._isolate_display_math_blocks(code_span)
    assert isolated == code_span

    # 2. [055] Đoạn mã 2 backticks chứa $$ qua _isolate_display_math_blocks và import_text
    code_span_2 = "Sử dụng mã ``prefix:$$x=1$$`` để minh họa."
    isolated_2 = MarkdownImporter._isolate_display_math_blocks(code_span_2)
    assert isolated_2 == code_span_2
    res_span = importer.import_text(code_span_2)
    assert len(res_span.document.blocks) == 1
    assert not any(isinstance(b, MathBlock) for b in res_span.document.blocks)


def test_linear_scalability_unclosed_display_math(importer: MarkdownImporter):
    """[055] 5,000 và 10,000 dòng mở $$ không đóng xử lý với tỷ lệ tuyến tính (T2/T1 <= 3.5)."""
    import time
    lines_n = ["Dòng văn bản\n$$unclosed_formula" for _ in range(2500)]
    input_n = "\n".join(lines_n)

    lines_2n = ["Dòng văn bản\n$$unclosed_formula" for _ in range(5000)]
    input_2n = "\n".join(lines_2n)

    t0 = time.perf_counter()
    res_n = MarkdownImporter._isolate_display_math_blocks(input_n)
    t1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    res_2n = MarkdownImporter._isolate_display_math_blocks(input_2n)
    t2 = time.perf_counter() - t0

    assert len(res_n) > 0
    assert len(res_2n) > 0

    # Tỷ lệ tăng thời gian giữa 2N và N: thuật toán tuyến tính xấp xỉ 2.0x, trần an toàn <= 3.5x
    if t1 > 0.01:
        ratio = t2 / t1
        assert ratio <= 3.5, f"Tỷ lệ tăng thời gian ({ratio:.2f}x) vượt ngưỡng tuyến tính (t1={t1:.3f}s, t2={t2:.3f}s)"

    # Ngưỡng trần an toàn chống treo (2.0s) để tránh flaky trên runner CI chậm
    assert t2 < 2.0, f"Thời gian xử lý 10,000 dòng vượt ngưỡng trần an toàn ({t2:.3f}s)"


def test_crlf_windows_line_endings_safety(importer: MarkdownImporter):
    """Chuẩn hóa an toàn ngắt dòng CRLF kiểu Windows."""
    text_crlf = "Dòng 1\r\n$$\\sum_{j=1}^9 x_j = 1$$\r\nDòng 2"
    res = importer.import_text(text_crlf)
    blocks = res.document.blocks

    assert len(blocks) == 3
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "\\sum_{j=1}^9 x_j = 1"
    assert isinstance(blocks[2], Paragraph)

