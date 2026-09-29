"""Kiểm tra cơ chế ghi log và fallback khi thư mục chính không có quyền ghi."""
from __future__ import annotations

import logging.handlers
import os

from chuviettay import logging_setup, paths


def test_user_log_dir_tra_ve_chuoi_hop_le():
    d = paths.user_log_dir()
    assert isinstance(d, str)
    assert len(d) > 0
    assert "chuviettay" in d.lower()


def test_logging_fallback_khi_primary_directory_loi(monkeypatch, tmp_path):
    # Reset cờ _configured để test chạy được
    monkeypatch.setattr(logging_setup, "_configured", False)
    monkeypatch.setattr(logging_setup, "_active_log_path", None)

    # Giả lập thư mục gốc read-only
    fake_fallback = str(tmp_path / "fallback_user_dir")
    monkeypatch.setattr(paths, "user_log_dir", lambda: fake_fallback)
    monkeypatch.setattr(logging_setup, "user_log_dir", lambda: fake_fallback)

    original_handler = logging.handlers.RotatingFileHandler

    def mock_rotating(filename, **kwargs):
        # Nếu cố ghi vào primary path thì ném OSError (giả lập PermissionError/read-only)
        if "fallback_user_dir" not in str(filename):
            raise OSError("Read-only filesystem")
        return original_handler(filename, **kwargs)

    monkeypatch.setattr("chuviettay.logging_setup.logging.handlers.RotatingFileHandler", mock_rotating)

    actual_path = logging_setup.configure_logging()
    assert "fallback_user_dir" in actual_path
    assert os.path.exists(actual_path)
    assert logging_setup.log_path() == actual_path


def test_logging_total_failure_returns_none(monkeypatch):
    monkeypatch.setattr(logging_setup, "_configured", False)
    monkeypatch.setattr(logging_setup, "_active_log_path", None)
    monkeypatch.setattr(logging_setup, "_logging_failed", False)

    def mock_fail(filename, **kwargs):
        raise OSError("Read-only filesystem")

    monkeypatch.setattr("chuviettay.logging_setup.logging.handlers.RotatingFileHandler", mock_fail)

    actual_path = logging_setup.configure_logging()
    assert actual_path is None
    assert logging_setup.log_path() is None


def test_report_error_with_no_log_path(monkeypatch):
    from chuviettay.view.dialogs import report_error

    monkeypatch.setattr("chuviettay.view.dialogs.log_path", lambda: None)
    called_boxes = []
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda title, msg: called_boxes.append((title, msg)))

    report_error("Lỗi test", ValueError("Chi tiết lỗi"))
    assert len(called_boxes) == 1
    assert called_boxes[0][0] == "Lỗi test"
    assert "Chi tiết lỗi" in called_boxes[0][1]
    assert "không hoạt động" in called_boxes[0][1]
    assert "None" not in called_boxes[0][1]

