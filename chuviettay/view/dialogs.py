"""Hộp thoại báo lỗi dùng chung cho mọi tab.

Bản gốc ở mỗi nơi tự viết `except Exception as e: messagebox.showerror("Lỗi", str(e))`
-- chỉ còn lại đúng một dòng thông báo, MẤT HẲN traceback (lỗi ở dòng nào, hàm nào).
Ở đây mọi lỗi đều được ghi đầy đủ vào file log trước, rồi mới hiện hộp thoại kèm
đường dẫn file log để người dùng gửi lại khi cần hỗ trợ.
"""
from __future__ import annotations

import logging
from tkinter import messagebox

from chuviettay.logging_setup import log_path

_log = logging.getLogger("chuviettay.view")


def report_error(title: str, exc: BaseException, logger: logging.Logger | None = None) -> None:
    """Ghi traceback đầy đủ vào log rồi hiện hộp thoại lỗi."""
    (logger or _log).error("%s: %s", title, exc, exc_info=(type(exc), exc, exc.__traceback__))
    messagebox.showerror(title, "%s\n\nChi tiết kỹ thuật đã được ghi vào:\n%s" % (exc, log_path()))
