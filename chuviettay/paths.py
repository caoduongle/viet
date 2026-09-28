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


def default_bank_path() -> str:
    return os.path.join(app_base_dir(), DEFAULT_BANK_FILENAME)
