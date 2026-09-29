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


class MarkdownImporter(BaseImporter):
    """Nạp tài liệu Markdown, hỗ trợ tiêu đề, danh sách, bảng GFM và công thức toán học."""

    def __init__(self):
        # Kiểm tra và nạp thư viện markdown-it-py
        require_dependency("markdown_it", feature_desc="tệp Markdown (.md)")
        require_dependency("mdit_py_plugins", feature_desc="tính năng toán học trong Markdown")

    def _sanitize_html(self, text: str) -> str:
        """Loại bỏ hoàn toàn các thẻ script, style và HTML tags thô để bảo mật và tránh ô nhiễm nét chữ."""
        # Xoá toàn bộ nội dung trong <script>...</script> và <style>...</style>
        no_scripts = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        # Xoá các thẻ HTML đơn lẻ <tag> hoặc </tag>
        clean_text = re.sub(r"<[^>]+>", "", no_scripts)
        return clean_text

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
            elif ctype == "math_inline":
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

        return inlines

    def import_text(self, text: str) -> ImportResult:
        """Phân tích chuỗi Markdown thành Document IR."""
        from markdown_it import MarkdownIt
        from mdit_py_plugins.dollarmath import dollarmath_plugin

        clean_content = self._sanitize_html(text or "")
        md = MarkdownIt("commonmark", {"html": False}).enable("table").use(dollarmath_plugin)
        tokens = md.parse(clean_content)

        blocks: list[Block] = []
        warnings: list[str] = []
        unsupported: list[str] = []

        i = 0
        n = len(tokens)
        while i < n:
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

            # 3. Math Block ($$...$$)
            elif tok.type in ("math_block", "math_block_end"):
                if tok.content.strip():
                    blocks.append(MathBlock(latex=tok.content.strip()))

            # 4. List Block
            elif tok.type in ("bullet_list_open", "ordered_list_open"):
                is_ordered = (tok.type == "ordered_list_open")
                items: list[list[Block]] = []
                i += 1
                while i < n and tokens[i].type not in ("bullet_list_close", "ordered_list_close"):
                    if tokens[i].type == "list_item_open":
                        item_blocks: list[Block] = []
                        i += 1
                        while i < n and tokens[i].type != "list_item_close":
                            if tokens[i].type == "paragraph_open":
                                if i + 1 < n and tokens[i + 1].type == "inline":
                                    item_blocks.append(Paragraph(inlines=self._parse_inlines(tokens[i + 1])))
                                    i += 1
                            i += 1
                        items.append(item_blocks)
                    else:
                        i += 1
                blocks.append(ListBlock(ordered=is_ordered, items=items))

            # 5. Table Block
            elif tok.type == "table_open":
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
                blocks.append(Table(rows=rows, border_style=TableBorder.ALL, col_alignments=col_alignments))

            i += 1

        return ImportResult(document=Document(blocks=blocks), warnings=warnings, unsupported=unsupported)

    def import_file(self, path: str) -> ImportResult:
        """Đọc tệp Markdown từ đĩa."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy tệp Markdown: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.import_text(content)
