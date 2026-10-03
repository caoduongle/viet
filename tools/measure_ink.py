"""Công cụ đo lường khách quan các chỉ số hình học nét vẽ từ file XOPP.

Đo đạc:
- x-height thực tế (phân vị và phát hiện theo dòng).
- Độ dày bút và tỉ lệ pen_thickness / x-height.
- Khoảng cách ngang giữa các chữ trong từ và giữa các từ.
- Tỉ lệ chồng lấn bounding box và khoảng cách nét gần nhất (khe tối thiểu).
- Độ lệch chuẩn chiều cao nhóm chữ.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET


def _read_xopp_xml(xopp_path: str | Path) -> str:
    path = Path(xopp_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    with open(path, "rb") as f:
        header = f.read(2)

    if header == b"\x1f\x8b":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as gz:
            return gz.read()
    else:
        with open(path, "rt", encoding="utf-8", errors="replace") as txt:
            return txt.read()


class StrokeData:
    __slots__ = ("pts", "min_x", "min_y", "max_x", "max_y", "w", "h", "width", "color")

    def __init__(self, pts: list[tuple[float, float]], width: float, color: str):
        self.pts = pts
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.min_x = min(xs)
        self.min_y = min(ys)
        self.max_x = max(xs)
        self.max_y = max(ys)
        self.w = self.max_x - self.min_x
        self.h = self.max_y - self.min_y
        self.width = width
        self.color = color


def parse_strokes_from_xopp(
    xopp_path: str | Path,
    page_idx: int | None = None,
    ignore_guides: bool = True,
) -> list[StrokeData]:
    xml_content = _read_xopp_xml(xopp_path)
    root = ET.fromstring(xml_content)

    pages = root.findall(".//page") or [e for e in root.iter("page")]
    if not pages:
        return []

    target_pages = [pages[page_idx]] if page_idx is not None else pages
    guide_colors = {"#c8c8c8", "#c8c8c8ff", "#e0e0e0", "#e0e0e0ff", "#a0a0a0", "#a0a0a0ff", "#d8d8d8", "#d8d8d8ff"}

    all_strokes: list[StrokeData] = []
    for p in target_pages:
        for s_elem in p.iter("stroke"):
            color = s_elem.get("color", "#000000ff").lower()
            if ignore_guides and color[:7] in {c[:7] for c in guide_colors}:
                continue

            text = (s_elem.text or "").strip()
            if not text:
                continue

            parts = text.split()
            if len(parts) < 2:
                continue

            nums = [float(v) for v in parts]
            pts = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
            if not pts:
                continue

            stroke_w = float(s_elem.get("width", "1.41"))
            all_strokes.append(StrokeData(pts, stroke_w, color))

    return all_strokes


def cluster_into_lines(strokes: list[StrokeData], max_y_gap: float = 12.0) -> list[list[StrokeData]]:
    """Gom nhóm nét theo từng dòng văn bản dựa trên toạ độ y tâm nét."""
    if not strokes:
        return []

    # Lọc bỏ nét bảng quá dài hoặc nét quá dị biệt
    text_strokes = [s for s in strokes if s.w < 350.0 and s.h < 80.0]
    if not text_strokes:
        text_strokes = strokes

    # Sắp xếp theo y_mid
    sorted_strokes = sorted(text_strokes, key=lambda s: (s.min_y + s.max_y) / 2.0)

    lines: list[list[StrokeData]] = []
    current_line: list[StrokeData] = [sorted_strokes[0]]
    current_line_y = (sorted_strokes[0].min_y + sorted_strokes[0].max_y) / 2.0

    for s in sorted_strokes[1:]:
        s_y = (s.min_y + s.max_y) / 2.0
        if abs(s_y - current_line_y) <= max_y_gap:
            current_line.append(s)
            current_line_y = sum((st.min_y + st.max_y) / 2.0 for st in current_line) / len(current_line)
        else:
            lines.append(sorted(current_line, key=lambda st: st.min_x))
            current_line = [s]
            current_line_y = s_y

    if current_line:
        lines.append(sorted(current_line, key=lambda st: st.min_x))

    return lines


def estimate_xheight_from_strokes(strokes: list[StrokeData]) -> tuple[float, float]:
    """Ước lượng x-height và độ lệch chuẩn từ phân bố chiều cao các nét chữ thường.

    Chữ thường nằm trong khoảng chiều cao loại bỏ dấu nhỏ (<2.5pt) và nét cao (>16pt).
    """
    letter_heights = [s.h for s in strokes if 2.5 <= s.h <= 18.0 and s.w <= 40.0]
    if not letter_heights:
        return (8.6, 1.5)

    # Phân vị 25% đến 60% của các nét chữ thường phản ánh chính xác nhất x-height
    # (vì các nét cao của ascender đẩy trung bình lên cao)
    sorted_h = sorted(letter_heights)
    n = len(sorted_h)
    p50 = sorted_h[int(n * 0.50)]

    # Ước lượng x-height quanh phân vị trung vị của nhóm chữ thấp
    xh = p50
    # Lấy tập các nét x-height xung quanh phân vị này để đo std dev
    xh_group = [h for h in letter_heights if abs(h - xh) <= 0.4 * xh]
    std_dev = statistics.stdev(xh_group) if len(xh_group) > 1 else 1.0

    return (round(xh, 2), round(std_dev, 2))


def min_distance_between_strokes(s1: StrokeData, s2: StrokeData) -> float:
    """Tính khoảng cách Euclidean nhỏ nhất giữa 2 nét (tối ưu hóa tập điểm biên)."""
    # Lấy 15 điểm thuộc mép phải của s1 và mép trái của s2
    pts1 = s1.pts[-25:] if len(s1.pts) > 25 else s1.pts
    pts2 = s2.pts[:25] if len(s2.pts) > 25 else s2.pts

    min_sq = float("inf")
    for x1, y1 in pts1:
        for x2, y2 in pts2:
            dx = x2 - x1
            dy = y2 - y1
            sq = dx * dx + dy * dy
            if sq < min_sq:
                min_sq = sq
    return math.sqrt(min_sq)


def measure_ink_metrics(
    xopp_path: str | Path,
    page_idx: int | None = None,
    ignore_guides: bool = True,
) -> dict[str, float | int | str]:
    strokes = parse_strokes_from_xopp(xopp_path, page_idx=page_idx, ignore_guides=ignore_guides)
    if not strokes:
        return {
            "source_file": str(xopp_path),
            "stroke_count": 0,
            "median_x_height": 0.0,
            "pen_thickness": 0.0,
            "pen_to_xh_ratio": 0.0,
            "median_letter_gap": 0.0,
            "median_word_gap": 0.0,
            "max_bbox_overlap_pct": 0.0,
            "min_stroke_clearance_pt": 0.0,
            "min_stroke_clearance_pen": 0.0,
            "xh_std_dev": 0.0,
        }

    # Đo độ dày bút (phân vị trung vị của trường width)
    widths = [s.width for s in strokes]
    median_pen_w = statistics.median(widths) if widths else 1.41

    # Ước lượng x-height và độ lệch chuẩn
    xh, xh_std = estimate_xheight_from_strokes(strokes)
    pen_ratio = median_pen_w / xh if xh > 0 else 0.0

    lines = cluster_into_lines(strokes)

    letter_gaps: list[float] = []
    word_gaps: list[float] = []
    overlap_pcts: list[float] = []
    clearances_pt: list[float] = []

    for line in lines:
        if len(line) < 2:
            continue
        for i in range(len(line) - 1):
            s1 = line[i]
            s2 = line[i + 1]

            # Bỏ qua nếu là các nét thuộc cùng một ký tự (nét dấu trên/dưới hoặc nét phụ chồng lên nhau)
            is_vertical_diacritic = (
                (s2.max_y <= s1.min_y + 3.0)
                or (s1.max_y <= s2.min_y + 3.0)
                or abs((s1.min_x + s1.max_x) / 2 - (s2.min_x + s2.max_x) / 2) < 4.5
            )
            if is_vertical_diacritic:
                continue

            h_gap = s2.min_x - s1.max_x
            if h_gap > 0:
                if h_gap < 1.2 * xh:
                    letter_gaps.append(h_gap)
                else:
                    word_gaps.append(h_gap)
            else:
                # Có chồng lấn bounding box
                overlap_w = min(s1.max_x, s2.max_x) - max(s1.min_x, s2.min_x)
                narrower = min(s1.w, s2.w)
                if narrower > 0.5:
                    pct = (overlap_w / narrower) * 100.0
                    overlap_pcts.append(pct)

            # Đo khoảng cách thực tế giữa các nét liền kề
            if -3.0 <= (s2.min_x - s1.max_x) <= 12.0:
                dist = min_distance_between_strokes(s1, s2)
                clearances_pt.append(dist)

    med_letter_gap = statistics.median(letter_gaps) if letter_gaps else 0.0
    med_word_gap = statistics.median(word_gaps) if word_gaps else 0.0
    max_overlap = max(overlap_pcts) if overlap_pcts else 0.0
    min_clearance = min(clearances_pt) if clearances_pt else 0.0
    min_clearance_pen = min_clearance / median_pen_w if median_pen_w > 0 else 0.0

    return {
        "source_file": Path(xopp_path).name,
        "stroke_count": len(strokes),
        "median_x_height": round(xh, 2),
        "pen_thickness": round(median_pen_w, 2),
        "pen_to_xh_ratio": round(pen_ratio, 3),
        "median_letter_gap": round(med_letter_gap, 2),
        "median_word_gap": round(med_word_gap, 2),
        "max_bbox_overlap_pct": round(max_overlap, 1),
        "min_stroke_clearance_pt": round(min_clearance, 2),
        "min_stroke_clearance_pen": round(min_clearance_pen, 2),
        "xh_std_dev": round(xh_std, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Đo số liệu hình học nét mực từ file XOPP.")
    parser.add_argument("xopp", help="Đường dẫn file .xopp")
    parser.add_argument("--page", type=int, default=None, help="Chỉ đo một trang cụ thể (0-indexed)")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả định dạng JSON")
    parser.add_argument("--no-ignore-guides", dest="ignore_guides", action="store_false", help="Không bỏ qua nét mốc")

    args = parser.parse_args()
    results = measure_ink_metrics(args.xopp, page_idx=args.page, ignore_guides=args.ignore_guides)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n=== BÁO CÁO ĐO LƯỜNG NÉT MỰC: {results['source_file']} ===")
        print(f"- Tổng số nét phân tích: {results['stroke_count']}")
        print(f"- x-height thực tế (trung vị): {results['median_x_height']} pt")
        print(f"- Độ dày bút vẽ: {results['pen_thickness']} pt")
        print(f"- Tỉ lệ [độ dày bút / x-height]: {results['pen_to_xh_ratio']} ({round(results['pen_to_xh_ratio']*100, 1)}%)")
        print(f"- Khoảng cách trong từ (trung vị): {results['median_letter_gap']} pt")
        print(f"- Khoảng cách giữa các từ (trung vị): {results['median_word_gap']} pt")
        print(f"- Tỉ lệ chồng bbox lớn nhất: {results['max_bbox_overlap_pct']}%")
        print(f"- Khe hở nét nhỏ nhất: {results['min_stroke_clearance_pt']} pt ({results['min_stroke_clearance_pen']}x độ dày bút)")
        print(f"- Độ lệch chuẩn x-height: {results['xh_std_dev']} pt\n")


if __name__ == "__main__":
    main()
