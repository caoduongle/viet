"""Giúp pytest import được package `chuviettay` mà không cần cài đặt gì
(thư mục này -- gốc dự án -- được thêm vào sys.path)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
