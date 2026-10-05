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
import re
import tkinter as tk
from collections.abc import Callable
from tkinter import colorchooser, filedialog, messagebox, ttk

from chuviettay.controller.app_controller import AppController
from chuviettay.controller.results import WriteOptions, WriteResult
from chuviettay.formatting import write_report_lines
from chuviettay.view.dialogs import report_error

_log = logging.getLogger(__name__)


class CustomPaperDialog(tk.Toplevel):
    """Hộp thoại cài đặt kích thước giấy tùy chỉnh theo mm, cm hoặc pt."""

    def __init__(self, parent: tk.Widget, initial_w: float = 210.0, initial_h: float = 297.0):
        super().__init__(parent)
        self.title("Khổ giấy tùy chỉnh")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.result: tuple[float, float] | None = None

        f = ttk.Frame(self, padding=12)
        f.pack(fill="both", expand=True)

        self.v_w = tk.StringVar(value=str(initial_w))
        self.v_h = tk.StringVar(value=str(initial_h))
        self.v_unit = tk.StringVar(value="mm")

        r1 = ttk.Frame(f)
        r1.pack(fill="x", pady=4)
        ttk.Label(r1, text="Bề ngang:", width=10).pack(side="left")
        ttk.Entry(r1, textvariable=self.v_w, width=12).pack(side="left")

        r2 = ttk.Frame(f)
        r2.pack(fill="x", pady=4)
        ttk.Label(r2, text="Bề dọc:", width=10).pack(side="left")
        ttk.Entry(r2, textvariable=self.v_h, width=12).pack(side="left")

        r3 = ttk.Frame(f)
        r3.pack(fill="x", pady=4)
        ttk.Label(r3, text="Đơn vị:", width=10).pack(side="left")
        u_cb = ttk.Combobox(r3, textvariable=self.v_unit, values=["mm", "cm", "pt"], width=10, state="readonly")
        u_cb.pack(side="left")

        btn_row = ttk.Frame(f)
        btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_row, text="Đồng ý", command=self._on_ok).pack(side="right", padx=(4, 0))
        ttk.Button(btn_row, text="Hủy", command=self.destroy).pack(side="right")

        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_ok(self) -> None:
        from chuviettay.document.page_format import parse_length

        try:
            unit = self.v_unit.get().strip()
            w_pt = parse_length(f"{self.v_w.get().strip()}{unit}")
            h_pt = parse_length(f"{self.v_h.get().strip()}{unit}")
            if w_pt <= 0 or h_pt <= 0:
                raise ValueError("Kích thước giấy phải lớn hơn 0.")
            self.result = (w_pt, h_pt)
            self.destroy()
        except ValueError as err:
            messagebox.showerror("Kích thước không hợp lệ", str(err), parent=self)


