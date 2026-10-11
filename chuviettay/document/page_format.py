"""Quản lý quy chuẩn khổ giấy, hướng giấy, lề trang và nền giấy chuẩn cho tài liệu Xournal++ (.xopp)."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

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


def parse_length(val: str | float | int, default_unit: str = "pt", allow_negative: bool = False) -> float:
    """Chuyển đổi kích thước dạng chuỗi (kèm đơn vị mm, cm, in, pt) hoặc số sang đơn vị điểm PostScript (pt).

    Ném ValueError nếu giá trị vô hạn, chuỗi không hợp lệ, hoặc âm khi allow_negative=False.
    """
    if isinstance(val, (int, float)):
        if not math.isfinite(val) or (not allow_negative and val < 0):
            raise ValueError(f"Kích thước phải là số {'hữu hạn' if allow_negative else 'dương hữu hạn'}, nhận được: {val}")
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
    if not math.isfinite(num) or (not allow_negative and num < 0):
        raise ValueError(f"Kích thước phải là số {'hữu hạn' if allow_negative else 'dương hữu hạn'}, nhận được: {val!r}")

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
    style: str = "plain"               # plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music/staves
    spacing: float | None = None       # r1: khoảng cách dòng kẻ / ô li (pt), ví dụ 14.17 pt = 5 mm
    margin: float | None = None        # m1: vị trí đường lề đứng (pt, số âm = lề phải)
    color: str = "#ffffffff"           # mã màu hex RGBA (mặc định trắng đục)
    line_width: float | None = None    # lw: độ dày nét dòng kẻ (pt, mặc định 0.5)
    primary_color: str | None = None   # f1: mã hex màu nét chính
    secondary_color: str | None = None # f2: mã hex màu nét phụ/lề
    attachment_primary_color: str | None = None   # af1
    attachment_secondary_color: str | None = None # af2
    round_margin: bool | None = None   # rm: 1 = làm tròn lề theo ô lưới
    bold_line_interval: int | None = None  # bli: chu kỳ đường kẻ đậm (ví dụ 5)
    bold_line_width: float | None = None   # blw: độ dày đường kẻ đậm (mặc định 1.5)

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
        if self.margin is not None and self.margin != 0:
            cfg_parts.append(f"m1={_fmt(self.margin)}")
        if self.line_width is not None and self.line_width > 0:
            cfg_parts.append(f"lw={_fmt(self.line_width)}")
        if self.primary_color is not None:
            cfg_parts.append(f"f1={self.primary_color.lstrip('#')}")
        if self.secondary_color is not None:
            cfg_parts.append(f"f2={self.secondary_color.lstrip('#')}")
        if self.attachment_primary_color is not None:
            cfg_parts.append(f"af1={self.attachment_primary_color.lstrip('#')}")
        if self.attachment_secondary_color is not None:
            cfg_parts.append(f"af2={self.attachment_secondary_color.lstrip('#')}")
        if self.round_margin is not None:
            cfg_parts.append(f"rm={'1' if self.round_margin else '0'}")
        if self.bold_line_interval is not None and self.bold_line_interval > 0:
            cfg_parts.append(f"bli={self.bold_line_interval}")
        if self.bold_line_width is not None and self.bold_line_width > 0:
            cfg_parts.append(f"blw={_fmt(self.bold_line_width)}")

        cfg_attr = f' config="{",".join(cfg_parts)}"' if cfg_parts else ""
        return f'<background type="solid" color="{color}" style="{xml_style}"{cfg_attr}/>'


# Các mẫu nền chuẩn theo pagetemplates.ini.in của Xournal++
BACKGROUND_PRESETS: dict[str, PageBackground] = {
    "plain": PageBackground(style="plain"),
    "ruled": PageBackground(style="ruled", spacing=24.0),
    "lined": PageBackground(style="lined", spacing=24.0, margin=72.0),
    "lined_right": PageBackground(style="lined", spacing=24.0, margin=-72.0),
    "lined_narrow": PageBackground(style="lined", spacing=18.0, margin=72.0),
    "lined_college": PageBackground(style="lined", spacing=20.0, margin=72.0),
    "lined_wide": PageBackground(style="lined", spacing=24.0, margin=72.0),
    "graph": PageBackground(style="graph", spacing=14.17),
    "graph_5mm": PageBackground(style="graph", spacing=14.17),
    "graph_grid": PageBackground(style="graph", spacing=14.17, bold_line_interval=5, bold_line_width=1.5),
    "graph_border": PageBackground(style="graph", spacing=14.17, margin=40.0, round_margin=True),
    "graph_border_bold_5": PageBackground(style="graph", spacing=14.17, margin=20.0, round_margin=True, bold_line_interval=5, bold_line_width=1.5),
    "dotted": PageBackground(style="dotted", spacing=14.17),
    "iso_graph": PageBackground(style="iso_graph", spacing=14.17),
    "iso_dotted": PageBackground(style="iso_dotted", spacing=14.17),
    "staves": PageBackground(style="staves"),
}

PRESET_METADATA: dict[str, dict[str, str]] = {
    "plain": {"name_en": "Plain", "name_vi": "Giấy trơn"},
    "ruled": {"name_en": "Ruled", "name_vi": "Kẻ ngang"},
    "lined": {"name_en": "Ruled with vertical line", "name_vi": "Kẻ ngang có lề trái"},
    "lined_right": {"name_en": "Ruled with vertical line on the right", "name_vi": "Kẻ ngang có lề phải"},
    "lined_narrow": {"name_en": "Lined narrow", "name_vi": "Kẻ ngang hẹp"},
    "lined_college": {"name_en": "Lined college", "name_vi": "Kẻ ngang vừa"},
    "lined_wide": {"name_en": "Lined wide", "name_vi": "Kẻ ngang rộng"},
    "graph": {"name_en": "Graph", "name_vi": "Ô ly caro"},
    "graph_5mm": {"name_en": "Graph 5mm", "name_vi": "Ô ly 5mm"},
    "graph_grid": {"name_en": "Graph grid with bold", "name_vi": "Ô ly có nét đậm"},
    "graph_border": {"name_en": "Graph with border", "name_vi": "Ô ly có viền lề"},
    "graph_border_bold_5": {"name_en": "Graph with border bold every 5th", "name_vi": "Ô ly có viền lề đậm chu kỳ 5"},
    "dotted": {"name_en": "Dotted", "name_vi": "Chấm điểm (Dot grid)"},
    "iso_graph": {"name_en": "Isometric Graph", "name_vi": "Lưới đẳng cự (Isometric)"},
    "iso_dotted": {"name_en": "Isometric Dotted", "name_vi": "Chấm đẳng cự"},
    "staves": {"name_en": "Music Staves", "name_vi": "Khuông nhạc"},
}


def get_page_catalog() -> dict[str, Any]:
    """Trả về danh mục đồng bộ khổ giấy, mẫu nền và tone màu chuẩn của Xournal++."""
    return {
        "sizes": {
            k: {
                "id": k,
                "name": v.name,
                "width": v.width,
                "height": v.height,
            }
            for k, v in PAPER_SIZES.items()
        },
        "presets": {
            k: {
                "id": k,
                "name": PRESET_METADATA.get(k, {}).get("name_vi", k),
                "name_en": PRESET_METADATA.get(k, {}).get("name_en", k),
                "name_vi": PRESET_METADATA.get(k, {}).get("name_vi", k),
                "style": v.style,
                "spacing": v.spacing,
                "margin": v.margin,
                "line_width": v.line_width,
                "bold_line_interval": v.bold_line_interval,
                "bold_line_width": v.bold_line_width,
                "round_margin": v.round_margin,
            }
            for k, v in BACKGROUND_PRESETS.items()
        },
        "tones": [
            {"id": "white", "name": "Trắng", "color": "#ffffffff", "dark": False},
            {"id": "ivory", "name": "Vàng ngà", "color": "#ffffc8ff", "dark": False},
            {"id": "blue", "name": "Xanh nhạt", "color": "#e8f4f8ff", "dark": False},
            {"id": "dark", "name": "Tối", "color": "#1e1e1eff", "dark": True},
        ],
    }


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
