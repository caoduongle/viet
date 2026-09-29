#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hw_note.py - Gõ chữ, ra NÉT VIẾT TAY CỦA BẠN cho Xournal++ (học từ ghi chú của bạn).

DÙNG HẰNG NGÀY
    python hw_note.py write -f van_ban.txt -o ra.xopp
      -> mở ra.xopp, Ctrl+A, Ctrl+C, dán (Ctrl+V) vào sổ rồi kéo về đúng chỗ.
      Từ nào chưa có mẫu sẽ được liệt kê và ghi vào file ra_thieu.xopp.

DẠY THÊM TỪ MỚI (chỉ cần làm 1 lần cho mỗi từ)
    mở ra_thieu.xopp -> viết từng từ vào ô (giữa hai đường kẻ) -> Ctrl+S
    python hw_note.py learn ra_thieu.xopp
      -> chạy lại lệnh write ở trên là đủ chữ.

LỆNH KHÁC
    python hw_note.py seed 200    # tạo mau_pho_bien.xopp: 200 từ tiếng Việt thông dụng còn thiếu
    python hw_note.py check       # tạo kiem_tra.xopp: xem lại toàn bộ chữ đã học (kèm chữ gõ)
    python hw_note.py drop từ ...  # xóa mẫu bị sai khỏi kho
    python hw_note.py stats       # thống kê kho mẫu

Tùy chỉnh khi write: --scale 1.1 (to hơn 10%), --line 24, --width 500, --space 1.0,
--jitter 1.0 (độ "run tay", 0 = tắt), --seed 5 (cố định ngẫu nhiên), --color #1a237e.
Chỉ dùng thư viện chuẩn của Python 3. Kho mẫu: chu_cua_ban.json.gz (cùng thư mục).

TÌM LỖI:  python hw_note.py -v <lệnh> ...   (ghi log chi tiết + in ra màn hình;
          log luôn được ghi vào file chuviettay.log cạnh chương trình)

