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


def test_math_layout_root_deduplication(tiny_bank_path):
    """Kiểm tra căn thức không bị nhân đôi ký tự hoặc nét vẽ."""
    from chuviettay.model.bank import Bank
    from chuviettay.layout.math_layout import MathLayoutEngine

    bank = Bank(tiny_bank_path)
    engine = MathLayoutEngine(bank)

    # Biểu thức \sqrt{x^2 + 1}
    ast = parse_latex_math("\\sqrt{x^2 + 1}")
    root_node = ast.items[0]
    assert isinstance(root_node, Root)

    # Đo riêng radicand
    rad_item = engine.measure(root_node.radicand)
    rad_glyph_count = len(rad_item.glyphs)
    assert rad_glyph_count > 0, "Radicand phải chứa ít nhất 1 glyph"

    # Đo toàn bộ căn thức
    root_item = engine.measure(root_node)

    # Số lượng glyph trong căn thức PHẢI bằng chính xác số lượng glyph của radicand (không được nhân đôi)
    assert len(root_item.glyphs) == rad_glyph_count, (
        f"Lỗi nhân đôi glyph: có {len(root_item.glyphs)} glyphs nhưng radicand chỉ có {rad_glyph_count}"
    )

    # Mọi glyph trong căn thức đều phải được dịch sang phải dấu căn (x > 0)
    for g in root_item.glyphs:
        assert g.x >= 5.0, f"Glyph '{g.char}' vẫn ở toạ độ gốc (x={g.x})"

    # Nét vẽ trong root_item: 1 nét dấu căn + số nét đã dịch của radicand (không bị duplicate)
    assert len(root_item.strokes) == 1 + len(rad_item.strokes), (
        f"Lỗi nhân đôi nét: {len(root_item.strokes)} nét trong root_item so với {1 + len(rad_item.strokes)} nét mong đợi"
    )


def test_math_layout_root_with_degree(tiny_bank_path):
    r"""Kiểm tra căn thức bậc n (\sqrt[n]{x}) hiển thị đúng bậc và radicand."""
    from chuviettay.model.bank import Bank
    from chuviettay.layout.math_layout import MathLayoutEngine

    bank = Bank(tiny_bank_path)
    engine = MathLayoutEngine(bank)

    # tiny_bank có số '1' và '2'
    ast = parse_latex_math("\\sqrt[2]{1}")
    root_node = ast.items[0]
    assert isinstance(root_node, Root)
    assert root_node.degree is not None

    root_item = engine.measure(root_node)
    # Phải có 2 glyphs: 1 cho bậc '2' và 1 cho radicand '1'
    assert len(root_item.glyphs) == 2
    # Bậc căn phải đặt ở góc trái trước dấu căn (x < hook_start_x), radicand nằm sau dấu căn
    deg_g, rad_g = root_item.glyphs[0], root_item.glyphs[1]
    assert deg_g.x < rad_g.x


def test_math_layout_text_node_handwriting_strokes(real_bank):
    """Kiểm tra các biểu thức toán thực sự sinh nét chữ viết tay (total_glyph_strokes > 0) khi có mẫu trong kho."""
    from chuviettay.layout.math_layout import MathLayoutEngine

    # Cung cấp mẫu nét chữ cho biến toán học 'x' và 'i'
    real_bank.symbols["x"] = [{"s": [[0.0, 0.0, 5.0, -7.0], [0.0, -7.0, 5.0, 0.0]], "w": 6.0}]
    real_bank.symbols["i"] = [{"s": [[0.0, 0.0, 1.0, -5.0], [0.5, -7.0, 0.5, -6.5]], "w": 3.0}]

    engine = MathLayoutEngine(real_bank)

    formulas = [
        "x^2 + 1",
        "\\sqrt{x}",
        "\\sqrt{x^2 + 1}",
        "\\frac{x + 1}{2}",
        "x_i^2",
    ]

    for f in formulas:
        ast = parse_latex_math(f)
        item = engine.measure(ast)
        assert len(item.glyphs) > 0, f"Biểu thức '{f}' không sinh glyph nào"
        total_strokes = sum(len(g.strokes) for g in item.glyphs)
        assert total_strokes > 0, f"Biểu thức '{f}' có glyphs nhưng không có nét chữ viết tay nào"


