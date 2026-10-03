"""Động cơ đo đạc và bố cục công thức toán học 2D căn chỉnh theo baseline.

Mọi toạ độ tương đối với baseline của phần tử (y = 0 là đường cơ sở, y âm là phía trên). Mẫu chữ viết
tay lấy từ kho (Bank/Writer); ký hiệu chưa có mẫu được vẽ bằng nét vector dự phòng (xem
``vector_glyphs``) và vẫn được ghi vào ``missing_symbols`` để người dùng biết cần dạy thêm.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from chuviettay.layout import vector_glyphs as vg
from chuviettay.layout.metrics import PositionedGlyph, PositionedStroke, Size
from chuviettay.math.ast import (
    Accent,
    Boxed,
    Delimited,
    Fraction,
    Matrix,
    MathNode,
    MathRow,
    NAry,
    OverUnder,
    Root,
    SpaceNode,
    Subscript,
    SubSuperscript,
    Superscript,
    SymbolNode,
    TextNode,
)
from chuviettay.math.symbols import BIG_OPERATORS, SIDE_LIMIT_OPERATORS, symbol_class
from chuviettay.model.text_utils import shift

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer

# Khoảng cách giữa hai nguyên tử theo bảng của TeX (TeXbook, chương 18).
# 0 = không, 1 = thin (3mu), 2 = medium (4mu), 3 = thick (5mu); số âm = bỏ khi ở chỉ số trên/dưới.
_SPACING_ROWS = {
    #         ord op  bin rel opn cls pun inn
    "ord":   (0, 1, -2, -3, 0, 0, 0, -1),
    "op":    (1, 1, 0, -3, 0, 0, 0, -1),
    "bin":   (-2, -2, 0, 0, -2, 0, 0, -2),
    "rel":   (-3, -3, 0, 0, -3, 0, 0, -3),
    "open":  (0, 0, 0, 0, 0, 0, 0, 0),
    "close": (0, 1, -2, -3, 0, 0, 0, -1),
    "punct": (-1, -1, 0, -1, -1, -1, -1, -1),
    "inner": (-1, 1, -2, -3, -1, 0, -1, -1),
}
_CLASS_ORDER = ("ord", "op", "bin", "rel", "open", "close", "punct", "inner")
_MU = {1: 1.0 / 6.0, 2: 2.0 / 9.0, 3: 5.0 / 18.0}
_TIGHT = 0.09           # khe hở nhỏ giữa hai ký tự liền kề (em) - chữ viết tay cần chút thở
_HUG = 0.02             # sát ngoặc mở/đóng
_ALIAS_REPORTED = frozenset("ℝℕℤℚℂℙℍℓℏ")   # thay bằng chữ thường: vẫn báo là chưa có mẫu riêng
_VAR_NARROW_ACCENTS = frozenset({"hat", "tilde", "dot", "ddot", "dddot", "acute", "grave", "check",
                                 "breve", "mathring", "vec", "bar"})
_UNDER_ACCENTS = frozenset({"underline", "underbrace", "underrightarrow", "underleftarrow"})
_BASIC_OPERATORS = "+-=<>/*"


@dataclass
class MathLayoutItem:
    """Kết quả bố cục cho một nút toán học bao gồm kích thước và các nét vẽ tương đối."""
    size: Size
    glyphs: list[PositionedGlyph] = field(default_factory=list)
    strokes: list[PositionedStroke] = field(default_factory=list)


def _size(width: float, ascent: float, descent: float) -> Size:
    return Size(width=width, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)


def _zero() -> MathLayoutItem:
    return MathLayoutItem(size=Size(width=0.0, height=0.0, ascent=0.0, descent=0.0, baseline=0.0))


class _Canvas:
    """Gom glyph/nét từ nhiều mục con (mỗi mục dời theo một vector) thành một mục mới."""

    def __init__(self) -> None:
        self.glyphs: list[PositionedGlyph] = []
        self.strokes: list[PositionedStroke] = []

    def put(self, item: MathLayoutItem, dx: float, dy: float) -> None:
        for g in item.glyphs:
            self.glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + dx, y=g.y + dy, scale=g.scale))
        for s in item.strokes:
            self.strokes.append(PositionedStroke(
                points=[(px + dx, py + dy) for px, py in s.points], width=s.width, color=s.color))

    def line(self, points: list[tuple[float, float]], width: float) -> None:
        self.strokes.append(PositionedStroke(points=points, width=width))

    def polys(self, polys: list[list[tuple[float, float]]], ox: float, oy: float, width: float) -> None:
        for poly in polys:
            self.strokes.append(PositionedStroke(points=[(ox + x, oy + y) for x, y in poly], width=width))

    def build(self, width: float, ascent: float, descent: float) -> MathLayoutItem:
        return MathLayoutItem(size=_size(width, ascent, descent), glyphs=self.glyphs, strokes=self.strokes)


class MathLayoutEngine:
    """Động cơ tính toán kích thước, căn lề đường cơ sở và sinh nét vẽ cho biểu thức toán học."""

    def __init__(
        self,
        bank: Bank,
        S: float = 1.0,
        writer: Writer | None = None,
        rnd: random.Random | None = None,
        display: bool = False,
    ):
        self.bank = bank
        self.S = S
        self.xh = float(getattr(bank, "xh", 10.0))
        self.rnd = rnd or random.Random(42)
        from chuviettay.model.writer import Writer
        self.writer = writer or Writer(bank, self.rnd)
        self.missing_symbols: dict[str, int] = {}
        self.display = display
        self._script_level = 0
        self._frac_level = 0

    # ------------------------------------------------------------------ tiện ích
    def _em(self, eff: float) -> float:
        return 1.9 * self.xh * eff

    def _pen(self, eff: float) -> float:
        return 1.41 * eff

    def _miss(self, sym: str, count: int = 1) -> None:
        self.missing_symbols[sym] = self.missing_symbols.get(sym, 0) + count

    def _scratch(self) -> MathLayoutEngine:
        """Bản đo thử độc lập (Writer/RNG riêng) để ước lượng kích thước mà không làm lệch kết quả chính."""
        from chuviettay.model.writer import Writer
        w = self.writer
        sw = Writer(self.bank, random.Random(0), w.J, w.loose, w.space, assemble_letters=w.assemble_letters)
        return MathLayoutEngine(self.bank, S=self.S, writer=sw, rnd=random.Random(0), display=self.display)

    def _script(self, node: MathNode, scale: float, depth: int) -> MathLayoutItem:
        self._script_level += 1
        try:
            return self.measure(node, scale * 0.7, depth + 1)
        finally:
            self._script_level -= 1

    @property
    def _display_style(self) -> bool:
        return self.display and self._script_level == 0 and self._frac_level == 0

    # ------------------------------------------------------------------ điểm vào
    def measure(self, node: MathNode, scale: float = 1.0, depth: int = 0) -> MathLayoutItem:
        """Đo đạc đệ quy và định vị toạ độ tương đối (gốc (0,0) nằm tại baseline của phần tử)."""
        scale = max(0.2, scale)
        eff = self.S * scale
        handler = getattr(self, "_m_" + type(node).__name__, None)
        if handler is None or depth > 96:
            return MathLayoutItem(size=_size(10.0 * eff, self.xh * eff, 0.0))
        return handler(node, scale, eff, depth)

    # ------------------------------------------------------------------ hàng + khoảng cách TeX
    def _atom_class(self, n: MathNode) -> str:
        if isinstance(n, SymbolNode):
            return symbol_class(n.symbol)
        if isinstance(n, TextNode):
            return "op" if n.kind == "func" else "ord"
        if isinstance(n, SpaceNode):
            return "space"
        if isinstance(n, (Superscript, Subscript, SubSuperscript)):
            return self._atom_class(n.base)
        if isinstance(n, (Fraction, Delimited)):
            return "inner"
        if isinstance(n, NAry):
            return "op"
        if isinstance(n, MathRow) and len(n.items) == 1:
            return self._atom_class(n.items[0])
        return "ord"

    def _resolved_classes(self, items: list[MathNode]) -> list[str]:
        """Phân lớp từng nguyên tử và đổi toán tử hai ngôi thành 'ord' khi nó là dấu đơn ngôi (như -x)."""
        cls = [self._atom_class(it) for it in items]
        for i, c in enumerate(cls):
            if c != "bin":
                continue
            prev = next((cls[j] for j in range(i - 1, -1, -1) if cls[j] != "space"), None)
            nxt = next((cls[j] for j in range(i + 1, len(cls)) if cls[j] != "space"), None)
            if prev is None or prev in ("bin", "op", "rel", "open", "punct"):
                cls[i] = "ord"
            elif nxt is None or nxt in ("rel", "close", "punct"):
                cls[i] = "ord"
        return cls

    def _row_gaps(self, items: list[MathNode], eff: float) -> list[float]:
        """Khoảng cách giữa phần tử i và i+1 (độ dài len(items) - 1)."""
        cls = self._resolved_classes(items)
        em = self._em(eff)
        script = self._script_level > 0
        gaps: list[float] = []
        for i in range(len(items) - 1):
            a, b = cls[i], cls[i + 1]
            if a == "space" or b == "space":
                gaps.append(0.0)
                continue
            code = _SPACING_ROWS[a][_CLASS_ORDER.index(b)]
            if code == 0:
                gaps.append(em * (_HUG if (a == "open" or b == "close") else _TIGHT))
            elif code < 0 and script:
                gaps.append(em * _TIGHT)
            else:
                gaps.append(em * _MU[abs(code)])
        return gaps

    def _m_MathRow(self, node: MathRow, scale: float, eff: float, depth: int) -> MathLayoutItem:
        if not node.items:
            return _zero()
        measured = [self.measure(it, scale, depth) for it in node.items]
        gaps = self._row_gaps(node.items, eff)
        max_ascent = max((it.size.ascent for it in measured), default=self.xh * eff)
        max_descent = max((it.size.descent for it in measured), default=0.2 * self.xh * eff)

        canvas = _Canvas()
        x = 0.0
        for idx, it in enumerate(measured):
            canvas.put(it, x, 0.0)
            x += it.size.width
            if idx < len(measured) - 1:
                x += gaps[idx]
        return canvas.build(x, max_ascent, max_descent)

    def _m_SpaceNode(self, node: SpaceNode, scale: float, eff: float, depth: int) -> MathLayoutItem:
        return MathLayoutItem(size=Size(width=node.width * self._em(eff), height=0.0, ascent=0.0,
                                        descent=0.0, baseline=0.0))

    # ------------------------------------------------------------------ chữ / số / hàm
    def _letter_strokes(self, ch: str):
        """Mẫu một chữ cái: từ kho words/symbols/punct, rồi bank.letters (kể cả khi chưa bật --assemble)."""
        st, w, miss = self.writer.token(ch)
        if st and not miss:
            return st, w
        letters = getattr(self.bank, "letters", None) or {}
        lib = None
        if ch in letters:
            lib = letters[ch]
        elif self.writer.loose and ch.isupper() and ch.lower() in letters:
            lib = letters[ch.lower()]
        if not lib:
            return None
        inst = self.writer.pick(lib, "let:" + ch)
        return list(inst.get("s", [])), float(inst.get("w", self.xh))

    def _compose_letters(self, txt: str):
        """Ghép từng chữ cái (biến, tên hàm như sin) khi kho chưa có mẫu nguyên từ."""
        if len(txt) > 1:
            assembled = self.writer.assemble_word(txt)
            if assembled:
                return assembled
        strokes: list = []
        x = 0.0
        gap = 0.12 * self.xh
        for i, ch in enumerate(txt):
            got = self._letter_strokes(ch)
            if got is None:
                return None
            st, w = got
            strokes += [shift(s, x, 0) for s in st]
            x += w + (gap if i < len(txt) - 1 else 0.0)
        return strokes, x

    def _m_TextNode(self, node: TextNode, scale: float, eff: float, depth: int) -> MathLayoutItem:
        txt = node.text
        if not txt:
            return _zero()
        numeric = node.kind == "num" or (node.kind == "" and txt.isdigit())
        if numeric:
            st, w, miss = self.writer.number(txt)
        else:
            st, w, miss = self.writer.token(txt)
            composable = node.kind != "text" or len(txt) == 1
            if miss and txt.isalpha() and composable:
                composed = self._compose_letters(txt)
                if composed is not None:
                    (st, w), miss = composed, []
        for m in miss:
            self._miss(m)

        if st:
            ys = [pt for stroke in st for pt in stroke[1::2]]
            has_ascender = numeric or any(c.isupper() or c in "bdfhklđ" for c in txt)
            if ys and has_ascender:
                ascent = max(self.xh * eff, -min(ys) * eff)
            else:
                ascent = self.xh * eff
            has_descender = any(c in "gjpqy" for c in txt)
            if ys and has_descender:
                descent = max(0.2 * self.xh * eff, max(ys) * eff)
            else:
                descent = 0.2 * self.xh * eff
            return MathLayoutItem(
                size=_size(w * eff, ascent, descent),
                glyphs=[PositionedGlyph(strokes=st, x=0.0, y=0.0, scale=eff)],
            )
        char_w = 0.5 * self.xh * eff
        return MathLayoutItem(size=_size(max(10.0 * eff, len(txt) * char_w), self.xh * eff, 0.2 * self.xh * eff))

    # ------------------------------------------------------------------ ký hiệu
    def _glyph_item(self, strokes, w: float, eff: float, min_ascent: float) -> MathLayoutItem:
        ys = [pt for stroke in strokes for pt in stroke[1::2]]
        if ys:
            ascent = max(min_ascent * self.xh * eff, -min(ys) * eff)
            descent = max(0.2 * self.xh * eff, max(ys) * eff)
        else:
            ascent, descent = min_ascent * self.xh * eff, 0.2 * self.xh * eff
        return MathLayoutItem(
            size=_size(w * eff, ascent, descent),
            glyphs=[PositionedGlyph(strokes=strokes, x=0.0, y=0.0, scale=eff)],
        )

    def _vector_small(self, sym: str, eff: float) -> MathLayoutItem | None:
        g = vg.small_glyph(sym)
        if g is None:
            return None
        width, polys = g
        xh = self.xh * eff
        canvas = _Canvas()
        ys = [y for poly in polys for _, y in poly]
        for poly in polys:
            canvas.line([(x * xh, -y * xh) for x, y in poly], self._pen(eff))
        ascent = max(0.9, max(ys, default=0.9)) * xh
        descent = max(0.2, -min(ys, default=0.0)) * xh
        return canvas.build((width + 0.12) * xh, ascent, descent)

    def _basic_operator(self, sym: str, eff: float) -> MathLayoutItem:
        """Toán tử chuẩn + - = < > / *: sinh nét vector, không tính là 'thiếu mẫu'."""
        w = 0.7 * self.xh * eff
        ascent = 0.7 * self.xh * eff
        descent = 0.1 * self.xh * eff
        pen_w = self._pen(eff)
        pts: list[PositionedStroke] = []
        mid_y = -0.45 * self.xh * eff
        if sym == "-":
            pts.append(PositionedStroke(points=[(0.1 * w, mid_y), (0.9 * w, mid_y)], width=pen_w))
        elif sym == "=":
            pts.append(PositionedStroke(points=[(0.1 * w, mid_y - 2.5 * eff), (0.9 * w, mid_y - 2.5 * eff)], width=pen_w))
            pts.append(PositionedStroke(points=[(0.1 * w, mid_y + 2.5 * eff), (0.9 * w, mid_y + 2.5 * eff)], width=pen_w))
        elif sym == "+":
            pts.append(PositionedStroke(points=[(0.1 * w, mid_y), (0.9 * w, mid_y)], width=pen_w))
            pts.append(PositionedStroke(points=[(0.5 * w, mid_y - 0.4 * w), (0.5 * w, mid_y + 0.4 * w)], width=pen_w))
        elif sym == "/":
            pts.append(PositionedStroke(points=[(0.15 * w, mid_y + 0.45 * self.xh * eff),
                                                (0.85 * w, mid_y - 0.45 * self.xh * eff)], width=pen_w))
        elif sym == "<":
            pts.append(PositionedStroke(points=[(0.8 * w, mid_y - 0.35 * self.xh * eff), (0.2 * w, mid_y),
                                                (0.8 * w, mid_y + 0.35 * self.xh * eff)], width=pen_w))
        elif sym == ">":
            pts.append(PositionedStroke(points=[(0.2 * w, mid_y - 0.35 * self.xh * eff), (0.8 * w, mid_y),
                                                (0.2 * w, mid_y + 0.35 * self.xh * eff)], width=pen_w))
        elif sym == "*":
            star = self._vector_small("∗", eff)
            if star is not None:
                return star
        return MathLayoutItem(size=_size(w, ascent, descent), strokes=pts)

    def _normal_delimiter(self, ch: str, eff: float) -> MathLayoutItem | None:
        h = 1.55 * self.xh * eff
        w = 0.42 * self.xh * eff
        polys = vg.delimiter_polylines(ch, w, h)
        if polys is None:
            return None
        canvas = _Canvas()
        canvas.polys(polys, 0.0, -1.25 * self.xh * eff, self._pen(eff))
        return canvas.build(w + 0.12 * self.xh * eff, 1.25 * self.xh * eff, 0.3 * self.xh * eff)

    def _m_SymbolNode(self, node: SymbolNode, scale: float, eff: float, depth: int) -> MathLayoutItem:
        sym = node.symbol
        # 1. Kho symbols
        if hasattr(self.bank, "symbols") and sym in self.bank.symbols and self.bank.symbols[sym]:
            sample = self.bank.symbols[sym][0]
            return self._glyph_item(sample.get("s", []), float(sample.get("w", 10.0)), eff, 0.9)

        # 2. Kho punct / words / digits của writer
        st, w, miss = self.writer.token(sym)
        if st and not miss:
            return self._glyph_item(st, w, eff, 0.8)

        # 3. Ký hiệu đồng dạng thị giác trong kho (… ⇄ ⋯, · ⇄ ⋅, ∣ ⇄ |...)
        for alias in vg.SYMBOL_ALIASES.get(sym, ()):
            ast_, aw, amiss = self.writer.token(alias)
            if ast_ and not amiss:
                if sym in _ALIAS_REPORTED:
                    self._miss(sym)
                return self._glyph_item(ast_, aw, eff, 0.8)

        # 4. Toán tử chuẩn: nét vector, không tính là thiếu
        if len(sym) == 1 and sym in _BASIC_OPERATORS:
            return self._basic_operator(sym, eff)

        # 5. Nét vector dự phòng (vẫn ghi nhận 'thiếu mẫu' để người dùng dạy thêm)
        if sym in BIG_OPERATORS:
            item = self._bigop_item(sym, False, scale, eff, record=True)
            if item is not None:
                return item
        stand_in = self._vector_small(sym, eff) or self._normal_delimiter(sym, eff)
        if stand_in is not None:
            self._miss(sym)
            return stand_in

        # 6. Hoàn toàn chưa có: ô giữ chỗ cố định kích thước
        self._miss(sym)
        w = max(10.0 * eff, 1.2 * self.xh * eff)
        return MathLayoutItem(size=_size(w, 0.9 * self.xh * eff, 0.2 * self.xh * eff))

    # ------------------------------------------------------------------ phân số
    def _m_Fraction(self, node: Fraction, scale: float, eff: float, depth: int) -> MathLayoutItem:
        child_scale = scale * 0.85
        self._frac_level += 1
        try:
            num_item = self.measure(node.num, child_scale, depth + 1)
            den_item = self.measure(node.den, child_scale, depth + 1)
        finally:
            self._frac_level -= 1

        pad = 8.0 if node.bar else 2.0
        frac_w = max(num_item.size.width, den_item.size.width) + pad * eff
        math_axis = 0.45 * self.xh * eff
        gap = 3.0 * eff if node.bar else 1.5 * eff
        num_x = (frac_w - num_item.size.width) / 2.0
        num_y = -math_axis - gap - num_item.size.descent
        den_x = (frac_w - den_item.size.width) / 2.0
        den_y = -math_axis + gap + den_item.size.ascent

        canvas = _Canvas()
        if node.bar:
            canvas.line([(0.0, -math_axis), (frac_w, -math_axis)], 1.41 * eff)
        canvas.put(num_item, num_x, num_y)
        canvas.put(den_item, den_x, den_y)
        total_ascent = math_axis + gap + num_item.size.height
        total_descent = gap + den_item.size.height - math_axis
        return canvas.build(frac_w, total_ascent, total_descent)

    # ------------------------------------------------------------------ chỉ số trên / dưới
    def _scripted(self, base_node: MathNode, sub_node: MathNode | None, sup_node: MathNode | None,
                  scale: float, eff: float, depth: int) -> MathLayoutItem:
        base = self.measure(base_node, scale, depth)
        sup = self._script(sup_node, scale, depth) if sup_node is not None else None
        sub = self._script(sub_node, scale, depth) if sub_node is not None else None

        ref_ascent = base.size.ascent if base.size.ascent > 0 else self.xh * eff
        sup_y = -0.55 * ref_ascent
        sub_y = 0.35 * base.size.descent + 3.0 * eff
        child_x = base.size.width + 1.0 * eff

        canvas = _Canvas()
        canvas.put(base, 0.0, 0.0)
        width = child_x
        ascent, descent = base.size.ascent, base.size.descent
        if sup is not None:
            canvas.put(sup, child_x, sup_y)
            ascent = max(ascent, -sup_y + sup.size.ascent)
        if sub is not None:
            canvas.put(sub, child_x, sub_y)
            descent = max(descent, sub_y + sub.size.descent)
        width = child_x + max(sup.size.width if sup else 0.0, sub.size.width if sub else 0.0)
        return canvas.build(width, ascent, descent)

    def _m_Superscript(self, node: Superscript, scale: float, eff: float, depth: int) -> MathLayoutItem:
        return self._scripted(node.base, None, node.exp, scale, eff, depth)

    def _m_Subscript(self, node: Subscript, scale: float, eff: float, depth: int) -> MathLayoutItem:
        return self._scripted(node.base, node.sub, None, scale, eff, depth)

    def _m_SubSuperscript(self, node: SubSuperscript, scale: float, eff: float, depth: int) -> MathLayoutItem:
        return self._scripted(node.base, node.sub, node.exp, scale, eff, depth)

    # ------------------------------------------------------------------ căn thức
    def _m_Root(self, node: Root, scale: float, eff: float, depth: int) -> MathLayoutItem:
        rad_item = self.measure(node.radicand, scale, depth + 1)

        deg_item = None
        deg_w = 0.0
        if getattr(node, "degree", None) is not None:
            deg_item = self._script_like(node.degree, scale * 0.65, depth)
            deg_w = deg_item.size.width

        sign_w = max(8.0 * eff, deg_w + 3.0 * eff)
        total_w = sign_w + rad_item.size.width + 3.0 * eff
        top_y = -rad_item.size.ascent - 3.0 * eff
        bot_y = rad_item.size.descent

        if deg_item:
            deg_top = -deg_item.size.ascent - 0.3 * self.xh * eff
            top_y = min(top_y, deg_top)

        canvas = _Canvas()
        if deg_item:
            canvas.put(deg_item, 0.0, -0.3 * self.xh * eff)

        hook_start_x = deg_w
        hook_w = sign_w - hook_start_x
        canvas.line([
            (hook_start_x, -0.2 * self.xh * eff),
            (hook_start_x + hook_w * 0.4, bot_y),
            (hook_start_x + hook_w * 0.8, top_y),
            (total_w, top_y),
        ], 1.41 * eff)
        canvas.put(rad_item, sign_w, 0.0)
        return canvas.build(total_w, -top_y, bot_y)

    def _script_like(self, node: MathNode, scale: float, depth: int) -> MathLayoutItem:
        self._script_level += 1
        try:
            return self.measure(node, scale, depth + 1)
        finally:
            self._script_level -= 1

    # ------------------------------------------------------------------ ngoặc co giãn
    def _delimiter_item(self, ch: str, half: float, axis: float, scale: float, eff: float,
                        stretch: bool) -> MathLayoutItem:
        if not ch:
            return _zero()
        if stretch:
            h = 2.0 * half + 0.35 * self.xh * eff
            w = min(max(0.12 * h, 0.42 * self.xh * eff), 0.95 * self.xh * eff)
            polys = vg.delimiter_polylines(ch, w, h)
            if polys is not None:
                canvas = _Canvas()
                canvas.polys(polys, 0.0, -(axis + h / 2.0), self._pen(eff))
                return canvas.build(w + 0.1 * self.xh * eff, axis + h / 2.0, h / 2.0 - axis)
        return self._m_SymbolNode(SymbolNode(ch), scale, eff, 0)

    def _m_Delimited(self, node: Delimited, scale: float, eff: float, depth: int) -> MathLayoutItem:
        body = self.measure(node.body, scale, depth + 1)
        axis = 0.45 * self.xh * eff
        half = max(body.size.ascent - axis, body.size.descent + axis, 0.0)
        stretch = 2.0 * half > 1.75 * self.xh * eff
        left = self._delimiter_item(node.left, half, axis, scale, eff, stretch)
        right = self._delimiter_item(node.right, half, axis, scale, eff, stretch)
        pad = 1.0 * eff

        canvas = _Canvas()
        x = 0.0
        canvas.put(left, x, 0.0)
        x += left.size.width + (pad if node.left else 0.0)
        canvas.put(body, x, 0.0)
        x += body.size.width + (pad if node.right else 0.0)
        canvas.put(right, x, 0.0)
        x += right.size.width
        ascent = max(left.size.ascent, body.size.ascent, right.size.ascent)
        descent = max(left.size.descent, body.size.descent, right.size.descent)
        return canvas.build(x, ascent, descent)

    # ------------------------------------------------------------------ toán tử lớn có cận
    def _bigop_item(self, op: str, large: bool, scale: float, eff: float, record: bool = False
                    ) -> MathLayoutItem | None:
        """Ký hiệu ∑ ∏ ∫ ...: mẫu viết tay nếu có, nếu không thì vẽ vector cỡ lớn."""
        if not record:
            if hasattr(self.bank, "symbols") and op in self.bank.symbols and self.bank.symbols[op]:
                return self._m_SymbolNode(SymbolNode(op), scale, eff, 0)
            st, w, miss = self.writer.token(op)
            if st and not miss:
                return self._glyph_item(st, w, eff, 0.8)
        xh = self.xh * eff
        integral = op in SIDE_LIMIT_OPERATORS
        if integral:
            h = (3.0 if large else 2.3) * xh
            w = (0.75 + 0.45 * ({"∬": 1, "∭": 2}.get(op, 0))) * xh * (1.15 if large else 1.0)
        else:
            h = (2.7 if large else 2.0) * xh
            w = (1.5 if large else 1.25) * xh
        polys = vg.bigop_polylines(op, w, h)
        if polys is None:
            return None
        axis = 0.45 * xh
        canvas = _Canvas()
        canvas.polys(polys, 0.0, -(axis + h / 2.0), self._pen(eff))
        self._miss(op)
        return canvas.build(w + 1.0 * eff, axis + h / 2.0, h / 2.0 - axis)

    def _m_NAry(self, node: NAry, scale: float, eff: float, depth: int) -> MathLayoutItem:
        display = self._display_style
        if node.is_function:
            op = self._m_TextNode(TextNode(node.op, kind="func"), scale, eff, depth)
            tall = False
        else:
            op = self._bigop_item(node.op, display, scale, eff)
            if op is None:
                op = self._m_SymbolNode(SymbolNode(node.op), scale, eff, depth)
            tall = True
        stacked = node.limits if node.limits is not None else (
            display and (node.is_function or node.op not in SIDE_LIMIT_OPERATORS))

        sup = self._script(node.sup, scale, depth) if node.sup is not None else None
        sub = self._script(node.sub, scale, depth) if node.sub is not None else None
        canvas = _Canvas()
        gap = 2.0 * eff

        if stacked:
            width = max(op.size.width, sup.size.width if sup else 0.0, sub.size.width if sub else 0.0)
            canvas.put(op, (width - op.size.width) / 2.0, 0.0)
            ascent, descent = op.size.ascent, op.size.descent
            if sup is not None:
                y = -(op.size.ascent + gap + sup.size.descent)
                canvas.put(sup, (width - sup.size.width) / 2.0, y)
                ascent = -y + sup.size.ascent
            if sub is not None:
                y = op.size.descent + gap + sub.size.ascent
                canvas.put(sub, (width - sub.size.width) / 2.0, y)
                descent = y + sub.size.descent
            return canvas.build(width, ascent, descent)

        canvas.put(op, 0.0, 0.0)
        x = op.size.width + 1.0 * eff
        ascent, descent = op.size.ascent, op.size.descent
        sup_dx = 0.35 * op.size.width if (tall and node.op in SIDE_LIMIT_OPERATORS) else 0.0
        right = x
        if sup is not None:
            y = (sup.size.ascent - op.size.ascent) if tall else -0.55 * max(op.size.ascent, self.xh * eff)
            canvas.put(sup, x + sup_dx, y)
            ascent = max(ascent, -y + sup.size.ascent)
            right = max(right, x + sup_dx + sup.size.width)
        if sub is not None:
            y = (op.size.descent - sub.size.descent) if tall else 0.35 * op.size.descent + 3.0 * eff
            canvas.put(sub, x, y)
            descent = max(descent, y + sub.size.descent)
            right = max(right, x + sub.size.width)
        return canvas.build(right, ascent, descent)

    # ------------------------------------------------------------------ xếp chồng, dấu trang trí, khung
    def _m_OverUnder(self, node: OverUnder, scale: float, eff: float, depth: int) -> MathLayoutItem:
        base = self.measure(node.base, scale, depth)
        over = self._script(node.over, scale, depth) if node.over is not None else None
        under = self._script(node.under, scale, depth) if node.under is not None else None
        width = max(base.size.width, over.size.width if over else 0.0, under.size.width if under else 0.0)
        gap = 1.5 * eff
        canvas = _Canvas()
        canvas.put(base, (width - base.size.width) / 2.0, 0.0)
        ascent, descent = base.size.ascent, base.size.descent
        if over is not None:
            y = -(base.size.ascent + gap + over.size.descent)
            canvas.put(over, (width - over.size.width) / 2.0, y)
            ascent = -y + over.size.ascent
        if under is not None:
            y = base.size.descent + gap + under.size.ascent
            canvas.put(under, (width - under.size.width) / 2.0, y)
            descent = y + under.size.descent
        return canvas.build(width, ascent, descent)

    def _m_Accent(self, node: Accent, scale: float, eff: float, depth: int) -> MathLayoutItem:
        base = self.measure(node.base, scale, depth)
        xh = self.xh * eff
        kind = node.kind
        wb = max(base.size.width, 1.0 * eff)
        canvas = _Canvas()
        canvas.put(base, 0.0, 0.0)
        ascent, descent = base.size.ascent, base.size.descent

        if kind == "strike":
            polys = vg.accent_polylines(kind, wb, base.size.height)
            if polys:
                canvas.polys(polys, 0.0, -base.size.ascent, self._pen(eff))
            return canvas.build(wb, ascent, descent)

        height = {"overbrace": 0.55, "underbrace": 0.55, "dot": 0.3, "ddot": 0.3, "dddot": 0.3,
                  "vec": 0.5, "overrightarrow": 0.5, "overleftarrow": 0.5, "overleftrightarrow": 0.5,
                  "underrightarrow": 0.5, "underleftarrow": 0.5}.get(kind, 0.38) * xh
        width = min(wb, 1.0 * xh) if kind in _VAR_NARROW_ACCENTS and kind != "bar" else wb
        polys = vg.accent_polylines(kind, width, height)
        if polys is None:
            return canvas.build(wb, ascent, descent)
        gap = 0.15 * xh
        x0 = (wb - width) / 2.0
        if kind in _UNDER_ACCENTS:
            y0 = base.size.descent + gap
            descent = y0 + height
        else:
            y0 = -(base.size.ascent + gap + height)
            ascent = -y0
        canvas.polys(polys, x0, y0, self._pen(eff))
        return canvas.build(wb, ascent, descent)

    def _m_Boxed(self, node: Boxed, scale: float, eff: float, depth: int) -> MathLayoutItem:
        body = self.measure(node.body, scale, depth + 1)
        pad = 2.5 * eff
        canvas = _Canvas()
        canvas.put(body, pad, 0.0)
        w, top, bot = body.size.width + 2 * pad, -(body.size.ascent + pad), body.size.descent + pad
        canvas.line([(0.0, top), (w, top), (w, bot), (0.0, bot), (0.0, top)], self._pen(eff))
        return canvas.build(w, -top, bot)

    # ------------------------------------------------------------------ ma trận / hệ phương trình
    def _m_Matrix(self, node: Matrix, scale: float, eff: float, depth: int) -> MathLayoutItem:
        rows = node.rows
        if not rows:
            return _zero()
        ncols = max(len(r) for r in rows)
        cells = [[self.measure(c, scale, depth + 1) for c in r] for r in rows]
        xh = self.xh * eff
        em = self._em(eff)

        col_w = [0.0] * ncols
        for r in cells:
            for j, it in enumerate(r):
                col_w[j] = max(col_w[j], it.size.width)
        row_asc = [max([it.size.ascent for it in r] + [0.95 * xh]) for r in cells]
        row_desc = [max([it.size.descent for it in r] + [0.3 * xh]) for r in cells]
        row_gap = 0.5 * xh

        def col_gap_before(j: int) -> float:
            if node.kind == "aligned":
                return 0.0 if j % 2 == 1 else 1.6 * em
            return 0.9 * em

        col_x = []
        x = 0.0
        for j in range(ncols):
            x += col_gap_before(j) if j > 0 else 0.0
            col_x.append(x)
            x += col_w[j]
        total_w = x

        total_h = sum(row_asc) + sum(row_desc) + row_gap * (len(rows) - 1)
        axis = 0.45 * xh
        top = -(axis + total_h / 2.0)
        aligns = list(node.col_align) or ["c"] * ncols
        aligns += [aligns[-1] if aligns else "c"] * (ncols - len(aligns))

        canvas = _Canvas()
        y = top
        for i, r in enumerate(cells):
            baseline = y + row_asc[i]
            for j, it in enumerate(r):
                a = aligns[j]
                dx = col_x[j] + (0.0 if a == "l" else (col_w[j] - it.size.width) if a == "r"
                                 else (col_w[j] - it.size.width) / 2.0)
                canvas.put(it, dx, baseline)
            y += row_asc[i] + row_desc[i] + row_gap
        return canvas.build(total_w, axis + total_h / 2.0, total_h / 2.0 - axis)

    # ------------------------------------------------------------------ ngắt dòng công thức dài
    def layout_lines(self, node: MathNode, max_width: float, scale: float = 1.0) -> list[MathLayoutItem]:
        """Bố cục công thức vừa bề rộng ``max_width``: ngắt dòng sau quan hệ/toán tử/dấu phẩy ở hàng ngoài
        cùng; nếu một đoạn vẫn quá rộng thì thu nhỏ (tối đa còn 50%). Đo thử dùng bản sao nên không làm
        lệch RNG hay số liệu 'thiếu mẫu' của engine chính."""
        if max_width <= 0:
            return [self.measure(node, scale)]
        scratch = self._scratch()
        whole = scratch.measure(node, scale)
        if whole.size.width <= max_width:
            return [self.measure(node, scale)]

        items = list(node.items) if isinstance(node, MathRow) else [node]
        spans: list[tuple[int, int]] = [(0, len(items))]
        if len(items) > 1:
            eff = self.S * scale
            widths = [scratch.measure(it, scale).size.width for it in items]
            gaps = scratch._row_gaps(items, eff)
            cls = scratch._resolved_classes(items)

            def span_w(a: int, b: int) -> float:
                return sum(widths[a:b]) + sum(gaps[a : b - 1]) if b > a else 0.0

            spans, start, brk, i, n = [], 0, None, 0, len(items)
            while i < n:
                if span_w(start, i + 1) > max_width and i > start:
                    cut = brk + 1 if (brk is not None and brk >= start) else i
                    spans.append((start, cut))
                    start, brk = cut, None
                    continue
                if cls[i] in ("rel", "bin", "punct") and i < n - 1:
                    brk = i
                i += 1
            spans.append((start, n))

        lines: list[MathLayoutItem] = []
        for a, b in spans:
            part = MathRow(items[a:b]) if len(items) > 1 else node
            w = scratch.measure(part, scale).size.width
            sc = scale if w <= max_width else scale * max(0.5, max_width / w)
            lines.append(self.measure(part, sc))
        return lines
