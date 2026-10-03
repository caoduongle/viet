"""Nét vector dự phòng cho ký hiệu toán học khi kho mẫu chưa có chữ viết tay tương ứng.

Thuần hình học, không phụ thuộc kho mẫu/Writer:
- ``small_glyph``: ký hiệu cỡ chữ thường, toạ độ theo đơn vị x-height (trục y hướng LÊN từ baseline).
- ``delimiter_polylines`` / ``bigop_polylines`` / ``accent_polylines``: hình co giãn theo hộp w x h,
  toạ độ cục bộ góc trên-trái, trục y hướng XUỐNG (như màn hình).
"""
from __future__ import annotations

import math

Point = tuple[float, float]
Polyline = list[Point]


def _arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float, n: int = 14) -> Polyline:
    """Cung elip (góc theo độ, y hướng lên) -> đa tuyến."""
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return pts


def _circle(cx: float, cy: float, r: float, n: int = 16) -> Polyline:
    return _arc(cx, cy, r, r, 0, 360, n)


def _wave(x0: float, x1: float, y: float, amp: float, n: int = 12) -> Polyline:
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def _dot(x: float, y: float, size: float = 0.07) -> Polyline:
    return [(x, y), (x + size, y + size * 0.6)]


def _mirror_x(poly: Polyline, width: float) -> Polyline:
    return [(width - x, y) for x, y in poly]


def _flip_y(poly: Polyline, top: float) -> Polyline:
    return [(x, top - y) for x, y in poly]


def _lemniscate(cx: float, cy: float, a: float, b: float, n: int = 28) -> Polyline:
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        d = 1 + math.sin(t) ** 2
        pts.append((cx + a * math.cos(t) / d, cy + b * math.sin(t) * math.cos(t) / d))
    return pts


def _arrow(x0: float, x1: float, y: float, head: float = 0.27, half: float = 0.26, left: bool = False,
           both: bool = False) -> list[Polyline]:
    out: list[Polyline] = [[(x0, y), (x1, y)]]
    if not left or both:
        out.append([(x1 - head, y + half), (x1, y), (x1 - head, y - half)])
    if left or both:
        out.append([(x0 + head, y + half), (x0, y), (x0 + head, y - half)])
    return out


_MEMBER_ARC: Polyline = [(0.72, 0.9), (0.4, 0.9), (0.15, 0.7), (0.15, 0.2), (0.4, 0.0), (0.72, 0.0)]

