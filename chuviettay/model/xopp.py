"""
Đọc/ghi định dạng file Xournal++ (.xopp) -- một file .xopp thực chất là XML nén gzip.

Module này gồm 2 nhóm việc:
1. XML thô: mở/lưu file .xopp, sinh thẻ <text>/<stroke> (dùng khi "write" tạo văn bản
   ra chữ viết tay, và khi "check"/"seed" tạo file lưới ô để người dùng viết mẫu vào).
2. Đọc ngược file lưới ô người dùng đã viết (dùng khi "learn" -- học từ những gì họ
   vừa viết tay vào các ô).

Toàn bộ công thức/hằng số giữ NGUYÊN từ bản gốc (hw_note.py).
"""
from __future__ import annotations

import gzip
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING
from xml.sax.saxutils import escape

from chuviettay.config import BASE, CH, COLS, CW, GUIDE, MXT, MYT, PAGE_H, PAGE_W, ROWS, TAG_CALIB, TAG_PLAIN
from chuviettay.model.text_utils import Stroke, fmt

TAG_HW3 = "hw3"
TAG_HW3_CALIB = "hw3c"
HW3_BASELINE_Y = 34.0
HW3_ASCENDER_Y = 20.0
HW3_DESCENDER_Y = 44.0
HW3_LEFT_MARGIN_X = 12.0
HW3_RIGHT_MARGIN_X = 116.0
HW3_GUIDE_COLORS = {GUIDE.lower()[:7], "#c8c8c8", "#a0a0a0", "#d8d8d8", "#e0e0e0", "#e8e8e8"}

VIETNAMESE_DIGRAPHS = [
    "ng", "nh", "ch", "tr", "ph", "th", "kh", "gi", "qu", "ươ", "ưa", "uy", "ay", "oa"
]

HW3_TONE_MAP = {
    "dấu sắc": "\u0301",
    "dấu huyền": "\u0300",
    "dấu hỏi": "\u0309",
    "dấu ngã": "\u0303",
    "dấu nặng": "\u0323",
    "sắc": "\u0301",
    "huyền": "\u0300",
    "hỏi": "\u0309",
    "ngã": "\u0303",
    "nặng": "\u0323",
}


def _ghost_vowel_o_points(cx: float, cy: float, rx: float, ry: float, n_pts: int = 16) -> list[tuple[float, float]]:
    """Tạo toạ độ điểm vẽ nét mốc chữ o mờ làm tham chiếu cho ô tập viết dấu thanh."""
    import math
    pts = []
    for i in range(n_pts + 1):
        angle = 2 * math.pi * i / n_pts
        pts.append((round(cx + rx * math.sin(angle), 2), round(cy - ry * math.cos(angle), 2)))
    return pts

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank

# ---------------------------------------------------------------- khung XML file .xopp
HEAD = ('<?xml version="1.0" standalone="no"?>\n'
        '<xournal creator="hw_note" fileversion="4">\n'
        '<title>Xournal++ document - see https://github.com/xournalpp/xournalpp</title>')
PAGE_OPEN = ('<page width="%s" height="%s">\n'
             '<background type="solid" color="#ffffffff" style="plain"/>\n<layer>')
PAGE_CLOSE = '</layer>\n</page>'


def pdf_background_xml(filename: str, pageno: int = 0, domain: str = "relative") -> str:
    """Sinh chuỗi XML thẻ <background type="pdf" ...> cho trang XOPP."""
    clean_fn = escape(filename)
    return f'<background type="pdf" domain="{domain}" filename="{clean_fn}" pageno="{pageno}"/>'


def page_open_xml(page_w: float, page_h: float, background: Any = None) -> str:
    """Sinh chuỗi XML mở trang <page ...> kèm thẻ <background ...> và mở <layer>."""
    if background is not None and hasattr(background, "to_xml"):
        bg_xml = background.to_xml()
    elif isinstance(background, str):
        bg_xml = background
    else:
        bg_xml = '<background type="solid" color="#ffffffff" style="plain"/>'
    return f'<page width="{fmt(page_w)}" height="{fmt(page_h)}">\n{bg_xml}\n<layer>'



def pts_xml(pts: list[tuple[float, float]]) -> str:
    return " ".join("%s %s" % (fmt(x), fmt(y)) for x, y in pts)


def save_xopp(path: str, parts: list[str]) -> None:
    """Ghi các đoạn XML (đã có sẵn HEAD/</xournal>) thành file .xopp (nén gzip)."""
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        f.write("\n".join(parts))


