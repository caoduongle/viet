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
    import gc
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

    was_gc_enabled = gc.isenabled()
    gc.collect()
    try:
        gc.disable()
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
        for _ in range(3):
            run_pipeline(text_4n)
        t_4n = (time.perf_counter() - t0) / 3
    finally:
        if was_gc_enabled:
            gc.enable()
        else:
            gc.disable()

    # Tỷ lệ tăng giữa 2N và N, 4N và N: thuật toán tuyến tính O(n) xấp xỉ 2.0x và 4.0x, trần an toàn <= 6.0x
    assert t_2n > 0
    ratio = t_4n / max(t_n, 0.001)
    assert ratio <= 6.0, f"Tỷ lệ tăng thời gian ({ratio:.2f}x) vượt ngưỡng tuyến tính (t_n={t_n:.3f}s, t_4n={t_4n:.3f}s)"
    assert t_4n < 1.0, f"Thời gian xử lý 4,000 dòng bất lợi vượt ngưỡng 1.0s ({t_4n:.3f}s)"


# ==============================================================================
# Feature 059: Bảo toàn Phụ thuộc Tùy chọn, Đồng bộ Code Fence & Đối kháng Blockquote
# ==============================================================================

def test_minimal_environment_simulation_import_and_error_handling():
    """[059-US1] Môi trường không có markdown-it-py vẫn nạp được chuviettay.importer,
    TxtImporter, get_importer_for_path(txt); còn MarkdownImporter ném OptionalDependencyError.
    """
    import sys
    import unittest.mock as mock

    # Lưu và dọn tạm thời chuviettay.importer khỏi sys.modules
    saved_modules = {k: v for k, v in sys.modules.items() if k.startswith("chuviettay.importer")}
    for k in list(saved_modules.keys()):
        del sys.modules[k]

    try:
        # Chặn toàn bộ nạp markdown_it và mdit_py_plugins
        blocked = {
            "markdown_it": None,
            "markdown_it.rules_block": None,
            "markdown_it.rules_block.table": None,
            "mdit_py_plugins": None,
        }
        with mock.patch.dict("sys.modules", blocked):
            # 1. Nạp chuviettay.importer không được phát sinh ImportError ở cấp module
            import chuviettay.importer as imp_pkg
            from chuviettay.importer.base import get_importer_for_path
            from chuviettay.importer.dependency import OptionalDependencyError
            from chuviettay.importer.markdown_importer import MarkdownImporter
            from chuviettay.importer.txt_importer import TxtImporter

            # 2. TxtImporter và get_importer_for_path(txt) hoạt động bình thường
            txt_imp = get_importer_for_path("test.txt", format_name="txt")
            assert isinstance(txt_imp, TxtImporter)
            res_txt = txt_imp.import_text("Dòng văn bản thuần túy.")
            assert len(res_txt.document.blocks) == 1

            # 3. AppController nạp và phân tích file txt bình thường
            from chuviettay.controller.app_controller import AppController
            ctrl = AppController()
            assert ctrl is not None

            # 4. Khởi tạo MarkdownImporter hoặc gọi tính năng Markdown báo lỗi OptionalDependencyError
            with pytest.raises(OptionalDependencyError) as exc_info:
                MarkdownImporter()
            assert exc_info.value.package_name == "markdown_it"
            assert exc_info.value.extra == "docs"

            with pytest.raises(OptionalDependencyError):
                get_importer_for_path("test.md")

            # 5. Gọi hàm tách bảng khi thiếu thư viện ném OptionalDependencyError
            with pytest.raises(OptionalDependencyError):
                MarkdownImporter._escaped_split_table_row("col1 | col2")
    finally:
        # Khôi phục lại sys.modules và thuộc tính module trên package cha
        for k, v in saved_modules.items():
            sys.modules[k] = v
            if "." in k:
                parent, child = k.rsplit(".", 1)
                if parent in sys.modules:
                    setattr(sys.modules[parent], child, v)


def test_code_fence_nested_blockquote_fake_close(importer: MarkdownImporter):
    """[059-US2] Code fence mở ở '>' không bị đóng bởi dòng đóng giả '>> ```',
    công thức toán ở các dòng tiếp theo trong fence được bảo toàn ký tự.
    """
    text = (
        "> ```python\n"
        ">> ```\n"
        "> ta có:$$x=1$$\n"
        "> \\[y=2\\]\n"
        "> ```\n"
        "> Đoạn ngoài fence:$$z=3$$"
    )
    # Bước cô lập không được xé dòng công thức trong fence
    isolated = importer._isolate_display_math_blocks(text)
    assert "> ta có:$$x=1$$" in isolated
    assert "> \\[y=2\\]" in isolated

    # Pipeline import_text(): nội dung trong fence là code_block, chỉ đoạn ngoài fence sinh MathBlock
    res = importer.import_text(text)
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks) == 1
    assert math_blocks[0].latex == "z=3"


