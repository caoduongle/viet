"""WordCanvas -- ô vẽ một từ bằng chuột / bút cảm ứng (dùng trong tab "Dạy từ mới").

So với bản gốc (hw_gui.py):
  - Phép quy đổi pixel màn hình -> đơn vị kho mẫu được tách thành HÀM THUẦN
    strokes_to_bank_units() (không cần cửa sổ Tk nên test được ngay, xem
    tests/test_word_canvas.py). Công thức giữ nguyên bản gốc.
  - Hệ số cỡ tay truyền thẳng như THAM SỐ (to_bank_strokes(scale)) thay vì qua hàm
    callback get_scale -- luồng dữ liệu tường minh hơn, dễ lần theo khi debug.
"""
from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from chuviettay.controller.teach_geometry import (
    BASE_PX,
    CANVAS_H,
    CANVAS_W,
    MIN_POINT_DIST,
    PxStroke,
    ZOOM,
    filter_stroke_points,  # noqa: F401
    strokes_to_bank_units,
)


class WordCanvas(ttk.Frame):
    """Canvas để vẽ một từ. Giữ các nét ở đơn vị pixel màn hình; to_bank_strokes(scale)
    đổi sang đơn vị kho mẫu."""

    def __init__(self, master, get_xh: Callable[[], float]):
        super().__init__(master)
        self.get_xh = get_xh
        self.canvas = tk.Canvas(self, width=CANVAS_W, height=CANVAS_H, bg="white",
                                cursor="pencil", highlightthickness=1, highlightbackground="#aaaaaa")
        self.canvas.pack(fill="both", expand=True)
        self.strokes: list[PxStroke] = []     # các nét đã xong
        self._cur: PxStroke | None = None     # nét đang vẽ dở
        self._last_pt: tuple[float, float] | None = None
        self.canvas.bind("<ButtonPress-1>", lambda e: self.start(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.move(e.x, e.y))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.end())
        self.draw_guides()

    # -- logic vẽ (không phụ thuộc sự kiện Tk nên gọi trực tiếp để test được) ----------
    def start(self, x: float, y: float) -> None:
        self._cur = [(x, y)]
        self._last_pt = (x, y)

    def move(self, x: float, y: float) -> None:
        if self._cur is None:
            self.start(x, y)
            return
        lx, ly = self._last_pt
        if (x - lx) ** 2 + (y - ly) ** 2 < MIN_POINT_DIST ** 2:
            return  # lọc bớt điểm quá gần nhau cho dữ liệu gọn
        self.canvas.create_line(lx, ly, x, y, fill="#000000", width=2,
                                capstyle="round", smooth=True, tags="ink")
        self._cur.append((x, y))
        self._last_pt = (x, y)

    def end(self) -> None:
        if self._cur and len(self._cur) >= 2:
            self.strokes.append(self._cur)
        self._cur = None
        self._last_pt = None

    def undo(self) -> None:
        if self.strokes:
            self.strokes.pop()
            self.redraw()

    def clear(self) -> None:
        self.strokes = []
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("ink")
        for st in self.strokes:
            for (x0, y0), (x1, y1) in zip(st, st[1:]):
                self.canvas.create_line(x0, y0, x1, y1, fill="#000000", width=2,
                                        capstyle="round", smooth=True, tags="ink")

    def draw_guides(self) -> None:
        """Vẽ 2 đường kẻ mờ làm mốc: dòng kẻ chân chữ + mốc chiều cao chữ thường."""
        self.canvas.delete("guide")
        c = self.canvas
        c.create_line(15, BASE_PX, CANVAS_W - 15, BASE_PX, fill="#c8c8c8", width=1, tags="guide")
        xh_px = self.get_xh() * ZOOM
        c.create_line(15, BASE_PX - xh_px, 130, BASE_PX - xh_px, fill="#c8c8c8", width=1,
                      dash=(3, 2), tags="guide")
        c.tag_lower("guide")

    def has_ink(self) -> bool:
        return len(self.strokes) > 0

    def to_bank_strokes(self, scale: float) -> tuple[list[list[float]], float]:
        """-> (nét, độ rộng) theo đơn vị kho mẫu với hệ số cỡ tay `scale`."""
        return strokes_to_bank_units(self.strokes, scale)