--------------------------------------------------------------------------------
Về mặt kiến trúc, file này là lớp "mỏng": chỉ đọc tham số dòng lệnh, gọi
AppController (controller/app_controller.py) rồi in kết quả. Mọi logic nghiệp vụ
nằm ở Controller/Model để dùng chung với giao diện đồ hoạ (gui.py).
"""
from __future__ import annotations

import argparse
import logging
import sys

from chuviettay import paths
from chuviettay.controller.app_controller import AppController, BankError
from chuviettay.controller.results import WriteOptions
from chuviettay.formatting import write_report_lines
from chuviettay.logging_setup import configure_logging

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------- các lệnh
# Mỗi hàm: nhận (controller, args đã parse), gọi Controller, in kết quả ra màn hình.
def _read_text(a: argparse.Namespace) -> str:
    """Nguồn văn bản cho lệnh write: file (-f), hoặc gõ thẳng (-t), hoặc đọc stdin."""
    if a.file:
        with open(a.file, encoding="utf-8-sig") as f:
            return f.read()
    if a.text:
        return a.text
    return sys.stdin.read()


def _cmd_write(ctl: AppController, a: argparse.Namespace) -> None:
    text = _read_text(a)
    opts = WriteOptions(
        scale=a.scale, line=a.line, width=a.width, space=a.space, jitter=a.jitter,
        wscale=a.wscale, color=a.color, seed=a.seed, strict_case=a.strict_case)
    result = ctl.write_text(text, opts, a.out)
    for line in write_report_lines(result):
        print(line)


def _cmd_learn(ctl: AppController, a: argparse.Namespace) -> None:
    result = ctl.learn_from_files(a.files)
    for note in result.file_notes:
        print(note)
    print("Đã học thêm %d mẫu. Chạy lại lệnh write để có đủ chữ." % result.n_added)


def _cmd_seed(ctl: AppController, a: argparse.Namespace) -> None:
    r = ctl.export_seed_grid(a.n, a.out)
    print("Đã tạo %s với %d từ (còn thiếu nhiều nhất trong văn bản thường gặp)." % (r.out_path, len(r.words)))


def _cmd_check(ctl: AppController, a: argparse.Namespace) -> None:
    r = ctl.export_check(a.out)
    print("Đã tạo %s (%d từ)." % (r.out_path, r.n_words))


def _cmd_drop(ctl: AppController, a: argparse.Namespace) -> None:
    r = ctl.drop_words(a.words)
    for w, n in r.removed.items():
        print("Đã xóa %d mẫu của '%s'" % (n, w) if n else "Không có '%s' trong kho" % w)


def _cmd_stats(ctl: AppController, a: argparse.Namespace) -> None:
    s = ctl.get_stats()
    print("%d từ, %d mẫu; chữ số: %s; dấu câu: %s" % (
        s.n_words, s.n_samples,
        " ".join("%s:%d" % kv for kv in s.digit_counts.items()),
        " ".join("%s:%d" % kv for kv in s.punct_counts.items())))
    print("Dấu thanh có mẫu để ghép: " + " ".join("%d" % n for n in s.tone_mark_counts.values())
          + " (huyền, sắc, ngã, hỏi, nặng)")


# ---------------------------------------------------------------- bộ đọc tham số
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Gõ chữ, ra nét viết tay của bạn cho Xournal++.")
    ap.add_argument("--bank", default=paths.default_bank_path(),
                    help="đường dẫn kho mẫu (mặc định: chu_cua_ban.json.gz)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="ghi log chi tiết (DEBUG) và in ra màn hình -- dùng khi cần tìm lỗi")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="đổi văn bản thành chữ viết tay")
    w.add_argument("-f", "--file", help="file văn bản UTF-8")
    w.add_argument("-t", "--text", help="hoặc gõ thẳng văn bản")
    w.add_argument("-o", "--out", default="ra.xopp")
    w.add_argument("--scale", type=float, default=1.0, help="nhân cỡ chữ")
    w.add_argument("--line", type=float, help="khoảng cách dòng (pt)")
    w.add_argument("--width", type=float, help="bề rộng dòng (pt)")
    w.add_argument("--space", type=float, default=1.0, help="nhân khoảng cách giữa các từ")
    w.add_argument("--jitter", type=float, default=1.0, help="độ 'run tay' ngẫu nhiên (0 = tắt)")
    w.add_argument("--wscale", type=float, default=1.0, help="nhân độ dày nét")
    w.add_argument("--color", help="đổi màu, ví dụ #1a237e")
    w.add_argument("--seed", type=int)
    w.add_argument("--strict-case", action="store_true", help="không dùng chữ thường thay cho chữ hoa đầu từ")
    w.set_defaults(fn=_cmd_write)

    l = sub.add_parser("learn", help="học từ trong file mẫu đã viết")
    l.add_argument("files", nargs="+")
    l.set_defaults(fn=_cmd_learn)

    s = sub.add_parser("seed", help="tạo file mẫu các từ thông dụng còn thiếu")
    s.add_argument("n", type=int, nargs="?", default=200)
    s.add_argument("-o", "--out", default="mau_pho_bien.xopp")
    s.set_defaults(fn=_cmd_seed)

    c = sub.add_parser("check", help="tạo file xem lại toàn bộ kho mẫu")
    c.add_argument("-o", "--out", default="kiem_tra.xopp")
    c.set_defaults(fn=_cmd_check)

    d = sub.add_parser("drop", help="xóa từ khỏi kho mẫu")
    d.add_argument("words", nargs="+")
    d.set_defaults(fn=_cmd_drop)

    t = sub.add_parser("stats", help="thống kê kho mẫu")
    t.set_defaults(fn=_cmd_stats)
    return ap


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = build_parser().parse_args(argv)
    log_file = configure_logging(verbose=a.verbose)
    if a.cmd == "write" and not (a.file or a.text) and sys.stdin.isatty():
        sys.exit("Cần -f van_ban.txt (hoặc -t \"văn bản\").")

    ctl = AppController(a.bank)
    try:
        ctl.load_bank(a.bank, create_if_missing=False)
        a.fn(ctl, a)
    except BankError as e:
        sys.exit(str(e))
    except Exception as e:  # noqa: BLE001 -- chốt chặn cuối: ghi traceback đầy đủ vào log
        _log.exception("Lỗi khi chạy lệnh %r", a.cmd)
        if a.verbose:
            raise
        if log_file:
            sys.exit(f"Lỗi: {e}\n(chi tiết đầy đủ đã ghi vào {log_file} -- chạy lại với -v để xem ngay trên màn hình)")
        sys.exit(f"Lỗi: {e}\n(chạy lại với -v để xem ngay trên màn hình)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
