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
from chuviettay.model.text_utils import tone_info


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
