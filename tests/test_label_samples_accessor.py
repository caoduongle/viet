"""Kiểm thử accessor chỉ-đọc list_label_samples ở AppController (thay đổi lõi 3.3).
Hỗ trợ web frontend dựng thư viện mẫu (xem từng mẫu của từ/chữ cái/số/dấu/ký hiệu).
"""
from __future__ import annotations

import copy
import pytest

from chuviettay.controller.app_controller import AppController


def test_list_label_samples_nonexistent_returns_empty(tmp_path):
    """Nhãn không tồn tại trong kho trả về danh sách rỗng."""
    bank_path = str(tmp_path / "bank.json.gz")
    ctl = AppController(bank_path)
    ctl.load_bank(bank_path, create_if_missing=True)

    samples = ctl.list_label_samples("tu_chua_day", category="words")
    assert samples == []


def test_list_label_samples_returns_copy(tmp_path):
    """Accessor trả về bản sao dữ liệu: sửa kết quả trả về không làm thay đổi kho trong bộ nhớ."""
    bank_path = str(tmp_path / "bank.json.gz")
    ctl = AppController(bank_path)
    bank = ctl.load_bank(bank_path, create_if_missing=True)

    # Thêm một mẫu từ
    bank.words["hoa"] = [
        {"w": 12.5, "s": [[0.0, 0.0, 5.0, -10.0], [5.0, 0.0, 10.0, 0.0]], "T": "", "vi": -1, "ti": -1}
    ]

    samples = ctl.list_label_samples("hoa", category="words")
    assert len(samples) == 1
    assert samples[0]["w"] == 12.5

    # Mutate bản sao
    samples[0]["w"] = 99.9
    samples[0]["s"].append([1.0, 2.0])

    # Kiểm tra kho gốc không bị ảnh hưởng
    assert bank.words["hoa"][0]["w"] == 12.5
    assert len(bank.words["hoa"][0]["s"]) == 2


def test_list_label_samples_all_categories(tmp_path):
    """Kiểm tra accessor hoạt động trên tất cả các phân loại: words, letters, digits, punct, symbols, marks."""
    bank_path = str(tmp_path / "bank.json.gz")
    ctl = AppController(bank_path)
    bank = ctl.load_bank(bank_path, create_if_missing=True)

    bank.letters["a"] = [{"w": 8.0, "s": [[0.0, 0.0, 8.0, 0.0]], "T": "", "vi": -1, "ti": -1}]
    bank.digits["5"] = [{"w": 6.0, "s": [[0.0, 0.0, 6.0, 0.0]], "T": "", "vi": -1, "ti": -1}]
    bank.punct["?"] = [{"w": 4.0, "s": [[0.0, 0.0, 4.0, 0.0]], "T": "", "vi": -1, "ti": -1}]
    bank.symbols["+"] = [{"w": 5.0, "s": [[0.0, 0.0, 5.0, 0.0]], "T": "", "vi": -1, "ti": -1}]
    bank.marks["sắc"] = [{"w": 3.0, "s": [[0.0, 0.0, 3.0, 3.0]], "T": "sắc", "vi": -1, "ti": -1}]

    assert len(ctl.list_label_samples("a", category="letters")) == 1
    assert len(ctl.list_label_samples("5", category="digits")) == 1
    assert len(ctl.list_label_samples("?", category="punct")) == 1
    assert len(ctl.list_label_samples("+", category="symbols")) == 1
    assert len(ctl.list_label_samples("sắc", category="marks")) == 1

    # Thử category không hợp lệ
    with pytest.raises(ValueError, match="Không hỗ trợ phân loại"):
        ctl.list_label_samples("a", category="invalid_cat")
