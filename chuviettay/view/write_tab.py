"""Tab "Viết chữ": gõ/dán văn bản -> xuất file .xopp nét viết tay của bạn.

So với bản gốc:
  - Không còn giả lập argparse.Namespace + gọi cmd_write() + redirect_stdout để "bắt" chữ
    in ra. Gọi thẳng controller.write_text() và nhận WriteResult (dữ liệu thuần); câu chữ
    báo cáo dựng bằng formatting.write_report_lines() -- cùng một hàm với CLI.
  - Danh sách "Từ còn thiếu mẫu" lấy từ CHÍNH kết quả lần viết này (result.missing), theo
    đúng tuỳ chọn người dùng đã đặt. Bản gốc tính lại bằng một hàm riêng luôn giả định
    strict-case = tắt, nên khi bật strict-case danh sách có thể thiếu những từ thực sự
    đang bị để trống trên trang.
  - Nút "Dạy các từ này →" không còn tự với tay sang tab khác; nó gọi callback
    on_teach_missing do MainWindow truyền vào (MainWindow lo việc chuyển tab).
"""
from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import colorchooser, filedialog, messagebox, ttk

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions, WriteResult
from chuviettay.formatting import write_report_lines
from chuviettay.view.dialogs import report_error

_log = logging.getLogger(__name__)


