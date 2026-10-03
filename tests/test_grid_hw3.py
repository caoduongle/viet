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
    make_grid(grid_path, labels, bank, header="Lưới cũ hw2", calib=False, grid_version="hw2")

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


def test_make_letter_grid_standalone_tone_marks(tmp_path):
    bank = Bank.create_empty(str(tmp_path / "test_bank_tone.json.gz"))
    bank.xh = 7.94
    grid_path = str(tmp_path / "hw3_tone_grid.xopp")

    labels = ["a", "dấu sắc", "dấu nặng"]
    make_letter_grid(grid_path, labels, bank, target_xh=7.94)

    assert Path(grid_path).exists()
    root = read_xopp(grid_path)

    # Kiểm tra stroke mốc chữ o mờ màu #e8e8e8 xuất hiện trong các ô dấu thanh
    strokes = list(root.iter("stroke"))
    ghost_strokes = [st for st in strokes if (st.get("color") or "").lower()[:7] == "#e8e8e8"]
    assert len(ghost_strokes) >= 2  # ô dấu sắc và ô dấu nặng đều có chữ o mờ


def test_learn_standalone_tone_marks_into_bank(tmp_path):
    bank_path = str(tmp_path / "test_bank_learn.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.xh = 7.94
    grid_path = str(tmp_path / "hw3_tone_to_learn.xopp")

    labels = ["dấu sắc", "dấu nặng"]
    make_letter_grid(grid_path, labels, bank, target_xh=7.94)

    root = read_xopp(grid_path)
    page = root.find("page")
    layer = page.find("layer")

    # Ô (0, 0) là "dấu sắc": cell_x0 = 32, center x = 32 + 64 = 96
    # Baseline = 50 + 34 = 84. Vạch x-height = 84 - 7.94 = 76.06. Dấu sắc nằm phía trên: y khoảng [70, 74]
    sac_stroke = ET.Element("stroke", {
        "tool": "pen",
        "color": "#000000",
        "width": "1.41",
    })
    sac_stroke.text = "97.0 70.0 95.0 74.0"
    layer.append(sac_stroke)

    # Ô (1, 0) là "dấu nặng": col 1, cell_x0 = 32 + 128 = 160, center x = 160 + 64 = 224
    # Baseline = 50 + 34 = 84. Dấu nặng nằm dưới baseline: y khoảng [86, 87]
    nang_stroke = ET.Element("stroke", {
        "tool": "pen",
        "color": "#000000",
        "width": "1.41",
    })
    nang_stroke.text = "224.0 86.0 224.5 87.0"
    layer.append(nang_stroke)

    from chuviettay.model import xopp
    xopp.save_xopp(grid_path, [ET.tostring(root, encoding="unicode")])

    # Học mẫu từ file
    from chuviettay.model.learning import learn_from_files
    res = learn_from_files(bank, [grid_path])
    assert res.n_added == 2

    # bank.words không bị ô nhiễm bởi nhãn "dấu sắc" hay "dấu nặng"
    assert "dấu sắc" not in bank.words
    assert "dấu nặng" not in bank.words

    # bank.marks có mẫu dấu thanh rời
    sac_code = "\u0301"
    nang_code = "\u0323"
    assert len(bank.marks[sac_code]) >= 1
    assert len(bank.marks[nang_code]) >= 1

    sample_sac = bank.marks[sac_code][0]
    assert sample_sac.get("_src") == "standalone"
    # Dấu sắc có dy âm (nằm phía trên x-height)
    assert sample_sac["dy"] < 0
    # Dấu nặng có dy dương (nằm phía dưới baseline)
    sample_nang = bank.marks[nang_code][0]
    assert sample_nang["dy"] > 0


def test_learn_standalone_tone_rejects_traced_vowel(tmp_path):
    bank_path = str(tmp_path / "test_bank_guard.json.gz")
    bank = Bank.create_empty(bank_path)
    bank.xh = 7.94
    grid_path = str(tmp_path / "hw3_tone_guard.xopp")

    labels = ["dấu hỏi"]
    make_letter_grid(grid_path, labels, bank, target_xh=7.94)

    root = read_xopp(grid_path)
    page = root.find("page")
    layer = page.find("layer")

    # Giả lập người dùng vẽ đè một chữ o lớn (cao 8.0 pt) vào ô dấu hỏi
    traced_stroke = ET.Element("stroke", {
        "tool": "pen",
        "color": "#000000",
        "width": "1.41",
    })
    traced_stroke.text = "96.0 76.0 92.0 80.0 96.0 84.0 100.0 80.0 96.0 76.0"
    layer.append(traced_stroke)

    from chuviettay.model import xopp
    xopp.save_xopp(grid_path, [ET.tostring(root, encoding="unicode")])

    from chuviettay.model.learning import learn_from_files
    res = learn_from_files(bank, [grid_path])
    assert res.n_added == 0
    hoi_code = "\u0309"
    assert len(bank.marks[hoi_code]) == 0


def test_make_grid_generates_hw3_by_default(tmp_path):
    """Kiểm tra hàm make_grid mặc định sinh định dạng hw3 (4 đường kẻ mốc + 2 lề)."""
    bank = Bank.create_empty(str(tmp_path / "test_bank_default.json.gz"))
    bank.xh = 7.94
    grid_path = str(tmp_path / "default_hw3.xopp")

    from chuviettay.model.xopp import make_grid
    labels = ["từ_mới", "đoạn_văn"]
    make_grid(grid_path, labels, bank, header="Từ thiếu cần học", calib=False)

    root = read_xopp(grid_path)
    all_texts = [t.text for t in root.iter("text") if t.text]
    assert any(TAG_HW3 in t for t in all_texts)

    strokes = list(root.iter("stroke"))
    colors = set((st.get("color") or "").lower()[:7] for st in strokes)
    # Phải có màu các vạch kẻ chuẩn: mốc viền (#c8c8c8), chân chữ (#a0a0a0), vạch cao/thấp (#e0e0e0), lề (#d8d8d8)
    assert "#c8c8c8" in colors
    assert "#a0a0a0" in colors
    assert "#e0e0e0" in colors
    assert "#d8d8d8" in colors

