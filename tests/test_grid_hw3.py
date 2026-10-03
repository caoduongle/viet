"""
Tests for hw3 Handwriting Grid Generation and Ingestion:
- 4 guide lines (baseline, xh, ascender, descender) + 2 vertical margin boundaries
- Vietnamese instructions in header
- Digraph inclusion (ng, nh, ch...)
- Ingestion via parse_learn_file supporting both hw3 and legacy hw2/hw2c
"""
from pathlib import Path
import xml.etree.ElementTree as ET

from chuviettay.model.bank import Bank
from chuviettay.model.xopp import (
    HW3_ASCENDER_Y,
    HW3_BASELINE_Y,
    HW3_DESCENDER_Y,
    HW3_LEFT_MARGIN_X,
    HW3_RIGHT_MARGIN_X,
    TAG_HW3,
    TAG_PLAIN,
    make_letter_grid,
    parse_learn_file,
    read_xopp,
)


def test_make_letter_grid_hw3_guidelines(tmp_path):
    bank = Bank.create_empty(str(tmp_path / "test_bank.json.gz"))
    bank.xh = 7.94
    out_path = str(tmp_path / "test_hw3.xopp")

    labels = ["a", "b", "c", "ng", "nh"]
    make_letter_grid(out_path, labels, bank, target_xh=7.94)

    assert Path(out_path).exists()
    root = read_xopp(out_path)

    # Kiểm tra metadata tag hw3
    all_texts = [t.text for t in root.iter("text") if t.text]
    assert any(TAG_HW3 in t for t in all_texts)

    # Kiểm tra có hướng dẫn tiếng Việt rõ ràng
    instr_found = any("HƯỚNG DẪN" in t or "chữ thường" in t for t in all_texts)
    assert instr_found

    # Kiểm tra các đường kẻ mốc (guidelines)
    strokes = list(root.iter("stroke"))
    colors = set((st.get("color") or "").lower()[:7] for st in strokes)

    # Phải có màu các vạch kẻ chuẩn: mốc viền (#c8c8c8), chân chữ (#a0a0a0), vạch cao/thấp (#e0e0e0), lề (#d8d8d8)
    assert "#c8c8c8" in colors or "#a0a0a0" in colors


def test_parse_learn_file_hw3(tmp_path):
    bank = Bank.create_empty(str(tmp_path / "test_bank.json.gz"))
    bank.xh = 7.94
    grid_path = str(tmp_path / "hw3_to_learn.xopp")

    labels = ["a", "b"]
    make_letter_grid(grid_path, labels, bank, target_xh=7.94)

    # Thêm nét viết tay của người dùng vào ô đầu tiên (nhãn "a")
    root = read_xopp(grid_path)
    page = root.find("page")
    layer = page.find("layer")

    # Giả lập nét viết tay của người dùng (màu đen #000000, độ dày 1.41)
    # Tọa độ ô (0, 0): x nằm trong khoảng [32 + 12, 32 + 116], y quanh y0 + BASE = 60 + 34 = 94
    user_stroke = ET.Element("stroke", {
        "tool": "pen",
        "color": "#000000",
        "width": "1.41",
    })
    user_stroke.text = "50.0 94.0 55.0 87.0 60.0 94.0"
    layer.append(user_stroke)

    # Lưu lại file đã viết
    from chuviettay.model import xopp
    xopp.save_xopp(grid_path, [ET.tostring(root, encoding="unicode")])

    # Đọc lại bằng parse_learn_file
    cells, has_calib = parse_learn_file(grid_path)
    assert (0, 0, 0) in cells  # (page, col, row)
    raw_cell = cells[(0, 0, 0)]
    assert raw_cell.label == "a"
    assert len(raw_cell.strokes) == 1
    # Nét mốc kẻ không bị nhận nhầm thành nét viết tay
    assert raw_cell.strokes[0] == [50.0, 94.0, 55.0, 87.0, 60.0, 94.0]


def test_parse_learn_file_hw2_backward_compatibility(tmp_path):
    # Kiểm tra tính tương thích ngược với lưới hw2 cũ
    bank = Bank.create_empty(str(tmp_path / "test_bank_hw2.json.gz"))
    grid_path = str(tmp_path / "hw2_legacy.xopp")

    from chuviettay.model.xopp import make_grid
    labels = ["ba", "ma"]
    make_grid(grid_path, labels, bank, header="Lưới cũ hw2", calib=False)

    root = read_xopp(grid_path)
    page = root.find("page")
    layer = page.find("layer")

    # Thêm nét viết tay người dùng màu đen vào ô (0, 0)
    user_stroke = ET.Element("stroke", {
        "tool": "pen",
        "color": "#000000",
        "width": "1.41",
    })
    user_stroke.text = "50.0 94.0 55.0 87.0 60.0 94.0"
    layer.append(user_stroke)

    from chuviettay.model import xopp
    xopp.save_xopp(grid_path, [ET.tostring(root, encoding="unicode")])

    cells, has_calib = parse_learn_file(grid_path)
    assert (0, 0, 0) in cells
    raw_cell = cells[(0, 0, 0)]
    assert raw_cell.label == "ba"
    assert len(raw_cell.strokes) == 1
