"""MainWindow -- cửa sổ chính: thanh chọn kho mẫu + 3 tab (Viết chữ / Dạy từ mới / Kho mẫu).

Vai trò: TRUNG GIAN giữa các tab (các tab không gọi nhau) và giữ Controller dùng chung.
So với bản gốc (class App):
  - Không còn cất kho mẫu (self.bank, self.bank_path) trên cửa sổ rồi để các tab tự với
    tay vào `self.app.bank`. Trạng thái ứng dụng nằm ở AppController; cửa sổ chỉ hiển thị.
  - Nếu mở kho mẫu lúc khởi động thất bại, rồi sau đó người dùng chọn được một kho hợp
    lệ, các tab được dựng ra ở thời điểm đó (bản gốc không dựng tab nữa nên cửa sổ trống
    trơn mãi).
  - Thêm nút "Tạo kho mẫu mới...": README bản gốc hứa "trỏ tới file chưa tồn tại thì app tự
    tạo kho trống", nhưng hộp thoại "Mở file" không cho chọn file chưa tồn tại.
  - report_callback_exception: mọi lỗi bất ngờ trong lúc xử lý sự kiện đều được ghi traceback
    đầy đủ vào file log và hiện hộp thoại, thay vì chỉ in ra stderr (mất hẳn với bản .exe).
"""
from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from chuviettay.controller.app_controller import AppController
from chuviettay.view.bank_tab import BankTab
from chuviettay.view.dialogs import report_error
from chuviettay.view.teach_tab import TeachTab
from chuviettay.view.write_tab import WriteTab

_log = logging.getLogger(__name__)

BANK_FILETYPES = [("Kho mẫu", "*.json.gz"), ("Tất cả", "*.*")]


class MainWindow(tk.Tk):
    def __init__(self, ctl: AppController):
        super().__init__()
        self.ctl = ctl
        self.title("Chữ viết tay của bạn")
        self.geometry("1180x760")

        top = ttk.Frame(self, padding=(10, 6))
        top.pack(fill="x")
        self.path_lbl = ttk.Label(top, foreground="#555555")
        self.path_lbl.pack(side="left")
        ttk.Button(top, text="Tạo kho mẫu mới...", command=self.new_bank).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Chọn kho mẫu khác...", command=self.choose_bank).pack(side="right")

        self.placeholder = ttk.Label(
            self, padding=20,
            text="Chưa có kho mẫu hợp lệ.\nBấm 'Chọn kho mẫu khác...' hoặc 'Tạo kho mẫu mới...' ở góc trên.")
        self.notebook = ttk.Notebook(self)
        self._tabs_built = False

        try:
            self.ctl.load_bank(create_if_missing=True)
        except Exception as e:  # noqa: BLE001
            report_error("Không mở được kho mẫu", e, _log)
        self._sync_ui()

    # ------------------------------------------------------------ dựng / đồng bộ giao diện
    def _build_tabs(self) -> None:
        self.write_tab = WriteTab(self.notebook, self.ctl, on_teach_missing=self._teach_missing)
        self.teach_tab = TeachTab(self.notebook, self.ctl)
        self.bank_tab = BankTab(self.notebook, self.ctl, on_choose_bank=self.choose_bank)
        self.notebook.add(self.write_tab, text="Viết chữ")
        self.notebook.add(self.teach_tab, text="Dạy từ mới")
        self.notebook.add(self.bank_tab, text="Kho mẫu")
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_changed())
        self._tabs_built = True

    def _sync_ui(self) -> None:
        """Đồng bộ cửa sổ với trạng thái Controller (đường dẫn kho mẫu, có/không có tab)."""
        self.path_lbl.configure(text="Kho mẫu: " + self.ctl.bank_path)
        if self.ctl.bank is None:
            self.notebook.pack_forget()
            self.placeholder.pack(fill="both", expand=True)
            return
        self.placeholder.pack_forget()
        if not self._tabs_built:
            self._build_tabs()
        else:
            self.teach_tab.on_bank_changed()
            self.bank_tab.refresh()
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

    def _on_tab_changed(self) -> None:
        if self.notebook.select() == str(self.bank_tab):
            self.bank_tab.refresh()

    # ------------------------------------------------------------ trung gian giữa các tab
    def _teach_missing(self, words: list[str]) -> None:
        """Tab Viết chữ yêu cầu dạy các từ còn thiếu: nạp vào hàng đợi tab Dạy rồi chuyển sang đó."""
        self.teach_tab.load_queue(words)
        self.notebook.select(self.teach_tab)

    # ------------------------------------------------------------ chọn / tạo kho mẫu
    def _switch_bank(self, path: str) -> bool:
        try:
            self.ctl.load_bank(path, create_if_missing=True)
        except Exception as e:  # noqa: BLE001
            report_error("Không mở được kho mẫu", e, _log)
            return False
        self._sync_ui()
        return True

    def choose_bank(self) -> None:
        path = filedialog.askopenfilename(title="Chọn kho mẫu (.json.gz)", filetypes=BANK_FILETYPES)
        if path:
            self._switch_bank(path)

    def new_bank(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Tạo kho mẫu mới", defaultextension=".json.gz",
            initialfile="chu_cua_ban_moi.json.gz", filetypes=BANK_FILETYPES)
        if not path:
            return
        existed = os.path.exists(path)
        if self._switch_bank(path) and existed:
            # KHÔNG bao giờ ghi đè: file đã có thì chỉ mở nó lên, dữ liệu bên trong còn nguyên.
            messagebox.showinfo("Kho mẫu đã tồn tại",
                                "File này đã có sẵn nên app đã MỞ nó lên (không ghi đè, dữ liệu bên trong còn nguyên).")

    # ------------------------------------------------------------ lỗi bất ngờ
    def report_callback_exception(self, exc, val, tb) -> None:  # noqa: D401  (Tk gọi tên này)
        report_error("Đã xảy ra lỗi không mong đợi", val, _log)