def test_code_fence_in_blockquote_auto_closes_on_dedent(importer: MarkdownImporter):
    """[059-US2] Code fence mở ở '>>' tự động kết thúc khi blockquote cấp 2 kết thúc
    (dòng kế tiếp quay về '>' hoặc không có '>').
    """
    text = (
        ">> ```python\n"
        ">> x = 1\n"
        "> ta có:$$x=2$$\n"
        "> \\[y=3\\]"
    )
    isolated = importer._isolate_display_math_blocks(text)
    # Dòng 'ta có:$$x=2$$' ở cấp '>' nằm ngoài fence cấp 2 nên phải được cô lập
    assert "$$x=2$$" in isolated
    res = importer.import_text(text)
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    # Cả x=2 và y=3 (được normalize từ \[y=3\]) đều được tách thành MathBlock
    assert [b.latex for b in math_blocks] == ["x=2", "y=3"]


def test_indented_code_block_in_blockquote(importer: MarkdownImporter):
    """[059-US2] Khối mã thụt lề bên trong blockquote (>     prefix:$$x=1$$)
    được bảo toàn 100% nội dung, không bị xé dòng bởi colon_match.
    """
    text = (
        "> Đoạn trích dẫn mở đầu\n"
        ">\n"
        ">     prefix:$$x=1$$\n"
        ">     $$y=2$$\n"
        ">     \\[z=3\\]\n"
        ">\n"
        "> Đoạn tiếp theo:$$a=4$$"
    )
    isolated = importer._isolate_display_math_blocks(text)
    assert ">     prefix:$$x=1$$" in isolated
    assert ">     $$y=2$$" in isolated

    normalized = importer._normalize_math_delimiters(text)
    assert "\\[z=3\\]" in normalized

    res = importer.import_text(text)
    # Khối mã thụt lề không sinh MathBlock nào, chỉ đoạn tiếp theo sinh MathBlock("a=4")
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks) == 1
    assert math_blocks[0].latex == "a=4"


def test_code_fence_info_string_with_backtick(importer: MarkdownImporter):
    """[059-US3] Dòng backtick có info string chứa backtick không mở fence nhiều dòng (CommonMark 4.5);
    công thức ở dòng tiếp theo vẫn được tách thành MathBlock.
    Ngược lại, fence tilde (~~~) cho phép backtick trong info string.
    """
    # 1. Backtick fence với backtick trong info string -> Không mở fence
    text_bt = (
        "```python`invalid\n"
        "ta có:$$x=1$$\n"
        "\\[y=2\\]\n"
        "```"
    )
    # Cả hai bước tiền xử lý đều thống nhất nhận diện công thức
    isolated_bt = importer._isolate_display_math_blocks(text_bt)
    assert "$$x=1$$" in isolated_bt

    res_bt = importer.import_text(text_bt)
    math_blocks_bt = [b for b in res_bt.document.blocks if isinstance(b, MathBlock)]
    assert any(b.latex == "x=1" for b in math_blocks_bt)

    # 2. Tilde fence với backtick trong info string -> Vẫn mở fence hợp lệ
    text_tilde = (
        "~~~python`valid\n"
        "ta có:$$x=1$$\n"
        "\\[y=2\\]\n"
        "~~~"
    )
    isolated_tilde = importer._isolate_display_math_blocks(text_tilde)
    assert "ta có:$$x=1$$" in isolated_tilde

    res_tilde = importer.import_text(text_tilde)
    math_blocks_tilde = [b for b in res_tilde.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks_tilde) == 0


def test_display_math_in_blockquote_exits_on_dedent(importer: MarkdownImporter):
    """[060-US1] Khối toán hiển thị nhiều dòng (> $$) chưa đóng tự động thoát
    khi ngữ cảnh trích dẫn kết thúc (dòng sau ra cấp gốc hoặc lùi từ >> về >),
    cho phép công thức tiếp theo (Ngoài trích dẫn:$$y=2$$) được tách thành MathBlock.
    """
    # Ca 1: Từ trích dẫn cấp 1 (>) ra cấp gốc
    text1 = (
        "> $$\n"
        "> x = 1\n"
        "Ngoài trích dẫn:$$y=2$$\n"
        "Đoạn văn tiếp theo"
    )
    isolated1 = importer._isolate_display_math_blocks(text1)
    # Dòng 'Ngoài trích dẫn:$$y=2$$' phải được tách công thức độc lập
    assert "$$y=2$$" in isolated1
    assert "Ngoài trích dẫn:" in isolated1
    assert "Đoạn văn tiếp theo" in isolated1

    res1 = importer.import_text(text1)
    math_blocks1 = [b for b in res1.document.blocks if isinstance(b, MathBlock)]
    assert any(b.latex == "y=2" for b in math_blocks1)

    # Ca 2: Từ trích dẫn cấp 2 (>>) lùi về trích dẫn cấp 1 (>)
    text2 = (
        ">> $$\n"
        ">> x = 1\n"
        "> Trong trích dẫn cấp 1:$$y=2$$\n"
        "> Đoạn văn tiếp theo"
    )
    isolated2 = importer._isolate_display_math_blocks(text2)
    assert "$$y=2$$" in isolated2
    assert "> Trong trích dẫn cấp 1:" in isolated2

    res2 = importer.import_text(text2)
    math_blocks2 = [b for b in res2.document.blocks if isinstance(b, MathBlock)]
    assert any(b.latex == "y=2" for b in math_blocks2)


