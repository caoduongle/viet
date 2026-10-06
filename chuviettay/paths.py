"""
Tính thư mục/đường dẫn mặc định của kho mẫu (chu_cua_ban.json.gz).

VÌ SAO CẦN XỬ LÝ RIÊNG TRƯỜNG HỢP "ĐÃ ĐÓNG GÓI" (PyInstaller --onefile):
Khi chạy bằng `python3 hw_gui.py`, __file__ trỏ đúng tới nơi có mã nguồn -- kho mẫu
mặc định nên nằm CẠNH thư mục đó (cùng thư mục với hw_gui.py/hw_note.py).

Khi đã đóng gói thành .exe/binary bằng PyInstaller (--onefile), chương trình mỗi lần
chạy sẽ tự giải nén mã nguồn ra một thư mục TẠM (sys._MEIPASS) rồi mới chạy -- thư mục
đó bị xoá sau khi thoát app. Nếu lấy __file__ lúc này sẽ trỏ vào thư mục tạm đó, ĐỌC
ĐƯỢC lúc chạy nhưng kho mẫu sẽ "biến mất" ở lần chạy sau (vì bị xoá cùng thư mục tạm).
Phải dùng sys.executable (đường dẫn tới chính file .exe đang chạy) để kho mẫu nằm ở
một nơi ỔN ĐỊNH, LÂU DÀI -- cạnh file .exe thật.

Việc đọc mã nguồn (package chuviettay) khi đã đóng gói KHÔNG cần xử lý riêng gì thêm:
PyInstaller tự đóng gói toàn bộ package vào bên trong .exe và tự lo việc import, đây
chỉ là vấn đề của DỮ LIỆU (kho mẫu) cần đọc/ghi lâu dài, không phải của mã nguồn.
"""
from __future__ import annotations

import os
import sys

DEFAULT_BANK_FILENAME = "chu_cua_ban.json.gz"


def app_base_dir() -> str:
    """Thư mục coi là 'gốc ứng dụng' để tìm/tạo kho mẫu mặc định."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # paths.py nằm trong chuviettay/, thư mục gốc ứng dụng là một cấp cha của nó
    # (nơi có hw_gui.py, hw_note.py, chu_cua_ban.json.gz).
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
    1. Đã đóng gói (sys.frozen) -> luôn cạnh file .exe.
    2. Chạy từ mã nguồn nếu file đã tồn tại ở app_base_dir() -> giữ hành vi portable.
    3. Thư mục dữ liệu người dùng của OS (khi cài bằng pip hoặc chưa có kho cục bộ).
    """
    if getattr(sys, "frozen", False):
        return os.path.join(app_base_dir(), DEFAULT_BANK_FILENAME)
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


def user_config_path() -> str:
    """Đường dẫn tệp cấu hình tùy chọn người dùng (user_config.json)."""
    return os.path.join(user_data_dir(), "user_config.json")


def load_user_config() -> dict:
    """Đọc tệp cấu hình người dùng, trả về dict rỗng nếu chưa tồn tại hoặc lỗi đọc."""
    cfg_file = user_config_path()
    if not os.path.isfile(cfg_file):
        return {}
    try:
        import json
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_user_config(config: dict) -> None:
    """Lưu tệp cấu hình người dùng an toàn nguyên tử."""
    cfg_file = user_config_path()
    os.makedirs(os.path.dirname(os.path.abspath(cfg_file)), exist_ok=True)
    tmp_file = f"{cfg_file}.tmp"
    import json
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, cfg_file)
