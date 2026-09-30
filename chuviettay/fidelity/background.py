"""Bộ tạo tệp nền tài liệu không chứa chữ in (Whiteout Background Generator).

Thực hiện biến đổi Whiteout Run Transform: đổi toàn bộ chữ in thành màu trắng (#FFFFFF),
giữ nguyên 100% hình ảnh (inline drawing), đường viền bảng, biểu đồ và tỷ lệ bố cục.
"""
from __future__ import annotations

import logging
import os
import tempfile

_log = logging.getLogger(__name__)


class WhiteoutBackgroundGenerator:
    """Tạo bản sao DOCX đã làm trắng chữ in để làm nền cho Xournal++."""

    @classmethod
    def create_whiteout_docx(cls, docx_path: str, output_path: str | None = None) -> str:
        """Đổi toàn bộ text runs trong DOCX thành màu trắng và lưu ra file mới."""
        docx_abs = os.path.abspath(docx_path)
        if not os.path.exists(docx_abs):
            raise FileNotFoundError(f"Không tìm thấy tệp DOCX: {docx_path}")

        if output_path is None:
            fd, output_path = tempfile.mkstemp(prefix="whiteout_", suffix=".docx")
            os.close(fd)

        try:
            import docx
            from docx.shared import RGBColor

            doc = docx.Document(docx_abs)
            white = RGBColor(255, 255, 255)

            # 1. Làm trắng toàn bộ các đoạn văn ngoài bảng
            for p in doc.paragraphs:
                for r in p.runs:
                    r.font.color.rgb = white

            # 2. Làm trắng toàn bộ chữ trong các bảng
            for tbl in doc.tables:
                for row in tbl.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for r in p.runs:
                                r.font.color.rgb = white

            # 3. Làm trắng chữ trong Headers và Footers nếu có
            for sec in doc.sections:
                for hf in (sec.header, sec.footer):
                    if hf is not None:
                        for p in hf.paragraphs:
                            for r in p.runs:
                                r.font.color.rgb = white

            doc.save(output_path)
            return output_path

        except Exception as e:
            _log.warning("Lỗi khi tạo whiteout DOCX: %s. Sao chép tệp gốc làm dự phòng.", e)
            import shutil
            shutil.copyfile(docx_abs, output_path)
            return output_path
