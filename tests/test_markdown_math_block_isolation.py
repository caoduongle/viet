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


# ==============================================================================
# Feature 058: Bảo vệ Indented Code, Nhận diện Bảng GFM chặt chẽ và Tuyến tính O(n)
# ==============================================================================

def test_indented_code_block_preservation_with_math_and_html(importer: MarkdownImporter):
    """[058-US3] Khối mã thụt lề chứa prefix:$$x=1$$, $$y=2$$, \\[z=3\\] và thẻ <b>tag</b> được bảo toàn 100%."""
    text = (
        "Đoạn văn mở đầu\n\n"
        "    prefix:$$x=1$$\n"
        "    $$y=2$$\n"
        "    \\[z=3\\]\n"
        "    <b>tag</b>\n\n"
        "Đoạn văn tiếp theo."
    )
    # Bước cô lập không được xé dòng khối mã thụt lề
    isolated = importer._isolate_display_math_blocks(text)
    assert "    prefix:$$x=1$$" in isolated
    assert "    $$y=2$$" in isolated
    assert "    <b>tag</b>" in isolated

    # Toàn bộ pipeline import_text()
    res = importer.import_text(text)
    # Không sinh bất kỳ MathBlock nào từ bên trong khối mã thụt lề
    assert not any(isinstance(b, MathBlock) for b in res.document.blocks)
    # 2 Paragraphs cho văn bản mở đầu và tiếp theo
    paragraphs = [b for b in res.document.blocks if isinstance(b, Paragraph)]
    assert len(paragraphs) == 2
    assert "Đoạn văn mở đầu" in paragraphs[0].inlines[0].text
    assert "Đoạn văn tiếp theo." in paragraphs[1].inlines[0].text
    assert any("code_block" in u for u in res.unsupported)


def test_indented_code_block_with_blank_lines_and_unclosed_math(importer: MarkdownImporter):
    """[058-US3] Khối mã thụt lề có dòng trống xen giữa và công thức dở dang không làm hỏng đoạn văn tiếp theo."""
    text = (
        "Đoạn văn 1\n\n"
        "    dòng 1: $$x=1\n\n"
        "    dòng 2: y=2$$\n\n"
        "Đoạn văn tiếp theo:\n"
        "$$a=b$$"
    )
    res = importer.import_text(text)
    # Đoạn văn tiếp theo vẫn tách được MathBlock("a=b")
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks) == 1
    assert math_blocks[0].latex == "a=b"


def test_lazy_paragraph_continuation_math_isolation(importer: MarkdownImporter):
    """[058-US3] Dòng tiếp nối đoạn văn thụt 4 khoảng trắng chứa $$x=1$$ (không có dòng trống) vẫn tách thành MathBlock."""
    text = "Đoạn văn 1\n    $$x=1$$"
    res = importer.import_text(text)
    blocks = res.document.blocks
    assert len(blocks) == 2
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "x=1"


def test_table_preceded_by_pipe_paragraph_with_math(importer: MarkdownImporter):
    """[058-US4] Đoạn văn chứa | và $$x=1$$ đứng ngay trước bảng GFM trong cùng nhóm dòng không bị nuốt vào bảng."""
    text = (
        "ta có | điều kiện:$$x=1$$\n"
        "Col 1 | Col 2\n"
        "---|---\n"
        "val 1 | val 2"
    )
    res = importer.import_text(text)
    blocks = res.document.blocks

    assert len(blocks) == 3
    assert isinstance(blocks[0], Paragraph)
    assert "ta có | điều kiện:" in blocks[0].inlines[0].text
    assert isinstance(blocks[1], MathBlock)
    assert blocks[1].latex == "x=1"
    assert isinstance(blocks[2], Table)
    assert len(blocks[2].rows) == 2


def test_fake_delimiter_row_mismatched_columns(importer: MarkdownImporter):
    """[058-US4] Dòng chứa | và $$x=1$$ đứng trước chuỗi giả phân cách không khớp số cột không bị coi là bảng."""
    text = (
        "$$x=1$$ | văn bản thường\n"
        "---|---|---"
    )
    res = importer.import_text(text)
    blocks = res.document.blocks
    # Không thành Table vì hàng trên không khớp số cột với hàng phân cách 3 cột
    assert not any(isinstance(b, Table) for b in blocks)
    assert any(isinstance(b, MathBlock) for b in blocks)


def test_adversarial_complexity_unclosed_backticks_and_blockquotes(importer: MarkdownImporter):
    """[058-US5] Đo độ phức tạp vô điều kiện trên đầu vào bất lợi (nhiều blockquote và nhiều backtick không đóng)."""
    import time

    def make_adversarial_text(num_lines: int) -> str:
        lines = []
        for i in range(num_lines):
            mod = i % 5
            if mod == 0:
                lines.append(f"> > `unclosed_line_{i} với \\[a=1\\]")
            elif mod == 1:
                lines.append(f"> ``double_unclosed_{i} và $$math")
            elif mod == 2:
                lines.append(f">> > ````quad_{i}")
            elif mod == 3:
                lines.append(f"    indented_code_{i} \\[x=1\\]")
            else:
                lines.append(f"dòng thường {i} với `span` và $$f$$")
        return "\n".join(lines)

    text_n = make_adversarial_text(1000)
    text_2n = make_adversarial_text(2000)
    text_4n = make_adversarial_text(4000)

    def run_pipeline(txt: str) -> str:
        return importer._sanitize_html(importer._isolate_display_math_blocks(importer._normalize_math_delimiters(txt)))

    # Warmup
    run_pipeline(text_n)

    # Đo N (lặp 5 lần để đảm bảo t_n đo lường được và ổn định)
    t0 = time.perf_counter()
    for _ in range(5):
        run_pipeline(text_n)
    t_n = (time.perf_counter() - t0) / 5

    # Đo 2N
    t0 = time.perf_counter()
    for _ in range(3):
        run_pipeline(text_2n)
    t_2n = (time.perf_counter() - t0) / 3

    # Đo 4N
    t0 = time.perf_counter()
    for _ in range(2):
        run_pipeline(text_4n)
    t_4n = (time.perf_counter() - t0) / 2

    # Tỷ lệ tăng giữa 2N và N, 4N và N: thuật toán tuyến tính O(n) xấp xỉ 2.0x và 4.0x, trần an toàn <= 6.0x
    assert t_2n > 0
    ratio = t_4n / max(t_n, 0.001)
    assert ratio <= 6.0, f"Tỷ lệ tăng thời gian ({ratio:.2f}x) vượt ngưỡng tuyến tính (t_n={t_n:.3f}s, t_4n={t_4n:.3f}s)"
    assert t_4n < 1.0, f"Thời gian xử lý 4,000 dòng bất lợi vượt ngưỡng 1.0s ({t_4n:.3f}s)"

