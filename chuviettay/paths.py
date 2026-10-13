"""
Tính thư mục/đường dẫn mặc định của kho mẫu (chu_cua_ban.json.gz) và thư mục log.
"""
from __future__ import annotations

import os
import sys

DEFAULT_BANK_FILENAME = "chu_cua_ban.json.gz"


def app_base_dir() -> str:
    """Thư mục gốc mã nguồn của ứng dụng."""
    # paths.py nằm trong chuviettay/, thư mục gốc ứng dụng là một cấp cha của nó
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_data_dir() -> str:
    """Thư mục lưu trữ dữ liệu người dùng chuẩn theo hệ điều hành:
    - Windows: %APPDATA%/chuviettay
    - macOS:   ~/Library/Application Support/chuviettay
    - Linux:   $XDG_DATA_HOME/chuviettay (mặc định ~/.local/share/chuviettay)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "chuviettay")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/chuviettay")
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(xdg, "chuviettay")


def default_bank_path() -> str:
    """Đường dẫn kho mẫu mặc định (chu_cua_ban.json.gz) theo thứ tự ưu tiên:
    1. Chạy từ mã nguồn nếu file đã tồn tại ở app_base_dir() -> giữ hành vi portable cục bộ.
    2. Thư mục dữ liệu người dùng của OS (khi cài bằng pip hoặc chưa có kho cục bộ).
    """
    local_path = os.path.join(app_base_dir(), DEFAULT_BANK_FILENAME)
    if os.path.exists(local_path):
        return local_path
    return os.path.join(user_data_dir(), DEFAULT_BANK_FILENAME)


def user_log_dir() -> str:
    """Thư mục ghi log dự phòng trong thư mục dữ liệu cá nhân của người dùng (OS user data)."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Chuviettay")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Logs/Chuviettay")
    state = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(state, "chuviettay")
