"""Bộ phân tích cú pháp biểu thức toán học LaTeX (pure-Python, không dùng TeX ngoài)."""
from __future__ import annotations

import re

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

# Bản đồ các macro toán học phổ biến sang ký tự Unicode tương ứng
LATEX_SYMBOL_MAP: dict[str, str] = {
    "\\alpha": "α",
    "\\beta": "β",
    "\\gamma": "γ",
    "\\delta": "δ",
    "\\pi": "π",
    "\\theta": "θ",
    "\\lambda": "λ",
    "\\sigma": "σ",
    "\\omega": "ω",
    "\\Delta": "Δ",
    "\\Sigma": "Σ",
    "\\Omega": "Ω",
    "\\sum": "∑",
    "\\int": "∫",
    "\\prod": "∏",
    "\\pm": "±",
    "\\mp": "∓",
    "\\times": "×",
    "\\div": "÷",
    "\\le": "≤",
    "\\leq": "≤",
    "\\ge": "≥",
    "\\geq": "≥",
    "\\ne": "≠",
    "\\neq": "≠",
    "\\approx": "≈",
    "\\infty": "∞",
    "\\in": "∈",
    "\\subset": "⊂",
    "\\cap": "∩",
    "\\cup": "∪",
}


class LatexMathParser:
    """Bộ phân tích cú pháp LaTeX an toàn, pure-Python với chốt chặn độ sâu đệ quy."""

    MAX_DEPTH = 10

    def __init__(self, latex: str):
        self.raw = latex or ""
        self.pos = 0
        self.len = len(self.raw)

    def _skip_whitespace(self):
        while self.pos < self.len and self.raw[self.pos].isspace():
            self.pos += 1

    def _peek(self) -> str:
        self._skip_whitespace()
        if self.pos < self.len:
            return self.raw[self.pos]
        return ""

    def _consume(self, char: str) -> bool:
        self._skip_whitespace()
        if self.pos < self.len and self.raw[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse_group(self, depth: int = 0) -> MathRow:
        """Đọc một nhóm trong ngoặc nhọn {...} hoặc một ký tự đơn."""
        if depth > self.MAX_DEPTH:
            self._skip_whitespace()
            if self._consume("{"):
                count = 1
                while self.pos < self.len and count > 0:
                    if self.raw[self.pos] == "{":
                        count += 1
                    elif self.raw[self.pos] == "}":
                        count -= 1
                    self.pos += 1
            elif self.pos < self.len:
                self.pos += 1
            return MathRow([TextNode("...")])

        self._skip_whitespace()
        if self.pos >= self.len:
            return MathRow([])

        if self._consume("{"):
            items = []
            while self.pos < self.len and self._peek() != "}":
                old_pos = self.pos
                elem = self.parse_element(depth=depth + 1)
                if elem:
                    items.append(elem)
                if self.pos == old_pos:
                    self.pos += 1
            self._consume("}")
            return MathRow(items)
        else:
            elem = self.parse_element(depth=depth + 1)
            return MathRow([elem]) if elem else MathRow([])

    def parse_bracket_group(self, depth: int = 0) -> MathRow | None:
        """Đọc một nhóm trong ngoặc vuông [...]."""
        if depth > self.MAX_DEPTH:
            self._skip_whitespace()
            if self._consume("["):
                count = 1
                while self.pos < self.len and count > 0:
                    if self.raw[self.pos] == "[":
                        count += 1
                    elif self.raw[self.pos] == "]":
                        count -= 1
                    self.pos += 1
                return MathRow([TextNode("...")])
            return None

        self._skip_whitespace()
        if self._consume("["):
            items = []
            while self.pos < self.len and self._peek() != "]":
                old_pos = self.pos
                elem = self.parse_element(depth=depth + 1)
                if elem:
                    items.append(elem)
                if self.pos == old_pos:
                    self.pos += 1
            self._consume("]")
            return MathRow(items)
        return None

    def parse_element(self, depth: int = 0) -> MathNode | None:
        """Đọc một phần tử cơ bản (lệnh, ký hiệu, hoặc văn bản)."""
        if depth > self.MAX_DEPTH:
            self._skip_whitespace()
            if self.pos >= self.len:
                return None
            if self.raw[self.pos] == "\\":
                match = re.match(r"\\[a-zA-Z]+", self.raw[self.pos:])
                if match:
                    self.pos += len(match.group(0))
                else:
                    self.pos += 1
            elif self.raw[self.pos] == "{":
                count = 1
                self.pos += 1
                while self.pos < self.len and count > 0:
                    if self.raw[self.pos] == "{":
                        count += 1
                    elif self.raw[self.pos] == "}":
                        count -= 1
                    self.pos += 1
            else:
                self.pos += 1
            return TextNode("...")

        self._skip_whitespace()
        if self.pos >= self.len:
            return None

        ch = self.raw[self.pos]

        # 1. Macro lệnh LaTeX bắt đầu bằng dấu gạch chéo ngược \
        if ch == "\\":
            match = re.match(r"\\[a-zA-Z]+", self.raw[self.pos:])
            if match:
                cmd = match.group(0)
                self.pos += len(cmd)

                if cmd == "\\frac":
                    num = self.parse_group(depth + 1)
                    den = self.parse_group(depth + 1)
                    return Fraction(num=num, den=den)
                elif cmd == "\\sqrt":
                    degree = self.parse_bracket_group(depth + 1)
                    radicand = self.parse_group(depth + 1)
                    return Root(radicand=radicand, degree=degree)
                elif cmd in LATEX_SYMBOL_MAP:
                    return SymbolNode(symbol=LATEX_SYMBOL_MAP[cmd])
                else:
                    # Lệnh chưa có trong danh mục biểu tượng: hiển thị tên lệnh
                    return TextNode(text=cmd.lstrip("\\"))
            else:
                self.pos += 1
                return SymbolNode(symbol="\\")

        # 2. Nhóm ngoặc nhọn lồng nhau {...}
        if ch == "{":
            return self.parse_group(depth + 1)

        # 3. Ký tự đóng ngoặc: dừng đọc phần tử
        if ch in ("}", "]"):
            return None

        # 4. Ký hiệu toán học đơn lẻ
        if ch in "+-=<>()[]/*|!:,;":
            self.pos += 1
            return SymbolNode(symbol=ch)

        # 5. Số (digits)
        match_num = re.match(r"[0-9]+", self.raw[self.pos:])
        if match_num:
            txt = match_num.group(0)
            self.pos += len(txt)
            return TextNode(text=txt)

        # 6. Biến chữ hoặc từ ngữ (alphabetic identifiers)
        match_alpha = re.match(r"[a-zA-Z]+", self.raw[self.pos:])
        if match_alpha:
            txt = match_alpha.group(0)
            self.pos += len(txt)
            return TextNode(text=txt)

        # 7. Các ký tự Unicode khác
        self.pos += 1
        return SymbolNode(symbol=ch)

    def parse(self) -> MathRow:
        """Phân tích toàn bộ chuỗi LaTeX và xử lý các toán tử chỉ số trên/dưới (^ và _)."""
        items: list[MathNode] = []

        while self.pos < self.len:
            self._skip_whitespace()
            if self.pos >= self.len:
                break

            ch = self.raw[self.pos]

            if ch == "^":
                self.pos += 1
                exp = self.parse_group()
                if items:
                    prev = items.pop()
                    if isinstance(prev, Subscript):
                        items.append(SubSuperscript(base=prev.base, sub=prev.sub, exp=exp))
                    else:
                        items.append(Superscript(base=prev, exp=exp))
                else:
                    items.append(Superscript(base=TextNode(""), exp=exp))
            elif ch == "_":
                self.pos += 1
                sub = self.parse_group()
                if items:
                    prev = items.pop()
                    if isinstance(prev, Superscript):
                        items.append(SubSuperscript(base=prev.base, sub=sub, exp=prev.exp))
                    else:
                        items.append(Subscript(base=prev, sub=sub))
                else:
                    items.append(Subscript(base=TextNode(""), sub=sub))
            else:
                old_pos = self.pos
                elem = self.parse_element()
                if elem:
                    items.append(elem)
                elif self.pos == old_pos and self.pos < self.len:
                    self.pos += 1

        return MathRow(items=items)


def parse_latex_math(latex: str) -> MathRow:
    """Hàm tiện ích chuyển đổi nhanh chuỗi biểu thức LaTeX sang Math AST."""
    parser = LatexMathParser(latex)
    return parser.parse()
