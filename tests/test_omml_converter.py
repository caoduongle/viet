"""Bộ chuyển đổi OMML (Equation của Word) -> Math AST: từng cấu trúc, ký tự và trường hợp biên."""
import pytest
from lxml import etree

from chuviettay.importer.omml import M_NS, iter_omath, omml_to_ast, tokenize_run
from chuviettay.math import (
    Accent, Boxed, Delimited, Fraction, Matrix, NAry, OverUnder, Root, SpaceNode, Subscript,
    SubSuperscript, Superscript, SymbolNode, TextNode, parse_latex_math, to_latex,
)
from tests.mathtest_helpers import canon

NS = f'xmlns:m="{M_NS}" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# Tách ra hằng số: f-string chứa dấu gạch chéo ngược chỉ hợp lệ từ Python 3.12 (CI chạy cả 3.10/3.11)
STY_P = '<m:sty m:val="p"/>'


def r(text, props=""):
    pr = f"<m:rPr>{props}</m:rPr>" if props else ""
    return f"<m:r>{pr}<m:t>{text}</m:t></m:r>"


def conv(inner):
    el = etree.fromstring(f"<m:oMath {NS}>{inner}</m:oMath>")
    row, unsupported = omml_to_ast(el)
    return row, unsupported


def latex(inner):
    return to_latex(conv(inner)[0])


def only(inner):
    row, _ = conv(inner)
    assert len(row.items) == 1, row
    return row.items[0]


# ------------------------------------------------------------------ chuỗi trong một m:r
def test_single_run_is_tokenised_into_numbers_variables_operators():
    """Lỗi cũ: cả '2x+3=0' thành MỘT ký hiệu -> ô trống, không có nét nào."""
    row, _ = conv(r("2x+3=0"))
    assert row.items == [TextNode("2", "num"), TextNode("x", "var"), SymbolNode("+"), TextNode("3", "num"),
                         SymbolNode("="), TextNode("0", "num")]


def test_word_minus_sign_is_normalised():
    """Word dùng U+2212 cho dấu trừ; kho mẫu chỉ có '-'."""
    row, _ = conv(r("x\u2212y"))
    assert SymbolNode("-") in row.items and not any(
        isinstance(n, SymbolNode) and n.symbol == "\u2212" for n in row.items)


def test_multi_letter_italic_run_is_separate_variables():
    row, _ = conv(r("xyz"))
    assert [n.text for n in row.items] == ["x", "y", "z"]
    assert all(isinstance(n, TextNode) and n.kind == "var" for n in row.items)


def test_upright_style_makes_function_or_word():
    sty_p = '<m:sty m:val="p"/>'
    assert conv(r("sin", sty_p))[0].items == [TextNode("sin", "func")]
    assert conv(r("mm", sty_p))[0].items == [TextNode("mm", "text")]
    # không có sty=p thì "sin" gõ nghiêng vẫn là hàm sin (tên hàm chuẩn dài hơn 1 chữ)
    assert conv(r("sin"))[0].items == [TextNode("sin", "func")]
    assert conv(r("abc"))[0].items == [TextNode(c, "var") for c in "abc"]


def test_normal_text_run_keeps_words():
    row, _ = conv(r("nếu x&gt;0", "<m:nor/>"))
    assert [n.text for n in row.items if isinstance(n, TextNode)] == ["nếu", "x>0"]
    assert all(isinstance(n, (TextNode, SpaceNode)) for n in row.items)


def test_decimal_comma_inside_one_run_is_a_number_but_lists_are_not():
    assert conv(r("13,65"))[0].items == [TextNode("13,65", "num")]
    assert conv(r("0.2318"))[0].items == [TextNode("0.2318", "num")]
    assert conv(r("1,2,3"))[0].items == [TextNode("1", "num"), SymbolNode(","), TextNode("2", "num"),
                                         SymbolNode(","), TextNode("3", "num")]


def test_greek_and_letterlike_are_symbols():
    assert conv(r("α"))[0].items == [SymbolNode("α")]
    assert conv(r("ℝ"))[0].items == [SymbolNode("ℝ")]


def test_double_struck_script_property_maps_letters():
    assert conv(r("R", '<m:scr m:val="double-struck"/>'))[0].items == [SymbolNode("ℝ")]
    assert conv(r("N", '<m:scr m:val="double-struck"/>'))[0].items == [SymbolNode("ℕ")]


def test_unicode_spaces_become_space_nodes():
    row, _ = conv(r("a\u2001b"))
    assert isinstance(row.items[1], SpaceNode) and row.items[1].width == 1.0


def test_tokenize_run_direct():
    assert tokenize_run("a+1") == [TextNode("a", "var"), SymbolNode("+"), TextNode("1", "num")]


