"""Bảng ký hiệu toán học dùng chung (thuần dữ liệu, không phụ thuộc tầng nào khác).

Gồm: ánh xạ macro LaTeX -> ký tự Unicode, phân lớp ký hiệu theo kiểu TeX (Ord/Op/Bin/Rel/
Open/Close/Punct/Inner) để dàn khoảng cách, tên hàm chuẩn và chuẩn hoá ký tự Unicode.
"""
from __future__ import annotations

import unicodedata

# ---------------------------------------------------------------------------------------------
# Macro LaTeX -> Unicode
# ---------------------------------------------------------------------------------------------
LATEX_SYMBOL_MAP: dict[str, str] = {
    # Chữ cái Hy Lạp thường
    "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ", "\\epsilon": "ϵ",
    "\\varepsilon": "ε", "\\zeta": "ζ", "\\eta": "η", "\\theta": "θ", "\\vartheta": "ϑ",
    "\\iota": "ι", "\\kappa": "κ", "\\lambda": "λ", "\\mu": "μ", "\\nu": "ν", "\\xi": "ξ",
    "\\pi": "π", "\\varpi": "ϖ", "\\rho": "ρ", "\\varrho": "ϱ", "\\sigma": "σ",
    "\\varsigma": "ς", "\\tau": "τ", "\\upsilon": "υ", "\\phi": "ϕ", "\\varphi": "φ",
    "\\chi": "χ", "\\psi": "ψ", "\\omega": "ω",
    # Chữ cái Hy Lạp hoa
    "\\Gamma": "Γ", "\\Delta": "Δ", "\\Theta": "Θ", "\\Lambda": "Λ", "\\Xi": "Ξ", "\\Pi": "Π",
    "\\Sigma": "Σ", "\\Upsilon": "Υ", "\\Phi": "Φ", "\\Psi": "Ψ", "\\Omega": "Ω",
    # Chữ cái đặc biệt
    "\\ell": "ℓ", "\\hbar": "ℏ", "\\Re": "ℜ", "\\Im": "ℑ", "\\aleph": "ℵ", "\\wp": "℘",
    "\\imath": "ı", "\\jmath": "ȷ",
    # Toán tử lớn
    "\\sum": "∑", "\\prod": "∏", "\\coprod": "∐", "\\int": "∫", "\\iint": "∬", "\\iiint": "∭",
    "\\oint": "∮", "\\bigcup": "⋃", "\\bigcap": "⋂", "\\bigvee": "⋁", "\\bigwedge": "⋀",
    "\\bigoplus": "⨁", "\\bigotimes": "⨂", "\\bigsqcup": "⨆",
    # Toán tử hai ngôi
    "\\pm": "±", "\\mp": "∓", "\\times": "×", "\\div": "÷", "\\cdot": "·", "\\ast": "∗",
    "\\bullet": "•", "\\star": "⋆", "\\circ": "∘", "\\oplus": "⊕", "\\ominus": "⊖",
    "\\otimes": "⊗", "\\oslash": "⊘", "\\odot": "⊙", "\\cap": "∩", "\\cup": "∪",
    "\\uplus": "⊎", "\\sqcap": "⊓", "\\sqcup": "⊔", "\\vee": "∨", "\\lor": "∨",
    "\\wedge": "∧", "\\land": "∧", "\\setminus": "∖", "\\smallsetminus": "∖", "\\wr": "≀",
    "\\diamond": "⋄", "\\dagger": "†", "\\ddagger": "‡", "\\amalg": "⨿",
    # Quan hệ
    "\\le": "≤", "\\leq": "≤", "\\ge": "≥", "\\geq": "≥", "\\ne": "≠", "\\neq": "≠",
    "\\approx": "≈", "\\equiv": "≡", "\\sim": "∼", "\\simeq": "≃", "\\cong": "≅",
    "\\propto": "∝", "\\ll": "≪", "\\gg": "≫", "\\prec": "≺", "\\succ": "≻",
    "\\preceq": "⪯", "\\succeq": "⪰", "\\subset": "⊂", "\\supset": "⊃", "\\subseteq": "⊆",
    "\\supseteq": "⊇", "\\subsetneq": "⊊", "\\supsetneq": "⊋", "\\in": "∈", "\\ni": "∋",
    "\\notin": "∉", "\\mid": "∣", "\\nmid": "∤", "\\parallel": "∥", "\\nparallel": "∦",
    "\\perp": "⊥", "\\vdash": "⊢", "\\dashv": "⊣", "\\models": "⊨", "\\asymp": "≍",
    "\\doteq": "≐", "\\ngtr": "≯", "\\nless": "≮", "\\nleq": "≰", "\\ngeq": "≱",
    "\\lneqq": "≨", "\\gneqq": "≩", "\\nsubseteq": "⊈", "\\nsupseteq": "⊉", "\\nsim": "≁",
    "\\ncong": "≇", "\\napprox": "≉",
    # Mũi tên
    "\\to": "→", "\\rightarrow": "→", "\\leftarrow": "←", "\\gets": "←",
    "\\leftrightarrow": "↔", "\\Rightarrow": "⇒", "\\Leftarrow": "⇐", "\\Leftrightarrow": "⇔",
    "\\iff": "⇔", "\\implies": "⇒", "\\impliedby": "⇐", "\\mapsto": "↦",
    "\\longrightarrow": "→", "\\longleftarrow": "←", "\\longleftrightarrow": "↔",
    "\\Longrightarrow": "⇒", "\\Longleftarrow": "⇐", "\\Longleftrightarrow": "⇔",
    "\\longmapsto": "↦", "\\uparrow": "↑", "\\downarrow": "↓", "\\updownarrow": "↕",
    "\\Uparrow": "⇑", "\\Downarrow": "⇓", "\\nearrow": "↗", "\\searrow": "↘",
    "\\nwarrow": "↖", "\\swarrow": "↙", "\\hookrightarrow": "↪", "\\rightleftharpoons": "⇌",
    "\\leadsto": "⇝",
    # Logic, tập hợp, hình học
    "\\infty": "∞", "\\forall": "∀", "\\exists": "∃", "\\nexists": "∄", "\\neg": "¬",
    "\\lnot": "¬", "\\emptyset": "∅", "\\varnothing": "∅", "\\partial": "∂", "\\nabla": "∇",
    "\\angle": "∠", "\\measuredangle": "∡", "\\triangle": "△", "\\square": "□", "\\Box": "□",
    "\\blacksquare": "■", "\\therefore": "∴", "\\because": "∵", "\\top": "⊤", "\\bot": "⊥",
    "\\prime": "′", "\\backslash": "\\", "\\surd": "√", "\\checkmark": "✓", "\\degree": "°",
    "\\textdegree": "°", "\\lbrace": "{", "\\rbrace": "}", "\\lvert": "|", "\\rvert": "|",
    "\\vert": "|", "\\lVert": "‖", "\\rVert": "‖", "\\Vert": "‖", "\\langle": "⟨",
    "\\rangle": "⟩", "\\lfloor": "⌊", "\\rfloor": "⌋", "\\lceil": "⌈", "\\rceil": "⌉",
    # Dấu chấm
    "\\ldots": "…", "\\dots": "…", "\\dotsc": "…", "\\cdots": "⋯", "\\dotsb": "⋯",
    "\\dotsm": "⋯", "\\dotsi": "⋯", "\\vdots": "⋮", "\\ddots": "⋱",
}