def read_xopp(path: str) -> ET.Element:
    """Đọc file .xopp, tự nhận biết có nén gzip hay không (một số công cụ khác có thể
    ghi .xopp không nén), trả về gốc cây XML."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)


def text_xml(x: float, y: float, s: str, size: int = 9) -> str:
    return ('<text font="Sans" size="%d" x="%s" y="%s" color="#808080ff">%s</text>'
            % (size, fmt(x), fmt(y), escape(s)))


def guide(pts: list[tuple[float, float]], w: float, color: str | None = None) -> str:
    """Một nét kẻ MỐC (đường kẻ dòng, khung ô...) -- không phải nét chữ thật, để mờ."""
    c = (color or GUIDE).lower()
    if not c.endswith("ff") and len(c) == 7:
        c += "ff"
    return '<stroke tool="pen" color="%s" width="%s">%s</stroke>' % (c, w, pts_xml(pts))


def stroke_xml(pts: list[tuple[float, float]], pen: dict, color: str | None = None, wscale: float = 1.0) -> str:
    a = dict(pen)
    w = float(a.pop("width", "1.41")) * wscale
    if color:
        a["color"] = color
    attrs = " ".join('%s="%s"' % (escape(str(k)), escape(str(v), entities={'"': "&quot;"})) for k, v in a.items())
    return '<stroke %s width="%s">%s</stroke>' % (attrs, fmt(w), pts_xml(pts))


# ---------------------------------------------------------------- file mẫu dạng lưới ô
def cell_xy(n: int) -> tuple[int, float, float]:
    """Ô thứ n (đánh số từ 0, theo trang rồi theo hàng rồi theo cột) -> (số trang, x0, y0)."""
    per = COLS * ROWS
    p, k = divmod(n, per)
    r, c = divmod(k, COLS)
    return p, MXT + c * CW, MYT + r * CH


def pick_calib_word(bank: "Bank") -> str | None:
    """Chọn một từ đã có NHIỀU mẫu và độ rộng ổn định (ít dao động giữa các lần viết),
    để dùng làm "ô đo cỡ tay" đầu tiên trong file lưới ô -- ưu tiên từ càng nhiều mẫu,
    càng ổn định càng tốt."""
    best, best_score = None, -1e9
    for k, lst in bank.words.items():
        if len(lst) < 5 or " " in k or not k.isalpha():
            continue
        ws = [i["w"] for i in lst]
        mu = sum(ws) / len(ws)
        cv = statistics.pstdev(ws) / mu if mu else 1.0
        score = len(lst) - 6 * cv
        if score > best_score:
            best, best_score = k, score
    return best or next(iter(bank.words), None)


def make_grid(path: str, labels: list[str], bank: "Bank", header: str,
              samples: dict[str, list[Stroke]] | None = None, calib: bool = True) -> None:
    """Tạo file .xopp dạng lưới ô, mỗi ô có sẵn chữ in mờ + 2 đường kẻ mốc, để người
    dùng viết tay từng từ trong `labels` vào (dùng cho seed/check/từ còn thiếu).

    samples: {nhãn: danh sách nét} nếu muốn hiện SẴN chữ viết tay đã học trong ô (lệnh
             check -- xem lại kho mẫu).
    calib:   có chèn thêm một ô "đo cỡ tay" ở đầu hay không (một từ đã biết sẵn, không
             đánh dấu gì đặc biệt trên chữ, chỉ nhận ra qua VỊ TRÍ ô đầu tiên + thẻ ẩn
             hw2c) để công cụ tự chỉnh cỡ chữ mới học cho khớp cỡ tay đã học trước đó.
    """
    cw = pick_calib_word(bank) if calib else None
    if cw:
        labels = [cw] + list(labels)
    per = COLS * ROWS
    npages = max(1, -(-len(labels) // per))
    o = [HEAD]
    xh = bank.xh
    for p in range(npages):
        o.append(PAGE_OPEN % (PAGE_W, PAGE_H))
        if p == 0:
            o.append(text_xml(MXT, 6, header, 8))
            o.append(text_xml(MXT, 20, "Viết nhỏ như chữ hằng ngày, ĐỪNG lấp đầy ô: chữ cao khoảng bằng đoạn kẻ ngắn phía trên, đặt trên đường kẻ dài.", 8))
            if cw:
                o.append(text_xml(MXT, 34, "Ô đầu tiên ('%s') dùng để đo cỡ tay bạn: viết lại đúng từ đó, thế thôi — cỡ nào cũng được, tool tự chỉnh các từ khác cho khớp." % cw, 8))
            o.append(text_xml(MXT, 46 if cw else 34, TAG_CALIB if cw else TAG_PLAIN, 6))
        for k in range(p * per, min(len(labels), (p + 1) * per)):
            _, x0, y0 = cell_xy(k)
            o.append(guide([(x0, y0), (x0 + CW, y0), (x0 + CW, y0 + CH), (x0, y0 + CH), (x0, y0)], 0.4))
            o.append(guide([(x0 + 3, y0 + BASE), (x0 + CW - 3, y0 + BASE)], 0.8))
            o.append(guide([(x0 + 3, y0 + BASE - xh), (x0 + 22, y0 + BASE - xh)], 0.5))
            o.append(text_xml(x0 + 2, y0 + 1, labels[k]))
            if samples and labels[k] in samples:
                for st in samples[labels[k]]:
                    pts = [(x0 + 8 + st[i], y0 + BASE + st[i + 1]) for i in range(0, len(st), 2)]
                    o.append(stroke_xml(pts, bank.pen))
        o.append(PAGE_CLOSE)
    o.append("</xournal>")
    save_xopp(path, o)


STANDALONE_TONE_LABELS = [
    "dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng"
]


def make_letter_grid(
    path: str,
    labels: list[str],
    bank: "Bank",
    target_xh: float = 7.94,
    include_digraphs: bool = True,
    include_tones: bool = True,
) -> None:
    """Tạo file .xopp lưới ô ký tự mẫu chuẩn hw3 với 4 đường kẻ mốc và 2 vạch giới hạn lề."""
    lbls = list(labels)
    if include_digraphs:
        for dg in VIETNAMESE_DIGRAPHS:
            if dg not in lbls:
                lbls.append(dg)
    if include_tones:
        for tone_lbl in STANDALONE_TONE_LABELS:
            if tone_lbl not in lbls:
                lbls.append(tone_lbl)

    per = COLS * ROWS
    npages = max(1, -(-len(lbls) // per))
    o = [HEAD]
    for p in range(npages):
        o.append(PAGE_OPEN % (PAGE_W, PAGE_H))
        if p == 0:
            o.append(text_xml(MXT, 6, "HƯỚNG DẪN VIẾT TỜ LƯỚI KÝ TỰ MẪU (Chuẩn hw3)", 10))
            o.append(text_xml(MXT, 18, "1. Chiều cao: Viết chữ thường nằm gọn giữa đường Chân chữ (đậm) và vạch x-height (nét vừa, ~8pt).", 7))
            o.append(text_xml(MXT, 28, "2. Chữ cao & chữ hoa: Đỉnh chữ b, d, h, k, l và chữ hoa chạm vạch Ascender phía trên.", 7))
            o.append(text_xml(MXT, 38, "3. Đuôi chữ & lề ngang: Đuôi chữ g, p, q, y chạm vạch Descender dưới. Viết nằm trong 2 vạch mốc lề trái/phải.", 7))
            o.append(text_xml(MXT, 48, TAG_HW3, 6))

        for k in range(p * per, min(len(lbls), (p + 1) * per)):
            _, x0, y0 = cell_xy(k)
            # Khung viền ô
            o.append(guide([(x0, y0), (x0 + CW, y0), (x0 + CW, y0 + CH), (x0, y0 + CH), (x0, y0)], 0.4, color="#c8c8c8"))
            # Vạch Ascender (nét mảnh trên cùng)
            o.append(guide([(x0 + 12, y0 + HW3_ASCENDER_Y), (x0 + CW - 12, y0 + HW3_ASCENDER_Y)], 0.5, color="#e0e0e0"))
            # Vạch x-height (nét vừa)
            xh_y = y0 + HW3_BASELINE_Y - target_xh
            o.append(guide([(x0 + 12, xh_y), (x0 + CW - 12, xh_y)], 0.75, color="#c8c8c8"))
            # Đường chân chữ Baseline (nét đậm)
            o.append(guide([(x0 + 6, y0 + HW3_BASELINE_Y), (x0 + CW - 6, y0 + HW3_BASELINE_Y)], 1.0, color="#a0a0a0"))
            # Vạch Descender (nét mảnh dưới cùng)
            o.append(guide([(x0 + 12, y0 + HW3_DESCENDER_Y), (x0 + CW - 12, y0 + HW3_DESCENDER_Y)], 0.5, color="#e0e0e0"))
            # Giới hạn lề trái & lề phải
            o.append(guide([(x0 + HW3_LEFT_MARGIN_X, y0 + 10), (x0 + HW3_LEFT_MARGIN_X, y0 + CH - 4)], 0.5, color="#d8d8d8"))
            o.append(guide([(x0 + HW3_RIGHT_MARGIN_X, y0 + 10), (x0 + HW3_RIGHT_MARGIN_X, y0 + CH - 4)], 0.5, color="#d8d8d8"))
            # Nhãn mẫu
            o.append(text_xml(x0 + 2, y0 + 1, lbls[k]))
            # Nét chữ mờ tham chiếu (ghost vowel o) cho ô tập viết dấu thanh
            if lbls[k].strip().lower() in HW3_TONE_MAP:
                ghost_cx = x0 + CW / 2.0
                ghost_ry = target_xh / 2.0
                ghost_rx = target_xh * 0.42
                ghost_cy = y0 + HW3_BASELINE_Y - ghost_ry
                o.append(guide(_ghost_vowel_o_points(ghost_cx, ghost_cy, ghost_rx, ghost_ry), 0.5, color="#e8e8e8"))

        o.append(PAGE_CLOSE)
    o.append("</xournal>")
    save_xopp(path, o)


# ---------------------------------------------------------------- đọc ngược file đã viết tay (learn)
@dataclass
class RawCell:
    """Một ô đã đọc được từ file người dùng viết tay, TRƯỚC khi chuyển sang toạ độ
    tương đối của kho mẫu (đó là việc của learning.py)."""
    label: str
    base: float                 # toạ độ y của đường kẻ chân chữ (đáy ô), theo hệ toạ độ trang
    left: float                 # x nhỏ nhất trong các nét đã viết ở ô này
    right: float                # x lớn nhất
    strokes: list[Stroke] = field(default_factory=list)   # nét thô, toạ độ tuyệt đối trong trang
    lsb: float = 0.0
    rsb: float = 0.0
    is_hw3: bool = False
    cell_x0: float = 0.0


def parse_learn_file(path: str) -> tuple[dict[tuple[int, int, int], RawCell], bool]:
    """Đọc một file .xopp người dùng đã viết tay vào lưới ô (từ seed/check/write),
    trả về: ({(trang, cột, hàng): RawCell}, có_thẻ_đo_cỡ_tay).

    Cách nhận diện: mỗi ô có một thẻ <text> ghi sẵn NHÃN (chữ cần viết) ở đúng vị trí
    lưới (MXT/MYT/CW/CH) -- dùng vị trí thẻ đó để biết ô nằm ở (cột, hàng) nào. Các nét
    <stroke> không phải màu GUIDE (đường kẻ mốc) được gán vào ô có tâm điểm nằm trong
    đúng ô lưới đó.
    """
    root = read_xopp(path)
    raw: dict[tuple[int, int, int], RawCell] = {}
    has_calib = False
    is_hw3 = False
    for pi, page in enumerate(root.findall("page")):
        cells: dict[tuple[int, int], str] = {}
        for t in page.iter("text"):
            s = (t.text or "").strip()
            if s in (TAG_PLAIN, TAG_CALIB, TAG_HW3, TAG_HW3_CALIB):
                has_calib = has_calib or (s in (TAG_CALIB, TAG_HW3_CALIB))
                if s in (TAG_HW3, TAG_HW3_CALIB):
                    is_hw3 = True
                continue
            try:
                x, y = float(t.get("x")), float(t.get("y"))
            except (TypeError, ValueError):
                continue
            col, row = int((x - MXT) // CW), int((y - MYT) // CH)
            if 0 <= col < COLS and 0 <= row < ROWS and s:
                cells[(col, row)] = s

        strokes_by_cell: dict[tuple[int, int], list[Stroke]] = {}
        for st in page.iter("stroke"):
            if st.get("tool", "pen") != "pen":
                continue
            color_hex = (st.get("color") or "").lower()[:7]
            if color_hex in HW3_GUIDE_COLORS:
                continue
            n = [float(v) for v in (st.text or "").split()]
            if len(n) < 2:
                continue
            cx, cy = sum(n[0::2]) / (len(n) // 2), sum(n[1::2]) / (len(n) // 2)
            col, row = int((cx - MXT) // CW), int((cy - MYT) // CH)
            if (col, row) in cells:
                strokes_by_cell.setdefault((col, row), []).append(n)

        for cell, sts in strokes_by_cell.items():
            label = cells[cell]
            base = MYT + cell[1] * CH + BASE
            left = min(min(s[0::2]) for s in sts)
            right = max(max(s[0::2]) for s in sts)
            cell_x0 = MXT + cell[0] * CW
            lsb = max(0.0, left - (cell_x0 + HW3_LEFT_MARGIN_X))
            rsb = max(0.0, (cell_x0 + HW3_RIGHT_MARGIN_X) - right)
            raw[(pi,) + cell] = RawCell(
                label=label,
                base=base,
                left=left,
                right=right,
                strokes=sts,
                lsb=round(lsb, 2),
                rsb=round(rsb, 2),
                is_hw3=is_hw3,
                cell_x0=cell_x0,
            )
    return raw, has_calib
