"""Quản lý bộ đệm trang (PageBuffer) phát trực tiếp ra file .xopp nhằm tối ưu bộ nhớ cho tài liệu lớn."""
from __future__ import annotations

import gzip
import os
import tempfile
from typing import IO, TYPE_CHECKING

from chuviettay.config import MAXH
from chuviettay.model import xopp

if TYPE_CHECKING:
    from chuviettay.document.page_format import PageBackground


class PageBuffer:
    """Bộ đệm ghi trang theo luồng (streaming) cho các tài liệu lớn nhiều trang."""

    def __init__(
        self,
        out_path: str,
        page_w: float,
        default_page_h: float = MAXH,
        default_background: PageBackground | None = None,
    ):
        self.out_path = out_path
        self.page_w = page_w
        self.default_page_h = default_page_h
        self.default_background = default_background
        self.n_pages = 0
        self._temp_path: str = ""
        # Tạo file tạm thời
        parent_dir = os.path.dirname(os.path.abspath(out_path)) or "."
        os.makedirs(parent_dir, exist_ok=True)
        fd, self._temp_path = tempfile.mkstemp(suffix=".xopp", dir=parent_dir)
        os.close(fd)
        self._f: IO[str] = gzip.open(self._temp_path, "wt", encoding="utf-8", newline="")
        self._f.write(xopp.HEAD + "\n")

    def append_page(
        self,
        page_strokes: list[str],
        page_h: float | None = None,
        page_w: float | None = None,
        background: PageBackground | None = None,
    ) -> None:
        """Ghi một trang hoàn chỉnh vào luồng và giải phóng ngay bộ nhớ các nét của trang đó."""
        w = page_w if page_w is not None else self.page_w
        h = page_h if page_h is not None else self.default_page_h
        bg = background if background is not None else self.default_background
        self._f.write(xopp.page_open_xml(w, h, bg) + "\n")
        for stroke in page_strokes:
            self._f.write(stroke + "\n")
        self._f.write(xopp.PAGE_CLOSE + "\n")
        self.n_pages += 1


    def close(self) -> str:
        """Đóng luồng, hoàn tất tài liệu và di chuyển nguyên tử về đường dẫn đích."""
        if not self._f.closed:
            self._f.write("</xournal>\n")
            self._f.close()
        if os.path.exists(self._temp_path):
            os.replace(self._temp_path, self.out_path)
        return self.out_path

    def __enter__(self) -> PageBuffer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            try:
                if not self._f.closed:
                    self._f.close()
                if os.path.exists(self._temp_path):
                    os.remove(self._temp_path)
            except OSError:
                pass
        else:
            self.close()