# Các ký tự điều khiển một ký tự sau dấu gạch chéo ngược: \{ \} \% ...
CONTROL_SYMBOLS: dict[str, str] = {
    "{": "{", "}": "}", "%": "%", "$": "$", "&": "&", "#": "#", "_": "_", "|": "‖",
    ",": " ", ";": " ", ":": " ", "!": " ", " ": " ", "/": "", "-": "",
}

# Từ hàm toán học chuẩn (render như một từ đứng thẳng, không phải chuỗi biến)
FUNCTION_NAMES: frozenset[str] = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "arccot",
    "sinh", "cosh", "tanh", "coth", "log", "ln", "lg", "exp", "lim", "limsup", "liminf",
    "max", "min", "sup", "inf", "det", "gcd", "deg", "dim", "ker", "hom", "arg", "Pr", "mod",
})
# Hàm đặt cận DƯỚI (khi trình bày dạng display): \lim_{x\to 0}
LIMIT_FUNCTIONS: frozenset[str] = frozenset({
    "lim", "limsup", "liminf", "max", "min", "sup", "inf", "det", "gcd", "Pr",
})

BIG_OPERATORS: frozenset[str] = frozenset("∑∏∐∫∬∭∮⋃⋂⋁⋀⨁⨂⨆")
# Toán tử lớn mà cận luôn đặt bên cạnh (kể cả display) theo quy ước TeX
SIDE_LIMIT_OPERATORS: frozenset[str] = frozenset("∫∬∭∮")

# ---------------------------------------------------------------------------------------------
# Phân lớp kiểu TeX để dàn khoảng cách
# ---------------------------------------------------------------------------------------------
RELATIONS: frozenset[str] = frozenset(
    "=<>≤≥≠≈≡∼≃≅∝≪≫≺≻⪯⪰⊂⊃⊆⊇⊊⊋∈∋∉∣∤∥∦⊥⊢⊣⊨≍≐≯≮≰≱≨≩⊈⊉≁≇≉"
    "←→↔⇐⇒⇔↦↑↓↕⇑⇓↗↘↖↙↪⇌⇝:∴∵"
)
BINARY_OPS: frozenset[str] = frozenset("+-±∓×÷·∗⋆∘•⊕⊖⊗⊘⊙∩∪⊎⊓⊔∨∧∖≀⋄†‡⨿*")
OPENERS: frozenset[str] = frozenset("([{⟨⌊⌈")
CLOSERS: frozenset[str] = frozenset(")]}⟩⌋⌉")
PUNCTUATION: frozenset[str] = frozenset(",;")

