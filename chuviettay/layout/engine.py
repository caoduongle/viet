"""Động cơ bố cục tài liệu (Document Layout Engine) và chuyển đổi sang nét vẽ Xournal++."""
from __future__ import annotations

import math
import os
import random
from collections.abc import Callable
from dataclasses import dataclass, field
import gzip
import tempfile
from typing import TYPE_CHECKING, Any

from chuviettay.model.composer import WriteOptions, WriteResult
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
    TableCell,
    Text,
)
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.layout.stream import PageBuffer
from chuviettay.layout.table_layout import LineVerticalMetrics, TableLayoutEngine
from chuviettay.math.parser import parse_latex_math
from chuviettay.model import xopp
from chuviettay.model.text_utils import Stroke, normalize_text, place
from chuviettay.model.writer import Writer

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank


@dataclass
class TokenBox:
    """Bounding box và metadata của một token trên trang (dùng cho D2)."""
    page: int
    token: str
    x: float
    y: float
    width: float
    height: float
    missing: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RenderItem:
    """Mục hiển thị trong dòng chữ với đầy đủ định danh token và nét vẽ."""
    start: float                          # Vị trí X tương đối trong dòng
    strokes: list[Stroke]                 # Danh sách các nét chữ
    width: float                          # Chiều rộng mục
    missing: list[str] = field(default_factory=list)  # Ký tự thiếu mẫu
    token: str = ""                       # Chuỗi token gốc
    token_id: str = ""                    # Định danh token trong phiên
    occurrence: int = 0                   # Thứ tự xuất hiện trong phạm vi khối/tài liệu

    def __iter__(self) -> Any:
        """Hỗ trợ giải nén tuple (unpacking: start, st, w = item[:3] hoặc a, b, c, d, e = item)."""
        yield self.start
        yield self.strokes
        yield self.width
        yield self.missing
        yield self.token
        yield self.token_id
        yield self.occurrence

    def __getitem__(self, idx: int | slice) -> Any:
        """Hỗ trợ truy cập chỉ số kiểu tuple và cắt lát (slice) để tương thích ngược 100% với mã nguồn cũ."""
        if isinstance(idx, slice) or idx < 0:
            return tuple(self)[idx]
        if idx == 0:
            return self.start
        if idx == 1:
            return self.strokes
        if idx == 2:
            return self.width
        if idx == 3:
            return self.missing
        if idx == 4:
            return self.token
        if idx == 5:
            return self.token_id
        if idx == 6:
            return self.occurrence
        raise IndexError(f"Chỉ số RenderItem không hợp lệ: {idx}")

    def __len__(self) -> int:
        return 7


def resolve_effective_line_height(
    requested_line: float | None,
    bank: Any,
    scale: float,
) -> float:
    """Xác định chiều cao dòng an toàn bảo đảm chống đè chữ vật lý (Anti-Collision Floor).
    Theo hợp đồng CTR-034-LINE-HEIGHT-POLICY."""
    font_xh = float(getattr(bank, "xh", 7.94) or 7.94)
    default_bank_line = float(bank.d.get("line", 24.0)) * scale
    safe_line_floor = max(1.4 * font_xh * scale, 0.65 * default_bank_line)

    if requested_line is None:
        return default_bank_line
    if 0.0 < requested_line < safe_line_floor:
        # Nhập khoảng cách nhỏ (ví dụ 1pt) -> coi là khoảng hở cộng thêm (inter-line gap)
        return safe_line_floor + requested_line
    return max(safe_line_floor, requested_line)


def _partition_long_token_linear(
    tok_str: str,
    usable_w: float,
    char_width_measurer: Callable[[str], float],
    scale: float = 1.0,
    min_chars: int = 1,
    letter_gap: float = 0.0,
) -> list[str]:
    """Phân chia một token dài thành các phân đoạn vừa với usable_w trong O(N) thời gian
    sử dụng phép đo thuần túy, tuyệt đối không làm đột biến trạng thái Writer."""
    if not tok_str:
        return []
    chunks: list[str] = []
    curr_chunk: list[str] = []
    curr_w = 0.0
    scaled_gap = letter_gap * scale

    for ch in tok_str:
        cw = char_width_measurer(ch) * scale
        added_w = cw + (scaled_gap if curr_chunk else 0.0)
        if curr_chunk and (curr_w + added_w > usable_w) and len(curr_chunk) >= min_chars:
            chunks.append("".join(curr_chunk))
            curr_chunk = [ch]
            curr_w = cw
        else:
            curr_chunk.append(ch)
            curr_w += added_w

    if curr_chunk:
        chunks.append("".join(curr_chunk))
    return chunks


