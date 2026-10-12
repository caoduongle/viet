"""Kiểm thử định vị dấu mũ toán học và chặn cận trên ascent theo hợp đồng CTR-034-MATH-ACCENT-PLACEMENT.
"""
from __future__ import annotations

import random
import pytest
from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math.parser import parse_latex_math
from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer

KHO_TONG_HOP = "tests/data/kho_mau_tong_hop.json.gz"


def test_bar_accent_proximity_to_base_glyph():
    """Dấu gạch ngang \\bar{x} phải nằm sát tự nhiên trên đỉnh chữ cái x."""
    bank = Bank(KHO_TONG_HOP)
    wr = Writer(bank, random.Random(42), 0.0)
    engine = MathLayoutEngine(bank, writer=wr, S=1.0)

    # Đo \\bar{x}
    item = engine.measure(parse_latex_math(r"\bar{x}"))
    xh = float(getattr(bank, "xh", 7.94))

    # item.strokes chứa nét vẽ thanh gạch ngang, item.glyphs chứa chữ x
    assert len(item.strokes) >= 1
    bar_stroke = item.strokes[0]
    bar_y = bar_stroke.points[0][1] # y âm trên baseline

    # Đỉnh nét chữ x
    assert len(item.glyphs) >= 1
    g = item.glyphs[0]
    ys = [pt for stroke in g.strokes for pt in stroke[1::2]]
    base_top_y = min(ys) if ys else -xh # ví dụ -7.94

    # Khoảng cách giữa đỉnh chữ x và gạch ngang (cả 2 đều là toạ độ âm)
    # bar_y nằm trên base_top_y -> bar_y < base_top_y
    gap = abs(bar_y - base_top_y)

    # Khe quang học tự nhiên không được bay cao quá 0.25 * xh
    assert gap <= 0.25 * xh, f"Dấu gạch ngang bay quá cao: gap={gap:.2f} > {0.25 * xh:.2f}"
    assert bar_y < base_top_y, "Dấu gạch ngang phải nằm phía trên đỉnh chữ cái"


def test_accent_ascent_is_compact():
    """Chỉ số ascent của ký tự có dấu mũ không được phình to bất thường."""
    bank = Bank(KHO_TONG_HOP)
    wr = Writer(bank, random.Random(42), 0.0)
    engine = MathLayoutEngine(bank, writer=wr, S=1.0)

    item = engine.measure(parse_latex_math(r"\bar{x}"))
    xh = float(getattr(bank, "xh", 7.94))
    # ascent không được vượt quá 1.35 * xh
    assert item.size.ascent <= 1.35 * xh, f"ascent quá lớn: {item.size.ascent} > {1.35 * xh}"
