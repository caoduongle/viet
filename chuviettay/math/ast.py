"""Cây cú pháp trừu tượng toán học (Math AST) cho biểu thức 2D."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MathNode:
    """Nút gốc cho mọi phần tử trong cây cú pháp toán học."""


@dataclass
class MathRow(MathNode):
    """Chuỗi tuyến tính các phần tử toán học đứng liền kề nhau trên cùng hàng."""
    items: list[MathNode] = field(default_factory=list)


@dataclass
class SymbolNode(MathNode):
    """Ký hiệu toán học, toán tử hoặc chữ cái Hy Lạp (ví dụ: +, -, =, ≤, ∑, π, α)."""
    symbol: str


@dataclass
class TextNode(MathNode):
    """Biến số, số hoặc hàm toán học (ví dụ: x, y, 123, sin, cos)."""
    text: str


@dataclass
class Fraction(MathNode):
    """Phân số gồm tử số và mẫu số phân cách bằng gạch phân số."""
    num: MathNode
    den: MathNode


@dataclass
class Superscript(MathNode):
    """Số mũ (chỉ số trên), ví dụ: x^2."""
    base: MathNode
    exp: MathNode


@dataclass
class Subscript(MathNode):
    """Chỉ số dưới, ví dụ: x_i."""
    base: MathNode
    sub: MathNode


@dataclass
class SubSuperscript(MathNode):
    """Phần tử có cả chỉ số dưới và số mũ thẳng hàng, ví dụ: x_i^2 hoặc tích phân có cận."""
    base: MathNode
    sub: MathNode
    exp: MathNode


@dataclass
class Root(MathNode):
    """Căn thức có dấu căn bao phủ biểu thức dưới căn (radicand) và bậc căn tuỳ chọn (degree)."""
    radicand: MathNode
    degree: MathNode | None = None
