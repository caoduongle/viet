"""Bộ nạp tài liệu Markdown (.md, .markdown) chuyển đổi sang Document IR."""
from __future__ import annotations

import os
import re
from typing import Any


from chuviettay.document.ir import (
    Block,
    Document,
    Heading,
    Inline,
    LineBreak,
    ListBlock,
    MathBlock,
    MathInline,
    Paragraph,
    Table,
    TableBorder,
    TableCell,
    TableRow,
    Text,
)
from chuviettay.importer.base import BaseImporter, ImportResult
from chuviettay.importer.dependency import require_dependency

# Tiền tố blockquote theo chuẩn CommonMark: ví dụ "> ", ">> ", "> > " (tối đa 3 khoảng trắng trước mỗi dấu >)
_BQ_PREFIX_RE = re.compile(r"([ ]{0,3}>[ ]?)+")

# Đoạn mã (fence / inline code): không đụng tới khi đổi dấu phân cách toán hay lọc HTML (hỗ trợ >=3 backticks/tildes và unclosed fence)
_CODE_SEGMENT = re.compile(r"(`{3,}.*?(?:`{3,}|\Z)|~{3,}.*?(?:~{3,}|\Z)|`[^`\n]*`)", re.DOTALL)
# Dấu phân cách toán kiểu LaTeX: \( ... \) và \[ ... \] (CommonMark sẽ nuốt dấu \ nếu không đổi trước)
_MAX_INLINE_MATH = 4000
_MAX_DISPLAY_MATH = 20000
# Vùng công thức được bảo vệ khi lọc HTML ($$..$$, $..$, \(..\), \[..\])
_MATH_SEGMENT = re.compile(r"(\$\$.*?\$\$|\$[^\s$][^$\n]*?\$)", re.DOTALL)

_HTML_TAG_NAMES = (
    "a|abbr|address|article|aside|audio|b|big|blockquote|body|br|button|canvas|caption|center|cite|code|col|"
    "colgroup|dd|del|details|dfn|div|dl|dt|em|embed|fieldset|figcaption|figure|font|footer|form|h[1-6]|head|"
    "header|hr|html|i|iframe|img|input|ins|kbd|label|legend|li|link|main|mark|math|menu|meta|nav|noscript|"
    "object|ol|option|p|param|picture|pre|q|s|samp|script|section|select|small|source|span|strike|strong|"
    "style|sub|summary|sup|svg|table|tbody|td|template|textarea|tfoot|th|thead|title|tr|track|tt|u|ul|var|"
    "video|wbr"
)
# Thẻ HTML thật: tên thẻ đã biết, thuộc tính (nếu có) dạng name=value. "a<b và c>d" KHÔNG khớp nên được giữ nguyên.
_HTML_TAG = re.compile(
    r"</?(?:" + _HTML_TAG_NAMES + r")"
    r"(?:\s+[A-Za-z_:][-A-Za-z0-9_:.]*\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))*\s*/?>",
    re.IGNORECASE,
)

# Miền ký tự Private Use Area của BMP (U+E000..U+F8FF, 6.400 điểm mã) dùng làm dấu giữ chỗ nội bộ
_FAKE_CLOSE_PUA_START = 0xE000
_FAKE_CLOSE_PUA_END = 0xF8FF
_FAKE_CLOSE_PUA_COUNT = _FAKE_CLOSE_PUA_END - _FAKE_CLOSE_PUA_START + 1
_PUA_RE = re.compile(r"[\uE000-\uF8FF]")


