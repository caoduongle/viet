"""Các helper dùng chung cho kiểm thử (test helpers)."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Sequence

from chuviettay.config import BASE, CH, CW, MXT, MYT, ROWS, COLS
from chuviettay.model.xopp import (
    HW3_BASELINE_Y,
    read_xopp,
    save_xopp,
)


def fill_grid_with_ink(
    grid_path: str,
    out_path: str,
    labels: Sequence[str] | None = None,
    color: str = "#000000",
    width: str = "1.41",
) -> int:
    """Giả lập người dùng viết nét mực vào các ô của file lưới .xopp.

    Tìm các thẻ <text> trong lưới. Nếu khớp với danh sách labels (hoặc tất cả nếu labels is None),
    chèn một nét <stroke> người dùng màu `color` vào đúng ô tương ứng.

    Trả về số ô đã được điền mực.
    """
    root = read_xopp(grid_path)
    filled_count = 0

    for pi, page in enumerate(root.findall("page")):
        layer = page.find("layer")
        if layer is None:
            continue

        for t in list(page.iter("text")):
            lbl = (t.text or "").strip()
            if not lbl or lbl.startswith("hw") or "HƯỚNG DẪN" in lbl or "Viết nhỏ" in lbl:
                continue

            if labels is not None and lbl not in labels:
                continue

            try:
                tx, ty = float(t.get("x")), float(t.get("y"))
            except (TypeError, ValueError):
                continue

            col = int((tx - MXT) // CW)
            row = int((ty - MYT) // CH)
            if not (0 <= col < COLS and 0 <= row < ROWS):
                continue

            # Toạ độ gốc ô:
            cell_x0 = MXT + col * CW
            cell_y0 = MYT + row * CH
            base_y = cell_y0 + HW3_BASELINE_Y

            # Sinh nét chữ giả lập có độ rộng ~8 pt, chiều cao ~8 pt nằm giữa xh và baseline
            # Ví dụ: chữ viết nằm từ x0 + 20 đến x0 + 28
            x1 = cell_x0 + 20.0
            x2 = cell_x0 + 24.0
            x3 = cell_x0 + 28.0
            y_base = base_y
            y_top = base_y - 8.0

            pts_str = f"{x1:.1f} {y_base:.1f} {x2:.1f} {y_top:.1f} {x3:.1f} {y_base:.1f}"

            stroke = ET.Element("stroke", {
                "tool": "pen",
                "color": color,
                "width": width,
            })
            stroke.text = pts_str
            layer.append(stroke)
            filled_count += 1

    save_xopp(out_path, [ET.tostring(root, encoding="unicode")])
    return filled_count