def test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close(importer: MarkdownImporter):
    """[060-US1] Dòng hoàn toàn trống (không có '>') kết thúc khối toán trích dẫn đang mở.
    Dấu đóng $$ chỉ có hiệu lực khi ở cùng độ sâu trích dẫn math_bq_depth.
    """
    # Dòng trống ở cấp gốc ngắt trích dẫn và khối toán dở dang
    text_blank = (
        "> $$\n"
        "> x = 1\n"
        "\n"
        "Đoạn văn mới:$$z=9$$"
    )
    isolated_blank = importer._isolate_display_math_blocks(text_blank)
    assert "$$z=9$$" in isolated_blank
    res_blank = importer.import_text(text_blank)
    math_blocks_blank = [b for b in res_blank.document.blocks if isinstance(b, MathBlock)]
    assert any(b.latex == "z=9" for b in math_blocks_blank)

    # Dấu đóng $$ ở cấp sâu hơn (>>) không đóng nhầm khối toán ở cấp >
    text_nested_close = (
        "> $$\n"
        "> x = 1\n"
        ">> $$\n"
        "> x = 2\n"
        "> $$"
    )
    isolated_nested = importer._isolate_display_math_blocks(text_nested_close)
    # [062-US3: T-ISO] So sánh chính xác 100% chuỗi đầu ra sau cô lập (chứa ký tự PUA \ue000)
    assert isolated_nested == "> $$\n> x = 1\n>> \ue000\n> x = 2\n> $$"

    # [062-US3: T-NEST] Xác nhận qua import_text(): chỉ sinh đúng 1 MathBlock với nội dung chính xác tuyệt đối
    res_nested = importer.import_text(text_nested_close)
    math_blocks_nested = [b for b in res_nested.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks_nested) == 1
    assert math_blocks_nested[0].latex == "> x = 1\n>> $$\n> x = 2\n>"

    # [062-US3: T-PUNCT] Dấu đóng $$ ở cấp sâu hơn (>>) kèm dấu câu và khoảng trắng được khôi phục chính xác từng ký tự
    text_nested_punct = (
        "> $$\n"
        "> a = 1\n"
        ">> $$,   \n"
        "> a = 2\n"
        "> $$"
    )
    res_punct = importer.import_text(text_nested_punct)
    math_blocks_punct = [b for b in res_punct.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks_punct) == 1
    assert math_blocks_punct[0].latex == "> a = 1\n>> $$,   \n> a = 2\n>"


def test_pipeline_code_preservation_and_outside_math_invariants(importer: MarkdownImporter):
    """[060-US2] Kiểm chứng tính bất biến bảo toàn từng ký tự của khối mã
    (fenced code với backticks/tildes, cấp gốc & trong blockquote; indented code)
    và trích xuất đầy đủ, chính xác các công thức toán bên ngoài mã qua toàn bộ pipeline.
    """
    raw_fenced_code_root = (
        "```python\n"
        "def compute(a, b):\n"
        "    # Inside fence: $$not_math$$ và \\[also_not_math\\]\n"
        "    return a + b\n"
        "```"
    )
    raw_fenced_tilde_bq = (
        "> ~~~bash\n"
        "> echo '$$hello_world$$'\n"
        "> # \\[not_a_formula\\]\n"
        "> ~~~"
    )
    raw_indented_code_root = (
        "    # Indented code block:\n"
        "    val = x * 2  # $$x_times_2$$\n"
        "    res = \\[z\\]"
    )
    raw_indented_code_bq = (
        ">     # Indented code in blockquote:\n"
        ">     y = val + 1  # $$y_plus_1$$\n"
        ">     out = \\[w\\]"
    )

    text = (
        "# Tiêu đề\n\n"
        f"{raw_fenced_code_root}\n\n"
        "Công thức cấp gốc:\n\n"
        "$$alpha=1$$\n\n"
        f"{raw_fenced_tilde_bq}\n\n"
        "> Công thức trong trích dẫn:$$beta=2$$\n\n"
        f"{raw_indented_code_root}\n\n"
        "Công thức thứ ba: \\[gamma=3\\]\n\n"
        f"{raw_indented_code_bq}\n\n"
        "Đoạn kết thúc: $$omega=4$$"
    )

    # 1. Chạy toàn bộ pipeline tiền xử lý
    pipeline_out = importer._sanitize_html(
        importer._isolate_display_math_blocks(importer._normalize_math_delimiters(text))
    )

    # Khẳng định bảo toàn từng ký tự tuyệt đối trong toàn bộ các khối mã
    assert raw_fenced_code_root in pipeline_out
    assert raw_fenced_tilde_bq in pipeline_out
    assert raw_indented_code_root in pipeline_out
    assert raw_indented_code_bq in pipeline_out

    # 2. Chạy import_text() và kiểm chứng danh sách MathBlock
    res = importer.import_text(text)
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    # Không có công thức giả nào bên trong các khối mã bị biến thành MathBlock
    extracted_latex = [b.latex for b in math_blocks]
    assert extracted_latex == ["alpha=1", "beta=2", "gamma=3", "omega=4"]


