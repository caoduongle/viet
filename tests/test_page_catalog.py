"""Kiểm thử catalog định dạng trang, mẫu nền và tone màu chuẩn."""
import json
import pytest
from chuviettay.controller.app_controller import AppController
from chuviettay.document.page_format import get_page_catalog, BACKGROUND_PRESETS, PAPER_SIZES


def test_page_catalog_structure_and_json_serializable():
    """Kiểm tra cấu trúc catalog và tính tuần tự hóa JSON."""
    cat = get_page_catalog()
    assert isinstance(cat, dict)
    assert "sizes" in cat
    assert "presets" in cat
    assert "tones" in cat

    # Kiểm tra JSON serialize không bị lỗi
    dumped = json.dumps(cat)
    assert len(dumped) > 0

    # Kiểm tra sizes
    for k, s in cat["sizes"].items():
        assert "id" in s and "name" in s and "width" in s and "height" in s
        assert s["width"] > 0 and s["height"] > 0

    # Kiểm tra presets
    for k, p in cat["presets"].items():
        assert "id" in p and "name" in p and "style" in p
        assert "name_en" in p and "name_vi" in p
        assert p["id"] in BACKGROUND_PRESETS

    # Kiểm tra tones
    assert len(cat["tones"]) >= 4
    for t in cat["tones"]:
        assert "id" in t and "name" in t and "color" in t and "dark" in t


def test_app_controller_delegates_catalog(tiny_bank_path):
    """Kiểm tra AppController.get_page_catalog() ủy quyền đúng."""
    ctl = AppController(tiny_bank_path)
    cat_ctl = ctl.get_page_catalog()
    cat_direct = get_page_catalog()
    assert cat_ctl == cat_direct
