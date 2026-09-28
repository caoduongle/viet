"""
Thiết lập ghi log ra file -- PHẦN BỔ SUNG MỚI so với bản gốc, nhắm đúng vào yêu cầu
"dễ debug".

Bản gốc chỉ có print() (CLI) và messagebox.showerror(str(e)) (GUI) -- messagebox chỉ
hiện ĐÚNG một dòng thông báo lỗi, traceback đầy đủ (dòng nào, hàm nào gây lỗi) bị mất
hoàn toàn. Với bản .exe đóng gói kiểu --windowed (không có cửa sổ console), đây gần
như là NGÕ CỤT khi cần tìm lỗi -- người dùng chỉ báo được "nó báo lỗi ..." mà không có
gì để lần ra nguyên nhân.

Module này ghi log ra một file văn bản CẠNH ứng dụng (chuviettay.log), xoay vòng khi
quá lớn, dùng chung cho cả CLI lẫn GUI. Khi có lỗi, traceback đầy đủ được ghi vào đây
-- người dùng chỉ cần gửi file này kèm mô tả lỗi là đủ để debug từ xa.

Chế độ chi tiết: chạy với cờ -v/--verbose (cả hw_note.py lẫn hw_gui.py) để ghi log mức
DEBUG và in thẳng ra màn hình console (stderr) -- tiện khi đang phát triển/tìm lỗi.
Mặc định CLI KHÔNG in log ra console để đầu ra của lệnh (stdout) giữ nguyên như trước.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys

from chuviettay.paths import app_base_dir

LOG_FILENAME = "chuviettay.log"
_configured = False


def log_path() -> str:
    return os.path.join(app_base_dir(), LOG_FILENAME)


def configure_logging(verbose: bool = False, console: bool | None = None) -> str:
    """Bật ghi log (idempotent -- gọi nhiều lần chỉ thiết lập một lần). Trả về đường
    dẫn file log, để hiển thị cho người dùng khi cần (ví dụ trong hộp thoại lỗi:
    "chi tiết đã được ghi vào <đường dẫn>").

    verbose: ghi cả mức DEBUG (mặc định chỉ INFO trở lên).
    console: có in log ra stderr không (mặc định: chỉ khi verbose).
    """
    global _configured
    path = log_path()
    if _configured:
        return path
    _configured = True

    if console is None:
        console = verbose
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        # Thư mục chỉ đọc / không có quyền ghi -- vẫn chạy tiếp được, chỉ là không có
        # file log. Không để lỗi ghi log làm sập cả ứng dụng.
        pass

    if console and sys.stderr is not None:     # .exe --windowed trên Windows: không có stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(fmt)
        root.addHandler(handler)

    logging.getLogger(__name__).info("=== Khởi động chuviettay (log tại: %s) ===", path)
    return path
