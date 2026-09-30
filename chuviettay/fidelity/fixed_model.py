"""Mô hình dữ liệu hình học cố định (Fixed-Layout Spatial Models) cho chế độ Fidelity Mode."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpatialBox:
    """Khối hình học cơ sở trên một trang cố định (tọa độ tính bằng points, 1 pt = 1/72 inch)."""
    x: float
    y: float
    width: float
    height: float
    z_index: int = 0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height


@dataclass
class TextBox(SpatialBox):
    """Khối văn bản cần thay thế bằng nét chữ viết tay tại đúng tọa độ."""
    text: str = ""
    font_size: float = 12.0
    font_family: str = "Times New Roman"
    align: str = "left"
    line_spacing: float = 14.0
    is_heading: bool = False


@dataclass
class ImageBox(SpatialBox):
    """Khối hình ảnh nhúng (inline drawing / picture) giữ nguyên trên tài liệu."""
    image_id: str = ""
    image_filename: str = ""
    image_bytes: bytes = b""
    format: str = "image/png"
    caption: str | None = None


@dataclass
class TableGeometry(SpatialBox):
    """Hình học khung viền bảng biểu và các ô bảng."""
    rows: int = 0
    cols: int = 0
    cell_boxes: list[SpatialBox] = field(default_factory=list)


@dataclass
class FixedPage:
    """Một trang cố định với kích thước tuyệt đối và danh sách các khối thành phần."""
    page_index: int
    width: float = 595.28   # mặc định A4 portrait
    height: float = 841.89  # mặc định A4 portrait
    background_pdf: str | None = None
    boxes: list[SpatialBox] = field(default_factory=list)

    @property
    def text_boxes(self) -> list[TextBox]:
        return [b for b in self.boxes if isinstance(b, TextBox)]

    @property
    def image_boxes(self) -> list[ImageBox]:
        return [b for b in self.boxes if isinstance(b, ImageBox)]

    @property
    def table_geometries(self) -> list[TableGeometry]:
        return [b for b in self.boxes if isinstance(b, TableGeometry)]


@dataclass
class FixedDocument:
    """Tài liệu đa trang với bố cục cố định trích xuất từ DOCX."""
    source_path: str
    pages: list[FixedPage] = field(default_factory=list)
    background_pdf_path: str | None = None

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: str = "") -> FixedDocument:
        pages: list[FixedPage] = []
        for p_data in data.get("pages", []):
            boxes: list[SpatialBox] = []
            for b_data in p_data.get("boxes", []):
                b_type = b_data.get("type", "text")
                x = float(b_data.get("x", 0.0))
                y = float(b_data.get("y", 0.0))
                w = float(b_data.get("width", 0.0))
                h = float(b_data.get("height", 0.0))
                z = int(b_data.get("z_index", 0))

                if b_type == "text":
                    boxes.append(
                        TextBox(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            z_index=z,
                            text=str(b_data.get("text", "")),
                            font_size=float(b_data.get("font_size", 12.0)),
                            font_family=str(b_data.get("font_family", "Times New Roman")),
                            align=str(b_data.get("align", "left")),
                            line_spacing=float(b_data.get("line_spacing", 14.0)),
                            is_heading=bool(b_data.get("is_heading", False)),
                        )
                    )
                elif b_type == "image":
                    boxes.append(
                        ImageBox(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            z_index=z,
                            image_id=str(b_data.get("image_id", "")),
                            image_filename=str(b_data.get("image_filename", "")),
                            format=str(b_data.get("format", "image/png")),
                            caption=b_data.get("caption"),
                        )
                    )
                elif b_type == "table":
                    boxes.append(
                        TableGeometry(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            z_index=z,
                            rows=int(b_data.get("rows", 0)),
                            cols=int(b_data.get("cols", 0)),
                        )
                    )
            pages.append(
                FixedPage(
                    page_index=int(p_data.get("page_index", len(pages))),
                    width=float(p_data.get("width", 595.28)),
                    height=float(p_data.get("height", 841.89)),
                    boxes=boxes,
                )
            )

        return cls(
            source_path=source_path or data.get("source_file", ""),
            pages=pages,
            background_pdf_path=data.get("background_pdf_path"),
        )
