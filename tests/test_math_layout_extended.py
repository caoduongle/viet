"""Hình học dàn trang toán: phân số, chỉ số, ngoặc co giãn, toán tử lớn, ma trận, dấu trang trí, khoảng cách."""
import random

import pytest

from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math import parse_latex_math
from chuviettay.model.bank import Bank
from chuviettay.model.writer import Writer
from tests.mathtest_helpers import make_block_bank

XH = 7.0


@pytest.fixture()
def bank(tmp_path):
    return Bank(make_block_bank(str(tmp_path / "block.json.gz"), xh=XH))


def lay(bank, latex, display=False, S=1.0, **kw):
    wr = Writer(bank, random.Random(1), **kw)
    eng = MathLayoutEngine(bank, S=S, writer=wr, rnd=random.Random(1), display=display)
    return eng.measure(parse_latex_math(latex)), eng


def all_points(item):
    pts = []
    for g in item.glyphs:
        for st in g.strokes:
            pts += [(st[i] * g.scale + g.x, st[i + 1] * g.scale + g.y) for i in range(0, len(st), 2)]
    for s in item.strokes:
        pts += list(s.points)
    return pts


def glyph_boxes(item):
    boxes = []
    for g in item.glyphs:
        xs = [st[i] * g.scale + g.x for st in g.strokes for i in range(0, len(st), 2)]
        ys = [st[i + 1] * g.scale + g.y for st in g.strokes for i in range(0, len(st), 2)]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return sorted(boxes)


def test_fraction_numerator_above_denominator_below_bar(bank):
    item, _ = lay(bank, r"\frac{a}{b}")
    bar = item.strokes[0]
    bar_y = bar.points[0][1]
    boxes = glyph_boxes(item)
    tops = sorted(boxes, key=lambda b: b[1])
    assert tops[0][3] < bar_y < tops[1][1]          # tử hoàn toàn trên gạch, mẫu hoàn toàn dưới
    assert bar.points[1][0] - bar.points[0][0] >= max(b[2] - b[0] for b in boxes)


def test_nested_fraction_is_smaller(bank):
    one, _ = lay(bank, r"\frac{a}{b}")
    nested, _ = lay(bank, r"\frac{a}{\frac{b}{c}}")
    assert nested.size.height > one.size.height
    inner_scales = sorted({g.scale for g in nested.glyphs})
    assert inner_scales[0] < inner_scales[-1]


def test_superscript_raised_and_subscript_lowered(bank):
    sup, _ = lay(bank, "x^2")
    sub, _ = lay(bank, "x_2")
    base_top = glyph_boxes(sup)[0][1]
    exp_box = glyph_boxes(sup)[1]
    assert exp_box[3] < 0.0 and exp_box[1] < base_top        # chỉ số trên nằm cao hơn
    sub_box = glyph_boxes(sub)[1]
    assert sub_box[3] > 0.0                                  # chỉ số dưới thấp hơn baseline


def test_script_of_empty_base_still_raised(bank):
    item, _ = lay(bank, r"{}^{14}C")
    assert item.size.ascent > 0
    assert min(b[1] for b in glyph_boxes(item)) < -XH


def test_delimiters_stretch_around_tall_body(bank):
    tall, _ = lay(bank, r"\left( \frac{a}{b} \right)")
    short, _ = lay(bank, r"\left( a \right)")
    assert tall.strokes, "ngoặc co giãn phải được vẽ bằng nét vector"
    ys = [y for s in tall.strokes for _, y in s.points]
    body_top = min(b[1] for b in glyph_boxes(tall))
    body_bottom = max(b[3] for b in glyph_boxes(tall))
    assert min(ys) <= body_top and max(ys) >= body_bottom
    # thân thấp thì dùng chính glyph ngoặc của kho (không vẽ nét vector)
    assert not short.strokes and len(short.glyphs) == 3


def test_delimiter_without_side_draws_only_one(bank):
    item, eng = lay(bank, r"\left\{ \frac{a}{b} \right.")
    assert len(item.strokes) == 2                       # dấu { + gạch phân số; không có dấu đóng
    brace = item.strokes[0]
    assert max(x for x, _ in brace.points) < item.size.width * 0.3     # dấu { nằm bên trái
    assert max(y for _, y in brace.points) - min(y for _, y in brace.points) >= 2 * XH
    assert not eng.missing_symbols


