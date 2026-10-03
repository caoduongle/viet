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
from typing import Any
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


def split_letters(word: str) -> tuple[list[str], str, int]:
    """Phân tách một từ tiếng Việt thành danh sách chữ cái cơ sở (NFC), dấu thanh và vị trí nguyên âm mang dấu.

    Args:
        word: Từ tiếng Việt (đã chuẩn hoá NFC hoặc bất kỳ dạng Unicode nào).

    Returns:
        letters: Danh sách chữ cái cơ sở (NFC) không chứa dấu thanh (ví dụ: ['đ', 'ư', 'ơ', 'n', 'g']).
        tone: Ký tự dấu thanh Unicode (trong config.TONES) hoặc "" nếu không có dấu thanh.
        vowel_index: Chỉ số của nguyên âm mang dấu thanh trong danh sách `letters` (-1 nếu không có).
    """
    tone, vi, _, _ = tone_info(word)
    unaccented = strip_tone(word)
    letters = list(unicodedata.normalize("NFC", unaccented))
    return letters, tone, vi


def missing_letters_ranked(
    missing_words: list[str],
    bank_letters: dict[str, list[dict]],
    bank_marks: dict[str, list[dict]],
    strict_case: bool = False,
    bank_digits: dict[str, list[dict]] | None = None,
    bank_punct: dict[str, list[dict]] | None = None,
    bank_symbols: dict[str, list[dict]] | None = None,
    bank_words: dict[str, list[dict]] | None = None,
) -> list[tuple[str, int, list[str]]]:
    """Xác định các chữ cái, dấu thanh, chữ số, dấu câu và ký hiệu còn thiếu để viết các từ trong missing_words,
    sắp xếp theo tần suất xuất hiện và khả năng mở khoá từ (greedy coverage).

    Args:
        missing_words: Danh sách các từ chưa có mẫu hoặc chưa ghép được.
        bank_letters: Từ điển chữ cái đã học trong kho.
        bank_marks: Từ điển dấu thanh đã có trong kho.
        strict_case: Nếu False, chữ hoa có thể dùng mẫu chữ thường nếu chưa có mẫu hoa.
        bank_digits: Từ điển chữ số đã có trong kho.
        bank_punct: Từ điển dấu câu đã có trong kho.
        bank_symbols: Từ điển ký hiệu toán học / đặc biệt đã có trong kho.
        bank_words: Từ điển từ nguyên khối đã có trong kho (hỗ trợ tra cứu fallback).

    Returns:
        [(ký_tự_hoặc_dấu, số_từ_mở_khoá, [danh_sách_từ_mở_khoá]), ...]
        được sắp xếp giảm dần theo số_từ_mở_khoá, rồi theo thứ tự bảng chữ cái.
    """
    digits = bank_digits or {}
    punct = bank_punct or {}
    symbols = bank_symbols or {}
    words_bank = bank_words or {}
    word_deps: dict[str, set[str]] = {}  # missing_char -> set of words needing it

    for w in missing_words:
        w_clean = w.strip()
        if not w_clean:
            continue
        if w_clean in words_bank and words_bank[w_clean]:
            continue

        letters, tone, _ = split_letters(w_clean)
        needed_in_word: set[str] = set()

        for ch in letters:
            has_sample = False
            if ch in bank_letters and bank_letters[ch]:
                has_sample = True
            elif not strict_case and ch.isupper() and ch.lower() in bank_letters and bank_letters[ch.lower()]:
                has_sample = True
            elif ch in digits and digits[ch]:
                has_sample = True
            elif ch in punct and punct[ch]:
                has_sample = True
            elif ch in symbols and symbols[ch]:
                has_sample = True
            elif ch in words_bank and words_bank[ch]:
                has_sample = True
            elif not strict_case and ch.isupper() and ch.lower() in words_bank and words_bank[ch.lower()]:
                has_sample = True

            if not has_sample:
                target_ch = ch if (strict_case or not ch.isupper()) else ch.lower()
                needed_in_word.add(target_ch)

        if tone:
            has_precomposed = False
            if w_clean in bank_letters and bank_letters[w_clean]:
                has_precomposed = True
            elif w_clean in words_bank and words_bank[w_clean]:
                has_precomposed = True
            elif len(letters) == 1:
                if letters[0] in bank_letters and bank_letters[letters[0]]:
                    has_precomposed = True
                elif letters[0] in words_bank and words_bank[letters[0]]:
                    has_precomposed = True

            if not has_precomposed:
                if not bank_marks.get(tone):
                    needed_in_word.add(tone)

        for req in needed_in_word:
            word_deps.setdefault(req, set()).add(w_clean)

    ranked: list[tuple[str, int, list[str]]] = []
    for ch, words_set in word_deps.items():
        w_list = sorted(words_set)
        ranked.append((ch, len(w_list), w_list))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked


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


