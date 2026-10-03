"""Hồi quy bộ phân tích LaTeX: các lỗi thực tế gặp trong bài giải (khoảng, mũ, hàm, ngoặc, môi trường...)."""
import logging

import pytest

from chuviettay.math import (
    Accent, Delimited, Fraction, Matrix, MathRow, NAry, OverUnder, Root, SpaceNode, Subscript,
    SubSuperscript, Superscript, SymbolNode, TextNode, parse_latex_math, parse_latex_math_with_warnings, walk,
)


def items(latex):
    return parse_latex_math(latex).items


def symbols(latex):
    return [n.symbol for n in walk(parse_latex_math(latex)) if isinstance(n, SymbolNode)]


def test_closing_bracket_is_not_dropped():
    """Lỗi cũ: ']' ở cấp ngoài cùng bị bỏ im lặng nên [0,1] thành '[0,1'."""
    assert symbols(r"x \in [0,1]").count("]") == 1
    assert symbols("(a;b]") == ["(", ";", "]"]
    assert symbols("[a;b)") == ["[", ";", ")"]


def test_each_latin_letter_is_its_own_variable():
    """Lỗi cũ: 'xy^2' thành (xy)^2. Theo TeX mỗi chữ cái là một biến và chỉ y mang số mũ."""
    row = items("xy^2")
    assert row[0] == TextNode("x", "var")
    assert isinstance(row[1], Superscript) and row[1].base == TextNode("y", "var")


def test_unbraced_script_takes_exactly_one_token():
    """x^23 là x^2 theo sau số 3; x_ij là x_i theo sau j."""
    row = items("x^23")
    assert isinstance(row[0], Superscript) and row[0].exp.items == [TextNode("2", "num")]
    assert row[1] == TextNode("3", "num")
    row = items("x_ij")
    assert isinstance(row[0], Subscript) and row[1] == TextNode("j", "var")


def test_frac_with_unbraced_digits():
    frac = items(r"\frac12")[0]
    assert isinstance(frac, Fraction)
    assert frac.num.items == [TextNode("1", "num")] and frac.den.items == [TextNode("2", "num")]


def test_function_names_are_words_not_unknown_macros():
    for name in ("sin", "cos", "tan", "log", "ln", "lim", "max", "min", "exp"):
        row, warns = parse_latex_math_with_warnings("\\" + name + " x")
        assert row.items[0] == TextNode(name, "func"), name
        assert not warns


def test_limit_function_with_subscript_becomes_nary():
    nary = items(r"\lim_{x \to 0} f")[0]
    assert isinstance(nary, NAry) and nary.is_function and nary.op == "lim"
    assert [s.symbol for s in walk(nary.sub) if isinstance(s, SymbolNode)] == ["→"]


@pytest.mark.parametrize("latex,op", [(r"\sum_{i=1}^{n} i", "∑"), (r"\prod_k a_k", "∏"), (r"\int_0^1 f", "∫"),
                                      (r"\bigcup_i A_i", "⋃"), (r"\oint_C F", "∮")])
def test_big_operators_with_limits(latex, op):
    nary = items(latex)[0]
    assert isinstance(nary, NAry) and nary.op == op and not nary.is_function


def test_limits_and_nolimits_modifiers():
    assert items(r"\sum\limits_{i} x")[0].limits is True
    assert items(r"\int\nolimits_a^b x")[0].limits is False
    assert items(r"\sum_i x")[0].limits is None


def test_escaped_braces_percent_and_underscore():
    assert symbols(r"\{1, 2\}") == ["{", ",", "}"]
    assert symbols(r"50\%") == ["%"]
    assert symbols(r"a\_b") == ["_"]
    assert symbols(r"\$5 \& \#") == ["$", "&", "#"]


def test_left_right_with_brace_and_dot():
    d = items(r"\left\{ x \right.")[0]
    assert isinstance(d, Delimited) and (d.left, d.right) == ("{", "")
    d = items(r"\left. f \right|")[0]
    assert isinstance(d, Delimited) and (d.left, d.right) == ("", "|")
    d = items(r"\left\langle a \right\rangle")[0]
    assert (d.left, d.right) == ("⟨", "⟩")
    d = items(r"\left\| v \right\|")[0]
    assert (d.left, d.right) == ("‖", "‖")


