"""Kiểm thử cấu hình PageBackground, mẫu nền BACKGROUND_PRESETS và sinh XML."""
import pytest
from chuviettay.document.page_format import (
    PageBackground,
    BACKGROUND_PRESETS,
    get_page_catalog,
    parse_length,
)
from chuviettay.model.composer import WriteOptions


def test_background_presets_defined():
    """Kiểm tra các preset chuẩn theo pagetemplates.ini.in được định nghĩa đầy đủ."""
    expected = [
        "plain",
        "ruled",
        "lined",
        "lined_right",
        "lined_narrow",
        "lined_college",
        "lined_wide",
        "graph",
        "graph_5mm",
        "graph_grid",
        "graph_border",
        "graph_border_bold_5",
        "dotted",
        "iso_graph",
        "iso_dotted",
        "staves",
    ]
    for p in expected:
        assert p in BACKGROUND_PRESETS, f"Thiếu preset {p}"


def test_background_preset_xml_generation():
    """Kiểm tra XML sinh ra cho các preset chính."""
    # Plain
    bg_plain = BACKGROUND_PRESETS["plain"]
    assert bg_plain.to_xml() == '<background type="solid" color="#ffffffff" style="plain"/>'

    # Ruled
    bg_ruled = BACKGROUND_PRESETS["ruled"]
    assert 'style="ruled"' in bg_ruled.to_xml()
    assert 'config="r1=24"' in bg_ruled.to_xml()

    # Lined with right vertical line
    bg_right = BACKGROUND_PRESETS["lined_right"]
    assert 'style="lined"' in bg_right.to_xml()
    assert 'config="r1=24,m1=-72"' in bg_right.to_xml()

    # Graph border bold 5th
    bg_gb5 = BACKGROUND_PRESETS["graph_border_bold_5"]
    xml_gb5 = bg_gb5.to_xml()
    assert 'style="graph"' in xml_gb5
    assert 'r1=14.17' in xml_gb5
    assert 'm1=20' in xml_gb5
    assert 'rm=1' in xml_gb5
    assert 'bli=5' in xml_gb5
    assert 'blw=1.5' in xml_gb5


def test_negative_margin_validation_and_parsing():
    """Kiểm tra parsing và validate lề đứng âm (m1 < 0) cho lined."""
    # parse_length với allow_negative
    assert parse_length("-72pt", allow_negative=True) == -72.0
    assert parse_length("-1in", allow_negative=True) == -72.0
    with pytest.raises(ValueError):
        parse_length("-72pt", allow_negative=False)

    # WriteOptions với m1 âm hợp lệ cho lined
    opts_ok = WriteOptions(background="lined", background_margin=-72.0)
    opts_ok.validate()
    pf = opts_ok.resolve_page_format()
    assert pf.background.margin == -72.0
    assert 'm1=-72' in pf.background.to_xml()

    # WriteOptions với m1 âm bị từ chối nếu không phải lined
    opts_bad = WriteOptions(background="graph", background_margin=-72.0)
    with pytest.raises(ValueError, match="background_margin âm chỉ được hỗ trợ với kiểu nền 'lined'"):
        opts_bad.validate()

    # m1 vượt quá kích thước trang bị từ chối
    opts_too_large = WriteOptions(paper="a4", background="lined", background_margin=-700.0)
    with pytest.raises(ValueError, match="Giá trị tuyệt đối của background_margin"):
        opts_too_large.validate()


def test_write_options_preset_and_overrides():
    """Kiểm tra WriteOptions nạp preset và ghi đè cờ riêng lẻ."""
    # Sử dụng preset lined_college (r1=20.0, m1=72.0)
    opts = WriteOptions(background_preset="lined_college")
    opts.validate()
    pf = opts.resolve_page_format()
    assert pf.background.style == "lined"
    assert pf.background.spacing == 20.0
    assert pf.background.margin == 72.0

    # Ghi đè r1 và background_color
    opts_ov = WriteOptions(
        background_preset="lined_college",
        background_spacing=22.5,
        background_color="#e8f4f8ff",
    )
    opts_ov.validate()
    pf_ov = opts_ov.resolve_page_format()
    assert pf_ov.background.style == "lined"
    assert pf_ov.background.spacing == 22.5
    assert pf_ov.background.margin == 72.0
    assert pf_ov.background.color == "#e8f4f8ff"
