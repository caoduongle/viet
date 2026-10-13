"""Package fidelity: Xử lý thay thế chữ in bằng chữ viết tay theo chế độ khóa bố cục (Fidelity Mode).

LƯU Ý LƯU TRỮ (LEGACY / ARCHIVE):
Module này phụ thuộc vào môi trường cục bộ có Microsoft Word COM (Windows) hoặc LibreOffice (Linux/macOS)
để trích xuất toạ độ không gian. Không khả dụng và không được đóng gói trong phiên bản Web tĩnh (Pyodide).
Web Client sử dụng cơ chế nhập nội dung Content-First (chuviettay.importer.importer_docx).
"""
from __future__ import annotations

from chuviettay.fidelity.fixed_model import (
    FixedDocument,
    FixedPage,
    ImageBox,
    SpatialBox,
    TableGeometry,
    TextBox,
)

__all__ = [
    "FixedDocument",
    "FixedPage",
    "ImageBox",
    "SpatialBox",
    "TableGeometry",
    "TextBox",
]