def test_nested_left_right():
    outer = items(r"\left( \left[ x \right] + 1 \right)")[0]
    assert isinstance(outer, Delimited) and any(isinstance(n, Delimited) for n in walk(outer.body))


def test_mathbb_mathcal_use_unicode_letters():
    assert items(r"\mathbb{R}") == [SymbolNode("ℝ")]
    assert items(r"\mathbb{N}\mathbb{Z}\mathbb{Q}\mathbb{C}") == [SymbolNode(c) for c in "ℕℤℚℂ"]
    assert items(r"\mathcal{L}") == [SymbolNode("ℒ")]


def test_vietnamese_geometry_notation():
    vec = items(r"\overrightarrow{AB}")[0]
    assert isinstance(vec, Accent) and vec.kind == "overrightarrow"
    assert [t.text for t in vec.base.items] == ["A", "B"]
    angle = items(r"\widehat{ABC}")[0]
    assert isinstance(angle, Accent) and angle.kind == "widehat"
    assert items(r"\overline{AB}")[0].kind == "overline"
    assert items(r"\bar{p}")[0].kind == "bar"
    assert items(r"\vec{u}")[0].kind == "vec"
    assert set(symbols(r"\triangle ABC \parallel \perp")) == {"△", "∥", "⊥"}


def test_degree_sign_uses_degree_symbol():
    sup = items(r"90^\circ")[0]
    assert isinstance(sup, Superscript) and sup.exp.items == [SymbolNode("°")]
    assert items(r"f \circ g")[1] == SymbolNode("∘")      # ở ngoài số mũ vẫn là phép hợp


def test_primes_become_superscripts():
    f1 = items("f'")[0]
    assert isinstance(f1, Superscript) and f1.exp.items == [SymbolNode("′")]
    f2 = items("f''")[0]
    assert f2.exp.items == [SymbolNode("″")]
    sub = items("w'_A")[0]
    assert isinstance(sub, SubSuperscript) and sub.exp.items == [SymbolNode("′")]


def test_text_unescapes_and_splits_words():
    row = items(r"\text{body\_mass\_g}")
    assert row == [TextNode("body_mass_g", "text")]
    row = items(r"\text{Mật độ}")
    assert isinstance(row[0], MathRow)
    assert [n.text for n in row[0].items if isinstance(n, TextNode)] == ["Mật", "độ"]
    row = items(r"5\text{ kg}")
    assert row[0] == TextNode("5", "num")
    assert isinstance(row[1], MathRow) and isinstance(row[1].items[0], SpaceNode)


def test_mathrm_simple_word_vs_expression():
    assert items(r"\mathrm{d}x")[0] == TextNode("d", "text")
    assert items(r"\mathbf{\alpha}") == [SymbolNode("α")]       # lỗi cũ: rò rỉ chữ '\alpha' thô
    assert items(r"\mathbf{50.3\%}")[0].items[0] == TextNode("50.3", "num")


def test_decimal_numbers_are_single_tokens():
    assert items("13.65") == [TextNode("13.65", "num")]
    assert items("1.000.000") == [TextNode("1.000.000", "num")]
    assert items(r"0{,}5") == [TextNode("0,5", "num")]
    # dấu phẩy trần là dấu ngăn cách (khoảng, chỉ số) theo quy ước TeX
    assert items("0,5") == [TextNode("0", "num"), SymbolNode(","), TextNode("5", "num")]


def test_spacing_commands_and_tilde():
    row = items(r"a\,b\;c\quad d\qquad e\!f")
    widths = [n.width for n in row if isinstance(n, SpaceNode)]
    assert widths == pytest.approx([1 / 6, 5 / 18, 1.0, 2.0, -1 / 6], abs=1e-3)


def test_binom_and_over_and_choose():
    d = items(r"\binom{n}{k}")[0]
    assert isinstance(d, Delimited) and isinstance(d.body, Fraction) and not d.body.bar
    frac = items(r"{a \over b}")[0].items[0]
    assert isinstance(frac, Fraction) and frac.bar
    assert isinstance(items(r"{n \choose k}")[0].items[0], Delimited)


def test_sqrt_forms():
    r = items(r"\sqrt[3]{x+1}")[0]
    assert isinstance(r, Root) and r.degree.items == [TextNode("3", "num")]
    assert isinstance(items(r"\sqrt x")[0], Root)


