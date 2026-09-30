"""Kiểm thử tính năng DOCX Fidelity & In-Place Text Replacement Mode (Feature 013)."""
from __future__ import annotations

import gzip
import json
import os
import xml.etree.ElementTree as ET

import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.fidelity.engine import FidelityLayoutEngine
from chuviettay.fidelity.extractor import SpatialTextExtractor
from chuviettay.fidelity.fixed_model import FixedDocument, FixedPage, ImageBox, TextBox
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteMode, WriteOptions

BANK_PATH = "tests/data/kho_mau_tong_hop.json.gz"
FIXTURE_JSON = "tests/fixtures/fidelity/sample_fidelity_data.json"
FIXTURE_PDF = "tests/fixtures/fidelity/sample_background.pdf"


@pytest.fixture
def bank():
    return Bank(BANK_PATH)


@pytest.fixture
def sample_data():
    with open(FIXTURE_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def test_fixed_model_deserialization(sample_data):
    """Mô hình FixedDocument giải mã chính xác các trang, text box, image box từ JSON."""
    doc = FixedDocument.from_dict(sample_data)
    assert doc.total_pages == 2

    page1 = doc.pages[0]
    assert page1.width == 595.28
    assert page1.height == 841.89
    assert len(page1.text_boxes) == 2
    assert len(page1.image_boxes) == 1

    tb0 = page1.text_boxes[0]
    assert tb0.text == "Văn bản word mẫu"
    assert tb0.x == 72.0
    assert tb0.y == 90.0

    img0 = page1.image_boxes[0]
    assert img0.image_filename == "image1.png"
    assert img0.width == 300.0


def test_write_mode_enum_and_validation():
    """WriteMode hỗ trợ semantic và fidelity; WriteOptions ném lỗi nếu chế độ sai."""
    assert WriteMode.SEMANTIC == "semantic"
    assert WriteMode.FIDELITY == "fidelity"

    opts = WriteOptions(mode="fidelity")
    opts.validate()

    with pytest.raises(ValueError, match="Chế độ xử lý không hợp lệ"):
        WriteOptions(mode="invalid_mode").validate()


def test_spatial_text_extractor_parse_data(sample_data):
    """SpatialTextExtractor phân tích dữ liệu không gian thành FixedDocument chuẩn."""
    extractor = SpatialTextExtractor()
    doc = extractor.load_from_data(sample_data, background_pdf="sample_background.pdf")

    assert isinstance(doc, FixedDocument)
    assert doc.total_pages == 2
    assert doc.background_pdf_path == "sample_background.pdf"
    assert doc.pages[0].text_boxes[1].text == "Bài 2: Tính xác suất xuất hiện biến cố."


def test_fidelity_layout_engine_stroke_generation(bank, sample_data, tmp_path):
    """FidelityLayoutEngine kết xuất nét vẽ trong từng bounding box mà không reflow sang trang khác."""
    doc = FixedDocument.from_dict(sample_data)
    doc.background_pdf_path = FIXTURE_PDF

    opts = WriteOptions(scale=1.0, mode="fidelity")
    engine = FidelityLayoutEngine(bank, opts)

    out_xopp = str(tmp_path / "test_fidelity_out.xopp")
    result = engine.render(doc, out_xopp)

    assert os.path.exists(out_xopp)
    assert result.out_path == out_xopp
    assert result.n_strokes > 0
    assert result.n_pages == 2
    assert result.n_images == 1
    assert result.n_tables == 1

    # Đọc XML của file .xopp đã nén gzip
    with gzip.open(out_xopp, "rb") as f:
        root = ET.fromstring(f.read().decode("utf-8"))

    pages = root.findall("page")
    assert len(pages) == 2, "Số trang .xopp phải khớp chính xác 2 trang của FixedDocument"

    # Kiểm tra kích thước và background của từng trang
    for idx, pg in enumerate(pages):
        assert float(pg.get("width", 0)) == 595.28
        assert float(pg.get("height", 0)) == 841.89
        bg = pg.find("background")
        assert bg is not None
        assert bg.get("type") == "pdf"
        assert bg.get("pageno") == str(idx)


def test_controller_write_docx_fidelity_api(tmp_path):
    """AppController.write_docx_fidelity() điều phối toàn bộ workflow tạo ra file .xopp và companion PDF."""
    ctl = AppController()
    ctl.load_bank(BANK_PATH)

    out_xopp = str(tmp_path / "api_fidelity_out.xopp")
    opts = WriteOptions(scale=1.0, mode="fidelity")

    # Dùng sample.docx
    docx_path = "tests/fixtures/sample.docx"
    result = ctl.write_docx_fidelity(docx_path, opts, out_xopp)

    assert os.path.exists(out_xopp)
    assert result.out_path == out_xopp
    assert result.n_strokes > 0

    # Companion background PDF phải được sinh ra cùng thư mục
    expected_bg = str(tmp_path / "api_fidelity_out_background.pdf")
    assert os.path.exists(expected_bg)


def test_whiteout_background_generator(tmp_path):
    """WhiteoutBackgroundGenerator đổi text color thành #FFFFFF mà không làm mất đoạn văn hay bảng."""
    from chuviettay.fidelity.background import WhiteoutBackgroundGenerator
    import docx
    from docx.shared import RGBColor

    src_docx = "tests/fixtures/sample.docx"
    out_white = str(tmp_path / "whiteout.docx")

    res_path = WhiteoutBackgroundGenerator.create_whiteout_docx(src_docx, out_white)
    assert os.path.exists(res_path)

    doc = docx.Document(res_path)
    assert len(doc.paragraphs) > 0

    # Kiểm tra màu của các runs trong văn bản
    white_rgb = RGBColor(255, 255, 255)
    for p in doc.paragraphs:
        for r in p.runs:
            assert r.font.color.rgb == white_rgb


def test_xopp_pdf_background_tag_generation():
    """Hàm pdf_background_xml sinh thẻ background type=pdf chuẩn cho Xournal++."""
    from chuviettay.model import xopp

    bg_xml = xopp.pdf_background_xml("tai_lieu_bg.pdf", pageno=3, domain="relative")
    assert 'type="pdf"' in bg_xml
    assert 'domain="relative"' in bg_xml
    assert 'filename="tai_lieu_bg.pdf"' in bg_xml
    assert 'pageno="3"' in bg_xml

    page_xml = xopp.page_open_xml(595.28, 841.89, background=bg_xml)
    assert '<page width="595.28" height="841.89">' in page_xml
    assert bg_xml in page_xml