class DocumentLayoutEngine:
    """Điều phối bố cục các khối (Paragraph, Heading, Table, PageBreak...) và sinh nét vẽ."""

    def __init__(
        self,
        bank: Bank,
        opts: WriteOptions,
        token_layout_callback: Callable[[TokenBox], None] | None = None,
    ):
        self.bank = bank
        self.opts = opts
        self.opts.validate()
        self.token_layout_callback = token_layout_callback
        self.page_format = opts.resolve_page_format()
        from chuviettay.model.rng import resolve_effective_seed

        self.effective_seed = resolve_effective_seed(opts.seed, getattr(opts, "stable_variants", False))
        self.rnd = random.Random(self.effective_seed)
        self.J = opts.jitter
        self.S = opts.scale
        self.effective_wscale = opts.wscale
        if getattr(opts, "auto_xh", False):
            current_xh = getattr(bank, "xh", 7.94) or 7.94
            target_xh = getattr(opts, "target_xh", 7.94)
            if current_xh > 0 and abs(current_xh - target_xh) > 0.05:
                self.S = opts.scale * (target_xh / current_xh)
            base_pen = float(bank.pen.get("width", 1.41)) if bank.pen else 1.41
            desired_pen = 0.178 * target_xh * (self.S / (target_xh / current_xh if current_xh > 0 else 1.0))
            self.effective_wscale = opts.wscale * (desired_pen / base_pen if base_pen > 0 else 1.0)

        self.line_h = resolve_effective_line_height(opts.line, bank, self.S)
        self.x0 = self.page_format.margin_left
        if self.page_format.background.style == "lined":
            m1 = self.page_format.background.margin if self.page_format.background.margin is not None else 72.0
            if m1 > 0:
                self.x0 = max(self.x0, m1 + 8.0)
                right_limit = self.page_format.width - self.page_format.margin_right
                avail = max(20.0, right_limit - self.x0)
                self.width = min(opts.width, avail) if opts.width is not None else avail
            elif m1 < 0:
                right_limit = min(self.page_format.width - self.page_format.margin_right, self.page_format.width + m1 - 8.0)
                avail = max(20.0, right_limit - self.x0)
                self.width = min(opts.width, avail) if opts.width is not None else avail
            else:
                self.width = min(opts.width, self.page_format.usable_width) if opts.width is not None else self.page_format.usable_width
        else:
            if opts.width is not None:
                self.width = min(opts.width, self.page_format.usable_width)
            else:
                self.width = self.page_format.usable_width
        self.gaps = [g for g in bank.d["wgaps"] if 6.0 <= g <= 20.0] or [11.0]

        self.wr = Writer(
            bank,
            self.rnd,
            self.J,
            not opts.strict_case,
            opts.space,
            assemble_letters=opts.assemble_letters,
            letter_gap=getattr(opts, "letter_gap", 1.0),
            pen_clearance_factor=getattr(opts, "pen_clearance_factor", 0.8),
            stable_variants=getattr(opts, "stable_variants", False),
            seed=self.effective_seed,
        )
        # id(danh sách nét của mục công thức inline) -> (ascent, descent) theo toạ độ kho (S=1): để nới chiều cao dòng
        self._math_extent: dict[int, tuple[float, float]] = {}
        # Quản lý bộ đếm lần xuất hiện cho ScopedRNG để chống va chạm và tạo nét tự nhiên
        self._doc_token_counts: dict[tuple[str, str], int] = {}
        self._math_inline_counts: dict[str, int] = {}
        self._math_block_counts: dict[str, int] = {}


    def _render_text_line(
        self,
        line_items: list[Any],
        base_y: float,
        start_x: float,
        scale_mult: float = 1.0,
        max_y: float | None = None,
    ) -> list[str]:
        """Tạo danh sách các thẻ <stroke> XML cho một dòng chữ với hiệu ứng run tay ngẫu nhiên."""
        out = []
        if not line_items:
            return out

        if self.opts.stable_variants:
            from chuviettay.model.rng import ScopedRNG
            slope, amp = 0.0, 0.0
            wl, ph = 200.0, 0.0
            xo = start_x
        else:
            slope, amp = self.rnd.gauss(0, 0.0015 * self.J), 0.45 * self.J
            wl, ph = self.rnd.uniform(140, 260), self.rnd.uniform(0, 6.283)
            xo = start_x + self.rnd.gauss(0, 1.2 * self.J)

        for it_idx, item in enumerate(line_items):
            start, st = item[0], item[1]
            if not st:
                continue
            if self.opts.stable_variants:
                tok_id = ""
                if hasattr(item, "token_id") and item.token_id:
                    tok_id = item.token_id
                elif len(item) > 5 and item[5]:
                    tok_id = item[5]
                else:
                    tok_str = item[4] if len(item) > 4 else ""
                    occ = item[6] if len(item) > 6 else 0
                    tok_id = f"tok:{tok_str}#{occ}"
                geom_rng = ScopedRNG(self.effective_seed, "geom", tok_id)
                s = self.S * scale_mult * (1 + geom_rng.gauss(0, 0.02 * self.J))
                rot = geom_rng.gauss(0, 0.010 * self.J)
                dy = geom_rng.gauss(0, 0.35 * self.J)
                wscale_mult = 1 + geom_rng.gauss(0, 0.02 * self.J)
                for pts in place(st, 0.0, 0.0, s, rot):
                    raw_pts = []
                    for x, y in pts:
                        X = start + x
                        pt_y = base_y + dy + y + slope * X + amp * math.sin(6.283 * X / wl + ph)
                        raw_pts.append((xo + X, pt_y))
                    if max_y is not None and raw_pts:
                        stroke_max_y = max(p[1] for p in raw_pts)
                        if stroke_max_y > max_y:
                            overshoot = stroke_max_y - max_y
                            raw_pts = [(p[0], p[1] - overshoot) for p in raw_pts]
                    out.append(xopp.stroke_xml(raw_pts, self.bank.pen, self.opts.color, self.effective_wscale * wscale_mult))
            else:
                s = self.S * scale_mult * (1 + self.rnd.gauss(0, 0.02 * self.J))
                rot = self.rnd.gauss(0, 0.010 * self.J)
                dy = self.rnd.gauss(0, 0.35 * self.J)
                for pts in place(st, 0.0, 0.0, s, rot):
                    raw_pts = []
                    for x, y in pts:
                        X = start + x
                        pt_y = base_y + dy + y + slope * X + amp * math.sin(6.283 * X / wl + ph)
                        raw_pts.append((xo + X, pt_y))
                    if max_y is not None and raw_pts:
                        stroke_max_y = max(p[1] for p in raw_pts)
                        if stroke_max_y > max_y:
                            overshoot = stroke_max_y - max_y
                            raw_pts = [(p[0], p[1] - overshoot) for p in raw_pts]
                    out.append(xopp.stroke_xml(raw_pts, self.bank.pen, self.opts.color, self.effective_wscale * (1 + self.rnd.gauss(0, 0.02 * self.J))))

        return out

    def _layout_inlines(
        self,
        inlines: list[Inline],
        scale_mult: float = 1.0,
        missing_symbols: dict[str, int] | None = None,
        max_item_width: float | None = None,
        context_prefix: str = "text",
    ) -> tuple[list[RenderItem], int, int]:
        """Chuyển đổi danh sách Inline (Text, MathInline, Symbol, LineBreak) thành các mục (strokes, width, miss).
        Trả về: (items, n_tokens, n_missing_tokens)."""
        items: list[RenderItem] = []
        ntok = 0
        nmiss = 0

        # Gộp các Text inline liền kề để tránh chèn khoảng trắng giả tạo trước dấu câu (L6)
        merged_inlines: list[Inline] = []
        for inl in inlines:
            if isinstance(inl, Text) and merged_inlines and isinstance(merged_inlines[-1], Text):
                t1_occ = getattr(merged_inlines[-1], "token_occurrences", None)
                t2_occ = getattr(inl, "token_occurrences", None)
                if t1_occ is None and t2_occ is None:
                    merged_inlines[-1].text += (inl.text or "")
                elif t1_occ is not None and t2_occ is not None:
                    merged_inlines[-1].text += (inl.text or "")
                    merged_inlines[-1].token_occurrences = list(t1_occ) + list(t2_occ)
                else:
                    merged_inlines.append(inl)
            else:
                merged_inlines.append(inl)

        xh = getattr(self.bank, "xh", 7.94)
        lg = max(getattr(self.opts, "letter_gap", 1.0) * xh * 0.1, 0.22 * xh)

        for inline in merged_inlines:
            if isinstance(inline, Text):
                norm = normalize_text(inline.text or "")
                inline_tok_idx = 0
                for tok in norm.split():
                    est_w = self.wr.measure_text_width(tok) * self.S * scale_mult
                    if max_item_width is not None and max_item_width > 0 and est_w > max_item_width:
                        chunks = _partition_long_token_linear(
                            tok,
                            max_item_width,
                            self.wr.get_char_advance_width,
                            scale=self.S * scale_mult,
                            min_chars=1,
                            letter_gap=lg,
                        )
                    else:
                        chunks = [tok]

                    if getattr(inline, "token_occurrences", None) is not None and inline_tok_idx < len(inline.token_occurrences):
                        tok_occ = inline.token_occurrences[inline_tok_idx]
                    else:
                        tok_occ = self._doc_token_counts.get((context_prefix, tok), 0)
                        self._doc_token_counts[(context_prefix, tok)] = tok_occ + 1
                    inline_tok_idx += 1

                    for chunk_idx, chunk in enumerate(chunks):
                        from chuviettay.model.rng import SeedContext
                        ctx = SeedContext(
                            content_type=context_prefix,
                            element_id=chunk,
                            occurrence=tok_occ,
                            sub_index=chunk_idx,
                        )
                        try:
                            st, w, miss = self.wr.token(chunk, context=ctx)
                        except TypeError:
                            st, w, miss = self.wr.token(chunk)
                        ntok += 1
                        if miss:
                            nmiss += 1
                            for m in miss:
                                self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                        items.append(
                            RenderItem(
                                start=0.0,
                                strokes=st,
                                width=w * self.S * scale_mult,
                                missing=miss,
                                token=chunk,
                                token_id=f"{ctx.token_id}:{chunk_idx}" if len(chunks) > 1 else ctx.token_id,
                                occurrence=tok_occ,
                            )
                        )

            elif isinstance(inline, Symbol):
                sym = inline.symbol
                sym_prefix = "sym"
                if getattr(inline, "occurrence", None) is not None:
                    occ = inline.occurrence
                else:
                    occ = self._doc_token_counts.get((sym_prefix, sym), 0)
                    self._doc_token_counts[(sym_prefix, sym)] = occ + 1
                from chuviettay.model.rng import SeedContext
                ctx = SeedContext(content_type=sym_prefix, element_id=sym, occurrence=occ)
                try:
                    st, w, miss = self.wr.symbol(sym, context=ctx)
                except TypeError:
                    st, w, miss = self.wr.symbol(sym)
                ntok += 1
                if miss:
                    nmiss += 1
                    for m in miss:
                        if missing_symbols is not None:
                            missing_symbols[m] = missing_symbols.get(m, 0) + 1
                        else:
                            self.wr.missing[m] = self.wr.missing.get(m, 0) + 1
                items.append(
                    RenderItem(
                        start=0.0,
                        strokes=st,
                        width=w * self.S * scale_mult,
                        missing=miss,
                        token=sym,
                        token_id=ctx.token_id,
                        occurrence=occ,
                    )
                )

            elif isinstance(inline, MathInline):
                math_ast = inline.ast or parse_latex_math(inline.latex)
                math_id = getattr(inline, "stable_id", None) or inline.latex
                if getattr(inline, "occurrence", None) is not None:
                    math_occ = inline.occurrence
                else:
                    math_occ = self._math_inline_counts.get(math_id, 0)
                    self._math_inline_counts[math_id] = math_occ + 1
                if self.opts.stable_variants:
                    from chuviettay.model.rng import ScopedRNG
                    math_seed = ScopedRNG(self.effective_seed, "math", math_id, math_occ).seed
                    math_rnd = random.Random(math_seed)
                    math_wr = Writer(
                        self.bank,
                        math_rnd,
                        self.wr.J,
                        self.wr.loose,
                        self.wr.space,
                        stable_variants=True,
                        seed=math_seed,
                        assemble_letters=self.wr.assemble_letters,
                        letter_gap=self.wr.letter_gap,
                        pen_clearance_factor=self.wr.pen_clearance_factor,
                    )
                else:
                    math_rnd = self.rnd
                    math_wr = self.wr
                math_engine = MathLayoutEngine(self.bank, S=1.0, writer=math_wr, rnd=math_rnd)
                # Công thức rộng hơn dòng/ô: thu nhỏ vừa khít (tối thiểu 50%); nếu vẫn quá rộng thì ngắt dòng
                # sau quan hệ/toán tử (như công thức display) thay vì tràn lề
                avail = (max_item_width if max_item_width is not None else self.width) / max(self.S * scale_mult, 1e-6)
                probe_w = math_engine._scratch().measure(math_ast).size.width
                if avail > 0 and probe_w * 0.5 > avail:
                    pieces = math_engine.layout_lines(math_ast, avail)
                elif avail > 0 and probe_w > avail:
                    pieces = [math_engine.measure(math_ast, scale=max(0.5, avail / probe_w))]
                else:
                    pieces = [math_engine.measure(math_ast)]
                math_miss_count = sum(math_engine.missing_symbols.values())
                for sym, count in math_engine.missing_symbols.items():
                    if missing_symbols is not None:
                        missing_symbols[sym] = missing_symbols.get(sym, 0) + count
                    else:
                        self.wr.missing[sym] = self.wr.missing.get(sym, 0) + count
                    nmiss += count
                ntok += max(1, sum(len(pc.glyphs) for pc in pieces), math_miss_count)

                for k, m_item in enumerate(pieces):
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

                    self._math_extent[id(math_strokes)] = (m_item.size.ascent, m_item.size.descent)
                    items.append(
                        RenderItem(
                            start=0.0,
                            strokes=math_strokes,
                            width=m_item.size.width * self.S * scale_mult,
                            missing=list(math_engine.missing_symbols.keys()),
                            token=inline.latex,
                            token_id=f"math:{inline.latex}#{math_occ}",
                            occurrence=math_occ,
                        )
                    )
                    if k < len(pieces) - 1:
                        items.append(RenderItem(0.0, [], 0.0, ["__LINE_BREAK__"], "", "", 0))

            elif isinstance(inline, LineBreak):
                items.append(RenderItem(0.0, [], 0.0, ["__LINE_BREAK__"], "", "", 0))

        return items, ntok, nmiss

    def render(self, document: Document, out_path: str) -> WriteResult:
        """Thực hiện bố cục toàn bộ Document IR và ghi file .xopp."""
        self._doc_token_counts.clear()
        self._math_inline_counts.clear()
        self._math_block_counts.clear()
        self._math_extent.clear()

        pf = self.page_format
        page_w = pf.width
        page_h = pf.height
        cur_page: list[str] = []
        cur_y = pf.content_top
        max_page_y = min(pf.max_page_y, page_h - 60.0)
        total_lines = 0
        total_strokes = 0
        ntok = nmiss = 0
        total_tables = 0
        table_sig_counts: dict[str, int] = {}
        total_math_blocks = 0
        missing_symbols: dict[str, int] = {}
        layout_warnings: list[str] = []
        bg = pf.background
        snap_ruling = bool(self.opts.snap_to_ruling and bg.style in ("ruled", "lined"))
        r1 = bg.spacing if (bg.spacing is not None and bg.spacing > 0) else 24.0
        max_ruling_y = page_h - 60.0

        pb = PageBuffer(out_path, page_w, default_page_h=page_h, default_background=bg)

        def new_page():
            nonlocal cur_page, cur_y
            pb.append_page(cur_page, page_h=page_h, page_w=page_w, background=bg)
            cur_page = []
            cur_y = pf.content_top

        def render_paragraph_inlines(inlines: list[Inline], scale_mult: float = 1.0, prefix: str = "",
                                     indent: float = 0.0, align: str = "left", context_prefix: str = "text"):
            nonlocal ntok, nmiss
            if prefix:
                inlines = [Text(text=prefix)] + list(inlines)

            avail_w = max(self.width - indent, 1.0)
            items, n_t, n_m = self._layout_inlines(inlines, scale_mult=scale_mult, missing_symbols=missing_symbols,
                                                   max_item_width=avail_w, context_prefix=context_prefix)
            ntok += n_t
            nmiss += n_m

            eff_line_h = self.line_h * scale_mult
            cur_line: list[RenderItem] = []
            curw = 0.0
            line_asc = line_desc = 0.0     # chiều cao lớn nhất của công thức inline trên dòng hiện tại

            def flush_line(is_last_line: bool = False):
                nonlocal cur_y, total_lines, total_strokes, cur_line, curw, line_asc, line_desc
                if not cur_line:
                    return
                # Công thức cao (phân số, căn...) cần thêm chỗ phía trên/dưới đường cơ sở để không chồng sang dòng kế
                extra_top = max(0.0, line_asc - 0.7 * eff_line_h)
                extra_bot = max(0.0, line_desc - 0.3 * eff_line_h)
                line_h_total = eff_line_h + extra_top + extra_bot

                if snap_ruling:
                    pitch = r1 * max(1, round(eff_line_h / r1))
                    candidate_y = cur_y + extra_top + eff_line_h
                    k = max(0, math.ceil((candidate_y - 80.0 - 1e-6) / r1))
                    target_baseline = 80.0 + k * r1
                    if target_baseline > max_ruling_y + 1e-6 and cur_y > pf.content_top:
                        new_page()
                        candidate_y = cur_y + extra_top + eff_line_h
                        k = max(0, math.ceil((candidate_y - 80.0 - 1e-6) / r1))
                        target_baseline = 80.0 + k * r1

                    line_base_y = target_baseline
                    token_box_y = target_baseline - eff_line_h
                else:
                    if cur_y + line_h_total > max_page_y:
                        new_page()
                    line_base_y = cur_y + extra_top + eff_line_h
                    token_box_y = cur_y + extra_top

                line_start_x = self.x0 + indent
                actual_line_w = cur_line[-1][0] + cur_line[-1][2]
                rem_space = max(0.0, avail_w - actual_line_w)

                norm_align = (align or "left").lower()
                final_line = cur_line

                if norm_align == "center":
                    line_start_x += rem_space / 2.0
                elif norm_align == "right":
                    line_start_x += rem_space
                elif norm_align == "justify":
                    if not is_last_line and len(cur_line) > 1 and rem_space > 0:
                        gap_add = rem_space / (len(cur_line) - 1)
                        adjusted_line = []
                        for idx, itm in enumerate(cur_line):
                            new_start = itm[0] + idx * gap_add
                            adjusted_line.append(RenderItem(new_start, itm[1], itm[2], itm[3], itm[4], itm[5], itm[6]))
                        final_line = adjusted_line

                if self.token_layout_callback is not None:
                    page_idx = pb.n_pages
                    for itm in final_line:
                        if itm[4]:
                            box_x = line_start_x + itm[0]
                            box_y = token_box_y
                            self.token_layout_callback(
                                TokenBox(
                                    page=page_idx,
                                    token=itm[4],
                                    x=round(box_x, 2),
                                    y=round(box_y, 2),
                                    width=round(itm[2], 2),
                                    height=round(eff_line_h, 2),
                                    missing=itm[3],
                                )
                            )

                line_strokes = self._render_text_line(
                    final_line, line_base_y, line_start_x,
                    scale_mult=scale_mult,
                )
                cur_page.extend(line_strokes)
                total_strokes += len(line_strokes)
                total_lines += 1

                if snap_ruling:
                    step = max(pitch, r1 * math.ceil((eff_line_h + extra_bot - 1e-6) / r1))
                    cur_y = target_baseline + step - eff_line_h
                else:
                    cur_y += line_h_total

                cur_line = []
                curw = 0.0
                line_asc = line_desc = 0.0

            for item in items:
                if isinstance(item, RenderItem):
                    st = item.strokes
                    w = item.width
                    miss = item.missing
                    tok_str = item.token
                    tok_id = item.token_id
                    occ = item.occurrence
                else:
                    st, w, miss = item[0], item[1], item[2]
                    tok_str = item[3] if len(item) > 3 else ""
                    tok_id = f"{tok_str}#0"
                    occ = 0
                if miss == ["__LINE_BREAK__"]:
                    flush_line(is_last_line=True)
                    continue

                if self.opts.stable_variants:
                    from chuviettay.model.rng import ScopedRNG
                    prev_token_id = cur_line[-1].token_id if cur_line and hasattr(cur_line[-1], "token_id") else (cur_line[-1][5] if cur_line and len(cur_line[-1]) > 5 else "")
                    wgap_rng = ScopedRNG(self.effective_seed, "wgap", prev_token_id, tok_id)
                    sp = wgap_rng.choice(self.gaps) * self.S * scale_mult * self.opts.space * (1 + wgap_rng.gauss(0, 0.06 * self.J))
                else:
                    sp = self.rnd.choice(self.gaps) * self.S * scale_mult * self.opts.space * (1 + self.rnd.gauss(0, 0.06 * self.J))
                if cur_line and curw + sp + w > avail_w:
                    flush_line(is_last_line=False)

                start = curw + (sp if cur_line else 0.0)
                r_item = RenderItem(start, st, w, miss, tok_str, tok_id, occ)
                cur_line.append(r_item)
                curw = start + w
                ext = self._math_extent.get(id(st))
                if ext is not None:
                    line_asc = max(line_asc, ext[0] * self.S * scale_mult)
                    line_desc = max(line_desc, ext[1] * self.S * scale_mult)

            flush_line(is_last_line=True)

        def render_math_block(block: MathBlock, indent: float = 0.0):
            """Công thức display: căn giữa, tự ngắt dòng sau quan hệ/toán tử nếu quá rộng, thu nhỏ nếu cần."""
            nonlocal cur_y, total_lines, total_strokes, ntok, nmiss, total_math_blocks
            math_ast = block.ast or parse_latex_math(block.latex)
            if self.opts.stable_variants:
                from chuviettay.model.rng import ScopedRNG
                math_id = getattr(block, "stable_id", None) or block.latex
                if getattr(block, "occurrence", None) is not None:
                    block_occ = block.occurrence
                else:
                    block_occ = self._math_block_counts.get(math_id, 0)
                    self._math_block_counts[math_id] = block_occ + 1
                math_seed = ScopedRNG(self.effective_seed, "math_block", math_id, block_occ).seed
                math_rnd = random.Random(math_seed)
                math_wr = Writer(
                    self.bank,
                    math_rnd,
                    self.wr.J,
                    self.wr.loose,
                    self.wr.space,
                    stable_variants=True,
                    seed=math_seed,
                    assemble_letters=self.wr.assemble_letters,
                    letter_gap=self.wr.letter_gap,
                    pen_clearance_factor=self.wr.pen_clearance_factor,
                )
            else:
                math_rnd = self.rnd
                math_wr = self.wr
            math_engine = MathLayoutEngine(self.bank, S=self.S, writer=math_wr, rnd=math_rnd, display=True)
            avail_w = max(self.width - indent, 1.0)
            lines = math_engine.layout_lines(math_ast, avail_w)
            math_miss_count = sum(math_engine.missing_symbols.values())
            for sym, count in math_engine.missing_symbols.items():
                missing_symbols[sym] = missing_symbols.get(sym, 0) + count
                nmiss += count
            ntok += max(1, sum(len(it.glyphs) for it in lines), math_miss_count)

            for item in lines:
                if cur_y + item.size.height > max_page_y and cur_y > pf.content_top:
                    new_page()
                math_x = self.x0 + indent + max(0.0, (avail_w - item.size.width) / 2.0)
                baseline_y = cur_y + item.size.ascent

                # 1. Stroke vector (gạch phân số, căn thức, ngoặc co giãn, dấu trang trí)
                for ps in item.strokes:
                    pts = [(math_x + pt[0], baseline_y + pt[1]) for pt in ps.points]
                    cur_page.append(xopp.stroke_xml(pts, self.bank.pen, self.opts.color, self.effective_wscale))
                    total_strokes += 1

                # 2. Glyphs (ký hiệu có mẫu nét viết tay)
                for g in item.glyphs:
                    for st in g.strokes:
                        fin = []
                        for idx in range(0, len(st), 2):
                            px = st[idx] * g.scale + math_x + g.x
                            py = st[idx + 1] * g.scale + baseline_y + g.y
                            fin.append((px, py))
                        cur_page.append(xopp.stroke_xml(fin, self.bank.pen, self.opts.color, self.effective_wscale))
                        total_strokes += 1

                cur_y += item.size.height + (self.line_h * 0.25 if item is not lines[-1] else 0.0)
                total_lines += 1
            cur_y += self.line_h * 0.5
            total_math_blocks += 1

        def render_list(block: ListBlock, depth: int = 0):
            """Danh sách (kể cả lồng nhau): mỗi mục có thể chứa đoạn văn, công thức display và danh sách con."""
            nonlocal cur_y
            indent = depth * 18.0 * self.S
            for idx, item_blocks in enumerate(block.items):
                pfx = f"{block.start + idx}. " if block.ordered else "- "
                first_sub = True
                for sub in item_blocks:
                    if isinstance(sub, Paragraph):
                        pref = pfx if first_sub else "  "
                        first_sub = False
                        render_paragraph_inlines(
                            sub.inlines, scale_mult=1.0, prefix=pref, indent=indent, align=getattr(sub, "align", "left")
                        )
                        if not snap_ruling:
                            cur_y += self.line_h * 0.1
                    elif isinstance(sub, MathBlock):
                        render_math_block(sub, indent=indent)
                    elif isinstance(sub, ListBlock):
                        render_list(sub, depth + 1)

        try:
            for block in document.blocks:
                if isinstance(block, PageBreak):
                    new_page()
                    continue

                elif isinstance(block, Heading):
                    head_scale = 1.35 if block.level == 1 else (1.2 if block.level == 2 else 1.1)
                    if not snap_ruling:
                        cur_y += self.line_h * 0.4
                    render_paragraph_inlines(block.inlines, scale_mult=head_scale, context_prefix="heading")
                    if not snap_ruling:
                        cur_y += self.line_h * 0.3

                elif isinstance(block, Paragraph):
                    if not block.inlines:
                        if snap_ruling:
                            pitch = r1 * max(1, round(self.line_h / r1))
                            cur_y += pitch
                            if cur_y + self.line_h > max_ruling_y and cur_y > pf.content_top:
                                new_page()
                        else:
                            cur_y += self.line_h * 0.8
                            if cur_y > max_page_y:
                                new_page()
                    else:
                        render_paragraph_inlines(block.inlines, scale_mult=1.0, align=getattr(block, "align", "left"))
                        if not snap_ruling:
                            cur_y += self.line_h * 0.2

                elif isinstance(block, ListBlock):
                    render_list(block)

                elif isinstance(block, Table):
                    if getattr(block, "stable_id", None):
                        table_id = block.stable_id
                    else:
                        num_cols = len(block.rows[0].cells) if block.rows else 0
                        first_row_texts = []
                        if block.rows:
                            for cell in block.rows[0].cells:
                                for b in cell.blocks:
                                    if isinstance(b, Paragraph):
                                        for inl in b.inlines:
                                            if isinstance(inl, Text) and inl.text:
                                                first_row_texts.append(inl.text.strip())
                        first_row_sig = "-".join(first_row_texts)[:30]
                        tbl_sig = f"tbl:cols:{num_cols}|r0:{first_row_sig}"
                        if getattr(block, "occurrence", None) is not None:
                            tbl_occ = block.occurrence
                        else:
                            tbl_occ = table_sig_counts.get(tbl_sig, 0)
                            table_sig_counts[tbl_sig] = tbl_occ + 1
                        table_id = f"{tbl_sig}#{tbl_occ}"

                    def measure_word_bounds(word: str) -> float:
                        return self.wr.measure_text_width(word) * self.S

                    table_engine = TableLayoutEngine(
                        self.width,
                        self.line_h,
                        calc_text_bounds=measure_word_bounds,
                    )

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
                                cell_inlines.append(MathInline(
                                    latex=b.latex,
                                    ast=b.ast,
                                    occurrence=getattr(b, "occurrence", None),
                                    stable_id=getattr(b, "stable_id", None),
                                ))

                        scale_mult = 1.0
                        if cell_inlines:
                            items, n_t, n_m = self._layout_inlines(
                                cell_inlines, scale_mult=scale_mult, missing_symbols=missing_symbols,
                                max_item_width=max(usable_w, 1.0),
                                context_prefix="cell",
                            )
                            ntok += n_t
                            nmiss += n_m
                        else:
                            items = []

                        cell_lines: list[list[RenderItem]] = []
                        cell_metrics: list[LineVerticalMetrics] = []
                        cur_l: list[RenderItem] = []
                        cur_lw = 0.0
                        cur_asc = 0.0
                        cur_desc = 0.0

                        def flush_cur_line():
                            nonlocal cur_l, cur_lw, cur_asc, cur_desc
                            if cur_l:
                                cell_lines.append(cur_l)
                                extra_t = max(0.0, cur_asc - 0.7 * self.line_h)
                                extra_b = max(0.0, cur_desc - 0.3 * self.line_h)
                                line_h_tot = self.line_h + extra_t + extra_b
                                cell_metrics.append(
                                    LineVerticalMetrics(ascent=cur_asc, descent=cur_desc, width=cur_lw, height=line_h_tot)
                                )
                                cur_l = []
                                cur_lw = 0.0
                                cur_asc = 0.0
                                cur_desc = 0.0

                        last_was_break = False
                        for item in items:
                            if isinstance(item, RenderItem):
                                st = item.strokes
                                w = item.width
                                miss = item.missing
                                tok_str = item.token
                                tok_id = item.token_id
                                occ = item.occurrence
                            else:
                                st, w, miss = item[0], item[1], item[2]
                                tok_str = item[3] if len(item) > 3 else ""
                                tok_id = f"{tok_str}#0"
                                occ = 0
                            if miss == ["__LINE_BREAK__"]:
                                if cur_l:
                                    flush_cur_line()
                                else:
                                    # Dòng trống có chủ đích (ví dụ \n\n hoặc ngắt dòng đầu ô)
                                    cell_lines.append([])
                                    cell_metrics.append(LineVerticalMetrics(height=self.line_h))
                                last_was_break = True
                                continue
                            last_was_break = False

                            item_asc = item_desc = 0.0
                            if id(st) in self._math_extent:
                                ext = self._math_extent[id(st)]
                                item_asc = ext[0] * self.S * scale_mult
                                item_desc = ext[1] * self.S * scale_mult

                            sp = 6.0 * self.S * self.opts.space

                            if cur_l and cur_lw + sp + w > usable_w:
                                flush_cur_line()
                                cur_l = [RenderItem(0.0, st, w, miss, tok_str, tok_id, occ)]
                                cur_lw = w
                                cur_asc = item_asc
                                cur_desc = item_desc
                            else:
                                start_rel = cur_lw + (sp if cur_l else 0.0)
                                cur_l.append(RenderItem(start_rel, st, w, miss, tok_str, tok_id, occ))
                                cur_lw = start_rel + w
                                cur_asc = max(cur_asc, item_asc)
                                cur_desc = max(cur_desc, item_desc)
                        flush_cur_line()
                        if last_was_break:
                            cell_lines.append([])
                            cell_metrics.append(LineVerticalMetrics(height=self.line_h))
                        return cell_lines, cell_metrics

                    full_table_data = table_engine.layout_table(
                        block,
                        x0=self.x0,
                        y0=cur_y,
                        cell_inlines_formatter=cell_inlines_formatter,
                    )
                    if full_table_data.width <= 0 or not full_table_data.cells:
                        continue

                    curr_row_idx = 0
                    while curr_row_idx < len(full_table_data.row_heights):
                        avail_h = max_page_y - cur_y
                        if avail_h < self.line_h + 2 * table_engine.cell_padding and cur_y > pf.content_top:
                            new_page()
                            avail_h = max_page_y - cur_y

                        slice_data, next_row = full_table_data.slice_page(
                            curr_row_idx,
                            max_height=avail_h,
                            new_y=cur_y,
                            can_defer_to_next_page=(cur_y > pf.content_top),
                        )
                        if slice_data.warnings:
                            layout_warnings.extend(slice_data.warnings)
                        if not slice_data.cells or next_row == curr_row_idx:
                            new_page()
                            avail_h = max_page_y - cur_y
                            slice_data, next_row = full_table_data.slice_page(
                                curr_row_idx,
                                max_height=avail_h,
                                new_y=cur_y,
                                can_defer_to_next_page=False,
                            )
                            if slice_data.warnings:
                                layout_warnings.extend(slice_data.warnings)
                            if not slice_data.cells or next_row == curr_row_idx:
                                break

                        # 1. Sinh nét viền bảng cho trang hiện tại
                        if self.opts.stable_variants:
                            from chuviettay.model.rng import ScopedRNG
                            tbl_seed = ScopedRNG(self.effective_seed, "tbl_border", table_id, curr_row_idx).randrange(0, 1000000)
                        else:
                            tbl_seed = self.rnd.randint(0, 1000000)
                        border_strokes = table_engine.generate_border_strokes(
                            slice_data,
                            block.border_style,
                            jitter=self.J,
                            seed=tbl_seed,
                        )
                        for bs in border_strokes:
                            cur_page.append(xopp.stroke_xml(bs.points, self.bank.pen, self.opts.color, self.effective_wscale))
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
                                    metrics_list = getattr(laid_cell, "line_metrics", [])
                                    for l_idx, l_items in enumerate(laid_cell.rendered_lines):
                                        m = metrics_list[l_idx] if l_idx < len(metrics_list) else None
                                        extra_top = max(0.0, m.ascent - 0.7 * self.line_h) if m else 0.0
                                        line_step_h = m.height if m and m.height > 0 else self.line_h

                                        if not l_items:
                                            cell_cur_y += line_step_h
                                            continue
                                        line_w = l_items[-1][0] + l_items[-1][2]
                                        if align == "center":
                                            extra_x = max(0.0, (usable_w - line_w) / 2.0)
                                        elif align == "right":
                                            extra_x = max(0.0, usable_w - line_w)
                                        else:
                                            extra_x = 0.0

                                        start_x = laid_cell.x + table_engine.cell_padding + extra_x
                                        baseline_y = cell_cur_y + extra_top + self.line_h * 0.8
                                        cur_desc = m.descent if m and m.descent > 0 else 0.3 * self.line_h * self.S
                                        jitter_tol = 1.5 * getattr(self.opts, "jitter", 1.0)
                                        line_bottom_y = baseline_y + cur_desc + jitter_tol
                                        if line_bottom_y > max_page_y:
                                            if cur_y <= pf.content_top + 1e-6:
                                                # Phần tử đơn lẻ quá cao trên trang mới: co tỷ lệ, vẽ kẹp và cảnh báo
                                                denom = max(1e-6, cur_desc)
                                                downscale = max(0.2, min(1.0, (max_page_y - baseline_y - jitter_tol) / denom))
                                                if self.token_layout_callback is not None:
                                                    page_idx = pb.n_pages
                                                    for it in l_items:
                                                        if len(it) >= 5 and it[4]:
                                                            self.token_layout_callback(
                                                                TokenBox(
                                                                    page=page_idx,
                                                                    token=it[4],
                                                                    x=round(start_x + it[0], 2),
                                                                    y=round(cell_cur_y + extra_top, 2),
                                                                    width=round(it[2], 2),
                                                                    height=round(line_step_h * downscale, 2),
                                                                    missing=it[3] if len(it) > 3 else [],
                                                                )
                                                            )
                                                cell_strokes = self._render_text_line(
                                                    l_items,
                                                    baseline_y,
                                                    start_x,
                                                    scale_mult=downscale,
                                                    max_y=max_page_y,
                                                )
                                                cur_page.extend(cell_strokes)
                                                total_strokes += len(cell_strokes)
                                                total_lines += 1
                                                cell_cur_y += line_step_h * downscale
                                                layout_warnings.append(
                                                    f"Dòng {l_idx} trong ô ({laid_cell.row}, {laid_cell.col}) quá khổ trên trang mới; đã co tỷ lệ {downscale:.2f}x và kẹp tọa độ trong giới hạn trang."
                                                )
                                                continue
                                            else:
                                                # Chuyển tiếp các dòng chưa vẽ sang trang kế tiếp
                                                rem_lines = laid_cell.rendered_lines[l_idx:]
                                                rem_metrics = metrics_list[l_idx:]
                                                target_sid = laid_cell.source_cell_id
                                                found_target = False
                                                if target_sid is not None:
                                                    for search_r in range(0, len(full_table_data.cells)):
                                                        for orig_c in full_table_data.cells[search_r]:
                                                            if orig_c.source_cell_id == target_sid:
                                                                orig_c.rendered_lines = rem_lines
                                                                orig_c.line_metrics = rem_metrics
                                                                orig_c.is_continuation = True
                                                                if search_r >= curr_row_idx:
                                                                    next_row = min(next_row, search_r)
                                                                found_target = True
                                                                break
                                                        if found_target:
                                                            break
                                                if not found_target:
                                                    layout_warnings.append(
                                                        f"Không tìm thấy ô nguồn có ID {target_sid} khi chuyển tiếp dòng ô ({laid_cell.row}, {laid_cell.col}); bảo tồn nội dung tránh ghi đè."
                                                    )
                                                break

                                        if self.token_layout_callback is not None:
                                            page_idx = pb.n_pages
                                            for it in l_items:
                                                if len(it) >= 5 and it[4]:
                                                    self.token_layout_callback(
                                                        TokenBox(
                                                            page=page_idx,
                                                            token=it[4],
                                                            x=round(start_x + it[0], 2),
                                                            y=round(cell_cur_y + extra_top, 2),
                                                            width=round(it[2], 2),
                                                            height=round(line_step_h, 2),
                                                            missing=it[3] if len(it) > 3 else [],
                                                        )
                                                    )
                                        cell_strokes = self._render_text_line(
                                            l_items,
                                            baseline_y,
                                            start_x,
                                            scale_mult=1.0,
                                            max_y=max_page_y,
                                        )
                                        cur_page.extend(cell_strokes)
                                        total_strokes += len(cell_strokes)
                                        total_lines += 1
                                        cell_cur_y += line_step_h

                        cur_y += slice_data.height
                        curr_row_idx = next_row

                        if curr_row_idx < len(full_table_data.row_heights):
                            new_page()

                    cur_y += self.line_h * 0.4
                    total_tables += 1

                elif isinstance(block, MathBlock):
                    render_math_block(block)

            if cur_page or cur_y > pf.content_top or pb.n_pages == 0:
                pb.append_page(cur_page, page_h=page_h, page_w=page_w, background=bg)
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

        from chuviettay.model.text_utils import missing_letters_ranked
        missing_lets = (
            missing_letters_ranked(
                list(self.wr.missing.keys()),
                getattr(self.bank, "letters", {}),
                getattr(self.bank, "marks", {}),
                strict_case=self.opts.strict_case,
                bank_digits=getattr(self.bank, "digits", {}),
                bank_punct=getattr(self.bank, "punct", {}),
                bank_symbols=getattr(self.bank, "symbols", {}),
                bank_words=getattr(self.bank, "words", {}),
            )
            if self.wr.missing
            else []
        )

        result = WriteResult(
            out_path=out_path,
            n_lines=total_lines,
            n_strokes=total_strokes,
            n_tokens=ntok,
            n_missing_tokens=nmiss,
            missing=all_missing,
            missing_symbols=dict(missing_symbols),
            missing_letters=missing_lets,
            assembled_words=list(self.wr.assembled),
            n_tables=total_tables,
            n_math_blocks=total_math_blocks,
            n_pages=pb.n_pages,
            seed_used=self.effective_seed,
            warnings=layout_warnings,
        )

        if all_missing and self.opts.missing_grid:
            raw_grid_path = os.path.splitext(out_path)[0] + "_thieu.xopp"
            grid_path = xopp.resolve_missing_grid_path(raw_grid_path)
            items = sorted(all_missing.items(), key=lambda kv: (-kv[1], kv[0]))
            xopp.make_grid(
                grid_path,
                [k for k, _ in items],
                self.bank,
                "Từ/ký hiệu CHƯA có mẫu: viết mỗi từ/ký hiệu vào ô theo 4 vạch kẻ mốc (chuẩn hw3), rồi Ctrl+S và nạp file này tại tab Dạy chữ -> Nạp file lưới.",
                grid_version="hw3",
            )
            result.missing_grid_path = grid_path

        return result

    def layout(self, document: Document, out_path: str | None = None) -> tuple[str, WriteResult]:
        """Bố cục Document và trả về chuỗi XML .xoj và kết quả WriteResult."""
        if out_path:
            res = self.render(document, out_path)
            with open(out_path, "rb") as f:
                content = gzip.decompress(f.read()).decode("utf-8")
            return content, res
        with tempfile.NamedTemporaryFile(suffix=".xopp", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            res = self.render(document, tmp_path)
            with open(tmp_path, "rb") as f:
                content = gzip.decompress(f.read()).decode("utf-8")
            return content, res
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

