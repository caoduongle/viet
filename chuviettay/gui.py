#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gui.py -- điểm vào giao diện đồ hoạ: dựng AppController + MainWindow rồi chạy mainloop().

    python3 hw_gui.py                 # mở app
    python3 hw_gui.py -v              # ghi log chi tiết + in ra console (để tìm lỗi)
    python3 hw_gui.py --bank D:\\kho_khac.json.gz   # mở thẳng một kho mẫu khác

Cần Python 3 có tkinter:
    Ubuntu/Debian:  sudo apt install python3-tk
    Windows/macOS:  thường có sẵn trong bản cài Python từ python.org
"""
from __future__ import annotations

import argparse
import logging

from chuviettay.controller.app_controller import AppController
from chuviettay.logging_setup import configure_logging
from chuviettay.view.app_window import MainWindow

_log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Giao diện đồ hoạ 'Chữ viết tay của bạn'.")
    parser.add_argument("--bank", default=None,
                        help="đường dẫn kho mẫu (mặc định: chu_cua_ban.json.gz cạnh chương trình)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="ghi log chi tiết (DEBUG) và in ra console -- dùng khi cần tìm lỗi")
    args = parser.parse_args(argv)

    configure_logging(verbose=args.verbose)
    ctl = AppController(args.bank)
    app = MainWindow(ctl)
    _log.info("Cửa sổ chính đã sẵn sàng")
    app.mainloop()
    _log.info("Đã thoát")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
