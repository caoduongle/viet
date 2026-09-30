"""Bộ trích xuất cấu trúc không gian (Spatial Text Extractor)."""
from __future__ import annotations

import logging
from typing import Any

from chuviettay.fidelity.converter import FidelityConverter
from chuviettay.fidelity.fixed_model import FixedDocument, FixedPage, ImageBox, SpatialBox, TextBox

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

        # Chuẩn hóa các TextBox nhiều dòng (Multi-line paragraphs, R1)
        normalized_pages: list[FixedPage] = []
        for pg in doc.pages:
            new_boxes: list[SpatialBox] = []
            for b in pg.boxes:
                if isinstance(b, TextBox):
                    clean_text = b.text.replace("\r\n", "\n").replace("\r", "\n")
                    if "\n" in clean_text:
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
                    elif b.line_spacing > 0 and b.height >= 1.7 * b.line_spacing:
                        # R1: Đoạn văn nhiều dòng tự quấn (wrap) trong Word không có ký tự \n
                        words = clean_text.split()
                        if words:
                            avg_char_w = max(4.0, (b.font_size or 12.0) * 0.55)
                            max_line_chars = max(10, int(b.width / avg_char_w)) if b.width > 20 else 60
                            current_line: list[str] = []
                            current_len = 0
                            lines: list[str] = []
                            for w in words:
                                if current_line and (current_len + len(w) + 1 > max_line_chars):
                                    lines.append(" ".join(current_line))
                                    current_line = [w]
                                    current_len = len(w)
                                else:
                                    current_line.append(w)
                                    current_len += len(w) + 1
                            if current_line:
                                lines.append(" ".join(current_line))

                            for idx, ln in enumerate(lines):
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
                    else:
                        new_boxes.append(b)
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

    @classmethod
    def extract_from_pdf(cls, pdf_path: str) -> FixedDocument:
        """Trích xuất dòng văn bản trực tiếp từ tệp PDF bằng pdfplumber (MIT)."""
        try:
            import pdfplumber
        except ImportError:
            raise RuntimeError(
                "Trích xuất PDF yêu cầu thư viện 'pdfplumber'. Vui lòng cài đặt: pip install pdfplumber"
            )

        pages: list[FixedPage] = []
        with pdfplumber.open(pdf_path) as pdf:
            for idx, p in enumerate(pdf.pages):
                boxes: list[SpatialBox] = []
                text_lines = getattr(p, "extract_text_lines", lambda: [])()
                for line in text_lines:
                    txt = line.get("text", "").strip()
                    if not txt:
                        continue
                    x0 = float(line.get("x0", 0.0))
                    top = float(line.get("top", 0.0))
                    width = float(line.get("x1", 0.0)) - x0
                    height = float(line.get("bottom", 0.0)) - top
                    chars = line.get("chars", [])
                    font_size = float(sum(c.get("size", 12.0) for c in chars) / len(chars)) if chars else 12.0
                    boxes.append(
                        TextBox(
                            x=x0,
                            y=top,
                            width=width,
                            height=height,
                            text=txt,
                            font_size=font_size,
                            line_spacing=height,
                            align="left",
                        )
                    )
                for img in getattr(p, "images", []):
                    boxes.append(
                        ImageBox(
                            x=float(img.get("x0", 0.0)),
                            y=float(img.get("top", 0.0)),
                            width=float(img.get("width", 0.0)),
                            height=float(img.get("height", 0.0)),
                        )
                    )
                pages.append(
                    FixedPage(
                        page_index=idx,
                        width=float(p.width),
                        height=float(p.height),
                        background_pdf=pdf_path,
                        boxes=boxes,
                    )
                )

        return FixedDocument(
            source_path=pdf_path,
            pages=pages,
            background_pdf_path=pdf_path,
        )
