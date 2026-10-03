"""
composer -- ghép MỘT văn bản hoàn chỉnh (nhiều dòng/nhiều trang) thành file .xopp.

Đây là phần thuật toán trong hàm cmd_write() của bản gốc (hw_note.py), tách riêng
PHẦN THUẬT TOÁN (dàn dòng theo bề rộng, chia trang, thêm độ "run tay" ngẫu nhiên) ra
khỏi PHẦN HIỂN THỊ (in ra màn hình) -- để cả CLI lẫn GUI dùng chung một hàm, mỗi bên tự
quyết định hiển thị kết quả kiểu gì (in ra terminal, hay hiện trong ô "Kết quả" của
tab Viết chữ).

Công thức/hằng số giữ NGUYÊN từ bản gốc.
"""
from __future__ import annotations

import math
import os
import random
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from chuviettay.config import MAXH
from chuviettay.model import xopp
from chuviettay.model.bank import Bank
from chuviettay.model.text_utils import Stroke, fmt, place
from chuviettay.model.writer import Writer

if TYPE_CHECKING:
    from chuviettay.document.page_format import PageFormat


class WriteMode(str, Enum):
    """Chế độ kết xuất chữ viết tay."""
    SEMANTIC = "semantic"  # Tái dàn trang ngữ nghĩa tự do qua DocumentLayoutEngine
    FIDELITY = "fidelity"  # Khóa cố định bố cục, giữ nguyên ảnh & trang qua FixedLayoutEngine


COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def parse_color(c: str) -> str:
    """Kiểm tra và chuẩn hóa mã màu hex: #RRGGBB hoặc #RRGGBBAA."""
    s = c.strip()
    if not COLOR_RE.match(s):
        raise ValueError(
            f"Mã màu không hợp lệ: {c!r}. Chỉ chấp nhận định dạng hex #RRGGBB hoặc #RRGGBBAA (ví dụ: #1a237e)."
        )
    return s.lower()