# (độ rộng, [đa tuyến]) -- toạ độ theo x-height, y hướng lên (0 = baseline, 1 = đỉnh chữ thường)
_SMALL: dict[str, tuple[float, list[Polyline]]] = {
    "±": (0.9, [[(0.1, 0.78), (0.8, 0.78)], [(0.45, 0.45), (0.45, 1.1)], [(0.1, 0.12), (0.8, 0.12)]]),
    "∓": (0.9, [[(0.1, 0.9), (0.8, 0.9)], [(0.1, 0.35), (0.8, 0.35)], [(0.45, 0.0), (0.45, 0.7)]]),
    "×": (0.9, [[(0.12, 0.12), (0.78, 0.78)], [(0.12, 0.78), (0.78, 0.12)]]),
    "÷": (0.9, [[(0.1, 0.45), (0.8, 0.45)], _dot(0.43, 0.8), _dot(0.43, 0.08)]),
    "·": (0.35, [_dot(0.14, 0.45)]),
    "∘": (0.55, [_circle(0.28, 0.45, 0.2)]),
    "∗": (0.6, [[(0.3, 0.95), (0.3, 0.45)], [(0.08, 0.83), (0.52, 0.57)], [(0.08, 0.57), (0.52, 0.83)]]),
    "°": (0.5, [_circle(0.25, 1.15, 0.2)]),
    "′": (0.3, [[(0.14, 1.3), (0.2, 0.85)]]),
    "″": (0.5, [[(0.14, 1.3), (0.2, 0.85)], [(0.32, 1.3), (0.38, 0.85)]]),
    "‴": (0.7, [[(0.14, 1.3), (0.2, 0.85)], [(0.32, 1.3), (0.38, 0.85)], [(0.5, 1.3), (0.56, 0.85)]]),
    "≤": (0.9, [[(0.8, 0.9), (0.1, 0.55), (0.8, 0.2)], [(0.1, -0.02), (0.8, -0.02)]]),
    "≥": (0.9, [[(0.1, 0.9), (0.8, 0.55), (0.1, 0.2)], [(0.1, -0.02), (0.8, -0.02)]]),
    "≠": (0.9, [[(0.1, 0.3), (0.8, 0.3)], [(0.1, 0.62), (0.8, 0.62)], [(0.28, 0.0), (0.62, 0.92)]]),
    "≈": (0.9, [_wave(0.1, 0.8, 0.64, 0.07), _wave(0.1, 0.8, 0.3, 0.07)]),
    "≡": (0.9, [[(0.1, 0.2), (0.8, 0.2)], [(0.1, 0.45), (0.8, 0.45)], [(0.1, 0.7), (0.8, 0.7)]]),
    "∼": (0.9, [_wave(0.1, 0.8, 0.45, 0.1)]),
    "→": (1.0, _arrow(0.05, 0.95, 0.45)),
    "←": (1.0, _arrow(0.05, 0.95, 0.45, left=True)),
    "↔": (1.1, _arrow(0.05, 1.05, 0.45, both=True)),
    "⇒": (1.0, [[(0.05, 0.6), (0.78, 0.6)], [(0.05, 0.3), (0.78, 0.3)],
                [(0.62, 0.88), (0.95, 0.45), (0.62, 0.02)]]),
    "⇐": (1.0, [[(0.22, 0.6), (0.95, 0.6)], [(0.22, 0.3), (0.95, 0.3)],
                [(0.38, 0.88), (0.05, 0.45), (0.38, 0.02)]]),
    "⇔": (1.2, [[(0.22, 0.6), (0.98, 0.6)], [(0.22, 0.3), (0.98, 0.3)],
                [(0.38, 0.88), (0.05, 0.45), (0.38, 0.02)], [(0.82, 0.88), (1.15, 0.45), (0.82, 0.02)]]),
    "↦": (1.0, [[(0.05, 0.15), (0.05, 0.75)]] + _arrow(0.05, 0.95, 0.45)),
    "∞": (1.1, [_lemniscate(0.55, 0.45, 0.5, 0.6)]),
    "∈": (0.8, [_MEMBER_ARC, [(0.15, 0.45), (0.72, 0.45)]]),
    "∉": (0.8, [_MEMBER_ARC, [(0.15, 0.45), (0.72, 0.45)], [(0.2, -0.1), (0.65, 1.0)]]),
    "∋": (0.8, [_mirror_x(_MEMBER_ARC, 0.87), [(0.15, 0.45), (0.72, 0.45)]]),
    "⊂": (0.8, [_MEMBER_ARC]),
    "⊃": (0.8, [_mirror_x(_MEMBER_ARC, 0.87)]),
    "⊆": (0.8, [_MEMBER_ARC, [(0.15, -0.2), (0.72, -0.2)]]),
    "⊇": (0.8, [_mirror_x(_MEMBER_ARC, 0.87), [(0.15, -0.2), (0.72, -0.2)]]),
    "∩": (0.8, [[(0.1, 0.0), (0.1, 0.55), (0.25, 0.85), (0.4, 0.92), (0.55, 0.85), (0.7, 0.55), (0.7, 0.0)]]),
    "∪": (0.8, [[(0.1, 0.92), (0.1, 0.37), (0.25, 0.07), (0.4, 0.0), (0.55, 0.07), (0.7, 0.37), (0.7, 0.92)]]),
    "∅": (0.8, [_circle(0.4, 0.45, 0.33), [(0.1, 0.0), (0.7, 0.95)]]),
    "∠": (0.9, [[(0.85, 0.0), (0.1, 0.0), (0.75, 0.8)]]),
    "△": (1.0, [[(0.05, 0.0), (0.5, 0.95), (0.95, 0.0), (0.05, 0.0)]]),
    "∥": (0.5, [[(0.15, -0.15), (0.15, 1.2)], [(0.35, -0.15), (0.35, 1.2)]]),
    "⊥": (0.8, [[(0.4, 0.0), (0.4, 0.9)], [(0.05, 0.0), (0.75, 0.0)]]),
    "|": (0.3, [[(0.15, -0.25), (0.15, 1.25)]]),
    "∣": (0.3, [[(0.15, -0.25), (0.15, 1.25)]]),
    "‖": (0.5, [[(0.15, -0.25), (0.15, 1.25)], [(0.35, -0.25), (0.35, 1.25)]]),
    "…": (1.0, [_dot(0.1, 0.03), _dot(0.48, 0.03), _dot(0.86, 0.03)]),
    "⋯": (1.0, [_dot(0.1, 0.45), _dot(0.48, 0.45), _dot(0.86, 0.45)]),
    "⋮": (0.3, [_dot(0.12, 0.05), _dot(0.12, 0.5), _dot(0.12, 0.95)]),
    "⋱": (0.9, [_dot(0.1, 0.95), _dot(0.43, 0.5), _dot(0.76, 0.05)]),
    "%": (1.1, [_circle(0.22, 0.98, 0.17), _circle(0.88, 0.2, 0.17), [(0.15, -0.05), (0.95, 1.2)]]),
    "∇": (0.9, [[(0.05, 1.0), (0.5, 0.0), (0.95, 1.0), (0.05, 1.0)]]),
    "∀": (0.9, [[(0.05, 1.0), (0.45, 0.0), (0.85, 1.0)], [(0.2, 0.45), (0.7, 0.45)]]),
    "∃": (0.7, [[(0.1, 1.0), (0.65, 1.0), (0.65, 0.0), (0.1, 0.0)], [(0.15, 0.5), (0.65, 0.5)]]),
    "∴": (0.8, [_dot(0.36, 0.8), _dot(0.08, 0.1), _dot(0.64, 0.1)]),
    "□": (1.0, [[(0.1, 0.0), (0.9, 0.0), (0.9, 1.0), (0.1, 1.0), (0.1, 0.0)]]),
    "∖": (0.7, [[(0.1, 1.1), (0.6, -0.1)]]),
    "\\": (0.7, [[(0.1, 1.1), (0.6, -0.1)]]),
    "√": (0.8, [[(0.0, 0.4), (0.15, 0.3), (0.35, 0.0), (0.6, 1.1), (0.8, 1.1)]]),
}

