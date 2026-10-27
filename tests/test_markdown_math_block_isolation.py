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
    # Ô 1 là công thức math: x=1
    cell_0_inlines = table.rows[1].cells[0].blocks[0].inlines
    assert len(cell_0_inlines) == 1
    assert isinstance(cell_0_inlines[0], MathInline)
    assert cell_0_inlines[0].latex == "x=1"
    # Ô 2 là văn bản: 2
    cell_1_inlines = table.rows[1].cells[1].blocks[0].inlines
    assert len(cell_1_inlines) == 1
    assert isinstance(cell_1_inlines[0], Text)
    assert cell_1_inlines[0].text == "2"


def test_isolated_pipe_line_is_not_table(importer: MarkdownImporter):
    """[056] Dòng đơn độc lập '$$x=1$$ | 2' không có hàng phân cách '---|---' không phải bảng GFM."""
    text = "$$x=1$$ | 2"
    res = importer.import_text(text)
    blocks = res.document.blocks

    # Phải được tách thành MathBlock("x=1") và Paragraph("| 2")
    assert len(blocks) == 2, f"Kỳ vọng 2 blocks (MathBlock + Paragraph) nhưng nhận được: {blocks}"
    assert isinstance(blocks[0], MathBlock)
    assert blocks[0].latex == "x=1"
    assert isinstance(blocks[1], Paragraph)
    assert "| 2" in blocks[1].inlines[0].text


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

    # 6. [056] Code fence tilde lồng trong Blockquote (> ~~~latex) qua _normalize_math_delimiters và import_text
    fence_bq_tilde = "> ~~~latex\n> \\[x=1\\]\n> ~~~"
    assert MarkdownImporter._normalize_math_delimiters(fence_bq_tilde) == fence_bq_tilde
    res_bq = importer.import_text(fence_bq_tilde)
    assert not any(isinstance(b, MathBlock) for b in res_bq.document.blocks)

    # 7. [056] Code fence 4 backticks lồng trong Blockquote (>> ````)
    fence_bq_nested = ">> ````markdown\n>> ```\n>> \\[x=1\\]\n>> ````"
    assert MarkdownImporter._normalize_math_delimiters(fence_bq_nested) == fence_bq_nested
    res_bq_nested = importer.import_text(fence_bq_nested)
    assert not any(isinstance(b, MathBlock) for b in res_bq_nested.document.blocks)


def test_indented_code_block_preservation(importer: MarkdownImporter):
    """[056] Khối mã thụt lề 4 khoảng trắng (Indented Code Block) bảo toàn công thức \\[...\\] không bị đổi thành MathBlock."""
    # Khối mã thụt lề 4 dấu cách đứng sau dòng trống
    text = "Văn bản dẫn nhập\n\n    \\[x=1\\]\n    \\[y=2\\]\n\nĐoạn văn kết thúc"
    normalized = MarkdownImporter._normalize_math_delimiters(text)
    assert "\\[x=1\\]" in normalized
    assert "$$x=1$$" not in normalized

    res = importer.import_text(text)
    # Khối mã thụt lề được ghi nhận vào unsupported code_block, không tạo MathBlock
    assert not any(isinstance(b, MathBlock) for b in res.document.blocks)
    assert any("code_block" in u for u in res.unsupported)


def test_escaped_backtick_not_code_span(importer: MarkdownImporter):
    """[056] Dấu backtick bị thoát bởi gạch chéo ngược (\\`) không được coi là mở/đóng code span."""
    # 1. Backtick bị thoát (\`) không mở code span; code span thật `\[x=1\]` nằm phía sau
    text = "Dấu \\` không phải code nhưng `\\[x=1\\]` là code."
    spans = MarkdownImporter._find_code_spans(text)
    # Duy nhất đoạn `\[x=1\]` là code span
    assert len(spans) == 1
    code_text = text[spans[0][0] : spans[0][1]]
    assert code_text == "`\\[x=1\\]`"

    # Công thức trong code span được giữ nguyên, backtick thoát không làm vỡ
    normalized = MarkdownImporter._normalize_math_delimiters(text)
    assert "`\\[x=1\\]`" in normalized

    # 2. Hai gạch chéo ngược (\\\\`) -> gạch chéo tự thoát, backtick là hợp lệ mở code span
    text_even = "Dấu \\\\`code\\` bình thường."
    spans_even = MarkdownImporter._find_code_spans(text_even)
    assert len(spans_even) == 1


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
    """[056] 5,000 và 10,000 dòng tiền xử lý toàn diện (split_code, normalize, isolate, sanitize) với tỷ lệ tuyến tính (T2/T1 <= 3.5)."""
    import time
    lines_n = ["Dòng văn bản \\[a=1\\] và `code`\n$$unclosed_formula" for _ in range(2500)]
    input_n = "\n".join(lines_n)

    lines_2n = ["Dòng văn bản \\[a=1\\] và `code`\n$$unclosed_formula" for _ in range(5000)]
    input_2n = "\n".join(lines_2n)

    def run_pipeline(text: str) -> str:
        s1 = importer._normalize_math_delimiters(text)
        s2 = importer._isolate_display_math_blocks(s1)
        return importer._sanitize_html(s2)

    t0 = time.perf_counter()
    res_n = run_pipeline(input_n)
    t1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    res_2n = run_pipeline(input_2n)
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

