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
) -> list[tuple[str, int, list[str]]]:
    """Xác định các chữ cái và dấu thanh còn thiếu để viết các từ trong missing_words,
    sắp xếp theo tần suất xuất hiện và khả năng mở khoá từ (greedy coverage).

    Args:
        missing_words: Danh sách các từ chưa có mẫu hoặc chưa ghép được.
        bank_letters: Từ điển chữ cái đã học trong kho.
        bank_marks: Từ điển dấu thanh đã có trong kho.
        strict_case: Nếu False, chữ hoa có thể dùng mẫu chữ thường nếu chưa có mẫu hoa.

    Returns:
        [(ký_tự_hoặc_dấu, số_từ_mở_khoá, [danh_sách_từ_mở_khoá]), ...]
        được sắp xếp giảm dần theo số_từ_mở_khoá, rồi theo thứ tự bảng chữ cái.
    """
    word_deps: dict[str, set[str]] = {}  # missing_char -> set of words needing it

    for w in missing_words:
        w_clean = w.strip()
        if not w_clean:
            continue
        letters, tone, _ = split_letters(w_clean)
        needed_in_word: set[str] = set()

        for ch in letters:
            has_sample = False
            if ch in bank_letters and bank_letters[ch]:
                has_sample = True
            elif not strict_case and ch.isupper() and ch.lower() in bank_letters and bank_letters[ch.lower()]:
                has_sample = True

            if not has_sample:
                target_ch = ch if (strict_case or not ch.isupper()) else ch.lower()
                needed_in_word.add(target_ch)

        if tone:
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