# Ký hiệu nên thử nhờ chữ/ký hiệu "gần giống" trong kho trước khi vẽ vector (đều là đồng dạng thị giác)
SYMBOL_ALIASES: dict[str, tuple[str, ...]] = {
    "ℝ": ("R",), "ℕ": ("N",), "ℤ": ("Z",), "ℚ": ("Q",), "ℂ": ("C",), "ℙ": ("P",), "ℍ": ("H",),
    "ℓ": ("l",), "ℏ": ("h",), "⋯": ("…",), "…": ("⋯",), "·": ("⋅", "∙"), "⋅": ("·", "∙"),
    "∙": ("·",), "′": ("'", "’"), "∣": ("|",), "|": ("∣",), "∗": ("*",), "*": ("∗",),
    "−": ("-",), "‐": ("-",), "⟨": ("<",), "⟩": (">",),
}


def small_glyph(sym: str) -> tuple[float, list[Polyline]] | None:
    """Ký hiệu cỡ chữ thường: (độ rộng, các đa tuyến) theo x-height, y hướng lên; None nếu chưa có."""
    return _SMALL.get(sym)


def has_small_glyph(sym: str) -> bool:
    return sym in _SMALL


def delimiter_polylines(ch: str, w: float, h: float) -> list[Polyline] | None:
    """Dấu ngoặc co giãn trong hộp w x h (góc trên-trái, y xuống). None nếu không hỗ trợ ``ch``."""
    if ch == "(":
        return [[(w * (1.0 - 0.8 * (1 - (2 * i / 12.0 - 1) ** 2)), h * i / 12.0) for i in range(13)]]
    if ch == ")":
        return [[(w * (0.2 + 0.8 * (1 - (2 * i / 12.0 - 1) ** 2)), h * i / 12.0) for i in range(13)]]
    if ch == "[":
        return [[(w * 0.9, 0.0), (w * 0.15, 0.0), (w * 0.15, h), (w * 0.9, h)]]
    if ch == "]":
        return [[(w * 0.1, 0.0), (w * 0.85, 0.0), (w * 0.85, h), (w * 0.1, h)]]
    if ch == "{":
        return [[(w * 0.95, 0.0), (w * 0.55, 0.04 * h), (w * 0.5, 0.12 * h), (w * 0.5, 0.42 * h),
                 (w * 0.3, 0.47 * h), (w * 0.05, 0.5 * h), (w * 0.3, 0.53 * h), (w * 0.5, 0.58 * h),
                 (w * 0.5, 0.88 * h), (w * 0.55, 0.96 * h), (w * 0.95, h)]]
    if ch == "}":
        return [[(w * 0.05, 0.0), (w * 0.45, 0.04 * h), (w * 0.5, 0.12 * h), (w * 0.5, 0.42 * h),
                 (w * 0.7, 0.47 * h), (w * 0.95, 0.5 * h), (w * 0.7, 0.53 * h), (w * 0.5, 0.58 * h),
                 (w * 0.5, 0.88 * h), (w * 0.45, 0.96 * h), (w * 0.05, h)]]
    if ch in ("|", "∣"):
        return [[(w * 0.5, 0.0), (w * 0.5, h)]]
    if ch == "‖":
        return [[(w * 0.3, 0.0), (w * 0.3, h)], [(w * 0.7, 0.0), (w * 0.7, h)]]
    if ch == "⟨":
        return [[(w * 0.9, 0.0), (w * 0.1, h * 0.5), (w * 0.9, h)]]
    if ch == "⟩":
        return [[(w * 0.1, 0.0), (w * 0.9, h * 0.5), (w * 0.1, h)]]
    if ch == "⌊":
        return [[(w * 0.15, 0.0), (w * 0.15, h), (w * 0.85, h)]]
    if ch == "⌋":
        return [[(w * 0.85, 0.0), (w * 0.85, h), (w * 0.15, h)]]
    if ch == "⌈":
        return [[(w * 0.85, 0.0), (w * 0.15, 0.0), (w * 0.15, h)]]
    if ch == "⌉":
        return [[(w * 0.15, 0.0), (w * 0.85, 0.0), (w * 0.85, h)]]
    if ch == "/":
        return [[(w * 0.9, 0.0), (w * 0.1, h)]]
    if ch == "\\":
        return [[(w * 0.1, 0.0), (w * 0.9, h)]]
    return None


