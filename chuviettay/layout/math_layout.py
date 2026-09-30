"""Động cơ đo đạc và bố cục công thức toán học 2D căn chỉnh theo baseline."""
from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import TYPE_CHECKING

from chuviettay.layout.metrics import PositionedGlyph, PositionedStroke, Size
from chuviettay.math.ast import (
    Fraction,
    MathNode,
    MathRow,
    Root,
    Subscript,
    SubSuperscript,
    Superscript,
    SymbolNode,
    TextNode,
)

if TYPE_CHECKING:
    from chuviettay.model.bank import Bank
    from chuviettay.model.writer import Writer


@dataclass
class MathLayoutItem:
    """Kết quả bố cục cho một nút toán học bao gồm kích thước và các nét vẽ tương đối."""
    size: Size
    glyphs: list[PositionedGlyph] = field(default_factory=list)
    strokes: list[PositionedStroke] = field(default_factory=list)


class MathLayoutEngine:
    """Động cơ tính toán kích thước, căn lề đường cơ sở và sinh nét vẽ cho biểu thức toán học."""

    def __init__(
        self,
        bank: Bank,
        S: float = 1.0,
        writer: Writer | None = None,
        rnd: random.Random | None = None,
    ):
        self.bank = bank
        self.S = S
        self.xh = float(getattr(bank, "xh", 10.0))
        self.rnd = rnd or random.Random(42)
        from chuviettay.model.writer import Writer
        self.writer = writer or Writer(bank, self.rnd)
        self.missing_symbols: dict[str, int] = {}

    def measure(self, node: MathNode, scale: float = 1.0, depth: int = 0) -> MathLayoutItem:
        """Đo đạc đệ quy và định vị toạ độ tương đối (gốc (0,0) nằm tại baseline của phần tử)."""
        scale = max(0.2, scale)
        eff_scale = self.S * scale

        # 1. MathRow: Chuỗi phần tử nằm ngang cùng đường cơ sở
        if isinstance(node, MathRow):
            if not node.items:
                return MathLayoutItem(size=Size(width=0.0, height=0.0, ascent=0.0, descent=0.0, baseline=0.0))

            measured_items = [self.measure(it, scale, depth) for it in node.items]
            max_ascent = max((it.size.ascent for it in measured_items), default=self.xh * eff_scale)
            max_descent = max((it.size.descent for it in measured_items), default=0.2 * self.xh * eff_scale)

            total_w = 0.0
            all_glyphs: list[PositionedGlyph] = []
            all_strokes: list[PositionedStroke] = []
            spacing = 3.0 * eff_scale

            for idx, it in enumerate(measured_items):
                offset_x = total_w
                # Dời toạ độ các glyph và nét vẽ theo offset_x
                for g in it.glyphs:
                    all_glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + offset_x, y=g.y, scale=g.scale))
                for s in it.strokes:
                    shifted_pts = [(pt[0] + offset_x, pt[1]) for pt in s.points]
                    all_strokes.append(PositionedStroke(points=shifted_pts, width=s.width, color=s.color))

                total_w += it.size.width
                if idx < len(measured_items) - 1:
                    total_w += spacing

            return MathLayoutItem(
                size=Size(
                    width=total_w,
                    height=max_ascent + max_descent,
                    ascent=max_ascent,
                    descent=max_descent,
                    baseline=max_ascent,
                ),
                glyphs=all_glyphs,
                strokes=all_strokes,
            )

        # 2. TextNode: Từ hoặc số
        elif isinstance(node, TextNode):
            txt = node.text
            if not txt:
                return MathLayoutItem(size=Size(width=0.0, height=0.0, ascent=0.0, descent=0.0, baseline=0.0))

            if txt.isdigit():
                st, w, miss = self.writer.number(txt)
            else:
                st, w, miss = self.writer.token(txt)

            if miss:
                for m in miss:
                    self.missing_symbols[m] = self.missing_symbols.get(m, 0) + 1

            if st:
                scaled_w = w * eff_scale
                ys = [pt for stroke in st for pt in stroke[1::2]]
                has_ascender = any(c.isupper() or c in "bdfhklđ" for c in txt)
                if ys and has_ascender:
                    ascent = max(self.xh * eff_scale, -min(ys) * eff_scale)
                else:
                    ascent = self.xh * eff_scale

                has_descender = any(c in "gjpqy" for c in txt)
                if ys and has_descender:
                    descent = max(0.2 * self.xh * eff_scale, max(ys) * eff_scale)
                else:
                    descent = 0.2 * self.xh * eff_scale

                glyphs = [PositionedGlyph(strokes=st, x=0.0, y=0.0, scale=eff_scale)]
                return MathLayoutItem(
                    size=Size(width=scaled_w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent),
                    glyphs=glyphs,
                )
            else:
                char_w = 0.5 * self.xh * eff_scale
                w_fallback = max(10.0 * eff_scale, len(txt) * char_w)
                ascent = self.xh * eff_scale
                descent = 0.2 * self.xh * eff_scale
                return MathLayoutItem(
                    size=Size(width=w_fallback, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)
                )

        # 3. SymbolNode: Ký hiệu toán học hoặc toán tử
        elif isinstance(node, SymbolNode):
            sym = node.symbol
            # 3.1 Kiểm tra trong kho symbols
            if hasattr(self.bank, "symbols") and sym in self.bank.symbols and self.bank.symbols[sym]:
                sample = self.bank.symbols[sym][0]
                w = float(sample.get("w", 10.0)) * eff_scale
                s = sample.get("s", [])
                ys = [pt for stroke in s for pt in stroke[1::2]]
                if ys:
                    ascent = max(0.9 * self.xh * eff_scale, -min(ys) * eff_scale)
                    descent = max(0.2 * self.xh * eff_scale, max(ys) * eff_scale)
                else:
                    ascent = 0.9 * self.xh * eff_scale
                    descent = 0.2 * self.xh * eff_scale
                glyphs = [PositionedGlyph(strokes=sample.get("s", []), x=0.0, y=0.0, scale=eff_scale)]
                return MathLayoutItem(
                    size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent),
                    glyphs=glyphs,
                )

            # 3.2 Kiểm tra trong kho punct hoặc words của writer
            st, w, miss = self.writer.token(sym)
            if st and not miss:
                scaled_w = w * eff_scale
                ys = [pt for stroke in st for pt in stroke[1::2]]
                if ys:
                    ascent = max(0.8 * self.xh * eff_scale, -min(ys) * eff_scale)
                    descent = max(0.2 * self.xh * eff_scale, max(ys) * eff_scale)
                else:
                    ascent = 0.8 * self.xh * eff_scale
                    descent = 0.2 * self.xh * eff_scale
                glyphs = [PositionedGlyph(strokes=st, x=0.0, y=0.0, scale=eff_scale)]
                return MathLayoutItem(
                    size=Size(width=scaled_w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent),
                    glyphs=glyphs,
                )

            # 3.3 Toán tử chuẩn: sinh nét vector nếu chưa có mẫu trong kho
            if sym in "+-=<>/*":
                w = 0.7 * self.xh * eff_scale
                ascent = 0.7 * self.xh * eff_scale
                descent = 0.1 * self.xh * eff_scale
                pen_w = 1.41 * eff_scale
                op_strokes: list[PositionedStroke] = []
                mid_y = -0.45 * self.xh * eff_scale

                if sym == "-":
                    op_strokes.append(PositionedStroke(points=[(0.1 * w, mid_y), (0.9 * w, mid_y)], width=pen_w))
                elif sym == "=":
                    op_strokes.append(PositionedStroke(points=[(0.1 * w, mid_y - 2.5 * eff_scale), (0.9 * w, mid_y - 2.5 * eff_scale)], width=pen_w))
                    op_strokes.append(PositionedStroke(points=[(0.1 * w, mid_y + 2.5 * eff_scale), (0.9 * w, mid_y + 2.5 * eff_scale)], width=pen_w))
                elif sym == "+":
                    op_strokes.append(PositionedStroke(points=[(0.1 * w, mid_y), (0.9 * w, mid_y)], width=pen_w))
                    op_strokes.append(PositionedStroke(points=[(0.5 * w, mid_y - 0.4 * w), (0.5 * w, mid_y + 0.4 * w)], width=pen_w))
                elif sym == "/":
                    op_strokes.append(PositionedStroke(points=[(0.15 * w, mid_y + 0.45 * self.xh * eff_scale), (0.85 * w, mid_y - 0.45 * self.xh * eff_scale)], width=pen_w))
                elif sym == "<":
                    op_strokes.append(PositionedStroke(points=[(0.8 * w, mid_y - 0.35 * self.xh * eff_scale), (0.2 * w, mid_y), (0.8 * w, mid_y + 0.35 * self.xh * eff_scale)], width=pen_w))
                elif sym == ">":
                    op_strokes.append(PositionedStroke(points=[(0.2 * w, mid_y - 0.35 * self.xh * eff_scale), (0.8 * w, mid_y), (0.2 * w, mid_y + 0.35 * self.xh * eff_scale)], width=pen_w))

                return MathLayoutItem(
                    size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent),
                    strokes=op_strokes,
                )

            # 3.4 Ký hiệu thiếu mẫu: tạo ô giữ chỗ kích thước cố định, ghi nhận missing_symbols
            self.missing_symbols[sym] = self.missing_symbols.get(sym, 0) + 1
            w = max(10.0 * eff_scale, 1.2 * self.xh * eff_scale)
            ascent = 0.9 * self.xh * eff_scale
            descent = 0.2 * self.xh * eff_scale
            return MathLayoutItem(
                size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)
            )

        # 4. Fraction: Phân số
        elif isinstance(node, Fraction):
            child_scale = scale * 0.85
            num_item = self.measure(node.num, child_scale, depth + 1)
            den_item = self.measure(node.den, child_scale, depth + 1)

            frac_w = max(num_item.size.width, den_item.size.width) + 8.0 * eff_scale
            # Trục phân số nằm cao hơn baseline một khoảng
            math_axis = 0.45 * self.xh * eff_scale
            gap = 3.0 * eff_scale

            # Căn giữa tử số phía trên thanh gạch
            num_x = (frac_w - num_item.size.width) / 2.0
            num_y = -math_axis - gap - num_item.size.descent
            # Căn giữa mẫu số phía dưới thanh gạch
            den_x = (frac_w - den_item.size.width) / 2.0
            den_y = -math_axis + gap + den_item.size.ascent

            glyphs: list[PositionedGlyph] = []
            strokes: list[PositionedStroke] = []

            # Thêm đường gạch phân số
            strokes.append(PositionedStroke(points=[(0.0, -math_axis), (frac_w, -math_axis)], width=1.41 * eff_scale))

            # Chuyển dời toạ độ tử và mẫu
            for g in num_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + num_x, y=g.y + num_y, scale=g.scale))
            for s in num_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + num_x, pt[1] + num_y) for pt in s.points], width=s.width, color=s.color))

            for g in den_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + den_x, y=g.y + den_y, scale=g.scale))
            for s in den_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + den_x, pt[1] + den_y) for pt in s.points], width=s.width, color=s.color))

            total_ascent = math_axis + gap + num_item.size.height
            total_descent = gap + den_item.size.height - math_axis

            return MathLayoutItem(
                size=Size(
                    width=frac_w,
                    height=total_ascent + total_descent,
                    ascent=total_ascent,
                    descent=total_descent,
                    baseline=total_ascent,
                ),
                glyphs=glyphs,
                strokes=strokes,
            )

        # 5. Superscript: Số mũ
        elif isinstance(node, Superscript):
            base_item = self.measure(node.base, scale, depth)
            exp_scale = scale * 0.7
            exp_item = self.measure(node.exp, exp_scale, depth + 1)

            shift_y = -0.55 * base_item.size.ascent
            exp_x = base_item.size.width + 1.0 * eff_scale

            glyphs = list(base_item.glyphs)
            strokes = list(base_item.strokes)

            for g in exp_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + exp_x, y=g.y + shift_y, scale=g.scale))
            for s in exp_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + exp_x, pt[1] + shift_y) for pt in s.points], width=s.width, color=s.color))

            total_w = exp_x + exp_item.size.width
            total_ascent = max(base_item.size.ascent, -shift_y + exp_item.size.ascent)
            total_descent = base_item.size.descent

            return MathLayoutItem(
                size=Size(width=total_w, height=total_ascent + total_descent, ascent=total_ascent, descent=total_descent, baseline=total_ascent),
                glyphs=glyphs,
                strokes=strokes,
            )

        # 6. Subscript: Chỉ số dưới
        elif isinstance(node, Subscript):
            base_item = self.measure(node.base, scale, depth)
            sub_scale = scale * 0.7
            sub_item = self.measure(node.sub, sub_scale, depth + 1)

            shift_y = 0.35 * base_item.size.descent + 3.0 * eff_scale
            sub_x = base_item.size.width + 1.0 * eff_scale

            glyphs = list(base_item.glyphs)
            strokes = list(base_item.strokes)

            for g in sub_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + sub_x, y=g.y + shift_y, scale=g.scale))
            for s in sub_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + sub_x, pt[1] + shift_y) for pt in s.points], width=s.width, color=s.color))

            total_w = sub_x + sub_item.size.width
            total_ascent = base_item.size.ascent
            total_descent = max(base_item.size.descent, shift_y + sub_item.size.descent)

            return MathLayoutItem(
                size=Size(width=total_w, height=total_ascent + total_descent, ascent=total_ascent, descent=total_descent, baseline=total_ascent),
                glyphs=glyphs,
                strokes=strokes,
            )

        # 7. SubSuperscript: Cả chỉ số dưới và trên
        elif isinstance(node, SubSuperscript):
            base_item = self.measure(node.base, scale, depth)
            child_scale = scale * 0.7
            sub_item = self.measure(node.sub, child_scale, depth + 1)
            exp_item = self.measure(node.exp, child_scale, depth + 1)

            exp_shift_y = -0.55 * base_item.size.ascent
            sub_shift_y = 0.35 * base_item.size.descent + 3.0 * eff_scale
            child_x = base_item.size.width + 1.0 * eff_scale

            glyphs = list(base_item.glyphs)
            strokes = list(base_item.strokes)

            for g in exp_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + child_x, y=g.y + exp_shift_y, scale=g.scale))
            for s in exp_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + child_x, pt[1] + exp_shift_y) for pt in s.points], width=s.width, color=s.color))

            for g in sub_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + child_x, y=g.y + sub_shift_y, scale=g.scale))
            for s in sub_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + child_x, pt[1] + sub_shift_y) for pt in s.points], width=s.width, color=s.color))

            total_w = child_x + max(exp_item.size.width, sub_item.size.width)
            total_ascent = max(base_item.size.ascent, -exp_shift_y + exp_item.size.ascent)
            total_descent = max(base_item.size.descent, sub_shift_y + sub_item.size.descent)

            return MathLayoutItem(
                size=Size(width=total_w, height=total_ascent + total_descent, ascent=total_ascent, descent=total_descent, baseline=total_ascent),
                glyphs=glyphs,
                strokes=strokes,
            )

        # 8. Root: Căn thức
        elif isinstance(node, Root):
            rad_item = self.measure(node.radicand, scale, depth + 1)

            # Bậc căn thức (degree, ví dụ: \sqrt[3]{x})
            deg_item = None
            deg_w = 0.0
            if getattr(node, "degree", None) is not None:
                deg_scale = scale * 0.65
                deg_item = self.measure(node.degree, deg_scale, depth + 1)
                deg_w = deg_item.size.width

            sign_w = max(8.0 * eff_scale, deg_w + 3.0 * eff_scale)
            total_w = sign_w + rad_item.size.width + 3.0 * eff_scale
            top_y = -rad_item.size.ascent - 3.0 * eff_scale
            bot_y = rad_item.size.descent

            if deg_item:
                deg_top = -deg_item.size.ascent - 0.3 * self.xh * eff_scale
                top_y = min(top_y, deg_top)

            # Bắt đầu danh sách rỗng để KHÔNG bị lặp lại strokes/glyphs của radicand
            strokes: list[PositionedStroke] = []
            glyphs: list[PositionedGlyph] = []

            # 1. Đặt ký tự bậc căn (nếu có)
            if deg_item:
                deg_x = 0.0
                deg_y = -0.3 * self.xh * eff_scale
                for g in deg_item.glyphs:
                    glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + deg_x, y=g.y + deg_y, scale=g.scale))
                for s in deg_item.strokes:
                    strokes.append(PositionedStroke(points=[(pt[0] + deg_x, pt[1] + deg_y) for pt in s.points], width=s.width, color=s.color))

            # 2. Nét dấu căn vươn lên và thanh ngang phủ qua radicand
            hook_start_x = deg_w
            hook_w = sign_w - hook_start_x
            radical_pts = [
                (hook_start_x, -0.2 * self.xh * eff_scale),
                (hook_start_x + hook_w * 0.4, bot_y),
                (hook_start_x + hook_w * 0.8, top_y),
                (total_w, top_y),
            ]
            strokes.append(PositionedStroke(points=radical_pts, width=1.41 * eff_scale))

            # 3. Chỉ thêm duy nhất bản radicand đã được dịch sang phải dấu căn
            for g in rad_item.glyphs:
                glyphs.append(PositionedGlyph(strokes=g.strokes, x=g.x + sign_w, y=g.y, scale=g.scale))
            for s in rad_item.strokes:
                strokes.append(PositionedStroke(points=[(pt[0] + sign_w, pt[1]) for pt in s.points], width=s.width, color=s.color))

            total_ascent = -top_y
            total_descent = bot_y

            return MathLayoutItem(
                size=Size(width=total_w, height=total_ascent + total_descent, ascent=total_ascent, descent=total_descent, baseline=total_ascent),
                glyphs=glyphs,
                strokes=strokes,
            )

        # Mặc định an toàn
        return MathLayoutItem(size=Size(width=10.0 * eff_scale, height=self.xh * eff_scale, ascent=self.xh * eff_scale, descent=0.0, baseline=self.xh * eff_scale))
