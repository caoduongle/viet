"""Bộ phân tích cú pháp biểu thức toán học LaTeX (pure-Python, không dùng TeX ngoài).

Phủ phần lớn LaTeX toán thường gặp trong bài giải: phân số, căn, chỉ số/số mũ (kể cả không
ngoặc ``x^2``, nháy ``f'``), ngoặc co giãn ``\\left...\\right``, ma trận/``cases``/``aligned``,
toán tử lớn có cận, dấu trang trí (vectơ, mũ, gạch ngang), ``\\text``/``\\mathrm``/``\\mathbb``,
khoảng trắng và các escape ``\\{ \\} \\% \\_``. Macro chưa biết vẫn rơi về ``SymbolNode`` để
đường báo cáo "ký hiệu thiếu mẫu" của ứng dụng ghi nhận (không bao giờ im lặng bỏ mất).
"""
from __future__ import annotations

import logging
import re
import unicodedata

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
from chuviettay.math.build import degree_sign, text_node, unwrap
from chuviettay.math.symbols import (
    BIG_OPERATORS,
    CONTROL_SYMBOLS,
    FUNCTION_NAMES,
    LATEX_SYMBOL_MAP,
    LIMIT_FUNCTIONS,
    SPACE_COMMANDS,
    canon_symbol,
    double_struck,
    is_symbol_letter,
    fraktur_style,
    script_style,
)

__all__ = [
    "LATEX_SYMBOL_MAP",
    "LatexMathParser",
    "parse_latex_math",
    "parse_latex_math_with_warnings",
]

_log = logging.getLogger(__name__)

_CMD_RE = re.compile(r"\\[a-zA-Z]+")
# Số: 3.14 / 1.000.000 / 13{,}65. Theo quy ước TeX, dấu phẩy trần "0,1" là dấu ngăn cách (khoảng [0,1],
# chỉ số x_{1,2}); muốn dấu phẩy thập phân kiểu Việt Nam hãy viết 0{,}1.
_NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*(?:\{,\}[0-9]+)?")
_SIMPLE_TEXT_RE = re.compile(r"^[^\\{}$^_&#~]*$")
_NEWLINE_CMD = "\\\\"

_FRAC_COMMANDS = {"\\frac", "\\dfrac", "\\tfrac", "\\cfrac"}
_BINOM_COMMANDS = {"\\binom", "\\dbinom", "\\tbinom"}
_TEXT_COMMANDS = {
    "\\text", "\\textrm", "\\textnormal", "\\mbox", "\\hbox", "\\textbf", "\\textit",
    "\\textsf", "\\texttt", "\\emph", "\\textup", "\\textmd",
}
_UPRIGHT_COMMANDS = {"\\mathrm", "\\mathit", "\\mathsf", "\\mathtt", "\\mathnormal", "\\mathup"}
_BOLD_COMMANDS = {"\\mathbf", "\\boldsymbol", "\\bm", "\\pmb", "\\mathbfit"}
_STYLE_MAPPERS = {
    "\\mathbb": double_struck, "\\mathbbm": double_struck, "\\Bbb": double_struck,
    "\\mathcal": script_style, "\\mathscr": script_style,
    "\\mathfrak": fraktur_style,
}
_ACCENT_COMMANDS = {
    "\\vec": "vec", "\\overrightarrow": "overrightarrow", "\\overleftarrow": "overleftarrow",
    "\\overleftrightarrow": "overleftrightarrow", "\\hat": "hat", "\\widehat": "widehat",
    "\\tilde": "tilde", "\\widetilde": "widetilde", "\\bar": "bar", "\\overline": "overline",
    "\\underline": "underline", "\\underbar": "underline", "\\dot": "dot", "\\ddot": "ddot",
    "\\dddot": "dddot", "\\acute": "acute", "\\grave": "grave", "\\check": "check",
    "\\breve": "breve", "\\mathring": "mathring", "\\overbrace": "overbrace",
    "\\underbrace": "underbrace", "\\underrightarrow": "underrightarrow",
    "\\underleftarrow": "underleftarrow", "\\cancel": "strike", "\\bcancel": "strike",
    "\\xcancel": "strike", "\\sout": "strike",
}
_IGNORED_NOARG = {
    "\\displaystyle", "\\textstyle", "\\scriptstyle", "\\scriptscriptstyle", "\\limits",
    "\\nolimits", "\\nonumber", "\\notag", "\\hline", "\\hdashline", "\\centering",
    "\\boldmath", "\\unboldmath", "\\allowbreak", "\\nobreak", "\\relax", "\\protect",
    "\\mathstrut", "\\strut", "\\hfill", "\\hss", "\\raggedright", "\\raggedleft", "\\bigskip",
    "\\medskip", "\\smallskip", "\\newline", "\\linebreak", "\\pagebreak",
}
_SIZE_COMMANDS = re.compile(r"^\\(?:big|Big|bigg|Bigg)[lrm]?$")
_MATRIX_ENVS = {
    "matrix": ("", ""), "smallmatrix": ("", ""), "pmatrix": ("(", ")"), "bmatrix": ("[", "]"),
    "Bmatrix": ("{", "}"), "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"),
}
_ALIGNED_ENVS = {"aligned", "align", "alignat", "split", "eqnarray", "flalign", "alignedat"}
_LINES_ENVS = {"gathered", "gather", "multline", "equation", "displaymath", "math", "subequations"}
_NEGATIONS = {
    "=": "≠", "<": "≮", ">": "≯", "∈": "∉", "⊂": "⊄", "⊆": "⊈", "⊃": "⊅", "⊇": "⊉", "≤": "≰",
    "≥": "≱", "∼": "≁", "≅": "≇", "≈": "≉", "≡": "≢", "∃": "∄", "∣": "∤", "∥": "∦", "→": "↛",
    "⇒": "⇏", "⇔": "⇎", "←": "↚",
}
_UNIT_EM = {"em": 1.0, "ex": 0.5, "pt": 0.1, "mu": 1.0 / 18.0, "cm": 2.845, "mm": 0.2845,
            "in": 7.227, "bp": 0.1, "sp": 0.0, "px": 0.075}
