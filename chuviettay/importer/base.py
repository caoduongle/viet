"""Giao diện trừu tượng và kết quả nạp tài liệu cho các bộ importer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from chuviettay.document.ir import Document


@dataclass
class ImportResult:
    """Đóng gói tài liệu Document IR đã phân tích kèm các thông tin chẩn đoán."""
    document: Document
    warnings: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


class UnsupportedFormatError(ValueError):
    """Ném ra khi định dạng tệp hoặc phần mở rộng không được hỗ trợ."""


class BaseImporter(ABC):
    """Lớp cơ sở trừu tượng cho mọi bộ nạp tệp và văn bản."""

    @abstractmethod
    def import_file(self, path: str) -> ImportResult:
        """Đọc và phân tích tài liệu từ đường dẫn tệp trên đĩa."""
        ...

    @abstractmethod
    def import_text(self, text: str) -> ImportResult:
        """Phân tích tài liệu trực tiếp từ chuỗi ký tự trong bộ nhớ."""
        ...


def get_importer_for_path(path: str, format_name: str = "auto") -> BaseImporter:
    """Tạo bộ nạp tương ứng dựa vào phần mở rộng hoặc định dạng yêu cầu."""
    import os

    fmt = (format_name or "auto").lower()
    ext = os.path.splitext(path)[1].lower() if path else ""

    # 1. Nếu định dạng được chỉ định rõ ràng
    if fmt != "auto":
        if fmt == "docx":
            from chuviettay.importer.docx_importer import DocxImporter

            return DocxImporter()
        elif fmt in ("md", "markdown"):
            from chuviettay.importer.markdown_importer import MarkdownImporter

            return MarkdownImporter()
        elif fmt == "txt":
            from chuviettay.importer.txt_importer import TxtImporter

            return TxtImporter()
        else:
            raise UnsupportedFormatError(f"Định dạng không được hỗ trợ: '{format_name}'")

    # 2. Định dạng 'auto': kiểm tra phần mở rộng tệp
    if ext == ".docx":
        from chuviettay.importer.docx_importer import DocxImporter

        return DocxImporter()
    elif ext in (".md", ".markdown"):
        from chuviettay.importer.markdown_importer import MarkdownImporter

        return MarkdownImporter()
    elif ext in (".txt", ""):
        from chuviettay.importer.txt_importer import TxtImporter

        return TxtImporter()
    else:
        raise UnsupportedFormatError(f"Phần mở rộng tệp không được hỗ trợ: '{ext}' ({path})")

