"""Bộ trích xuất cấu trúc không gian (Spatial Text Extractor)."""
from __future__ import annotations

import logging
from typing import Any

from chuviettay.fidelity.converter import FidelityConverter
from chuviettay.fidelity.fixed_model import FixedDocument, FixedPage, SpatialBox, TextBox

_log = logging.getLogger(__name__)


class SpatialTextExtractor:
    """Trích xuất và chuẩn hóa dữ liệu không gian từ tệp DOCX thành mô hình FixedDocument."""

    def extract(self, docx_path: str, background_pdf: str | None = None) -> FixedDocument:
        """Trích xuất dữ liệu không gian từ DOCX qua FidelityConverter."""
        data = FidelityConverter.extract_spatial_data(docx_path)
        return self.load_from_data(data, background_pdf=background_pdf, source_path=docx_path)

    def load_from_data(
        self,
        data: dict[str, Any],
        background_pdf: str | None = None,
        source_path: str = "",
    ) -> FixedDocument:
        """Phân tích dữ liệu từ cấu trúc dict sang FixedDocument, hỗ trợ tách đoạn văn nhiều dòng."""
        doc = FixedDocument.from_dict(data, source_path=source_path)
        if background_pdf:
            doc.background_pdf_path = background_pdf

        # Chuẩn hóa các TextBox nhiều dòng (Multi-line paragraphs)
        normalized_pages: list[FixedPage] = []
        for pg in doc.pages:
            new_boxes: list[SpatialBox] = []
            for b in pg.boxes:
                if isinstance(b, TextBox) and ("\n" in b.text or "\r" in b.text):
                    clean_text = b.text.replace("\r\n", "\n").replace("\r", "\n")
                    sub_lines = [ln.strip() for ln in clean_text.split("\n") if ln.strip()]
                    for idx, ln in enumerate(sub_lines):
                        new_boxes.append(
                            TextBox(
                                x=b.x,
                                y=b.y + (idx * b.line_spacing),
                                width=b.width,
                                height=b.line_spacing,
                                z_index=b.z_index,
                                text=ln,
                                font_size=b.font_size,
                                font_family=b.font_family,
                                align=b.align,
                                line_spacing=b.line_spacing,
                                is_heading=b.is_heading,
                            )
                        )
                else:
                    new_boxes.append(b)
            normalized_pages.append(
                FixedPage(
                    page_index=pg.page_index,
                    width=pg.width,
                    height=pg.height,
                    background_pdf=background_pdf,
                    boxes=new_boxes,
                )
            )

        doc.pages = normalized_pages
        return doc
