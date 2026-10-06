"""Kiểm thử nạp file lưới tập viết (.xopp) tạo kho mẫu ký tự và tái hiện lỗi F2."""
from __future__ import annotations

from pathlib import Path
import pytest

from chuviettay.model.bank import Bank
from chuviettay.model.xopp import make_letter_grid, parse_learn_file
from tests.helpers import fill_grid_with_ink


def test_repro_f2_bearing_cell_margin_causes_spacing_bug(tmp_path):
    """Tái hiện F2: parse_learn_file tính lsb/rsb theo vạch lề HW3_LEFT_MARGIN_X (12.0)
    và HW3_RIGHT_MARGIN_X (116.0), dẫn tới bearing lên tới 30-80 pt khiến chữ bị giãn 10 lần.
    
    Kỳ vọng sau khi sửa F2:
    - lsb và rsb được tính theo bounding box nét vẽ hoặc contour hợp lý (nhỏ hơn 0.3 * xh).
    """
    bank = Bank.create_empty(str(tmp_path / "test_bank.json.gz"))
    bank.xh = 8.0
    grid_path = str(tmp_path / "grid_a.xopp")
    grid_ink_path = str(tmp_path / "grid_a_ink.xopp")

    make_letter_grid(grid_path, ["a"], bank, target_xh=8.0, include_digraphs=False, include_tones=False)
    fill_grid_with_ink(grid_path, grid_ink_path, labels=["a"])

    cells, _ = parse_learn_file(grid_ink_path)
    assert (0, 0, 0) in cells
    cell_a = cells[(0, 0, 0)]

    # TRƯỚC KHI SỬA F2:
    # nét vẽ ở x = cell_x0 + 20..28
    # HW3_LEFT_MARGIN_X = 12.0 -> lsb = 20 - 12 = 8.0 (bằng cả x-height!)
    # HW3_RIGHT_MARGIN_X = 116.0 -> rsb = 116 - 28 = 88.0 (gấp 11 lần x-height!)
    # Điều này khiến chữ bị giãn cách hàng chục lần.
    # BÀI TEST NÀY KIỂM TRA RẰNG BEARING KHÔNG ĐƯỢC VƯỢT QUÁ 0.3 * xh (2.4 pt)
    assert cell_a.lsb <= 0.3 * bank.xh, f"Lỗi F2: lsb = {cell_a.lsb} quá lớn so với xh = {bank.xh}"
    assert cell_a.rsb <= 0.3 * bank.xh, f"Lỗi F2: rsb = {cell_a.rsb} quá lớn so với xh = {bank.xh}"


def test_import_char_grid_exists_and_returns_result(tmp_path):
    """Kiểm tra sự tồn tại của hàm import_char_grid và trả về GridImportResult."""
    from chuviettay.model import xopp
    assert hasattr(xopp, "import_char_grid"), "xopp thiếu hàm import_char_grid"
    assert hasattr(xopp, "GridImportResult"), "xopp thiếu dataclass GridImportResult"