# ---------------------------------------------------------------------------------------------
# Chuẩn hoá ký tự Unicode gặp trong LaTeX/OMML
# ---------------------------------------------------------------------------------------------
UNICODE_CANON: dict[str, str] = {
    "\u2212": "-",   # dấu trừ toán học (Word dùng) -> '-'
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u22c5": "·",   # dot operator
    "\u2219": "·",   # bullet operator
    "\u00b7": "·",
    "\u2217": "*",   # asterisk operator
    "\u2215": "/", "\u2044": "/",
    "\u00d7": "×",
    "\u2236": ":",
    "\u2032": "′", "\u2033": "″", "\u2034": "‴",
    "\u27c2": "⊥",
}

# Ký tự khoảng trắng Unicode -> độ rộng theo em (0 = bỏ qua)
UNICODE_SPACES: dict[str, float] = {
    "\u00a0": 0.28, "\u2002": 0.5, "\u2003": 1.0, "\u2001": 1.0, "\u2004": 0.33,
    "\u2005": 0.25, "\u2006": 0.17, "\u2009": 0.17, "\u200a": 0.1, "\u202f": 0.17,
    "\u205f": 0.22, "\u3000": 1.0,
}

# Độ rộng khoảng trắng của các macro (đơn vị em)
SPACE_COMMANDS: dict[str, float] = {
    "\\,": 0.1667, "\\thinspace": 0.1667, "\\:": 0.2222, "\\medspace": 0.2222,
    "\\;": 0.2778, "\\thickspace": 0.2778, "\\!": -0.1667, "\\negthinspace": -0.1667,
    "\\ ": 0.33, "\\enspace": 0.5, "\\quad": 1.0, "\\qquad": 2.0,
}


def is_symbol_letter(ch: str) -> bool:
    """Chữ cái được coi là KÝ HIỆU toán (Hy Lạp, ℝ ℕ ℓ..., chữ in đậm/viết tay Unicode) chứ không phải biến Latin."""
    o = ord(ch)
    return 0x0370 <= o <= 0x03FF or 0x2100 <= o <= 0x214F or 0x1D400 <= o <= 0x1D7FF


def canon_symbol(ch: str) -> str:
    """Chuẩn hoá một ký tự Unicode sang dạng chuẩn dùng trong kho mẫu (vd. U+2212 -> '-')."""
    return UNICODE_CANON.get(ch, ch)


def symbol_class(sym: str) -> str:
    """Phân lớp ký hiệu theo TeX: 'rel', 'bin', 'open', 'close', 'punct', 'op' hoặc 'ord'."""
    if len(sym) != 1:
        return "ord"
    if sym in RELATIONS:
        return "rel"
    if sym in BINARY_OPS:
        return "bin"
    if sym in OPENERS:
        return "open"
    if sym in CLOSERS:
        return "close"
    if sym in PUNCTUATION:
        return "punct"
    if sym in BIG_OPERATORS:
        return "op"
    return "ord"


def double_struck(ch: str) -> str:
    """Chữ/chữ số kiểu \\mathbb ('R' -> 'ℝ'); không có thì trả lại ký tự gốc."""
    return _styled(ch, "DOUBLE-STRUCK")


def script_style(ch: str) -> str:
    """Chữ viết hoa kiểu \\mathcal ('L' -> 'ℒ'); không có thì trả lại ký tự gốc."""
    return _styled(ch, "SCRIPT")


def fraktur_style(ch: str) -> str:
    """Chữ kiểu \\mathfrak."""
    return _styled(ch, "FRAKTUR")


def _styled(ch: str, style: str) -> str:
    if len(ch) != 1:
        return ch
    if ch.isdigit() and style == "DOUBLE-STRUCK":
        names = [f"MATHEMATICAL DOUBLE-STRUCK DIGIT {unicodedata.name(ch).split()[-1]}"]
    elif ch.isalpha() and ch.isascii():
        case = "CAPITAL" if ch.isupper() else "SMALL"
        letter = ch.upper()
        if style == "DOUBLE-STRUCK":
            names = [f"DOUBLE-STRUCK {case} {letter}", f"MATHEMATICAL DOUBLE-STRUCK {case} {letter}"]
        elif style == "SCRIPT":
            names = [f"SCRIPT {case} {letter}", f"MATHEMATICAL SCRIPT {case} {letter}"]
        else:
            names = [f"BLACK-LETTER {case} {letter}", f"MATHEMATICAL FRAKTUR {case} {letter}"]
    else:
        return ch
    for name in names:
        try:
            return unicodedata.lookup(name)
        except KeyError:
            continue
    return ch