def bigop_polylines(op: str, w: float, h: float) -> list[Polyline] | None:
    """Toán tử lớn (∑ ∏ ∫ ⋃ ⋂ ...) trong hộp w x h (góc trên-trái, y xuống)."""
    if op == "∑":
        return [[(w, 0.14 * h), (w, 0.0), (0.05 * w, 0.0), (0.62 * w, 0.5 * h), (0.05 * w, h),
                 (w, h), (w, 0.86 * h)]]
    if op == "∏":
        return [[(0.0, 0.0), (w, 0.0)], [(0.18 * w, 0.0), (0.18 * w, h)], [(0.82 * w, 0.0), (0.82 * w, h)]]
    if op == "∐":
        return [[(0.0, h), (w, h)], [(0.18 * w, 0.0), (0.18 * w, h)], [(0.82 * w, 0.0), (0.82 * w, h)]]
    if op in ("∫", "∮", "∬", "∭"):
        count = {"∫": 1, "∮": 1, "∬": 2, "∭": 3}[op]
        wi = w / (1.0 + 0.55 * (count - 1))
        out: list[Polyline] = []
        for k in range(count):
            ox = k * 0.55 * wi
            out.append([(ox + x * wi, y * h) for x, y in
                        [(0.0, 0.93), (0.1, 1.0), (0.25, 0.96), (0.38, 0.8), (0.46, 0.5), (0.54, 0.2),
                         (0.66, 0.04), (0.82, 0.0), (0.95, 0.05)]])
        if op == "∮":
            out.append(_circle(w * 0.5, h * 0.5, min(w, h) * 0.22))
        return out
    if op == "⋃":
        return [[(0.0, 0.0), (0.0, 0.55 * h), (0.15 * w, 0.85 * h), (0.5 * w, h), (0.85 * w, 0.85 * h),
                 (w, 0.55 * h), (w, 0.0)]]
    if op == "⋂":
        return [[(0.0, h), (0.0, 0.45 * h), (0.15 * w, 0.15 * h), (0.5 * w, 0.0), (0.85 * w, 0.15 * h),
                 (w, 0.45 * h), (w, h)]]
    if op == "⋁":
        return [[(0.0, 0.0), (0.5 * w, h), (w, 0.0)]]
    if op == "⋀":
        return [[(0.0, h), (0.5 * w, 0.0), (w, h)]]
    if op in ("⨁", "⨂"):
        r = min(w, h) / 2.0
        cx, cy = w / 2.0, h / 2.0
        inner = ([[(cx - r, cy), (cx + r, cy)], [(cx, cy - r), (cx, cy + r)]] if op == "⨁" else
                 [[(cx - r * 0.7, cy - r * 0.7), (cx + r * 0.7, cy + r * 0.7)],
                  [(cx - r * 0.7, cy + r * 0.7), (cx + r * 0.7, cy - r * 0.7)]])
        return [_circle(cx, cy, r)] + inner
    return None


