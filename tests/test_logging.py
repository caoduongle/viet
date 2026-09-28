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