def test_nary_display_stacks_limits_inline_places_side(bank):
    inline, _ = lay(bank, r"\sum_{i}^{n} a", display=False)
    display, _ = lay(bank, r"\sum_{i}^{n} a", display=True)
    assert display.size.height > inline.size.height
    # display: i và n căn giữa theo trục dọc của ∑; inline: lệch sang phải ∑
    def lim_boxes(item):
        return [b for b in glyph_boxes(item) if b[2] - b[0] < 0.7 * XH * 0.8 + 1][:2]
    d = [b for b in glyph_boxes(display)]
    sigma_right = max(x for s in display.strokes for x, _ in s.points)
    assert min(b[0] for b in d[:2]) < sigma_right               # giới hạn nằm dưới/trên, chồng theo chiều ngang với ∑
    i_in = [b for b in glyph_boxes(inline)]
    sigma_right_inline = max(x for s in inline.strokes for x, _ in s.points)
    assert min(b[0] for b in i_in[:2]) >= sigma_right_inline - 1e-6


def test_integral_keeps_side_limits_in_display(bank):
    item, _ = lay(bank, r"\int_0^1 f", display=True)
    sign_right = max(x for s in item.strokes for x, _ in s.points)
    lim = glyph_boxes(item)[:2]
    assert all(b[0] >= sign_right - 1e-6 for b in lim)


def test_big_operator_without_sample_is_drawn_and_reported(bank):
    item, eng = lay(bank, r"\sum")
    assert item.strokes and eng.missing_symbols == {"∑": 1}


def test_function_limit_stacked_in_display(bank):
    item, _ = lay(bank, r"\lim_{x}", display=True)
    # trong display, x nằm dưới "lim": đáy lớn hơn baseline đáng kể
    assert item.size.descent > 0.9 * XH


def test_matrix_columns_align(bank):
    item, _ = lay(bank, r"\begin{matrix} a & bb \\ cc & d \end{matrix}")
    boxes = glyph_boxes(item)
    assert len(boxes) == 6 and item.size.height > 2 * XH
    rows = sorted({round(b[3], 1) for b in boxes})
    assert len(rows) >= 2


def test_pmatrix_has_stretched_parentheses(bank):
    item, _ = lay(bank, r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}")
    assert len(item.strokes) == 2
    ys = [y for s in item.strokes for _, y in s.points]
    assert max(ys) - min(ys) >= 2 * XH


def test_cases_has_left_brace_only(bank):
    item, _ = lay(bank, r"\begin{cases} a \\ b \end{cases}")
    assert len(item.strokes) == 1
    assert max(x for x, _ in item.strokes[0].points) < item.size.width * 0.4


def test_aligned_aligns_relation_column(bank):
    item, _ = lay(bank, r"\begin{aligned} a &= b \\ cc &= d \end{aligned}")
    eq_x = sorted({round(s.points[0][0], 1) for s in item.strokes})
    assert len(eq_x) == 1, "dấu = của hai dòng phải thẳng cột"


def test_overrightarrow_spans_base_above(bank):
    plain, _ = lay(bank, "AB")
    item, _ = lay(bank, r"\overrightarrow{AB}")
    shaft = item.strokes[0].points
    assert shaft[0][0] <= 0.5 and shaft[1][0] >= plain.size.width - 1.0
    assert max(y for _, y in shaft) < -plain.size.ascent + 1e-6      # nằm phía trên chữ
    assert item.size.ascent > plain.size.ascent


def test_underline_below_and_overline_above(bank):
    under, _ = lay(bank, r"\underline{x}")
    over, _ = lay(bank, r"\overline{x}")
    assert under.strokes[0].points[0][1] > 0
    assert over.strokes[0].points[0][1] < -XH


def test_boxed_surrounds_content(bank):
    item, _ = lay(bank, r"\boxed{a}")
    box = item.strokes[0].points
    xs, ys = [p[0] for p in box], [p[1] for p in box]
    gb = glyph_boxes(item)[0]
    assert min(xs) < gb[0] and max(xs) > gb[2] and min(ys) < gb[1] and max(ys) > gb[3]


def test_relation_gets_wider_spacing_than_adjacent_letters(bank):
    ab, _ = lay(bank, "ab")
    a_eq_b, _ = lay(bank, "a=b")
    boxes = glyph_boxes(ab)
    gap_ord = boxes[1][0] - boxes[0][2]
    eq_item, _ = lay(bank, "=")
    assert a_eq_b.size.width - eq_item.size.width - 2 * (boxes[0][2] - boxes[0][0]) > 2 * gap_ord


def test_unary_minus_is_tighter_than_binary_minus(bank):
    un, _ = lay(bank, "-a")
    binary, _ = lay(bank, "b-a")
    a_w = glyph_boxes(un)[0][2] - glyph_boxes(un)[0][0]
    un_gap = un.size.width - a_w - lay(bank, "-")[0].size.width
    bin_gap = binary.size.width - 2 * a_w - lay(bank, "-")[0].size.width
    assert bin_gap > un_gap


