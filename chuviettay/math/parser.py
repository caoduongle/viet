"""Bộ phân tích cú pháp biểu thức toán học LaTeX (pure-Python, không dùng TeX ngoài)."""
from __future__ import annotations

import logging
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

_log = logging.getLogger(__name__)

# Bản đồ các macro toán học phổ biến sang ký tự Unicode tương ứng
LATEX_SYMBOL_MAP: dict[str, str] = {
    # Chữ cái Hy Lạp thường
    "\\alpha": "α",
    "\\beta": "β",
    "\\gamma": "γ",
    "\\delta": "δ",
    "\\epsilon": "ϵ",
    "\\varepsilon": "ε",
    "\\zeta": "ζ",
    "\\eta": "η",
    "\\theta": "θ",
    "\\vartheta": "ϑ",
    "\\iota": "ι",
    "\\kappa": "κ",
    "\\lambda": "λ",
    "\\mu": "μ",
    "\\nu": "ν",
    "\\xi": "ξ",
    "\\pi": "π",
    "\\varpi": "ϖ",
    "\\rho": "ρ",
    "\\varrho": "ϱ",
    "\\sigma": "σ",
    "\\varsigma": "ς",
    "\\tau": "τ",
    "\\upsilon": "υ",
    "\\phi": "ϕ",
    "\\varphi": "φ",
    "\\chi": "χ",
    "\\psi": "ψ",
    "\\omega": "ω",
    # Chữ cái Hy Lạp hoa
    "\\Gamma": "Γ",
    "\\Delta": "Δ",
    "\\Theta": "Θ",
    "\\Lambda": "Λ",
    "\\Xi": "Ξ",
    "\\Pi": "Π",
    "\\Sigma": "Σ",
    "\\Upsilon": "Υ",
    "\\Phi": "Φ",
    "\\Psi": "Ψ",
    "\\Omega": "Ω",
    # Toán tử, dấu so sánh & ký hiệu tập hợp
    "\\sum": "∑",
    "\\int": "∫",
    "\\prod": "∏",
    "\\pm": "±",
    "\\mp": "∓",
    "\\times": "×",
    "\\div": "÷",
    "\\cdot": "·",
    "\\bullet": "•",
    "\\star": "⋆",
    "\\circ": "∘",
    "\\to": "→",
    "\\rightarrow": "→",
    "\\leftarrow": "←",
    "\\gets": "←",
    "\\Rightarrow": "⇒",
    "\\Leftarrow": "⇐",
    "\\iff": "⇔",
    "\\le": "≤",
    "\\leq": "≤",
    "\\ge": "≥",
    "\\geq": "≥",
    "\\ne": "≠",
    "\\neq": "≠",
    "\\approx": "≈",
    "\\equiv": "≡",
    "\\infty": "∞",
    "\\in": "∈",
    "\\notin": "∉",
    "\\subset": "⊂",
    "\\subseteq": "⊆",
    "\\cap": "∩",
    "\\cup": "∪",
    "\\forall": "∀",
    "\\exists": "∃",
    "\\partial": "∂",
    "\\nabla": "∇",
    "\\emptyset": "∅",
    "\\varnothing": "∅",
    "\\ldots": "…",
    "\\cdots": "…",
    "\\dots": "…",
}


class LatexMathParser:
    """Bộ phân tích cú pháp LaTeX an toàn, pure-Python với chốt chặn độ sâu đệ quy (hỗ trợ tới độ sâu 32)."""

    MAX_DEPTH = 32

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

    def parse_row(self, stop_chars: str = "", depth: int = 0) -> MathRow:
        """Phân tích một hàng phần tử toán học, xử lý các toán tử chỉ số trên/dưới (^ và _) ở mọi cấp độ lồng nhau."""
        if depth > self.MAX_DEPTH:
            return MathRow([TextNode("...")])

        items: list[MathNode] = []

        while self.pos < self.len:
            self._skip_whitespace()
            if self.pos >= self.len:
                break

            ch = self.raw[self.pos]
            if stop_chars and ch in stop_chars:
                break

            if ch == "^":
                self.pos += 1
                exp = self.parse_group(depth=depth + 1)
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
                sub = self.parse_group(depth=depth + 1)
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
                elem = self.parse_element(depth=depth)
                if elem:
                    items.append(elem)
                elif self.pos == old_pos and self.pos < self.len:
                    self.pos += 1

        return MathRow(items=items)

    def parse_group(self, depth: int = 0) -> MathRow:
        """Đọc một nhóm trong ngoặc nhọn {...} hoặc một phần tử đơn lẻ (kế thừa đầy đủ ^ và _)."""
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
            row = self.parse_row(stop_chars="}", depth=depth + 1)
            self._consume("}")
            return row
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
            row = self.parse_row(stop_chars="]", depth=depth + 1)
            self._consume("]")
            return row
        return None

    def parse_element(self, depth: int = 0) -> MathNode | None:
        """Đọc một phần tử cơ bản (lệnh macro, ký hiệu, hoặc văn bản)."""
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
                elif cmd in ("\\left", "\\right"):
                    # Tiêu thụ dấu phân cách đi liền sau (\left( -> '(', \left. -> bỏ qua)
                    self._skip_whitespace()
                    if self.pos < self.len:
                        delim = self.raw[self.pos]
                        self.pos += 1
                        if delim != ".":
                            return SymbolNode(symbol=delim)
                    return None
                elif cmd in ("\\text", "\\mathrm", "\\mathbf", "\\mathit", "\\textbf", "\\textit"):
                    # Trích xuất nội dung văn bản thuần
                    self._skip_whitespace()
                    if self._consume("{"):
                        start = self.pos
                        count = 1
                        while self.pos < self.len and count > 0:
                            if self.raw[self.pos] == "{":
                                count += 1
                            elif self.raw[self.pos] == "}":
                                count -= 1
                            self.pos += 1
                        inner = self.raw[start : self.pos - 1]
                        return TextNode(text=inner.strip())
                    else:
                        return self.parse_element(depth + 1)
                elif cmd in LATEX_SYMBOL_MAP:
                    return SymbolNode(symbol=LATEX_SYMBOL_MAP[cmd])
                else:
                    # Macro lạ: cảnh báo và ghi nhận thành SymbolNode để route sang missing_symbols
                    _log.warning("Ký hiệu macro LaTeX chưa hỗ trợ: %s", cmd)
                    return SymbolNode(symbol=cmd)
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
        """Phân tích toàn bộ chuỗi LaTeX."""
        return self.parse_row(depth=0)


def parse_latex_math(latex: str) -> MathRow:
    """Hàm tiện ích chuyển đổi nhanh chuỗi biểu thức LaTeX sang Math AST."""
    parser = LatexMathParser(latex)
    return parser.parse()
