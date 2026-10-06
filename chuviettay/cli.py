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
    """Nguồn văn bản cho lệnh write: file (-f hoặc positional), hoặc gõ thẳng (-t), hoặc đọc stdin."""
    target_file = getattr(a, "file", None) or getattr(a, "file_pos", None)
    if target_file:
        with open(target_file, encoding="utf-8-sig") as f:
            return f.read()
    if a.text:
        return a.text
    return sys.stdin.read()


def _cmd_write(ctl: AppController, a: argparse.Namespace) -> None:
    from chuviettay.document.page_format import parse_length

    paper_width = parse_length(a.paper_width) if getattr(a, "paper_width", None) else None
    paper_height = parse_length(a.paper_height) if getattr(a, "paper_height", None) else None
    bg_spacing = parse_length(a.background_spacing) if getattr(a, "background_spacing", None) else None
    bg_margin = parse_length(a.background_margin) if getattr(a, "background_margin", None) else None

    opts = WriteOptions(
        scale=a.scale, line=a.line, width=a.width, space=a.space, jitter=a.jitter,
        wscale=a.wscale, color=a.color, seed=a.seed, strict_case=a.strict_case,
        paper=getattr(a, "paper", "a4"),
        orientation=getattr(a, "orientation", "portrait"),
        paper_width=paper_width,
        paper_height=paper_height,
        background=getattr(a, "background", "plain"),
        background_spacing=bg_spacing,
        background_margin=bg_margin,
        background_color=getattr(a, "background_color", "#ffffffff"),
        mode=getattr(a, "mode", "semantic"),
        assemble_letters=getattr(a, "assemble", False),
        letter_gap=getattr(a, "letter_gap", 1.0),
        target_xh=getattr(a, "target_xh", 7.94),
        auto_xh=getattr(a, "auto_xh", False),
        pen_clearance_factor=getattr(a, "pen_clearance", 0.8),
        missing_grid=getattr(a, "missing_grid", True),
        stable_variants=getattr(a, "stable", False),
    )

    target_file = getattr(a, "file", None) or getattr(a, "file_pos", None)
    fmt = getattr(a, "format", "auto")
    mode = getattr(a, "mode", "semantic").lower().strip()
    use_doc_importer = False
    is_docx = False
    if target_file:
        import os
        ext = os.path.splitext(target_file)[1].lower()
        is_docx = (ext == ".docx" or fmt == "docx")
        if fmt in ("txt", "md", "docx") or (fmt == "auto" and ext in (".txt", ".md", ".markdown", ".docx")):
            use_doc_importer = True

    if mode == "fidelity" and not (target_file and is_docx):
        sys.exit(
            "Lỗi: Chế độ Fidelity (--mode fidelity) chỉ áp dụng cho tệp .docx (giữ nguyên số trang và hình ảnh).\n"
            "Vui lòng chỉ định tệp .docx (ví dụ: python -m chuviettay write tailieu.docx --mode fidelity) "
            "hoặc sử dụng chế độ mặc định (--mode semantic)."
        )

    if target_file and is_docx and mode == "fidelity":
        result = ctl.write_docx_fidelity(target_file, opts, a.out)
        print(f"Fidelity mode: {result.n_pages} trang, {result.n_images} hình ảnh, {result.n_tables} bảng biểu được giữ nguyên.")
    elif use_doc_importer and target_file:
        import_res = ctl.import_document(target_file, fmt)
        for warn in import_res.warnings:
            print(f"Cảnh báo: {warn}")
        for unsupp in import_res.unsupported:
            print(f"Chưa hỗ trợ: {unsupp}")
        result = ctl.write_document(import_res.document, opts, a.out)
    else:
        text = _read_text(a)
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
    if s.n_letters:
        print("Chữ cái đơn lẻ (%d chữ): %s" % (
            s.n_letters,
            " ".join("%s:%d" % kv for kv in s.letter_counts.items())))


def _cmd_grid(ctl: AppController, a: argparse.Namespace) -> None:
    path = ctl.export_letter_grid(a.out, target_xh=a.target_xh, include_digraphs=not a.no_digraphs)
    print(f"Đã tạo tờ lưới chữ cái chuẩn hw3 tại: {path}")
    print("Mở file bằng Xournal++ -> viết từng chữ cái vào ô -> lưu lại -> chạy lệnh: python hw_note.py learn %s" % path)


