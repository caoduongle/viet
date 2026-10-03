"""Tiện ích dùng chung cho các test toán: kho mẫu 'hộp chữ' và bộ chuẩn hoá AST để so sánh."""
from __future__ import annotations

import dataclasses
import gzip
import json
import os

from chuviettay.math.ast import MathNode, MathRow


def make_block_bank(path: str, xh: float = 7.0, with_letters: bool = True) -> str:
    """Kho mẫu giả lập: mỗi chữ/số/dấu là một hình chữ nhật có kích thước xác định (đủ để kiểm tra hình học)."""
    def box(w: float, top: float, bottom: float = 0.0) -> dict:
        return {"w": w, "s": [[0.0, bottom, w - 1.0, bottom, w - 1.0, -top, 0.0, -top, 0.0, bottom]],
                "T": "", "vi": -1, "ti": -1}

    words, digits, punct = {}, {}, {}
    if with_letters:
        for ch in "abcdefghijklmnopqrstuvwxyz":
            words[ch] = [box(0.8 * xh, xh * (1.45 if ch in "bdfhklt" else 1.0), xh * (0.4 if ch in "gjpqy" else 0.0))]
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            words[ch] = [box(0.95 * xh, xh * 1.45)]
    for ch in "0123456789":
        digits[ch] = [box(0.8 * xh, xh * 1.45)]
    for ch in ",.()[]|":
        punct[ch] = [box(0.4 * xh, xh * 1.2)]
    data = {"schema_version": 2, "xh": xh, "wgaps": [6.0], "dgaps": [1.0], "line": 24.0, "v": 1, "x0": 78.0,
            "width": 500.0, "ratio": 6.6,
            "pen": {"tool": "pen", "color": "#000000ff", "width": "1.41", "capStyle": "round"},
            "words": words, "digits": digits, "punct": punct}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def canon(node):
    """Làm phẳng MathRow lồng nhau và bỏ lớp bọc một phần tử để so sánh cấu trúc hai AST."""
    if isinstance(node, MathRow):
        flat: list = []
        for it in node.items:
            c = canon(it)
            flat.extend(c.items if isinstance(c, MathRow) else [c])
        return flat[0] if len(flat) == 1 else MathRow(flat)
    if dataclasses.is_dataclass(node):
        kw = {}
        for f in dataclasses.fields(node):
            v = getattr(node, f.name)
            if isinstance(v, MathNode):
                v = canon(v)
            elif isinstance(v, list):
                v = [[canon(c) if isinstance(c, MathNode) else c for c in x] if isinstance(x, list)
                     else (canon(x) if isinstance(x, MathNode) else x) for x in v]
            kw[f.name] = v
        return type(node)(**kw)
    return node


def canon_for_compare(node):
    """Chuẩn hoá thêm để so sánh đường LaTeX với đường OMML (pandoc/Word) - chỉ bỏ khác biệt vô hại:
    SpaceNode, ngoặc dạng Delimited <-> ký hiệu rời, cận mặc định của NAry, Matrix aligned/cases ~ matrix,
    chỉ số bám cả cụm ngoặc (OMML) ~ bám dấu đóng (LaTeX)."""
    from chuviettay.math.ast import Delimited, Matrix, NAry, SpaceNode, Subscript, SubSuperscript, Superscript, SymbolNode

    def go(x):
        if isinstance(x, MathRow):
            items = []
            for i in x.items:
                c = go(i)
                if isinstance(c, SpaceNode):
                    continue
                items.extend(c.items if isinstance(c, MathRow) else [c])
            return items[0] if len(items) == 1 else MathRow(items)
        if isinstance(x, Delimited) and not isinstance(x.body, Matrix) and type(x.body).__name__ != "Fraction":
            parts = ([SymbolNode(x.left)] if x.left else []) + [x.body] + ([SymbolNode(x.right)] if x.right else [])
            return go(MathRow(parts))
        if isinstance(x, Matrix):
            return Matrix(rows=[[go(c) for c in r] for r in x.rows], kind="matrix", col_align=[])
        if isinstance(x, (Superscript, Subscript, SubSuperscript)) and isinstance(x.base, Delimited):
            inner = go(x.base)
            items = list(inner.items) if isinstance(inner, MathRow) else [inner]
            kw = {f: go(getattr(x, f)) for f in ("sub", "exp") if hasattr(x, f)}
            return MathRow(items[:-1] + [type(x)(base=items[-1], **kw)])
        if isinstance(x, NAry):
            x = NAry(op=x.op, sub=x.sub, sup=x.sup, limits=None, is_function=x.is_function)
        if dataclasses.is_dataclass(x):
            kw = {}
            for f in dataclasses.fields(x):
                v = getattr(x, f.name)
                if isinstance(v, MathNode):
                    v = go(v)
                elif isinstance(v, list):
                    v = [[go(c) if isinstance(c, MathNode) else c for c in y] if isinstance(y, list)
                         else (go(y) if isinstance(y, MathNode) else y) for y in v]
                kw[f.name] = v
            return type(x)(**kw)
        return x

    return go(node)