def test_adversarial_complexity_multi_length_backticks_and_long_lines(importer: MarkdownImporter):
    """[059-US4 / 060-US2] Đo độ phức tạp O(n) vô điều kiện trên dữ liệu bất lợi hỗn hợp:
    nhiều độ dài backtick chưa đóng (1-6 ký tự), dòng dài, blockquote lồng nhau.
    Xác nhận T(4N)/T(N) <= 6.0 và nội dung đầu ra thỏa mãn các bất biến cụ thể.
    """
    import gc
    import statistics
    import time

    def make_adversarial_text(n_chunks: int) -> str:
        chunks = []
        for i in range(n_chunks):
            # Xen kẽ nhiều độ dài backticks khác nhau từ 1 đến 6
            bt_len = (i % 6) + 1
            bts = "`" * bt_len
            mod = i % 4
            if mod == 0:
                chunks.append(f"> > {bts}unclosed_depth2_{i} với \\[math=1\\] và chuỗi rất dài {'x'*80}")
            elif mod == 1:
                chunks.append(f"> {bts}unclosed_depth1_{i} và $$display_formula$$")
            elif mod == 2:
                chunks.append(f">{bts}no_space_bq_{i} cùng `code_span` và \\\\[escaped\\\\]")
            else:
                chunks.append(f"Dòng cấp gốc {bts}unclosed_{i} kèm $$x=1$$ và 'chuỗi dài {'y'*60}'")
        return "\n".join(chunks)

    text_n = make_adversarial_text(1000)
    text_2n = make_adversarial_text(2000)
    text_4n = make_adversarial_text(4000)

    def run_pipeline(txt: str) -> str:
        return importer._sanitize_html(importer._isolate_display_math_blocks(importer._normalize_math_delimiters(txt)))

    was_gc_enabled = gc.isenabled()
    gc.collect()
    try:
        gc.disable()
        # Warmup
        out_warmup = run_pipeline(text_n)
        assert len(out_warmup) > 0

        # Đo 2N một lần để kiểm chứng các bất biến bảo toàn
        gc.collect()
        t0 = time.perf_counter()
        for _ in range(3):
            out_2n = run_pipeline(text_2n)
        t_2n = (time.perf_counter() - t0) / 3

        # Đo thống kê trung vị trên 5 lượt độc lập cho (N, 4N) để loại trừ nhiễu hệ điều hành
        ratios: list[float] = []
        t_n_rounds: list[float] = []
        t_4n_rounds: list[float] = []

        out_n = ""
        out_4n = ""
        for _ in range(5):
            gc.collect()
            t0 = time.perf_counter()
            for _ in range(3):
                out_n = run_pipeline(text_n)
            t_n_r = (time.perf_counter() - t0) / 3

            gc.collect()
            t0 = time.perf_counter()
            for _ in range(3):
                out_4n = run_pipeline(text_4n)
            t_4n_r = (time.perf_counter() - t0) / 3

            ratios.append(t_4n_r / max(t_n_r, 0.001))
            t_n_rounds.append(t_n_r)
            t_4n_rounds.append(t_4n_r)
    finally:
        if was_gc_enabled:
            gc.enable()
        else:
            gc.disable()

    assert len(out_n) > 0
    assert len(out_2n) > 0
    assert len(out_4n) > 0
    assert t_2n > 0

    # Khẳng định bất biến công thức toán học được bảo toàn / chuẩn hóa đúng số lượng
    assert out_n.count("$$display_formula$$") == 250
    assert out_2n.count("$$display_formula$$") == 500
    assert out_4n.count("$$display_formula$$") == 1000

    assert out_n.count("$$x=1$$") == 250
    assert out_2n.count("$$x=1$$") == 500
    assert out_4n.count("$$x=1$$") == 1000

    # Khẳng định bất biến bảo toàn nội dung cụ thể trên out_n, out_2n, out_4n
    # Mỗi cấu trúc trong 4 mẫu xuất hiện đúng n_chunks // 4 lần
    assert out_n.count("x" * 80) == 250
    assert out_2n.count("x" * 80) == 500
    assert out_4n.count("x" * 80) == 1000

    assert out_n.count("y" * 60) == 250
    assert out_2n.count("y" * 60) == 500
    assert out_4n.count("y" * 60) == 1000

    assert out_n.count("unclosed_depth2_") == 250
    assert out_2n.count("unclosed_depth2_") == 500
    assert out_4n.count("unclosed_depth2_") == 1000

    assert out_n.count("unclosed_depth1_") == 250
    assert out_2n.count("unclosed_depth1_") == 500
    assert out_4n.count("unclosed_depth1_") == 1000

    assert out_n.count("no_space_bq_") == 250
    assert out_2n.count("no_space_bq_") == 500
    assert out_4n.count("no_space_bq_") == 1000

    assert out_n.count("code_span") == 250
    assert out_2n.count("code_span") == 500
    assert out_4n.count("code_span") == 1000

    # Đánh giá hiệu năng bằng trung vị 5 lượt đo (loại trừ thiên vị min retry)
    med_ratio = statistics.median(ratios)
    med_t_n = statistics.median(t_n_rounds)
    med_t_4n = statistics.median(t_4n_rounds)
    rounds_diag = ", ".join(
        f"R{i+1}: {r:.2f}x (T_N={tn:.3f}s, T_4N={t4n:.3f}s)"
        for i, (r, tn, t4n) in enumerate(zip(ratios, t_n_rounds, t_4n_rounds))
    )

    assert med_ratio <= 6.0, (
        f"Trung vị tỷ lệ tăng thời gian ({med_ratio:.2f}x) vượt ngưỡng tuyến tính 6.0x "
        f"(med_t_n={med_t_n:.3f}s, med_t_4n={med_t_4n:.3f}s) across 5 rounds: [{rounds_diag}]"
    )
    assert med_t_4n < 2.0, (
        f"Trung vị thời gian xử lý 4,000 dòng bất lợi vượt ngưỡng 2.0s ({med_t_4n:.3f}s) "
        f"across 5 rounds: [{rounds_diag}]"
    )