# ---------------------------------------------------------------- bộ đọc tham số
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Gõ chữ, ra nét viết tay của bạn cho Xournal++.")
    ap.add_argument("--bank", default=paths.default_bank_path(),
                    help="đường dẫn kho mẫu (mặc định: chu_cua_ban.json.gz)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="ghi log chi tiết (DEBUG) và in ra màn hình -- dùng khi cần tìm lỗi")
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="đổi văn bản thành chữ viết tay")
    w.add_argument("file_pos", nargs="?", default=None, metavar="file", help="đường dẫn file tài liệu")
    w.add_argument("-f", "--file", help="file văn bản UTF-8")
    w.add_argument("-t", "--text", help="hoặc gõ thẳng văn bản")
    w.add_argument("--format", choices=["auto", "txt", "md", "docx"], default="auto",
                   help="định dạng tài liệu đầu vào (mặc định: auto)")
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
    w.add_argument("--paper", default="a4",
                   choices=["a5", "a4", "a3", "letter", "legal", "16:9", "4:3", "custom"],
                   help="khổ giấy (a4, a3, a5, letter, legal, 16:9, 4:3, custom; mặc định: a4)")
    w.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"],
                   help="chiều giấy: portrait (dọc) hoặc landscape (ngang; mặc định: portrait)")
    w.add_argument("--paper-width", help="bề ngang khổ giấy custom (ví dụ: 210mm, 595.28pt)")
    w.add_argument("--paper-height", help="bề dọc khổ giấy custom (ví dụ: 297mm, 841.89pt)")
    w.add_argument("--background", default="plain",
                   choices=[
                       "plain", "lined", "ruled", "graph", "dotted",
                       "iso_graph", "iso_dotted", "music",
                       "isograph", "isodotted", "staves",
                   ],
                   help="kiểu nền giấy XOPP (plain, lined, ruled, graph, dotted, iso_graph, iso_dotted, music; mặc định: plain)")
    w.add_argument("--background-spacing", help="khoảng cách dòng/lưới ô kẻ (ví dụ: 5mm, 14.17pt, 24pt)")
    w.add_argument("--background-margin", help="lề dọc cho ruled (ví dụ: 72pt, 2.5cm)")
    w.add_argument("--background-color", default="#ffffffff", help="màu nền hex RGBA (mặc định: #ffffffff)")
    w.add_argument("--mode", default="semantic", choices=["semantic", "fidelity"],
                   help="chế độ kết xuất: semantic (tái dàn trang) hoặc fidelity (khóa cố định bố cục & ảnh; mặc định: semantic)")
    w.add_argument("--assemble", action="store_true",
                   help="tự động ghép chữ cái thành từ khi thiếu mẫu nguyên từ")
    w.add_argument("--letter-gap", type=float, default=1.0,
                   help="hệ số khoảng cách giữa các chữ cái (mặc định: 1.0)")
    w.add_argument("--target-xh", type=float, default=7.94,
                   help="x-height mục tiêu (pt, mặc định: 7.94 pt theo note gốc)")
    w.add_argument("--auto-xh", action="store_true",
                   help="tự động chuẩn hóa cỡ chữ và độ dày nét theo bản note gốc (tỉ lệ 17.8%%)")
    w.add_argument("--pen-clearance", type=float, default=0.8,
                   help="hệ số sàn khe hở tối thiểu theo độ dày bút (mặc định: 0.8)")
    w.add_argument("--no-missing-grid", dest="missing_grid", action="store_false", default=True,
                   help="không tự động tạo file lưới ô từ còn thiếu (_thieu.xopp)")
    w.add_argument("--stable", action="store_true", default=False,
                   help="bật chế độ chọn biến thể chữ ổn định (stable_variants) khi sửa văn bản")
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

    g = sub.add_parser("grid", help="tạo file lưới ô chuẩn hw3 để viết mẫu chữ cái")
    g.add_argument("-o", "--out", default="luoi_chu_cai.xopp", help="đường dẫn file .xopp xuất ra (mặc định: luoi_chu_cai.xopp)")
    g.add_argument("--target-xh", type=float, default=7.94, help="x-height mục tiêu (pt, mặc định: 7.94 pt)")
    g.add_argument("--no-digraphs", action="store_true", help="không bao gồm các cụm phụ âm đôi (ng, nh, ch...)")
    g.set_defaults(fn=_cmd_grid)
    return ap


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = build_parser().parse_args(argv)
    log_file = configure_logging(verbose=a.verbose)
    if a.cmd == "write" and not (a.file or a.text or getattr(a, "file_pos", None)) and sys.stdin.isatty():
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
