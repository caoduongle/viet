"""
Các hàm thuần (pure function) xử lý chữ tiếng Việt + hình học nét vẽ.

"Thuần" nghĩa là: không đọc/ghi file, không random, không phụ thuộc trạng thái ngoài
tham số truyền vào -- gọi lại nhiều lần với cùng đầu vào luôn ra cùng đầu ra. Nhờ vậy
đây là nhóm hàm DỄ VIẾT UNIT TEST NHẤT trong cả ứng dụng (xem tests/test_text_utils.py).

Toàn bộ công thức giữ NGUYÊN từ bản gốc (hw_note.py) -- chỉ thêm type hint + docstring,
không đổi bất kỳ hằng số hay phép tính nào, để không làm lệch kết quả so với kho mẫu
chu_cua_ban.json.gz đã học từ trước.
"""
from __future__ import annotations

import math
import unicodedata

from chuviettay.config import NANG, TONES

Stroke = list[float]           # một nét: [x0, y0, x1, y1, ...] phẳng
BBox = tuple[float, float, float, float]   # (min_x, min_y, max_x, max_y)


def fmt(v: float) -> str:
    """Định dạng số cho file .xopp: 3 số lẻ, bỏ số 0/dấu chấm thừa ở cuối."""
    s = "%.3f" % v
    return s.rstrip("0").rstrip(".") or "0"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def weight(tok: str) -> float:
    """Độ rộng ước lượng của một chuỗi (đơn vị 'chữ'), dùng để dàn dòng/ước lượng bề
    rộng khi CHƯA có mẫu chữ viết tay thật cho token đó."""
    w = 0.0
    for ch in unicodedata.normalize("NFC", tok):
        if ch in "iltrfj1|.,:;!'":
            w += 0.55
        elif ch in "mwMW%":
            w += 1.5
        elif ch.isupper():
            w += 1.25
        elif ch.isalnum():
            w += 1.0
        else:
            w += 0.8
    return w


def tone_info(key: str) -> tuple[str, int, int, list[str]]:
    """Phân tích một từ (đã gõ dấu Unicode) thành:
    (dấu thanh nếu có, chỉ số chữ cái mang dấu, số dấu mũ/trăng (ô/ơ/ă...), danh sách chữ cái).
    """
    letters: list[str] = []
    tone, vi, hats = "", -1, 0
    for ch in unicodedata.normalize("NFD", key):
        if unicodedata.combining(ch):
            if ch in TONES:
                tone, vi = ch, len(letters) - 1
            elif ch in "\u0302\u0306":
                hats += 1
        else:
            letters.append(ch)
    return tone, vi, hats, letters


def strip_tone(key: str) -> str:
    """Bỏ dấu thanh (không bỏ dấu mũ/trăng/móc), trả về dạng NFC."""
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", key) if c not in TONES))


def vowel_x(letters: list[str], vi: int, width: float) -> float:
    """Ước lượng toạ độ x (theo tỉ lệ `width`) của nguyên âm mang dấu thanh, dựa trên
    độ rộng ước lượng của từng chữ cái đứng trước nó."""
    ws = [weight(c) for c in letters]
    tot = sum(ws) or 1.0
    return (sum(ws[:vi]) + ws[vi] / 2) / tot * width


def near_extreme(strokes: list[Stroke], cx: float, fn, span: float = 5.0) -> float:
    """fn=min/max: tìm toạ độ y cực trị trong số các điểm nằm gần cx (trong khoảng span);
    nếu không có điểm nào gần đó thì xét toàn bộ các nét."""
    ys = [st[i + 1] for st in strokes for i in range(0, len(st), 2) if abs(st[i] - cx) <= span]
    if not ys:
        ys = [st[i + 1] for st in strokes for i in range(0, len(st), 2)]
    return fn(ys) if ys else 0.0


def shift(st: Stroke, dx: float, dy: float) -> Stroke:
    """Dịch một nét (x,y,x,y,...) theo (dx, dy), làm tròn 2 số lẻ."""
    return [round(v + (dx if i % 2 == 0 else dy), 2) for i, v in enumerate(st)]


def bbox(st: Stroke) -> BBox:
    xs, ys = st[0::2], st[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def find_tone(strokes: list[Stroke], key: str, xh: float) -> int:
    """Tìm nét nào trong danh sách `strokes` (của MỘT từ đã viết) là nét dấu thanh.
    Trả về chỉ số nét, hoặc -1 nếu không xác định chắc chắn.

    Logic: dấu nặng nằm DƯỚI dòng kẻ, thấp và ngắn; các dấu còn lại (huyền/sắc/hỏi/ngã)
    nằm CAO hơn cỡ chữ thường (xh) một khoảng, cũng ngắn -- nhưng phải khớp đúng số
    lượng nét "nằm cao" mong đợi (1 dấu + số dấu mũ/trăng + số chấm i/j khác vị trí có
    dấu + số gạch ngang chữ đ) thì mới coi là chắc chắn, tránh nhận nhầm nét của chữ
    cái khác (ví dụ chấm trên chữ "i") thành dấu thanh.
    """
    T, vi, hats, letters = tone_info(key)
    if not T or vi < 0:
        return -1
    bbs = [bbox(s) for s in strokes]
    if T == NANG:
        c = [k for k, b in enumerate(bbs) if b[1] > 0.2 * xh and b[3] - b[1] < 4 and b[2] - b[0] < 6]
        if not c:
            return -1
        w = max(b[2] for b in bbs)
        xv = vowel_x(letters, vi, w)
        return min(c, key=lambda k: abs((bbs[k][0] + bbs[k][2]) / 2 - xv))
    idots = sum(1 for k, ch in enumerate(letters) if ch in "ij" and k != vi)
    dbars = sum(1 for ch in letters if ch in "đĐ")
    c = [k for k, b in enumerate(bbs) if b[3] < -1.0 * xh and b[3] - b[1] < 5.5 and b[2] - b[0] < 7]
    return max(c) if len(c) == 1 + hats + idots + dbars else -1


def normalize_text(text: str) -> str:
    """Chuẩn hoá văn bản đầu vào trước khi viết: đổi dấu ngoặc kép/nháy kiểu 'thông
    minh' và gạch ngang dài về dạng ASCII thường, đổi tab thành khoảng trắng, bỏ các
    ký tự định dạng ẩn (Unicode category 'Cf', ví dụ zero-width joiner), rồi chuẩn hoá
    NFC."""
    for a, b in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'"), ("\u2013", "-"),
                 ("\u2014", "-"), ("\u00a0", " "), ("\t", "    ")):
        text = text.replace(a, b)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return unicodedata.normalize("NFC", text.replace("\r", ""))


def place(strokes: list[Stroke], ox: float, oy: float, s: float, rot: float) -> list[list[tuple[float, float]]]:
    """Đặt danh sách nét vào vị trí (ox, oy), nhân tỉ lệ s, xoay góc rot (radian).
    Trả về danh sách nét dạng list[(x, y)] (khác với Stroke phẳng) để ghép vào trang."""
    c, sn = math.cos(rot), math.sin(rot)
    return [[(ox + s * (st[i] * c - st[i + 1] * sn), oy + s * (st[i] * sn + st[i + 1] * c))
             for i in range(0, len(st), 2)] for st in strokes]