def test_function_name_composed_from_letters_without_missing(bank):
    item, eng = lay(bank, r"\sin x")
    assert not eng.missing_symbols
    assert len(item.glyphs) == 2 and len(item.glyphs[0].strokes) == 3      # "sin" ghép từ 3 chữ cái + "x"


def test_variable_falls_back_to_letters_store(tmp_path):
    import gzip
    import json

    path = make_block_bank(str(tmp_path / "b.json.gz"), with_letters=False)
    data = json.load(gzip.open(path, "rt", encoding="utf-8"))
    data["symbols"] = {}
    data["letters"] = {"x": [{"w": 5.0, "s": [[0, 0, 4, -7]], "T": "", "vi": -1, "ti": -1}]}
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    bank = Bank(path)
    item, eng = lay(bank, "x")
    assert not eng.missing_symbols and item.glyphs


def test_blackboard_letter_uses_plain_letter_but_is_still_reported(bank):
    item, eng = lay(bank, r"\mathbb{R}")
    assert item.glyphs and eng.missing_symbols == {"ℝ": 1}


def test_vector_stand_ins_are_reported_as_missing(bank):
    item, eng = lay(bank, r"a \le b \pm c \to d")
    assert set(eng.missing_symbols) == {"≤", "±", "→"}
    assert item.strokes


def test_basic_operators_not_reported_missing(bank):
    _, eng = lay(bank, "a + b - c = d < e > f / g")
    assert eng.missing_symbols == {}


def test_unknown_macro_gets_placeholder_box(bank):
    item, eng = lay(bank, r"\unsupportedmacro")
    assert eng.missing_symbols == {"\\unsupportedmacro": 1}
    assert item.size.width >= 10.0


def test_scale_factor_scales_geometry(bank):
    a, _ = lay(bank, r"\frac{a}{b} + x^2", S=1.0)
    b, _ = lay(bank, r"\frac{a}{b} + x^2", S=2.0)
    assert b.size.width == pytest.approx(2 * a.size.width, rel=0.05)
    assert b.size.height == pytest.approx(2 * a.size.height, rel=0.05)


def test_layout_lines_breaks_long_formula_after_relations_or_operators(bank):
    wr = Writer(bank, random.Random(1))
    eng = MathLayoutEngine(bank, writer=wr, rnd=random.Random(1), display=True)
    ast = parse_latex_math(" + ".join(["a1"] * 40) + " = b")
    whole = eng.measure(ast)
    lines = eng.layout_lines(ast, max_width=whole.size.width / 3)
    assert len(lines) >= 3
    assert all(it.size.width <= whole.size.width / 3 + 1e-6 for it in lines)


def test_layout_lines_shrinks_unbreakable_item(bank):
    wr = Writer(bank, random.Random(1))
    eng = MathLayoutEngine(bank, writer=wr, rnd=random.Random(1), display=True)
    ast = parse_latex_math(r"\frac{abcdefgh}{ijklmnop}")
    whole = eng.measure(ast)
    lines = eng.layout_lines(ast, max_width=whole.size.width * 0.7)
    assert len(lines) == 1 and lines[0].size.width <= whole.size.width * 0.7 + 1e-6


def test_layout_lines_does_not_double_count_missing_symbols(bank):
    wr = Writer(bank, random.Random(1))
    eng = MathLayoutEngine(bank, writer=wr, rnd=random.Random(1), display=True)
    ast = parse_latex_math(r"a \le b \le c \le d \le e \le f \le g \le h")
    eng.layout_lines(ast, max_width=40.0)
    assert eng.missing_symbols == {"≤": 7}


def test_layout_lines_returns_single_line_when_it_fits(bank):
    wr = Writer(bank, random.Random(1))
    eng = MathLayoutEngine(bank, writer=wr, rnd=random.Random(1))
    assert len(eng.layout_lines(parse_latex_math("a+b"), max_width=1000.0)) == 1


def test_measure_handles_every_corpus_formula(bank):
    import os

    with open(os.path.join(os.path.dirname(__file__), "data", "math_corpus.txt"), encoding="utf-8") as f:
        for src in (ln for ln in f.read().splitlines() if ln.strip()):
            for display in (False, True):
                item, _ = lay(bank, src, display=display)
                assert item.size.width >= 0 and item.size.height >= 0
                pts = all_points(item)
                assert all(x == x and y == y for x, y in pts)        # không có NaN
