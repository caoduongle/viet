"""Chuyển Math AST ngược lại thành chuỗi LaTeX (dùng để ghi nhận/so sánh công thức từ OMML)."""
from __future__ import annotations

import re

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
from chuviettay.math.symbols import FUNCTION_NAMES, LATEX_SYMBOL_MAP

__all__ = ["to_latex"]

_REVERSE: dict[str, str] = {}
for _macro, _char in LATEX_SYMBOL_MAP.items():
    _REVERSE.setdefault(_char, _macro)
_REVERSE.update({
    "{": "\\{", "}": "\\}", "%": "\\%", "&": "\\&", "#": "\\#", "_": "\\_", "$": "\\$",
    "\\": "\\backslash", "‖": "\\|", "∘": "\\circ", "·": "\\cdot", "…": "\\ldots",
    "⋯": "\\cdots", "→": "\\to", "≤": "\\le", "≥": "\\ge", "≠": "\\ne", "⇔": "\\iff",
    "⟨": "\\langle", "⟩": "\\rangle",
})
for _prime in ("′", "″", "‴"):
    _REVERSE.pop(_prime, None)  # xuất nguyên ký tự dấu nháy, không dùng dấu ' (tránh bị đọc lại thành nháy lồng)
_DELIM = {
    "": ".", "{": "\\{", "}": "\\}", "‖": "\\|", "⟨": "\\langle", "⟩": "\\rangle",
    "⌊": "\\lfloor", "⌋": "\\rfloor", "⌈": "\\lceil", "⌉": "\\rceil",
}
_ACCENT_CMD = {
    "vec": "\\vec", "overrightarrow": "\\overrightarrow", "overleftarrow": "\\overleftarrow",
    "overleftrightarrow": "\\overleftrightarrow", "hat": "\\hat", "widehat": "\\widehat",
    "tilde": "\\tilde", "widetilde": "\\widetilde", "bar": "\\bar", "overline": "\\overline",
    "underline": "\\underline", "dot": "\\dot", "ddot": "\\ddot", "dddot": "\\dddot",
    "acute": "\\acute", "grave": "\\grave", "check": "\\check", "breve": "\\breve",
    "mathring": "\\mathring", "overbrace": "\\overbrace", "underbrace": "\\underbrace",
    "underrightarrow": "\\underrightarrow", "underleftarrow": "\\underleftarrow",
    "strike": "\\cancel",
}
_MATRIX_ENV_BY_DELIMS = {
    ("(", ")"): "pmatrix", ("[", "]"): "bmatrix", ("{", "}"): "Bmatrix",
    ("|", "|"): "vmatrix", ("‖", "‖"): "Vmatrix",
}
_SPACE_CMD = {
    0.1667: "\\,", 0.2222: "\\:", 0.2778: "\\;", -0.1667: "\\!", 0.33: "\\ ", 0.5: "\\enspace",
    1.0: "\\quad", 2.0: "\\qquad", 0.28: "~",
}
_TEXT_ESCAPES = {"_": "\\_", "%": "\\%", "&": "\\&", "#": "\\#", "$": "\\$", "{": "\\{", "}": "\\}",
                 "\\": "\\textbackslash "}
_ENDS_WITH_COMMAND = re.compile(r"\\[A-Za-z]+$")


def to_latex(node: MathNode | None) -> str:
    """Chuyển một nút (hoặc cả cây) Math AST thành chuỗi LaTeX có thể phân tích ngược lại."""
    if node is None:
        return ""
    return _emit(node).strip()


def _join(pieces: list[str]) -> str:
    out = ""
    for p in pieces:
        if not p:
            continue
        if out:
            if _ENDS_WITH_COMMAND.search(out) and (p[0].isalpha() or p[0] == "*"):
                out += " "
            elif out[-1].isdigit() and p[0].isdigit():
                out += " "
            elif out[-1] == "'" and p[0] == "'":
                out += " "
        out += p
    return out


def _braced(node: MathNode | None) -> str:
    return "{" + (_emit(node).strip() if node is not None else "") + "}"


def _atom(node: MathNode) -> str:
    """Biểu thức làm cơ sở cho ^ / _ : cần ngoặc nhóm nếu không phải một nguyên tử."""
    if isinstance(node, MathRow):
        if not node.items:
            return "{}"
        if len(node.items) == 1:
            return _atom(node.items[0])
        return "{" + _emit(node).strip() + "}"
    if isinstance(node, (Superscript, Subscript, SubSuperscript, NAry)):
        return "{" + _emit(node).strip() + "}"
    if isinstance(node, TextNode) and node.kind == "num" and len(node.text) > 1:
        return "{" + _emit(node) + "}"
    return _emit(node)


def _symbol(sym: str) -> str:
    if sym.startswith("\\") and len(sym) > 1:
        return sym
    if sym == ",":
        return ", "
    if sym == ".":
        return ". "
    return _REVERSE.get(sym, sym)