class WriteTab(ttk.Frame):
    def __init__(self, master, ctl: AppController, on_teach_missing: Callable[[list[str]], None]):
        super().__init__(master, padding=10)
        self.ctl = ctl
        self.on_teach_missing = on_teach_missing
        self.last_missing: list[tuple[str, int]] = []
        self.current_doc = None

        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(self, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="y")
        self._build_left(left)
        self._build_options(right)

    # ------------------------------------------------------------ dựng giao diện
    def _build_left(self, left: ttk.Frame) -> None:
        ttk.Label(left, text="Văn bản cần viết:").pack(anchor="w")
        self.text = tk.Text(left, height=14, wrap="word", font=("Sans", 12))
        self.text.pack(fill="both", expand=True, pady=(2, 6))
        self.text.bind("<KeyRelease>", self._on_text_modified)

        btnrow = ttk.Frame(left)
        btnrow.pack(fill="x")
        ttk.Button(btnrow, text="Mở tài liệu...", command=self.open_document).pack(side="left")
        ttk.Button(btnrow, text="Tạo file viết tay (.xopp)...", command=self.do_write).pack(side="left", padx=6)

        ttk.Label(left, text="Kết quả:").pack(anchor="w", pady=(10, 0))
        self.status = tk.Text(left, height=6, wrap="word", state="disabled", font=("Sans", 10))
        self.status.pack(fill="x")

        misswrap = ttk.LabelFrame(left, text="Từ còn thiếu mẫu (nếu có)")
        misswrap.pack(fill="both", expand=True, pady=(10, 0))
        self.miss_list = tk.Listbox(misswrap, height=5)
        self.miss_list.pack(side="left", fill="both", expand=True)
        ttk.Button(misswrap, text="Dạy các từ này →",
                   command=self.teach_missing).pack(side="left", padx=6, anchor="n", pady=4)

    def _build_options(self, right: ttk.Frame) -> None:
        opt = ttk.LabelFrame(right, text="Tuỳ chỉnh", padding=8)
        opt.pack(fill="y")
        self.v_scale = tk.StringVar(value="1.0")
        self.v_line = tk.StringVar(value="")
        self.v_width = tk.StringVar(value="")
        self.v_space = tk.StringVar(value="1.0")
        self.v_jitter = tk.StringVar(value="1.0")
        self.v_wscale = tk.StringVar(value="1.0")
        self.v_seed = tk.StringVar(value="")
        self.v_color = tk.StringVar(value="")
        self.v_strict = tk.BooleanVar(value=False)

        def row(lbl: str, var: tk.StringVar, hint: str = "") -> None:
            f = ttk.Frame(opt)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=lbl, width=16).pack(side="left")
            ttk.Entry(f, textvariable=var, width=10).pack(side="left")
            if hint:
                ttk.Label(f, text=hint, foreground="#888888").pack(side="left", padx=4)

        row("Cỡ chữ (scale)", self.v_scale, "1.0 = giữ nguyên")
        row("Dòng cách (line)", self.v_line, "để trống = mặc định")
        row("Bề rộng dòng", self.v_width, "để trống = mặc định")
        row("Khoảng cách từ", self.v_space, "space")
        row("Độ run tay", self.v_jitter, "0 = tắt")
        row("Độ dày nét", self.v_wscale)
        row("Seed ngẫu nhiên", self.v_seed, "để trống = mỗi lần khác nhau")
        colf = ttk.Frame(opt)
        colf.pack(fill="x", pady=2)
        ttk.Label(colf, text="Màu chữ", width=16).pack(side="left")
        self.color_sw = tk.Label(colf, textvariable=self.v_color, width=10, relief="sunken")
        self.color_sw.pack(side="left")
        ttk.Button(colf, text="Chọn...", command=self.pick_color).pack(side="left", padx=4)
        ttk.Button(colf, text="Mặc định", command=lambda: self.v_color.set("")).pack(side="left")
        ttk.Checkbutton(opt, text="Không tự hạ chữ hoa đầu câu (strict-case)",
                        variable=self.v_strict).pack(anchor="w", pady=(6, 0))

    # ------------------------------------------------------------ đọc tuỳ chọn
    @staticmethod
    def _float(var: tk.StringVar, label: str, default: float | None) -> float | None:
        s = var.get().strip()
        if not s:
            return default
        try:
            return float(s)
        except ValueError:
            raise ValueError("Ô '%s' phải là một con số (bạn đang nhập: %r)." % (label, s)) from None

    def read_options(self) -> WriteOptions:
        """Đọc các ô nhập thành WriteOptions; ném ValueError kèm tên ô nếu nhập sai."""
        seed_s = self.v_seed.get().strip()
        try:
            seed = int(seed_s) if seed_s else None
        except ValueError:
            raise ValueError("Ô 'Seed ngẫu nhiên' phải là một số nguyên (bạn đang nhập: %r)." % seed_s) from None
        opts = WriteOptions(
            scale=self._float(self.v_scale, "Cỡ chữ", 1.0),
            line=self._float(self.v_line, "Dòng cách", None),
            width=self._float(self.v_width, "Bề rộng dòng", None),
            space=self._float(self.v_space, "Khoảng cách từ", 1.0),
            jitter=self._float(self.v_jitter, "Độ run tay", 1.0),
            wscale=self._float(self.v_wscale, "Độ dày nét", 1.0),
            color=(self.v_color.get().strip() or None),
            seed=seed,
            strict_case=self.v_strict.get(),
        )
        opts.validate()
        return opts

    def _on_text_modified(self, event=None) -> None:
        self.current_doc = None

    # ------------------------------------------------------------ hành động
    def open_document(self) -> None:
        import os

        path = filedialog.askopenfilename(
            filetypes=[
                ("Tài liệu hỗ trợ", "*.txt;*.md;*.markdown;*.docx"),
                ("Văn bản thuần (.txt)", "*.txt"),
                ("Markdown (.md)", "*.md;*.markdown"),
                ("Word (.docx)", "*.docx"),
                ("Tất cả", "*.*"),
            ]
        )
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in (".md", ".markdown", ".docx", ".txt"):
            try:
                res = self.ctl.import_document(path)
                self.current_doc = res.document
                self.text.delete("1.0", "end")
                if ext == ".txt":
                    with open(path, encoding="utf-8-sig") as f:
                        content = f.read()
                    self.text.insert("1.0", content)
                else:
                    preview_lines = []
                    for b in res.document.blocks:
                        if hasattr(b, "inlines"):
                            preview_lines.append(
                                " ".join(getattr(i, "text", "") for i in b.inlines if hasattr(i, "text"))
                            )
                        elif hasattr(b, "latex"):
                            preview_lines.append(f"$${b.latex}$$")
                        elif hasattr(b, "rows"):
                            preview_lines.append(f"[Bảng {len(b.rows)} hàng]")
                    self.text.insert("1.0", "\n".join(preview_lines))

                info_lines = [f"Đã mở tài liệu: {os.path.basename(path)} ({len(res.document.blocks)} khối)."]
                if res.warnings:
                    info_lines.append("Cảnh báo: " + "; ".join(res.warnings))
                if res.unsupported:
                    info_lines.append("Chưa hỗ trợ (đã bỏ qua): " + "; ".join(res.unsupported))

                self.status.configure(state="normal")
                self.status.delete("1.0", "end")
                self.status.insert("1.0", "\n".join(info_lines) + "\n")
                self.status.configure(state="disabled")
            except Exception as e:  # noqa: BLE001
                report_error("Không đọc được tài liệu", e, _log)
                return
        else:
            self.current_doc = None
            try:
                with open(path, encoding="utf-8-sig") as f:
                    content = f.read()
            except Exception as e:  # noqa: BLE001
                report_error("Không đọc được file văn bản", e, _log)
                return
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.status.configure(state="normal")
            self.status.delete("1.0", "end")
            self.status.insert("1.0", f"Đã mở tệp: {os.path.basename(path)}\n")
            self.status.configure(state="disabled")

    open_txt = open_document

    def pick_color(self) -> None:
        _rgb, hexval = colorchooser.askcolor(title="Chọn màu chữ")
        if hexval:
            self.v_color.set(hexval)

    def do_write(self) -> None:
        text = self.text.get("1.0", "end").strip("\n")
        if not text.strip() and not self.current_doc:
            messagebox.showwarning("Thiếu văn bản", "Hãy gõ hoặc dán văn bản trước đã.")
            return
        try:
            opts = self.read_options()
        except ValueError as e:
            messagebox.showerror("Giá trị không hợp lệ", str(e))
            return
        out = filedialog.asksaveasfilename(defaultextension=".xopp",
                                           filetypes=[("Xournal++", "*.xopp")],
                                           initialfile="ra.xopp")
        if not out:
            return
        try:
            # Luôn viết bằng kho mẫu MỚI NHẤT trên đĩa (bản gốc: cmd_write tự nạp lại kho mỗi lần bấm),
            # để nếu bạn vừa chạy `hw_note.py learn ...` ở cửa sổ dòng lệnh khác thì từ mới có hiệu lực ngay.
            self.ctl.reload_bank()
            if self.current_doc is not None:
                result = self.ctl.write_document(self.current_doc, opts, out)
            else:
                result = self.ctl.write_text(text, opts, out)
        except Exception as e:  # noqa: BLE001
            report_error("Lỗi khi viết văn bản", e, _log)
            return
        self._show_result(result)

    def _show_result(self, result: WriteResult) -> None:
        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.insert("1.0", "\n".join(write_report_lines(result)) + "\n")
        self.status.configure(state="disabled")

        self.last_missing = result.missing_sorted()
        self.miss_list.delete(0, "end")
        for w, n in self.last_missing:
            self.miss_list.insert("end", "%s  (x%d)" % (w, n))

    def teach_missing(self) -> None:
        if not self.last_missing:
            messagebox.showinfo("Không có gì để dạy", "Chưa có từ nào đang thiếu.")
            return
        self.on_teach_missing([w for w, _n in self.last_missing])
