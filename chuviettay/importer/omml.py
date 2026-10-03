"""Chuyển công thức Office Math (OMML, ``m:oMath``) của Word sang Math AST.

Phủ toàn bộ cấu trúc thường gặp: phân số (``m:f``), chỉ số (``m:sSup/sSub/sSubSup/sPre``), căn
(``m:rad``), ngoặc co giãn nhiều phần tử (``m:d``), toán tử lớn có cận (``m:nary``), giới hạn
(``m:limLow/limUpp``), hàm (``m:func``), dấu trang trí (``m:acc``, ``m:bar``, ``m:groupChr``), hệ phương
trình/căn lề (``m:eqArr``), ma trận (``m:m``), khung (``m:borderBox``) và chữ thường (``m:nor``).

Điểm khác biệt chính so với cách làm cũ (coi cả ``m:r`` là một ký hiệu): chuỗi ``2x+3=0`` trong MỘT
``m:r`` được tách thành số / biến / toán tử riêng, dấu trừ U+2212 của Word được chuẩn hoá thành ``-``.
Cấu trúc chưa biết không bị bỏ im lặng: tên thẻ được trả về để importer báo cáo.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

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
from chuviettay.math.build import PRIME_CHARS, degree_sign, fold_primes, text_node, unwrap
from chuviettay.math.symbols import (
    FUNCTION_NAMES,
    LIMIT_FUNCTIONS,
    UNICODE_SPACES,
    canon_symbol,
    double_struck,
    is_symbol_letter,
    fraktur_style,
    script_style,
)

__all__ = ["M_NS", "W_NS", "omml_to_ast", "iter_omath"]

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Số: 3.14 / 1.000.000 / 13,65 (Word gõ dấu phẩy thập phân kiểu Việt Nam trong CÙNG một run; danh sách
# 1,2,3 trong một run thì dấu phẩy vẫn là dấu ngăn cách).
_NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*(?:,[0-9]+(?![0-9]|,[0-9]))?")

_ACCENT_KIND = {
    "\u0302": "hat", "^": "hat", "\u02c6": "hat", "\u0303": "tilde", "~": "tilde", "\u02dc": "tilde",
    "\u0305": "bar", "\u00af": "bar", "\u203e": "bar", "\u0304": "bar", "\u2015": "bar",
    "\u20d7": "vec", "\u2192": "overrightarrow", "\u20d6": "overleftarrow", "\u2190": "overleftarrow",
    "\u20e1": "overleftrightarrow", "\u2194": "overleftrightarrow", "\u0307": "dot", "\u02d9": "dot",
    "\u0308": "ddot", "\u00a8": "ddot", "\u20db": "dddot", "\u0301": "acute", "\u00b4": "acute",
    "\u0300": "grave", "`": "grave", "\u030c": "check", "\u02c7": "check", "\u0306": "breve",
    "\u02d8": "breve", "\u030a": "mathring", "\u02da": "mathring",
}
_WIDE_ACCENT = {"hat": "widehat", "tilde": "widetilde", "vec": "overrightarrow"}
_PROPERTY_TAGS = frozenset({
    "accPr", "barPr", "borderBoxPr", "boxPr", "dPr", "eqArrPr", "fPr", "funcPr", "groupChrPr",
    "limLowPr", "limUppPr", "mPr", "naryPr", "phantPr", "radPr", "sPrePr", "sSubPr", "sSubSupPr",
    "sSupPr", "ctrlPr", "oMathParaPr", "rPr", "mcs", "mcPr", "mc", "argPr",
})
_ARG_TAGS = frozenset({"e", "num", "den", "sub", "sup", "deg", "lim", "fName", "mr"})
_TRUE_VALUES = frozenset({"1", "on", "true", "t"})


def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _is_m(el: Any, name: str) -> bool:
    return getattr(el, "tag", None) == f"{{{M_NS}}}{name}"


def _val(el: Any) -> str | None:
    """Giá trị ``m:val`` của một phần tử thuộc tính (None nếu thiếu phần tử/thuộc tính)."""
    if el is None:
        return None
    v = el.get(f"{{{M_NS}}}val")
    if v is None:
        v = el.get("val")
    return v


def _find(parent: Any, name: str) -> Any:
    for c in parent:
        if _is_m(c, name):
            return c
    return None


def _children_m(parent: Any, name: str) -> list[Any]:
    return [c for c in parent if _is_m(c, name)]


def iter_omath(container: Any) -> Iterable[Any]:
    """Các ``m:oMath`` nằm trong ``container`` (chính nó nếu ``container`` là ``m:oMath``)."""
    if _is_m(container, "oMath"):
        yield container
        return
    for c in container:
        if _is_m(c, "oMath"):
            yield c
        elif _is_m(c, "oMathPara"):
            yield from iter_omath(c)


class _Converter:
    def __init__(self) -> None:
        self.unsupported: list[str] = []

    # ------------------------------------------------------------------ helper
    def _note_unsupported(self, tag: str) -> None:
        if tag not in self.unsupported:
            self.unsupported.append(tag)

    def row(self, parent: Any, upright: bool = False) -> MathRow:
        """Chuyển các phần tử con của ``parent`` thành một MathRow."""
        if parent is None:
            return MathRow([])
        return MathRow(fold_primes(self.children(parent, upright)))

    def children(self, parent: Any, upright: bool = False) -> list[MathNode]:
        nodes: list[MathNode] = []
        for c in parent:
            nodes.extend(self.element(c, upright))
        return nodes

    def element(self, el: Any, upright: bool = False) -> list[MathNode]:
        tag = _local(el.tag)
        if el.tag != f"{{{M_NS}}}{tag}":
            if el.tag == f"{{{W_NS}}}r":      # chạy văn bản thường nằm trong oMath
                text = "".join(t.text or "" for t in el if _local(t.tag) == "t")
                return [text_node(text, "text")] if text else []
            if el.tag == f"{{{W_NS}}}ins":    # nội dung chèn (theo dõi thay đổi) vẫn tính
                return self.children(el, upright)
            return []                         # w:del và các thẻ ngoài không gian tên toán: bỏ
        if tag in _PROPERTY_TAGS:
            return []
        handler = getattr(self, "_e_" + tag, None)
        if handler is None:
            if tag in _ARG_TAGS or tag in ("oMath", "oMathPara"):
                return self.children(el, upright)
            self._note_unsupported(tag)
            return self.children(el, upright)       # vẫn giữ phần chữ bên trong
        return handler(el, upright)

    # ------------------------------------------------------------------ chạy văn bản
    def _e_r(self, r: Any, upright: bool) -> list[MathNode]:
        rpr = _find(r, "rPr")
        normal = style = scr = None
        literal = False
        if rpr is not None:
            normal = _find(rpr, "nor") is not None
            literal = _find(rpr, "lit") is not None
            style = _val(_find(rpr, "sty"))
            scr = _val(_find(rpr, "scr"))
        text = "".join(t.text or "" for t in r if _is_m(t, "t") or t.tag == f"{{{W_NS}}}t")
        if not text:
            return []
        if normal or literal:
            node = text_node(text, "text")
            return list(node.items) if isinstance(node, MathRow) else [node]
        return tokenize_run(text, upright=upright or style == "p", scr=scr)

    # ------------------------------------------------------------------ cấu trúc
    def _e_f(self, f: Any, upright: bool) -> list[MathNode]:
        kind = _val(_find(_find(f, "fPr"), "type")) if _find(f, "fPr") is not None else None
        num, den = self.row(_find(f, "num")), self.row(_find(f, "den"))
        if kind in ("lin", "skw"):
            return [*num.items, SymbolNode("/"), *den.items]
        return [Fraction(num=num, den=den, bar=(kind != "noBar"))]

    def _e_sSup(self, el: Any, upright: bool) -> list[MathNode]:
        base = unwrap(self.row(_find(el, "e")))
        return [Superscript(base=base, exp=degree_sign(self.row(_find(el, "sup"))))]

    def _e_sSub(self, el: Any, upright: bool) -> list[MathNode]:
        base_row = self.row(_find(el, "e"))
        sub = self.row(_find(el, "sub"))
        last = base_row.items[-1] if base_row.items else None
        if isinstance(last, Superscript) and last.exp.items and all(
                isinstance(x, SymbolNode) and x.symbol in PRIME_CHARS for x in last.exp.items):
            # w′ có chỉ số dưới A: dấu nháy là số mũ của w, xếp chồng với chỉ số dưới như w'_A trong LaTeX
            core = unwrap(MathRow([*base_row.items[:-1], last.base]))
            return [SubSuperscript(base=core, sub=sub, exp=last.exp)]
        return [Subscript(base=unwrap(base_row), sub=sub)]

    def _e_sSubSup(self, el: Any, upright: bool) -> list[MathNode]:
        base = unwrap(self.row(_find(el, "e")))
        return [SubSuperscript(base=base, sub=self.row(_find(el, "sub")),
                               exp=degree_sign(self.row(_find(el, "sup"))))]

    def _e_sPre(self, el: Any, upright: bool) -> list[MathNode]:
        pre = SubSuperscript(base=MathRow([]), sub=self.row(_find(el, "sub")),
                             exp=self.row(_find(el, "sup")))
        return [pre, *self.row(_find(el, "e")).items]

    def _e_rad(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "radPr")
        hidden = pr is not None and (_val(_find(pr, "degHide")) or "0").lower() in _TRUE_VALUES
        deg_el = _find(el, "deg")
        degree = None
        if not hidden and deg_el is not None:
            deg = self.row(deg_el)
            degree = deg if deg.items else None
        return [Root(radicand=self.row(_find(el, "e")), degree=degree)]

    def _delimiter_chars(self, pr: Any) -> tuple[str, str, str]:
        """Ký tự mở / đóng / ngăn cách của ``m:d`` (thiếu phần tử = mặc định, ``m:val=""`` = không có)."""
        def pick(name: str, default: str) -> str:
            el = _find(pr, name) if pr is not None else None
            if el is None:
                return default
            v = _val(el)
            return default if v is None else v
        left, right, sep = pick("begChr", "("), pick("endChr", ")"), pick("sepChr", "|")
        fix = {"\u2225": "‖", "\u2223": "|"}
        return fix.get(left, left), fix.get(right, right), fix.get(sep, sep)

    def _e_d(self, el: Any, upright: bool) -> list[MathNode]:
        left, right, sep = self._delimiter_chars(_find(el, "dPr"))
        args = _children_m(el, "e")
        if len(args) == 1 and _find(args[0], "eqArr") is not None and len(args[0]) == 1:
            matrix = self._eqarr(_find(args[0], "eqArr"), cases=(left == "{" and right == ""))
            return [Delimited(canon_symbol(left), canon_symbol(right), matrix)]
        body: MathNode
        items: list[MathNode] = []
        for i, a in enumerate(args):
            if i and sep:
                items.append(SymbolNode(canon_symbol(sep)))
            items.extend(self.row(a).items)
        body = MathRow(items)
        # Một phần tử duy nhất là ma trận / phân số không gạch -> giữ nguyên làm thân ngoặc
        if len(items) == 1 and (isinstance(items[0], Matrix) or (isinstance(items[0], Fraction) and not items[0].bar)):
            body = items[0]
            if isinstance(body, Matrix) and body.kind == "matrix" and left == "{" and right == "":
                # dấu { không đóng bao một ma trận: đó là hệ phương trình/định nghĩa từng khúc (cases), căn trái
                body = Matrix(rows=body.rows, kind="cases", col_align=["l"] * max(len(r) for r in body.rows))
        return [Delimited(canon_symbol(left), canon_symbol(right), body)]

    def _e_nary(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "naryPr")
        chr_el = _find(pr, "chr") if pr is not None else None
        op = "∫" if chr_el is None else (_val(chr_el) if _val(chr_el) is not None else "∫")
        sub_hide = pr is not None and (_val(_find(pr, "subHide")) or "0").lower() in _TRUE_VALUES
        sup_hide = pr is not None and (_val(_find(pr, "supHide")) or "0").lower() in _TRUE_VALUES
        loc = _val(_find(pr, "limLoc")) if pr is not None else None
        sub = None if sub_hide else self.row(_find(el, "sub"))
        sup = None if sup_hide else self.row(_find(el, "sup"))
        sub = sub if sub is not None and sub.items else None
        sup = sup if sup is not None and sup.items else None
        body = self.row(_find(el, "e")).items
        if not op:
            return list(body)
        limits = {"undOvr": True, "subSup": False}.get(loc or "")
        return [NAry(op=op, sub=sub, sup=sup, limits=limits), *body]

    def _e_limLow(self, el: Any, upright: bool) -> list[MathNode]:
        return self._limit(el, below=True)

    def _e_limUpp(self, el: Any, upright: bool) -> list[MathNode]:
        return self._limit(el, below=False)

    def _limit(self, el: Any, below: bool) -> list[MathNode]:
        base = self.row(_find(el, "e"), upright=True)
        lim = self.row(_find(el, "lim"))
        if below and len(base.items) == 1 and isinstance(base.items[0], TextNode) \
                and base.items[0].kind == "func" and base.items[0].text in LIMIT_FUNCTIONS:
            return [NAry(op=base.items[0].text, sub=lim, sup=None, limits=True, is_function=True)]
        if below:
            return [OverUnder(base=unwrap(base), under=lim)]
        return [OverUnder(base=unwrap(base), over=lim)]

    def _e_func(self, el: Any, upright: bool) -> list[MathNode]:
        name = self.row(_find(el, "fName"), upright=True)
        return [*name.items, *self.row(_find(el, "e")).items]

    def _e_bar(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "barPr")
        pos = _val(_find(pr, "pos")) if pr is not None else None
        kind = "overline" if pos == "top" else "underline"
        return [Accent(base=self.row(_find(el, "e")), kind=kind)]

    def _e_acc(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "accPr")
        chr_el = _find(pr, "chr") if pr is not None else None
        ch = _val(chr_el) if chr_el is not None else "\u0302"
        kind = _ACCENT_KIND.get(ch or "\u0302", "hat")
        base = self.row(_find(el, "e"))
        if len(base.items) > 1 or (base.items and isinstance(base.items[0], TextNode) and len(base.items[0].text) > 1):
            kind = _WIDE_ACCENT.get(kind, kind)
        return [Accent(base=base, kind=kind)]

    def _e_groupChr(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "groupChrPr")
        chr_el = _find(pr, "chr") if pr is not None else None
        ch = _val(chr_el) if chr_el is not None else "\u23df"
        pos = (_val(_find(pr, "pos")) if pr is not None else None) or "bot"
        top = pos == "top"
        kind = {
            "\u23de": "overbrace", "\u23df": "underbrace", "\u2192": "overrightarrow",
            "\u2190": "overleftarrow", "\u2194": "overleftrightarrow",
        }.get(ch or "\u23df")
        if kind is None:
            kind = "overline" if top else "underline"
        elif not top and kind.startswith("over") and kind != "overbrace":
            kind = kind.replace("over", "under", 1)
        elif top and kind == "underbrace":
            kind = "overbrace"
        elif not top and kind == "overbrace":
            kind = "underbrace"
        return [Accent(base=self.row(_find(el, "e")), kind=kind)]

    def _eqarr(self, el: Any, cases: bool = False) -> Matrix:
        rows: list[list[MathNode]] = []
        for e in _children_m(el, "e"):
            cells: list[MathRow] = [MathRow([])]
            for node in self.row(e).items:
                if isinstance(node, SymbolNode) and node.symbol == "&":
                    cells.append(MathRow([]))
                else:
                    cells[-1].items.append(node)
            rows.append(list(cells))
        ncols = max((len(r) for r in rows), default=1)
        if cases:
            return Matrix(rows=rows, kind="cases", col_align=["l"] * ncols)
        if ncols > 1:
            return Matrix(rows=rows, kind="aligned", col_align=[("r" if i % 2 == 0 else "l") for i in range(ncols)])
        return Matrix(rows=rows, kind="lines", col_align=["c"])

    def _e_eqArr(self, el: Any, upright: bool) -> list[MathNode]:
        return [self._eqarr(el)]

    def _e_m(self, el: Any, upright: bool) -> list[MathNode]:
        rows = [[self.row(c) for c in _children_m(mr, "e")] for mr in _children_m(el, "mr")]
        ncols = max((len(r) for r in rows), default=1)
        aligns = ["c"] * ncols
        mcs = _find(_find(el, "mPr"), "mcs") if _find(el, "mPr") is not None else None
        if mcs is not None:
            col = 0
            for mc in _children_m(mcs, "mc"):
                pr = _find(mc, "mcPr")
                count = int(_val(_find(pr, "count")) or 1) if pr is not None else 1
                jc = (_val(_find(pr, "mcJc")) or "center") if pr is not None else "center"
                letter = {"left": "l", "right": "r"}.get(jc, "c")
                for _ in range(count):
                    if col < ncols:
                        aligns[col] = letter
                        col += 1
        return [Matrix(rows=[list(r) for r in rows], kind="matrix", col_align=aligns)]

    def _e_box(self, el: Any, upright: bool) -> list[MathNode]:
        return list(self.row(_find(el, "e")).items)

    def _e_borderBox(self, el: Any, upright: bool) -> list[MathNode]:
        return [Boxed(body=self.row(_find(el, "e")))]

    def _e_phant(self, el: Any, upright: bool) -> list[MathNode]:
        pr = _find(el, "phantPr")
        show = (_val(_find(pr, "show")) or "1").lower() if pr is not None else "1"
        body = self.row(_find(el, "e"))
        if show in _TRUE_VALUES:
            return list(body.items)
        return [SpaceNode(max(0.3, 0.55 * len(body.items)))]


def tokenize_run(text: str, upright: bool = False, scr: str | None = None) -> list[MathNode]:
    """Tách một chuỗi trong ``m:r`` thành số / biến / hàm / ký hiệu (giống bộ phân tích LaTeX)."""
    style = {"double-struck": double_struck, "script": script_style, "fraktur": fraktur_style}.get(scr or "")
    nodes: list[MathNode] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in UNICODE_SPACES:
            nodes.append(SpaceNode(UNICODE_SPACES[ch]))
            i += 1
        elif ch.isspace():
            i += 1
        elif "0" <= ch <= "9":
            m = _NUM_RE.match(text, i)
            tok = m.group(0) if m else ch
            in_list = (len(nodes) >= 2 and nodes[-1] == SymbolNode(",")
                       and isinstance(nodes[-2], TextNode) and nodes[-2].kind == "num")
            if in_list and "," in tok:        # 1,2,3: dấu phẩy ngăn cách danh sách, không phải thập phân
                tok = tok.split(",", 1)[0]
            if style is not None and len(tok) == 1:
                mapped = style(tok)
                if mapped != tok:
                    nodes.append(SymbolNode(mapped))
                    i += 1
                    continue
            nodes.append(TextNode(tok, kind="num"))
            i += len(tok)
        elif ch.isalpha() and not is_symbol_letter(ch):
            j = i
            while j < n and text[j].isalpha() and not is_symbol_letter(text[j]):
                j += 1
            word = text[i:j]
            i = j
            if style is not None:
                for c in word:
                    mapped = style(c)
                    nodes.append(SymbolNode(mapped) if mapped != c else TextNode(c, kind="var"))
            elif word in FUNCTION_NAMES and (upright or len(word) > 1):
                nodes.append(TextNode(word, kind="func"))
            elif upright:
                nodes.append(TextNode(word, kind="text"))
            else:
                for c in word:
                    mapped = style(c) if style is not None else c
                    nodes.append(SymbolNode(mapped) if mapped != c else TextNode(c, kind="var"))
        elif ch.isalpha():            # chữ Hy Lạp, ℝ ℕ ℓ ... : ký hiệu
            nodes.append(SymbolNode(ch))
            i += 1
        else:
            nodes.append(SymbolNode(canon_symbol(ch)))
            i += 1
    return nodes


def omml_to_ast(omath: Any) -> tuple[MathRow, list[str]]:
    """Chuyển một ``m:oMath`` thành (MathRow, danh sách tên thẻ OMML chưa hỗ trợ)."""
    conv = _Converter()
    row = conv.row(omath)
    return row, conv.unsupported
