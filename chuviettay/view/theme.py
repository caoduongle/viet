"""Quản lý chủ đề giao diện Sáng / Tối cho Desktop Tkinter/ttk.

Cung cấp bảng màu chuẩn (THEME_PALETTES) và hàm apply_theme() để cấu hình ttk.Style
cũng như cập nhật màu sắc của các widget Tkinter truyền thống.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from chuviettay.paths import load_user_config, save_user_config

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None  # type: ignore
    ttk = None  # type: ignore

_log = logging.getLogger(__name__)

ThemeMode = Literal["light", "dark"]

THEME_PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "bg_main": "#f0f2f5",
        "bg_panel": "#ffffff",
        "fg_main": "#1e293b",
        "fg_muted": "#64748b",
        "border": "#cbd5e1",
        "canvas_bg": "#ffffff",
        "canvas_baseline": "#808080",
        "canvas_xheight": "#aaaaaa",
        "entry_bg": "#ffffff",
        "entry_fg": "#1e293b",
        "listbox_bg": "#ffffff",
        "listbox_fg": "#1e293b",
        "listbox_sel_bg": "#2563eb",
        "listbox_sel_fg": "#ffffff",
    },
    "dark": {
        "bg_main": "#0f172a",
        "bg_panel": "#1e293b",
        "fg_main": "#f8fafc",
        "fg_muted": "#94a3b8",
        "border": "#334155",
        "canvas_bg": "#1e293b",
        "canvas_baseline": "#64748b",
        "canvas_xheight": "#475569",
        "entry_bg": "#0f172a",
        "entry_fg": "#f8fafc",
        "listbox_bg": "#0f172a",
        "listbox_fg": "#f8fafc",
        "listbox_sel_bg": "#3b82f6",
        "listbox_sel_fg": "#ffffff",
    },
}


def get_current_theme() -> ThemeMode:
    """Đọc theme hiện tại từ cấu hình user_config.json (mặc định 'light')."""
    cfg = load_user_config()
    theme = cfg.get("theme", "light")
    return "dark" if theme == "dark" else "light"


def save_current_theme(theme: ThemeMode) -> None:
    """Lưu theme vào user_config.json."""
    cfg = load_user_config()
    cfg["theme"] = theme
    save_user_config(cfg)


def apply_theme(root: Any, theme: ThemeMode) -> dict[str, str]:
    """Cấu hình ttk.Style và màu nền của root theo theme chỉ định.
    Trả về palette tương ứng để các widget con (như WordCanvas) sử dụng."""
    palette = THEME_PALETTES.get(theme, THEME_PALETTES["light"])

    if root is None or ttk is None:
        return palette

    try:
        root.configure(bg=palette["bg_main"])
    except Exception:
        pass

    style = ttk.Style(root)
    # Cố gắng dùng theme 'clam' làm nền tảng nếu có để hỗ trợ đổi màu tốt hơn
    available = style.theme_names()
    if "clam" in available and style.theme_use() != "clam":
        try:
            style.theme_use("clam")
        except Exception:
            pass

    # Cấu hình các style ttk cơ bản
    style.configure(".", background=palette["bg_main"], foreground=palette["fg_main"])
    style.configure("TFrame", background=palette["bg_main"])
    style.configure("TLabel", background=palette["bg_main"], foreground=palette["fg_main"])
    style.configure("TLabelframe", background=palette["bg_main"], foreground=palette["fg_main"])
    style.configure("TLabelframe.Label", background=palette["bg_main"], foreground=palette["fg_main"])

    style.configure("TButton", background=palette["bg_panel"], foreground=palette["fg_main"], bordercolor=palette["border"])
    style.map(
        "TButton",
        background=[("active", palette["border"]), ("pressed", palette["canvas_baseline"])],
        foreground=[("disabled", palette["fg_muted"])],
    )

    style.configure("TEntry", fieldbackground=palette["entry_bg"], foreground=palette["entry_fg"])
    style.configure("TNotebook", background=palette["bg_main"], borderwidth=0)
    style.configure("TNotebook.Tab", background=palette["bg_panel"], foreground=palette["fg_main"], padding=[10, 4])
    style.map(
        "TNotebook.Tab",
        background=[("selected", palette["border"]), ("active", palette["canvas_baseline"])],
        foreground=[("selected", palette["fg_main"])],
    )

    return palette