def test_over_under_constructs():
    ou = items(r"\overset{def}{=}")[0]
    assert isinstance(ou, OverUnder) and ou.over is not None
    ub = items(r"\underbrace{a+b}_{n}")[0]
    assert isinstance(ub, OverUnder) and ub.under is not None and ub.base.kind == "underbrace"


@pytest.mark.parametrize("env,left,right", [("pmatrix", "(", ")"), ("bmatrix", "[", "]"), ("Bmatrix", "{", "}"),
                                            ("vmatrix", "|", "|"), ("Vmatrix", "‖", "‖")])
def test_matrix_environments(env, left, right):
    d = items(r"\begin{%s} 1 & 2 \\ 3 & 4 \end{%s}" % (env, env))[0]
    assert isinstance(d, Delimited) and (d.left, d.right) == (left, right)
    assert isinstance(d.body, Matrix) and len(d.body.rows) == 2 and len(d.body.rows[0]) == 2


def test_cases_and_aligned_and_array():
    d = items(r"\begin{cases} x+y=1 \\ x-y=3 \end{cases}")[0]
    assert isinstance(d, Delimited) and d.left == "{" and d.right == "" and d.body.kind == "cases"
    m = items(r"\begin{aligned} a &= b \\ c &= d \end{aligned}")[0]
    assert isinstance(m, Matrix) and m.kind == "aligned" and m.col_align[:2] == ["r", "l"]
    a = items(r"\begin{array}{lcr} 1 & 2 & 3 \end{array}")[0]
    assert a.kind == "array" and a.col_align == ["l", "c", "r"]


def test_top_level_row_breaks_become_lines():
    """Công thức display nhiều dòng không có \\begin{...}: \\\\ vẫn tách dòng."""
    m = items(r"a = b \\ c = d")[0]
    assert isinstance(m, Matrix) and len(m.rows) == 2
    m = items(r"a &= b \\ c &= d")[0]
    assert m.kind == "aligned"


def test_negations():
    assert symbols(r"a \not= b \not\in S") == ["≠", "∉"]
    assert symbols(r"a \ngtr b") == ["≯"]


def test_unknown_macro_still_routes_to_symbol_with_warning(caplog):
    with caplog.at_level(logging.WARNING):
        row, warns = parse_latex_math_with_warnings(r"\unsupportedmacro x")
    assert row.items[0] == SymbolNode("\\unsupportedmacro")
    assert any("unsupportedmacro" in w for w in warns)


def test_stray_closing_brace_is_reported_not_silent():
    row, warns = parse_latex_math_with_warnings("x}y")
    assert [n.text for n in row.items if isinstance(n, TextNode)] == ["x", "y"]
    assert warns and "}" in warns[0]


def test_unbalanced_left_is_reported():
    row, warns = parse_latex_math_with_warnings(r"\left( x")
    assert isinstance(row.items[0], Delimited) and row.items[0].right == ""
    assert any("\\left" in w for w in warns)


def test_stray_right_does_not_crash():
    row, warns = parse_latex_math_with_warnings(r"x \right) y")
    assert warns


@pytest.mark.parametrize("bad", ["", "   ", "{", "}", "^", "_", "x^", "x_", r"\frac", r"\frac{1}", r"\sqrt", r"\left",
                                 r"\begin{matrix}", r"\begin{pmatrix} 1 & 2 \\", r"\end{matrix}", "{{{{", "\\", "\\\\",
                                 "$", "&&&", r"\text{", r"\mathbb{", "a^^b", "a__b", r"\\\\\\"])
def test_malformed_input_never_raises(bad):
    parse_latex_math(bad)
    parse_latex_math_with_warnings(bad)


def test_deep_nesting_is_bounded_and_reported():
    deep = r"\frac{1}{" * 60 + "x" + "}" * 60
    row, warns = parse_latex_math_with_warnings(deep)
    assert any("32" in w for w in warns)
    deep_left = r"\left(" * 60 + "x" + r"\right)" * 60
    parse_latex_math(deep_left)
    deep_env = r"\begin{matrix}" * 50 + "x" + r"\end{matrix}" * 50
    parse_latex_math(deep_env)
    parse_latex_math("{" * 500 + "x" + "}" * 500)


def test_long_input_is_linear_enough():
    import time
    t = time.perf_counter()
    parse_latex_math(" + ".join(["x_{i}^{2}"] * 3000))
    assert time.perf_counter() - t < 2.0
