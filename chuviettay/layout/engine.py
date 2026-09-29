"""Động cơ bố cục tài liệu (Document Layout Engine) và chuyển đổi sang nét vẽ Xournal++."""
from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

from chuviettay.config import MAXH
from chuviettay.controller.results import WriteOptions, WriteResult
from chuviettay.document.ir import (
    Document,
    Heading,
    Inline,
    LineBreak,
    ListBlock,
    MathBlock,
    MathInline,
    PageBreak,
    Paragraph,
    Symbol,
    Table,
    Text,
)
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.layout.stream import PageBuffer
from chuviettay.layout.table_layout import LaidOutCell, TableLayoutData, TableLayoutEngine
from chuviettay.math.parser import parse_latex_math
from chuviettay.model import xopp
from chuviettay.model.text_utils import Stroke, normalize_text, place
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
        scale_mult: float = 1.0,
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
            s = self.S * scale_mult * (1 + self.rnd.gauss(0, 0.02 * self.J))
            rot = self.rnd.gauss(0, 0.010 * self.J)
            dy = self.rnd.gauss(0, 0.35 * self.J)
            for pts in place(st, 0.0, 0.0, s, rot):
                fin = []
                for x, y in pts:
                    X = start + x
                    fin.append((xo + X, base_y + dy + y + slope * X + amp * math.sin(6.283 * X / wl + ph)))
                out.append(xopp.stroke_xml(fin, self.bank.pen, self.opts.color, self.opts.wscale * (1 + self.rnd.gauss(0, 0.02 * self.J))))

        return out

    def _layout_inlines(
        self,
        inlines: list[Inline],
        scale_mult: float = 1.0,
        missing_symbols: dict[str, int] | None = None,
    ) -> tuple[list[tuple[list[Stroke], float, list[str]]], int, int]:
        """Chuyển đổi danh sách Inline (Text, MathInline, Symbol, LineBreak) thành các mục (strokes, width, miss).
        Trả về: (items, n_tokens, n_missing_tokens)."""
        items: list[tuple[list[Stroke], float, list[str]]] = []
        ntok = 0
        nmiss = 0

        for inline in inlines:
            if isinstance(inline, Text):
                norm = normalize_text(inline.text or "")
                for tok in norm.split():
                    st, w, miss = self.wr.token(tok)
                    ntok += 1
                    if miss:
                        nmiss += len(miss)
                        for m in miss:
                            self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                    items.append((st, w * self.S * scale_mult, miss))

            elif isinstance(inline, Symbol):
                sym = inline.symbol
                st, w, miss = self.wr.symbol(sym)
                ntok += 1
                if miss:
                    nmiss += len(miss)
                    for m in miss:
                        if missing_symbols is not None:
                            missing_symbols[m] = missing_symbols.get(m, 0) + 1
                        self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                items.append((st, w * self.S * scale_mult, miss))

            elif isinstance(inline, MathInline):
                math_ast = inline.ast or parse_latex_math(inline.latex)
                math_engine = MathLayoutEngine(self.bank, S=1.0, writer=self.wr, rnd=self.rnd)
                m_item = math_engine.measure(math_ast)
                for sym, count in math_engine.missing_symbols.items():
                    if missing_symbols is not None:
                        missing_symbols[sym] = missing_symbols.get(sym, 0) + count
                    self.wr.missing[sym] = self.wr.missing.get(sym, 0) + count
                    nmiss += count
                ntok += 1

                # Chuyển đổi MathLayoutItem thành các nét viết tay tương đối trong toạ độ bank (S=1.0)
                math_strokes: list[Stroke] = []
                for g in m_item.glyphs:
                    for gst in g.strokes:
                        fin_s = []
                        for idx in range(0, len(gst), 2):
                            fin_s.append(round(gst[idx] * g.scale + g.x, 2))
                            fin_s.append(round(gst[idx + 1] * g.scale + g.y, 2))
                        math_strokes.append(fin_s)
                for ps in m_item.strokes:
                    flat_pts = []
                    for pt in ps.points:
                        flat_pts.append(round(pt[0], 2))
                        flat_pts.append(round(pt[1], 2))
                    math_strokes.append(flat_pts)

                items.append((math_strokes, m_item.size.width * self.S * scale_mult, list(math_engine.missing_symbols.keys())))

            elif isinstance(inline, LineBreak):
                items.append(([], 0.0, ["__LINE_BREAK__"]))

        return items, ntok, nmiss

    def render(self, document: Document, out_path: str) -> WriteResult:
        """Thực hiện bố cục toàn bộ Document IR và ghi file .xopp."""
        cur_page: list[str] = []
        cur_y = 20.0
        max_page_y = MAXH - 40.0
        total_lines = 0
        total_strokes = 0
        ntok = nmiss = 0
        total_tables = 0
        total_math_blocks = 0
        missing_symbols: dict[str, int] = {}
        page_w = self.x0 + self.width + 20

        pb = PageBuffer(out_path, page_w, default_page_h=MAXH)

        def new_page():
            nonlocal cur_page, cur_y
            pb.append_page(cur_page, page_h=MAXH)
            cur_page = []
            cur_y = 20.0

        def render_paragraph_inlines(inlines: list[Inline], scale_mult: float = 1.0, prefix: str = ""):
            nonlocal cur_y, total_lines, total_strokes, ntok, nmiss
            if prefix:
                inlines = [Text(text=prefix)] + list(inlines)

            items, n_t, n_m = self._layout_inlines(inlines, scale_mult=scale_mult, missing_symbols=missing_symbols)
            ntok += n_t
            nmiss += n_m

            eff_line_h = self.line_h * scale_mult
            cur_line: list[tuple[float, list[Stroke], float]] = []
            curw = 0.0

            def flush_line():
                nonlocal cur_y, total_lines, total_strokes, cur_line, curw
                if not cur_line:
                    return
                if cur_y + eff_line_h > max_page_y:
                    new_page()
                line_strokes = self._render_text_line(cur_line, cur_y + eff_line_h, self.x0, scale_mult=scale_mult)
                cur_page.extend(line_strokes)
                total_strokes += len(line_strokes)
                total_lines += 1
                cur_y += eff_line_h
                cur_line = []
                curw = 0.0

            for st, w, miss in items:
                if miss == ["__LINE_BREAK__"]:
                    flush_line()
                    continue

                sp = self.rnd.choice(self.gaps) * self.S * scale_mult * self.opts.space * (1 + self.rnd.gauss(0, 0.06 * self.J))
                if cur_line and curw + sp + w > self.width:
                    flush_line()

                start = curw + (sp if cur_line else 0.0)
                cur_line.append((start, st, w))
                curw = start + w

            flush_line()

        try:
            for block in document.blocks:
                if isinstance(block, PageBreak):
                    new_page()
                    continue

                elif isinstance(block, Heading):
                    head_scale = 1.35 if block.level == 1 else (1.2 if block.level == 2 else 1.1)
                    cur_y += self.line_h * 0.4
                    render_paragraph_inlines(block.inlines, scale_mult=head_scale)
                    cur_y += self.line_h * 0.3

                elif isinstance(block, Paragraph):
                    if not block.inlines:
                        cur_y += self.line_h * 0.8
                        if cur_y > max_page_y:
                            new_page()
                    else:
                        render_paragraph_inlines(block.inlines, scale_mult=1.0)
                        cur_y += self.line_h * 0.2

                elif isinstance(block, ListBlock):
                    for idx, item_blocks in enumerate(block.items):
                        pfx = f"{block.start + idx}. " if block.ordered else "- "
                        first_sub = True
                        for sub in item_blocks:
                            if isinstance(sub, Paragraph):
                                pref = pfx if first_sub else "  "
                                first_sub = False
                                render_paragraph_inlines(sub.inlines, scale_mult=1.0, prefix=pref)
                                cur_y += self.line_h * 0.1

                elif isinstance(block, Table):
                    table_engine = TableLayoutEngine(self.width, self.line_h)

                    def cell_inlines_formatter(cell: TableCell, usable_w: float) -> list[list[tuple[float, list[Stroke], float]]]:
                        nonlocal ntok, nmiss
                        cell_inlines: list[Inline] = []
                        for blk_idx, b in enumerate(cell.blocks):
                            if isinstance(b, Paragraph):
                                if blk_idx > 0:
                                    cell_inlines.append(LineBreak())
                                cell_inlines.extend(b.inlines)
                            elif isinstance(b, MathBlock):
                                if blk_idx > 0:
                                    cell_inlines.append(LineBreak())
                                cell_inlines.append(MathInline(latex=b.latex, ast=b.ast))

                        if cell_inlines:
                            items, n_t, n_m = self._layout_inlines(cell_inlines, scale_mult=1.0, missing_symbols=missing_symbols)
                            ntok += n_t
                            nmiss += n_m
                        else:
                            items = []

                        cell_lines: list[list[tuple[float, list[Stroke], float]]] = []
                        cur_l: list[tuple[float, list[Stroke], float]] = []
                        cur_lw = 0.0
                        for st, w, miss in items:
                            if miss == ["__LINE_BREAK__"]:
                                if cur_l:
                                    cell_lines.append(cur_l)
                                    cur_l = []
                                    cur_lw = 0.0
                                continue
                            sp = 6.0 * self.S * self.opts.space
                            if cur_l and cur_lw + sp + w > usable_w:
                                cell_lines.append(cur_l)
                                cur_l = [(0.0, st, w)]
                                cur_lw = w
                            else:
                                start_rel = cur_lw + (sp if cur_l else 0.0)
                                cur_l.append((start_rel, st, w))
                                cur_lw = start_rel + w
                        if cur_l:
                            cell_lines.append(cur_l)
                        return cell_lines

                    full_table_data = table_engine.layout_table(
                        block,
                        x0=self.x0,
                        y0=cur_y,
                        cell_inlines_formatter=cell_inlines_formatter,
                    )
                    if full_table_data.width <= 0 or not full_table_data.cells:
                        continue

                    curr_row_idx = 0
                    num_rows = len(full_table_data.row_heights)

                    while curr_row_idx < num_rows:
                        avail_h = max_page_y - cur_y
                        if avail_h < self.line_h + 2 * table_engine.cell_padding and cur_y > 30.0:
                            new_page()
                            avail_h = max_page_y - cur_y

                        slice_data, next_row = full_table_data.slice_page(
                            curr_row_idx,
                            max_height=avail_h,
                            new_y=cur_y,
                        )
                        if not slice_data.cells or next_row == curr_row_idx:
                            new_page()
                            avail_h = max_page_y - cur_y
                            slice_data, next_row = full_table_data.slice_page(
                                curr_row_idx,
                                max_height=avail_h,
                                new_y=cur_y,
                            )
                            if not slice_data.cells or next_row == curr_row_idx:
                                break

                        # 1. Sinh nét viền bảng cho trang hiện tại
                        border_strokes = table_engine.generate_border_strokes(slice_data, block.border_style)
                        for bs in border_strokes:
                            cur_page.append(xopp.stroke_xml(bs.points, self.bank.pen, self.opts.color, self.opts.wscale))
                            total_strokes += 1

                        # 2. Sinh nét chữ bên trong các ô
                        for row_cells in slice_data.cells:
                            for laid_cell in row_cells:
                                align = "left"
                                if block.col_alignments and laid_cell.col < len(block.col_alignments):
                                    align = block.col_alignments[laid_cell.col].lower()

                                usable_w = max(10.0, laid_cell.width - 2 * table_engine.cell_padding)
                                cell_cur_y = laid_cell.y + table_engine.cell_padding

                                if laid_cell.rendered_lines:
                                    for l_items in laid_cell.rendered_lines:
                                        if not l_items:
                                            cell_cur_y += self.line_h
                                            continue
                                        line_w = l_items[-1][0] + l_items[-1][2]
                                        if align == "center":
                                            extra_x = max(0.0, (usable_w - line_w) / 2.0)
                                        elif align == "right":
                                            extra_x = max(0.0, usable_w - line_w)
                                        else:
                                            extra_x = 0.0

                                        start_x = laid_cell.x + table_engine.cell_padding + extra_x
                                        cell_strokes = self._render_text_line(
                                            l_items,
                                            cell_cur_y + self.line_h * 0.8,
                                            start_x,
                                        )
                                        cur_page.extend(cell_strokes)
                                        total_strokes += len(cell_strokes)
                                        total_lines += 1
                                        cell_cur_y += self.line_h

                        cur_y += slice_data.height
                        curr_row_idx = next_row

                        if curr_row_idx < num_rows:
                            new_page()

                    cur_y += self.line_h * 0.4
                    total_tables += 1

                elif isinstance(block, MathBlock):
                    math_ast = block.ast or parse_latex_math(block.latex)
                    math_engine = MathLayoutEngine(self.bank, S=self.S, writer=self.wr, rnd=self.rnd)
                    item = math_engine.measure(math_ast)
                    for sym, count in math_engine.missing_symbols.items():
                        missing_symbols[sym] = missing_symbols.get(sym, 0) + count
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
                    total_math_blocks += 1

            if pb.n_pages == 0:
                final_page_h = max(200.0, cur_y + 40.0)
                pb.append_page(cur_page, page_h=final_page_h)
            else:
                if cur_page:
                    pb.append_page(cur_page, page_h=MAXH)
            cur_page = []
            pb.close()
        except Exception:
            if not pb._f.closed:
                pb._f.close()
            if os.path.exists(pb._temp_path):
                try:
                    os.remove(pb._temp_path)
                except OSError:
                    pass
            raise

        all_missing = dict(self.wr.missing)
        for sym, count in missing_symbols.items():
            all_missing[sym] = all_missing.get(sym, 0) + count

        result = WriteResult(
            out_path=out_path,
            n_lines=total_lines,
            n_strokes=total_strokes,
            n_tokens=ntok,
            n_missing_tokens=nmiss,
            missing=all_missing,
            missing_symbols=dict(missing_symbols),
            n_tables=total_tables,
            n_math_blocks=total_math_blocks,
        )

        if all_missing:
            grid_path = os.path.splitext(out_path)[0] + "_thieu.xopp"
            items = sorted(all_missing.items(), key=lambda kv: (-kv[1], kv[0]))
            xopp.make_grid(
                grid_path,
                [k for k, _ in items],
                self.bank,
                "Từ/ký hiệu CHƯA có mẫu: viết mỗi từ/ký hiệu vào ô, giữa hai đường kẻ, rồi Ctrl+S và chạy: python hw_note.py learn %s"
                % os.path.basename(grid_path),
            )
            result.missing_grid_path = grid_path

        return result

