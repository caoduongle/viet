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


class MarkdownImporter(BaseImporter):
    """Nạp tài liệu Markdown, hỗ trợ tiêu đề, danh sách, bảng GFM và công thức toán học."""

    def __init__(self):
        # Kiểm tra và nạp thư viện markdown-it-py
        require_dependency("markdown_it", feature_desc="tệp Markdown (.md)")
        require_dependency("mdit_py_plugins", feature_desc="tính năng toán học trong Markdown")

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

    @classmethod
    def _isolate_display_math_blocks(cls, seg: str) -> str:
        """Đảm bảo các khối công thức toán display ($$..$$) bắt đầu ở dòng mới hoặc liền sau
        dấu hai chấm có dòng trống phân cách chuẩn CommonMark, ngoại trừ các khối mã (code fence),
        đoạn mã nội dòng (code span) và các ô bảng GFM.

        Sử dụng máy trạng thái một lượt (single-pass line scanner) đạt độ phức tạp O(n) tuyến tính,
        chuẩn hóa ngắt dòng CRLF và bảo toàn 100% nội dung bên trong code fence."""
        if not seg:
            return ""

        # 1. Chuẩn hóa CRLF / CR thành \n để tránh lỗi bám ký tự \r
        seg = seg.replace("\r\n", "\n").replace("\r", "\n")

        if "$$" not in seg:
            return seg

        lines = seg.split("\n")
        out_lines: list[str] = []
        n = len(lines)

        in_fence = False
        fence_char = ""
        fence_len = 0

        in_display_math = False
        math_indent = ""

        for idx, line in enumerate(lines):
            stripped = line.strip()

            # A. Đang ở trong khối mã lập trình (FENCED_CODE)
            if in_fence:
                out_lines.append(line)
                # Dòng đóng fence: cùng ký tự, độ dài >= fence_len, không chứa ký tự khác ngoài khoảng trắng
                m_close = re.match(r"^[ \t]*(`{3,}|~{3,})[ \t]*$", line)
                if m_close and m_close.group(1)[0] == fence_char and len(m_close.group(1)) >= fence_len:
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                continue

            # B. Kiểm tra bắt đầu khối mã lập trình (code fence: >=3 backticks hoặc tildes)
            m_open_fence = re.match(r"^[ \t]*(`{3,}|~{3,})", line)
            if m_open_fence:
                in_fence = True
                fence_char = m_open_fence.group(1)[0]
                fence_len = len(m_open_fence.group(1))
                out_lines.append(line)
                continue

            # C. Đang ở trong khối toán display nhiều dòng (DISPLAY_MATH)
            if in_display_math:
                out_lines.append(line)
                # Kiểm tra kết thúc khối toán: dòng kết thúc bằng $$ (có thể kèm dấu câu)
                if stripped.endswith("$$") or re.search(r"\$\$[ \t]*[,.;:!?]?$", stripped):
                    in_display_math = False
                    # Đảm bảo dòng trống sau khối toán nếu dòng tiếp theo có chữ
                    if idx + 1 < n and lines[idx + 1].strip() != "":
                        out_lines.append(math_indent)
                continue

            # D. Kiểm tra bảng GFM: dòng chứa phân tách cột '|'
            # (bao gồm cả hàng chuẩn | a | b | và hàng rút gọn a | b)
            if "|" in line and not stripped.startswith("$$"):
                out_lines.append(line)
                continue

            # E. Xử lý trường hợp nhãn hai chấm dẫn nhập: 'ta có:$$...' hoặc 'với: $$...'
            # Tuyệt đối bỏ qua nếu nằm bên trong đoạn mã nội dòng `...`
            def _is_inside_code_span(txt: str, pos: int) -> bool:
                for span in re.finditer(r"`[^`\n]*`", txt):
                    if span.start() <= pos < span.end():
                        return True
                return False

            colon_match = re.search(r"([^\n$]+:)[ \t]*(\$\$[^\n$].*?\$\$)", line)
            if colon_match and not _is_inside_code_span(line, colon_match.start(2)):
                prefix = line[:colon_match.start(2)].rstrip()
                rest = line[colon_match.start(2):]
                if out_lines and out_lines[-1].strip() != "":
                    out_lines.append("")
                out_lines.append(prefix)
                out_lines.append("")
                line = rest
                stripped = line.strip()

            # F. Dòng bắt đầu bằng $$ (sau khoảng trắng thụt lề nếu có)
            m_open_math = re.match(r"^([ \t]*)\$\$", line)
            if m_open_math and not _is_inside_code_span(line, m_open_math.start(1)):
                indent = m_open_math.group(1)
                math_indent = indent

                # Đảm bảo có dòng trống phía trước nếu dòng trước có chữ
                if out_lines and out_lines[-1].strip() != "":
                    out_lines.append(indent)

                # Kiểm tra khối đóng ngay trên cùng một dòng: '  $$content$$[punct] tail'
                m_single = re.match(r"^([ \t]*)\$\$(.*?)\$\$([ \t]*[,.;:!?]?)(.*)$", line)
                if m_single:
                    content = m_single.group(2)
                    trail_punct = m_single.group(3).strip()
                    tail = m_single.group(4)

                    block_line = f"{indent}$${content}$$"
                    out_lines.append(block_line)

                    after_text = f"{trail_punct}{tail}".strip()
                    if after_text:
                        out_lines.append(indent)
                        out_lines.append(f"{indent}{after_text}")
                    elif idx + 1 < n and lines[idx + 1].strip() != "":
                        out_lines.append(indent)
                    continue
                else:
                    # Khối mở nhiều dòng: chuyển trạng thái sang DISPLAY_MATH
                    in_display_math = True
                    out_lines.append(line)
                    continue

            out_lines.append(line)

        return "\n".join(out_lines)

    @classmethod
    def _normalize_math_delimiters(cls, text: str) -> str:
        """Đổi \\( .. \\) thành $..$ và \\[ .. \\] thành $$..$$ (ngoài đoạn mã) để markdown-it nhận ra công thức."""
        parts = _CODE_SEGMENT.split(text)
        for i in range(0, len(parts), 2):
            seg = parts[i]
            seg = cls._convert_delimited(seg, "\\[", "\\]", "$$", _MAX_DISPLAY_MATH, strip=False)
            seg = cls._convert_delimited(seg, "\\(", "\\)", "$", _MAX_INLINE_MATH, strip=True)
            parts[i] = seg
        return "".join(parts)

    def _sanitize_html(self, text: str) -> str:
        """Loại bỏ an toàn các thẻ HTML và script độc hại,
        đồng thời bảo toàn nguyên vẹn mọi khối công thức toán ($...$, $$...$$)
        và các toán tử so sánh <, > (L7)."""
        if not text:
            return ""
        # Tách riêng đoạn mã và các khối công thức toán để không bao giờ bị can thiệp
        out: list[str] = []
        for k, code_part in enumerate(_CODE_SEGMENT.split(text)):
            if k % 2:
                out.append(code_part)
                continue
            parts = _MATH_SEGMENT.split(code_part)
            for i in range(0, len(parts), 2):
                chunk = parts[i]
                # Loại bỏ thẻ script/style kèm nội dung bên trong
                chunk = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", chunk, flags=re.DOTALL | re.IGNORECASE)
                # Loại bỏ các thẻ HTML thật (tên thẻ đã biết); chữ như "a<b và c>d" được giữ nguyên
                chunk = _HTML_TAG.sub("", chunk)
                parts[i] = chunk
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

        clean_content = self._sanitize_html(self._isolate_display_math_blocks(self._normalize_math_delimiters(text or "")))
        # allow_space=False: "$ x $" và "5$ rồi 10$" (tiền tệ) không bị nhận nhầm là công thức
        md = (
            MarkdownIt("commonmark", {"html": False})
            .enable("table")
            .enable("strikethrough")
            .use(dollarmath_plugin, allow_space=False, double_inline=True)
            .use(amsmath_plugin)
        )
        tokens = md.parse(clean_content)

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
