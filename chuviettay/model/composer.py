"""composer -- Định nghĩa các hợp đồng dữ liệu cho tuỳ chọn và kết quả kết xuất chữ viết tay.

Chứa các lớp hợp đồng dữ liệu dùng chung giữa Controller, Layout Engine, CLI và GUI:
- WriteMode: Chế độ kết xuất (semantic / fidelity)
- WriteOptions: Các tuỳ chọn khổ giấy, cỡ chữ, dãn dòng, nền trang và màu mực
- WriteResult: Thống kê số dòng, số nét, token thiếu và đường dẫn file kết xuất
- parse_color: Kiểm tra và chuẩn hoá mã màu hex #RRGGBB / #RRGGBBAA
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chuviettay.document.page_format import PageFormat


class WriteMode(str, Enum):
    """Chế độ kết xuất chữ viết tay."""
    SEMANTIC = "semantic"  # Tái dàn trang ngữ nghĩa tự do qua DocumentLayoutEngine
    FIDELITY = "fidelity"  # Khóa cố định bố cục, giữ nguyên ảnh & trang qua FixedLayoutEngine


COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def parse_color(c: str) -> str:
    """Kiểm tra và chuẩn hóa mã màu hex: #RRGGBB hoặc #RRGGBBAA."""
    s = c.strip()
    if not COLOR_RE.match(s):
        raise ValueError(
            f"Mã màu không hợp lệ: {c!r}. Chỉ chấp nhận định dạng hex #RRGGBB hoặc #RRGGBBAA (ví dụ: #1a237e)."
        )
    return s.lower()


