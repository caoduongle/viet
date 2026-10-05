#!/usr/bin/env python3
"""Tái hiện các lỗi đã rà soát trong repo caoduongle/viet (chuviettay), commit e517636.

Cách dùng:
    python repro_viet_baseline.py --repo /đường/dẫn/tới/viet            # chạy tất cả
    python repro_viet_baseline.py --repo ... --only D1a D3              # chạy một số mục
    python repro_viet_baseline.py --repo ... --with-pip                 # thêm F4 (cần pip install cục bộ)

Mỗi mục in một trong ba trạng thái:
    BUG        lỗi còn nguyên (kỳ vọng ở commit gốc)
    ĐÃ SỬA     hành vi đúng
    LỖI-CHẠY   chính phép thử gặp ngoại lệ (đọc chi tiết, đừng coi là đã sửa)

Script chỉ dùng thư mục tạm, không đụng kho mẫu thật. Không cần thư viện ngoài ngoài những gì repo đã dùng
(F2 cần markdown-it-py; thiếu thì mục đó báo BỎ-QUA).
Mã thoát: 0 nếu không còn BUG, 1 nếu còn BUG, 2 nếu có LỖI-CHẠY.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=".")
ap.add_argument("--only", nargs="*")
ap.add_argument("--with-pip", action="store_true")
ARGS = ap.parse_args()
REPO = os.path.abspath(ARGS.repo)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tests"))

from conftest import generate_large_synthetic_bank_dict, tiny_bank_dict  # noqa: E402

from chuviettay.controller.app_controller import AppController  # noqa: E402
from chuviettay.controller.results import WriteOptions  # noqa: E402
from chuviettay.model import xopp  # noqa: E402
from chuviettay.model.bank import Bank  # noqa: E402

RESULTS: list[tuple[str, str, str]] = []


def write_bank(tmp: str, d: dict | None = None, name: str = "b.json.gz") -> str:
    d = d or tiny_bank_dict()
    d["schema_version"] = 3
    d.setdefault("symbols", {})
    d.setdefault("letters", {})
    p = os.path.join(tmp, name)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    return p


def touch_from_other_process(path: str) -> None:
    """Giả lập tiến trình khác đã ghi kho (đổi mtime/size) để lần save() sau phải HỢP NHẤT."""
    other = Bank(path)
    other.add_sample("zzz_external", [[0.0, 0.0, 1.0, -1.0]], 5.0)
    other.save()


def check(code: str, title: str):
    def deco(fn):
        def run():
            if ARGS.only and code not in ARGS.only:
                return
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    bug, detail = fn(tmp)
                status = "BUG" if bug else "ĐÃ SỬA"
            except ModuleNotFoundError as e:
                status, detail = "BỎ-QUA", "thiếu thư viện: %s" % e.name
            except Exception as e:  # noqa: BLE001
                tb = traceback.extract_tb(e.__traceback__)[-1]
                status, detail = "LỖI-CHẠY", "%s: %s (%s:%d)" % (type(e).__name__, e, os.path.basename(tb.filename), tb.lineno)
            RESULTS.append((code, status, title))
            print("[%-8s] %-4s %s\n           %s" % (status, code, title, detail))
        run.code = code
        CHECKS.append(run)
        return run
    return deco


CHECKS: list = []


@check("D1a", "Xoá CHỮ CÁI 'a' rồi lưu có hợp nhất làm mất luôn TỪ 'a'")
def d1a(tmp):
    p = write_bank(tmp)
    b = Bank(p)
    b.add_letter_sample("a", [[0.0, -5.0, 3.0, 0.0]], 4.0, dedup=False)
    b.add_sample("a", [[0.0, -5.0, 3.0, 0.0]], 4.0, dedup=False)
    b.save()
    b.drop_letter("a")
    touch_from_other_process(p)
    b.save()
    w, le = len(b.words.get("a", [])), len(b.letters.get("a", []))
    return w == 0, "sau hợp nhất: words['a']=%d (kỳ vọng 1), letters['a']=%d (kỳ vọng 0)" % (w, le)


@check("D1b", "Chọn TỪ 'a' ở tab Kho mẫu rồi xoá lại xoá nhầm CHỮ CÁI 'a'")
def d1b(tmp):
    p = write_bank(tmp)
    b = Bank(p)
    b.add_letter_sample("a", [[0.0, -5.0, 3.0, 0.0]], 4.0, dedup=False)
    b.add_sample("a", [[0.0, -5.0, 3.0, 0.0]], 4.0, dedup=False)
    b.save()
    ctl = AppController(p)
    ctl.load_bank()
    ctl.drop_words(["a"])
    w, le = len(ctl.bank.words.get("a", [])), len(ctl.bank.letters.get("a", []))
    return (w == 1 and le == 0), "sau drop_words(['a']): words['a']=%d (kỳ vọng 0), letters['a']=%d (kỳ vọng 1)" % (w, le)


@check("D2", "Xoá ký hiệu rồi dạy lại bằng add_symbol_sample: mẫu mới mất sau lần hợp nhất kế")
def d2(tmp):
    p = write_bank(tmp)
    b = Bank(p)
    b.add_symbol_sample("π", [[0.0, 0.0, 5.0, 5.0]], 6.0)
    b.save()
    b.drop_symbol("π")
    b.save()
    b.add_symbol_sample("π", [[0.0, 0.0, 9.0, 9.0]], 7.0)
    touch_from_other_process(p)
    b.save()
    n_ram, n_disk = len(b.symbols.get("π", [])), len(Bank(p).symbols.get("π", []))
    return n_disk == 0, "mẫu π sau hợp nhất: trong RAM=%d, trên đĩa=%d (kỳ vọng 1)" % (n_ram, n_disk)


@check("D3", "learn không idempotent: lưu lại cùng tờ lưới (header gzip đổi) bị học trùng")
def d3(tmp):
    p = write_bank(tmp)
    ctl = AppController(p)
    ctl.load_bank()
    samples = {"khoai": [[0.0, -5.0, 3.0, 0.0, 6.0, -5.0]]}
    f1, f2 = os.path.join(tmp, "g1.xopp"), os.path.join(tmp, "g2.xopp")
    xopp.make_grid(f1, ["khoai"], ctl.bank, "t", samples=samples, calib=False, grid_version="hw3")
    raw = gzip.decompress(open(f1, "rb").read())
    with open(f2, "wb") as raw_f, gzip.GzipFile(fileobj=raw_f, mode="wb", mtime=1234567890) as g:
        g.write(raw)  # cùng XML, khác mtime trong header => khác SHA-256 của file thô
    ctl.learn_from_files([f1])
    n1 = len(ctl.bank.words.get("khoai", []))
    ctl.learn_from_files([f2])
    n2 = len(ctl.bank.words.get("khoai", []))
    return n2 > n1, "số mẫu 'khoai': sau lần học 1 = %d, sau lần học 2 (cùng nội dung) = %d (kỳ vọng vẫn %d)" % (n1, n2, n1)


@check("D4a", "WriteOptions(missing_grid=False) bị bỏ qua ở chế độ Semantic; CLI không có --no-missing-grid")
def d4a(tmp):
    p = write_bank(tmp)
    ctl = AppController(p)
    ctl.load_bank()
    out = os.path.join(tmp, "ra.xopp")
    ctl.write_text("zebra quokka", WriteOptions(seed=1, missing_grid=False), out)
    created = os.path.exists(os.path.join(tmp, "ra_thieu.xopp"))
    helptxt = subprocess.run([sys.executable, "-m", "chuviettay", "write", "--help"], capture_output=True, text=True, cwd=REPO).stdout
    has_flag = "no-missing-grid" in helptxt
    return created or not has_flag, "_thieu.xopp vẫn được tạo khi tắt cờ: %s | CLI có --no-missing-grid: %s" % (created, has_flag)


@check("D4b", "Chạy lại write ghi đè ra_thieu.xopp, mất nét người dùng đã viết dở")
def d4b(tmp):
    p = write_bank(tmp)
    ctl = AppController(p)
    ctl.load_bank()
    out = os.path.join(tmp, "ra.xopp")
    ctl.write_text("zebra quokka", WriteOptions(seed=1), out)
    grid = os.path.join(tmp, "ra_thieu.xopp")
    xml = gzip.decompress(open(grid, "rb").read()).decode()
    marker = '<stroke tool="pen" color="#000000ff" width="1.41">60 100 70 90 80 100</stroke>\n'
    xml = xml.replace("</layer>", marker + "</layer>", 1)
    with gzip.open(grid, "wt", encoding="utf-8") as f:
        f.write(xml)
    before = gzip.decompress(open(grid, "rb").read()).decode().count("60 100 70 90 80 100")
    ctl.write_text("zebra quokka", WriteOptions(seed=1, scale=1.1), out)
    after = gzip.decompress(open(grid, "rb").read()).decode().count("60 100 70 90 80 100")
    return (before == 1 and after == 0), "nét người dùng trong ra_thieu.xopp: trước=%d, sau khi chạy lại write=%d (kỳ vọng vẫn 1)" % (before, after)


@check("D5", "Lưu hoãn trên luồng Timer: RuntimeError 'dictionary changed size during iteration'")
def d5(tmp):
    d = generate_large_synthetic_bank_dict(40000)
    p = write_bank(tmp, d)
    ctl = AppController(p)
    ctl.load_bank()
    ctl.debounce_delay = 0.01
    errors: list[str] = []
    old_hook = threading.excepthook
    threading.excepthook = lambda a: errors.append("%s: %s" % (a.exc_type.__name__, a.exc_value))
    try:
        for i in range(8):  # đúng thao tác GUI: dạy 1 từ, Timer bắt đầu ghi, người dùng dạy tiếp từ kế
            ctl.teach_word("kt_a%d" % i, [[0.0, 0.0, 1.0, -1.0]], 5.0, deferred_save=True)
            time.sleep(0.08)
            ctl.teach_word("kt_b%d" % i, [[0.0, 0.0, 2.0, -1.0]], 5.0, deferred_save=True)
            time.sleep(0.8)
        ctl.flush_save()
    finally:
        threading.excepthook = old_hook
    return len(errors) > 0, "%d/8 vòng làm luồng Timer ném lỗi%s" % (len(errors), (" (vd: %s)" % errors[0]) if errors else "")


@check("F1", "Paragraph.align (center/right) bị bỏ qua khi dàn trang Semantic")
def f1(tmp):
    from chuviettay.document.ir import Document, Paragraph, Text

    p = write_bank(tmp)
    ctl = AppController(p)
    ctl.load_bank()
    xs = {}
    for al in ("left", "center", "right"):
        out = os.path.join(tmp, "al_%s.xopp" % al)
        ctl.write_document(Document(blocks=[Paragraph(inlines=[Text(text="xin")], align=al)]), WriteOptions(seed=3, jitter=0.0), out)
        xml = gzip.decompress(open(out, "rb").read()).decode()
        xs[al] = min(float(m.group(1)) for m in re.finditer(r"<stroke[^>]*>(-?[0-9.]+) ", xml))
    return xs["left"] == xs["center"] == xs["right"], "x nhỏ nhất: %s" % xs


@check("F2", "Markdown: đậm/nghiêng/code/liên kết bị làm phẳng không cảnh báo; ~~gạch~~ còn nguyên ký tự ~~")
def f2(tmp):
    from chuviettay.importer.markdown_importer import MarkdownImporter

    res = MarkdownImporter().import_text("Chữ **đậm** và *nghiêng* và ~~gạch~~ và [liên kết](http://x.y).")
    text = "".join(getattr(i, "text", "") for b in res.document.blocks for i in getattr(b, "inlines", []))
    return ("~~" in text and not res.warnings), "văn bản vào IR: %r | cảnh báo: %s" % (text, res.warnings)


@check("F4", "Cài bằng pip: kho/log mặc định nằm trong site-packages, `hw-note stats` báo không thấy kho")
def f4(tmp):
    if not ARGS.with_pip:
        raise ModuleNotFoundError(name="--with-pip (bỏ qua có chủ ý)")
    target = os.path.join(tmp, "site")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target", target, REPO], check=True, capture_output=True)
    env = dict(os.environ, PYTHONPATH=target)
    code = "from chuviettay import paths; print(paths.default_bank_path())"
    path = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=tmp).stdout.strip()
    return os.path.abspath(path).startswith(os.path.abspath(target)), "kho mặc định = %s" % path


if __name__ == "__main__":
    for run in CHECKS:
        run()
    bad = [r for r in RESULTS if r[1] == "BUG"]
    err = [r for r in RESULTS if r[1] == "LỖI-CHẠY"]
    print("\nTổng: %d mục | BUG: %d | ĐÃ SỬA: %d | LỖI-CHẠY: %d | BỎ-QUA: %d" % (
        len(RESULTS), len(bad), sum(r[1] == "ĐÃ SỬA" for r in RESULTS), len(err), sum(r[1] == "BỎ-QUA" for r in RESULTS)))
    sys.exit(2 if err else (1 if bad else 0))
