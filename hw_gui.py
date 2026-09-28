#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hw_gui.py -- giao diện đồ hoạ "Chữ viết tay của bạn" (Tkinter).

File này chỉ là LỐI VÀO mỏng, giữ nguyên tên và cách gọi như trước:
    python3 hw_gui.py
Toàn bộ mã nguồn nằm trong thư mục chuviettay/ (cùng chỗ với file này):
    chuviettay/gui.py   -> dựng cửa sổ + nối Controller với các tab
    chuviettay/view/    -> các tab giao diện
Đóng gói thành .exe/binary: xem build_windows.bat / build_linux_mac.sh.
"""
import sys

try:
    from chuviettay.gui import main
except ModuleNotFoundError as e:
    root = (e.name or "").split(".")[0]
    if root == "chuviettay":
        sys.exit("Không nạp được gói 'chuviettay'.\n"
                 "Hãy để thư mục chuviettay/ CÙNG CHỖ với file hw_gui.py rồi chạy lại.")
    if root in ("tkinter", "_tkinter"):
        sys.exit("Python của bạn chưa có tkinter (thư viện giao diện).\n"
                 "  Ubuntu/Debian:  sudo apt install python3-tk\n"
                 "  Windows/macOS:  cài lại Python từ python.org (đã kèm sẵn tkinter).")
    raise

if __name__ == "__main__":
    sys.exit(main())
