"""Động cơ bố cục tài liệu (Document Layout Engine) và chuyển đổi sang nét vẽ Xournal++."""
from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

from chuviettay.config import MAXH
from chuviettay.controller.results import WriteOptions, WriteResult
from chuviettay.document.ir import Document, Heading, MathBlock, MathInline, PageBreak, Paragraph, Symbol, Table, Text
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.layout.table_layout import TableLayoutEngine
from chuviettay.math.parser import parse_latex_math
from chuviettay.model import xopp
from chuviettay.model.text_utils import Stroke, fmt, normalize_text, place
from chuviettay.model.writer import Writer

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank


class DocumentLayoutEngine:
    """Điều phối bố cục các khối (Paragraph, Heading, Table, PageBreak...) và sinh nét vẽ."""

    def __init__(self, bank: Bank, opts: WriteOptions):
        self.bank = bank
        self.opts = opts
        self.opts.validate()
        self.rnd = random.Random(opts.seed)
        self.J = opts.jitter
        self.S = opts.scale
        self.line_h = opts.line or bank.d["line"]
        self.width = opts.width or bank.d["width"]
        self.x0 = bank.d["x0"]
        self.gaps = [g for g in bank.d["wgaps"] if 6.0 <= g <= 20.0] or [11.0]
        self.wr = Writer(bank, self.rnd, self.J, not opts.strict_case, opts.space)

    def _render_text_line(
        self,
        line_items: list[tuple[float, list[Stroke], float]],
        base_y: float,
        start_x: float,
    ) -> list[str]:
        """Tạo danh sách các thẻ <stroke> XML cho một dòng chữ với hiệu ứng run tay ngẫu nhiên."""
        out = []
        if not line_items:
            return out

        slope, amp = self.rnd.gauss(0, 0.0015 * self.J), 0.45 * self.J
        wl, ph = self.rnd.uniform(140, 260), self.rnd.uniform(0, 6.283)
        xo = start_x + self.rnd.gauss(0, 1.2 * self.J)

        for start, st, w in line_items:
            if not st:
                continue
            s = self.S * (1 + self.rnd.gauss(0, 0.02 * self.J))
            rot = self.rnd.gauss(0, 0.010 * self.J)
            dy = self.rnd.gauss(0, 0.35 * self.J)
            for pts in place(st, 0.0, 0.0, s, rot):
                fin = []
                for x, y in pts:
                    X = start + x
                    fin.append((xo + X, base_y + dy + y + slope * X + amp * math.sin(6.283 * X / wl + ph)))
                out.append(xopp.stroke_xml(fin, self.bank.pen, self.opts.color, self.opts.wscale * (1 + self.rnd.gauss(0, 0.02 * self.J))))

        return out

    def render(self, document: Document, out_path: str) -> WriteResult:
        """Thực hiện bố cục toàn bộ Document IR và ghi file .xopp."""
        pages_xml: list[list[str]] = []
        cur_page: list[str] = []
        cur_y = 20.0
        max_page_y = MAXH - 40.0
        total_lines = 0
        total_strokes = 0
        ntok = nmiss = 0

        def new_page():
            nonlocal cur_page, cur_y
            if cur_page or not pages_xml:
                pages_xml.append(cur_page)
            cur_page = []
            cur_y = 20.0

        if not document.blocks:
            # Tài liệu rỗng: sinh 1 trang trắng
            new_page()
        else:
            for block in document.blocks:
                if isinstance(block, PageBreak):
                    new_page()
                    continue

                if isinstance(block, (Paragraph, Heading)):
                    text_parts = []
                    for inline in block.inlines:
                        if isinstance(inline, Text):
                            text_parts.append(inline.text)
                        elif isinstance(inline, MathInline):
                            text_parts.append(inline.latex)
                        elif isinstance(inline, Symbol):
                            text_parts.append(inline.name)
                    raw_text = " ".join(text_parts)
                    norm_text = normalize_text(raw_text)
                    toks = norm_text.split()
                    if not toks:
                        cur_y += self.line_h
                        continue

                    # Gói từ thành các dòng
                    cur_line, curw = [], 0.0
                    for tok in toks:
                        st, w, miss = self.wr.token(tok)
                        ntok += 1
                        if miss:
                            nmiss += 1
                            for m in miss:
                                self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                        w *= self.S
                        sp = self.rnd.choice(self.gaps) * self.S * self.opts.space * (1 + self.rnd.gauss(0, 0.06 * self.J))
                        if cur_line and curw + sp + w > self.width:
                            # Đẩy dòng vào trang
                            if cur_y + self.line_h > max_page_y:
                                new_page()
                            line_strokes = self._render_text_line(cur_line, cur_y + self.line_h, self.x0)
                            cur_page.extend(line_strokes)
                            total_strokes += len(line_strokes)
                            total_lines += 1
                            cur_y += self.line_h
                            cur_line, curw = [], 0.0

                        start = curw + (sp if cur_line else 0.0)
                        cur_line.append((start, st, w))
                        curw = start + w

                    if cur_line:
                        if cur_y + self.line_h > max_page_y:
                            new_page()
                        line_strokes = self._render_text_line(cur_line, cur_y + self.line_h, self.x0)
                        cur_page.extend(line_strokes)
                        total_strokes += len(line_strokes)
                        total_lines += 1
                        cur_y += self.line_h

                elif isinstance(block, Table):
                    table_engine = TableLayoutEngine(self.width, self.line_h)
                    layout_data = table_engine.layout_table(block, x0=self.x0, y0=cur_y)
                    if layout_data.height > 0:
                        # Kiểm tra xem có đủ chỗ trên trang không
                        if cur_y + layout_data.height > max_page_y and cur_y > 30.0:
                            new_page()
                            layout_data = table_engine.layout_table(block, x0=self.x0, y0=cur_y)

                        # 1. Sinh nét viền bảng
                        border_strokes = table_engine.generate_border_strokes(layout_data, block.border_style)
                        for bs in border_strokes:
                            cur_page.append(xopp.stroke_xml(bs.points, self.bank.pen, self.opts.color, self.opts.wscale))
                            total_strokes += 1

                        # 2. Sinh nét chữ bên trong các ô
                        for row_cells in layout_data.cells:
                            for cell in row_cells:
                                cell_cur_y = cell.y + table_engine.cell_padding
                                for t_line in cell.text_lines:
                                    norm_t = normalize_text(t_line)
                                    toks = norm_t.split()
                                    cell_line_items = []
                                    c_w = 0.0
                                    for tok in toks:
                                        st, w, miss = self.wr.token(tok)
                                        ntok += 1
                                        if miss:
                                            nmiss += 1
                                            for m in miss:
                                                self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                                        w *= self.S
                                        sp = 6.0 * self.S * self.opts.space
                                        start = c_w + (sp if cell_line_items else 0.0)
                                        cell_line_items.append((start, st, w))
                                        c_w = start + w

                                    cell_strokes = self._render_text_line(cell_line_items, cell_cur_y + self.line_h * 0.8, cell.x + table_engine.cell_padding)
                                    cur_page.extend(cell_strokes)
                                    total_strokes += len(cell_strokes)
                                    cell_cur_y += self.line_h

                elif isinstance(block, MathBlock):
                    math_ast = parse_latex_math(block.latex)
                    math_engine = MathLayoutEngine(self.bank, S=self.S)
                    item = math_engine.measure(math_ast)
                    for sym, count in math_engine.missing_symbols.items():
                        self.wr.missing[sym] = self.wr.missing.get(sym, 0) + count
                        nmiss += count
                    ntok += 1

                    if cur_y + item.size.height > max_page_y and cur_y > 30.0:
                        new_page()

                    math_x = self.x0 + max(0.0, (self.width - item.size.width) / 2.0)
                    baseline_y = cur_y + item.size.ascent

                    # 1. Stroke vector (gạch phân số, căn thức)
                    for ps in item.strokes:
                        pts = [(math_x + pt[0], baseline_y + pt[1]) for pt in ps.points]
                        cur_page.append(xopp.stroke_xml(pts, self.bank.pen, self.opts.color, self.opts.wscale))
                        total_strokes += 1

                    # 2. Glyphs (ký hiệu có mẫu nét viết tay)
                    for g in item.glyphs:
                        for st in g.strokes:
                            fin = []
                            for idx in range(0, len(st), 2):
                                px = st[idx] * g.scale + math_x + g.x
                                py = st[idx + 1] * g.scale + baseline_y + g.y
                                fin.append((px, py))
                            cur_page.append(xopp.stroke_xml(fin, self.bank.pen, self.opts.color, self.opts.wscale))
                            total_strokes += 1

                    cur_y += item.size.height + self.line_h * 0.5
                    total_lines += 1

        if cur_page or not pages_xml:
            pages_xml.append(cur_page)

        # Xuất file XML XOPP
        o = [xopp.HEAD]
        for pg in pages_xml:
            page_h = max(200.0, cur_y + 40.0) if len(pages_xml) == 1 else MAXH
            o.append(xopp.PAGE_OPEN % (fmt(self.x0 + self.width + 20), fmt(page_h)))
            o.extend(pg)
            o.append(xopp.PAGE_CLOSE)
        o.append("</xournal>")

        xopp.save_xopp(out_path, o)

        result = WriteResult(
            out_path=out_path,
            n_lines=total_lines,
            n_strokes=total_strokes,
            n_tokens=ntok,
            n_missing_tokens=nmiss,
            missing=dict(self.wr.missing),
        )

        if result.missing:
            grid_path = os.path.splitext(out_path)[0] + "_thieu.xopp"
            items = result.missing_sorted()
            xopp.make_grid(
                grid_path, [k for k, _ in items], self.bank,
                "Từ CHƯA có mẫu: viết mỗi từ vào ô, giữa hai đường kẻ, rồi Ctrl+S và chạy: python hw_note.py learn %s"
                % os.path.basename(grid_path)
            )
            result.missing_grid_path = grid_path

        return result