class WriteTab(ttk.Frame):
    def __init__(self, master, ctl: AppController, on_teach_missing: Callable[[list[str]], None]):
        super().__init__(master, padding=10)
        self.ctl = ctl
        self.on_teach_missing = on_teach_missing
        self.last_missing: list[tuple[str, int]] = []
        self.current_doc = None

        self.v_paper = tk.StringVar(value="A4 (210×297 mm)")
        self.v_orientation = tk.StringVar(value="Dọc (Portrait)")
        self.v_background = tk.StringVar(value="Trắng (Plain)")
        self.v_spacing = tk.StringVar(value="")
        self.v_mode = tk.StringVar(value="Tự do (Semantic)")
        self.v_assemble = tk.BooleanVar(value=False)
        self.v_missing_grid = tk.BooleanVar(value=True)
        self.custom_paper_width: float | None = None
        self.custom_paper_height: float | None = None
        self.current_docx_path: str | None = None


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
        act_box = ttk.Frame(misswrap)
        act_box.pack(side="left", padx=6, anchor="n", pady=4)
        ttk.Button(act_box, text="Dạy các từ này →",
                   command=self.teach_missing).pack(fill="x", pady=2)
        ttk.Button(act_box, text="Dạy chữ cái thiếu →",
                   command=self.teach_missing_letters).pack(fill="x", pady=2)
        ttk.Button(act_box, text="Dạy bộ tối thiểu →",
                   command=self.teach_minimal_essentials).pack(fill="x", pady=2)

    def _build_options(self, right: ttk.Frame) -> None:
        # Nhóm 1: Trang & Nền giấy
        pnl_paper = ttk.LabelFrame(right, text="Trang & Nền giấy", padding=8)
        pnl_paper.pack(fill="x", pady=(0, 8))

        row_p = ttk.Frame(pnl_paper)
        row_p.pack(fill="x", pady=2)
        ttk.Label(row_p, text="Khổ giấy", width=14).pack(side="left")
        self.cb_paper = ttk.Combobox(
            row_p,
            textvariable=self.v_paper,
            values=[
                "A4 (210×297 mm)",
                "A5 (148×210 mm)",
                "A3 (297×420 mm)",
                "US Letter",
                "US Legal",
                "16:9 (Màn hình rộng)",
                "4:3 (Màn hình chuẩn)",
                "Tùy chỉnh...",
            ],
            state="readonly",
            width=16,
        )
        self.cb_paper.pack(side="left")
        self.cb_paper.bind("<<ComboboxSelected>>", self._on_paper_changed)
        self.btn_paper_custom = ttk.Button(row_p, text="Cỡ...", width=4, command=self.open_custom_paper_dialog)
        self.btn_paper_custom.pack(side="left", padx=4)

        row_o = ttk.Frame(pnl_paper)
        row_o.pack(fill="x", pady=2)
        ttk.Label(row_o, text="Chiều giấy", width=14).pack(side="left")
        self.cb_ori = ttk.Combobox(
            row_o,
            textvariable=self.v_orientation,
            values=["Dọc (Portrait)", "Ngang (Landscape)"],
            state="readonly",
            width=16,
        )
        self.cb_ori.pack(side="left")

        row_b = ttk.Frame(pnl_paper)
        row_b.pack(fill="x", pady=2)
        ttk.Label(row_b, text="Nền giấy", width=14).pack(side="left")
        self.cb_bg = ttk.Combobox(
            row_b,
            textvariable=self.v_background,
            values=[
                "Trắng (Plain)",
                "Dòng kẻ (Ruled)",
                "Dòng kẻ ngang (Lined)",
                "Dòng kẻ + lề",
                "Ô li (Graph)",
                "Chấm (Dotted)",
                "Isometric (Ô li xiên)",
                "Isometric chấm (Iso Dotted)",
                "Khuông nhạc (Music)",
            ],
            state="readonly",
            width=16,
        )
        self.cb_bg.pack(side="left")
        self.cb_bg.bind("<<ComboboxSelected>>", self._on_background_changed)

        row_sp = ttk.Frame(pnl_paper)
        row_sp.pack(fill="x", pady=2)
        ttk.Label(row_sp, text="Khoảng cách (mm)", width=14).pack(side="left")
        self.entry_spacing = ttk.Entry(row_sp, textvariable=self.v_spacing, width=8)
        self.entry_spacing.pack(side="left")
        ttk.Label(row_sp, text="vd: 5 ô li", foreground="#888888").pack(side="left", padx=4)

        row_m = ttk.Frame(pnl_paper)
        row_m.pack(fill="x", pady=2)
        ttk.Label(row_m, text="Chế độ DOCX", width=14).pack(side="left")
        self.cb_mode = ttk.Combobox(
            row_m,
            textvariable=self.v_mode,
            values=["Tự do (Semantic)", "Khóa bố cục & ảnh (Fidelity)"],
            state="readonly",
            width=20,
        )
        self.cb_mode.pack(side="left", fill="x", expand=True)
        self.cb_mode.bind("<<ComboboxSelected>>", self._on_mode_changed)
        self.v_mode.trace_add("write", lambda *args: self._on_mode_changed())

        # Nhóm 2: Tuỳ chỉnh nét chữ
        opt = ttk.LabelFrame(right, text="Tuỳ chỉnh nét chữ", padding=8)
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
        ttk.Checkbutton(opt, text="Ghép từ chữ cái khi thiếu từ nguyên khối",
                        variable=self.v_assemble).pack(anchor="w", pady=(2, 0))
        ttk.Checkbutton(opt, text="Tự động tạo file lưới ô khi thiếu mẫu (_thieu.xopp)",
                        variable=self.v_missing_grid).pack(anchor="w", pady=(2, 0))

        self._on_mode_changed()

    def _on_mode_changed(self, event=None) -> None:
        """Khóa các điều khiển giấy và nền khi ở chế độ Fidelity (lấy layout từ file gốc)."""
        is_fidelity = "fidelity" in self.v_mode.get().lower() or "khóa" in self.v_mode.get().lower()
        if is_fidelity:
            self.cb_paper.configure(state="disabled")
            self.btn_paper_custom.configure(state="disabled")
            self.cb_ori.configure(state="disabled")
            self.cb_bg.configure(state="disabled")
            self.entry_spacing.configure(state="disabled")
        else:
            self.cb_paper.configure(state="readonly")
            self.btn_paper_custom.configure(state="normal")
            self.cb_ori.configure(state="readonly")
            self.cb_bg.configure(state="readonly")
            self.entry_spacing.configure(state="normal")

    def _on_paper_changed(self, event=None) -> None:
        p_val = self.v_paper.get()
        if "tùy chỉnh" in p_val.lower():
            self.open_custom_paper_dialog()

    def _on_background_changed(self, event=None) -> None:
        bg_val = self.v_background.get().lower()
        if "ô li" in bg_val and "xiên" not in bg_val:
            if not self.v_spacing.get().strip():
                self.v_spacing.set("5.0")
        elif "dòng kẻ" in bg_val:
            if not self.v_spacing.get().strip():
                self.v_spacing.set("8.0")
        elif "trắng" in bg_val:
            self.v_spacing.set("")

    def open_custom_paper_dialog(self) -> None:
        init_w = 210.0
        init_h = 297.0
        dlg = CustomPaperDialog(self, initial_w=init_w, initial_h=init_h)
        self.wait_window(dlg)
        if dlg.result:
            self.custom_paper_width, self.custom_paper_height = dlg.result
            self.v_paper.set("Tùy chỉnh...")

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

        paper_text = self.v_paper.get().strip().lower()
        if "a5" in paper_text:
            paper = "a5"
        elif "a3" in paper_text:
            paper = "a3"
        elif "letter" in paper_text:
            paper = "letter"
        elif "legal" in paper_text:
            paper = "legal"
        elif "16:9" in paper_text:
            paper = "16:9"
        elif "4:3" in paper_text:
            paper = "4:3"
        elif "tùy chỉnh" in paper_text or "custom" in paper_text:
            paper = "custom"
        else:
            paper = "a4"

        ori_text = self.v_orientation.get().strip().lower()
        orientation = "landscape" if "ngang" in ori_text or "landscape" in ori_text else "portrait"

        bg_text = self.v_background.get().strip().lower()
        bg_margin = None
        if "iso dotted" in bg_text or "isometric chấm" in bg_text or "iso_dotted" in bg_text:
            bg_style = "iso_dotted"
        elif "ô li xiên" in bg_text or "iso_graph" in bg_text or "isometric" in bg_text:
            bg_style = "iso_graph"
        elif "ô li" in bg_text or "graph" in bg_text:
            bg_style = "graph"
        elif "lề" in bg_text or "margin" in bg_text:
            bg_style = "ruled"
            bg_margin = 72.0
        elif "lined" in bg_text or "kẻ ngang" in bg_text:
            bg_style = "lined"
        elif "dòng kẻ" in bg_text or "ruled" in bg_text:
            bg_style = "ruled"
        elif "chấm" in bg_text or "dotted" in bg_text:
            bg_style = "dotted"
        elif "khuông nhạc" in bg_text or "music" in bg_text:
            bg_style = "music"
        else:
            bg_style = "plain"

        from chuviettay.document.page_format import parse_length

        bg_spacing = None
        spacing_s = self.v_spacing.get().strip()
        if spacing_s:
            try:
                if re.match(r"^\d+(?:\.\d+)?$", spacing_s):
                    bg_spacing = parse_length(f"{spacing_s}mm")
                else:
                    bg_spacing = parse_length(spacing_s)
            except ValueError as e:
                raise ValueError(f"Khoảng cách nền không hợp lệ: {spacing_s}") from e

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
            paper=paper,
            orientation=orientation,
            paper_width=self.custom_paper_width,
            paper_height=self.custom_paper_height,
            background=bg_style,
            background_spacing=bg_spacing,
            background_margin=bg_margin,
            mode=("fidelity" if ("khóa" in self.v_mode.get().lower() or "fidelity" in self.v_mode.get().lower()) else "semantic"),
            missing_grid=self.v_missing_grid.get(),
            assemble_letters=self.v_assemble.get(),
        )
        opts.validate()
        return opts


    def _on_text_modified(self, event=None) -> None:
        self.current_doc = None
        self.current_docx_path = None

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
            self.current_docx_path = path if ext == ".docx" else None
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
            if opts.mode == "fidelity":
                if not self.current_docx_path:
                    messagebox.showerror(
                        "Chế độ Fidelity",
                        "Chế độ khóa bố cục (Fidelity) chỉ áp dụng cho tệp .docx đã mở bằng nút 'Mở tài liệu'.\n"
                        "Vui lòng chuyển sang chế độ 'Tự do (Semantic)' cho văn bản gõ trực tiếp hoặc tệp khác.",
                    )
                    return
                result = self.ctl.write_docx_fidelity(self.current_docx_path, opts, out)
            elif self.current_doc is not None:
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

    def teach_minimal_essentials(self) -> None:
        todo = self.ctl.missing_minimal_essentials()
        if not todo:
            messagebox.showinfo("Đầy đủ", "Kho mẫu đã có đủ bộ tối thiểu (chữ số, dấu câu và các từ phổ biến).")
            return
        self.on_teach_missing(todo)

    def teach_missing_letters(self) -> None:
        if not self.last_missing:
            messagebox.showinfo("Không có gì để dạy", "Chưa có từ nào đang thiếu.")
            return
        words = [w for w, _n in self.last_missing]
        ranked = self.ctl.missing_letters_for_words(words, strict_case=self.v_strict.get())
        if not ranked:
            messagebox.showinfo("Đầy đủ", "Tất cả các chữ cái và dấu thanh cấu thành đều đã có trong kho!")
            return
        self.on_teach_missing([item[0] for item in ranked])
