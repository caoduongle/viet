"""Kiểm thử sinh nét viết tay cho các nút toán học AST (biến số, chữ số, toán tử)."""
import pytest

from chuviettay.layout.math_layout import MathLayoutEngine
from chuviettay.math.ast import Fraction, MathRow, Superscript, SymbolNode, TextNode
from chuviettay.math.parser import parse_latex_math
from chuviettay.model.writer import Writer


def test_text_node_with_alphabetic_variable(tiny_bank):
    # tiny_bank có sẵn "ba"
    engine = MathLayoutEngine(tiny_bank)
    item = engine.measure(TextNode(text="ba"))
    assert item.size.width > 0
    assert len(item.glyphs) > 0 or len(item.strokes) > 0
    assert item.glyphs[0].strokes, "Phải có nét vẽ cho từ đã có mẫu trong bank"


def test_text_node_with_digits(tiny_bank):
    engine = MathLayoutEngine(tiny_bank)
    item = engine.measure(TextNode(text="12"))
    assert item.size.width > 0
    assert len(item.glyphs) > 0
    assert len(item.glyphs[0].strokes) > 0, "Phải có nét vẽ cho chữ số"


def test_math_formula_x2_plus_y2_equals_10(tiny_bank):
    # Dạy thêm "x" và "y" vào tiny_bank để đảm bảo có mẫu
    tiny_bank.words["x"] = [{"s": [[0, 0, 5, -10, 10, 0]], "w": 10.0}]
    tiny_bank.words["y"] = [{"s": [[0, 0, 5, 10, 10, -5]], "w": 10.0}]

    ast = parse_latex_math("x^2 + y^2 = 10")
    engine = MathLayoutEngine(tiny_bank)
    item = engine.measure(ast)

    assert item.size.width > 0
    # Phải có nét vẽ cho các biến x, y và số 2, 10
    total_strokes = len(item.strokes) + sum(len(g.strokes) for g in item.glyphs)
    assert total_strokes >= 5, f"Công thức x^2 + y^2 = 10 phải sinh đủ nét, thực tế: {total_strokes}"


def test_math_operators_fallback_strokes(tiny_bank):
    # tiny_bank chưa có ký hiệu toán trong symbols
    engine = MathLayoutEngine(tiny_bank)

    for op in ("+", "-", "=", "/"):
        item = engine.measure(SymbolNode(symbol=op))
        assert item.size.width > 0
        total_strokes = len(item.strokes) + sum(len(g.strokes) for g in item.glyphs)
        assert total_strokes > 0, f"Toán tử {op} phải có nét vẽ fallback hoặc mẫu, không được để trống"


def test_missing_math_variable_reserved_box(tiny_bank):
    engine = MathLayoutEngine(tiny_bank)
    item = engine.measure(TextNode(text="bien_chua_hoc"))
    assert "bien_chua_hoc" in engine.missing_symbols
    assert item.size.width >= 10.0, "Ký hiệu thiếu phải giữ ô kích thước để không vỡ bố cục"


def test_math_layout_engine_shares_writer(tiny_bank):
    writer = Writer(tiny_bank, rnd=None)
    engine = MathLayoutEngine(tiny_bank, writer=writer)
    assert engine.writer is writer