@dataclass
class WriteOptions:
    """Tuỳ chọn khi 'viết' văn bản -- tương ứng các cờ dòng lệnh --scale/--line/...
    của lệnh `write`."""
    scale: float = 1.0            # nhân cỡ chữ
    line: float | None = None     # khoảng cách dòng (pt); None = lấy mặc định của kho mẫu
    width: float | None = None    # bề rộng dòng (pt); None = lấy mặc định của kho mẫu
    space: float = 1.0            # nhân khoảng cách giữa các từ
    jitter: float = 1.0           # độ "run tay" ngẫu nhiên (0 = tắt)
    wscale: float = 1.0           # nhân độ dày nét
    color: str | None = None      # đổi màu mực, ví dụ "#1a237e"; None = màu mặc định trong kho mẫu
    seed: int | None = None       # cố định số ngẫu nhiên (để tái tạo lại đúng kết quả)
    strict_case: bool = False     # không tự hạ chữ hoa đầu từ khi tìm mẫu thay thế

    # Cấu hình khổ giấy, lề và nền trang (áp dụng cho DocumentLayoutEngine)
    paper: str = "a4"             # a5, a4, a3, letter, legal, 16:9, 4:3, custom
    orientation: str = "portrait" # portrait (dọc) hoặc landscape (ngang)
    paper_width: float | None = None   # kích thước tùy chỉnh (pt), chỉ dùng khi paper="custom"
    paper_height: float | None = None  # kích thước tùy chỉnh (pt), chỉ dùng khi paper="custom"
    margin_left: float = 36.0     # lề trái (pt)
    margin_right: float = 36.0    # lề phải (pt)
    margin_top: float = 40.0      # lề trên (pt)
    margin_bottom: float = 40.0   # lề dưới (pt)
    background: str = "plain"     # plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music
    background_spacing: float | None = None  # khoảng cách dòng/ô kẻ (pt), ví dụ 14.17 pt = 5mm
    background_margin: float | None = None   # lề dọc cho ruled (pt)
    background_color: str = "#ffffffff"      # màu nền hex RGBA

    # Chế độ kết xuất: semantic (tái dàn trang) hoặc fidelity (khóa cố định bố cục)
    mode: str = "semantic"
    missing_grid: bool = True     # tự động tạo file _thieu.xopp khi thiếu mẫu (có thể tắt bằng --no-missing-grid)
    assemble_letters: bool = False  # tự động ghép từ các mẫu chữ cái khi thiếu từ nguyên khối

    # Các tuỳ chọn chất lượng ghép chữ cái & độ đậm nét
    letter_gap: float = 1.0       # hệ số nhân khoảng cách chữ cái
    target_xh: float = 7.94       # x-height mục tiêu chuẩn (pt)
    auto_xh: bool = False         # tự động chuẩn hóa x-height và bù trừ wscale theo tỉ lệ thực của note (17.8%)
    pen_clearance_factor: float = 0.8  # hệ số sàn khe hở tối thiểu theo độ dày bút (clearance >= factor * pen)

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ nghiệp vụ của các tùy chọn viết. Ném ValueError nếu sai."""
        from chuviettay.document.page_format import (
            PAPER_SIZES,
            VALID_BACKGROUND_STYLES,
            normalize_background_style,
        )

        m = self.mode.lower().strip()
        if m not in ("semantic", "fidelity"):
            raise ValueError(f"Chế độ xử lý không hợp lệ: {self.mode!r}. Chỉ chấp nhận: semantic, fidelity")

        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError(f"scale phải là số dương hữu hạn, nhận được: {self.scale}")
        if self.line is not None and (not math.isfinite(self.line) or self.line <= 0):
            raise ValueError(f"line phải là số dương hữu hạn, nhận được: {self.line}")
        if self.width is not None and (not math.isfinite(self.width) or self.width <= 0):
            raise ValueError(f"width phải là số dương hữu hạn, nhận được: {self.width}")
        if not math.isfinite(self.space) or self.space < 0:
            raise ValueError(f"space phải là số không âm hữu hạn, nhận được: {self.space}")
        if not math.isfinite(self.jitter) or self.jitter < 0:
            raise ValueError(f"jitter phải là số không âm hữu hạn, nhận được: {self.jitter}")
        if not math.isfinite(self.wscale) or self.wscale <= 0:
            raise ValueError(f"wscale phải là số dương hữu hạn, nhận được: {self.wscale}")
        if self.color is not None:
            self.color = parse_color(self.color)

        # Kiểm tra khổ giấy và hướng giấy
        p = self.paper.lower().strip()
        if p != "custom" and p not in PAPER_SIZES:
            raise ValueError(f"Khổ giấy không hợp lệ: {self.paper!r}. Chỉ chấp nhận: {', '.join(sorted(PAPER_SIZES.keys()))}, custom")

        if p == "custom":
            if self.paper_width is None or not math.isfinite(self.paper_width) or self.paper_width <= 0:
                raise ValueError("paper_width phải là số dương hữu hạn khi chọn khổ giấy custom")
            if self.paper_height is None or not math.isfinite(self.paper_height) or self.paper_height <= 0:
                raise ValueError("paper_height phải là số dương hữu hạn khi chọn khổ giấy custom")

        ori = self.orientation.lower().strip()
        if ori not in ("portrait", "landscape"):
            raise ValueError(f"Hướng giấy không hợp lệ: {self.orientation!r}. Chỉ chấp nhận: portrait, landscape")

        # Kiểm tra lề trang
        for m_name, m_val in (
            ("margin_left", self.margin_left),
            ("margin_right", self.margin_right),
            ("margin_top", self.margin_top),
            ("margin_bottom", self.margin_bottom),
        ):
            if not math.isfinite(m_val) or m_val < 0:
                raise ValueError(f"{m_name} phải là số không âm hữu hạn, nhận được: {m_val}")

        # Kiểm tra nền trang
        bg_style = normalize_background_style(self.background)
        if bg_style not in VALID_BACKGROUND_STYLES:
            raise ValueError(f"Kiểu nền không hợp lệ: {self.background!r}. Chỉ chấp nhận: {', '.join(sorted(VALID_BACKGROUND_STYLES))}")
        if self.background_spacing is not None and (not math.isfinite(self.background_spacing) or self.background_spacing <= 0):
            raise ValueError(f"background_spacing phải là số dương hữu hạn, nhận được: {self.background_spacing}")
        if self.background_margin is not None and (not math.isfinite(self.background_margin) or self.background_margin < 0):
            raise ValueError(f"background_margin phải là số không âm hữu hạn, nhận được: {self.background_margin}")
        if self.background_color is not None:
            self.background_color = parse_color(self.background_color)

        # Kiểm tra lề không vượt quá kích thước giấy
        pf = self.resolve_page_format()
        if self.margin_left + self.margin_right >= pf.width:
            raise ValueError(
                f"Tổng lề trái ({self.margin_left} pt) và lề phải ({self.margin_right} pt) "
                f"phải nhỏ hơn bề ngang trang ({pf.width} pt)."
            )
        if self.margin_top + self.margin_bottom >= pf.height:
            raise ValueError(
                f"Tổng lề trên ({self.margin_top} pt) và lề dưới ({self.margin_bottom} pt) "
                f"phải nhỏ hơn bề dọc trang ({pf.height} pt)."
            )

    def resolve_page_format(self) -> PageFormat:
        """Phân giải cấu hình WriteOptions thành đối tượng PageFormat hoàn chỉnh."""
        from chuviettay.document.page_format import (
            PAPER_SIZES,
            PageBackground,
            PageFormat,
            PaperSize,
            normalize_background_style,
        )

        p = self.paper.lower().strip()
        if p == "custom":
            w = self.paper_width if self.paper_width is not None else 595.28
            h = self.paper_height if self.paper_height is not None else 841.89
            paper_size = PaperSize("Custom", w, h)
        else:
            paper_size = PAPER_SIZES.get(p, PAPER_SIZES["a4"])

        bg = PageBackground(
            style=normalize_background_style(self.background),
            spacing=self.background_spacing,
            margin=self.background_margin,
            color=self.background_color,
        )

        return PageFormat(
            paper=paper_size,
            orientation=self.orientation.lower().strip(),
            margin_left=self.margin_left,
            margin_right=self.margin_right,
            margin_top=self.margin_top,
            margin_bottom=self.margin_bottom,
            background=bg,
        )


@dataclass
class WriteResult:
    """Kết quả một lần 'viết' -- CLI/GUI tự quyết định hiển thị thế nào từ dữ liệu này,
    không phải parse chuỗi in ra màn hình."""
    out_path: str
    n_lines: int
    n_strokes: int
    n_tokens: int
    n_missing_tokens: int
    missing: dict[str, int] = field(default_factory=dict)   # token thiếu mẫu -> số lần gặp
    missing_grid_path: str | None = None   # file lưới ô đã tạo để dạy các từ thiếu (None nếu không thiếu gì)
    missing_symbols: dict[str, int] = field(default_factory=dict)  # ký hiệu toán học thiếu mẫu -> số lần gặp
    missing_letters: list[tuple[str, int]] = field(default_factory=list)  # (chữ cái/dấu, số từ mở khoá)
    assembled_words: list[str] = field(default_factory=list)  # các từ được ghép thành công từ chữ cái
    n_tables: int = 0                      # tổng số bảng biểu đã dàn trang
    n_math_blocks: int = 0                 # tổng số khối công thức toán học đã dàn trang
    n_pages: int = 1                       # tổng số trang của tài liệu
    n_images: int = 0                      # tổng số hình ảnh giữ nguyên ở nền

    def missing_sorted(self) -> list[tuple[str, int]]:
        """[(token, số lần gặp), ...] gặp nhiều nhất xếp trước, bằng nhau thì theo chữ
        cái -- một cách sắp xếp duy nhất dùng chung cho file lưới ô, CLI và GUI (bản
        gốc viết lại đúng biểu thức sắp xếp này ở 3 chỗ)."""
        return sorted(self.missing.items(), key=lambda kv: (-kv[1], kv[0]))

    def missing_symbols_sorted(self) -> list[tuple[str, int]]:
        """[(ký hiệu, số lần gặp), ...] gặp nhiều nhất xếp trước, bằng nhau thì theo chữ cái."""
        return sorted(self.missing_symbols.items(), key=lambda kv: (-kv[1], kv[0]))
