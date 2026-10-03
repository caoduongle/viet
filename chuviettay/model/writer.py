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
                 assemble_letters: bool = False,
                 letter_gap: float = 1.0,
                 pen_clearance_factor: float = 0.8):
        self.b = bank
        self.rnd = rnd
        self.J = jitter
        self.loose = loose_case
        self.space = space
        self.assemble_letters = assemble_letters
        self.letter_gap = letter_gap
        self.pen_clearance_factor = pen_clearance_factor
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

    def get_letter_sample(self, char: str) -> dict | None:
        """Tìm mẫu ký tự theo thứ tự ưu tiên đa tầng (cascade):
        1. bank.letters[char]
        2. bank.letters[char.lower()] (nếu loose và char viết hoa)
        3. bank.words[char] (nếu len(char) == 1)
        4. bank.words[char.lower()] (nếu loose, len(char) == 1 và char viết hoa)
        5. bank.digits[char] (nếu là chữ số)
        6. bank.punct[char] (nếu là dấu câu)
        7. bank.symbols[char] (nếu là ký hiệu)
        8. get_vector_glyph_fallback(char, xh) (nét vector dự phòng)
        """
        b = self.b
        if getattr(b, "letters", None) and char in b.letters:
            return self.pick(b.letters[char], "let:" + char)
        if self.loose and char.isupper() and getattr(b, "letters", None) and char.lower() in b.letters:
            return self.pick(b.letters[char.lower()], "let:" + char.lower())

        if len(char) == 1 and char in b.words:
            return self.pick(b.words[char], char)
        if self.loose and char.isupper() and len(char) == 1 and char.lower() in b.words:
            return self.pick(b.words[char.lower()], char.lower())

        if getattr(b, "digits", None) and char in b.digits:
            return self.pick(b.digits[char], "d" + char)

        if getattr(b, "punct", None) and char in b.punct:
            return self.pick(b.punct[char], "p" + char)

        if getattr(b, "symbols", None) and char in b.symbols:
            return self.pick(b.symbols[char], "sym:" + char)

        xh = getattr(b, "xh", 7.94)
        from chuviettay.model.text_utils import get_vector_glyph_fallback
        fb = get_vector_glyph_fallback(char, xh=xh)
        if fb:
            return fb

        return None

    def assemble_word(self, core: str) -> tuple[list[Stroke], float] | None:
        """Ghép MỘT từ từ các mẫu chữ cái đơn lẻ, hỗ trợ Dual-Path (mẫu nguyên chữ hoặc phân rã dấu thanh),
        tính khoảng cách quang học biên (contour kerning) và bảo đảm sàn khe hở vật lý (clearance floor)."""
        import unicodedata
        from chuviettay.model.text_utils import (
            classify_left_contour,
            classify_right_contour,
            contour_pair_gap,
            min_stroke_clearance,
            split_letters,
        )

        core_clean = core.strip()
        if not core_clean:
            return None

        xh = getattr(self.b, "xh", 7.94)
        pen_w = float(self.b.pen.get("width", 1.41)) if self.b.pen else 1.41
        clearance_floor = self.pen_clearance_factor * pen_w

        # --- DUAL-PATH RESOLUTION ---
        # Path 1: Thử tìm mẫu cho tất cả các ký tự nguyên khối (kể cả ký tự có dấu như 'à', 'ế')
        nfc_chars = list(unicodedata.normalize("NFC", core_clean))
        path1_samples: list[dict] = []
        path1_ok = True
        for ch in nfc_chars:
            s = self.get_letter_sample(ch)
            if s:
                path1_samples.append(s)
            else:
                path1_ok = False
                break

        use_path1 = path1_ok and len(path1_samples) == len(nfc_chars)

        if use_path1:
            chars_to_place = nfc_chars
            samples_to_place = path1_samples
            T, vi = "", -1
        else:
            # Path 2: Phân tách dấu thanh rời (decomposed)
            letters, T, vi = split_letters(core_clean)
            if not letters:
                return None
            if T and not self.b.marks.get(T):
                return None

            path2_samples = []
            for ch in letters:
                s = self.get_letter_sample(ch)
                if not s:
                    return None
                path2_samples.append(s)

            chars_to_place = letters
            samples_to_place = path2_samples

        # --- GHÉP NÉT VÀ ĐỊNH VỊ (PLACEMENT & KERNING) ---
        body_strokes: list[Stroke] = []
        cur_x = 0.0
        vowel_strokes_placed: list[Stroke] = []
        vowel_cx = 0.0
        prev_placed_strokes: list[Stroke] = []

        for idx, (ch, inst) in enumerate(zip(chars_to_place, samples_to_place)):
            w = inst.get("w", 1.0 * xh)
            ch_strokes = list(inst.get("s", []))

            # Hiệu chỉnh chân chữ cho ký tự có dấu nặng ở Path 1 (nếu kho mẫu bị neo nhầm dấu nặng về baseline y=0)
            if use_path1 and len(ch_strokes) >= 2:
                ch_T, _, _, _ = tone_info(ch)
                if ch_T == NANG:
                    bbs = [bbox(st) for st in ch_strokes]
                    ti = max(range(len(ch_strokes)), key=lambda k: bbs[k][3])
                    body_max_y = max((pt for k, st in enumerate(ch_strokes) if k != ti for pt in st[1::2]), default=0.0)
                    if body_max_y < -0.2 * xh:
                        dy_align = -body_max_y
                        ch_strokes = [shift(st, 0.0, dy_align) for st in ch_strokes]

            # Dot suppression cho chữ i/j khi có dấu thanh phía trên (Path 2)
            if not use_path1 and idx == vi and ch in ("i", "j") and T and T != NANG:
                clean_strokes = []
                for st in ch_strokes:
                    bb = bbox(st)
                    st_h = bb[3] - bb[1]
                    st_w = bb[2] - bb[0]
                    is_dot = (bb[3] < -0.75 * xh and st_h < 0.45 * xh and st_w < 0.55 * xh)
                    if not is_dot:
                        clean_strokes.append(st)
                ch_strokes = clean_strokes or ch_strokes

            # Ký tự đầu tiên
            if idx == 0:
                placed = [shift(st, cur_x, 0.0) for st in ch_strokes]
                body_strokes.extend(placed)
                prev_placed_strokes = placed
                if idx == vi:
                    vowel_strokes_placed = placed
                    vowel_cx = cur_x + w / 2.0
                continue

            # Tính khoảng cách tiến (advance)
            prev_ch = chars_to_place[idx - 1]
            prev_inst = samples_to_place[idx - 1]
            prev_w = prev_inst.get("w", 1.0 * xh)

            rc_prev = prev_inst.get("rc") or classify_right_contour(prev_ch)
            rsb_prev = prev_inst.get("rsb")
            if rsb_prev is None:
                rsb_prev = 0.04 * xh if rc_prev == "CURVED" else (0.06 * xh if rc_prev == "OPEN" else 0.08 * xh)

            lc_curr = inst.get("lc") or classify_left_contour(ch)
            lsb_curr = inst.get("lsb")
            if lsb_curr is None:
                lsb_curr = 0.04 * xh if lc_curr == "CURVED" else (0.06 * xh if lc_curr == "OPEN" else 0.08 * xh)

            pair_gap = contour_pair_gap(rc_prev, lc_curr, xh=xh) * self.letter_gap
            advance = prev_w + rsb_prev + pair_gap + lsb_curr

            if self.J > 0 and self.rnd:
                jitter_amt = self.rnd.uniform(-0.015 * self.J * xh, 0.015 * self.J * xh)
                advance += jitter_amt

            candidate_x = cur_x + advance
            candidate_placed = [shift(st, candidate_x, 0.0) for st in ch_strokes]

            # Cưỡng chế sàn khe hở vật lý (Clearance Floor)
            if prev_placed_strokes and candidate_placed:
                dist = min_stroke_clearance(prev_placed_strokes, candidate_placed)
                if dist < clearance_floor:
                    nudge = clearance_floor - dist
                    candidate_x += nudge
                    candidate_placed = [shift(st, candidate_x, 0.0) for st in ch_strokes]
                    advance += nudge

            body_strokes.extend(candidate_placed)
            prev_placed_strokes = candidate_placed
            cur_x = candidate_x

            if idx == vi:
                vowel_strokes_placed = candidate_placed
                vowel_cx = cur_x + w / 2.0

        last_w = samples_to_place[-1].get("w", 1.0 * xh)
        total_w = cur_x + last_w

        # Gắn dấu thanh rời (Path 2)
        if not use_path1 and T and vi >= 0:
            m = self.pick(self.b.marks[T], "m" + T)
            cx = vowel_cx + m.get("dx", 0.0)
            target_strokes = vowel_strokes_placed or body_strokes
            if T == NANG:
                cy = max(0.0, near_extreme(target_strokes, cx, max)) + m.get("dy", 0.2 * xh)
                if cy < 0.2 * xh:
                    cy = 0.25 * xh
            else:
                top_v = near_extreme(target_strokes, cx, min)
                cy = top_v + m.get("dy", -0.25 * xh)
                if cy > top_v - 0.2 * xh:
                    cy = top_v - 0.25 * xh

            m_strokes = m.get("s", [])
            placed_mark = [shift(st, cx, cy) for st in m_strokes]

            if body_strokes and placed_mark:
                dist_mark = min_stroke_clearance(body_strokes, placed_mark)
                if dist_mark < clearance_floor:
                    cy -= (clearance_floor - dist_mark)
                    placed_mark = [shift(st, cx, cy) for st in m_strokes]

            body_strokes.extend(placed_mark)

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

    def _punct_w(self, inst: dict) -> float:
        w = inst.get("w")
        if w is not None:
            return float(w)
        sts = inst.get("s", [])
        if sts:
            return max((st[i] for st in sts for i in range(0, len(st), 2)), default=0.0) + 0.3
        return 0.3

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
            return list(inst["s"]), self._punct_w(inst), []
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
                x += self._punct_w(inst) + 0.15 * b.xh
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
