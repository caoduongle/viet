"""Tab "Kho mẫu": xem thống kê, tìm/xoá từ, xuất file kiểm tra lại toàn bộ kho.

So với bản gốc: mọi thao tác dữ liệu (xoá từ, thống kê, xuất file) đi qua Controller thay
vì `bank.words.pop(...)`/`bank.rebuild()`/`bank.save()` ngay trong hàm xử lý nút bấm.
Việc xoá cũng không còn phải "đọc ngược" nhãn từ chuỗi hiển thị ("từ  (3 mẫu)") -- giữ
danh sách các từ đang hiển thị song song với Listbox nên luôn lấy đúng từ được chọn.
"""
from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk

from chuviettay.controller.app_controller import TONE_NAMES, AppController
from chuviettay.controller.results import BankStats
from chuviettay.view.dialogs import report_error

_log = logging.getLogger(__name__)


def format_stats_gui(stats: BankStats) -> str:
    """Nhãn thống kê nhiều dòng cho tab Kho mẫu (thuần: không cần Tk, test được)."""
    digits = " ".join("%s:%d" % kv for kv in stats.digit_counts.items()) or "(chưa có)"
    puncts = " ".join("%s:%d" % kv for kv in stats.punct_counts.items()) or "(chưa có)"
    marks = " ".join(str(n) for n in stats.tone_mark_counts.values())
    return "\n".join([
        "%d từ, %d mẫu" % (stats.n_words, stats.n_samples),
        "Chữ số có mẫu: " + digits,
        "Dấu câu có mẫu: " + puncts,
        "Dấu thanh để ghép (%s): %s" % (",".join(TONE_NAMES), marks),
    ])


class BankTab(ttk.Frame):
    def __init__(self, master, ctl: AppController, on_choose_bank: Callable[[], None]):
        super().__init__(master, padding=10)
        self.ctl = ctl

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.stats_lbl = ttk.Label(top, justify="left", font=("Sans", 10))
        self.stats_lbl.pack(side="left", anchor="w")
        ttk.Button(top, text="Làm mới", command=self.refresh).pack(side="right", anchor="n")

        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, pady=(10, 0))

        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)
        srow = ttk.Frame(left)
        srow.pack(fill="x")
        ttk.Label(srow, text="Tìm:").pack(side="left")
        self.search_var = tk.StringVar()
        se = ttk.Entry(srow, textvariable=self.search_var)
        se.pack(side="left", fill="x", expand=True, padx=4)
        se.bind("<KeyRelease>", lambda ev: self._filter())

        self.word_list = tk.Listbox(left, height=18)
        self.word_list.pack(fill="both", expand=True, pady=4)

        right = ttk.Frame(mid, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="y")
        ttk.Button(right, text="Xoá từ đã chọn", command=self.drop_selected).pack(fill="x", pady=2)
        ttk.Separator(right).pack(fill="x", pady=8)
        ttk.Button(right, text="Xuất file kiểm tra lại (.xopp)...", command=self.export_check).pack(fill="x", pady=2)
        ttk.Label(right, text="(mở file này trong Xournal++ để\nxem chữ gõ có khớp chữ viết tay)",
                  foreground="#888888", justify="left").pack(anchor="w", pady=(2, 10))
        ttk.Separator(right).pack(fill="x", pady=8)
        ttk.Button(right, text="Chọn kho mẫu khác...", command=on_choose_bank).pack(fill="x", pady=2)

        self._all_words: list[tuple[str, int]] = []   # (từ, số mẫu)
        self._shown: list[str] = []                    # các từ đang hiển thị, cùng thứ tự với Listbox
        self.refresh()

    def refresh(self) -> None:
        self.stats_lbl.configure(text=format_stats_gui(self.ctl.get_stats()))
        self._all_words = self.ctl.list_words()
        self._filter()

    def _filter(self) -> None:
        q = self.search_var.get().strip().lower()
        self.word_list.delete(0, "end")
        self._shown = []
        for w, n in self._all_words:
            if q in w.lower():
                self._shown.append(w)
                self.word_list.insert("end", "%s  (%d mẫu)" % (w, n))

    def selected_word(self) -> str | None:
        sel = self.word_list.curselection()
        return self._shown[sel[0]] if sel else None

    def drop_selected(self) -> None:
        label = self.selected_word()
        if label is None:
            return
        if not messagebox.askyesno("Xoá từ", "Xoá hết mẫu của '%s' khỏi kho?" % label):
            return
        try:
            self.ctl.drop_words([label])
        except Exception as e:  # noqa: BLE001
            report_error("Lỗi khi xoá từ", e, _log)
            return
        self.refresh()

    def export_check(self) -> None:
        out = filedialog.asksaveasfilename(defaultextension=".xopp",
                                           filetypes=[("Xournal++", "*.xopp")],
                                           initialfile="kiem_tra.xopp")
        if not out:
            return
        try:
            result = self.ctl.export_check(out)
        except Exception as e:  # noqa: BLE001
            report_error("Lỗi khi xuất file kiểm tra", e, _log)
            return
        messagebox.showinfo("Xong", "Đã tạo %s (%d từ)." % (result.out_path, result.n_words))