@dataclass
class WriteOptions:
    """Tuỳ chọn khi 'viết' văn bản -- tương ứng các cờ dòng lệnh --scale/--line/...
    của lệnh `write` bản gốc."""
    scale: float = 1.0            # nhân cỡ chữ
    line: float | None = None     # khoảng cách dòng (pt); None = lấy mặc định của kho mẫu
    width: float | None = None    # bề rộng dòng (pt); None = lấy mặc định của kho mẫu
    space: float = 1.0            # nhân khoảng cách giữa các từ
    jitter: float = 1.0           # độ "run tay" ngẫu nhiên (0 = tắt)
    wscale: float = 1.0           # nhân độ dày nét
    color: str | None = None      # đổi màu mực, ví dụ "#1a237e"; None = màu mặc định trong kho mẫu
    seed: int | None = None       # cố định số ngẫu nhiên (để tái tạo lại đúng kết quả)
    strict_case: bool = False     # không tự hạ chữ hoa đầu từ khi tìm mẫu thay thế

    # Cấu hình khổ giấy, lề và nền trang (áp dụng cho DocumentLayoutEngine)
    paper: str = "a4"             # a5, a4, a3, letter, legal, 16:9, 4:3, custom
    orientation: str = "portrait" # portrait (dọc) hoặc landscape (ngang)
    paper_width: float | None = None   # kích thước tùy chỉnh (pt), chỉ dùng khi paper="custom"
    paper_height: float | None = None  # kích thước tùy chỉnh (pt), chỉ dùng khi paper="custom"
    margin_left: float = 36.0     # lề trái (pt)
    margin_right: float = 36.0    # lề phải (pt)
    margin_top: float = 40.0      # lề trên (pt)
    margin_bottom: float = 40.0   # lề dưới (pt)
    background: str = "plain"     # plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music
    background_spacing: float | None = None  # khoảng cách dòng/ô kẻ (pt), ví dụ 14.17 pt = 5mm
    background_margin: float | None = None   # lề dọc cho ruled (pt)
    background_color: str = "#ffffffff"      # màu nền hex RGBA

    # Chế độ kết xuất: semantic (tái dàn trang) hoặc fidelity (khóa cố định bố cục)
    mode: str = "semantic"
    missing_grid: bool = True     # tự động tạo file _thieu.xopp khi thiếu mẫu (có thể tắt bằng --no-missing-grid)
    assemble_letters: bool = False  # tự động ghép từ các mẫu chữ cái khi thiếu từ nguyên khối

    # Các tuỳ chọn chất lượng ghép chữ cái & độ đậm nét
    letter_gap: float = 1.0       # hệ số nhân khoảng cách chữ cái
    target_xh: float = 7.94       # x-height mục tiêu chuẩn (pt)
    auto_xh: bool = False         # tự động chuẩn hóa x-height và bù trừ wscale theo tỉ lệ thực của note (17.8%)
    pen_clearance_factor: float = 0.8  # hệ số sàn khe hở tối thiểu theo độ dày bút (clearance >= factor * pen)

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ nghiệp vụ của các tùy chọn viết. Ném ValueError nếu sai."""
        from chuviettay.document.page_format import PAPER_SIZES, VALID_BACKGROUND_STYLES

        m = self.mode.lower().strip()
        if m not in ("semantic", "fidelity"):
            raise ValueError(f"Chế độ xử lý không hợp lệ: {self.mode!r}. Chỉ chấp nhận: semantic, fidelity")

        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError(f"scale phải là số dương hữu hạn, nhận được: {self.scale}")
        if self.line is not None and (not math.isfinite(self.line) or self.line <= 0):
            raise ValueError(f"line phải là số dương hữu hạn hoặc None, nhận được: {self.line}")
        if self.width is not None and (not math.isfinite(self.width) or self.width <= 0):
            raise ValueError(f"width phải là số dương hữu hạn hoặc None, nhận được: {self.width}")
        if not math.isfinite(self.space) or self.space <= 0:
            raise ValueError(f"space phải là số dương hữu hạn, nhận được: {self.space}")
        if not math.isfinite(self.jitter) or self.jitter < 0:
            raise ValueError(f"jitter phải là số không âm hữu hạn, nhận được: {self.jitter}")
        if not math.isfinite(self.wscale) or self.wscale <= 0:
            raise ValueError(f"wscale phải là số dương hữu hạn, nhận được: {self.wscale}")
        if not math.isfinite(self.letter_gap) or self.letter_gap <= 0:
            raise ValueError(f"letter_gap phải là số dương hữu hạn, nhận được: {self.letter_gap}")
        if not math.isfinite(self.target_xh) or self.target_xh <= 0:
            raise ValueError(f"target_xh phải là số dương hữu hạn, nhận được: {self.target_xh}")
        if not math.isfinite(self.pen_clearance_factor) or self.pen_clearance_factor < 0:
            raise ValueError(f"pen_clearance_factor phải là số không âm hữu hạn, nhận được: {self.pen_clearance_factor}")
        if self.color is not None:
            self.color = parse_color(self.color)

        # Kiểm tra khổ giấy & hướng giấy
        p = self.paper.lower().strip()
        if p != "custom" and p not in PAPER_SIZES:
            raise ValueError(f"Khổ giấy không hợp lệ: {self.paper!r}. Chỉ chấp nhận: {', '.join(PAPER_SIZES.keys())}, custom")
        if p == "custom":
            if self.paper_width is None or not math.isfinite(self.paper_width) or self.paper_width <= 0:
                raise ValueError(f"paper_width cho khổ giấy custom phải là số dương hữu hạn, nhận được: {self.paper_width}")
            if self.paper_height is None or not math.isfinite(self.paper_height) or self.paper_height <= 0:
                raise ValueError(f"paper_height cho khổ giấy custom phải là số dương hữu hạn, nhận được: {self.paper_height}")

        ori = self.orientation.lower().strip()
        if ori not in ("portrait", "landscape"):
            raise ValueError(f"Hướng giấy không hợp lệ: {self.orientation!r}. Chỉ chấp nhận: portrait, landscape")

        # Kiểm tra lề trang
        for m_name, m_val in (("margin_left", self.margin_left), ("margin_right", self.margin_right),
                              ("margin_top", self.margin_top), ("margin_bottom", self.margin_bottom)):
            if not math.isfinite(m_val) or m_val < 0:
                raise ValueError(f"{m_name} phải là số không âm hữu hạn, nhận được: {m_val}")

        # Kiểm tra nền trang
        bg_style = self.background.lower().strip()
        if bg_style not in VALID_BACKGROUND_STYLES:
            raise ValueError(f"Kiểu nền không hợp lệ: {self.background!r}. Chỉ chấp nhận: {', '.join(sorted(VALID_BACKGROUND_STYLES))}")
        if self.background_spacing is not None and (not math.isfinite(self.background_spacing) or self.background_spacing <= 0):
            raise ValueError(f"background_spacing phải là số dương hữu hạn, nhận được: {self.background_spacing}")
        if self.background_margin is not None and (not math.isfinite(self.background_margin) or self.background_margin < 0):
            raise ValueError(f"background_margin phải là số không âm hữu hạn, nhận được: {self.background_margin}")
        if self.background_color is not None:
            self.background_color = parse_color(self.background_color)

        pf = self.resolve_page_format()
        if self.margin_left + self.margin_right >= pf.width:
            raise ValueError(
                f"Tổng lề trái ({self.margin_left} pt) và lề phải ({self.margin_right} pt) "
                f"phải nhỏ hơn bề ngang trang ({pf.width} pt)."
            )
        if self.margin_top + self.margin_bottom >= pf.height:
            raise ValueError(
                f"Tổng lề trên ({self.margin_top} pt) và lề dưới ({self.margin_bottom} pt) "
                f"phải nhỏ hơn bề dọc trang ({pf.height} pt)."
            )

    def resolve_page_format(self) -> PageFormat:
        """Phân giải cấu hình WriteOptions thành đối tượng PageFormat hoàn chỉnh."""
        from chuviettay.document.page_format import (
            PAPER_SIZES,
            PageBackground,
            PageFormat,
            PaperSize,
        )

        p = self.paper.lower().strip()
        if p == "custom":
            w = self.paper_width if self.paper_width is not None else 595.28
            h = self.paper_height if self.paper_height is not None else 841.89
            paper_size = PaperSize("Custom", w, h)
        else:
            paper_size = PAPER_SIZES.get(p, PAPER_SIZES["a4"])

        bg = PageBackground(
            style=self.background.lower().strip(),
            spacing=self.background_spacing,
            margin=self.background_margin,
            color=self.background_color,
        )

        return PageFormat(
            paper=paper_size,
            orientation=self.orientation.lower().strip(),
            margin_left=self.margin_left,
            margin_right=self.margin_right,
            margin_top=self.margin_top,
            margin_bottom=self.margin_bottom,
            background=bg,
        )



@dataclass
class WriteResult:
    """Kết quả một lần 'viết' -- CLI/GUI tự quyết định hiển thị thế nào từ dữ liệu này,
    không phải parse chuỗi in ra màn hình."""
    out_path: str
    n_lines: int
    n_strokes: int
    n_tokens: int
    n_missing_tokens: int
    missing: dict[str, int] = field(default_factory=dict)   # token thiếu mẫu -> số lần gặp
    missing_grid_path: str | None = None   # file lưới ô đã tạo để dạy các từ thiếu (None nếu không thiếu gì)
    missing_symbols: dict[str, int] = field(default_factory=dict)  # ký hiệu toán học thiếu mẫu -> số lần gặp
    missing_letters: list[tuple[str, int]] = field(default_factory=list)  # (chữ cái/dấu, số từ mở khoá)
    assembled_words: list[str] = field(default_factory=list)  # các từ được ghép thành công từ chữ cái
    n_tables: int = 0                      # tổng số bảng biểu đã dàn trang
    n_math_blocks: int = 0                 # tổng số khối công thức toán học đã dàn trang
    n_pages: int = 1                       # tổng số trang của tài liệu
    n_images: int = 0                      # tổng số hình ảnh giữ nguyên ở nền

    def missing_sorted(self) -> list[tuple[str, int]]:
        """[(token, số lần gặp), ...] gặp nhiều nhất xếp trước, bằng nhau thì theo chữ
        cái -- một cách sắp xếp duy nhất dùng chung cho file lưới ô, CLI và GUI (bản
        gốc viết lại đúng biểu thức sắp xếp này ở 3 chỗ)."""
        return sorted(self.missing.items(), key=lambda kv: (-kv[1], kv[0]))

    def missing_symbols_sorted(self) -> list[tuple[str, int]]:
        """[(ký hiệu, số lần gặp), ...] gặp nhiều nhất xếp trước, bằng nhau thì theo chữ cái."""
        return sorted(self.missing_symbols.items(), key=lambda kv: (-kv[1], kv[0]))


def _missing_grid_path(out_path: str) -> str:
    return os.path.splitext(out_path)[0] + "_thieu.xopp"


def compose_document(bank: Bank, text: str, opts: WriteOptions) -> tuple[list[str], WriteResult]:
    """[DEPRECATED] Thuật toán kết xuất đơn trang cũ (giữ cho kiểm định tương thích ngược).

    Toàn bộ luồng kết xuất hiện đại sử dụng DocumentLayoutEngine (chuviettay/layout/engine.py).
    """
    rnd = random.Random(opts.seed)
    J = opts.jitter
    S = opts.scale
    effective_wscale = opts.wscale
    if opts.auto_xh:
        current_xh = getattr(bank, "xh", 7.94) or 7.94
        if current_xh > 0 and abs(current_xh - opts.target_xh) > 0.05:
            S = opts.scale * (opts.target_xh / current_xh)
        base_pen = float(bank.pen.get("width", 1.41)) if bank.pen else 1.41
        desired_pen = 0.178 * opts.target_xh * (S / (opts.target_xh / current_xh if current_xh > 0 else 1.0))
        effective_wscale = opts.wscale * (desired_pen / base_pen if base_pen > 0 else 1.0)

    wr = Writer(
        bank,
        rnd,
        J,
        not opts.strict_case,
        opts.space,
        assemble_letters=opts.assemble_letters,
        letter_gap=opts.letter_gap,
        pen_clearance_factor=opts.pen_clearance_factor,
    )
    line_h = opts.line or bank.d["line"]
    width = opts.width or bank.d["width"]
    x0 = bank.d["x0"]
    gaps = [g for g in bank.d["wgaps"] if 6.0 <= g <= 20.0] or [11.0]

    lines: list[list[tuple[float, list[Stroke], float]]] = []
    ntok = nmiss = 0
    for para in text.split("\n"):
        toks = para.split()
        if not toks:
            lines.append([])
            continue
        cur, curw = [], 0.0
        for tok in toks:
            st, w, miss = wr.token(tok)
            ntok += 1
            if miss:
                nmiss += 1
                for m in miss:
                    wr.missing[m] = wr.missing.get(m, 0) + 1
            w *= S
            sp = rnd.choice(gaps) * S * opts.space * (1 + rnd.gauss(0, 0.06 * J))
            if cur and curw + sp + w > width:
                lines.append(cur)
                cur, curw = [], 0.0
            start = curw + (sp if cur else 0.0)
            cur.append((start, st, w))
            curw = start + w
        if cur:
            lines.append(cur)

    per_page = max(1, int((MAXH - 40) // line_h))
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]
    o, nstroke = [xopp.HEAD], 0
    for pg in pages:
        o.append(xopp.PAGE_OPEN % (fmt(x0 + width + 20), fmt(max(200.0, 40 + len(pg) * line_h))))
        for i, ln in enumerate(pg):
            base = 20 + (i + 1) * line_h
            slope, amp = rnd.gauss(0, 0.0015 * J), 0.45 * J
            wl, ph = rnd.uniform(140, 260), rnd.uniform(0, 6.283)
            xo = x0 + rnd.gauss(0, 1.2 * J)
            for start, st, w in ln:
                if not st:
                    continue
                s = S * (1 + rnd.gauss(0, 0.02 * J))
                rot = rnd.gauss(0, 0.010 * J)
                dy = rnd.gauss(0, 0.35 * J)
                for pts in place(st, 0.0, 0.0, s, rot):
                    fin = []
                    for x, y in pts:
                        X = start + x
                        fin.append((xo + X, base + dy + y + slope * X + amp * math.sin(6.283 * X / wl + ph)))
                    o.append(xopp.stroke_xml(fin, bank.pen, opts.color, effective_wscale * (1 + rnd.gauss(0, 0.02 * J))))
                    nstroke += 1
        o.append(xopp.PAGE_CLOSE)
    o.append("</xournal>")

    from chuviettay.model.text_utils import missing_letters_ranked
    missing_lets = (
        missing_letters_ranked(
            list(wr.missing.keys()),
            getattr(bank, "letters", {}),
            getattr(bank, "marks", {}),
            strict_case=opts.strict_case,
            bank_digits=getattr(bank, "digits", {}),
            bank_punct=getattr(bank, "punct", {}),
            bank_symbols=getattr(bank, "symbols", {}),
            bank_words=getattr(bank, "words", {}),
        )
        if wr.missing
        else []
    )

    result = WriteResult(
        out_path="", n_lines=len(lines), n_strokes=nstroke,
        n_tokens=ntok, n_missing_tokens=nmiss, missing=dict(wr.missing),
        missing_letters=missing_lets,
        assembled_words=list(wr.assembled),
    )
    return o, result


def write_document(bank: Bank, text: str, opts: WriteOptions, out_path: str,
                    make_missing_grid: bool = True) -> WriteResult:
    """[DEPRECATED] Ghi file theo thuật toán cũ compose_document().

    Dùng riêng cho kiểm định đối sánh (golden master). Mọi caller mới sử dụng AppController.write_text()
    hoặc AppController.write_document().
    """
    parts, result = compose_document(bank, text, opts)
    xopp.save_xopp(out_path, parts)
    result.out_path = out_path

    if make_missing_grid and result.missing:
        grid_path = _missing_grid_path(out_path)
        items = result.missing_sorted()
        xopp.make_grid(
            grid_path, [k for k, _ in items], bank,
            "Từ CHƯA có mẫu: viết mỗi từ vào ô, giữa hai đường kẻ, rồi Ctrl+S và chạy: python hw_note.py learn %s"
            % os.path.basename(grid_path))
        result.missing_grid_path = grid_path

    return result
