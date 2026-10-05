#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/gen_synthetic_bank.py -- Sinh fixture kho mẫu chữ tổng hợp (synthetic benchmark fixture).

Fixture này thay thế cho kho mẫu cá nhân (kho_mau_chup_lai.json.gz) trong bộ kiểm thử:
- Hoàn toàn độc lập, không chứa nét chữ viết tay thực tế của bất kỳ cá nhân nào.
- Sinh các nét hình học giả lập (pseudo-strokes) có cấu trúc chuẩn xác theo đúng quy cách của Bank.
- Bao gồm đầy đủ 5 dấu thanh tiếng Việt (huyền, sắc, hỏi, ngã, nặng), chữ số và dấu câu.
- Có thể chạy lại bất cứ lúc nào để tái tạo fixture một cách tất định (deterministic).
"""
from __future__ import annotations

import gzip
import json
import os
import sys

# Cho phép chạy trực tiếp script từ mọi thư mục
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chuviettay.config import NANG, TONES
from chuviettay.model.bank_schema import CURRENT_VERSION
from chuviettay.model.text_utils import normalize_letter_sample, tone_info


def make_sample(width: float, strokes: list[list[float]], T: str = "", vi: int = -1, ti: int = -1) -> dict:
    return {"w": round(width, 2), "s": strokes, "T": T, "vi": vi, "ti": ti}


def generate_synthetic_bank() -> dict:
    """Sinh cấu trúc kho mẫu tổng hợp phục vụ kiểm thử."""
    # Nét thân chữ cơ bản: đường zigzag ziczac giả lập chữ
    base_stroke = [0.0, 0.0, 3.0, -5.0, 6.0, 0.0, 9.0, -5.0]

    # Các nét dấu thanh riêng biệt (stroke thứ 2, ti=1)
    tone_marks = {
        "\\": [4.0, -9.0, 2.0, -7.0],       # huyền
        "/": [2.0, -7.0, 4.0, -9.0],        # sắc
        "?": [3.0, -9.0, 4.0, -8.0, 3.0, -7.0],  # hỏi
        "~": [2.0, -8.0, 3.5, -9.0, 5.0, -8.0],  # ngã
        NANG: [4.0, 2.0, 4.5, 2.5],         # nặng (dưới chân chữ)
    }

    words: dict[str, list[dict]] = {}

    # 1. Từ "xin" có 5 mẫu độ rộng ổn định (phục vụ test hiệu chỉnh cỡ tay - calibration)
    words["xin"] = [
        make_sample(w, [list(base_stroke)])
        for w in (9.0, 9.2, 8.8, 9.1, 8.9)
    ]

    # 2. Các từ không dấu cơ bản (thân chữ để ghép)
    for w_name, w_len in [("ba", 8.0), ("ma", 8.0), ("so", 8.0), ("cho", 10.0), ("la", 7.5)]:
        words[w_name] = [
            make_sample(w_len, [[0.0, 0.0, w_len / 2, -5.0, w_len, 0.0]]),
            make_sample(w_len + 0.2, [[0.0, 0.0, w_len / 2, -5.2, w_len + 0.2, 0.0]]),
        ]

    # 3. Các từ có dấu thanh (cung cấp nét dấu thanh để "harvest" vào bank.marks)
    # Cần ít nhất 10 mẫu để qua bộ lọc phân vị trong rebuild():
    #   if len(lst) >= 10: ...
    # Để đơn giản và phong phú, sinh cho mỗi dấu thanh 12 mẫu phân bố quanh nguyên âm
    tone_examples = [
        ("bà", "\\", "ba"),
        ("chào", "\\", "chao"),
        ("bá", "/", "ba"),
        ("số", "/", "so"),
        ("bả", "?", "ba"),
        ("bã", "~", "ba"),
        ("xạ", NANG, "xa"),
    ]

    for label, t_char, base_w in tone_examples:
        T, vi, _, _ = tone_info(label)
        mark_st = tone_marks[t_char]
        sample_list = []
        for i in range(12):
            # Tạo dao động nhỏ về vị trí dấu
            dx = (i - 6) * 0.1
            dy = (i - 6) * 0.05
            shifted_mark = [mark_st[j] + (dx if j % 2 == 0 else dy) for j in range(len(mark_st))]
            sample_list.append(
                make_sample(8.0, [[0.0, 0.0, 4.0, -5.0, 8.0, 0.0], shifted_mark], T=T, vi=vi, ti=1)
            )
        words[label] = sample_list

    # 4. Chữ số
    digits: dict[str, list[dict]] = {}
    for d_char in "0123456789":
        digits[d_char] = [
            make_sample(6.0, [[1.0, 0.0, 3.0, -7.0, 5.0, 0.0]]),
            make_sample(6.0, [[1.0, 0.0, 3.0, -6.8, 5.0, 0.0]]),
        ]

    # 5. Dấu câu
    punct: dict[str, list[dict]] = {}
    for p_char, st in [
        (".", [[1.0, 0.0, 2.0, 0.0]]),
        (",", [[1.0, 0.0, 1.0, 2.0]]),
        ("!", [[1.0, -7.0, 1.0, -2.0], [1.0, 0.0, 1.5, 0.0]]),
        ("?", [[1.0, -7.0, 3.0, -7.0, 2.0, -3.0], [2.0, 0.0, 2.5, 0.0]]),
        ("(", [[3.0, -7.0, 1.0, -3.5, 3.0, 0.0]]),
        (")", [[1.0, -7.0, 3.0, -3.5, 1.0, 0.0]]),
    ]:
        punct[p_char] = [make_sample(4.0, st)]

    return {
        "schema_version": CURRENT_VERSION,
        "xh": 7.0,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "line": 24.0,
        "v": 1,
        "x0": 78.0,
        "width": 500.0,
        "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": words,
        "digits": digits,
        "punct": punct,
        "symbols": {},
        "letters": {},
        "marks": {t: [] for t in TONES},
    }


def build_synthetic_letter_bank(seed: int = 42) -> dict:
    """Sinh kho mẫu chữ cái tổng hợp chuẩn (synthetic letter bank) với hình học xác định.

    CHÚ Ý: Hàm này chỉ chứng minh cơ chế lắp ghép chữ (dual-path letter assembly),
    tự động co giãn x-height (auto-xh) và sàn khoảng cách vật lý (clearance floor)
    trong môi trường kiểm thử tự động, không đại diện cho tính thẩm mỹ chữ viết tay.

    Đặc tính kỹ thuật:
    - Schema version: v4
    - Target x-height: 7.94 pt
    - Bút vẽ chuẩn: width 1.41 pt
    - Bao gồm: 29 chữ cái tiếng Việt + 4 chữ Latin mượn (f, j, w, z) hoa/thường
    - 5 dấu thanh rời trong marks (\u0300, \u0301, \u0303, \u0309, \u0323)
    - Đầy đủ chữ số (0-9), dấu câu và ký hiệu toán học / lập trình
    """
    xh = 7.94

    # 1. Nét hình học cơ sở chữ cái viết thường
    raw_letters: dict[str, list[list[float]]] = {
        # x_height letters (min_y = -7.94, max_y = 0.0 -> height = 7.94)
        "a": [[4.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0, 4.5, -xh, 4.5, 0.0]],
        "c": [[4.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0]],
        "e": [[0.5, -xh / 2, 4.5, -xh / 2, 4.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0]],
        "m": [[0.5, 0.0, 0.5, -xh, 3.5, -xh, 3.5, 0.0, 3.5, -xh, 6.5, -xh, 6.5, 0.0]],
        "n": [[0.5, 0.0, 0.5, -xh, 4.5, -xh, 4.5, 0.0]],
        "o": [[2.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0, 4.5, -xh, 2.5, -xh]],
        "r": [[0.5, 0.0, 0.5, -xh, 3.5, -xh, 4.0, -xh * 0.8]],
        "s": [[4.0, -xh, 0.5, -xh, 0.5, -xh / 2, 4.0, -xh / 2, 4.0, 0.0, 0.5, 0.0]],
        "u": [[0.5, -xh, 0.5, 0.0, 4.5, 0.0, 4.5, -xh, 4.5, 0.0]],
        "v": [[0.5, -xh, 2.5, 0.0, 4.5, -xh]],
        "w": [[0.5, -xh, 2.0, 0.0, 3.5, -xh * 0.6, 5.0, 0.0, 6.5, -xh]],
        "x": [[0.5, -xh, 4.5, 0.0, 2.5, -xh / 2, 4.5, -xh, 0.5, 0.0]],
        "z": [[0.5, -xh, 4.5, -xh, 0.5, 0.0, 4.5, 0.0]],
        # ascenders (height ~ 10.5)
        "b": [[0.5, -10.5, 0.5, 0.0, 4.5, 0.0, 4.5, -xh, 0.5, -xh]],
        "d": [[4.5, -10.5, 4.5, 0.0, 0.5, 0.0, 0.5, -xh, 4.5, -xh]],
        "h": [[0.5, -10.5, 0.5, 0.0, 0.5, -xh, 4.5, -xh, 4.5, 0.0]],
        "k": [[0.5, -10.5, 0.5, 0.0, 0.5, -xh / 2, 4.5, -xh, 0.5, -xh / 2, 4.5, 0.0]],
        "l": [[1.0, -10.5, 1.0, 0.0, 2.5, 0.0]],
        "t": [[1.5, -10.0, 1.5, 0.0, 3.0, 0.0, 1.5, 0.0, 1.5, -xh, 0.5, -xh, 3.0, -xh]],
        # descenders (height ~ 10.5)
        "g": [[4.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0, 4.5, 3.0, 1.0, 3.0]],
        "p": [[0.5, 3.0, 0.5, -xh, 4.5, -xh, 4.5, 0.0, 0.5, 0.0]],
        "q": [[4.5, 3.0, 4.5, -xh, 0.5, -xh, 0.5, 0.0, 4.5, 0.0]],
        "y": [[0.5, -xh, 2.5, 0.0, 4.5, -xh, 2.5, 0.0, 1.0, 3.0]],
        # i, j
        "i": [[1.0, -xh, 1.0, 0.0, 2.5, 0.0]],
        "j": [[2.5, -xh, 2.5, 3.0, 0.5, 3.0]],
        "f": [[3.5, -10.5, 1.5, -10.5, 1.5, 0.0, 1.5, -xh, 0.5, -xh, 3.5, -xh]],
    }

    # Ký tự có dấu phụ (mũ, trăng, sừng, gạch ngang)
    hat_bre = [1.5, -9.5, 2.5, -9.0, 3.5, -9.5]
    hat_cir = [1.5, -9.0, 2.5, -9.8, 3.5, -9.0]
    bar_d = [3.0, -9.0, 5.5, -9.0]
    horn = [4.5, -xh, 5.2, -9.0]

    raw_letters["ă"] = raw_letters["a"] + [hat_bre]
    raw_letters["â"] = raw_letters["a"] + [hat_cir]
    raw_letters["đ"] = raw_letters["d"] + [bar_d]
    raw_letters["ê"] = raw_letters["e"] + [hat_cir]
    raw_letters["ô"] = raw_letters["o"] + [hat_cir]
    raw_letters["ơ"] = raw_letters["o"] + [horn]
    raw_letters["ư"] = raw_letters["u"] + [horn]

    # 2. Nét hình học chữ in hoa
    raw_upper: dict[str, list[list[float]]] = {
        "A": [[0.5, 0.0, 3.5, -10.5, 6.5, 0.0, 5.0, -4.0, 2.0, -4.0]],
        "B": [[0.5, 0.0, 0.5, -10.5, 4.5, -10.5, 4.5, -5.5, 0.5, -5.5, 5.0, -5.5, 5.0, 0.0, 0.5, 0.0]],
        "C": [[5.5, -10.5, 0.5, -10.5, 0.5, 0.0, 5.5, 0.0]],
        "D": [[0.5, 0.0, 0.5, -10.5, 4.5, -10.5, 5.5, -5.5, 4.5, 0.0, 0.5, 0.0]],
        "E": [[5.0, -10.5, 0.5, -10.5, 0.5, -5.5, 4.0, -5.5, 0.5, -5.5, 0.5, 0.0, 5.0, 0.0]],
        "G": [[5.5, -10.5, 0.5, -10.5, 0.5, 0.0, 5.5, 0.0, 5.5, -5.0, 3.0, -5.0]],
        "H": [[0.5, 0.0, 0.5, -10.5, 0.5, -5.5, 5.5, -5.5, 5.5, -10.5, 5.5, 0.0]],
        "I": [[1.0, -10.5, 4.0, -10.5, 2.5, -10.5, 2.5, 0.0, 1.0, 0.0, 4.0, 0.0]],
        "K": [[0.5, 0.0, 0.5, -10.5, 0.5, -5.5, 5.0, -10.5, 0.5, -5.5, 5.0, 0.0]],
        "L": [[0.5, -10.5, 0.5, 0.0, 4.5, 0.0]],
        "M": [[0.5, 0.0, 0.5, -10.5, 3.5, 0.0, 6.5, -10.5, 6.5, 0.0]],
        "N": [[0.5, 0.0, 0.5, -10.5, 5.5, 0.0, 5.5, -10.5]],
        "O": [[3.0, -10.5, 0.5, -10.5, 0.5, 0.0, 5.5, 0.0, 5.5, -10.5, 3.0, -10.5]],
        "P": [[0.5, 0.0, 0.5, -10.5, 5.0, -10.5, 5.0, -5.0, 0.5, -5.0]],
        "Q": [[3.0, -10.5, 0.5, -10.5, 0.5, 0.0, 5.5, 0.0, 5.5, -10.5, 3.0, -10.5, 4.0, -2.0, 6.0, 1.5]],
        "R": [[0.5, 0.0, 0.5, -10.5, 5.0, -10.5, 5.0, -5.5, 0.5, -5.5, 3.0, -5.5, 5.5, 0.0]],
        "S": [[5.0, -10.5, 0.5, -10.5, 0.5, -5.5, 5.0, -5.5, 5.0, 0.0, 0.5, 0.0]],
        "T": [[0.5, -10.5, 5.5, -10.5, 3.0, -10.5, 3.0, 0.0]],
        "U": [[0.5, -10.5, 0.5, 0.0, 5.5, 0.0, 5.5, -10.5]],
        "V": [[0.5, -10.5, 3.0, 0.0, 5.5, -10.5]],
        "X": [[0.5, -10.5, 5.5, 0.0, 3.0, -5.25, 5.5, -10.5, 0.5, 0.0]],
        "Y": [[0.5, -10.5, 3.0, -5.5, 5.5, -10.5, 3.0, -5.5, 3.0, 0.0]],
        "F": [[0.5, 0.0, 0.5, -10.5, 5.0, -10.5, 0.5, -10.5, 0.5, -5.5, 4.0, -5.5]],
        "J": [[4.5, -10.5, 4.5, 0.0, 0.5, 0.0, 0.5, -2.5]],
        "W": [[0.5, -10.5, 2.0, 0.0, 3.5, -7.0, 5.0, 0.0, 6.5, -10.5]],
        "Z": [[0.5, -10.5, 5.5, -10.5, 0.5, 0.0, 5.5, 0.0]],
    }
    raw_upper["Ă"] = raw_upper["A"] + [[2.5, -12.5, 3.5, -12.0, 4.5, -12.5]]
    raw_upper["Â"] = raw_upper["A"] + [[2.5, -12.0, 3.5, -12.8, 4.5, -12.0]]
    raw_upper["Đ"] = raw_upper["D"] + [[-0.5, -5.5, 2.5, -5.5]]
    raw_upper["Ê"] = raw_upper["E"] + [[2.0, -12.0, 3.0, -12.8, 4.0, -12.0]]
    raw_upper["Ô"] = raw_upper["O"] + [[2.0, -12.0, 3.0, -12.8, 4.0, -12.0]]
    raw_upper["Ơ"] = raw_upper["O"] + [[5.5, -10.5, 6.2, -12.2]]
    raw_upper["Ư"] = raw_upper["U"] + [[5.5, -10.5, 6.2, -12.2]]

    letters: dict[str, list[dict]] = {}
    for ch, sts in {**raw_letters, **raw_upper}.items():
        w_guess = max((pt for s in sts for pt in s[0::2]), default=5.0) + 1.0
        norm = normalize_letter_sample(ch, sts, w_guess, raw_xh=xh, target_xh=xh)
        letters[ch] = [norm]

    # 3. Dấu thanh rời (\u0300, \u0301, \u0303, \u0309, \u0323)
    marks: dict[str, list[dict]] = {
        "\u0300": [{"s": [[-1.2, -0.6, 1.2, 0.6]], "dx": 0.0, "dy": -2.0, "_src": "synthetic", "T": "\u0300"}],
        "\u0301": [{"s": [[-1.2, 0.6, 1.2, -0.6]], "dx": 0.0, "dy": -2.0, "_src": "synthetic", "T": "\u0301"}],
        "\u0309": [{"s": [[-0.8, -0.6, 0.2, -0.6, 0.0, 0.6]], "dx": 0.0, "dy": -2.0, "_src": "synthetic", "T": "\u0309"}],
        "\u0303": [{"s": [[-1.0, 0.4, 0.0, -0.4, 1.0, 0.4]], "dx": 0.0, "dy": -2.0, "_src": "synthetic", "T": "\u0303"}],
        NANG: [{"s": [[-0.5, 0.0, 0.5, 0.0]], "dx": 0.0, "dy": 2.0, "_src": "synthetic", "T": NANG}],
    }

    # 4. Chữ số 0-9
    digits: dict[str, list[dict]] = {}
    for d_char in "0123456789":
        digits[d_char] = [
            make_sample(5.0, [[0.5, 0.0, 0.5, -xh, 4.5, -xh, 4.5, 0.0, 0.5, 0.0]])
        ]

    # 5. Dấu câu
    punct: dict[str, list[dict]] = {
        ".": [make_sample(3.0, [[1.0, 0.0, 1.5, 0.0]])],
        ",": [make_sample(3.0, [[1.5, 0.0, 1.0, 1.5]])],
        "!": [make_sample(3.0, [[1.5, -xh, 1.5, -2.5], [1.5, 0.0, 1.7, 0.0]])],
        "?": [make_sample(4.0, [[1.0, -xh, 3.5, -xh, 3.5, -xh / 2, 2.0, -xh / 2, 2.0, -2.5], [2.0, 0.0, 2.2, 0.0]])],
        "(": [make_sample(3.0, [[2.5, -xh * 1.2, 1.0, -xh * 0.5, 2.5, xh * 0.2]])],
        ")": [make_sample(3.0, [[1.0, -xh * 1.2, 2.5, -xh * 0.5, 1.0, xh * 0.2]])],
        ":": [make_sample(3.0, [[1.5, -xh * 0.7, 1.7, -xh * 0.7], [1.5, 0.0, 1.7, 0.0]])],
        ";": [make_sample(3.0, [[1.5, -xh * 0.7, 1.7, -xh * 0.7], [1.5, 0.0, 1.0, 1.5]])],
        "-": [make_sample(4.0, [[0.5, -xh * 0.5, 3.5, -xh * 0.5]])],
        '"': [make_sample(4.0, [[1.0, -xh * 1.2, 1.0, -xh * 0.8], [2.5, -xh * 1.2, 2.5, -xh * 0.8]])],
        "'": [make_sample(2.5, [[1.0, -xh * 1.2, 1.0, -xh * 0.8]])],
        "/": [make_sample(4.0, [[0.5, xh * 0.2, 3.5, -xh * 1.2]])],
    }

    # 6. Ký hiệu toán học và kỹ thuật
    symbols: dict[str, list[dict]] = {
        ">=": [make_sample(6.0, [[0.5, -xh * 0.8, 4.5, -xh * 0.5, 0.5, -xh * 0.2], [0.5, 0.0, 4.5, 0.0]])],
        "<=": [make_sample(6.0, [[4.5, -xh * 0.8, 0.5, -xh * 0.5, 4.5, -xh * 0.2], [0.5, 0.0, 4.5, 0.0]])],
        ">": [make_sample(5.0, [[0.5, -xh * 0.8, 4.5, -xh * 0.5, 0.5, -xh * 0.2]])],
        "<": [make_sample(5.0, [[4.5, -xh * 0.8, 0.5, -xh * 0.5, 4.5, -xh * 0.2]])],
        "=": [make_sample(5.0, [[0.5, -xh * 0.6, 4.5, -xh * 0.6], [0.5, -xh * 0.3, 4.5, -xh * 0.3]])],
        "_": [make_sample(5.0, [[0.0, 1.0, 5.0, 1.0]])],
        "---": [make_sample(15.0, [[0.0, -xh * 0.5, 15.0, -xh * 0.5]])],
        "--": [make_sample(10.0, [[0.0, -xh * 0.5, 10.0, -xh * 0.5]])],
    }

    # 7. Mẫu từ chuẩn phục vụ calibration
    words: dict[str, list[dict]] = {
        "xin": [make_sample(9.0, [[0.0, 0.0, 3.0, -5.0, 6.0, 0.0, 9.0, -5.0]]) for _ in range(5)]
    }

    return {
        "schema_version": CURRENT_VERSION,
        "xh": xh,
        "wgaps": [11.0],
        "dgaps": [3.5],
        "line": 24.0,
        "v": 1,
        "x0": 78.0,
        "width": 500.0,
        "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": words,
        "digits": digits,
        "punct": punct,
        "symbols": symbols,
        "letters": letters,
        "marks": marks,
    }


def save_synthetic_bank(out_path: str) -> None:
    data = generate_synthetic_bank()
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Đã sinh fixture tổng hợp thành công tại: {out_path}")
    print(f"Số từ: {len(data['words'])}, số chữ số: {len(data['digits'])}, số dấu câu: {len(data['punct'])}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join("tests", "data", "kho_mau_tong_hop.json.gz")
    save_synthetic_bank(target)
