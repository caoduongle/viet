"""Kiểm thử bộ phân tích cú pháp toán LaTeX và bố cục Math AST."""
import pytest

from chuviettay.document.ir import MathBlock, MathInline
from chuviettay.layout.metrics import Size
from chuviettay.math.ast import Fraction, MathRow, Root, Subscript, Superscript, SymbolNode, TextNode
from chuviettay.math.parser import parse_latex_math


def test_parse_latex_basic_tokens():
    ast = parse_latex_math("x + y = 10")
    assert isinstance(ast, MathRow)
    types = [type(item) for item in ast.items]
    assert TextNode in types
    assert SymbolNode in types


def test_parse_latex_fraction():
    ast = parse_latex_math("\\frac{a + 1}{b}")
    assert isinstance(ast, MathRow)
    assert len(ast.items) == 1
    frac = ast.items[0]
    assert isinstance(frac, Fraction)
    assert isinstance(frac.num, MathRow)
    assert isinstance(frac.den, MathRow)


def test_parse_latex_powers_and_indices():
    ast = parse_latex_math("x^2 + a_i")
    assert isinstance(ast, MathRow)
    assert any(isinstance(it, Superscript) for it in ast.items)
    assert any(isinstance(it, Subscript) for it in ast.items)


def test_parse_latex_square_root():
    ast = parse_latex_math("\\sqrt{x^2 + 1}")
    assert isinstance(ast, MathRow)
    assert len(ast.items) == 1
    root = ast.items[0]
    assert isinstance(root, Root)
    assert root.degree is None
    assert isinstance(root.radicand, MathRow)


def test_parse_latex_depth_limit():
    # Thử lồng quá 10 tầng phân số
    deep = "\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{\\frac{1}{2}}}}}}}}}}}"
    ast = parse_latex_math(deep)
    assert isinstance(ast, MathRow)


def test_math_layout_fraction_and_symbol_measurement(tiny_bank_path):
    from chuviettay.model.bank import Bank
    from chuviettay.layout.math_layout import MathLayoutEngine

    bank = Bank(tiny_bank_path)
    engine = MathLayoutEngine(bank)

    # 1. Đo phân số
    frac = Fraction(num=MathRow([TextNode("1")]), den=MathRow([TextNode("2")]))
    layout_item = engine.measure(frac)
    assert layout_item.size.width > 0
    assert layout_item.size.height > 0
    # Phải sinh đường gạch ngang phân số
    assert len(layout_item.strokes) >= 1

    # 2. Đo ký hiệu thiếu: không được đổ sụp về width 0
    sym = SymbolNode("∑")
    layout_sym = engine.measure(sym)
    assert layout_sym.size.width > 5.0
    assert "∑" in engine.missing_symbols
