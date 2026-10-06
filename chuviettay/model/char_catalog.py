"""Danh mục các bộ ký tự mẫu chuẩn (char catalog).

Đóng vai trò Single Source of Truth cho:
- Sinh lưới tập viết (.xopp) qua CLI và Controller
- Hàng đợi dạy chữ trên Desktop GUI và Web Client
- Quản lý các nhóm ký tự: Cơ bản, Toán học & Hy Lạp, Mở rộng, Đầy đủ.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharCatalogGroup:
    id: str
    name: str
    description: str
    chars: tuple[str, ...]


# 1. Bộ chữ cái tiếng Việt cơ bản (thường + hoa)
VIETNAMESE_LOWERCASE = (
    "a", "ă", "â", "b", "c", "d", "đ", "e", "ê", "g", "h", "i", "k", "l", "m",
    "n", "o", "ô", "ơ", "p", "q", "r", "s", "t", "u", "ư", "v", "x", "y",
    "f", "j", "w", "z",
)

VIETNAMESE_UPPERCASE = (
    "A", "Ă", "Â", "B", "C", "D", "Đ", "E", "Ê", "G", "H", "I", "K", "L", "M",
    "N", "O", "Ô", "Ơ", "P", "Q", "R", "S", "T", "U", "Ư", "V", "X", "Y",
    "F", "J", "W", "Z",
)

# Chữ số
DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")

# Dấu câu cơ bản
PUNCTUATION = (
    ".", ",", "!", "?", ":", ";", "-", "—", "–",
    "(", ")", "[", "]", "{", "}", "\"", "'", "“", "”", "‘", "’", "/", "…",
)

# Dấu thanh rời chuẩn hw3
TONE_MARKS = ("dấu sắc", "dấu huyền", "dấu hỏi", "dấu ngã", "dấu nặng")

# Digraphs tiếng Việt phổ biến (tùy chọn)
DIGRAPHS = ("ng", "nh", "ch", "tr", "ph", "th", "kh", "gi", "qu", "ươ", "ưa", "uy", "ay", "oa")

# 2. Bộ toán học & Hy Lạp
GREEK_LOWERCASE = (
    "α", "β", "γ", "δ", "ε", "θ", "λ", "μ", "π", "ρ", "σ", "τ", "φ", "ω",
)
GREEK_UPPERCASE = (
    "Γ", "Δ", "Θ", "Λ", "Π", "Σ", "Φ", "Ψ", "Ω",
)
MATH_OPERATORS = (
    "+", "-", "=", "<", ">", "±", "×", "÷", "·", "≤", "≥", "≠", "≈", "≡",
    "∈", "∉", "⊂", "⊃", "⊆", "⊇", "∪", "∩", "∅", "∞", "√", "∑", "∏", "∫", "∂", "∇",
    "→", "←", "↔", "⇒", "⇐", "⇔",
)

# 3. Ký tự mở rộng (tiền tệ, biểu tượng thông dụng)
EXTENDED_SYMBOLS = (
    "$", "€", "£", "¥", "₫", "%", "&", "@", "#", "*", "^", "~", "`", "|", "\\", "§", "©", "®", "°",
)


# Tổng hợp các bộ
CO_BAN_CHARS: tuple[str, ...] = (
    VIETNAMESE_LOWERCASE
    + VIETNAMESE_UPPERCASE
    + DIGITS
    + PUNCTUATION
    + TONE_MARKS
)

TOAN_HY_LAP_CHARS: tuple[str, ...] = (
    GREEK_LOWERCASE
    + GREEK_UPPERCASE
    + MATH_OPERATORS
)

MO_RONG_CHARS: tuple[str, ...] = (
    EXTENDED_SYMBOLS
)

DAY_DU_CHARS: tuple[str, ...] = (
    CO_BAN_CHARS
    + TOAN_HY_LAP_CHARS
    + MO_RONG_CHARS
)


CATALOG_GROUPS: dict[str, CharCatalogGroup] = {
    "co_ban": CharCatalogGroup(
        id="co_ban",
        name="Cơ bản",
        description="Chữ cái tiếng Việt, chữ số, dấu câu và 5 dấu thanh rời",
        chars=CO_BAN_CHARS,
    ),
    "chu_hoa": CharCatalogGroup(
        id="chu_hoa",
        name="Chữ cái in hoa",
        description="33 chữ cái in hoa tiếng Việt & mượn",
        chars=VIETNAMESE_UPPERCASE,
    ),
    "chu_thuong": CharCatalogGroup(
        id="chu_thuong",
        name="Chữ cái viết thường",
        description="33 chữ cái viết thường tiếng Việt & mượn",
        chars=VIETNAMESE_LOWERCASE,
    ),
    "chu_so": CharCatalogGroup(
        id="chu_so",
        name="Chữ số",
        description="Chữ số từ 0 đến 9",
        chars=DIGITS,
    ),
    "dau_cau": CharCatalogGroup(
        id="dau_cau",
        name="Dấu câu",
        description="Các dấu câu cơ bản và mở rộng",
        chars=PUNCTUATION,
    ),
    "dau_thanh": CharCatalogGroup(
        id="dau_thanh",
        name="Dấu thanh rời",
        description="5 dấu thanh rời tiếng Việt chuẩn hw3",
        chars=TONE_MARKS,
    ),
    "ky_hieu_toan": CharCatalogGroup(
        id="ky_hieu_toan",
        name="Ký hiệu toán & biểu tượng",
        description="Các toán tử số học, so sánh và ký hiệu mở rộng",
        chars=MATH_OPERATORS + EXTENDED_SYMBOLS,
    ),
    "toan_hy_lap": CharCatalogGroup(
        id="toan_hy_lap",
        name="Toán học & Hy Lạp",
        description="Ký tự Hy Lạp hoa/thường và các ký hiệu toán học phổ biến",
        chars=TOAN_HY_LAP_CHARS,
    ),
    "mo_rong": CharCatalogGroup(
        id="mo_rong",
        name="Mở rộng",
        description="Ký hiệu tiền tệ, biểu tượng đặc biệt và dấu phụ",
        chars=MO_RONG_CHARS,
    ),
    "day_du": CharCatalogGroup(
        id="day_du",
        name="Đầy đủ",
        description="Hợp nhất tất cả các bộ ký tự (cơ bản + toán học + mở rộng)",
        chars=DAY_DU_CHARS,
    ),
}


def get_catalog_group(group_id: str = "co_ban") -> CharCatalogGroup:
    """Lấy thông tin nhóm ký tự theo id (mặc định 'co_ban')."""
    if group_id not in CATALOG_GROUPS:
        valid = ", ".join(CATALOG_GROUPS.keys())
        raise ValueError(f"Nhóm ký tự {group_id!r} không tồn tại. Các nhóm hợp lệ: {valid}")
    return CATALOG_GROUPS[group_id]