PUNCT_CHARS = set(".,!?:;-\"'()[]{}/…“”‘’–—")


def is_symbol_label(label: str, known_symbols: Any = None) -> bool:
    """Xác định xem nhãn ô học có phải là ký hiệu toán học / glyph đặc biệt hay không."""
    if label.startswith("\\"):
        return True
    if known_symbols is not None:
        sym_set = known_symbols.symbols if hasattr(known_symbols, "symbols") else known_symbols
        if label in sym_set:
            return True
    if len(label) == 1:
        cat = unicodedata.category(label)
        if cat in ("Sm", "So", "Sk"):
            return True
        code = ord(label)
        if (0x0370 <= code <= 0x03FF) or (0x2190 <= code <= 0x22FF):
            return True
    return False


def classify_token(token: str, known_symbols: Any = None) -> str:
    """Phân loại nhãn token thành một trong các nhóm: 'digits', 'punct', 'symbols', hoặc 'words'."""
    t = token.strip()
    if not t:
        return "words"
    if t.isdigit() and len(t) == 1:
        return "digits"
    if is_symbol_label(t, known_symbols):
        return "symbols"
    if t in PUNCT_CHARS or (len(t) == 1 and not t.isalnum()):
        return "punct"
    return "words"


def sample_signature(strokes: list[Stroke]) -> str:
    """Tạo chữ ký băm (SHA-256) từ tọa độ nét vẽ đã làm tròn để phát hiện và khử trùng mẫu học trùng lặp."""
    import hashlib

    parts = []
    for s in strokes:
        parts.append(",".join(f"{round(coord, 2):.2f}" for coord in s))
    norm_repr = ";".join(parts)
    return hashlib.sha256(norm_repr.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ Chỉ số hình học & Chuẩn hoá chữ cái

CONTOUR_CURVED = "CURVED"
CONTOUR_STRAIGHT = "STRAIGHT"
CONTOUR_OPEN = "OPEN"

_LEFT_CURVED = set("cdeopqCDEGOPQ0689ăâêôơư" + "àáảãạèéẻẽẹòóỏõọồốổỗộờớởỡợùúủũụừứửữự")
_LEFT_STRAIGHT = set("bhijklmnruBHIJKLMNRU1" + "đĐìíỉĩị")

_RIGHT_CURVED = set("obpOPBD038ôơ" + "òóỏõọồốổỗộờớởỡợ")
_RIGHT_STRAIGHT = set("adhijlmnquHIMNU1" + "àáảãạìíỉĩịùúủũụ")


def classify_char_category(char: str) -> str:
    """Phân loại ký tự thành: 'x_height', 'ascender', 'descender', 'uppercase', 'digit', 'punct', 'symbol'."""
    if not char:
        return "x_height"
    ch = unicodedata.normalize("NFC", char)
    if len(ch) == 1 and ch.isdigit():
        return "digit"
    if ch in PUNCT_CHARS or (len(ch) == 1 and unicodedata.category(ch).startswith("P")):
        return "punct"
    if is_symbol_label(ch):
        return "symbol"
    if ch.isupper():
        return "uppercase"

    unaccented = strip_tone(ch).lower()
    if unaccented in ("b", "d", "đ", "h", "k", "l", "t"):
        return "ascender"
    if unaccented in ("g", "p", "q", "y"):
        return "descender"
    return "x_height"


def classify_left_contour(char: str) -> str:
    """Phân loại hình dạng đường biên bên trái của chữ cái ('CURVED', 'STRAIGHT', 'OPEN')."""
    ch = unicodedata.normalize("NFC", char)
    if ch in _LEFT_CURVED:
        return CONTOUR_CURVED
    if ch in _LEFT_STRAIGHT:
        return CONTOUR_STRAIGHT
    return CONTOUR_OPEN


def classify_right_contour(char: str) -> str:
    """Phân loại hình dạng đường biên bên phải của chữ cái ('CURVED', 'STRAIGHT', 'OPEN')."""
    ch = unicodedata.normalize("NFC", char)
    if ch in _RIGHT_CURVED:
        return CONTOUR_CURVED
    if ch in _RIGHT_STRAIGHT:
        return CONTOUR_STRAIGHT
    return CONTOUR_OPEN


def contour_pair_gap(left_c: str, right_c: str, xh: float = 7.94) -> float:
    """Tính khoảng hở quang học tự nhiên giữa 2 đường biên tiếp giáp của cặp chữ cái."""
    if left_c == CONTOUR_CURVED and right_c == CONTOUR_CURVED:
        return round(0.08 * xh, 2)
    if (left_c == CONTOUR_CURVED and right_c == CONTOUR_OPEN) or (left_c == CONTOUR_OPEN and right_c == CONTOUR_CURVED):
        return round(0.10 * xh, 2)
    if left_c == CONTOUR_OPEN and right_c == CONTOUR_OPEN:
        return round(0.12 * xh, 2)
    if (left_c == CONTOUR_STRAIGHT and right_c == CONTOUR_CURVED) or (left_c == CONTOUR_CURVED and right_c == CONTOUR_STRAIGHT):
        return round(0.14 * xh, 2)
    if (left_c == CONTOUR_STRAIGHT and right_c == CONTOUR_OPEN) or (left_c == CONTOUR_OPEN and right_c == CONTOUR_STRAIGHT):
        return round(0.15 * xh, 2)
    # STRAIGHT gặp STRAIGHT: khoảng cách lớn nhất để tránh dính nét
    return round(0.18 * xh, 2)


def compute_side_bearings(
    char: str,
    strokes: list[Stroke],
    w: float,
    xh: float = 7.94,
) -> tuple[float, float, float]:
    """Tính toán Left Side Bearing (lsb), Right Side Bearing (rsb) và Advance Width (adv)."""
    lc = classify_left_contour(char)
    rc = classify_right_contour(char)

    lsb = 0.04 * xh if lc == CONTOUR_CURVED else (0.06 * xh if lc == CONTOUR_OPEN else 0.08 * xh)
    rsb = 0.04 * xh if rc == CONTOUR_CURVED else (0.06 * xh if rc == CONTOUR_OPEN else 0.08 * xh)

    lsb = round(lsb, 2)
    rsb = round(rsb, 2)
    adv = round(w + lsb + rsb, 2)
    return lsb, rsb, adv


def normalize_letter_sample(
    char: str,
    strokes: list[Stroke],
    raw_w: float,
    raw_xh: float,
    target_xh: float = 7.94,
) -> dict[str, Any]:
    """Chuẩn hóa một mẫu chữ cái: co giãn đồng dạng theo x-height mục tiêu và neo chân chữ về y=0."""
    cat = classify_char_category(char)
    lc = classify_left_contour(char)
    rc = classify_right_contour(char)

    scale = target_xh / raw_xh if raw_xh > 0 else 1.0

    scaled_strokes: list[Stroke] = []
    all_ys: list[float] = []
    all_xs: list[float] = []

    for st in strokes:
        sc_st: list[float] = []
        for i in range(0, len(st) - 1, 2):
            x_val = st[i] * scale
            y_val = st[i + 1] * scale
            sc_st.extend([x_val, y_val])
            all_xs.append(x_val)
            all_ys.append(y_val)
        scaled_strokes.append(sc_st)

    if not all_xs or not all_ys:
        return {
            "s": strokes,
            "w": raw_w,
            "h": 0.0,
            "lsb": 0.0,
            "rsb": 0.0,
            "adv": raw_w,
            "cat": cat,
            "lc": lc,
            "rc": rc,
        }

    # Neo chân chữ:
    # Trong toạ độ .xopp/kho mẫu, y âm là hướng lên trên, y=0 là đường chân chữ (baseline)
    # Đối với chữ không có đuôi xuống (descender), toạ độ y lớn nhất (thấp nhất thị giác) neo về 0
    if cat != "descender":
        shift_y = -max(all_ys)
    else:
        # Với descender (g, p, q, y), phần thân chữ nằm trên y <= 0, phần đuôi vượt qua y > 0
        # Ước lượng đường chân chữ dựa trên đỉnh nét: baseline = min_y + target_xh
        shift_y = -(min(all_ys) + target_xh)

    # Shift to baseline y=0 và mép trái x=0
    shift_x = -min(all_xs)

    norm_strokes: list[Stroke] = []
    for st in scaled_strokes:
        norm_st: list[float] = []
        for i in range(0, len(st) - 1, 2):
            norm_st.append(round(st[i] + shift_x, 2))
            norm_st.append(round(st[i + 1] + shift_y, 2))
        norm_strokes.append(norm_st)

    norm_xs = [norm_st[i] for norm_st in norm_strokes for i in range(0, len(norm_st) - 1, 2)]
    norm_ys = [norm_st[i + 1] for norm_st in norm_strokes for i in range(0, len(norm_st) - 1, 2)]

    norm_w = round(max(norm_xs) - min(norm_xs), 2)
    norm_h = round(max(norm_ys) - min(norm_ys), 2)

    lsb, rsb, adv = compute_side_bearings(char, norm_strokes, norm_w, xh=target_xh)

    return {
        "s": norm_strokes,
        "w": norm_w,
        "h": norm_h,
        "lsb": lsb,
        "rsb": rsb,
        "adv": adv,
        "cat": cat,
        "lc": lc,
        "rc": rc,
    }


def min_stroke_clearance(
    strokes_a: list[Stroke],
    strokes_b: list[Stroke],
    max_pts: int = 25,
) -> float:
    """Tính khoảng cách Euclid nhỏ nhất giữa 2 tập hợp nét vẽ phẳng [x0,y0, x1,y1...].

    Tối ưu hóa: chỉ so sánh tập con điểm biên phải của `strokes_a` với tập con điểm biên trái
    của `strokes_b` để đạt hiệu năng < 0.05ms trong pure Python mà không cần numpy.
    """
    pts_a: list[tuple[float, float]] = []
    for st in strokes_a:
        for i in range(0, len(st) - 1, 2):
            pts_a.append((st[i], st[i + 1]))

    pts_b: list[tuple[float, float]] = []
    for st in strokes_b:
        for i in range(0, len(st) - 1, 2):
            pts_b.append((st[i], st[i + 1]))

    if not pts_a or not pts_b:
        return 999.0

    max_xa = max(p[0] for p in pts_a)
    subset_a = [p for p in pts_a if p[0] >= max_xa - 4.0]
    if len(subset_a) > max_pts:
        subset_a = sorted(subset_a, key=lambda p: -p[0])[:max_pts]

    min_xb = min(p[0] for p in pts_b)
    subset_b = [p for p in pts_b if p[0] <= min_xb + 4.0]
    if len(subset_b) > max_pts:
        subset_b = sorted(subset_b, key=lambda p: p[0])[:max_pts]

    min_dist_sq = 1e9
    for xa, ya in subset_a:
        for xb, yb in subset_b:
            dx = xb - xa
            dy = yb - ya
            d_sq = dx * dx + dy * dy
            if d_sq < min_dist_sq:
                min_dist_sq = d_sq

    return round(math.sqrt(min_dist_sq), 2) if min_dist_sq < 1e8 else 999.0


def get_vector_glyph_fallback(token: str, xh: float = 7.94) -> dict[str, Any] | None:
    """Sinh nét vector dự phòng cho các ký hiệu lập trình / toán học phổ biến khi kho chưa có mẫu."""
    t = token.strip()
    if not t:
        return None

    if t == "_":
        # Underscore: nét ngang sát chân chữ hoặc hơi dưới baseline
        w = round(0.6 * xh, 2)
        s = [[0.0, round(0.15 * xh, 2), w, round(0.15 * xh, 2)]]
        return {"s": s, "w": w, "h": 0.5, "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == "-":
        w = round(0.5 * xh, 2)
        y = round(-0.5 * xh, 2)
        s = [[0.0, y, w, y]]
        return {"s": s, "w": w, "h": 0.5, "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t in ("--", "–"):
        w = round(1.0 * xh, 2)
        y = round(-0.5 * xh, 2)
        s = [[0.0, y, w, y]]
        return {"s": s, "w": w, "h": 0.5, "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t in ("---", "—"):
        w = round(1.8 * xh, 2)
        y = round(-0.5 * xh, 2)
        s = [[0.0, y, w, y]]
        return {"s": s, "w": w, "h": 0.5, "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == "<":
        w = round(0.6 * xh, 2)
        top_y = round(-0.85 * xh, 2)
        mid_y = round(-0.5 * xh, 2)
        bot_y = round(-0.15 * xh, 2)
        s = [[w, top_y, 0.0, mid_y, w, bot_y]]
        return {"s": s, "w": w, "h": round(0.7 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == ">":
        w = round(0.6 * xh, 2)
        top_y = round(-0.85 * xh, 2)
        mid_y = round(-0.5 * xh, 2)
        bot_y = round(-0.15 * xh, 2)
        s = [[0.0, top_y, w, mid_y, 0.0, bot_y]]
        return {"s": s, "w": w, "h": round(0.7 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == "<=":
        w = round(0.6 * xh, 2)
        top_y = round(-0.95 * xh, 2)
        mid_y = round(-0.6 * xh, 2)
        bot_y = round(-0.25 * xh, 2)
        bar_y = round(-0.05 * xh, 2)
        s = [[w, top_y, 0.0, mid_y, w, bot_y], [0.0, bar_y, w, bar_y]]
        return {"s": s, "w": w, "h": round(0.9 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == ">=":
        w = round(0.6 * xh, 2)
        top_y = round(-0.95 * xh, 2)
        mid_y = round(-0.6 * xh, 2)
        bot_y = round(-0.25 * xh, 2)
        bar_y = round(-0.05 * xh, 2)
        s = [[0.0, top_y, w, mid_y, 0.0, bot_y], [0.0, bar_y, w, bar_y]]
        return {"s": s, "w": w, "h": round(0.9 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == "=":
        w = round(0.6 * xh, 2)
        y1 = round(-0.65 * xh, 2)
        y2 = round(-0.35 * xh, 2)
        s = [[0.0, y1, w, y1], [0.0, y2, w, y2]]
        return {"s": s, "w": w, "h": round(0.3 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "symbol", "lc": "OPEN", "rc": "OPEN"}

    if t == "(":
        w = round(0.35 * xh, 2)
        top_y = round(-1.2 * xh, 2)
        mid_y = round(-0.5 * xh, 2)
        bot_y = round(0.2 * xh, 2)
        s = [[w, top_y, 0.05 * xh, mid_y, w, bot_y]]
        return {"s": s, "w": w, "h": round(1.4 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "punct", "lc": "OPEN", "rc": "OPEN"}

    if t == ")":
        w = round(0.35 * xh, 2)
        top_y = round(-1.2 * xh, 2)
        mid_y = round(-0.5 * xh, 2)
        bot_y = round(0.2 * xh, 2)
        s = [[0.0, top_y, 0.3 * xh, mid_y, 0.0, bot_y]]
        return {"s": s, "w": w, "h": round(1.4 * xh, 2), "lsb": 0.2, "rsb": 0.2, "adv": w + 0.4, "cat": "punct", "lc": "OPEN", "rc": "OPEN"}

    return None



