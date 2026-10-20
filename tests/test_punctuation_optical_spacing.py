"""Kiểm thử tính năng Feature 049:
- US3: Đồng bộ ngữ cảnh SeedContext giữa measure_text_width() và render số.
- US4: Sàn khoảng hở quang học hình học cho số thập phân, ngoặc toán và dấu câu.
"""
from __future__ import annotations

import gzip
import json
import random
from pathlib import Path

import pytest

from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math import parse_latex_math
from chuviettay.model.bank import Bank
from chuviettay.model.rng import SeedContext
from chuviettay.model.writer import Writer


def _inst(w, strokes, T="", vi=-1, ti=-1):
    return {"w": w, "s": strokes, "T": T, "vi": vi, "ti": ti}


def create_multivariant_number_bank(tmp_path: Path, xh: float = 7.0) -> Bank:
    """Tạo kho mẫu có chữ số nhiều biến thể với độ rộng và hình dáng khác nhau."""
    # Chữ số 1: mẫu hẹp 2.5pt, mẫu trung bình 3.5pt, mẫu rộng 5.0pt
    d1 = [
        _inst(2.5, [[0.0, 0.0, 0.5, -6.0]]),
        _inst(3.5, [[0.0, -4.0, 1.5, -6.0, 1.5, 0.0]]),
        _inst(5.0, [[0.0, -4.0, 2.0, -6.0, 2.0, 0.0, 0.0, 0.0, 4.0, 0.0]]),
    ]
    # Chữ số 0: mẫu tròn chuẩn và mẫu nghiêng rộng
    d0 = [
        _inst(4.0, [[0.0, -3.0, 2.0, -6.0, 4.0, -3.0, 2.0, 0.0, 0.0, -3.0]]),
        _inst(5.5, [[0.0, -3.0, 3.0, -6.0, 5.5, -3.0, 2.5, 0.0, 0.0, -3.0]]),
    ]
    # Chữ số 2
    d2 = [
        _inst(4.0, [[0.0, -5.0, 2.0, -6.0, 4.0, -4.0, 0.0, 0.0, 4.0, 0.0]]),
        _inst(5.2, [[0.0, -5.0, 2.5, -6.0, 5.2, -4.0, 0.0, 0.0, 5.2, 0.0]]),
    ]
    # Dấu phẩy có đuôi móc
    punct_comma = [
        {"w": 1.2, "s": [[0.5, 0.0, 0.8, 1.0, 0.3, 2.0]]},
    ]
    # Dấu chấm
    punct_dot = [
        {"w": 1.0, "s": [[0.3, 0.0, 0.7, 0.0]]},
    ]

    bank_dict = {
        "schema_version": 2,
        "xh": xh,
        "wgaps": [10.0],
        "dgaps": [3.0],
        "line": 24.0,
        "v": 1,
        "x0": 78.0,
        "width": 500.0,
        "ratio": 6.6,
        "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
        "words": {
            "có": [
                _inst(8.0, [[0.0, -3.0, 2.0, -5.0, 4.0, -3.0], [4.5, -3.0, 6.5, -5.0, 8.0, -3.0], [5.0, -7.0, 7.0, -9.0]]),
            ],
            "ta": [
                _inst(7.0, [[0.0, 0.0, 3.5, 0.0], [1.75, 0.0, 1.75, -6.0], [4.0, -3.0, 6.0, -5.0, 7.0, -1.0]]),
            ],
        },
        "digits": {"0": d0, "1": d1, "2": d2},
        "punct": {",": punct_comma, ".": punct_dot},
        "symbols": {},
        "letters": {},
        "marks": {},
    }

    p = tmp_path / "multivariant_bank.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(bank_dict, f, ensure_ascii=False)
    return Bank(str(p))


# ==============================================================================
# USER STORY 3 TESTS: Context-Aware Number Measurement Parity
# ==============================================================================

def test_context_aware_measurement_parity(tmp_path):
    """T015 [US3]: measure_text_width khớp độ rộng khi render trên từng ngữ cảnh (heading/cell/text)."""
    bank = create_multivariant_number_bank(tmp_path)
    writer = Writer(bank, stable_variants=True)

    num_test = "102"
    contexts = [
        SeedContext(content_type="heading", element_id=num_test, occurrence=0, sub_index=0),
        SeedContext(content_type="heading", element_id=num_test, occurrence=2, sub_index=0),
        SeedContext(content_type="cell", element_id=num_test, occurrence=1, sub_index=0),
        SeedContext(content_type="cell", element_id=num_test, occurrence=3, sub_index=0),
        SeedContext(content_type="text", element_id=num_test, occurrence=0, sub_index=0),
    ]

    xh = bank.xh
    for ctx in contexts:
        # Đo độ rộng với context
        est_w = writer.measure_text_width(num_test, context=ctx)

        # Kết xuất thực tế với cùng context
        st, rendered_w, miss = writer.token(num_test, context=ctx)
        assert not miss

        # Sai lệch phải <= 0.05 * xh (hoàn toàn khớp biến thể chữ số đã chọn)
        assert abs(est_w - rendered_w) <= 0.05 * xh, (
            f"Lệch độ rộng cho context {ctx}: est={est_w:.3f}, rendered={rendered_w:.3f}"
        )


