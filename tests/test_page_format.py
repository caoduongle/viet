"""Kiểm thử đơn vị cho module page_format: PaperSize, PageBackground, PageFormat và parse_length."""
import pytest

from chuviettay.document.page_format import (
    PAPER_SIZES,
    VALID_BACKGROUND_STYLES,
    PageBackground,
    PageFormat,
    PaperSize,
    parse_length,
)
from chuviettay.model.composer import WriteOptions


class TestParseLength:
    """Kiểm tra hàm parse_length chuyển đổi đơn vị đo lường sang điểm PostScript."""

    def test_numeric_inputs(self):
        assert parse_length(100) == 100.0
        assert parse_length(595.28) == 595.28
        assert parse_length(0) == 0.0

    def test_units_conversion(self):
        # 1 inch = 72 pt
        assert parse_length("1in") == 72.0
        assert parse_length("1 inch") == 72.0
        assert parse_length("8.5in") == 612.0

        # 1 mm = 72 / 25.4 pt ~ 2.8346 pt -> 5 mm ~ 14.17 pt
        assert parse_length("5mm") == 14.17
        assert parse_length("5 mm") == 14.17
        assert parse_length("210mm") == 595.28
        assert parse_length("297mm") == 841.89

        # 1 cm = 10 mm ~ 28.346 pt -> 21 cm ~ 595.28 pt
        assert parse_length("21cm") == 595.28
        assert parse_length("29.7cm") == 841.89

        # pt
        assert parse_length("595.28pt") == 595.28
        assert parse_length("14.17") == 14.17

    def test_case_insensitive_and_whitespace(self):
        assert parse_length("  5MM  ") == 14.17
        assert parse_length("1.5 CM") == 42.52

    def test_invalid_lengths(self):
        with pytest.raises(ValueError, match="Kích thước phải là số dương hữu hạn"):
            parse_length(-10)

        with pytest.raises(ValueError, match="Kích thước phải là số dương hữu hạn"):
            parse_length("-5mm")

        with pytest.raises(ValueError, match="Kích thước không được để trống"):
            parse_length("")

        with pytest.raises(ValueError, match="Đơn vị đo không được hỗ trợ"):
            parse_length("100px")

        with pytest.raises(ValueError, match="Chuỗi kích thước không hợp lệ"):
            parse_length("abc")


class TestPaperSizes:
    """Kiểm tra kích thước chuẩn của các loại giấy."""

    def test_standard_sizes_dimensions(self):
        assert "a4" in PAPER_SIZES
        assert "a3" in PAPER_SIZES
        assert "a5" in PAPER_SIZES
        assert "letter" in PAPER_SIZES
        assert "legal" in PAPER_SIZES
        assert "16:9" in PAPER_SIZES
        assert "4:3" in PAPER_SIZES

        a4 = PAPER_SIZES["a4"]
        assert round(a4.width, 2) == 595.28
        assert round(a4.height, 2) == 841.89

        a5 = PAPER_SIZES["a5"]
        assert round(a5.width, 2) == 419.53
        assert round(a5.height, 2) == 595.28

        a3 = PAPER_SIZES["a3"]
        assert round(a3.width, 2) == 841.89
        assert round(a3.height, 2) == 1190.55


class TestPageBackground:
    """Kiểm tra sinh thẻ XML nền trang XOPP."""

    def test_plain_background(self):
        bg = PageBackground(style="plain")
        xml = bg.to_xml()
        assert xml == '<background type="solid" color="#ffffffff" style="plain"/>'

    def test_graph_background_spacing(self):
        bg = PageBackground(style="graph", spacing=14.17)
        xml = bg.to_xml()
        assert 'style="graph"' in xml
        assert 'config="r1=14.17"' in xml
        assert 'color="#ffffffff"' in xml

    def test_ruled_background_with_margin(self):
        bg = PageBackground(style="ruled", spacing=24.0, margin=72.0)
        xml = bg.to_xml()
        assert 'style="ruled"' in xml
        assert 'config="r1=24 m1=72"' in xml or 'config="r1=24,m1=72"' in xml

    @pytest.mark.parametrize(
        ("style_in", "expected_xml_style"),
        [
            ("plain", "plain"),
            ("lined", "lined"),
            ("ruled", "ruled"),
            ("graph", "graph"),
            ("dotted", "dotted"),
            ("iso_graph", "isograph"),
            ("iso_dotted", "isodotted"),
            ("music", "staves"),
        ],
    )
    def test_page_background_to_xml_styles(self, style_in, expected_xml_style):
        bg = PageBackground(style=style_in)
        assert f'style="{expected_xml_style}"' in bg.to_xml()

    @pytest.mark.parametrize(
        ("alias", "canonical_internal"),
        [
            ("isograph", "iso_graph"),
            ("isodotted", "iso_dotted"),
            ("staves", "music"),
        ],
    )
    def test_write_options_background_alias_compatibility(self, alias, canonical_internal):
        opts_alias = WriteOptions(background=alias)
        opts_alias.validate()
        opts_internal = WriteOptions(background=canonical_internal)
        opts_internal.validate()

        xml_alias = opts_alias.resolve_page_format().background.to_xml()
        xml_internal = opts_internal.resolve_page_format().background.to_xml()
        assert xml_alias == xml_internal

    def test_invalid_style_fallback_to_plain(self):
        bg = PageBackground(style="non_existent_style")
        xml = bg.to_xml()
        assert 'style="plain"' in xml

    def test_custom_color_normalization(self):
        bg = PageBackground(color="#1A237E")
        assert 'color="#1a237e"' in bg.to_xml()

        bg_invalid = PageBackground(color="invalid_color")
        assert 'color="#ffffffff"' in bg_invalid.to_xml()