def _text(node: TextNode) -> str:
    txt = node.text
    if node.kind == "func":
        if txt in FUNCTION_NAMES:
            return "\\" + txt
        return "\\operatorname{" + "".join(_TEXT_ESCAPES.get(c, c) for c in txt) + "}"
    if node.kind == "text":
        return "\\text{" + "".join(_TEXT_ESCAPES.get(c, c) for c in txt) + "}"
    if not txt:
        return "{}"
    if node.kind in ("num", "") and "," in txt:
        return txt.replace(",", "{,}")  # dấu phẩy thập phân kiểu Việt Nam
    return txt


def _space(width: float) -> str:
    for known, cmd in _SPACE_CMD.items():
        if abs(known - width) < 1e-6:
            return cmd
    return "\\hspace{" + format(width, "g") + "em}"


def _rows(matrix: Matrix) -> str:
    return " \\\\ ".join(" & ".join(_emit(c).strip() for c in row) for row in matrix.rows)


def _matrix(m: Matrix) -> str:
    if m.kind == "aligned":
        env, spec = "aligned", ""
    elif m.kind == "lines":
        env, spec = "gathered", ""
    elif m.kind in ("array", "cases"):
        env, spec = "array", "{" + "".join(m.col_align or ["c"]) + "}"
    else:
        env, spec = "matrix", ""
    return f"\\begin{{{env}}}{spec} {_rows(m)} \\end{{{env}}}"


def _delimited(d: Delimited) -> str:
    body = d.body
    if isinstance(body, Fraction) and not body.bar and (d.left, d.right) == ("(", ")"):
        return "\\binom" + _braced(body.num) + _braced(body.den)
    if isinstance(body, Matrix):
        if body.kind == "cases" and (d.left, d.right) == ("{", ""):
            return f"\\begin{{cases}} {_rows(body)} \\end{{cases}}"
        if body.kind == "matrix" and (d.left, d.right) in _MATRIX_ENV_BY_DELIMS:
            env = _MATRIX_ENV_BY_DELIMS[(d.left, d.right)]
            return f"\\begin{{{env}}} {_rows(body)} \\end{{{env}}}"
    left = _DELIM.get(d.left, d.left)
    right = _DELIM.get(d.right, d.right)
    return f"\\left{left} {_emit(body).strip()} \\right{right}"


def _emit(node: MathNode) -> str:
    if isinstance(node, MathRow):
        return _join([_emit(it) for it in node.items])
    if isinstance(node, SymbolNode):
        return _symbol(node.symbol)
    if isinstance(node, TextNode):
        return _text(node)
    if isinstance(node, SpaceNode):
        return _space(node.width)
    if isinstance(node, Fraction):
        if node.bar:
            return "\\frac" + _braced(node.num) + _braced(node.den)
        return "{" + _emit(node.num).strip() + " \\atop " + _emit(node.den).strip() + "}"
    if isinstance(node, Superscript):
        return _atom(node.base) + "^" + _braced(node.exp)
    if isinstance(node, Subscript):
        return _atom(node.base) + "_" + _braced(node.sub)
    if isinstance(node, SubSuperscript):
        return _atom(node.base) + "_" + _braced(node.sub) + "^" + _braced(node.exp)
    if isinstance(node, Root):
        if node.degree is not None:
            return "\\sqrt[" + _emit(node.degree).strip() + "]" + _braced(node.radicand)
        return "\\sqrt" + _braced(node.radicand)
    if isinstance(node, Delimited):
        return _delimited(node)
    if isinstance(node, NAry):
        op = ("\\" + node.op) if node.is_function and node.op in FUNCTION_NAMES else (
            "\\operatorname{" + node.op + "}" if node.is_function else _symbol(node.op))
        if node.limits is True:
            op += "\\limits"
        elif node.limits is False:
            op += "\\nolimits"
        if node.sub is not None:
            op += "_" + _braced(node.sub)
        if node.sup is not None:
            op += "^" + _braced(node.sup)
        return op
    if isinstance(node, OverUnder):
        base = node.base
        if isinstance(base, Accent) and base.kind in ("overbrace", "underbrace"):
            out = _emit(base)
            if node.under is not None:
                out += "_" + _braced(node.under)
            if node.over is not None:
                out += "^" + _braced(node.over)
            return out
        out = _braced(base)
        if node.over is not None:
            out = "\\overset" + _braced(node.over) + out
        if node.under is not None:
            out = "\\underset" + _braced(node.under) + out
        return out
    if isinstance(node, Accent):
        return _ACCENT_CMD.get(node.kind, "\\hat") + _braced(node.base)
    if isinstance(node, Matrix):
        return _matrix(node)
    if isinstance(node, Boxed):
        return "\\boxed" + _braced(node.body)
    return ""
