"""Khóa file liên tiến trình đa nền tảng (Windows + POSIX) dùng thư viện chuẩn Python.

Module này cung cấp FileLock context manager đảm bảo an toàn ghi đồng thời:
- Windows: dùng msvcrt.locking
- POSIX (Linux/macOS): dùng fcntl.flock
Không yêu cầu bất kỳ thư viện ngoài nào (zero third-party dependency).
"""
from __future__ import annotations

import os
import sys
import time
from typing import IO


class LockTimeoutError(RuntimeError):
    """Không lấy được khóa file sau khoảng thời gian chờ (timeout)."""


class FileLock:
    """Context manager khóa file độc quyền liên tiến trình (cross-process exclusive lock).

    Cách dùng:
        with FileLock("path/to/bank.json.gz.lock", timeout=10.0):
            # thao tác ghi an toàn
    """

    def __init__(self, lock_path: str, timeout: float = 10.0, poll_interval: float = 0.05):
        self.lock_path = lock_path
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._f: IO | None = None

    def acquire(self) -> None:
        start_time = time.monotonic()
        # Đảm bảo thư mục chứa file khóa tồn tại
        parent_dir = os.path.dirname(self.lock_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self._f = open(self.lock_path, "a+b")
        fd = self._f.fileno()

        while True:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    # Thử khóa 1 byte đầu tiên không chặn (LK_NBLCK)
                    self._f.seek(0)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    # Thử khóa độc quyền không chặn
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (OSError, IOError):
                if time.monotonic() - start_time >= self.timeout:
                    self.release()
                    raise LockTimeoutError(
                        f"Không thể khóa file '{self.lock_path}' sau {self.timeout:.1f}s. "
                        "Có tiến trình khác đang thao tác trên kho mẫu."
                    )
                time.sleep(self.poll_interval)

    def release(self) -> None:
        if self._f is not None:
            try:
                fd = self._f.fileno()
                if sys.platform == "win32":
                    import msvcrt
                    self._f.seek(0)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                try:
                    self._f.close()
                except OSError:
                    pass
                self._f = None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