def accent_polylines(kind: str, w: float, h: float) -> list[Polyline] | None:
    """Dấu trang trí trong hộp w x h (góc trên-trái, y xuống) đặt phía trên (hoặc dưới) phần tử gốc."""
    w = max(w, 1.0)
    mid = h / 2.0
    if kind in ("bar", "overline", "underline"):
        inset = 0.12 * w if kind == "bar" else 0.0
        return [[(inset, mid), (w - inset, mid)]]
    if kind in ("vec", "overrightarrow", "underrightarrow", "overleftarrow", "underleftarrow",
                "overleftrightarrow"):
        head = min(0.5 * w, h * 0.95)
        half = h * 0.42
        left = kind in ("overleftarrow", "underleftarrow")
        both = kind == "overleftrightarrow"
        shaft: list[Polyline] = [[(0.0, mid), (w, mid)]]
        if not left or both:
            shaft.append([(w - head, mid - half), (w, mid), (w - head, mid + half)])
        if left or both:
            shaft.append([(head, mid - half), (0.0, mid), (head, mid + half)])
        return shaft
    if kind in ("hat", "widehat"):
        return [[(0.12 * w, h), (0.5 * w, 0.1 * h), (0.88 * w, h)]]
    if kind in ("tilde", "widetilde"):
        return [[(w * i / 14.0, mid + 0.34 * h * math.sin(2 * math.pi * i / 14.0)) for i in range(15)]]
    if kind == "dot":
        return [_dot(0.5 * w - 0.3, mid, 0.6)]
    if kind == "ddot":
        return [_dot(0.34 * w - 0.3, mid, 0.6), _dot(0.66 * w - 0.3, mid, 0.6)]
    if kind == "dddot":
        return [_dot(0.25 * w - 0.3, mid, 0.6), _dot(0.5 * w - 0.3, mid, 0.6), _dot(0.75 * w - 0.3, mid, 0.6)]
    if kind == "acute":
        return [[(0.35 * w, h), (0.7 * w, 0.05 * h)]]
    if kind == "grave":
        return [[(0.65 * w, h), (0.3 * w, 0.05 * h)]]
    if kind == "check":
        return [[(0.12 * w, 0.1 * h), (0.5 * w, h), (0.88 * w, 0.1 * h)]]
    if kind == "breve":
        return [[(0.15 * w, 0.1 * h), (0.3 * w, 0.75 * h), (0.5 * w, h), (0.7 * w, 0.75 * h),
                 (0.85 * w, 0.1 * h)]]
    if kind == "mathring":
        return [_circle(0.5 * w, mid, 0.4 * h)]
    if kind == "overbrace":
        return [[(0.0, h), (0.03 * w, 0.55 * h), (0.46 * w, 0.55 * h), (0.5 * w, 0.05 * h),
                 (0.54 * w, 0.55 * h), (0.97 * w, 0.55 * h), (w, h)]]
    if kind == "underbrace":
        return [[(0.0, 0.0), (0.03 * w, 0.45 * h), (0.46 * w, 0.45 * h), (0.5 * w, 0.95 * h),
                 (0.54 * w, 0.45 * h), (0.97 * w, 0.45 * h), (w, 0.0)]]
    if kind == "strike":
        return [[(0.0, h), (w, 0.0)]]
    return None