# ==============================================================================
# Feature 062: Khôi phục Dấu Đóng Giả bằng Dấu Giữ Chỗ Riêng & Bảo Toàn LaTeX
# ==============================================================================

def test_escaped_dollar_formula_preservation(importer: MarkdownImporter):
    """[062-US1] Khẳng định các công thức LaTeX chứa ký hiệu đô-la escape (\\$, \\$\\$)
    được bảo toàn 100% nguyên vẹn từng ký tự, không bị replace(r"\\$\\$", "$$") làm sai lệch.
    """
    # T-ESC1: Một dòng $$\\text{\\$\\$}$$
    res_esc1 = importer.import_text("$$\\text{\\$\\$}$$")
    math_esc1 = [b for b in res_esc1.document.blocks if isinstance(b, MathBlock)]
    assert len(math_esc1) == 1
    assert math_esc1[0].latex == r"\text{\$\$}"

    # T-ESC2: Nhiều dòng
    res_esc2 = importer.import_text("$$\n\\text{\\$\\$}\n$$")
    math_esc2 = [b for b in res_esc2.document.blocks if isinstance(b, MathBlock)]
    assert len(math_esc2) == 1
    assert math_esc2[0].latex == r"\text{\$\$}"

    # T-ESC3: Trong trích dẫn
    res_esc3 = importer.import_text("> $$\n> \\text{\\$\\$}\n> $$")
    math_esc3 = [b for b in res_esc3.document.blocks if isinstance(b, MathBlock)]
    assert len(math_esc3) == 1
    assert math_esc3[0].latex == "> \\text{\\$\\$}\n>"

    # T-MULTI: Một dòng và nhiều dòng chứa cả \\$ và \\$\\$\\$\\$
    res_multi_single = importer.import_text(r"$$\$ + \text{\$\$\$\$}$$")
    math_multi_single = [b for b in res_multi_single.document.blocks if isinstance(b, MathBlock)]
    assert len(math_multi_single) == 1
    assert math_multi_single[0].latex == r"\$ + \text{\$\$\$\$}"

    res_multi_multi = importer.import_text("$$\n\\$ + \\$\\$\\$\\$\n$$")
    math_multi_multi = [b for b in res_multi_multi.document.blocks if isinstance(b, MathBlock)]
    assert len(math_multi_multi) == 1
    assert math_multi_multi[0].latex == r"\$ + \$\$\$\$"

    # T-COMBO: Cùng một khối toán vừa có \\text{\\$\\$} vừa có dấu đóng giả lồng nhau >> $$
    res_combo = importer.import_text("> $$\n> \\text{\\$\\$}\n>> $$\n> x = 2\n> $$")
    math_combo = [b for b in res_combo.document.blocks if isinstance(b, MathBlock)]
    assert len(math_combo) == 1
    assert math_combo[0].latex == "> \\text{\\$\\$}\n>> $$\n> x = 2\n>"


