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

# Đoạn mã (fence / inline code): không đụng tới khi đổi dấu phân cách toán hay lọc HTML
_CODE_SEGMENT = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]*`)", re.DOTALL)
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

    def _parse_inlines(self, inline_token: Any) -> list[Inline]:
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
            else:
                # Các thẻ định dạng như strong, em... ta lấy nội dung text bên trong
                if child.content:
                    inlines.append(Text(text=child.content))

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

    def _parse_list(self, tokens: list[Any], start_idx: int, unsupported: list[str]) -> tuple[ListBlock, int]:
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
                item_blocks, i = self._parse_blocks(tokens, i + 1, "list_item_close", unsupported)
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

    def _parse_table(self, tokens: list[Any], i: int) -> tuple[Table, int]:
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
                            cell_inlines = self._parse_inlines(tokens[i + 1])
                            i += 1
                        cells.append(TableCell(blocks=[Paragraph(inlines=cell_inlines)]))
                    i += 1
                rows.append(TableRow(cells=cells))
            i += 1
        return Table(rows=rows, border_style=TableBorder.ALL, col_alignments=col_alignments), i

    def _parse_blocks(
        self, tokens: list[Any], i: int, close_type: str | None, unsupported: list[str]
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
                    inlines = self._parse_inlines(tokens[i + 1])
                    i += 1
                blocks.append(Heading(level=level, inlines=inlines))

            # 2. Paragraph
            elif tok.type == "paragraph_open":
                inlines = []
                if i + 1 < n and tokens[i + 1].type == "inline":
                    inlines = self._parse_inlines(tokens[i + 1])
                    i += 1
                if inlines:
                    blocks.append(Paragraph(inlines=inlines))

            # 3. Math Block ($$...$$, \[...\], \begin{align}...\end{align})
            elif tok.type in ("math_block", "math_block_label", "math_block_end", "amsmath"):
                if tok.content.strip():
                    blocks.append(MathBlock(latex=tok.content.strip()))

            # 4. List Block (đệ quy lồng nhau)
            elif tok.type in ("bullet_list_open", "ordered_list_open"):
                list_block, i = self._parse_list(tokens, i, unsupported)
                blocks.append(list_block)

            # 5. Table Block
            elif tok.type == "table_open":
                table, i = self._parse_table(tokens, i)
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

        clean_content = self._sanitize_html(self._normalize_math_delimiters(text or ""))
        # allow_space=False: "$ x $" và "5$ rồi 10$" (tiền tệ) không bị nhận nhầm là công thức
        md = (
            MarkdownIt("commonmark", {"html": False})
            .enable("table")
            .use(dollarmath_plugin, allow_space=False, double_inline=True)
            .use(amsmath_plugin)
        )
        tokens = md.parse(clean_content)

        warnings: list[str] = []
        unsupported: list[str] = []
        blocks, _ = self._parse_blocks(tokens, 0, None, unsupported)
        return ImportResult(document=Document(blocks=blocks), warnings=warnings, unsupported=unsupported)

    def import_file(self, path: str) -> ImportResult:
        """Đọc tệp Markdown từ đĩa."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy tệp Markdown: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.import_text(content)
