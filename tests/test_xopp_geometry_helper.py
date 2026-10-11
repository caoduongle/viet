"""Tiện ích kiểm tra hình học và toạ độ nét vẽ trong tệp .xopp cho các bài test."""
from __future__ import annotations

import gzip
import os
import xml.etree.ElementTree as ET


def extract_xopp_pages_strokes(xopp_path: str) -> list[list[list[tuple[float, float]]]]:
    """Giải nén và trích xuất toạ độ tất cả các nét vẽ theo từng trang từ file .xopp.

    Returns:
        list các trang, mỗi trang là list các nét (stroke), mỗi nét là list các điểm (x, y).
    """
    if not os.path.exists(xopp_path):
        raise FileNotFoundError(f"Không tìm thấy file: {xopp_path}")

    with gzip.open(xopp_path, "rb") as f:
        xml_content = f.read().decode("utf-8")

    root = ET.fromstring(xml_content)
    pages_strokes: list[list[list[tuple[float, float]]]] = []

    for page in root.findall("page"):
        page_strokes: list[list[tuple[float, float]]] = []
        for stroke in page.iter("stroke"):
            text = (stroke.text or "").strip()
            if not text:
                continue
            coords = [float(val) for val in text.split()]
            points = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
            if points:
                page_strokes.append(points)
        pages_strokes.append(page_strokes)

    return pages_strokes


def assert_all_strokes_within_page_bounds(
    xopp_path: str,
    max_y: float,
    min_y: float = 0.0,
    min_x: float = 0.0,
    max_x: float | None = None,
) -> None:
    """Khẳng định 100% toạ độ điểm của mọi nét vẽ trong tệp .xopp nằm trong giới hạn trang in."""
    pages_strokes = extract_xopp_pages_strokes(xopp_path)
    assert len(pages_strokes) > 0, f"File {xopp_path} không có trang nào."

    for p_idx, strokes in enumerate(pages_strokes):
        for s_idx, pts in enumerate(strokes):
            for pt in pts:
                x, y = pt
                assert y <= max_y + 1e-3, (
                    f"Trang {p_idx}, nét {s_idx} có toạ độ y={y:.2f} vượt quá giới hạn đáy trang {max_y:.2f} pt."
                )
                assert y >= min_y - 1e-3, (
                    f"Trang {p_idx}, nét {s_idx} có toạ độ y={y:.2f} nhỏ hơn giới hạn đỉnh trang {min_y:.2f} pt."
                )
                assert x >= min_x - 1e-3, (
                    f"Trang {p_idx}, nét {s_idx} có toạ độ x={x:.2f} nhỏ hơn lề trái {min_x:.2f} pt."
                )
                if max_x is not None:
                    assert x <= max_x + 1e-3, (
                        f"Trang {p_idx}, nét {s_idx} có toạ độ x={x:.2f} vượt quá lề phải {max_x:.2f} pt."
                    )


def extract_strokes_in_bbox(
    strokes: list[list[tuple[float, float]]],
    bbox: tuple[float, float, float, float],
) -> list[list[tuple[float, float]]]:
    """Lọc các nét có ít nhất 1 điểm nằm trong bounding box (x, y, w, h)."""
    bx, by, bw, bh = bbox
    matched: list[list[tuple[float, float]]] = []
    for s in strokes:
        if any(bx <= pt[0] <= bx + bw and by <= pt[1] <= by + bh for pt in s):
            matched.append(s)
    return matched
