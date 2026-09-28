"""Kiểm tra cơ chế khóa file liên tiến trình FileLock (chuviettay/model/file_lock.py)."""
from __future__ import annotations

import os

import pytest

from chuviettay.model.file_lock import FileLock, LockTimeoutError


def test_file_lock_acquire_va_release_co_ban(tmp_path):
    lock_file = str(tmp_path / "test.lock")
    with FileLock(lock_file, timeout=1.0) as lock:
        assert os.path.exists(lock_file)
        assert lock._f is not None
    # Sau khi thoát context manager, file handle đã đóng
    assert lock._f is None


def test_file_lock_tai_su_dung_nhieu_lan(tmp_path):
    lock_file = str(tmp_path / "test.lock")
    lock = FileLock(lock_file, timeout=1.0)
    with lock:
        pass
    with lock:
        pass


def test_file_lock_timeout_khi_bi_giu_khoa(tmp_path):
    lock_file = str(tmp_path / "test.lock")
    lock1 = FileLock(lock_file, timeout=1.0)
    lock2 = FileLock(lock_file, timeout=0.1, poll_interval=0.02)

    with lock1:
        # lock1 đang giữ khóa độc quyền, lock2 thử lấy sẽ bị timeout
        with pytest.raises(LockTimeoutError, match="Không thể khóa file"):
            with lock2:
                pass


def test_file_lock_tu_tao_thu_muc_cha_neu_chua_co(tmp_path):
    lock_file = str(tmp_path / "sub" / "dir" / "test.lock")
    with FileLock(lock_file, timeout=1.0):
        assert os.path.exists(lock_file)
