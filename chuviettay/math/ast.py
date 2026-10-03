"""Cây cú pháp trừu tượng toán học (Math AST) cho biểu thức 2D."""
from __future__ import annotations

import dataclasses
from collections.abc import Iterator
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
    """Biến số, số hoặc hàm toán học (ví dụ: x, y, 123, sin, cos).

    ``kind`` cho biết vai trò để dàn trang đúng: ``"var"`` (một chữ cái biến), ``"num"`` (số),
    ``"func"`` (tên hàm như sin, lim), ``"text"`` (chữ đứng thẳng như \\text{...}); rỗng = tự suy ra.
    """
    text: str
    kind: str = ""


@dataclass
class SpaceNode(MathNode):
    """Khoảng trắng toán học (\\, \\; \\quad ...), ``width`` tính theo em (âm = lùi lại)."""
    width: float = 0.0


@dataclass
class Fraction(MathNode):
    """Phân số gồm tử số và mẫu số phân cách bằng gạch phân số (``bar=False``: không gạch)."""
    num: MathNode
    den: MathNode
    bar: bool = True


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


@dataclass
class Delimited(MathNode):
    """Cặp ngoặc co giãn theo nội dung (\\left( ... \\right) hoặc ``m:d`` của OMML).

    ``left``/``right`` rỗng nghĩa là không vẽ phía đó (\\left. hoặc \\right.).
    """
    left: str
    right: str
    body: MathNode


@dataclass
class NAry(MathNode):
    """Toán tử lớn có cận (∑ ∏ ∫ ⋃ ⋂ ... hoặc hàm đặt cận như lim, max, min).

    ``limits``: True = cận trên/dưới (khi display), False = cận bên cạnh, None = theo quy ước.
    ``is_function``: ``op`` là tên hàm (``lim``) chứ không phải ký hiệu lớn.
    """
    op: str
    sub: MathNode | None = None
    sup: MathNode | None = None
    limits: bool | None = None
    is_function: bool = False


@dataclass
class OverUnder(MathNode):
    """Phần tử gốc kèm nội dung xếp chồng phía trên và/hoặc phía dưới (\\overset, \\underset, limLow...)."""
    base: MathNode
    over: MathNode | None = None
    under: MathNode | None = None


@dataclass
class Accent(MathNode):
    """Dấu trang trí trên/dưới phần tử gốc: vectơ, mũ, gạch ngang, ngã, chấm, ngoặc nhọn...

    ``kind``: vec, overrightarrow, overleftarrow, overleftrightarrow, hat, widehat, tilde,
    widetilde, bar, overline, underline, dot, ddot, dddot, acute, grave, check, breve, mathring,
    overbrace, underbrace, underrightarrow, underleftarrow, strike.
    """
    base: MathNode
    kind: str


@dataclass
class Matrix(MathNode):
    """Lưới ô: ma trận, hệ cases, aligned, array (ngoặc bao quanh là ``Delimited`` bên ngoài).

    ``kind``: matrix (căn giữa), aligned (cột r/l xen kẽ), cases (căn trái), lines (một cột, căn giữa),
    array (theo ``col_align``). ``col_align`` mỗi phần tử là ``"l"``, ``"c"`` hoặc ``"r"``.
    """
    rows: list[list[MathNode]] = field(default_factory=list)
    kind: str = "matrix"
    col_align: list[str] = field(default_factory=list)


@dataclass
class Boxed(MathNode):
    """Khung chữ nhật bao quanh biểu thức (\\boxed, ``m:borderBox``)."""
    body: MathNode


def children(node: MathNode) -> Iterator[MathNode]:
    """Duyệt các nút con trực tiếp của ``node`` (tổng quát cho mọi loại nút)."""
    for f in dataclasses.fields(node):
        value = getattr(node, f.name)
        if isinstance(value, MathNode):
            yield value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, MathNode):
                    yield item
                elif isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, MathNode):
                            yield sub


def walk(node: MathNode) -> Iterator[MathNode]:
    """Duyệt toàn bộ cây (cha trước, con sau) bằng ngăn xếp nên không tràn đệ quy."""
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(reversed(list(children(cur))))