def test_fake_close_pua_placeholder_safety_and_fallback(importer: MarkdownImporter):
    """[062-US2] Kiểm chứng cơ chế dấu giữ chỗ PUA:
    - T-COLL: Đầu vào chứa sẵn ký tự \\ue000 tự động dịch sang ký tự PUA tiếp theo,
      ký tự \\ue000 của người dùng được bảo toàn nguyên vẹn.
    - T-LEAK: Khối toán không đóng chứa dòng đóng giả lồng nhau không làm rò rỉ ký tự PUA
      vào bất kỳ node nào của Document hay ImportResult.unsupported; dòng rơi vào Paragraph có chữ '$$'.
    - Fallback: fake_close_placeholder=None giữ nguyên dòng '$$' mà không ném lỗi.
    """
    # T-COLL: Đầu vào chứa sẵn \ue000
    text_coll = "\ue000 văn bản gốc\n\n> $$\n> x = 1\n>> $$\n> x = 2\n> $$"
    res_coll = importer.import_text(text_coll)
    math_coll = [b for b in res_coll.document.blocks if isinstance(b, MathBlock)]
    assert len(math_coll) == 1
    assert math_coll[0].latex == "> x = 1\n>> $$\n> x = 2\n>"
    p_coll = [b for b in res_coll.document.blocks if isinstance(b, Paragraph)]
    assert any("\ue000 văn bản gốc" in [inl.text for inl in p.inlines if isinstance(inl, Text)] for p in p_coll)

    # T-LEAK: Khối toán không đóng
    text_unclosed = "> $$\n> x = 1\n>> $$\n> x = 2"
    res_unclosed = importer.import_text(text_unclosed)
    # Khối toán không đóng -> không tạo MathBlock
    assert not any(isinstance(b, MathBlock) for b in res_unclosed.document.blocks)
    # Không ký tự PUA nào rò rỉ trong document
    for b in res_unclosed.document.blocks:
        if isinstance(b, Paragraph):
            for inl in b.inlines:
                if isinstance(inl, Text):
                    assert not any(0xE000 <= ord(c) <= 0xF8FF for c in inl.text)
    # Dòng đóng giả trong đoạn văn hiển thị đúng '$$'
    text_fragments = []
    for b in res_unclosed.document.blocks:
        if isinstance(b, Paragraph):
            text_fragments.extend([inl.text for inl in b.inlines if isinstance(inl, Text)])
    assert any("$$" in frag for frag in text_fragments)

    # T-LEAK 2: Dòng mở fence lồng nhau có $$ trong khối toán không đóng không rò rỉ PUA vào unsupported
    text_fence_unclosed = "> $$\n>> ```python $$\n>> pass\n>> ```"
    res_fence_unclosed = importer.import_text(text_fence_unclosed)
    for unsup in res_fence_unclosed.unsupported:
        assert not any(0xE000 <= ord(c) <= 0xF8FF for c in unsup)

    # Fallback: fake_close_placeholder=None giữ nguyên chuỗi
    raw_nested = "> $$\n> x = 1\n>> $$\n> x = 2\n> $$"
    out_fallback = importer._isolate_display_math_blocks(raw_nested, fake_close_placeholder=None)
    assert ">> $$" in out_fallback


def test_choose_fake_close_placeholder_optimization():
    """[063-US1 & US2] Kiểm chứng thuật toán chọn ký tự giữ chỗ PUA tối ưu hóa:
    - C-FAST: Văn bản thông thường không chứa U+E000 -> Fast-path trả về U+E000.
    - C-EMPTY: Văn bản rỗng -> Fast-path trả về U+E000.
    - C-COLL-MULTI: Văn bản chứa chuỗi liên tiếp U+E000..U+E009 -> Trả về U+E00A.
    - C-COLL-SPARSE: Văn bản chứa U+E000, U+E002, U+E003 (khuyết U+E001) -> Trả về U+E001.
    - C-EXHAUST-NONE: Văn bản chứa toàn bộ 6.400 ký tự PUA -> Trả về None.
    """
    # C-FAST
    text_normal = "Văn bản tài liệu thông thường\n$$x = 1$$"
    assert MarkdownImporter._choose_fake_close_placeholder(text_normal) == "\ue000"

    # C-EMPTY
    assert MarkdownImporter._choose_fake_close_placeholder("") == "\ue000"

    # C-COLL-MULTI (chuỗi 10 ký tự PUA liên tiếp)
    chain_pua = "".join(chr(0xE000 + i) for i in range(10))
    text_multi = f"{chain_pua} nội dung khác"
    assert MarkdownImporter._choose_fake_close_placeholder(text_multi) == chr(0xE000 + 10)  # \ue00a

    # C-COLL-SPARSE (va chạm ngắt quãng, khuyết \ue001)
    text_sparse = "\ue000\ue002\ue003 văn bản ngắt quãng"
    assert MarkdownImporter._choose_fake_close_placeholder(text_sparse) == "\ue001"

    # C-EXHAUST-NONE (cạn kiệt toàn bộ 6.400 điểm mã BMP PUA)
    all_pua = "".join(chr(cp) for cp in range(0xE000, 0xF8FF + 1))
    assert len(all_pua) == 6400
    assert MarkdownImporter._choose_fake_close_placeholder(all_pua) is None


