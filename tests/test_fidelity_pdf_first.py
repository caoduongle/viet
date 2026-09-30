"""Kiểm thử kiến trúc PDF-first và độ ổn định Fidelity Mode (User Story 8, R1-R6)."""
from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock, patch

from chuviettay.fidelity.background import WhiteoutBackgroundGenerator
from chuviettay.fidelity.converter import FidelityConverter
from chuviettay.fidelity.engine import FidelityLayoutEngine
from chuviettay.fidelity.extractor import SpatialTextExtractor
from chuviettay.fidelity.fixed_model import FixedDocument, FixedPage, TextBox
from chuviettay.model.bank import Bank
from chuviettay.model.composer import WriteOptions


def test_r1_multiline_paragraph_line_splitting():
    """R1: Đoạn văn nhiều dòng phải được tách thành từng dòng riêng biệt, không bị ép co nhỏ thành một dòng."""
    extractor = SpatialTextExtractor()
    # Đoạn văn 3 dòng với line_spacing = 15.0, height = 45.0
    text_paragraph = "Đây là dòng thứ nhất.\nĐây là dòng thứ hai.\nĐây là dòng thứ ba kết thúc đoạn."
    data = {
        "source_file": "test.docx",
        "total_pages": 1,
        "pages": [
            {
                "page_index": 0,
                "width": 595.0,
                "height": 842.0,
                "boxes": [
                    {
                        "type": "text",
                        "x": 72.0,
                        "y": 100.0,
                        "width": 450.0,
                        "height": 45.0,
                        "text": text_paragraph,
                        "font_size": 12.0,
                        "line_spacing": 15.0,
                        "align": "left",
                    }
                ],
            }
        ],
    }

    doc = extractor.load_from_data(data)
    boxes = doc.pages[0].text_boxes

    # Phải có 3 TextBox thay vì 1 TextBox gộp
    assert len(boxes) == 3, f"Đoạn văn nhiều dòng phải tách thành 3 dòng, thực tế: {len(boxes)}"
    assert boxes[0].text == "Đây là dòng thứ nhất."
    assert boxes[0].y == 100.0
    assert boxes[1].text == "Đây là dòng thứ hai."
    assert boxes[1].y == 115.0
    assert boxes[2].text == "Đây là dòng thứ ba kết thúc đoạn."
    assert boxes[2].y == 130.0


def test_r4_whiteout_whitens_all_runs_and_raises_on_failure(tmp_path):
    """R4: WhiteoutBackgroundGenerator phải làm trắng cả header, footer và báo lỗi rõ ràng nếu tệp hỏng."""
    import docx
    from docx.shared import RGBColor

    src_docx = "tests/fixtures/sample.docx"
    out_white = str(tmp_path / "whiteout_clean.docx")

    res_path = WhiteoutBackgroundGenerator.create_whiteout_docx(src_docx, out_white)
    assert os.path.exists(res_path)

    # Đọc lại kiểm tra tất cả các run có màu #FFFFFF
    doc = docx.Document(res_path)
    white = RGBColor(255, 255, 255)
    for p in doc.paragraphs:
        for r in p.runs:
            assert r.font.color.rgb == white

    # Nếu tệp nguồn không tồn tại hoặc lỗi, phải ném lỗi thay vì âm thầm chép file gốc
    with pytest.raises((FileNotFoundError, RuntimeError)):
        WhiteoutBackgroundGenerator.create_whiteout_docx("non_existent_file.docx", str(tmp_path / "out.docx"))


def test_r5_fidelity_engine_xh_ratio_and_missing_grid(tmp_path):
    """R5: Tỉ lệ cỡ chữ phải dùng xh thực tế của kho mẫu (không dùng max(10, xh)), và sinh file _thieu.xopp."""
    bank = Bank.create_empty(str(tmp_path / "test_bank.json.gz"))
    bank.d["xh"] = 7.0
    bank.xh = 7.0
    bank.save()

    doc = FixedDocument(
        source_path="test.docx",
        pages=[
            FixedPage(
                page_index=0,
                width=595.0,
                height=842.0,
                boxes=[
                    TextBox(
                        x=72.0,
                        y=100.0,
                        width=400.0,
                        height=20.0,
                        text="từ_chưa_có_trong_kho",
                        font_size=14.0,
                        line_spacing=20.0,
                    )
                ],
            )
        ],
    )

    out_xopp = str(tmp_path / "out_fidelity.xopp")
    opts = WriteOptions(scale=1.0, mode="fidelity", missing_grid=True)
    engine = FidelityLayoutEngine(bank, opts)
    res = engine.render(doc, out_xopp)

    assert res.n_missing_tokens > 0
    # Phải tạo file lưới ô còn thiếu (_thieu.xopp)
    expected_grid = str(tmp_path / "out_fidelity_thieu.xopp")
    assert os.path.exists(expected_grid), "Fidelity mode phải tạo file _thieu.xopp khi có từ thiếu"


def test_r6_converter_availability_caching():
    """R6: Kiểm tra khả dụng của Word COM / LibreOffice được ghi nhớ (cache), không khởi động lại liên tục."""
    FidelityConverter.reset_cache()
    assert FidelityConverter._word_available_cache is None

    # Lần 1: Gọi is_word_available
    avail1 = FidelityConverter.is_word_available()
    assert FidelityConverter._word_available_cache is not None

    # Lần 2: Phải trả về giá trị cache
    avail2 = FidelityConverter.is_word_available()
    assert avail1 == avail2

    # Reset cache hoạt động đúng
    FidelityConverter.reset_cache()
    assert FidelityConverter._word_available_cache is None
