"""Kiểm thử module quản lý theme Desktop Tkinter."""
from __future__ import annotations

import os

from chuviettay.paths import load_user_config, save_user_config, user_config_path
from chuviettay.view.theme import THEME_PALETTES, get_current_theme, save_current_theme


def test_theme_palettes_structure():
    assert "light" in THEME_PALETTES
    assert "dark" in THEME_PALETTES

    for theme_name in ("light", "dark"):
        palette = THEME_PALETTES[theme_name]
        assert "bg_main" in palette
        assert "bg_panel" in palette
        assert "fg_main" in palette
        assert "canvas_bg" in palette
        assert "canvas_baseline" in palette
        assert "canvas_xheight" in palette


def test_theme_save_and_load(tmp_path, monkeypatch):
    test_cfg_path = str(tmp_path / "user_config.json")
    monkeypatch.setattr("chuviettay.paths.user_config_path", lambda: test_cfg_path)

    # Mặc định chưa có file -> light
    assert get_current_theme() == "light"

    # Lưu dark -> đọc ra dark
    save_current_theme("dark")
    assert get_current_theme() == "dark"
    assert os.path.exists(test_cfg_path)

    # Đọc raw config kiểm tra
    cfg = load_user_config()
    assert cfg.get("theme") == "dark"

    # Đổi lại light
    save_current_theme("light")
    assert get_current_theme() == "light"
