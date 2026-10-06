"""Kiểm thử danh mục ký tự chuẩn (char_catalog), phân loại ký tự (classify_char)
và chọn ký tự mốc calib (pick_calib_char)."""
from __future__ import annotations

import pytest


def test_char_catalog_module_and_groups():
    """Kiểm tra module chuviettay.model.char_catalog và các bộ ký tự chuẩn."""
    from chuviettay.model import char_catalog

    assert hasattr(char_catalog, "CATALOG_GROUPS"), "Thiếu CATALOG_GROUPS"
    groups = char_catalog.CATALOG_GROUPS
    assert "co_ban" in groups, "Thiếu bộ co_ban"
    assert "toan_hy_lap" in groups, "Thiếu bộ toan_hy_lap"
    assert "mo_rong" in groups, "Thiếu bộ mo_rong"
    assert "day_du" in groups, "Thiếu bộ day_du"

    co_ban_chars = groups["co_ban"].chars
    assert "a" in co_ban_chars
    assert "A" in co_ban_chars
    assert "0" in co_ban_chars
    assert "." in co_ban_chars


def test_classify_char():
    """Kiểm tra hàm classify_char phân loại chuẩn và nhận diện HW3_TONE_MAP."""
    from chuviettay.model.text_utils import classify_char

    assert classify_char("a") == "letters"
    assert classify_char("A") == "letters"
    assert classify_char("0") == "digits"
    assert classify_char(".") == "punct"
    assert classify_char("+") == "symbols"
    # Dấu thanh rời
    assert classify_char("\u0301") == "marks"  # Sắc
    assert classify_char("dấu sắc") == "marks"
    assert classify_char("dấu huyền") == "marks"
    assert classify_char("dấu hỏi") == "marks"
    assert classify_char("dấu ngã") == "marks"
    assert classify_char("dấu nặng") == "marks"


def test_pick_calib_char(tmp_path):
    """Kiểm tra hàm calibration.pick_calib_char chọn ký tự mốc đo x-height thay vì từ."""
    from chuviettay.model.calibration import pick_calib_char
    from chuviettay.model.bank import Bank

    # Kho rỗng
    bank = Bank.create_empty(str(tmp_path / "temp_calib.json.gz"))
    assert pick_calib_char(bank) is None

    # Kho chỉ có chữ 'a' và 'n'
    bank.add_letter_sample("a", [[0.0, 0.0, 5.0, -8.0]], width=5.0)
    bank.add_letter_sample("n", [[0.0, 0.0, 6.0, -8.0]], width=6.0)

    chosen = pick_calib_char(bank)
    assert chosen in ("n", "a", "o", "m", "u")