class TestPageFormat:
    """Kiểm tra tính toán kích thước, hướng giấy và lề."""

    def test_portrait_orientation(self):
        fmt = PageFormat(paper=PAPER_SIZES["a4"], orientation="portrait")
        assert fmt.width == 595.28
        assert fmt.height == 841.89
        assert fmt.content_top == 40.0
        assert fmt.max_page_y == 841.89 - 40.0
        assert fmt.usable_width == 595.28 - 36.0 - 36.0

    def test_landscape_orientation(self):
        fmt = PageFormat(paper=PAPER_SIZES["a4"], orientation="landscape")
        # Hoán đổi chiều dài và rộng
        assert fmt.width == 841.89
        assert fmt.height == 595.28
        assert fmt.usable_width == 841.89 - 36.0 - 36.0
        assert fmt.max_page_y == 595.28 - 40.0

    def test_custom_margins(self):
        fmt = PageFormat(
            paper=PAPER_SIZES["letter"],
            margin_left=50.0,
            margin_right=50.0,
            margin_top=60.0,
            margin_bottom=60.0,
        )
        assert fmt.usable_width == 612.0 - 100.0
        assert fmt.usable_height == 792.0 - 120.0
        assert fmt.content_top == 60.0
        assert fmt.max_page_y == 792.0 - 60.0


class TestWriteOptionsPageFormatResolution:
    """Kiểm tra phân giải WriteOptions sang PageFormat."""

    def test_default_options(self):
        opts = WriteOptions()
        opts.validate()
        pf = opts.resolve_page_format()
        assert pf.paper.name == "A4"
        assert pf.orientation == "portrait"
        assert pf.background.style == "plain"

    def test_custom_paper_resolution(self):
        opts = WriteOptions(
            paper="custom",
            paper_width=450.0,
            paper_height=650.0,
            orientation="landscape",
            background="graph",
            background_spacing=14.17,
        )
        opts.validate()
        pf = opts.resolve_page_format()
        assert pf.width == 650.0
        assert pf.height == 450.0
        assert pf.background.style == "graph"
        assert pf.background.spacing == 14.17

    def test_margin_left_plus_right_exceeds_width_raises_value_error(self):
        opts = WriteOptions(paper="a4", margin_left=350.0, margin_right=300.0)
        with pytest.raises(ValueError, match="nhỏ hơn bề ngang trang"):
            opts.validate()

    def test_margin_top_plus_bottom_exceeds_height_raises_value_error(self):
        opts = WriteOptions(paper="a4", margin_top=500.0, margin_bottom=400.0)
        with pytest.raises(ValueError, match="nhỏ hơn bề dọc trang"):
            opts.validate()

    def test_margin_sum_equal_to_page_dimension_raises_value_error(self):
        opts = WriteOptions(paper="a4", margin_left=297.64, margin_right=297.64)
        with pytest.raises(ValueError, match="nhỏ hơn bề ngang trang"):
            opts.validate()

    def test_landscape_orientation_swapped_margin_validation(self):
        # A4 landscape: width is 841.89, height is 595.28
        opts = WriteOptions(
            paper="a4",
            orientation="landscape",
            margin_left=400.0,
            margin_right=300.0,
            margin_top=350.0,
            margin_bottom=300.0,
        )
        with pytest.raises(ValueError, match="nhỏ hơn bề dọc trang"):
            opts.validate()

    def test_custom_paper_margin_validation(self):
        opts = WriteOptions(
            paper="custom",
            paper_width=200.0,
            paper_height=200.0,
            margin_left=120.0,
            margin_right=100.0,
        )
        with pytest.raises(ValueError, match="nhỏ hơn bề ngang trang"):
            opts.validate()
