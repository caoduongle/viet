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

from chuviettay.controller.app_controller import AppController
from chuviettay.formatting import format_stats_gui
from chuviettay.view.dialogs import report_error

_log = logging.getLogger(__name__)


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

        self.word_list = tk.Listbox(left, height=18, selectmode="extended")
        self.word_list.pack(fill="both", expand=True, pady=4)
        self.word_list.bind("<<ListboxSelect>>", lambda ev: self._update_btn_states())

        right = ttk.Frame(mid, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="y")
        self.btn_select_all = ttk.Button(right, text="Chọn tất cả", command=self.select_all)
        self.btn_select_all.pack(fill="x", pady=2)
        self.btn_deselect_all = ttk.Button(right, text="Bỏ chọn", command=self.deselect_all)
        self.btn_deselect_all.pack(fill="x", pady=2)
        ttk.Separator(right).pack(fill="x", pady=6)
        self.btn_drop_selected = ttk.Button(right, text="Xoá đã chọn (0)", command=self.drop_selected)
        self.btn_drop_selected.pack(fill="x", pady=2)
        ttk.Separator(right).pack(fill="x", pady=8)
        ttk.Button(right, text="Xuất file kiểm tra lại (.xopp)...", command=self.export_check).pack(fill="x", pady=2)
        ttk.Label(right, text="(mở file này trong Xournal++ để\nxem chữ gõ có khớp chữ viết tay)",
                  foreground="#888888", justify="left").pack(anchor="w", pady=(2, 10))
        ttk.Separator(right).pack(fill="x", pady=8)
        ttk.Button(right, text="Chọn kho mẫu khác...", command=on_choose_bank).pack(fill="x", pady=2)

        self._all_chars: list[tuple[str, str, int]] = []  # [(loại, nhãn, số mẫu), ...]
        self._shown: list[tuple[str, str, int]] = []       # [(loại, nhãn, số mẫu), ...]
        self.refresh()

    def refresh(self) -> None:
        self.stats_lbl.configure(text=format_stats_gui(self.ctl.get_stats()))
        self._all_chars = self.ctl.list_all_chars()
        self._filter()

    def _filter(self) -> None:
        q = self.search_var.get().strip().lower()
        self.word_list.delete(0, "end")
        self._shown = []
        for kind, ch, n in self._all_chars:
            if q in ch.lower():
                self._shown.append((kind, ch, n))
                self.word_list.insert("end", "[%s] %s  (%d mẫu)" % (kind, ch, n))
        self._update_btn_states()

    def _update_btn_states(self) -> None:
        sel = self.word_list.curselection()
        count = len(sel)
        self.btn_drop_selected.configure(text=f"Xoá đã chọn ({count})")

    def select_all(self) -> None:
        self.word_list.select_set(0, "end")
        self._update_btn_states()

    def deselect_all(self) -> None:
        self.word_list.select_clear(0, "end")
        self._update_btn_states()

    def selected_items(self) -> list[tuple[str, str, int]]:
        sel = self.word_list.curselection()
        return [self._shown[i] for i in sel if i < len(self._shown)]

    def selected_item(self) -> tuple[str, str, int] | None:
        items = self.selected_items()
        return items[0] if items else None

    def selected_word(self) -> str | None:
        item = self.selected_item()
        return item[1] if item else None

    def drop_selected(self) -> None:
        items = self.selected_items()
        if not items:
            return
        total_chars = len(items)
        total_samples = sum(item[2] for item in items)

        if total_chars == 1:
            kind, label, n = items[0]
            prompt = f"Xoá {kind} '{label}' ({n} mẫu) khỏi kho?"
        else:
            prompt = (
                f"Bạn có chắc muốn xoá {total_chars} ký tự đã chọn "
                f"(tổng cộng {total_samples} mẫu nét) khỏi kho mẫu?\n"
                f"Thao tác này sẽ cập nhật kho vĩnh viễn."
            )

        if not messagebox.askyesno("Xác nhận xoá", prompt):
            return
        try:
            labels_to_drop = [item[1] for item in items]
            res = self.ctl.drop_chars(labels_to_drop)
            _log.info("Đã xoá hàng loạt: %d ký tự, %d mẫu nét", res.total_removed_chars, res.total_removed_samples)
        except Exception as e:  # noqa: BLE001
            report_error("Lỗi khi xoá", e, _log)
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
        messagebox.showinfo("Xong", "Đã tạo %s (%d ký tự)." % (result.out_path, result.n_words))
