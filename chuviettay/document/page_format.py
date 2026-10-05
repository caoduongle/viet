"""Quản lý quy chuẩn khổ giấy, hướng giấy, lề trang và nền giấy chuẩn cho tài liệu Xournal++ (.xopp)."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# 1 inch = 72 PostScript points, 1 mm = 72 / 25.4 pt
PT_PER_MM = 72.0 / 25.4
PT_PER_CM = PT_PER_MM * 10.0
PT_PER_INCH = 72.0

COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def _fmt(v: float) -> str:
    s = f"{v:.3f}"
    return s.rstrip("0").rstrip(".") or "0"


# Ánh xạ từ tên kiểu nền nội bộ/alias sang tên thuộc tính style chuẩn của Xournal++ XML
# Tham chiếu: PageTypeHandler::getPageTypeFormatForString trong mã nguồn Xournal++ (commit 9882ffaaf2)
XOPP_STYLE_NAMES: dict[str, str] = {
    "plain": "plain",
    "lined": "lined",
    "ruled": "ruled",
    "graph": "graph",
    "dotted": "dotted",
    "iso_graph": "isograph",
    "isograph": "isograph",
    "iso_dotted": "isodotted",
    "isodotted": "isodotted",
    "music": "staves",
    "staves": "staves",
}

# Ánh xạ chuẩn hoá mọi biểu diễn về tên nội bộ chuẩn
STYLE_ALIASES: dict[str, str] = {
    "isograph": "iso_graph",
    "isodotted": "iso_dotted",
    "staves": "music",
}

VALID_BACKGROUND_STYLES = {
    "plain",
    "lined",
    "ruled",
    "graph",
    "dotted",
    "iso_graph",
    "iso_dotted",
    "music",
    "isograph",
    "isodotted",
    "staves",
}


def normalize_background_style(style: str) -> str:
    """Chuẩn hoá chuỗi kiểu nền về tên nội bộ chuẩn của chuviettay.

    Chấp nhận cả tên nội bộ ('iso_graph', 'iso_dotted', 'music') lẫn tên chuẩn Xournal++ XML ('isograph', 'isodotted', 'staves').
    """
    s = (style or "").strip().lower()
    return STYLE_ALIASES.get(s, s)


def parse_length(val: str | float | int, default_unit: str = "pt") -> float:
    """Chuyển đổi kích thước dạng chuỗi (kèm đơn vị mm, cm, in, pt) hoặc số sang đơn vị điểm PostScript (pt).

    Ném ValueError nếu giá trị âm, vô hạn hoặc chuỗi không hợp lệ.
    """
    if isinstance(val, (int, float)):
        if not math.isfinite(val) or val < 0:
            raise ValueError(f"Kích thước phải là số dương hữu hạn, nhận được: {val}")
        return float(val)

    s = str(val).strip().lower()
    if not s:
        raise ValueError("Kích thước không được để trống")

    # Tách số và đơn vị
    match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*([a-z\"']*)$", s)
    if not match:
        raise ValueError(f"Chuỗi kích thước không hợp lệ: {val!r}")

    num_str, unit = match.groups()
    num = float(num_str)
    if not math.isfinite(num) or num < 0:
        raise ValueError(f"Kích thước phải là số dương hữu hạn, nhận được: {val!r}")

    unit = unit or default_unit.lower()
    if unit in ("pt", "point", "points"):
        return round(num, 2)
    elif unit in ("mm", "milimeter", "millimeter"):
        return round(num * PT_PER_MM, 2)
    elif unit in ("cm", "centimeter"):
        return round(num * PT_PER_CM, 2)
    elif unit in ("in", "inch", '"'):
        return round(num * PT_PER_INCH, 2)
    else:
        raise ValueError(f"Đơn vị đo không được hỗ trợ: {unit!r}. Chỉ chấp nhận: pt, mm, cm, in.")


@dataclass(frozen=True)
class PaperSize:
    """Kích thước khổ giấy chuẩn tính theo đơn vị PostScript points (1 pt = 1/72 inch)."""
    name: str
    width: float   # bề ngang (pt)
    height: float  # bề dọc (pt)


# Thư viện khổ giấy thông dụng (chuẩn quốc tế ISO 216 và Bắc Mỹ ANSI)
PAPER_SIZES: dict[str, PaperSize] = {
    "a5": PaperSize("A5", 419.53, 595.28),
    "a4": PaperSize("A4", 595.28, 841.89),
    "a3": PaperSize("A3", 841.89, 1190.55),
    "letter": PaperSize("US Letter", 612.00, 792.00),
    "legal": PaperSize("US Legal", 612.00, 1008.00),
    "16:9": PaperSize("16:9", 841.89, 473.56),
    "4:3": PaperSize("4:3", 792.00, 594.00),
}


@dataclass(frozen=True)
class PageBackground:
    """Quy cách nền trang cho Xournal++ (kiểu nền, khoảng cách ô kẻ, lề và màu sắc)."""
    style: str = "plain"               # plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music
    spacing: float | None = None       # khoảng cách dòng kẻ / ô li (pt), ví dụ 14.17 pt = 5 mm
    margin: float | None = None        # vị trí đường lề đứng (pt, áp dụng cho ruled)
    color: str = "#ffffffff"           # mã màu hex RGBA (mặc định trắng đục)

    def to_xml(self) -> str:
        """Sinh chuỗi XML thẻ <background> cho trang trong file .xopp."""
        style_key = (self.style or "").strip().lower()
        if style_key not in VALID_BACKGROUND_STYLES:
            xml_style = "plain"
        else:
            xml_style = XOPP_STYLE_NAMES.get(style_key, "plain")

        color = self.color.strip()
        if not COLOR_RE.match(color):
            color = "#ffffffff"
        else:
            color = color.lower()

        cfg_parts = []
        if self.spacing is not None and self.spacing > 0:
            cfg_parts.append(f"r1={_fmt(self.spacing)}")
        if self.margin is not None and self.margin > 0:
            cfg_parts.append(f"m1={_fmt(self.margin)}")

        cfg_attr = f' config="{",".join(cfg_parts)}"' if cfg_parts else ""
        return f'<background type="solid" color="{color}" style="{xml_style}"{cfg_attr}/>'


@dataclass(frozen=True)
class PageFormat:
    """Cấu hình định dạng trang hoàn chỉnh gồm khổ giấy, chiều giấy, lề và nền."""
    paper: PaperSize
    orientation: str = "portrait"      # portrait (dọc) hoặc landscape (ngang)
    margin_left: float = 36.0          # lề trái (pt)
    margin_right: float = 36.0         # lề phải (pt)
    margin_top: float = 40.0           # lề trên (pt)
    margin_bottom: float = 40.0        # lề dưới (pt)
    background: PageBackground = field(default_factory=PageBackground)

    @property
    def width(self) -> float:
        w, h = self.paper.width, self.paper.height
        if self.orientation.lower() == "landscape":
            return max(w, h)
        return min(w, h)

    @property
    def height(self) -> float:
        w, h = self.paper.width, self.paper.height
        if self.orientation.lower() == "landscape":
            return min(w, h)
        return max(w, h)

    @property
    def usable_width(self) -> float:
        return max(20.0, self.width - self.margin_left - self.margin_right)

    @property
    def usable_height(self) -> float:
        return max(20.0, self.height - self.margin_top - self.margin_bottom)

    @property
    def content_top(self) -> float:
        return self.margin_top

    @property
    def max_page_y(self) -> float:
        return self.height - self.margin_bottom
