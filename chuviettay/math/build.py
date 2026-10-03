"""Hàm dựng nút AST dùng chung giữa bộ phân tích LaTeX và bộ chuyển đổi OMML (thuần dữ liệu)."""
from __future__ import annotations

from chuviettay.math.ast import MathNode, MathRow, SpaceNode, Subscript, SubSuperscript, Superscript, SymbolNode, TextNode

PRIME_CHARS = frozenset("′″‴")
_WORD_SPACE_EM = 0.4


def text_node(text: str, kind: str = "text") -> MathNode:
    """Chữ đứng thẳng (\\text, \\mathrm, hàm): tách theo từ, giữ khoảng trắng đầu/cuối."""
    words = text.split()
    if not words:
        return SpaceNode(0.33) if text else MathRow([])
    pieces: list[MathNode] = []
    if text[:1].isspace():
        pieces.append(SpaceNode(_WORD_SPACE_EM))
    for i, w in enumerate(words):
        if i:
            pieces.append(SpaceNode(_WORD_SPACE_EM))
        pieces.append(TextNode(w, kind=kind))
    if text[-1:].isspace():
        pieces.append(SpaceNode(_WORD_SPACE_EM))
    return pieces[0] if len(pieces) == 1 else MathRow(pieces)


def unwrap(row: MathNode) -> MathNode:
    """Hàng chỉ có một phần tử -> chính phần tử đó (để ^ _ bám vào phần tử thay vì nhóm)."""
    if isinstance(row, MathRow) and len(row.items) == 1:
        return row.items[0]
    return row


def degree_sign(exp: MathRow) -> MathRow:
    """Số mũ chỉ gồm ``∘`` (\\circ) là ký hiệu độ: đổi thành ``°``."""
    if len(exp.items) == 1 and isinstance(exp.items[0], SymbolNode) and exp.items[0].symbol == "∘":
        return MathRow([SymbolNode("°")])
    return exp


def fold_primes(nodes: list[MathNode]) -> list[MathNode]:
    """Dấu nháy ′ ″ ‴ đứng ngay sau một phần tử trở thành số mũ của phần tử đó (f′ -> f^′)."""
    out: list[MathNode] = []
    for n in nodes:
        if (
            isinstance(n, Subscript) and out
            and isinstance(n.base, SymbolNode) and n.base.symbol in PRIME_CHARS
            and not isinstance(out[-1], SpaceNode)
        ):
            # pandoc/Word: w + (′ với chỉ số dưới A) == w' _A: dấu nháy là số mũ của w, xếp chồng với chỉ số dưới
            prev = out.pop()
            out.append(SubSuperscript(base=prev, sub=n.sub, exp=MathRow([n.base])))
        elif isinstance(n, SymbolNode) and n.symbol in PRIME_CHARS and out:
            prev = out[-1]
            if isinstance(prev, (Superscript, SubSuperscript)) or isinstance(prev, SpaceNode):
                out.append(n)
            elif isinstance(prev, Subscript):
                out[-1] = SubSuperscript(base=prev.base, sub=prev.sub, exp=MathRow([n]))
            else:
                out[-1] = Superscript(base=prev, exp=MathRow([n]))
        else:
            out.append(n)
    return out
