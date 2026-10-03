"""Kiểm tra trên kho công thức thật: không macro lạ, không rò rỉ LaTeX thô, AST -> LaTeX -> AST ổn định."""
import logging
import os
import random

import pytest

from chuviettay.math import SymbolNode, TextNode, parse_latex_math, parse_latex_math_with_warnings, to_latex, walk
from tests.mathtest_helpers import canon

CORPUS = os.path.join(os.path.dirname(__file__), "data", "math_corpus.txt")


def _corpus():
    with open(CORPUS, encoding="utf-8") as f:
        return [ln for ln in f.read().splitlines() if ln.strip()]


@pytest.mark.parametrize("src", _corpus())
def test_corpus_formula_parses_cleanly(src):
    ast, warns = parse_latex_math_with_warnings(src)
    assert warns == []
    # Không còn macro lạ (SymbolNode bắt đầu bằng '\') và không còn ký tự LaTeX thô trong chữ
    assert [n.symbol for n in walk(ast) if isinstance(n, SymbolNode) and n.symbol.startswith("\\") and len(n.symbol) > 1] == []
    assert [n.text for n in walk(ast) if isinstance(n, TextNode) and any(c in n.text for c in "\\{}")] == []


@pytest.mark.parametrize("src", _corpus())
def test_corpus_formula_roundtrip_is_stable(src):
    ast = parse_latex_math(src)
    again = parse_latex_math(to_latex(ast))
    assert canon(ast) == canon(again), to_latex(ast)


def test_to_latex_emits_decimal_comma_safely():
    ast = parse_latex_math(r"13{,}65 + 1,5")
    assert canon(parse_latex_math(to_latex(ast))) == canon(ast)


def test_to_latex_of_empty_and_none():
    assert to_latex(None) == ""
    assert to_latex(parse_latex_math("")) == ""


def test_random_token_soup_never_raises_and_terminates(caplog):
    caplog.set_level(logging.CRITICAL)
    rng = random.Random(1234)
    atoms = ["x", "y", "1", "23", ".", ",", "{", "}", "[", "]", "(", ")", "^", "_", "'", "&", r"\\", "+", "-", "=",
             r"\frac", r"\sqrt", r"\left", r"\right", r"\begin{matrix}", r"\end{matrix}", r"\begin{cases}",
             r"\end{cases}", r"\sum", r"\int", r"\text", r"\mathbb", r"\vec", r"\overline", r"\not", r"\over", r"\ ",
             r"\,", r"\alpha", r"\unknown", "$", "%", "~", "é", "∑", "≤", " "]
    for _ in range(600):
        src = "".join(rng.choice(atoms) for _ in range(rng.randint(1, 40)))
        ast = parse_latex_math(src)
        to_latex(ast)                       # xuất lại cũng không được lỗi
        parse_latex_math(to_latex(ast))
