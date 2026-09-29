"""Động cơ đo đạc và bố cục công thức toán học 2D căn chỉnh theo baseline."""
from __future__ import annotations

from dataclasses import dataclass, field
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


@dataclass
class MathLayoutItem:
    """Kết quả bố cục cho một nút toán học bao gồm kích thước và các nét vẽ tương đối."""
    size: Size
    glyphs: list[PositionedGlyph] = field(default_factory=list)
    strokes: list[PositionedStroke] = field(default_factory=list)


class MathLayoutEngine:
    """Động cơ tính toán kích thước, căn lề đường cơ sở và sinh nét vẽ cho biểu thức toán học."""

    def __init__(self, bank: Bank, S: float = 1.0):
        self.bank = bank
        self.S = S
        self.xh = float(bank.xh) * S
        self.missing_symbols: dict[str, int] = {}

    def measure(self, node: MathNode, scale: float = 1.0, depth: int = 0) -> MathLayoutItem:
        """Đo đạc đệ quy và định vị toạ độ tương đối (gốc (0,0) nằm tại baseline của phần tử)."""
        eff_scale = max(0.5 * self.S, scale)

        # 1. MathRow: Chuỗi phần tử nằm ngang cùng đường cơ sở
        if isinstance(node, MathRow):
            if not node.items:
                return MathLayoutItem(size=Size(width=0.0, height=0.0, ascent=0.0, descent=0.0, baseline=0.0))

            measured_items = [self.measure(it, eff_scale, depth) for it in node.items]
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
            char_w = 0.5 * self.xh * eff_scale
            w = max(5.0 * eff_scale, len(txt) * char_w)
            ascent = self.xh * eff_scale
            descent = 0.2 * self.xh * eff_scale
            return MathLayoutItem(
                size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)
            )

        # 3. SymbolNode: Ký hiệu toán học hoặc toán tử
        elif isinstance(node, SymbolNode):
            sym = node.symbol
            # Kiểm tra trong kho symbols
            if hasattr(self.bank, "symbols") and sym in self.bank.symbols and self.bank.symbols[sym]:
                sample = self.bank.symbols[sym][0]
                w = float(sample.get("w", 10.0)) * eff_scale
                ascent = 0.9 * self.xh * eff_scale
                descent = 0.2 * self.xh * eff_scale
                glyphs = [PositionedGlyph(strokes=sample.get("s", []), x=0.0, y=0.0, scale=eff_scale)]
                return MathLayoutItem(
                    size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent),
                    glyphs=glyphs,
                )
            elif sym in "+-=<>/*":
                # Toán tử chuẩn
                w = 0.7 * self.xh * eff_scale
                ascent = 0.7 * self.xh * eff_scale
                descent = 0.1 * self.xh * eff_scale
                return MathLayoutItem(
                    size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)
                )
            else:
                # Ký hiệu thiếu mẫu: tạo ô giữ chỗ kích thước cố định, ghi nhận missing_symbols
                self.missing_symbols[sym] = self.missing_symbols.get(sym, 0) + 1
                w = max(10.0 * eff_scale, 1.2 * self.xh * eff_scale)
                ascent = 0.9 * self.xh * eff_scale
                descent = 0.2 * self.xh * eff_scale
                return MathLayoutItem(
                    size=Size(width=w, height=ascent + descent, ascent=ascent, descent=descent, baseline=ascent)
                )

        # 4. Fraction: Phân số
        elif isinstance(node, Fraction):
            child_scale = max(0.5 * self.S, eff_scale * 0.85)
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
            base_item = self.measure(node.base, eff_scale, depth)
            exp_scale = max(0.5 * self.S, eff_scale * 0.7)
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
            base_item = self.measure(node.base, eff_scale, depth)
            sub_scale = max(0.5 * self.S, eff_scale * 0.7)
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
            base_item = self.measure(node.base, eff_scale, depth)
            child_scale = max(0.5 * self.S, eff_scale * 0.7)
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
            rad_item = self.measure(node.radicand, eff_scale, depth + 1)
            sign_w = 8.0 * eff_scale
            total_w = sign_w + rad_item.size.width + 3.0 * eff_scale
            top_y = -rad_item.size.ascent - 3.0 * eff_scale
            bot_y = rad_item.size.descent

            strokes = list(rad_item.strokes)
            glyphs = list(rad_item.glyphs)

            # Nét dấu căn vươn lên và thanh ngang phủ qua radicand
            radical_pts = [
                (0.0, -0.2 * self.xh * eff_scale),
                (sign_w * 0.4, bot_y),
                (sign_w * 0.8, top_y),
                (total_w, top_y),
            ]
            strokes.append(PositionedStroke(points=radical_pts, width=1.41 * eff_scale))

            # Dời radicand sang phải dấu căn
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