# ------------------------------------------------------------------ cấu trúc
def test_fraction_variants():
    f = only(f"<m:f><m:num>{r('a')}</m:num><m:den>{r('b')}</m:den></m:f>")
    assert isinstance(f, Fraction) and f.bar
    nb = only(f'<m:f><m:fPr><m:type m:val="noBar"/></m:fPr><m:num>{r("n")}</m:num><m:den>{r("k")}</m:den></m:f>')
    assert isinstance(nb, Fraction) and not nb.bar
    row, _ = conv(f'<m:f><m:fPr><m:type m:val="lin"/></m:fPr><m:num>{r("a")}</m:num><m:den>{r("b")}</m:den></m:f>')
    assert [type(n).__name__ for n in row.items] == ["TextNode", "SymbolNode", "TextNode"]


def test_scripts():
    sup = only(f"<m:sSup><m:e>{r('x')}</m:e><m:sup>{r('2')}</m:sup></m:sSup>")
    assert isinstance(sup, Superscript) and sup.base == TextNode("x", "var")
    sub = only(f"<m:sSub><m:e>{r('x')}</m:e><m:sub>{r('i')}</m:sub></m:sSub>")
    assert isinstance(sub, Subscript)
    both = only(f"<m:sSubSup><m:e>{r('x')}</m:e><m:sub>{r('i')}</m:sub><m:sup>{r('2')}</m:sup></m:sSubSup>")
    assert isinstance(both, SubSuperscript)
    row, _ = conv(f"<m:sPre><m:sub>{r('6')}</m:sub><m:sup>{r('14')}</m:sup><m:e>{r('C')}</m:e></m:sPre>")
    assert isinstance(row.items[0], SubSuperscript) and row.items[1] == TextNode("C", "var")


def test_degree_circle_in_superscript_becomes_degree_sign():
    sup = only(f"<m:sSup><m:e>{r('90')}</m:e><m:sup>{r('∘')}</m:sup></m:sSup>")
    assert sup.exp.items == [SymbolNode("°")]


def test_primes_fold_into_superscripts():
    row, _ = conv(r("f′") + f"<m:d><m:e>{r('x')}</m:e></m:d>")
    assert isinstance(row.items[0], Superscript) and row.items[0].exp.items == [SymbolNode("′")]
    # w′ có chỉ số dưới A (pandoc/Word) -> w'_A của LaTeX
    row, _ = conv(r("w") + f"<m:sSub><m:e>{r('′')}</m:e><m:sub>{r('A')}</m:sub></m:sSub>")
    assert len(row.items) == 1 and isinstance(row.items[0], SubSuperscript)
    assert canon(row) == canon(parse_latex_math("w'_A"))


