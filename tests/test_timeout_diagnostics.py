"""Kiểm thử chẩn đoán cơ chế ngắt tiến trình kiểm thử bằng watchdog timeout (pytest-timeout)."""
import subprocess
import sys
import pytest


def test_pytest_timeout_plugin_is_installed():
    """Xác nhận plugin pytest-timeout đã được cài đặt và tích hợp vào môi trường."""
    pytest_timeout = pytest.importorskip("pytest_timeout")
    assert pytest_timeout is not None


def test_watchdog_timeout_aborts_hanging_test_and_dumps_traceback(tmp_path):
    """Xác nhận test case chạy quá ngưỡng timeout sẽ bị watchdog ngắt ngay lập tức kèm traceback."""
    pytest.importorskip("pytest_timeout")

    hang_test_file = tmp_path / "test_hanging_probe.py"
    hang_test_file.write_text(
        "import time\n"
        "def test_hang():\n"
        "    time.sleep(5)\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(hang_test_file),
        "-vv",
        "-s",
        "--timeout=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    # Watchdog phải ngắt test khiến kết quả là FAILED (exit code 1)
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "Timeout" in combined or "test_hang" in combined
    assert "time.sleep" in combined or "Timeout" in combined
