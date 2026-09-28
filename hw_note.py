#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hw_note.py -- lệnh dòng lệnh "Chữ viết tay của bạn" (write / learn / seed / check / drop / stats).

File này chỉ là LỐI VÀO mỏng, giữ nguyên tên và cách gọi như trước:
    python hw_note.py write -f van_ban.txt -o ra.xopp
Toàn bộ mã nguồn nằm trong thư mục chuviettay/ (cùng chỗ với file này):
    chuviettay/cli.py  -> hướng dẫn dùng đầy đủ + các lệnh
"""
import sys

try:
    from chuviettay.cli import main
except ModuleNotFoundError as e:
    if (e.name or "").split(".")[0] != "chuviettay":
        raise
    sys.exit("Không nạp được gói 'chuviettay'.\n"
             "Hãy để thư mục chuviettay/ CÙNG CHỖ với file hw_note.py rồi chạy lại.")

if __name__ == "__main__":
    sys.exit(main())
