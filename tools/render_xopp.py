"""Công cụ kết xuất (render) file XOPP thành ảnh PNG độ phân giải cao.

Hỗ trợ:
- Đọc file .xopp (nén gzip hoặc XML thô).
- Vẽ các nét vector với độ dày nét bút, màu sắc và khớp nối bo tròn (curve joint).
- Tuỳ chọn cắt vùng (crop), tỉ lệ phóng đại (scale), và bỏ qua nét mốc định vị (guide strokes).
"""
from __future__ import annotations

import argparse
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw


def _read_xopp_xml(xopp_path: str | Path) -> str:
    path = Path(xopp_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    with open(path, "rb") as f:
        header = f.read(2)

    if header == b"\x1f\x8b":  # Gzip magic number
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as gz:
            return gz.read()
    else:
        with open(path, "rt", encoding="utf-8", errors="replace") as txt:
            return txt.read()


def render(
    xopp_path: str | Path,
    page_idx: int,
    out_png: str | Path,
    crop: tuple[float, float, float, float] | None = None,
    scale: float = 2.5,
    ignore_guides: bool = False,
    bg_color: str = "#ffffff",
) -> int:
    """Kết xuất một trang trong file .xopp thành file ảnh PNG.

    Args:
        xopp_path: Đường dẫn tới file .xopp.
        page_idx: Chỉ số trang cần vẽ (0-indexed).
        out_png: Đường dẫn file ảnh PNG đầu ra.
        crop: Vùng cắt (x0, y0, x1, y1) theo đơn vị point trong XOPP, hoặc None.
        scale: Tỉ lệ phóng đại pixel trên point (mặc định 2.5).
        ignore_guides: Nếu True, bỏ qua các nét mốc mờ định vị (#c8c8c8, #e0e0e0, #a0a0a0).
        bg_color: Màu nền (mặc định trắng).

    Returns:
        Tổng số trang trong tài liệu .xopp.
    """
    xml_content = _read_xopp_xml(xopp_path)
    root = ET.fromstring(xml_content)

    pages = root.findall(".//page")
    if not pages:
        # Một số file XML đặt <page> trực tiếp dưới root <xournal>
        pages = [elem for elem in root.iter("page")]

    if not pages:
        raise ValueError(f"Không tìm thấy thẻ <page> trong file: {xopp_path}")

    total_pages = len(pages)
    if page_idx < 0 or page_idx >= total_pages:
        raise IndexError(f"Chỉ số trang {page_idx} không hợp lệ (tổng số trang: {total_pages})")

    page_elem = pages[page_idx]
    w = float(page_elem.get("width", 595.28))
    h = float(page_elem.get("height", 841.89))

    img_w = max(1, int(round(w * scale)))
    img_h = max(1, int(round(h * scale)))

    im = Image.new("RGBA", (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(im)

    guide_colors = {"#c8c8c8", "#c8c8c8ff", "#e0e0e0", "#e0e0e0ff", "#a0a0a0", "#a0a0a0ff", "#d8d8d8", "#d8d8d8ff"}

    # Duyệt tất cả các nét trong trang
    for stroke_elem in page_elem.iter("stroke"):
        color_attr = stroke_elem.get("color", "#000000ff").lower()
        if ignore_guides and color_attr[:7] in {c[:7] for c in guide_colors}:
            continue

        raw_text = (stroke_elem.text or "").strip()
        if not raw_text:
            continue

        parts = raw_text.split()
        if len(parts) < 2:
            continue

        nums = [float(x) for x in parts]
        pts = [(nums[i] * scale, nums[i + 1] * scale) for i in range(0, len(nums) - 1, 2)]

        col = color_attr[:7]
        alpha = int(color_attr[7:9], 16) if len(color_attr) >= 9 else 255
        fill_color = col if alpha == 255 else (int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16), alpha)

        width_attr = float(stroke_elem.get("width", "1.41"))
        wd = max(1, int(round(width_attr * scale * 0.9)))

        if len(pts) > 1:
            draw.line(pts, fill=fill_color, width=wd, joint="curve")
        elif pts:
            x, y = pts[0]
            draw.ellipse([x - wd, y - wd, x + wd, y + wd], fill=fill_color)

    # Duyệt các nhãn text nếu có
    for text_elem in page_elem.iter("text"):
        raw_text = text_elem.text or ""
        tx = float(text_elem.get("x", 0)) * scale
        ty = float(text_elem.get("y", 0)) * scale
        draw.text((tx, ty), raw_text, fill="#808080")

    if crop:
        c_x0, c_y0, c_x1, c_y1 = crop
        crop_box = (
            max(0, int(round(c_x0 * scale))),
            max(0, int(round(c_y0 * scale))),
            min(img_w, int(round(c_x1 * scale))),
            min(img_h, int(round(c_y1 * scale))),
        )
        if crop_box[2] > crop_box[0] and crop_box[3] > crop_box[1]:
            im = im.crop(crop_box)

    out_p = Path(out_png)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out_p)
    return total_pages


def main() -> None:
    parser = argparse.ArgumentParser(description="Render file XOPP ra ảnh PNG.")
    parser.add_argument("xopp", help="Đường dẫn file .xopp")
    parser.add_argument("page", type=int, help="Chỉ số trang (0-indexed)")
    parser.add_argument("out", help="Đường dẫn file .png đầu ra")
    parser.add_argument("--scale", type=float, default=2.5, help="Tỉ lệ scale (mặc định 2.5)")
    parser.add_argument("--crop", nargs=4, type=float, metavar=("X0", "Y0", "X1", "Y1"), help="Toạ độ vùng cắt")
    parser.add_argument("--ignore-guides", action="store_true", help="Bỏ qua các nét kẻ mốc định vị")

    args = parser.parse_args()
    crop_tuple = tuple(args.crop) if args.crop else None
    pages = render(args.xopp, args.page, args.out, crop=crop_tuple, scale=args.scale, ignore_guides=args.ignore_guides)
    print(f"Đã render trang {args.page}/{pages} vào: {args.out}")


if __name__ == "__main__":
    main()
