"""Kiểm thử tính năng lưu hoãn (debounced save) và ghi nền bảo toàn luồng (User Story 7 - L14, v2.1)."""
import time
import pytest

from chuviettay.controller.app_controller import AppController
from chuviettay.model.bank import Bank


def test_teach_word_deferred_save_latency(tiny_bank_path):
    """L14: Dạy từ trực tiếp trong app phải phản hồi dưới 50ms nhờ cơ chế lưu hoãn (deferred save)."""
    ctl = AppController(tiny_bank_path)
    ctl.load_bank()

    # Thêm 100 từ giả lập để tăng dung lượng kho
    dummy_stroke = [[0, 0, 5, -10, 10, 0]]
    for i in range(100):
        ctl.bank.words[f"dummy_{i}"] = [{"s": dummy_stroke, "w": 10.0}]

    start_time = time.perf_counter()
    outcome = ctl.teach_word("từ_mới", dummy_stroke, 12.0, deferred_save=True)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert outcome.label == "từ_mới"
    assert duration_ms < 50.0, f"Dạy từ bị nghẽn UI: mất {duration_ms:.2f}ms (> 50ms)"
    assert ctl.bank.is_dirty, "Kho mẫu phải được đánh dấu 'dirty' sau khi dạy từ hoãn lưu"

    # Dọn dẹp: flush xuống đĩa
    ctl.flush_save()
    assert not ctl.bank.is_dirty


def test_debounce_timer_flushes_after_inactivity(tmp_path):
    """Sau thời gian nghỉ (inactivity debounce), thay đổi phải được tự động ghi xuống đĩa."""
    bank_path = str(tmp_path / "debounce_test.json.gz")
    Bank.create_empty(bank_path)

    ctl = AppController(bank_path)
    ctl.load_bank()
    ctl.debounce_delay = 0.2  # Đặt thời gian debounce ngắn (0.2s) cho kiểm thử

    dummy_stroke = [[0, 0, 5, -10, 10, 0]]
    ctl.teach_word("xác_nhận", dummy_stroke, 10.0, deferred_save=True)

    # Trước khi hết thời gian debounce: file trên đĩa chưa có từ mới
    disk_before = Bank(bank_path)
    assert "xác_nhận" not in disk_before.words

    # Chờ quá thời gian debounce (0.3s)
    time.sleep(0.35)

    # Sau khi debounce kích hoạt: file trên đĩa đã được cập nhật
    disk_after = Bank(bank_path)
    assert "xác_nhận" in disk_after.words
    assert not ctl.bank.is_dirty


def test_flush_save_synchronous_persistence(tmp_path):
    """flush_save ép ghi ngay lập tức xuống đĩa (dùng khi đổi tab hoặc đóng ứng dụng)."""
    bank_path = str(tmp_path / "flush_test.json.gz")
    Bank.create_empty(bank_path)

    ctl = AppController(bank_path)
    ctl.load_bank()
    ctl.debounce_delay = 5.0  # Đặt debounce rất dài (5.0s)

    dummy_stroke = [[0, 0, 5, -10, 10, 0]]
    ctl.teach_word("khẩn_cấp", dummy_stroke, 10.0, deferred_save=True)

    # Gọi flush_save chủ động
    ctl.flush_save()

    # Kiểm tra ngay lập tức trên đĩa
    disk = Bank(bank_path)
    assert "khẩn_cấp" in disk.words
    assert not ctl.bank.is_dirty


def test_save_compresslevel_optimization(tmp_path):
    """Bank.save sử dụng compresslevel=1 giúp tăng tốc độ nén mà không làm hỏng dữ liệu."""
    bank_path = str(tmp_path / "compress_test.json.gz")
    bank = Bank.create_empty(bank_path)

    dummy_stroke = [[0, 0, 5, -10, 10, 0]]
    for i in range(50):
        bank.add_sample(f"w_{i}", dummy_stroke, 10.0)

    bank.save()

    # Mở lại kiểm tra tính nguyên vẹn của gzip
    reloaded = Bank(bank_path)
    assert len(reloaded.words) == 50