def test_fake_close_pua_exhaustion_e2e_fallback(importer: MarkdownImporter):
    """[063-US2] Kiểm chứng luồng xử lý toàn diện qua import_text() khi cạn kiệt toàn bộ 6.400 ký tự PUA:
    - Khi PUA cạn kiệt, placeholder=None.
    - Quy trình nhập tài liệu không được ném ngoại lệ (graceful fallback).
    - Toàn bộ 6.400 ký tự PUA của người dùng được bảo toàn 100% trong tài liệu đầu ra.
    - Không rò rỉ bất kỳ dấu giữ chỗ nội bộ nào vào document blocks hay unsupported.
    """
    all_pua = "".join(chr(cp) for cp in range(0xE000, 0xF8FF + 1))
    text_exhausted = (
        f"{all_pua}\n\n"
        "> $$\n"
        "> x = 1\n"
        ">> $$\n"
        "> x = 2\n"
        "> $$"
    )

    # 1. import_text phải hoàn thành thành công không ném ngoại lệ
    res = importer.import_text(text_exhausted)
    assert res is not None
    assert res.document is not None

    # 2. Toàn bộ 6.400 ký tự PUA của người dùng phải được bảo toàn trong các inlines văn bản
    collected_pua_chars = set()
    for block in res.document.blocks:
        if isinstance(block, Paragraph):
            for inl in block.inlines:
                if isinstance(inl, Text):
                    for ch in inl.text:
                        if 0xE000 <= ord(ch) <= 0xF8FF:
                            collected_pua_chars.add(ch)

    assert len(collected_pua_chars) == 6400

    # 3. Không có rò rỉ ký tự lạ hay chuỗi hỏng trong unsupported
    assert len(res.unsupported) == 0


def test_pua_memory_bounded_multilingual(importer: MarkdownImporter):
    """[064-US1] Kiểm chứng khống chế bộ nhớ và độ chính xác khi tài liệu chứa nhiều ký tự đa ngữ:
    - Ca 1: Tài liệu chứa 10.000 ký tự Hán/Nôm khác nhau và ký tự \\ue000 -> Trả về \\ue001.
    - Ca 2: Tài liệu chứa 10.000 ký tự đa ngữ và 10 ký tự PUA (\\ue000..\\ue009) -> Trả về \\ue00a.
    - Ca 3: Tài liệu chứa toàn bộ 6.400 ký tự PUA xen kẽ văn bản đa ngữ lớn -> Thoát sớm và trả về None.
    - Ca 4: Toàn bộ quy trình import_text() với tài liệu đa ngữ chứa \\ue000 và trích dẫn lồng nhau
      bảo toàn 100% nội dung chữ Nôm và ký tự PUA gốc của người dùng.
    """
    # Ca 1: 10.000 ký tự chữ Hán/Nôm phân biệt (U+4E00..U+751F) + \ue000
    han_nom_chars = "".join(chr(0x4E00 + i) for i in range(10000))
    text_c1 = f"{han_nom_chars}\ue000 văn bản chữ Nôm"
    placeholder_c1 = MarkdownImporter._choose_fake_close_placeholder(text_c1)
    assert placeholder_c1 == "\ue001"

    # Ca 2: 10.000 ký tự đa ngữ và chuỗi 10 ký tự PUA liên tiếp (\ue000..\ue009)
    multi_pua = "".join(chr(0xE000 + i) for i in range(10))
    text_c2 = f"{han_nom_chars}{multi_pua} tài liệu đa ngữ"
    placeholder_c2 = MarkdownImporter._choose_fake_close_placeholder(text_c2)
    assert placeholder_c2 == chr(0xE000 + 10)  # \ue00a

    # Ca 3: Toàn bộ 6.400 ký tự PUA kèm văn bản đa ngữ lớn phía sau -> Trả về None
    all_pua = "".join(chr(cp) for cp in range(0xE000, 0xF8FF + 1))
    text_c3 = f"{all_pua}{han_nom_chars * 2}"
    placeholder_c3 = MarkdownImporter._choose_fake_close_placeholder(text_c3)
    assert placeholder_c3 is None

    # Ca 4: Tích hợp e2e import_text() với văn bản chữ Nôm chứa \ue000 và dấu đóng giả lồng nhau
    sample_nom = "".join(chr(0x4E00 + i) for i in range(500))
    text_e2e = (
        f"{sample_nom}\n\n"
        "\ue000 Đoạn văn chứa PUA người dùng\n\n"
        "> $$\n"
        "> \\alpha = 1\n"
        ">> $$\n"
        "> \\beta = 2\n"
        "> $$"
    )
    res = importer.import_text(text_e2e)
    assert res is not None
    assert len(res.unsupported) == 0

    # Khẳng định trích xuất đúng MathBlock
    math_blocks = [b for b in res.document.blocks if isinstance(b, MathBlock)]
    assert len(math_blocks) == 1
    assert math_blocks[0].latex == "> \\alpha = 1\n>> $$\n> \\beta = 2\n>"

    # Khẳng định bảo toàn trọn vẹn 500 ký tự chữ Nôm và \ue000 trong các Paragraph
    paragraphs = [b for b in res.document.blocks if isinstance(b, Paragraph)]
    all_para_text = "".join(
        inl.text for p in paragraphs for inl in p.inlines if isinstance(inl, Text)
    )
    assert sample_nom in all_para_text
    assert "\ue000 Đoạn văn chứa PUA người dùng" in all_para_text


