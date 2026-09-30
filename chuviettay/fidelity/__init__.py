"""Package fidelity: Xử lý thay thế chữ in bằng chữ viết tay theo chế độ khóa bố cục (Fidelity Mode).

Giữ nguyên 100% số trang, tọa độ không gian, hình ảnh nhúng và cấu trúc bảng biểu.
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