class MarkdownImporter(BaseImporter):
    """Nạp tài liệu Markdown, hỗ trợ tiêu đề, danh sách, bảng GFM và công thức toán học."""

    def __init__(self):
        # Kiểm tra và nạp thư viện markdown-it-py
        require_dependency("markdown_it", feature_desc="tệp Markdown (.md)")
        require_dependency("mdit_py_plugins", feature_desc="tính năng toán học trong Markdown")

    @classmethod
    def _choose_fake_close_placeholder(cls, text: str) -> str | None:
        """Chọn ký tự giữ chỗ cho dấu đóng giả từ vùng Private Use Area của BMP (U+E000..U+F8FF).

        Độ phức tạp và cơ chế:
        1. Fast-path: Kiểm tra text rỗng hoặc first_pua not in text.
           - Phép tìm kiếm chuỗi con 'not in' thực thi ở tầng C với thời gian O(N) trong trường hợp xấu nhất,
             nhưng không cấp phát bộ nhớ phụ nào (O(1) auxiliary memory), tối ưu cho hầu hết tài liệu thông thường.
        2. Collision path: Khi U+E000 xuất hiện trong text (va chạm), quét các ký tự PUA bằng biểu thức chính quy
           _PUA_RE.finditer(text) ở tầng C mà không cấp phát danh sách hay tập hợp toàn bộ ký tự tài liệu:
           - Tập hợp used_cps chỉ chứa các điểm mã PUA đã dùng, khống chế bộ nhớ phụ tối đa <= 6.400 phần tử.
           - Thoát sớm ngay trong vòng lặp finditer nếu used_cps đã đủ 6.400 ký tự (cạn kiệt PUA).
           - Duyệt dải mã U+E001..U+F8FF để tìm điểm mã chưa dùng đầu tiên; trả về None nếu cạn kiệt.
        """
        if not text:
            return chr(_FAKE_CLOSE_PUA_START)

        first_pua = chr(_FAKE_CLOSE_PUA_START)
        if first_pua not in text:
            return first_pua

        used_cps: set[int] = set()
        for m in _PUA_RE.finditer(text):
            used_cps.add(ord(m.group(0)))
            if len(used_cps) == _FAKE_CLOSE_PUA_COUNT:
                return None

        for cp in range(_FAKE_CLOSE_PUA_START + 1, _FAKE_CLOSE_PUA_END + 1):
            if cp not in used_cps:
                return chr(cp)
        return None

    @classmethod
    def _restore_fake_close_placeholder(cls, tokens: list[Any], placeholder: str | None) -> None:
        """Khôi phục đệ quy dấu giữ chỗ nội bộ về '$$' trên toàn bộ cây token của markdown-it.
        Xử lý cả token.content và token.info (phòng ngừa rò rỉ vào unsupported hoặc Text)."""
        if not placeholder or not tokens:
            return

        for tok in tokens:
            if getattr(tok, "content", None) and placeholder in tok.content:
                tok.content = tok.content.replace(placeholder, "$$")
            if getattr(tok, "info", None) and placeholder in tok.info:
                tok.info = tok.info.replace(placeholder, "$$")
            children = getattr(tok, "children", None)
            if children:
                cls._restore_fake_close_placeholder(children, placeholder)

    @classmethod
    def _escaped_split_table_row(cls, line_str: str) -> list[str]:
        """Tách các ô của hàng bảng theo ký tự '|' không bị thoát (dùng escapedSplit của markdown-it)."""
        require_dependency("markdown_it", feature_desc="tệp Markdown (.md)")
        from markdown_it.rules_block.table import escapedSplit

        return escapedSplit(line_str.strip())

    @classmethod
    def _get_bq_depth_and_rest(cls, line: str) -> tuple[int, str]:
        """Trích xuất độ sâu trích dẫn (số dấu >) và phần nội dung sau tiền tố blockquote."""
        clean = line.rstrip("\r")
        m_bq = _BQ_PREFIX_RE.match(clean)
        bq_prefix = m_bq.group(0) if m_bq else ""
        return bq_prefix.count(">"), clean[len(bq_prefix) :]

    @classmethod
    def _parse_fence_open_line(cls, line: str) -> tuple[int, str, int] | None:
        """Kiểm tra dòng có mở code fence hay không (CommonMark 4.5).
        Trả về (bq_depth, fence_char, fence_len) nếu hợp lệ, ngược lại None."""
        clean = line.rstrip("\r")
        m_bq = _BQ_PREFIX_RE.match(clean)
        bq_prefix = m_bq.group(0) if m_bq else ""
        bq_depth = bq_prefix.count(">")
        pos = len(bq_prefix)

        indent = 0
        n = len(clean)
        while pos + indent < n and clean[pos + indent] == " " and indent < 3:
            indent += 1
        pos += indent

        if pos >= n or clean[pos] not in ("`", "~"):
            return None

        fc = clean[pos]
        flen = 0
        while pos + flen < n and clean[pos + flen] == fc:
            flen += 1

        if flen < 3:
            return None

        info_str = clean[pos + flen :]
        if fc == "`" and "`" in info_str:
            return None

        return (bq_depth, fc, flen)

    @classmethod
    def _is_fence_close_line(cls, line: str, open_bq_depth: int, fence_char: str, fence_len: int) -> bool:
        """Kiểm tra dòng có đóng code fence đang mở hay không (CommonMark 4.5).
        Chỉ đóng khi dòng có cùng độ sâu trích dẫn (line_bq_depth == open_bq_depth)
        và phần nội dung khớp 0-3 khoảng trắng + >= fence_len ký tự fence + khoảng trắng."""
        clean = line.rstrip("\r")
        m_bq = _BQ_PREFIX_RE.match(clean)
        bq_prefix = m_bq.group(0) if m_bq else ""
        bq_depth = bq_prefix.count(">")
        if bq_depth != open_bq_depth:
            return False

        rest = clean[len(bq_prefix) :]
        m_close = re.match(
            r"^[ ]{0,3}(" + re.escape(fence_char) + r"{" + str(fence_len) + r",})[ \t]*$",
            rest,
        )
        return bool(m_close)

    @staticmethod
    def _convert_delimited(seg: str, opener: str, closer: str, wrap: str, max_len: int, strip: bool) -> str:
        """Đổi ``opener..closer`` (không có dấu \\ đứng ngay trước) thành ``wrap..wrap``; quét tuyến tính,
        nên dù có hàng chục nghìn dấu mở không đóng cũng không bị chậm."""
        out: list[str] = []
        i = 0
        n = len(seg)
        close_at = -2          # vị trí closer gần nhất đã tìm thấy (-1: không còn closer nào phía sau)
        while i < n:
            j = seg.find(opener, i)
            if j == -1:
                break
            if j > 0 and seg[j - 1] == "\\":            # \\( là dấu gạch ngược thoát rồi tới dấu ngoặc thường
                out.append(seg[i : j + len(opener)])
                i = j + len(opener)
                continue
            start = j + len(opener)
            if close_at != -1 and close_at < start:
                k = seg.find(closer, start)
                while k > 0 and seg[k - 1] == "\\":      # closer bị thoát thì bỏ qua
                    k = seg.find(closer, k + len(closer))
                close_at = k
            if close_at == -1:                           # phía sau không còn closer nào: hết việc
                break
            if close_at - start > max_len or close_at < start:
                out.append(seg[i:start])
                i = start
                continue
            body = seg[start:close_at]
            if strip:
                body = body.strip()
            if not body.strip():
                out.append(seg[i:start])
                i = start
                continue
            out.append(seg[i:j] + wrap + body + wrap)
            i = close_at + len(closer)
        out.append(seg[i:])
        return "".join(out)

    @staticmethod
    def _is_escaped_backtick(text: str, idx: int) -> bool:
        """Kiểm tra ký tự backtick tại idx có bị thoát bởi số lẻ dấu gạch ngược hay không."""
        p = idx - 1
        count = 0
        while p >= 0 and text[p] == "\\":
            count += 1
            p -= 1
        return count % 2 == 1

    @classmethod
    def _find_code_spans(cls, text: str) -> list[tuple[int, int]]:
        """Tìm tất cả các vị trí (start, end) của inline code spans theo CommonMark.
        Hỗ trợ bất kỳ độ dài backticks nào (1, 2, 3+ backticks) và bỏ qua backtick bị escape.
        Áp dụng cơ chế bộ nhớ đệm backticks_max_pos đạt độ phức tạp tuyến tính O(n)."""
        spans: list[tuple[int, int]] = []
        i = 0
        n = len(text)
        backticks_scanned = False
        backticks_max_pos: dict[int, int] = {}
        while i < n:
            if text[i] == "`":
                if cls._is_escaped_backtick(text, i):
                    i += 1
                    continue
                start = i
                while i < n and text[i] == "`":
                    i += 1
                flen = i - start

                if backticks_scanned and backticks_max_pos.get(flen, 0) <= start:
                    continue

                j = i
                found = False
                while j < n:
                    try:
                        k = text.index("`", j)
                    except ValueError:
                        break
                    m_end = k + 1
                    while m_end < n and text[m_end] == "`":
                        m_end += 1
                    c_len = m_end - k
                    if c_len == flen:
                        spans.append((start, m_end))
                        i = m_end
                        found = True
                        break
                    backticks_max_pos[c_len] = k
                    j = m_end

                if not found:
                    backticks_scanned = True
            else:
                i += 1
        return spans

    @classmethod
    def _split_code_segments(cls, text: str) -> list[tuple[str, bool]]:
        """Phân tách văn bản thành danh sách (chunk, is_code) tuân thủ CommonMark.
        Hỗ trợ code fence ở cấp gốc hoặc lồng trong blockquote (>=3 backticks/tildes),
        indented code block (4 khoảng trắng sau dòng trống), và inline code span
        bất kỳ độ dài (bỏ qua backtick bị escape). Bảo toàn 100% từng ký tự ban đầu."""
        if not text:
            return []

        n = len(text)
        i = 0
        segments: list[tuple[str, bool]] = []
        text_start = 0
        prev_line_blank = True
        backticks_scanned = False
        backticks_max_pos: dict[int, int] = {}

        def flush_text(end_idx: int):
            nonlocal text_start
            if end_idx > text_start:
                segments.append((text[text_start:end_idx], False))
            text_start = end_idx

        while i < n:
            is_line_start = (i == 0 or text[i - 1] == "\n")

            if is_line_start:
                eol = text.find("\n", i)
                if eol == -1:
                    eol = n
                line_str = text[i:eol]

                # A. Code Fence (cấp gốc hoặc trong blockquote, hỗ trợ CommonMark info string)
                fence_open = cls._parse_fence_open_line(line_str)
                if fence_open is not None:
                    open_bq_depth, fc, flen = fence_open
                    flush_text(i)
                    fence_start = i
                    i = eol + 1 if eol < n else n

                    found_close = False
                    while i < n:
                        curr_eol = text.find("\n", i)
                        if curr_eol == -1:
                            curr_eol = n
                        curr_line = text[i:curr_eol]
                        clean_curr = curr_line.rstrip("\r")
                        m_curr_bq = _BQ_PREFIX_RE.match(clean_curr)
                        curr_bq_prefix = m_curr_bq.group(0) if m_curr_bq else ""
                        curr_bq_depth = curr_bq_prefix.count(">")

                        if curr_bq_depth < open_bq_depth:
                            # Khối trích dẫn chứa rào chắn đã kết thúc trước dòng này!
                            segments.append((text[fence_start:i], True))
                            text_start = i
                            found_close = True
                            prev_line_blank = False
                            break

                        if cls._is_fence_close_line(curr_line, open_bq_depth, fc, flen):
                            found_close = True
                            i = curr_eol + 1 if curr_eol < n else n
                            segments.append((text[fence_start:i], True))
                            text_start = i
                            prev_line_blank = False
                            break

                        if curr_eol == n:
                            i = n
                            break
                        i = curr_eol + 1

                    if not found_close:
                        segments.append((text[fence_start:n], True))
                        text_start = n
                        i = n
                        prev_line_blank = False
                    continue

                # B. Indented Code Block (CommonMark 4.4, cấp gốc hoặc trong blockquote)
                bq_depth, rest = cls._get_bq_depth_and_rest(line_str)
                if prev_line_blank and (rest.startswith("    ") or rest.startswith("\t")) and rest.strip() != "":
                    flush_text(i)
                    indented_start = i
                    curr_line_start = i
                    last_indented_end = eol + 1 if eol < n else n

                    while curr_line_start < n:
                        curr_eol = text.find("\n", curr_line_start)
                        if curr_eol == -1:
                            curr_eol = n
                        curr_line = text[curr_line_start:curr_eol]
                        c_depth, c_rest = cls._get_bq_depth_and_rest(curr_line)
                        if c_depth == bq_depth and (c_rest.startswith("    ") or c_rest.startswith("\t")):
                            last_indented_end = curr_eol + 1 if curr_eol < n else n
                            curr_line_start = curr_eol + 1 if curr_eol < n else n
                        elif c_depth == bq_depth and c_rest.strip() == "":
                            # Dòng trống nằm giữa các dòng thụt lề
                            peek = curr_eol + 1 if curr_eol < n else n
                            is_trailing_blank = True
                            while peek < n:
                                peek_eol = text.find("\n", peek)
                                if peek_eol == -1:
                                    peek_eol = n
                                p_depth, p_rest = cls._get_bq_depth_and_rest(text[peek:peek_eol])
                                if p_depth == bq_depth and (p_rest.startswith("    ") or p_rest.startswith("\t")):
                                    is_trailing_blank = False
                                    break
                                elif p_depth == bq_depth and p_rest.strip() == "":
                                    peek = peek_eol + 1 if peek_eol < n else n
                                else:
                                    break
                            if not is_trailing_blank:
                                curr_line_start = peek
                            else:
                                break
                        else:
                            break

                    segments.append((text[indented_start:last_indented_end], True))
                    text_start = last_indented_end
                    i = last_indented_end
                    prev_line_blank = False
                    continue

            # C. Inline Code Span (xét thoát backtick và bộ nhớ đệm O(n))
            if text[i] == "`":
                if cls._is_escaped_backtick(text, i):
                    i += 1
                    continue
                start_backticks = i
                while i < n and text[i] == "`":
                    i += 1
                span_len = i - start_backticks

                if backticks_scanned and backticks_max_pos.get(span_len, 0) <= start_backticks:
                    continue

                j = i
                found_span = False
                while j < n:
                    try:
                        k = text.index("`", j)
                    except ValueError:
                        break
                    m_end = k + 1
                    while m_end < n and text[m_end] == "`":
                        m_end += 1
                    c_len = m_end - k
                    if c_len == span_len:
                        flush_text(start_backticks)
                        segments.append((text[start_backticks:m_end], True))
                        text_start = m_end
                        i = m_end
                        found_span = True
                        prev_line_blank = False
                        break
                    backticks_max_pos[c_len] = k
                    j = m_end

                if not found_span:
                    backticks_scanned = True
                continue

            if text[i] == "\n":
                prev_nl = text.rfind("\n", 0, i)
                line_content = text[prev_nl + 1 : i] if prev_nl != -1 else text[:i]
                _, prev_rest = cls._get_bq_depth_and_rest(line_content)
                prev_line_blank = (prev_rest.strip() == "")

            i += 1

        flush_text(n)
        return segments

    @classmethod
    def _is_table_line(cls, line: str) -> bool:
        """Kiểm tra dòng có thuộc bảng GFM hay không dựa trên ký tự phân cách cột '|'
        nằm BÊN NGOÀI các code spans và công thức toán học ($$...$$, $...$)."""
        if "|" not in line:
            return False

        # Ẩn code spans trong line
        spans = cls._find_code_spans(line)
        cleaned = list(line)
        for st, en in spans:
            for idx in range(st, en):
                cleaned[idx] = " "
        s = "".join(cleaned)

        # Ẩn các công thức hoàn chỉnh trên dòng ($$...$$ và $...$)
        s = re.sub(r"\$\$.*?\$\$", " ", s)
        s = re.sub(r"\$[^\s$][^$\n]*?\$", " ", s)

        # Kiểm tra còn ký tự | không bị thoát
        return bool(re.search(r"(?<!\\)\|", s))

    @classmethod
    def _isolate_display_math_blocks(cls, seg: str, fake_close_placeholder: str | None = "") -> str:
        """Đảm bảo các khối công thức toán display ($$..$$) bắt đầu ở dòng mới hoặc liền sau
        dấu hai chấm có dòng trống phân cách chuẩn CommonMark, ngoại trừ các khối mã (code fence),
        khối mã thụt lề (indented code block), đoạn mã nội dòng (code span) và các ô bảng GFM.

        Sử dụng máy trạng thái một lượt (single-pass line scanner) đạt độ phức tạp O(n) tuyến tính,
        chuẩn hóa ngắt dòng CRLF và bảo toàn 100% nội dung bên trong code fence và khối mã thụt lề."""
        if not seg:
            return ""

        # 1. Chuẩn hóa CRLF / CR thành \n để tránh lỗi bám ký tự \r
        seg = seg.replace("\r\n", "\n").replace("\r", "\n")

        if "$$" not in seg:
            return seg

        if fake_close_placeholder == "":
            fake_close_placeholder = cls._choose_fake_close_placeholder(seg)

        lines = seg.split("\n")
        out_lines: list[str] = []
        n = len(lines)

        # Tiền quét các khối bảng GFM có hàng phân cách cột (delimiter row)
        # Chỉ đánh dấu bảng khi có dòng tiêu đề h = d - 1 ngay trước dòng phân cách d
        # có số cột khớp nhau (C_header == C_delim >= 1) và các dòng dữ liệu liền kề
        table_line_indices: set[int] = set()

        def _parse_delim_cols(line_str: str) -> int | None:
            if len(line_str) - len(line_str.lstrip(" ")) >= 4 or line_str.startswith("\t"):
                return None
            s = line_str.strip()
            if not s or not all(c in "|-: \t" for c in s):
                return None
            if s.startswith("- "):
                return None
            if "|" not in s:
                return None
            cols = [c.strip() for c in s.split("|")]
            if cols and cols[0] == "":
                cols.pop(0)
            if cols and cols[-1] == "":
                cols.pop()
            if not cols:
                return None
            if any(not c or not re.match(r"^:?-+:?$", c) for c in cols):
                return None
            return len(cols)

        def _count_header_cols(line_str: str) -> int:
            if not cls._is_table_line(line_str):
                return 0
            cols = cls._escaped_split_table_row(line_str)
            if cols and cols[0] == "":
                cols.pop(0)
            if cols and cols[-1] == "":
                cols.pop()
            return len(cols)

        i_scan = 1
        while i_scan < n:
            d_cols = _parse_delim_cols(lines[i_scan])
            if d_cols is not None:
                h_idx = i_scan - 1
                if h_idx not in table_line_indices and lines[h_idx].strip() != "":
                    if len(lines[h_idx]) - len(lines[h_idx].lstrip(" ")) < 4 and not lines[h_idx].startswith("\t"):
                        h_cols = _count_header_cols(lines[h_idx])
                        if h_cols == d_cols and h_cols > 0:
                            table_line_indices.add(h_idx)
                            table_line_indices.add(i_scan)
                            k = i_scan + 1
                            while k < n:
                                k_line = lines[k]
                                if k_line.strip() == "":
                                    break
                                if len(k_line) - len(k_line.lstrip(" ")) >= 4 or k_line.startswith("\t"):
                                    break
                                if re.match(r"^[ ]{0,3}(`{3,}|~{3,}|#{1,6}([ \t]|$)|([-*_])([ \t]*\3){2,}[ \t]*$|[+*-][ \t]|\d+[.)][ \t])", k_line):
                                    break
                                if not cls._is_table_line(k_line):
                                    break
                                table_line_indices.add(k)
                                k += 1
                            i_scan = k
                            continue
            i_scan += 1

        in_fence = False
        fence_bq_depth = 0
        fence_char = ""
        fence_len = 0

        in_display_math = False
        math_bq_depth = 0
        math_indent = ""

        in_indented_code = False
        indented_bq_depth = 0
        can_start_indented = True

        for idx, line in enumerate(lines):
            stripped = line.strip()
            bq_depth, rest = cls._get_bq_depth_and_rest(line)
            stripped_rest = rest.strip()

            # A. Đang ở trong khối mã lập trình (FENCED_CODE, bao gồm cả trong blockquote)
            if in_fence:
                if bq_depth < fence_bq_depth:
                    # Khối trích dẫn chứa rào chắn đã kết thúc trước dòng này (CommonMark container block)
                    in_fence = False
                    fence_bq_depth = 0
                    fence_char = ""
                    fence_len = 0
                    can_start_indented = True
                    # Không continue: dòng này rơi ra ngoài fence và cần được xử lý tiếp bên dưới
                elif cls._is_fence_close_line(line, fence_bq_depth, fence_char, fence_len):
                    out_lines.append(line)
                    in_fence = False
                    fence_bq_depth = 0
                    fence_char = ""
                    fence_len = 0
                    can_start_indented = True
                    continue
                else:
                    out_lines.append(line)
                    continue

            # B. Đang ở trong khối toán display nhiều dòng (DISPLAY_MATH)
            if in_display_math:
                if bq_depth < math_bq_depth:
                    # Khối trích dẫn chứa khối toán đã kết thúc trước dòng này (CommonMark container block)
                    in_display_math = False
                    math_bq_depth = 0
                    math_indent = ""
                    can_start_indented = True
                    # Chèn dòng phân cách để đóng khối trích dẫn cũ, tránh CommonMark lazy continuation
                    # nếu dòng trước đó có nội dung và dòng hiện tại không phải dòng trống
                    if out_lines and cls._get_bq_depth_and_rest(out_lines[-1])[1].strip() != "" and stripped_rest != "":
                        m_curr_bq = _BQ_PREFIX_RE.match(line)
                        curr_bq_pref = m_curr_bq.group(0) if m_curr_bq else ""
                        out_lines.append(curr_bq_pref.rstrip())
                    # Không continue: dòng này rơi ra ngoài trích dẫn của khối toán và cần được xử lý tiếp bên dưới
                else:
                    line_to_emit = line
                    # Nếu dòng có độ sâu trích dẫn sâu hơn math_bq_depth và kết thúc bằng $$,
                    # đây là dấu đóng giả ở cấp lồng nhau. Thay $$ bằng dấu giữ chỗ nội bộ
                    # để dollarmath của markdown-it không đóng sớm ở cấp lồng nhau này.
                    if (
                        fake_close_placeholder
                        and bq_depth > math_bq_depth
                        and (stripped_rest.endswith("$$") or re.search(r"\$\$[ \t]*[,.;:!?]?$", stripped_rest))
                    ):
                        m_trail = re.search(r"\$\$([ \t]*[,.;:!?]?[ \t]*)$", line)
                        if m_trail:
                            trail_punct = m_trail.group(1)
                            line_to_emit = line[:m_trail.start()] + fake_close_placeholder + trail_punct
                    out_lines.append(line_to_emit)

                    # Chỉ đóng khối toán khi ở cùng độ sâu trích dẫn math_bq_depth
                    # và dòng kết thúc bằng $$ (có thể kèm dấu câu)
                    is_close = False
                    if bq_depth == math_bq_depth:
                        if stripped_rest.endswith("$$") or re.search(r"\$\$[ \t]*[,.;:!?]?$", stripped_rest):
                            is_close = True

                    if is_close:
                        in_display_math = False
                        math_bq_depth = 0
                        can_start_indented = True
                        # Đảm bảo dòng trống sau khối toán nếu dòng tiếp theo có chữ
                        if idx + 1 < n and lines[idx + 1].strip() != "":
                            next_bq_depth, next_rest = cls._get_bq_depth_and_rest(lines[idx + 1])
                            if next_rest.strip() != "":
                                if next_bq_depth < bq_depth:
                                    m_next_bq = _BQ_PREFIX_RE.match(lines[idx + 1])
                                    next_pref = m_next_bq.group(0) if m_next_bq else ""
                                    out_lines.append(next_pref.rstrip())
                                else:
                                    out_lines.append(math_indent.rstrip())
                    continue

            # C. Dòng trống
            if stripped == "":
                in_indented_code = False
                can_start_indented = True
                out_lines.append(line)
                continue

            # D. Bắt đầu khối mã lập trình (code fence: >=3 backticks hoặc tildes, cấp gốc hoặc trong blockquote)
            m_open_fence = cls._parse_fence_open_line(line)
            if m_open_fence is not None:
                in_fence = True
                fence_bq_depth, fence_char, fence_len = m_open_fence
                in_indented_code = False
                out_lines.append(line)
                continue

            # E. Khối mã thụt lề (Indented Code Block - CommonMark 4.4, cấp gốc hoặc trong blockquote)
            is_indented_line = (rest.startswith("    ") or rest.startswith("\t")) and (stripped_rest != "")
            if (can_start_indented or (in_indented_code and bq_depth == indented_bq_depth)) and is_indented_line:
                in_indented_code = True
                indented_bq_depth = bq_depth
                out_lines.append(line)
                continue

            in_indented_code = False

            # F. Kiểm tra bảng GFM: dòng phải thuộc khối bảng có hàng phân cách cột
            if idx in table_line_indices and cls._is_table_line(line):
                can_start_indented = True
                out_lines.append(line)
                continue

            # G. Xử lý trường hợp nhãn hai chấm dẫn nhập: 'ta có:$$...' hoặc '> ta có:$$...'
            line_spans = cls._find_code_spans(line)

            def _is_inside_code_span(pos: int) -> bool:
                for span_st, span_en in line_spans:
                    if span_st <= pos < span_en:
                        return True
                return False

            colon_match = re.search(r"([^\n$]+:)[ \t]*(\$\$[^\n$].*?\$\$)", line)
            if colon_match and not _is_inside_code_span(colon_match.start(2)):
                m_bq = _BQ_PREFIX_RE.match(line)
                bq_pref = m_bq.group(0) if m_bq else ""
                sep_line = bq_pref.rstrip() if bq_pref else ""

                prefix = line[:colon_match.start(2)].rstrip()
                rest_math = line[colon_match.start(2):]
                if out_lines and cls._get_bq_depth_and_rest(out_lines[-1])[1].strip() != "":
                    out_lines.append(sep_line)
                out_lines.append(prefix)
                out_lines.append(sep_line)
                line = (bq_pref + rest_math) if bq_pref else rest_math
                stripped = line.strip()
                line_spans = cls._find_code_spans(line)

            # H. Dòng bắt đầu bằng $$ (sau khoảng trắng thụt lề hoặc tiền tố blockquote nếu có)
            m_bq = _BQ_PREFIX_RE.match(line)
            bq_pref = m_bq.group(0) if m_bq else ""
            line_after_bq = line[len(bq_pref):]
            m_open_math = re.match(r"^([ \t]*)\$\$", line_after_bq)
            if m_open_math and not _is_inside_code_span(len(bq_pref) + m_open_math.start(1)):
                raw_indent = m_open_math.group(1)
                # Nếu thụt lề >= 4 khoảng trắng ở cấp gốc (dòng tiếp nối đoạn văn),
                # chuẩn hóa indent về "" để dòng trống chèn trước không biến nó thành
                # indented code block ở bước markdown-it
                indent = "" if len(raw_indent.expandtabs(4)) >= 4 else raw_indent
                math_indent = bq_pref + indent

                # Đảm bảo có dòng trống phía trước nếu dòng trước có chữ
                if out_lines and cls._get_bq_depth_and_rest(out_lines[-1])[1].strip() != "":
                    out_lines.append(math_indent.rstrip())

                # Kiểm tra khối đóng ngay trên cùng một dòng: '  $$content$$[punct] tail'
                m_single = re.match(r"^([ \t]*)\$\$(.*?)\$\$([ \t]*[,.;:!?]?)(.*)$", line_after_bq)
                if m_single:
                    content = m_single.group(2)
                    trail_punct = m_single.group(3).strip()
                    tail = m_single.group(4)

                    block_line = f"{math_indent}$${content}$$"
                    out_lines.append(block_line)

                    after_text = f"{trail_punct}{tail}".strip()
                    if after_text:
                        out_lines.append(math_indent.rstrip())
                        out_lines.append(f"{math_indent}{after_text}")
                    elif idx + 1 < n and lines[idx + 1].strip() != "":
                        next_bq_depth, next_rest = cls._get_bq_depth_and_rest(lines[idx + 1])
                        if next_rest.strip() != "":
                            if next_bq_depth < bq_depth:
                                m_next_bq = _BQ_PREFIX_RE.match(lines[idx + 1])
                                next_pref = m_next_bq.group(0) if m_next_bq else ""
                                out_lines.append(next_pref.rstrip())
                            else:
                                out_lines.append(math_indent.rstrip())
                    can_start_indented = True
                    continue
                else:
                    # Khối mở nhiều dòng: chuyển trạng thái sang DISPLAY_MATH
                    in_display_math = True
                    math_bq_depth = bq_depth
                    out_lines.append(line)
                    continue

            # Đánh giá xem dòng có thể mở khối mã thụt lề ở dòng kế tiếp hay không
            if stripped_rest == "" or re.match(r"^[ ]{0,3}(#{1,6}([ \t]|$)|([-*_])([ \t]*\3){2,}[ \t]*$)", rest):
                can_start_indented = True
            else:
                can_start_indented = False

            out_lines.append(line)

        return "\n".join(out_lines)

    @classmethod
    def _normalize_math_delimiters(cls, text: str) -> str:
        """Đổi \\( .. \\) thành $..$ và \\[ .. \\] thành $$..$$ (ngoài đoạn mã) để markdown-it nhận ra công thức."""
        segments = cls._split_code_segments(text)
        out: list[str] = []
        for chunk, is_code in segments:
            if is_code:
                out.append(chunk)
            else:
                seg = cls._convert_delimited(chunk, "\\[", "\\]", "$$", _MAX_DISPLAY_MATH, strip=False)
                seg = cls._convert_delimited(seg, "\\(", "\\)", "$", _MAX_INLINE_MATH, strip=True)
                out.append(seg)
        return "".join(out)

    def _sanitize_html(self, text: str) -> str:
        """Loại bỏ an toàn các thẻ HTML và script độc hại,
        đồng thời bảo toàn nguyên vẹn mọi khối công thức toán ($...$, $$...$$)
        và các toán tử so sánh <, > (L7)."""
        if not text:
            return ""
        # Tách riêng đoạn mã và các khối công thức toán để không bao giờ bị can thiệp
        segments = self._split_code_segments(text)
        out: list[str] = []
        for chunk, is_code in segments:
            if is_code:
                out.append(chunk)
                continue
            parts = _MATH_SEGMENT.split(chunk)
            for i in range(0, len(parts), 2):
                c = parts[i]
                # Loại bỏ thẻ script/style kèm nội dung bên trong
                c = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", c, flags=re.DOTALL | re.IGNORECASE)
                # Loại bỏ các thẻ HTML thật (tên thẻ đã biết); chữ như "a<b và c>d" được giữ nguyên
                c = _HTML_TAG.sub("", c)
                parts[i] = c
            out.append("".join(parts))
        return "".join(out)

    def _parse_inlines(self, inline_token: Any, warnings: list[str] | None = None) -> list[Inline]:
        """Chuyển đổi token inline của markdown-it thành danh sách Inline IR."""
        inlines: list[Inline] = []
        if not inline_token or not getattr(inline_token, "children", None):
            return inlines

        for child in inline_token.children:
            ctype = child.type
            if ctype in ("html_inline", "html_block"):
                # Bỏ qua hoàn toàn thẻ HTML thô
                continue
            elif ctype in ("math_inline", "math_inline_double"):
                inlines.append(MathInline(latex=child.content.strip()))
            elif ctype == "math_block":
                inlines.append(MathInline(latex=child.content.strip()))
            elif ctype in ("softbreak", "hardbreak"):
                inlines.append(LineBreak())
            elif ctype in ("text", "code_inline"):
                content = child.content
                if content:
                    inlines.append(Text(text=content))
                if ctype == "code_inline" and warnings is not None:
                    msg = "Định dạng kiểu chữ (in đậm, in nghiêng, gạch ngang, mã nội tuyến...) đã được chuyển về nét viết tay chuẩn."
                    if msg not in warnings:
                        warnings.append(msg)
            else:
                # Các thẻ định dạng như strong, em, s, link... ta lấy nội dung text bên trong
                if child.content:
                    inlines.append(Text(text=child.content))
                if ctype in ("strong_open", "em_open", "s_open", "link_open") and warnings is not None:
                    msg = "Định dạng kiểu chữ (in đậm, in nghiêng, gạch ngang, mã nội tuyến...) đã được chuyển về nét viết tay chuẩn."
                    if msg not in warnings:
                        warnings.append(msg)

        # Gộp các Text inline liền kề để tránh chèn khoảng trắng giả tạo trước dấu câu (L6)
        merged: list[Inline] = []
        for inl in inlines:
            if isinstance(inl, Text) and merged and isinstance(merged[-1], Text):
                merged[-1].text += inl.text
            else:
                merged.append(inl)
        return merged

    def _extract_list_start(self, tok: Any) -> int:
        """Trích xuất số bắt đầu cho ordered list từ thuộc tính token, mặc định 1."""
        raw_start = tok.attrGet("start") if hasattr(tok, "attrGet") else None
        if raw_start is None and getattr(tok, "attrs", None):
            if isinstance(tok.attrs, dict):
                raw_start = tok.attrs.get("start")
            elif isinstance(tok.attrs, (list, tuple)):
                for item in tok.attrs:
                    if isinstance(item, (list, tuple)) and len(item) == 2 and item[0] == "start":
                        raw_start = item[1]
                        break
        if raw_start is not None:
            try:
                return int(raw_start)
            except (ValueError, TypeError):
                return 1
        return 1

    def _parse_list(
        self, tokens: list[Any], start_idx: int, unsupported: list[str], warnings: list[str] | None = None
    ) -> tuple[ListBlock, int]:
        """Phân tích danh sách Markdown theo kiểu đệ quy để bảo toàn phân cấp danh sách lồng nhau."""
        tok = tokens[start_idx]
        is_ordered = (tok.type == "ordered_list_open")
        start = self._extract_list_start(tok) if is_ordered else 1
        close_type = "ordered_list_close" if is_ordered else "bullet_list_close"
        items: list[list[Block]] = []
        i = start_idx + 1
        n = len(tokens)

        while i < n and tokens[i].type != close_type:
            if tokens[i].type == "list_item_open":
                item_blocks, i = self._parse_blocks(tokens, i + 1, "list_item_close", unsupported, warnings)
                items.append(self._normalize_item_blocks(item_blocks, unsupported))
            i += 1

        return ListBlock(ordered=is_ordered, items=items, start=start), i

    @staticmethod
    def _normalize_item_blocks(blocks: list[Block], unsupported: list[str]) -> list[Block]:
        """Mục danh sách chỉ giữ Paragraph / ListBlock / MathBlock (engine dàn trang đúng các loại này)."""
        out: list[Block] = []
        for b in blocks:
            if isinstance(b, Heading):
                out.append(Paragraph(inlines=b.inlines))
            elif isinstance(b, Table):
                unsupported.append("table: table inside list item")
            else:
                out.append(b)
        return out

    def _parse_table(self, tokens: list[Any], i: int, warnings: list[str] | None = None) -> tuple[Table, int]:
        n = len(tokens)
        rows: list[TableRow] = []
        col_alignments: list[str] = []
        i += 1
        while i < n and tokens[i].type != "table_close":
            if tokens[i].type == "tr_open":
                cells: list[TableCell] = []
                i += 1
                while i < n and tokens[i].type != "tr_close":
                    if tokens[i].type in ("th_open", "td_open"):
                        cell_token = tokens[i]
                        style_attr = cell_token.attrs.get("style", "") if cell_token.attrs else ""
                        align = "left"
                        if "center" in style_attr:
                            align = "center"
                        elif "right" in style_attr:
                            align = "right"
                        elif "left" in style_attr:
                            align = "left"

                        if cell_token.type == "th_open":
                            col_alignments.append(align)

                        cell_inlines = []
                        if i + 1 < n and tokens[i + 1].type == "inline":
                            cell_inlines = self._parse_inlines(tokens[i + 1], warnings)
                            i += 1
                        cells.append(TableCell(blocks=[Paragraph(inlines=cell_inlines)]))
                    i += 1
                rows.append(TableRow(cells=cells))
            i += 1
        return Table(rows=rows, border_style=TableBorder.ALL, col_alignments=col_alignments), i

    def _parse_blocks(
        self, tokens: list[Any], i: int, close_type: str | None, unsupported: list[str], warnings: list[str] | None = None
    ) -> tuple[list[Block], int]:
        """Đọc các khối từ vị trí ``i`` tới token ``close_type`` (không tiêu thụ) hoặc hết token."""
        blocks: list[Block] = []
        n = len(tokens)
        while i < n and (close_type is None or tokens[i].type != close_type):
            tok = tokens[i]

            # 1. Heading
            if tok.type == "heading_open":
                level = int(tok.tag[1]) if len(tok.tag) > 1 and tok.tag[1].isdigit() else 1
                inlines = []
                if i + 1 < n and tokens[i + 1].type == "inline":
                    inlines = self._parse_inlines(tokens[i + 1], warnings)
                    i += 1
                blocks.append(Heading(level=level, inlines=inlines))

            # 2. Paragraph
            elif tok.type == "paragraph_open":
                inlines = []
                if i + 1 < n and tokens[i + 1].type == "inline":
                    inlines = self._parse_inlines(tokens[i + 1], warnings)
                    i += 1
                if inlines:
                    blocks.append(Paragraph(inlines=inlines))

            # 3. Math Block ($$...$$, \[...\], \begin{align}...\end{align})
            elif tok.type in ("math_block", "math_block_label", "math_block_end", "amsmath"):
                if tok.content.strip():
                    blocks.append(MathBlock(latex=tok.content.strip()))

            # 4. List Block (đệ quy lồng nhau)
            elif tok.type in ("bullet_list_open", "ordered_list_open"):
                list_block, i = self._parse_list(tokens, i, unsupported, warnings)
                blocks.append(list_block)

            # 5. Table Block
            elif tok.type == "table_open":
                table, i = self._parse_table(tokens, i, warnings)
                blocks.append(table)

            # 6. Code Block / Fenced Code
            elif tok.type in ("fence", "code_block"):
                info = (tok.info or "").strip()
                unsupported.append(f"code_block: {info}" if info else "code_block")

            # 7. Horizontal Rule (---)
            elif tok.type == "hr":
                unsupported.append("hr: horizontal rule")

            i += 1
        return blocks, i

    def import_text(self, text: str) -> ImportResult:
        """Phân tích chuỗi Markdown thành Document IR."""
        from markdown_it import MarkdownIt
        from mdit_py_plugins.amsmath import amsmath_plugin
        from mdit_py_plugins.dollarmath import dollarmath_plugin

        normalized = self._normalize_math_delimiters(text or "")
        placeholder = self._choose_fake_close_placeholder(normalized) if "$$" in normalized else None
        isolated = self._isolate_display_math_blocks(normalized, fake_close_placeholder=placeholder)
        clean_content = self._sanitize_html(isolated)
        # allow_space=False: "$ x $" và "5$ rồi 10$" (tiền tệ) không bị nhận nhầm là công thức
        md = (
            MarkdownIt("commonmark", {"html": False})
            .enable("table")
            .enable("strikethrough")
            .use(dollarmath_plugin, allow_space=False, double_inline=True)
            .use(amsmath_plugin)
        )
        tokens = md.parse(clean_content)
        self._restore_fake_close_placeholder(tokens, placeholder)

        warnings: list[str] = []
        unsupported: list[str] = []
        blocks, _ = self._parse_blocks(tokens, 0, None, unsupported, warnings)
        return ImportResult(document=Document(blocks=blocks), warnings=warnings, unsupported=unsupported)

    def import_file(self, path: str) -> ImportResult:
        """Đọc tệp Markdown từ đĩa."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy tệp Markdown: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.import_text(content)
