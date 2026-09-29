"""Bộ nạp tài liệu văn bản thuần (.txt) chuyển đổi sang Document IR."""
from __future__ import annotations

import os
import unicodedata

from chuviettay.document.ir import Document, Paragraph, Text
from chuviettay.importer.base import BaseImporter, ImportResult


class TxtImporter(BaseImporter):
    """Nạp tệp văn bản thuần UTF-8 thành cây Document IR."""

    def import_text(self, text: str) -> ImportResult:
        """Phân tích chuỗi văn bản thành danh sách Paragraph."""
        normalized = unicodedata.normalize("NFC", text or "")
        blocks = []
        for line in normalized.splitlines():
            s = line.strip()
            if s:
                blocks.append(Paragraph(inlines=[Text(text=s)]))
        return ImportResult(document=Document(blocks=blocks))

    def import_file(self, path: str) -> ImportResult:
        """Đọc tệp văn bản từ đĩa."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy tệp văn bản: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return self.import_text(content)
