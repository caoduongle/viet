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
from chuviettay.model.text_utils import (
    Stroke,
    bbox,
    clamp,
    near_extreme,
    shift,
    split_letters,
    tone_info,
    weight,
)


class Writer:
    """Một phiên ghép chữ cho MỘT lần "write" (giữ self.last để né chọn trùng mẫu 2
    lần liên tiếp cho cùng một token, và self.missing để gom các phần chưa có mẫu)."""

    def __init__(self, bank: Bank, rnd: random.Random | None = None, jitter: float = 1.0,
                 loose_case: bool = True, space: float = 1.0,
                 assemble_letters: bool = True,
                 letter_gap: float = 1.0,
                 pen_clearance_factor: float = 0.8,
                 stable_variants: bool = False,
                 seed: int | None = None):
        self.b = bank
        self.rnd = rnd if rnd is not None else random.Random(seed)
        self.J = jitter
        self.loose = loose_case
        self.space = space
        self.assemble_letters = assemble_letters
        self.letter_gap = letter_gap
        self.pen_clearance_factor = pen_clearance_factor
        self.stable_variants = stable_variants
        self.seed = seed
        self.counts: dict[str, int] = {}
        self.last: dict[str, int] = {}       # tag -> chỉ số mẫu chọn lần trước (né lặp)
        self.missing: dict[str, int] = {}     # phần chưa có mẫu -> số lần gặp
        self.assembled: list[str] = []        # các từ đã ghép tự động từ chữ cái

    def pick(self, lst: list, tag: str):
        """Chọn ngẫu nhiên 1 phần tử trong `lst`, né KHÔNG chọn trùng chỉ số đã chọn
        lần trước cho cùng `tag` (nếu có hơn 1 lựa chọn) -- để cùng một từ xuất hiện
        nhiều lần trong văn bản không bị lặp y hệt nét viết liên tiếp."""
        if not lst:
            return None
        if self.stable_variants:
            import hashlib
            tag_count = self.counts.get(tag, 0)
            self.counts[tag] = tag_count + 1
            seed_val = self.seed if self.seed is not None else 0
            digest = hashlib.sha256(f"{seed_val}\x00{tag}\x00{tag_count}".encode("utf-8")).digest()
            i = int.from_bytes(digest[:4], "big") % len(lst)
            if len(lst) > 1 and self.last.get(tag) == i:
                extra = int.from_bytes(digest[4:8], "big") % (len(lst) - 1)
                i = (i + 1 + extra) % len(lst)
        else:
            i = self.rnd.randrange(len(lst))
            if len(lst) > 1 and self.last.get(tag) == i:
                i = (i + 1 + self.rnd.randrange(len(lst) - 1)) % len(lst)
        self.last[tag] = i
        return lst[i]

    # -- một từ tiếng Việt
    def word(self, core: str) -> tuple[list[Stroke], float] | None:
        """Ghép MỘT từ (đã tách khỏi số/dấu câu bao quanh).
        Theo R1: Nếu từ chứa ký tự chữ cái và bật assemble_letters, ưu tiên ghép từ các chữ cái mẫu (assemble_word).
        Nếu không có đủ chữ cái mẫu (hoặc không chứa ký tự chữ cái, ví dụ ký hiệu toán học / kho cũ),
        thử khớp thẳng (kể cả biến thể hạ chữ hoa đầu nếu loose_case), rồi mới thử ghép thân-chữ + dấu-thanh-rời (substitute).
        None nếu hoàn toàn chưa có mẫu nào dùng được."""
        variants = [core]
        if self.loose and core[:1].isupper():
            variants.append(core[:1].lower() + core[1:])

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

        if getattr(b, "digits", None) and char in b.digits:
            return self.pick(b.digits[char], "d" + char)

        if getattr(b, "punct", None) and char in b.punct:
            return self.pick(b.punct[char], "p" + char)

        if getattr(b, "symbols", None) and char in b.symbols:
            return self.pick(b.symbols[char], "sym:" + char)

        xh = getattr(b, "xh", 7.94)
        from chuviettay.model.text_utils import get_vector_glyph_fallback
        # Không sinh nét vector dự phòng cho các toán tử số học/quan hệ như '+', '-', '=' khi tìm mẫu chữ cái
        # để nhường chỗ cho MathLayoutEngine và punct xử lý tự nhiên.
        if char not in "+-=<>/*":
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
            else:
                rsb_prev = min(rsb_prev, 0.3 * xh)

            lc_curr = inst.get("lc") or classify_left_contour(ch)
            lsb_curr = inst.get("lsb")
            if lsb_curr is None:
                lsb_curr = 0.04 * xh if lc_curr == "CURVED" else (0.06 * xh if lc_curr == "OPEN" else 0.08 * xh)
            else:
                lsb_curr = min(lsb_curr, 0.3 * xh)

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
                    nudge = clearance_floor - dist_mark
                    if T == NANG:
                        cy += nudge
                    else:
                        cy -= nudge
                    placed_mark = [shift(st, cx, cy) for st in m_strokes]

            body_strokes.extend(placed_mark)

        return body_strokes, total_w

    # -- số
    def _resolve_dgap(self, first: bool, is_hyphen: bool = False) -> float:
        """Tính khoảng cách tự nhiên giữa 2 chữ số liên tiếp trong cùng một số,
        được chuẩn hóa theo tỷ lệ chiều cao chữ xh và chống giãn cách quá xa."""
        if first:
            return 0.0
        b, rnd = self.b, self.rnd
        xh = getattr(b, "xh", 7.94) or 7.94
        raw_gaps = b.d.get("dgaps")
        # Lọc các khoảng cách hợp lý (tương tự như cách engine lọc wgaps: 6.0 <= g <= 20.0)
        # Đối với chữ số: dgap chỉ nên trong khoảng 0.5 đến 0.55 * xh (tối đa ~3.8 khi xh=7.0, ~4.3 khi xh=7.94)
        valid_gaps = [float(g) for g in raw_gaps if 0.5 <= float(g) <= 0.55 * xh] if raw_gaps else []
        if valid_gaps:
            gap = rnd.choice(valid_gaps)
        elif raw_gaps:
            # Nếu toàn bộ mẫu trong kho đều quá lớn (ví dụ kho cũ bị outlier > 5.0), clamp về dải an toàn
            min_dgap = 0.08 * xh
            max_dgap = 0.22 * xh
            g_raw = rnd.choice(raw_gaps)
            scaled = float(g_raw) * (xh / 7.94)
            gap = clamp(scaled, min_dgap, max_dgap)
        else:
            gap = 0.14 * xh
        return gap * (0.5 if is_hyphen else 1.0)

    def _normalize_punct_sample(self, inst: dict) -> tuple[list[Stroke], float]:
        """Chuẩn hóa mẫu dấu câu về gốc x = 0.0, trả về (danh sách nét đã dịch, độ rộng thực tế)."""
        raw_s = inst.get("s", [])
        if not raw_s:
            return [], float(inst.get("w", 0.3))
        xs = [pt for st in raw_s for pt in st[0::2]]
        if not xs:
            return [], float(inst.get("w", 0.3))
        min_x = min(xs)
        max_x = max(xs)
        norm_strokes = [shift(st, -min_x, 0.0) for st in raw_s]
        glyph_w = max_x - min_x
        w_field = inst.get("w")
        if w_field is not None and float(w_field) > glyph_w:
            effective_w = float(w_field)
        else:
            effective_w = glyph_w
        return norm_strokes, effective_w

    def number(self, s: str) -> tuple[list[Stroke], float, list[str]]:
        """Ghép một chuỗi số/dấu chấm-phẩy-gạch ngang (đã khớp NUMRE), từng ký tự một,
        theo mẫu chữ số/dấu phẩy-chấm đã học. -> (nét, độ rộng, ký tự còn thiếu mẫu)."""
        b = self.b
        xh = getattr(b, "xh", 7.94) or 7.94
        out: list[Stroke] = []
        x, missing, first = 0.0, [], True
        for ch in s:
            if ch in ",.":
                lib = b.punct.get(ch) or b.punct.get(",") or b.punct.get(".")
                if not lib:
                    missing.append(ch)
                    continue
                g = self.pick(lib, "p" + ch)
                p_st, p_w = self._normalize_punct_sample(g)
                # Dấu phẩy/chấm nằm ngay sau chữ số trước với khoảng hở nhỏ
                p_gap = 0.08 * xh if not first else 0.0
                out += [shift(st, x + p_gap, 0) for st in p_st]
                x += p_gap + p_w + 0.10 * xh
                first = True
                continue
            lib = b.digits.get(ch)
            if not lib and getattr(b, "words", None) and ch in b.words:
                lib = b.words[ch]
            if not lib:
                missing.append(ch)
                continue
            g = self.pick(lib, "d" + ch)
            gap = self._resolve_dgap(first, is_hyphen=(ch == "-"))
            d_st, d_w = self._normalize_punct_sample(g)
            out += [shift(st, x + gap, 0) for st in d_st]
            w_advance = float(g.get("w", d_w))
            x += gap + w_advance
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
            xs = [st[i] for st in sts for i in range(0, len(st), 2)]
            return (max(xs) - min(xs)) + 0.3 if xs else 0.3
        return 0.3

    # -- một token (đã tách khoảng trắng)
    def token(self, tok: str) -> tuple[list[Stroke], float, list[str]]:
        """Ghép một token (đã tách theo khoảng trắng, có thể còn kèm dấu ngoặc/dấu câu
        bao quanh) thành nét viết tay. -> (nét, độ rộng, danh sách phần còn thiếu mẫu).

        Thử khớp NGUYÊN token trước (ví dụ cụm "cà phê" đã dạy như một nhãn); nếu
        không có mới tách ra lead (dấu mở ngoặc/nháy đầu) + core (phần thân: số hoặc
        từ) + trail (dấu đóng ngoặc/dấu câu cuối) rồi ghép từng phần."""
        b = self.b
        xh = getattr(b, "xh", 7.94) or 7.94
        pen_w = float(b.pen.get("width", 1.41)) if b.pen else 1.41

        if len(tok) == 1:
            if getattr(b, "punct", None) and tok in b.punct:
                inst = self.pick(b.punct[tok], "p" + tok)
                p_st, p_w = self._normalize_punct_sample(inst)
                return p_st, p_w + 0.15 * xh, []
            sample = self.get_letter_sample(tok)
            if sample:
                w_tok = sample.get("w", 1.0 * xh)
                return list(sample["s"]), w_tok, []
        if getattr(b, "digits", None) and tok in b.digits:
            inst = self.pick(b.digits[tok], "d" + tok)
            return list(inst["s"]), inst["w"], []
        if getattr(b, "punct", None) and tok in b.punct:
            inst = self.pick(b.punct[tok], "p" + tok)
            p_st, p_w = self._normalize_punct_sample(inst)
            return p_st, p_w + 0.15 * xh, []
        if getattr(b, "symbols", None) and tok in b.symbols:
            inst = self.pick(b.symbols[tok], "sym:" + tok)
            return list(inst["s"]), inst["w"], []

        lead, core, trail = TOKRE.match(tok).groups()
        strokes: list[Stroke] = []
        x, miss = 0.0, []

        for ch in lead:
            if getattr(b, "punct", None) and ch in b.punct:
                inst = self.pick(b.punct[ch], "p" + ch)
                p_st, p_w = self._normalize_punct_sample(inst)
                strokes += [shift(st, x, 0) for st in p_st]
                x += p_w + 0.15 * xh
            elif getattr(b, "symbols", None) and ch in b.symbols:
                inst = self.pick(b.symbols[ch], "sym:" + ch)
                strokes += [shift(st, x, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * xh
            elif getattr(b, "letters", None) and ch in b.letters:
                inst = self.pick(b.letters[ch], "let:" + ch)
                strokes += [shift(st, x, 0) for st in inst["s"]]
                x += inst.get("w", 1.0 * xh) + 0.15 * xh
            else:
                miss.append(ch)

        placed_core_strokes: list[Stroke] = []
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
                    st, w = [], weight(core) * b.d.get("ratio", 6.6)
                    needed_chars, needed_tone, _ = split_letters(core)
                    m = [ch for ch in needed_chars if not self.get_letter_sample(ch)]
                    if needed_tone and not b.marks.get(needed_tone):
                        m.append(needed_tone)
                    if not m:
                        m = [core]
                miss += m
            shifted_core = [shift(s_, x, 0) for s_ in st]
            placed_core_strokes = shifted_core
            strokes += shifted_core
            x += w

        first_trail = True
        for ch in trail:
            lib = b.punct.get(ch)
            if lib:
                g = self.pick(lib, "p" + ch)
                p_st, p_w = self._normalize_punct_sample(g)
                if first_trail and placed_core_strokes:
                    core_max_x = max((pt for s_ in placed_core_strokes for pt in s_[0::2]), default=x)
                    clearance_gap = max(0.8 * pen_w, 0.18 * xh)
                    x = max(x, core_max_x) + clearance_gap
                elif not first_trail:
                    x += 0.10 * xh
                strokes += [shift(st, x, 0) for st in p_st]
                x += p_w + 0.12 * xh
                first_trail = False
            elif getattr(b, "symbols", None) and ch in b.symbols:
                inst = self.pick(b.symbols[ch], "sym:" + ch)
                strokes += [shift(st, x + 0.15 * xh, 0) for st in inst["s"]]
                x += inst["w"] + 0.15 * xh
                first_trail = False
            elif getattr(b, "letters", None) and ch in b.letters:
                inst = self.pick(b.letters[ch], "let:" + ch)
                strokes += [shift(st, x + 0.15 * xh, 0) for st in inst["s"]]
                x += inst.get("w", 1.0 * xh) + 0.15 * xh
                first_trail = False
            else:
                miss.append(ch)

        if not core and not lead and trail == tok and (
            tok not in getattr(b, "letters", {})
            and tok not in getattr(b, "punct", {})
            and tok not in getattr(b, "digits", {})
            and tok not in getattr(b, "symbols", {})
        ):
            miss = [tok]
        return strokes, x, miss
