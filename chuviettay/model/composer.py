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

from chuviettay.config import MAXH
from chuviettay.model import xopp
from chuviettay.model.bank import Bank
from chuviettay.model.text_utils import Stroke, fmt, normalize_text, place
from chuviettay.model.writer import Writer

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

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ nghiệp vụ của các tùy chọn viết. Ném ValueError nếu sai."""
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
        if self.color is not None:
            self.color = parse_color(self.color)


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
    n_tables: int = 0                      # tổng số bảng biểu đã dàn trang
    n_math_blocks: int = 0                 # tổng số khối công thức toán học đã dàn trang

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
    """Thuật toán chính: chuẩn hoá văn bản, ghép từng token thành nét (Writer), dàn
    thành các dòng vừa bề rộng, chia trang, thêm "run tay" (jitter) rồi đặt nét lên
    từng trang. -> (các đoạn XML sẵn sàng ghi bằng xopp.save_xopp, WriteResult chưa có
    out_path/missing_grid_path -- 2 trường đó điền ở write_document())."""
    rnd = random.Random(opts.seed)
    J = opts.jitter
    text = normalize_text(text)
    wr = Writer(bank, rnd, J, not opts.strict_case, opts.space)
    line_h = opts.line or bank.d["line"]
    width = opts.width or bank.d["width"]
    x0 = bank.d["x0"]
    S = opts.scale
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
                    o.append(xopp.stroke_xml(fin, bank.pen, opts.color, opts.wscale * (1 + rnd.gauss(0, 0.02 * J))))
                    nstroke += 1
        o.append(xopp.PAGE_CLOSE)
    o.append("</xournal>")

    result = WriteResult(
        out_path="", n_lines=len(lines), n_strokes=nstroke,
        n_tokens=ntok, n_missing_tokens=nmiss, missing=dict(wr.missing),
    )
    return o, result


def write_document(bank: Bank, text: str, opts: WriteOptions, out_path: str,
                    make_missing_grid: bool = True) -> WriteResult:
    """compose_document() rồi lưu ra `out_path`; nếu còn token thiếu mẫu, TỰ ĐỘNG tạo
    thêm file lưới ô cùng tên (hậu tố _thieu.xopp) để người dùng viết mẫu các từ đó
    vào -- giữ đúng hành vi bản gốc (lệnh `learn` sau đó nạp lại đúng file này)."""
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