def test_pua_codepoint_collection_direct_and_bounded():
    """[065-US1] Kiểm chứng trực tiếp số lượng phần tử và miền giá trị của tập hợp điểm mã PUA:
    - Ca 1: Văn bản chứa 10.000 ký tự chữ Hán/Nôm và 1 ký tự \\ue000 -> used_cps chỉ có đúng 1 phần tử {0xE000}.
    - Ca 2: Văn bản chứa 10.000 ký tự đa ngữ và 10 ký tự PUA (\\ue000..\\ue009) -> used_cps có đúng 10 phần tử.
    - Ca 3: Văn bản chứa toàn bộ 6.400 ký tự PUA xen kẽ văn bản đa ngữ -> used_cps đạt đúng 6.400 phần tử.
    - Ca 4: Văn bản không chứa ký tự PUA nào -> used_cps là tập hợp rỗng set().
    """
    han_nom_chars = "".join(chr(0x4E00 + i) for i in range(10000))

    # Ca 1: 10.000 ký tự chữ Nôm + \ue000
    text_c1 = f"{han_nom_chars}\ue000 văn bản chữ Nôm"
    used_c1 = MarkdownImporter._collect_used_pua_codepoints(text_c1)
    assert used_c1 == {0xE000}
    assert len(used_c1) == 1

    # Ca 2: 10.000 ký tự đa ngữ và 10 ký tự PUA liên tiếp
    multi_pua = "".join(chr(0xE000 + i) for i in range(10))
    text_c2 = f"{han_nom_chars}{multi_pua}"
    used_c2 = MarkdownImporter._collect_used_pua_codepoints(text_c2)
    assert len(used_c2) == 10
    assert used_c2 == set(range(0xE000, 0xE00A))

    # Ca 3: 6.400 ký tự PUA kèm văn bản lớn phía sau
    all_pua = "".join(chr(cp) for cp in range(0xE000, 0xF8FF + 1))
    text_c3 = f"{all_pua}{han_nom_chars * 2}"
    used_c3 = MarkdownImporter._collect_used_pua_codepoints(text_c3)
    assert len(used_c3) == 6400
    assert all(0xE000 <= cp <= 0xF8FF for cp in used_c3)

    # Ca 4: Văn bản thuần túy không có ký tự PUA
    text_c4 = f"{han_nom_chars} văn bản hoàn toàn không chứa PUA"
    used_c4 = MarkdownImporter._collect_used_pua_codepoints(text_c4)
    assert used_c4 == set()
    assert len(used_c4) == 0


def test_pua_memory_allocation_bounded_tracemalloc():
    """[065-US1] Đo lường định lượng bộ nhớ đỉnh phân bổ (tracemalloc) khi trích xuất PUA:
    - Xác nhận khi xử lý văn bản lớn chứa 10.000 ký tự phân biệt và ký tự PUA va chạm,
      mức tăng bộ nhớ đỉnh phân bổ luôn duy trì <= 50KB, hoàn toàn không bùng nổ theo quy mô bảng chữ cái.
    - Đảm bảo dọn dẹp an toàn qua khối try...finally để tránh rò rỉ trạng thái tracing.
    """
    import gc
    import tracemalloc

    han_nom_chars = "".join(chr(0x4E00 + i) for i in range(10000))
    # Tạo văn bản ~100.000 ký tự với 10.001 ký tự phân biệt
    text_large = f"{han_nom_chars}\ue000" * 10

    gc.collect()
    tracemalloc.start()
    try:
        used_cps = MarkdownImporter._collect_used_pua_codepoints(text_large)
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert used_cps == {0xE000}
    peak_kb = peak_memory / 1024
    assert peak_kb <= 50.0, f"Mức tăng bộ nhớ đỉnh ({peak_kb:.2f} KB) vượt ngưỡng an toàn 50 KB"