_PRIMES = {1: "′", 2: "″", 3: "‴"}


class LatexMathParser:
    """Bộ phân tích cú pháp LaTeX an toàn, pure-Python với chốt chặn độ sâu đệ quy (tới độ sâu 32)."""

    MAX_DEPTH = 32

    def __init__(self, latex: str):
        self.raw = unicodedata.normalize("NFC", latex or "")
        self.pos = 0
        self.len = len(self.raw)
        self.warnings: list[str] = []

    # ------------------------------------------------------------------ tiện ích mức thấp
    def _warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def _skip_whitespace(self) -> None:
        while self.pos < self.len and self.raw[self.pos].isspace():
            self.pos += 1

    # Tên cũ được giữ để tương thích
    _skip_ws = _skip_whitespace

    def _peek(self) -> str:
        self._skip_whitespace()
        return self.raw[self.pos] if self.pos < self.len else ""

    def _consume(self, char: str) -> bool:
        self._skip_whitespace()
        if self.pos < self.len and self.raw[self.pos] == char:
            self.pos += 1
            return True
        return False

    def _peek_command(self) -> str:
        """Lệnh bắt đầu tại vị trí hiện tại (đã bỏ khoảng trắng): ``\\frac``, ``\\{``, ``\\\\``..."""
        self._skip_whitespace()
        if self.pos >= self.len or self.raw[self.pos] != "\\":
            return ""
        m = _CMD_RE.match(self.raw, self.pos)
        if m:
            return m.group(0)
        return self.raw[self.pos : self.pos + 2]

    def _take_command(self) -> str:
        cmd = self._peek_command()
        self.pos += len(cmd)
        return cmd

    def _skip_balanced_braces(self) -> None:
        """Bỏ qua một nhóm {...} (hoặc một ký tự) khi đã vượt quá độ sâu cho phép."""
        self._skip_whitespace()
        if self._consume("{"):
            count = 1
            while self.pos < self.len and count > 0:
                ch = self.raw[self.pos]
                if ch == "\\":
                    self.pos += 2
                    continue
                if ch == "{":
                    count += 1
                elif ch == "}":
                    count -= 1
                self.pos += 1
        elif self.pos < self.len:
            self.pos += len(self._peek_command()) or 1

    def _depth_exceeded(self) -> MathRow:
        self._warn(f"Công thức lồng quá {self.MAX_DEPTH} cấp, phần sâu hơn bị rút gọn thành '...'")
        return MathRow([TextNode("...", kind="text")])

    def _read_braced_raw(self) -> str:
        """Đọc nội dung thô trong {...} (có xử lý lồng nhau và \\{ \\}); không có ngoặc thì lấy một ký tự."""
        self._skip_whitespace()
        if self.pos >= self.len:
            return ""
        if self.raw[self.pos] != "{":
            if self.raw[self.pos] == "\\":
                cmd = self._take_command()
                return cmd
            ch = self.raw[self.pos]
            self.pos += 1
            return ch
        self.pos += 1
        start = self.pos
        count = 1
        while self.pos < self.len:
            ch = self.raw[self.pos]
            if ch == "\\":
                self.pos += 2
                continue
            if ch == "{":
                count += 1
            elif ch == "}":
                count -= 1
                if count == 0:
                    inner = self.raw[start : self.pos]
                    self.pos += 1
                    return inner
            self.pos += 1
        self._warn("Thiếu dấu '}' đóng nhóm")
        return self.raw[start : self.pos]

    # ------------------------------------------------------------------ cấp hàng
    def parse_row(self, stop_chars: str = "", depth: int = 0, table_mode: bool = False) -> MathRow:
        """Phân tích một hàng phần tử, dừng ở ``stop_chars`` / ``\\right`` / ``\\end`` (và ``&``, ``\\\\`` trong bảng)."""
        if depth > self.MAX_DEPTH:
            self._skip_balanced_braces()
            return self._depth_exceeded()

        items: list[MathNode] = []
        while True:
            self._skip_whitespace()
            if self.pos >= self.len:
                break
            ch = self.raw[self.pos]
            if stop_chars and ch in stop_chars:
                break
            if ch == "}":
                self.pos += 1
                self._warn("Dấu '}' thừa, đã bỏ qua")
                continue
            if table_mode and ch == "&":
                break
            if ch == "\\":
                cmd = self._peek_command()
                if cmd in ("\\right", "\\end"):
                    break
                if table_mode and cmd == _NEWLINE_CMD:
                    break
                if cmd in ("\\over", "\\atop", "\\choose"):
                    self.pos += len(cmd)
                    den = self.parse_row(stop_chars, depth + 1, table_mode)
                    num = MathRow(items)
                    frac: MathNode = Fraction(num=num, den=den, bar=(cmd == "\\over"))
                    if cmd == "\\choose":
                        frac = Delimited("(", ")", Fraction(num=num, den=den, bar=False))
                    return MathRow([frac])

            old_pos = self.pos
            atom = self._parse_atom_with_scripts(depth)
            if atom is not None:
                items.append(atom)
            elif self.pos == old_pos and self.pos < self.len:
                self.pos += 1
        return MathRow(items=items)

    def parse_group(self, depth: int = 0) -> MathRow:
        """Đọc một nhóm {...} hoặc một phần tử đơn lẻ (kế thừa đầy đủ ^ và _)."""
        if depth > self.MAX_DEPTH:
            self._skip_balanced_braces()
            return self._depth_exceeded()
        self._skip_whitespace()
        if self.pos >= self.len:
            return MathRow([])
        if self._consume("{"):
            row = self.parse_row(stop_chars="}", depth=depth + 1)
            if not self._consume("}"):
                self._warn("Thiếu dấu '}' đóng nhóm")
            return row
        node = self._parse_single_token(depth)
        return MathRow([node] if node is not None else [])

    def parse_bracket_group(self, depth: int = 0) -> MathRow | None:
        """Đọc một nhóm trong ngoặc vuông [...] (tuỳ chọn, vd. bậc của căn)."""
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
                return self._depth_exceeded()
            return None
        self._skip_whitespace()
        if self._consume("["):
            row = self.parse_row(stop_chars="]", depth=depth + 1)
            self._consume("]")
            return row
        return None

    # ------------------------------------------------------------------ nguyên tử + chỉ số
    def parse_element(self, depth: int = 0) -> MathNode | None:
        """Đọc một nguyên tử (lệnh, ký hiệu, chữ, số) - giữ tên cũ để tương thích."""
        return self._parse_atom(depth)

    def _parse_atom_with_scripts(self, depth: int) -> MathNode | None:
        atom = self._parse_atom(depth)
        if atom is None:
            return None
        return self._attach_scripts(atom, depth)

    def _attach_scripts(self, base: MathNode, depth: int) -> MathNode:
        sub: MathRow | None = None
        sup: MathRow | None = None
        primes = 0
        limits: bool | None = None

        while True:
            self._skip_whitespace()
            if self.pos >= self.len:
                break
            ch = self.raw[self.pos]
            if ch == "\\":
                cmd = self._peek_command()
                if cmd in ("\\limits", "\\nolimits"):
                    self.pos += len(cmd)
                    limits = cmd == "\\limits"
                    continue
                break
            if ch == "'":
                while self.pos < self.len and self.raw[self.pos] == "'":
                    primes += 1
                    self.pos += 1
                continue
            if ch == "^":
                self.pos += 1
                arg = self._script_arg(depth + 1)
                if sup is not None or primes:
                    if sup is not None:
                        base = self._build_scripted(base, sub, sup, limits)
                        sub, sup, limits = None, None, None
                        primes = 0
                    else:
                        arg = MathRow([self._prime_symbol(primes)] + list(arg.items))
                        primes = 0
                sup = arg
            elif ch == "_":
                self.pos += 1
                arg = self._script_arg(depth + 1)
                if sub is not None:
                    base = self._build_scripted(base, sub, sup, limits)
                    sub, sup, limits = None, None, None
                    primes = 0
                sub = arg
            else:
                break

        if primes:
            prime = self._prime_symbol(primes)
            sup = MathRow([prime] + (list(sup.items) if sup is not None else []))
        return self._build_scripted(base, sub, sup, limits)

    @staticmethod
    def _prime_symbol(count: int) -> SymbolNode:
        return SymbolNode(_PRIMES.get(count, "′" * count))

    def _build_scripted(
        self, base: MathNode, sub: MathRow | None, sup: MathRow | None, limits: bool | None = None
    ) -> MathNode:
        if sub is None and sup is None:
            return base
        if sup is not None:
            sup = degree_sign(sup)  # ^\circ là ký hiệu độ
        if isinstance(base, SymbolNode) and base.symbol in BIG_OPERATORS:
            return NAry(op=base.symbol, sub=sub, sup=sup, limits=limits)
        if isinstance(base, TextNode) and base.kind == "func" and base.text in LIMIT_FUNCTIONS:
            return NAry(op=base.text, sub=sub, sup=sup, limits=limits, is_function=True)
        if isinstance(base, Accent) and base.kind in ("overbrace", "underbrace"):
            return OverUnder(base=base, over=sup, under=sub)
        if sub is not None and sup is not None:
            return SubSuperscript(base=base, sub=sub, exp=sup)
        if sup is not None:
            return Superscript(base=base, exp=sup)
        assert sub is not None
        return Subscript(base=base, sub=sub)

    def _script_arg(self, depth: int) -> MathRow:
        """Đối số của ^/_ : nhóm {...} hoặc ĐÚNG MỘT ký tự (x^23 chỉ mũ chữ số 2)."""
        if depth > self.MAX_DEPTH:
            self._skip_balanced_braces()
            return self._depth_exceeded()
        self._skip_whitespace()
        if self.pos >= self.len:
            return MathRow([])
        if self.raw[self.pos] == "{":
            return self.parse_group(depth)
        node = self._parse_single_token(depth)
        return MathRow([node] if node is not None else [])

    def _parse_single_token(self, depth: int) -> MathNode | None:
        """Một token duy nhất: một chữ số, một chữ cái, hoặc một lệnh (kèm đối số của nó)."""
        self._skip_whitespace()
        if self.pos >= self.len:
            return None
        ch = self.raw[self.pos]
        if "0" <= ch <= "9":
            self.pos += 1
            return TextNode(ch, kind="num")
        if ch == "\\":
            return self._parse_command(depth)
        if ch == "{":
            return self.parse_group(depth + 1)
        if ch in "^_}":
            return None
        return self._parse_char(ch)

    # ------------------------------------------------------------------ nguyên tử
    def _parse_char(self, ch: str) -> MathNode | None:
        """Ký tự thường (không phải lệnh): chữ cái, ký hiệu hoặc khoảng trắng."""
        self.pos += 1
        if ch.isalpha():
            if is_symbol_letter(ch):
                return SymbolNode(ch)
            return TextNode(ch, kind="var")
        if ch == "~":
            return SpaceNode(0.28)
        if ch == "$":
            return None
        return SymbolNode(canon_symbol(ch))

    def _parse_atom(self, depth: int = 0) -> MathNode | None:
        self._skip_whitespace()
        if self.pos >= self.len:
            return None
        if depth > self.MAX_DEPTH:
            self._skip_balanced_braces()
            return TextNode("...", kind="text")

        ch = self.raw[self.pos]
        if ch == "\\":
            return self._parse_command(depth)
        if ch == "{":
            return self.parse_group(depth + 1)
        if ch in "^_":
            return MathRow([])  # chỉ số đứng đầu, không có cơ sở: {}^{14}C
        if ch == "'":
            self.pos += 1
            return SymbolNode("′")
        if ch == "}":
            self.pos += 1
            self._warn("Dấu '}' thừa, đã bỏ qua")
            return None
        if "0" <= ch <= "9":
            m = _NUM_RE.match(self.raw, self.pos)
            txt = m.group(0) if m else ch
            self.pos += len(txt)
            return TextNode(txt.replace("{,}", ","), kind="num")
        return self._parse_char(ch)

    # ------------------------------------------------------------------ lệnh
    def _parse_command(self, depth: int) -> MathNode | None:
        cmd = self._take_command()
        if not cmd:
            return None
        if depth > self.MAX_DEPTH:
            self._skip_balanced_braces()
            return TextNode("...", kind="text")

        if cmd in _FRAC_COMMANDS:
            if cmd == "\\cfrac":
                self.parse_bracket_group(depth + 1)
            num = self.parse_group(depth + 1)
            den = self.parse_group(depth + 1)
            return Fraction(num=num, den=den)
        if cmd in _BINOM_COMMANDS:
            num = self.parse_group(depth + 1)
            den = self.parse_group(depth + 1)
            return Delimited("(", ")", Fraction(num=num, den=den, bar=False))
        if cmd == "\\sqrt":
            degree = self.parse_bracket_group(depth + 1)
            radicand = self.parse_group(depth + 1)
            return Root(radicand=radicand, degree=degree)
        if cmd == "\\left":
            return self._parse_left_right(depth)
        if cmd == "\\right":
            delim = self._read_delimiter()
            self._warn("\\right không có \\left tương ứng")
            return SymbolNode(delim) if delim else None
        if cmd == "\\middle" or _SIZE_COMMANDS.match(cmd):
            delim = self._read_delimiter()
            return SymbolNode(delim) if delim else None
        if cmd == "\\begin":
            return self._parse_environment(depth)
        if cmd == "\\end":
            self._read_braced_raw()
            self._warn("\\end không có \\begin tương ứng")
            return None

        if cmd in SPACE_COMMANDS:
            return SpaceNode(SPACE_COMMANDS[cmd])
        if cmd == _NEWLINE_CMD:
            self._skip_optional_bracket()
            return SpaceNode(1.0)

        if cmd in _TEXT_COMMANDS:
            return self._parse_text(self._read_braced_raw(), kind="text")
        if cmd in _UPRIGHT_COMMANDS:
            return self._parse_upright(depth)
        if cmd in ("\\operatorname", "\\mathop", "\\operatornamewithlimits"):
            if self._peek() == "*":
                self.pos += 1
            raw = self._read_braced_raw()
            return self._parse_text(raw, kind="func")
        if cmd in _BOLD_COMMANDS:
            return unwrap(self.parse_group(depth + 1))
        if cmd in _STYLE_MAPPERS:
            return self._parse_styled(_STYLE_MAPPERS[cmd], self._read_braced_raw())
        if cmd in _ACCENT_COMMANDS:
            base = self.parse_group(depth + 1)
            return Accent(base=base, kind=_ACCENT_COMMANDS[cmd])
        if cmd in ("\\overset", "\\stackrel", "\\underset"):
            first = self.parse_group(depth + 1)
            base = self.parse_group(depth + 1)
            if cmd == "\\underset":
                return OverUnder(base=base, under=first)
            return OverUnder(base=base, over=first)
        if cmd in ("\\xrightarrow", "\\xleftarrow", "\\xlongequal"):
            under = self.parse_bracket_group(depth + 1)
            over = self.parse_group(depth + 1)
            arrow = {"\\xrightarrow": "→", "\\xleftarrow": "←", "\\xlongequal": "="}[cmd]
            return OverUnder(base=SymbolNode(arrow), over=over, under=under)
        if cmd == "\\boxed":
            return Boxed(body=self.parse_group(depth + 1))
        if cmd == "\\not":
            return self._parse_negation(depth)
        if cmd in ("\\pmod", "\\mod", "\\bmod"):
            return self._parse_mod(cmd, depth)
        if cmd == "\\textcolor":
            self._read_braced_raw()
            return unwrap(self.parse_group(depth + 1))
        if cmd in ("\\phantom", "\\hphantom", "\\vphantom"):
            raw = self._read_braced_raw()
            return SpaceNode(0.0 if cmd == "\\vphantom" else max(0.3, 0.55 * len(raw.strip())))
        if cmd in ("\\hspace", "\\hspace*", "\\mspace", "\\kern", "\\mkern", "\\hskip"):
            return SpaceNode(self._parse_length())
        if cmd in _IGNORED_NOARG:
            return None
        if cmd in ("\\label", "\\tag", "\\ref", "\\eqref", "\\color", "\\pagecolor", "\\cline", "\\vspace"):
            if cmd == "\\tag" and self._peek() == "*":
                self.pos += 1
            self._read_braced_raw()
            return None
        name = cmd[1:]
        if name in FUNCTION_NAMES:
            return TextNode(name, kind="func")
        if cmd in LATEX_SYMBOL_MAP:
            return SymbolNode(LATEX_SYMBOL_MAP[cmd])
        if len(cmd) == 2 and not cmd[1].isalpha():
            ctrl = cmd[1]
            if ctrl in CONTROL_SYMBOLS:
                value = CONTROL_SYMBOLS[ctrl]
                return SymbolNode(value) if value.strip() else None
            _log.warning("Ký hiệu macro LaTeX chưa hỗ trợ: %s", cmd)
            self._warn(f"Macro LaTeX chưa hỗ trợ: {cmd}")
            return SymbolNode(cmd)
        if cmd == "\\":
            return SymbolNode("\\")

        # Macro lạ: cảnh báo và ghi nhận thành SymbolNode để route sang missing_symbols
        _log.warning("Ký hiệu macro LaTeX chưa hỗ trợ: %s", cmd)
        self._warn(f"Macro LaTeX chưa hỗ trợ: {cmd}")
        return SymbolNode(symbol=cmd)

    # ------------------------------------------------------------------ các nhóm lệnh
    def _read_delimiter(self) -> str:
        """Đọc dấu phân cách sau \\left / \\right / \\big...: ``(``, ``\\{``, ``\\langle``, ``.`` ..."""
        self._skip_whitespace()
        if self.pos >= self.len:
            return ""
        ch = self.raw[self.pos]
        if ch == ".":
            self.pos += 1
            return ""
        if ch == "\\":
            cmd = self._take_command()
            if cmd in ("\\{", "\\lbrace"):
                return "{"
            if cmd in ("\\}", "\\rbrace"):
                return "}"
            if cmd == "\\|":
                return "‖"
            if cmd in LATEX_SYMBOL_MAP:
                return LATEX_SYMBOL_MAP[cmd]
            if cmd == "\\backslash":
                return "\\"
            self._warn(f"Dấu phân cách chưa hỗ trợ: {cmd}")
            return ""
        self.pos += 1
        return {"<": "⟨", ">": "⟩"}.get(ch, canon_symbol(ch))

    def _parse_left_right(self, depth: int) -> MathNode:
        left = self._read_delimiter()
        if depth + 1 > self.MAX_DEPTH:
            self._depth_exceeded()
            self.pos = self.len
            return TextNode("...", kind="text")
        body = self.parse_row(depth=depth + 1)
        right = ""
        if self._peek_command() == "\\right":
            self.pos += len("\\right")
            right = self._read_delimiter()
        else:
            self._warn("\\left không có \\right tương ứng")
        return Delimited(left=left, right=right, body=body)

    def _parse_text(self, raw: str, kind: str) -> MathNode:
        """\\text{...}: tách thành các từ đứng thẳng; khoảng trắng đầu/cuối được giữ lại."""
        return text_node(self._unescape_text(raw), kind)

    @staticmethod
    def _unescape_text(raw: str) -> str:
        out = raw
        for esc, rep in (("\\_", "_"), ("\\%", "%"), ("\\&", "&"), ("\\#", "#"), ("\\$", "$"),
                         ("\\{", "{"), ("\\}", "}"), ("\\textbackslash", "\\"),
                         ("\\ ", " "), ("\\,", " "), ("\\;", " "), ("\\:", " "), ("\\!", ""),
                         ("\\\\", " "), ("~", " "), ("\\quad", "  "), ("\\qquad", "   ")):
            out = out.replace(esc, rep)
        out = re.sub(r"\\[a-zA-Z]+\*?", "", out)
        return out.replace("$", "").replace("{", "").replace("}", "")

    def _parse_upright(self, depth: int) -> MathNode:
        """\\mathrm{...}: chữ đơn giản -> một từ đứng thẳng; còn lại phân tích như toán."""
        start = self.pos
        raw = self._read_braced_raw()
        if raw and _SIMPLE_TEXT_RE.match(raw) and not raw.isspace():
            return self._parse_text(raw, kind="text")
        self.pos = start
        return self.parse_group(depth + 1)

    @staticmethod
    def _parse_styled(mapper, raw: str) -> MathNode:
        """\\mathbb{R} -> ℝ, \\mathcal{L} -> ℒ ..."""
        raw = raw.strip()
        nodes: list[MathNode] = []
        for ch in raw:
            if ch.isspace():
                continue
            mapped = mapper(ch)
            if mapped != ch:
                nodes.append(SymbolNode(mapped))
            elif ch.isalpha():
                nodes.append(TextNode(ch, kind="var"))
            elif "0" <= ch <= "9":
                nodes.append(TextNode(ch, kind="num"))
            else:
                nodes.append(SymbolNode(canon_symbol(ch)))
        if len(nodes) == 1:
            return nodes[0]
        return MathRow(nodes)

    def _parse_negation(self, depth: int) -> MathNode | None:
        self._skip_whitespace()
        nxt = self._parse_single_token(depth)
        if isinstance(nxt, SymbolNode) and nxt.symbol in _NEGATIONS:
            return SymbolNode(_NEGATIONS[nxt.symbol])
        if nxt is None:
            return None
        self._warn("\\not chỉ hỗ trợ trước các quan hệ thông dụng")
        return MathRow([nxt, SymbolNode("/")])

    def _parse_mod(self, cmd: str, depth: int) -> MathNode:
        mod = TextNode("mod", kind="func")
        if cmd != "\\pmod":
            return mod
        arg = self.parse_group(depth + 1)
        return MathRow([SymbolNode("("), mod, SpaceNode(0.33), *arg.items, SymbolNode(")")])

    def _parse_length(self) -> float:
        """Đọc độ dài kiểu ``{1.5em}`` hoặc ``2pt`` và đổi sang em."""
        raw = self._read_braced_raw().strip()
        m = re.match(r"^(-?[0-9]*\.?[0-9]+)\s*([a-z]{2})?$", raw)
        if not m:
            return 0.5
        return float(m.group(1)) * _UNIT_EM.get(m.group(2) or "em", 1.0)

    def _skip_optional_bracket(self) -> None:
        """Bỏ qua tuỳ chọn độ dài sau ``\\\\`` (vd. ``\\\\[2pt]``)."""
        save = self.pos
        self._skip_whitespace()
        if self.pos < self.len and self.raw[self.pos] == "[":
            end = self.raw.find("]", self.pos)
            if end != -1 and end - self.pos <= 16:
                self.pos = end + 1
                return
        self.pos = save

    # ------------------------------------------------------------------ môi trường \begin ... \end
    def _parse_environment(self, depth: int) -> MathNode | None:
        name = self._read_braced_raw().strip()
        if depth + 1 > self.MAX_DEPTH:
            self._depth_exceeded()
            self.pos = self.len
            return TextNode("...", kind="text")
        spec = ""
        base = name.rstrip("*")
        if base in ("array", "tabular", "subarray", "alignat", "alignedat", "tabularx"):
            self._skip_whitespace()
            if self.pos < self.len and self.raw[self.pos] == "{":
                spec = self._read_braced_raw()
        rows = self._parse_table_body(depth + 1, env=name)
        return self._build_environment(base, rows, spec)

    def _parse_table_body(self, depth: int, env: str | None) -> list[list[MathRow]]:
        """Đọc các ô (ngăn bởi ``&``) và hàng (ngăn bởi ``\\\\``) tới ``\\end{env}`` hoặc hết chuỗi."""
        rows: list[list[MathRow]] = []
        cells: list[MathRow] = []
        cur = MathRow([])
        while True:
            part = self.parse_row("", depth, table_mode=True)
            cur.items.extend(part.items)
            if self.pos >= self.len:
                if env is not None:
                    self._warn(f"Thiếu \\end{{{env}}}")
                break
            self._skip_whitespace()
            cmd = self._peek_command()
            ch = self.raw[self.pos]
            if ch == "&":
                self.pos += 1
                cells.append(cur)
                cur = MathRow([])
            elif cmd == _NEWLINE_CMD:
                self.pos += 2
                self._skip_optional_bracket()
                cells.append(cur)
                rows.append(cells)
                cells, cur = [], MathRow([])
            elif cmd == "\\end":
                self.pos += len(cmd)
                closing = self._read_braced_raw().strip()
                if env is None:
                    self._warn("\\end không có \\begin tương ứng")
                    continue
                if closing != env:
                    self._warn(f"\\begin{{{env}}} đóng bằng \\end{{{closing}}}")
                break
            elif cmd == "\\right":
                if env is not None:
                    self._warn(f"Thiếu \\end{{{env}}} trước \\right")
                    break
                self.pos += len(cmd)
                delim = self._read_delimiter()
                self._warn("\\right không có \\left tương ứng")
                if delim:
                    cur.items.append(SymbolNode(delim))
            else:
                self.pos += 1
        if cur.items or cells or not rows:
            cells.append(cur)
        if cells:
            rows.append(cells)
        while len(rows) > 1 and all(not c.items for c in rows[-1]):
            rows.pop()
        return rows

    def _build_environment(self, name: str, rows: list[list[MathRow]], spec: str) -> MathNode:
        node_rows: list[list[MathNode]] = [list(r) for r in rows]
        ncols = max((len(r) for r in node_rows), default=1)
        if name in _MATRIX_ENVS:
            left, right = _MATRIX_ENVS[name]
            matrix = Matrix(rows=node_rows, kind="matrix", col_align=["c"] * ncols)
            return Delimited(left, right, matrix) if (left or right) else matrix
        if name == "cases":
            return Delimited("{", "", Matrix(rows=node_rows, kind="cases", col_align=["l"] * ncols))
        if name in _ALIGNED_ENVS:
            return Matrix(rows=node_rows, kind="aligned",
                          col_align=[("r" if i % 2 == 0 else "l") for i in range(ncols)])
        if name in _LINES_ENVS:
            if len(node_rows) == 1 and len(node_rows[0]) == 1:
                return node_rows[0][0]
            return Matrix(rows=node_rows, kind="lines", col_align=["c"] * ncols)
        if name in ("array", "tabular", "subarray", "tabularx"):
            aligns = [c for c in spec if c in "lcr"] or ["c"] * ncols
            return Matrix(rows=node_rows, kind="array", col_align=aligns)
        self._warn(f"Môi trường LaTeX chưa hỗ trợ: {name}")
        return Matrix(rows=node_rows, kind="lines", col_align=["c"] * ncols)

    # ------------------------------------------------------------------ điểm vào
    def parse(self) -> MathRow:
        """Phân tích toàn bộ chuỗi LaTeX (nhiều hàng/ô ngăn bởi ``\\\\``/``&`` thành ``Matrix``)."""
        rows = self._parse_table_body(0, env=None)
        if len(rows) == 1 and len(rows[0]) == 1:
            return rows[0][0]
        has_alignment = any(len(r) > 1 for r in rows)
        ncols = max(len(r) for r in rows)
        if has_alignment:
            matrix = Matrix(rows=[list(r) for r in rows], kind="aligned",
                            col_align=[("r" if i % 2 == 0 else "l") for i in range(ncols)])
        else:
            matrix = Matrix(rows=[list(r) for r in rows], kind="lines", col_align=["c"])
        return MathRow([matrix])


def parse_latex_math(latex: str) -> MathRow:
    """Hàm tiện ích chuyển đổi nhanh chuỗi biểu thức LaTeX sang Math AST."""
    return LatexMathParser(latex).parse()


def parse_latex_math_with_warnings(latex: str) -> tuple[MathRow, list[str]]:
    """Như ``parse_latex_math`` nhưng trả thêm danh sách cảnh báo (macro lạ, thiếu ngoặc, quá sâu...)."""
    parser = LatexMathParser(latex)
    row = parser.parse()
    return row, parser.warnings