def test_radical_with_and_without_degree():
    sq = only(f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{r("x")}</m:e></m:rad>')
    assert isinstance(sq, Root) and sq.degree is None
    cube = only(f"<m:rad><m:deg>{r('3')}</m:deg><m:e>{r('x')}</m:e></m:rad>")
    assert cube.degree.items == [TextNode("3", "num")]
    # Word luôn ghi <m:deg/> rỗng cho căn bậc hai kể cả khi không có degHide
    assert only(f"<m:rad><m:deg/><m:e>{r('x')}</m:e></m:rad>").degree is None


def test_delimiters_default_custom_empty_and_multi():
    paren = only(f"<m:d><m:e>{r('x')}</m:e></m:d>")
    assert isinstance(paren, Delimited) and (paren.left, paren.right) == ("(", ")")
    interval = only(f'<m:d><m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/><m:sepChr m:val=";"/></m:dPr>'
                    f"<m:e>{r('a')}</m:e><m:e>{r('b')}</m:e></m:d>")
    assert (interval.left, interval.right) == ("[", "]")
    assert SymbolNode(";") in interval.body.items and len(interval.body.items) == 3   # lỗi cũ: mất phần tử thứ 2
    left_only = only(f'<m:d><m:dPr><m:endChr m:val=""/></m:dPr><m:e>{r("x")}</m:e></m:d>')
    assert (left_only.left, left_only.right) == ("(", "")
    bars = only(f'<m:d><m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr><m:e>{r("x")}</m:e></m:d>')
    assert (bars.left, bars.right) == ("|", "|")
    angle = only(f'<m:d><m:dPr><m:begChr m:val="\u2225"/><m:endChr m:val="\u2225"/></m:dPr><m:e>{r("v")}</m:e></m:d>')
    assert (angle.left, angle.right) == ("‖", "‖")


def test_default_separator_is_pipe_and_empty_separator_is_none():
    piped = only(f"<m:d><m:e>{r('a')}</m:e><m:e>{r('b')}</m:e></m:d>")
    assert SymbolNode("|") in piped.body.items
    none = only(f'<m:d><m:dPr><m:sepChr m:val=""/></m:dPr><m:e>{r("a")}</m:e><m:e>{r("b")}</m:e></m:d>')
    assert [type(n).__name__ for n in none.body.items] == ["TextNode", "TextNode"]


def test_nary_sum_integral_and_hidden_limits():
    s = conv(f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr><m:sub>{r("i=1")}</m:sub>'
             f"<m:sup>{r('n')}</m:sup><m:e>{r('i')}</m:e></m:nary>")[0]
    nary, body = s.items[0], s.items[1:]
    assert isinstance(nary, NAry) and nary.op == "∑" and nary.limits is True and nary.sup is not None
    assert body == [TextNode("i", "var")]                         # thân đi ngay sau toán tử
    integral = conv(f'<m:nary><m:naryPr><m:supHide m:val="1"/></m:naryPr><m:sub>{r("0")}</m:sub><m:sup/>'
                    f"<m:e>{r('f')}</m:e></m:nary>")[0].items[0]
    assert integral.op == "∫" and integral.sup is None and integral.sub is not None   # mặc định ∫
    side = conv(f'<m:nary><m:naryPr><m:chr m:val="∫"/><m:limLoc m:val="subSup"/></m:naryPr><m:sub>{r("a")}</m:sub>'
                f"<m:sup>{r('b')}</m:sup><m:e>{r('f')}</m:e></m:nary>")[0].items[0]
    assert side.limits is False


def test_limit_and_function():
    lim = conv(f"<m:limLow><m:e>{r('lim', STY_P)}</m:e><m:lim>{r('x→0')}</m:lim></m:limLow>")[0].items[0]
    assert isinstance(lim, NAry) and lim.is_function and lim.op == "lim" and lim.limits is True
    under = only(f"<m:limLow><m:e>{r('x')}</m:e><m:lim>{r('n')}</m:lim></m:limLow>")
    assert isinstance(under, OverUnder) and under.under is not None
    over = only(f"<m:limUpp><m:e>{r('x')}</m:e><m:lim>{r('n')}</m:lim></m:limUpp>")
    assert isinstance(over, OverUnder) and over.over is not None
    row, _ = conv(f"<m:func><m:fName>{r('sin', STY_P)}</m:fName><m:e>{r('x')}</m:e></m:func>")
    assert row.items == [TextNode("sin", "func"), TextNode("x", "var")]


@pytest.mark.parametrize("chr_val,kind,base_text", [
    ("\u0302", "hat", "x"), ("\u0303", "tilde", "y"), ("\u0305", "bar", "p"), ("\u20d7", "vec", "u"),
    ("\u2192", "overrightarrow", "u"), ("\u0307", "dot", "z"), ("\u0308", "ddot", "z"),
    ("\u0302", "widehat", "ABC"), ("\u20d7", "overrightarrow", "AB"), ("\u0303", "widetilde", "xy"),
])
def test_accents(chr_val, kind, base_text):
    acc = only(f'<m:acc><m:accPr><m:chr m:val="{chr_val}"/></m:accPr><m:e>{r(base_text)}</m:e></m:acc>')
    assert isinstance(acc, Accent) and acc.kind == kind


def test_accent_default_is_hat():
    assert only(f"<m:acc><m:e>{r('x')}</m:e></m:acc>").kind == "hat"


def test_bar_top_and_bottom():
    assert only(f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{r("AB")}</m:e></m:bar>').kind == "overline"
    assert only(f'<m:bar><m:barPr><m:pos m:val="bot"/></m:barPr><m:e>{r("AB")}</m:e></m:bar>').kind == "underline"


def test_group_character_braces():
    under = only(f'<m:groupChr><m:groupChrPr><m:chr m:val="\u23df"/><m:pos m:val="bot"/></m:groupChrPr><m:e>{r("ab")}</m:e></m:groupChr>')
    assert isinstance(under, Accent) and under.kind == "underbrace"
    over = only(f'<m:groupChr><m:groupChrPr><m:chr m:val="\u23de"/><m:pos m:val="top"/></m:groupChrPr><m:e>{r("ab")}</m:e></m:groupChr>')
    assert over.kind == "overbrace"


def test_equation_array_and_cases():
    eq = only(f"<m:eqArr><m:e>{r('a&amp;=b')}</m:e><m:e>{r('c&amp;=d')}</m:e></m:eqArr>")
    assert isinstance(eq, Matrix) and eq.kind == "aligned" and all(len(row) == 2 for row in eq.rows)
    sys = only(f'<m:d><m:dPr><m:begChr m:val="{{"/><m:endChr m:val=""/></m:dPr><m:e><m:eqArr>'
               f"<m:e>{r('x+y=1')}</m:e><m:e>{r('x−y=3')}</m:e></m:eqArr></m:e></m:d>")
    assert isinstance(sys, Delimited) and (sys.left, sys.right) == ("{", "") and sys.body.kind == "cases"


def test_cases_equals_latex_cases():
    sys = conv(f'<m:d><m:dPr><m:begChr m:val="{{"/><m:endChr m:val=""/></m:dPr><m:e><m:eqArr>'
               f"<m:e>{r('x+y=1')}</m:e><m:e>{r('x−y=3')}</m:e></m:eqArr></m:e></m:d>")[0]
    assert canon(sys) == canon(parse_latex_math(r"\begin{cases} x+y=1 \\ x-y=3 \end{cases}"))


def test_matrix_with_column_alignment():
    m = only(f'<m:m><m:mPr><m:mcs><m:mc><m:mcPr><m:count m:val="2"/><m:mcJc m:val="left"/></m:mcPr></m:mc></m:mcs></m:mPr>'
             f"<m:mr><m:e>{r('1')}</m:e><m:e>{r('2')}</m:e></m:mr><m:mr><m:e>{r('3')}</m:e><m:e>{r('4')}</m:e></m:mr></m:m>")
    assert isinstance(m, Matrix) and len(m.rows) == 2 and m.col_align == ["l", "l"]
    plain = only(f"<m:m><m:mr><m:e>{r('1')}</m:e></m:mr></m:m>")
    assert plain.col_align == ["c"]


def test_pmatrix_matches_latex():
    row, _ = conv(f'<m:d><m:e><m:m><m:mr><m:e>{r("1")}</m:e><m:e>{r("2")}</m:e></m:mr>'
                  f'<m:mr><m:e>{r("3")}</m:e><m:e>{r("4")}</m:e></m:mr></m:m></m:e></m:d>')
    assert canon(row) == canon(parse_latex_math(r"\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}"))


def test_border_box_and_phantom():
    assert isinstance(only(f"<m:borderBox><m:e>{r('x')}</m:e></m:borderBox>"), Boxed)
    shown = conv(f"<m:phant><m:e>{r('x')}</m:e></m:phant>")[0]
    assert shown.items == [TextNode("x", "var")]
    hidden = conv(f'<m:phant><m:phantPr><m:show m:val="0"/></m:phantPr><m:e>{r("x")}</m:e></m:phant>')[0]
    assert isinstance(hidden.items[0], SpaceNode)


def test_box_is_transparent():
    assert conv(f"<m:box><m:e>{r('x')}</m:e></m:box>")[0].items == [TextNode("x", "var")]


def test_unknown_structure_is_reported_but_content_kept():
    row, unsupported = conv(f"<m:futureThing><m:e>{r('x')}</m:e></m:futureThing>")
    assert unsupported == ["futureThing"]
    assert row.items == [TextNode("x", "var")]


def test_property_elements_never_reported():
    _, unsupported = conv(f'<m:sSup><m:sSupPr><m:ctrlPr><w:rPr/></m:ctrlPr></m:sSupPr><m:e>{r("x")}</m:e><m:sup>{r("2")}</m:sup></m:sSup>')
    assert unsupported == []


def test_tracked_insertions_inside_math_are_kept_and_deletions_dropped():
    row, _ = conv("<w:ins><m:r><m:t>a</m:t></m:r></w:ins><w:del><m:r><m:t>b</m:t></m:r></w:del>")
    assert row.items == [TextNode("a", "var")]


def test_empty_and_degenerate_structures_do_not_crash():
    for inner in ("", "<m:f/>", "<m:d/>", "<m:nary/>", "<m:m/>", "<m:eqArr/>", "<m:rad/>", "<m:sSup/>",
                  "<m:acc/>", "<m:limLow/>", "<m:func/>", "<m:r/>", "<m:r><m:t/></m:r>"):
        conv(inner)


def test_iter_omath_handles_para_and_direct():
    para = etree.fromstring(f"<m:oMathPara {NS}><m:oMath>{r('a')}</m:oMath><m:oMath>{r('b')}</m:oMath></m:oMathPara>")
    assert len(list(iter_omath(para))) == 2
    single = etree.fromstring(f"<m:oMath {NS}>{r('a')}</m:oMath>")
    assert list(iter_omath(single)) == [single]


def test_ast_to_latex_for_typical_word_formula():
    """(−b ± √(b²−4ac)) / 2a gõ trong Word."""
    inner = (f"<m:f><m:num>{r('−b±')}<m:rad><m:radPr><m:degHide m:val=\"1\"/></m:radPr><m:deg/><m:e>"
             f"<m:sSup><m:e>{r('b')}</m:e><m:sup>{r('2')}</m:sup></m:sSup>{r('−4ac')}</m:e></m:rad></m:num>"
             f"<m:den>{r('2a')}</m:den></m:f>")
    assert canon(conv(inner)[0]) == canon(parse_latex_math(r"\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"))