def test_measure_text_width_is_pure_function(tmp_path):
    """T015 [US3]: measure_text_width không làm biến đổi bất kỳ bộ đếm hay trạng thái nào."""
    bank = create_multivariant_number_bank(tmp_path)
    writer = Writer(bank, stable_variants=True)

    counts_before = dict(writer._token_counts)
    last_before = dict(writer.last)
    token_last_before = dict(writer._token_last)

    ctx = SeedContext(content_type="cell", element_id="102", occurrence=5)
    _ = writer.measure_text_width("102", context=ctx)
    _ = writer.measure_text_width("không_phải_số", context=ctx)

    assert writer._token_counts == counts_before, "_token_counts bị thay đổi sau khi đo"
    assert writer.last == last_before, "last bị thay đổi sau khi đo"
    assert writer._token_last == token_last_before, "_token_last bị thay đổi sau khi đo"


# ==============================================================================
# USER STORY 4 TESTS: Optical Spacing and Clearance (P2)
# ==============================================================================

def test_decimal_numbers_optical_clearance(real_bank):
    """T021 [US4]: Dấu phẩy thập phân trong 0,39, 0,19, 0,20 có khoảng hở quang học dương, không dính nét."""
    writer = Writer(real_bank)
    xh = real_bank.xh

    for num_str in ["0,39", "0,19", "0,20"]:
        strokes, total_w, miss = writer.number(num_str)
        assert not miss, f"Có ký tự thiếu trong {num_str}: {miss}"
        assert len(strokes) >= 3, f"Số strokes không đủ cho {num_str}"

        # Tọa độ ink x của chữ số trước (0)
        st0_xs = [pt for pt in strokes[0][0::2]]
        # Tọa độ ink x của dấu phẩy
        comma_xs = [pt for pt in strokes[1][0::2]]
        # Tọa độ ink x của chữ số kế tiếp
        st_next_xs = [pt for pt in strokes[2][0::2]]

        gap_before = min(comma_xs) - max(st0_xs)
        gap_after = min(st_next_xs) - max(comma_xs)

        # Khoảng hở trước dấu phẩy >= 0.08 * xh - epsilon
        assert gap_before >= 0.08 * xh - 1e-4, (
            f"{num_str}: Khoảng hở trước dấu phẩy quá nhỏ: {gap_before:.3f} < {0.08 * xh:.3f}"
        )
        # Khoảng hở sau dấu phẩy >= 0.10 * xh - epsilon
        assert gap_after >= 0.10 * xh - 1e-4, (
            f"{num_str}: Khoảng hở sau dấu phẩy quá nhỏ: {gap_after:.3f} < {0.10 * xh:.3f}"
        )


def test_trailing_punctuation_optical_clearance(real_bank):
    """T021 [US4]: Dấu kết thúc (như hai chấm 'có:', chấm phẩy 'xin;') có vector fallback và không dính nét."""
    writer = Writer(real_bank)
    xh = real_bank.xh

    # Test với 'có:'
    strokes, total_w, miss = writer.token("có:")
    assert not miss, f"Ký tự thiếu trong 'có:': {miss}"
    assert len(strokes) >= 3
    word_strokes = strokes[:-2]
    colon_strokes = strokes[-2:]

    word_max_x = max(pt for st in word_strokes for pt in st[0::2])
    colon_min_x = min(pt for st in colon_strokes for pt in st[0::2])
    gap = colon_min_x - word_max_x

    # Khoảng hở giữa từ và dấu hai chấm >= 0.18 * xh - epsilon
    assert gap >= 0.18 * xh - 1e-4, (
        f"'có:': Khoảng hở dấu hai chấm dính nét: gap={gap:.3f} < {0.18 * xh:.3f}"
    )

    # Test với 'xin;'
    strokes_semi, total_w_semi, miss_semi = writer.token("xin;")
    assert not miss_semi, f"Ký tự thiếu trong 'xin;': {miss_semi}"
    assert len(strokes_semi) >= 2
    word_strokes_semi = strokes_semi[:-2]
    semi_strokes = strokes_semi[-2:]

    word_max_x_semi = max(pt for st in word_strokes_semi for pt in st[0::2])
    semi_min_x = min(pt for st in semi_strokes for pt in st[0::2])
    gap_semi = semi_min_x - word_max_x_semi

    assert gap_semi >= 0.18 * xh - 1e-4, (
        f"'xin;': Khoảng hở chấm phẩy dính nét: gap={gap_semi:.3f} < {0.18 * xh:.3f}"
    )


def test_math_delimiters_and_spacing_hardening(real_bank):
    """T021 [US4]: Công thức toán F_X(1), F_X(4), P(2 <= X <= 5) không bị đè nét, khoảng hở mở rộng."""
    math_eng = MathLayoutEngine(real_bank)

    for expr in ["F_X(1)", "F_X(4)", r"P(2 \le X \le 5)"]:
        node = parse_latex_math(expr)
        item = math_eng.measure(node, 1.0)
        assert item is not None
        assert item.size.width > 0
        assert item.size.height > 0
