"""Lớp Controller: điều phối giữa Model và giao diện (CLI hoặc GUI).

Quy tắc: không import tkinter, không import argparse, không gọi print()/input().
Nhận tham số dạng dữ liệu thuần (str, số, list, dataclass), trả về dataclass. Xem
app_controller.py -- đây là điểm vào DUY NHẤT mà cli.py và view/ nên gọi tới; cả hai
không tự ý thao tác thẳng vào Bank/Writer.
"""
