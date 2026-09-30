"""Kiểm thử phân tích cú pháp biểu thức toán học LaTeX và mở rộng macro (User Story 6 - L9, v2.1)."""
import pytest

from chuviettay.math.ast import (
    Fraction,
    MathRow,
    Root,
    Subscript,
    SubSuperscript,
    Superscript,
    SymbolNode,
    TextNode,
)
from chuviettay.math.parser import LATEX_SYMBOL_MAP, LatexMathParser, parse_latex_math


def test_nested_exponents_and_subscripts_inside_groups():
    """L9: Toán tử ^ và _ trong nhóm {...} phải tạo nút Superscript / Subscript đúng cú pháp."""
    # 1. \frac{x^2}{y}: tử số x^2 phải là Superscript, không phải 3 phần tử rời rạc ['x', '^', '2']
    row_frac = parse_latex_math(r"\frac{x^2}{y}")
    assert len(row_frac.items) == 1
    frac = row_frac.items[0]
    assert isinstance(frac, Fraction)
    assert len(frac.num.items) == 1
    num_node = frac.num.items[0]
    assert isinstance(num_node, Superscript)
    assert isinstance(num_node.base, TextNode) and num_node.base.text == "x"

    # 2. e^{x^2}: số mũ lồng nhau
    row_exp = parse_latex_math(r"e^{x^2}")
    assert len(row_exp.items) == 1
    exp_node = row_exp.items[0]
    assert isinstance(exp_node, Superscript)
    assert isinstance(exp_node.base, TextNode) and exp_node.base.text == "e"
    assert len(exp_node.exp.items) == 1
    inner_exp = exp_node.exp.items[0]
    assert isinstance(inner_exp, Superscript)

    # 3. a_{i_1}: chỉ số dưới lồng nhau
    row_sub = parse_latex_math(r"a_{i_1}")
    assert len(row_sub.items) == 1
    sub_node = row_sub.items[0]
    assert isinstance(sub_node, Subscript)
    assert isinstance(sub_node.base, TextNode) and sub_node.base.text == "a"
    assert len(sub_node.sub.items) == 1
    inner_sub = sub_node.sub.items[0]
    assert isinstance(inner_sub, Subscript)


def test_latex_standard_macros_expansion():
    r"""L9: Các macro chuẩn (\cdot, \to, \forall, \exists, \partial, \nabla,...) ánh xạ sang ký tự biểu tượng."""
    expr = r"a \cdot b \to c \forall x \exists y \partial z \nabla w \notin S \emptyset \ldots"
    row = parse_latex_math(expr)

    # Thu thập tất cả các symbol trong kết quả
    symbols = [item.symbol for item in row.items if isinstance(item, SymbolNode)]

    assert "·" in symbols or "⋅" in symbols, "\\cdot phải ánh xạ sang dấu chấm nhân"
    assert "→" in symbols, "\\to phải ánh xạ sang mũi tên sang phải"
    assert "∀" in symbols, "\\forall phải ánh xạ sang ∀"
    assert "∃" in symbols, "\\exists phải ánh xạ sang ∃"
    assert "∂" in symbols, "\\partial phải ánh xạ sang ∂"
    assert "∇" in symbols, "\\nabla phải ánh xạ sang ∇"
    assert "∉" in symbols, "\\notin phải ánh xạ sang ∉"
    assert "∅" in symbols, "\\emptyset phải ánh xạ sang ∅"
    assert "…" in symbols, "\\ldots phải ánh xạ sang dấu ba chấm …"


def test_greek_letters_alphabet():
    """Tất cả các chữ cái Hy Lạp phổ biến (hoa và thường) đều được hỗ trợ."""
    expr = r"\alpha \beta \gamma \delta \epsilon \zeta \eta \theta \iota \kappa \lambda \mu \nu \xi \pi \rho \sigma \tau \upsilon \phi \chi \psi \omega \Gamma \Delta \Theta \Lambda \Xi \Pi \Sigma \Phi \Psi \Omega"
    row = parse_latex_math(expr)
    symbols = [item.symbol for item in row.items if isinstance(item, SymbolNode)]

    assert "α" in symbols
    assert "β" in symbols
    assert "π" in symbols
    assert "Δ" in symbols
    assert "Ω" in symbols


def test_left_right_delimiters_handling():
    """\\left và \\right không được hiện thành chữ 'left'/'right'."""
    row = parse_latex_math(r"\left( \frac{a}{b} \right)")
    texts = [item.text for item in row.items if isinstance(item, TextNode)]
    assert "left" not in texts
    assert "right" not in texts


def test_text_and_mathrm_wrappers():
    """\\text{...} và \\mathrm{...} trích xuất nội dung văn bản."""
    row = parse_latex_math(r"\text{hello} + \mathrm{world}")
    texts = [item.text for item in row.items if isinstance(item, TextNode)]
    assert "hello" in texts
    assert "world" in texts


def test_unknown_macro_routes_to_symbol_not_plain_text():
    """Macro lạ không được in tên lệnh thành chữ thường mà định tuyến về SymbolNode để ghi nhận thiếu."""
    row = parse_latex_math(r"\unsupportedmacro")
    assert len(row.items) == 1
    item = row.items[0]
    assert isinstance(item, SymbolNode), "Macro lạ phải là SymbolNode chứ không phải TextNode('unsupportedmacro')"
    assert item.symbol == r"\unsupportedmacro"


def test_max_depth_recursion_limit():
    """Lồng nhau sâu tới 32 cấp không gây tràn ngăn xếp."""
    nested = "{" * 35 + "x" + "}" * 35
    row = parse_latex_math(nested)
    assert row is not None
