"""
Writer -- thuật toán lõi: ghép một TOKEN (từ / số / dấu câu / cụm) thành danh sách nét
viết tay, tra cứu từ Bank.

Đây là phần thuật toán "nhạy cảm" nhất của cả ứng dụng (nhiều heuristic tinh chỉnh qua
thời gian) nên giữ NGUYÊN 100% logic từ bản gốc (hw_note.py) -- chỉ thêm type hint và
tách nhỏ docstring cho từng bước, không đổi bất kỳ công thức/hằng số/thứ tự điều kiện
nào. Đổi bất kỳ chi tiết nào ở đây đều có thể làm sai lệch cách ghép dấu thanh cho các
từ đã học trước đó.
"""
from __future__ import annotations

import random

from chuviettay.config import NANG, NUMRE, TOKRE
from chuviettay.model.bank import Bank
from chuviettay.model.text_utils import Stroke, bbox, clamp, near_extreme, shift, strip_tone, tone_info, vowel_x, weight


class Writer:
    """Một phiên ghép chữ cho MỘT lần "write" (giữ self.last để né chọn trùng mẫu 2
    lần liên tiếp cho cùng một token, và self.missing để gom các phần chưa có mẫu)."""

    def __init__(self, bank: Bank, rnd: random.Random, jitter: float = 1.0,
                 loose_case: bool = True, space: float = 1.0,
                 assemble_letters: bool = False):
        self.b = bank
        self.rnd = rnd
        self.J = jitter
        self.loose = loose_case
        self.space = space
        self.assemble_letters = assemble_letters
        self.last: dict[str, int] = {}       # tag -> chỉ số mẫu chọn lần trước (né lặp)
        self.missing: dict[str, int] = {}     # phần chưa có mẫu -> số lần gặp
        self.assembled: list[str] = []        # các từ đã ghép tự động từ chữ cái

    def pick(self, lst: list, tag: str):
        """Chọn ngẫu nhiên 1 phần tử trong `lst`, né KHÔNG chọn trùng chỉ số đã chọn
        lần trước cho cùng `tag` (nếu có hơn 1 lựa chọn) -- để cùng một từ xuất hiện
        nhiều lần trong văn bản không bị lặp y hệt nét viết liên tiếp."""
        i = self.rnd.randrange(len(lst))
        if len(lst) > 1 and self.last.get(tag) == i:
            i = (i + 1 + self.rnd.randrange(len(lst) - 1)) % len(lst)
        self.last[tag] = i
        return lst[i]

    # -- một từ tiếng Việt
    def word(self, core: str) -> tuple[list[Stroke], float] | None:
        """Ghép MỘT từ (đã tách khỏi số/dấu câu bao quanh). Thử khớp thẳng (kể cả biến
        thể hạ chữ hoa đầu nếu loose_case), rồi mới thử ghép thân-chữ + dấu-thanh-rời
        (substitute), rồi thử ghép từ các chữ cái mẫu (assemble_word).
        None nếu hoàn toàn chưa có mẫu nào dùng được."""
        variants = [core]
        if self.loose and core[:1].isupper():
            variants.append(core[:1].lower() + core[1:])
        for c in variants:
            if c in self.b.words:
                inst = self.pick(self.b.words[c], c)
                return inst["s"], inst["w"]
        for c in variants:
            r = self.substitute(c)
            if r:
                return r
        if self.assemble_letters:
            for c in variants:
                r = self.assemble_word(c)
                if r:
                    self.assembled.append(core)
                    return r
        return None

    def assemble_word(self, core: str) -> tuple[list[Stroke], float] | None:
        """Ghép MỘT từ tiếng Việt từ các mẫu chữ cái đơn lẻ trong bank.letters và dấu thanh rời trong bank.marks."""
        from chuviettay.model.text_utils import split_letters

        letters, T, vi = split_letters(core)
        if not letters:
            return None

        if T and not self.b.marks.get(T):
            return None

        xh = getattr(self.b, "xh", 7.0)
        overlap = max(0.3, min(1.2, 0.08 * xh))
        cur_x = 0.0
        body_strokes: list[Stroke] = []
        vowel_cx = 0.0

        for idx, ch in enumerate(letters):
            lib = None
            if getattr(self.b, "letters", None) and ch in self.b.letters:
                lib = self.b.letters[ch]
            elif self.loose and ch.isupper() and getattr(self.b, "letters", None) and ch.lower() in self.b.letters:
                lib = self.b.letters[ch.lower()]
            elif len(ch) == 1 and ch in self.b.words:
                lib = self.b.words[ch]
            elif self.loose and ch.isupper() and len(ch) == 1 and ch.lower() in self.b.words:
                lib = self.b.words[ch.lower()]

            if not lib:
                return None

            inst = self.pick(lib, "let:" + ch)
            w = inst.get("w", 1.0 * xh)
            ch_strokes = inst.get("s", [])

            if idx == vi and ch == "i" and T and T != NANG:
                clean_strokes = []
                for st in ch_strokes:
                    bb = bbox(st)
                    is_dot = (bb[3] < -0.85 * xh and (bb[2] - bb[0]) < 0.6 * xh)
                    if not is_dot:
                        clean_strokes.append(st)
                ch_strokes = clean_strokes or ch_strokes

            placed = [shift(st, cur_x, 0) for st in ch_strokes]
            body_strokes.extend(placed)

            if idx == vi:
                vowel_cx = cur_x + w / 2.0

            advance = max(0.2 * xh, w - overlap)
            if self.J > 0 and self.rnd:
                advance += self.rnd.uniform(-0.02 * self.J * xh, 0.02 * self.J * xh)
            cur_x += advance

        total_w = cur_x + overlap

        if T and vi >= 0:
            m = self.pick(self.b.marks[T], "m" + T)
            cx = vowel_cx + m.get("dx", 0.0)
            if T == NANG:
                cy = max(0.0, near_extreme(body_strokes, cx, max)) + m.get("dy", 0.0)
            else:
                cy = near_extreme(body_strokes, cx, min) + m.get("dy", 0.0)
            for st in m.get("s", []):
                body_strokes.append(shift(st, cx, cy))

        return body_strokes, total_w

    def substitute(self, c: str) -> tuple[list[Stroke], float] | None:
        """Chưa có mẫu cho ĐÚNG từ `c`, nhưng có thể đã có mẫu cho từ khác cùng phần
        thân (bỏ dấu thanh) + có nét dấu thanh rời phù hợp đã "gặt" được (bank.marks)
        -- ghép 2 phần đó lại. Nếu nguyên âm mang dấu là "i" thì bỏ chấm trên đầu chữ i
        gốc trước khi gắn dấu thanh vào (tránh chồng 2 dấu)."""
        T, vi, hats, letters = tone_info(c)
        lst = self.b.tl.get(strip_tone(c))
        if not lst or (T and not self.b.marks.get(T)):
            return None
        _, inst = self.pick(lst, "tl:" + strip_tone(c))
        body = [st for k, st in enumerate(inst["s"]) if k != inst.get("ti", -1)]
        w = inst["w"]
        if T and vi >= 0:
            m = self.pick(self.b.marks[T], "m" + T)
            xv = vowel_x(letters, vi, w)
            cx = xv + m["dx"]
            if T == NANG:
                cy = max(0.0, near_extreme(body, cx, max)) + m["dy"]
            else:
                if letters[vi] == "i":        # có dấu trên thì bỏ chấm của chữ i
                    xh = self.b.xh
                    dots = [k for k, st in enumerate(body) if bbox(st)[3] < -0.9 * xh
                            and bbox(st)[2] - bbox(st)[0] < 5 and abs((bbox(st)[0] + bbox(st)[2]) / 2 - xv) < 4]
                    if dots:
                        body = [st for k, st in enumerate(body) if k != dots[0]]
                cy = near_extreme(body, cx, min) + m["dy"]
            body = body + [shift(m["s"][0], cx, cy)]
        return body, w

    # -- số
    def number(self, s: str) -> tuple[list[Stroke], float, list[str]]:
        """Ghép một chuỗi số/dấu chấm-phẩy-gạch ngang (đã khớp NUMRE), từng ký tự một,
        theo mẫu chữ số/dấu phẩy-chấm đã học. -> (nét, độ rộng, ký tự còn thiếu mẫu)."""
        b, rnd = self.b, self.rnd
        out: list[Stroke] = []
        x, missing, first = 0.0, [], True
        gaps = b.d.get("dgaps") or [3.5]
        for ch in s:
            if ch in ",.":
                lib = b.punct.get(ch) or b.punct.get(",") or b.punct.get(".") or b.words.get(ch)
                if not lib:
                    missing.append(ch)
                    continue
                g = self.pick(lib, "p" + ch)
                out += [shift(st, x, 0) for st in g["s"]]
                x += max(st[i] for st in g["s"] for i in range(0, len(st), 2)) + 0.6
                first = True
                continue
            lib = b.digits.get(ch) or b.words.get(ch)
            if not lib:
                missing.append(ch)
                continue
            g = self.pick(lib, "d" + ch)
            gap = 0.0 if first else clamp(rnd.choice(gaps), 0.5, 7.0) * (0.5 if ch == "-" else 1.0)
            out += [shift(st, x + gap, 0) for st in g["s"]]
            x += gap + g["w"]
            first = False
        return out, x, missing

    def symbol(self, sym: str) -> tuple[list[Stroke], float, list[str]]:
        """Ghép một ký hiệu toán học / glyph đặc biệt từ bank.symbols.
        Nếu chưa có mẫu, trả về ([], fallback_width, [sym])."""
        b = self.b
        if getattr(b, "symbols", None) and sym in b.symbols:
            inst = self.pick(b.symbols[sym], "sym:" + sym)
            return list(inst["s"]), inst["w"], []
        fallback_w = 0.8 * getattr(b, "xh", 10.0)
        return [], fallback_w, [sym]

    # -- một token (đã tách khoảng trắng)
    def token(self, tok: str) -> tuple[list[Stroke], float, list[str]]:
        """Ghép một token (đã tách theo khoảng trắng, có thể còn kèm dấu ngoặc/dấu câu
        bao quanh) thành nét viết tay. -> (nét, độ rộng, danh sách phần còn thiếu mẫu).

        Thử khớp NGUYÊN token trước (ví dụ cụm "cà phê" đã dạy như một nhãn); nếu
        không có mới tách ra lead (dấu mở ngoặc/nháy đầu) + core (phần thân: số hoặc
        từ) + trail (dấu đóng ngoặc/dấu câu cuối) rồi ghép từng phần."""
        b = self.b
        if tok in b.words:
            inst = self.pick(b.words[tok], tok)
            return list(inst["s"]), inst["w"], []
        if getattr(b, "digits", None) and tok in b.digits:
            inst = self.pick(b.digits[tok], "d" + tok)
            return list(inst["s"]), inst["w"], []
        if getattr(b, "punct", None) and tok in b.punct:
            inst = self.pick(b.punct[tok], "p" + tok)
            return list(inst["s"]), inst["w"], []
        if getattr(b, "symbols", None) and tok in b.symbols:
            inst = self.pick(b.symbols[tok], "sym:" + tok)
            return list(inst["s"]), inst["w"], []
        lead, core, trail = TOKRE.match(tok).groups()
        strokes: list[Stroke] = []
        x, miss = 0.0, []
        for ch in lead:
            if ch in b.words:
                inst = self.pick(b.words[ch], ch)
                strokes += [shift(st, x, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * b.xh
            elif getattr(b, "punct", None) and ch in b.punct:
                inst = self.pick(b.punct[ch], "p" + ch)
                strokes += [shift(st, x, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * b.xh
            elif getattr(b, "symbols", None) and ch in b.symbols:
                inst = self.pick(b.symbols[ch], "sym:" + ch)
                strokes += [shift(st, x, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * b.xh
            else:
                miss.append(ch)
        if core:
            if NUMRE.match(core):
                st, w, m = self.number(core)
                miss += m
            else:
                r = self.word(core)
                if r:
                    st, w = r
                    m = []
                else:
                    st, w, m = [], weight(core) * b.d.get("ratio", 6.6), [core]
                miss += m
            strokes += [shift(s_, x, 0) for s_ in st]
            x += w
        for ch in trail:
            lib = b.punct.get(ch)
            if lib:
                g = self.pick(lib, "p" + ch)
                strokes += [shift(st, x, 0) for st in g["s"]]
                x += max(st[i] for st in g["s"] for i in range(0, len(st), 2)) + 0.3
            elif ch in b.words:
                inst = self.pick(b.words[ch], ch)
                strokes += [shift(st, x + 0.15 * b.xh, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * b.xh
            elif getattr(b, "symbols", None) and ch in b.symbols:
                inst = self.pick(b.symbols[ch], "sym:" + ch)
                strokes += [shift(st, x + 0.15 * b.xh, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * b.xh
            else:
                miss.append(ch)
        if not core and not lead and trail == tok and (
            tok not in b.words
            and tok not in getattr(b, "punct", {})
            and tok not in getattr(b, "digits", {})
            and tok not in getattr(b, "symbols", {})
        ):
            miss = [tok]
        return strokes, x, miss
