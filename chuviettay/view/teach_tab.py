"""Tab "Dạy từ mới": vẽ trực tiếp từng từ bằng chuột/bút cảm ứng, bấm Lưu là xong (KHÔNG
cần xuất/nạp file .xopp trung gian).

So với bản gốc:
  - Lưu từ / hiệu chỉnh cỡ tay đi qua controller.teach_word() (dùng chung công thức với
    lệnh `learn` ở model/calibration.py) thay vì tự viết lại công thức + tự thao tác
    bank.words/rebuild()/save() ngay trong hàm của nút bấm.
  - Hệ số cỡ tay của phiên là trạng thái NGHIỆP VỤ nên nằm ở Controller (ctl.session_scale);
    tab chỉ hiển thị nó.
  - Cờ "đang hiệu chỉnh" (_calib_pending) được tắt khi người dùng bỏ qua từ mốc hoặc xoá
    hàng đợi. Bản gốc để cờ này bật mãi trong trường hợp đó, khiến từ đầu tiên lưu sau
    đó bị coi nhầm là từ mốc hiệu chỉnh (nếu từ đó đã có mẫu sẵn trong kho).
"""
from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Iterable
from tkinter import messagebox, simpledialog, ttk

from chuviettay.controller.app_controller import AppController
from chuviettay.view.dialogs import report_error
from chuviettay.view.word_canvas import WordCanvas

_log = logging.getLogger(__name__)


class TeachTab(ttk.Frame):
    def __init__(self, master, ctl: AppController):
        super().__init__(master, padding=10)
        self.ctl = ctl
        self.queue: list[str] = []
        self.current: str | None = None
        self._calib_pending = False   # từ đầu hàng đợi đang là từ mốc hiệu chỉnh cỡ tay
        self._calibrated = False      # phiên này đã hiệu chỉnh cỡ tay ít nhất một lần

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Thêm từ vào hàng đợi:").pack(side="left")
        self.add_var = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.add_var, width=20)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.add_word())
        ttk.Button(top, text="Thêm", command=self.add_word).pack(side="left")
        ttk.Button(top, text="Bộ tối thiểu", command=self.add_minimal_essentials).pack(side="left", padx=6)
        ttk.Button(top, text="Nạp từ thông dụng còn thiếu...", command=self.add_seed).pack(side="left", padx=6)
        ttk.Button(top, text="Xoá hàng đợi", command=self.clear_queue).pack(side="left")
        ttk.Button(top, text="Hiệu chỉnh cỡ tay", command=self.start_calibration).pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(10, 0))

        qframe = ttk.LabelFrame(body, text="Hàng đợi", padding=6)
        qframe.pack(side="left", fill="y")
        self.qlist = tk.Listbox(qframe, height=18, width=22)
        self.qlist.pack(fill="y")

        work = ttk.Frame(body, padding=(12, 0, 0, 0))
        work.pack(side="left", fill="both", expand=True)

        self.word_lbl = ttk.Label(work, text="(hàng đợi trống)", font=("Sans", 26, "bold"))
        self.word_lbl.pack(anchor="w")
        self.hint_lbl = ttk.Label(work, foreground="#888888",
                                  text="Viết nhỏ, tự nhiên như chữ hằng ngày; đặt chữ TRÊN đường kẻ dưới.")
        self.hint_lbl.pack(anchor="w", pady=(0, 4))

        self.canvas = WordCanvas(work, get_xh=lambda: self.ctl.x_height)
        self.canvas.pack(fill="x")

        act = ttk.Frame(work)
        act.pack(fill="x", pady=8)
        ttk.Button(act, text="Hoàn tác nét", command=self.canvas.undo).pack(side="left")
        ttk.Button(act, text="Xoá hết", command=self.canvas.clear).pack(side="left", padx=6)
        ttk.Button(act, text="Bỏ qua từ này ⏭", command=self.skip_word).pack(side="left", padx=20)
        self.save_btn = ttk.Button(act, text="Lưu từ này & tiếp theo →", command=self.save_word)
        self.save_btn.pack(side="left")

        self.scale_lbl = ttk.Label(work, foreground="#888888")
        self.scale_lbl.pack(anchor="w", pady=(6, 0))
        self._update_scale_label()

        self._refresh()

    # ------------------------------------------------------------ hàng đợi
    def load_queue(self, words: Iterable[str]) -> None:
        for w in words:
            if w not in self.queue:
                self.queue.append(w)
        self._refresh()

    def add_word(self) -> None:
        w = self.add_var.get().strip()
        # Không tách theo khoảng trắng: gõ "cà phê" sẽ dạy đúng CỤM đó như một nhãn,
        # y hệt việc viết "cà phê" vào một ô khi dùng cách cũ qua Xournal++.
        if w and w not in self.queue:
            self.queue.append(w)
        self.add_var.set("")
        self._refresh()

    def add_minimal_essentials(self) -> None:
        todo = self.ctl.missing_minimal_essentials(exclude=self.queue)
        if not todo:
            messagebox.showinfo("Đầy đủ", "Kho mẫu đã có đủ bộ tối thiểu (chữ số, dấu câu và các từ phổ biến).")
            return
        self.queue.extend(todo)
        self._refresh()
        messagebox.showinfo("Đã nạp", "Đã thêm %d mục tối thiểu vào hàng đợi." % len(todo))

    def add_seed(self) -> None:
        n = simpledialog.askinteger("Nạp từ thông dụng", "Nạp bao nhiêu từ còn thiếu?",
                                    initialvalue=50, minvalue=1, maxvalue=5000, parent=self)
        if not n:
            return
        todo = self.ctl.missing_seed_words(n, exclude=self.queue)
        self.queue.extend(todo)
        self._refresh()
        messagebox.showinfo("Đã nạp", "Đã thêm %d từ vào hàng đợi." % len(todo))

    def clear_queue(self) -> None:
        self.queue = []
        self.current = None
        self._calib_pending = False
        self._refresh()

    def skip_word(self) -> None:
        self._calib_pending = False   # bỏ qua từ mốc = huỷ luôn việc hiệu chỉnh
        self._refresh(advance=True)

    # ------------------------------------------------------------ hiệu chỉnh cỡ tay
    def start_calibration(self) -> None:
        word = self.ctl.pick_calibration_word()
        if not word:
            messagebox.showinfo("Chưa có dữ liệu", "Kho mẫu chưa có từ nào để dùng làm mốc hiệu chỉnh.")
            return
        self._calib_pending = True
        self.queue.insert(0, word)
        self._refresh()
        messagebox.showinfo("Hiệu chỉnh cỡ tay",
                            "Viết từ '%s' đúng như bạn viết bình thường (không cần cố to/nhỏ), rồi bấm Lưu."
                            % word)

    def _update_scale_label(self) -> None:
        if self._calibrated:
            text = "Hệ số cỡ tay hiện tại: %.2fx" % self.ctl.session_scale
        else:
            text = "Hệ số cỡ tay hiện tại: 1.00x (chưa hiệu chỉnh)"
        self.scale_lbl.configure(text=text)

    def on_bank_changed(self) -> None:
        """MainWindow gọi khi người dùng đổi sang kho mẫu khác: Controller đã đặt lại hệ
        số cỡ tay về 1.0, chiều cao chữ thường (đường kẻ mốc) có thể khác."""
        self._calib_pending = False
        self._calibrated = False
        self._update_scale_label()
        self.canvas.draw_guides()

    # ------------------------------------------------------------ lưu / chuyển từ
    def save_word(self) -> None:
        if not self.current:
            return
        if not self.canvas.has_ink():
            messagebox.showwarning("Chưa có nét nào", "Hãy vẽ từ này trước khi lưu.")
            return
        label = self.current
        rel, width = self.canvas.to_bank_strokes(self.ctl.session_scale)
        use_deferred = (self.ctl.bank_size >= 30) if self.ctl else False
        try:
            if not self._calib_pending and self.ctl.is_letter_token(label):
                outcome = self.ctl.teach_letter(label, rel, width, deferred_save=use_deferred)
            else:
                outcome = self.ctl.teach_word(
                    label, rel, width,
                    calibrating=self._calib_pending,
                    recompute=self.canvas.to_bank_strokes,
                    deferred_save=use_deferred)   # L14: Lưu hoãn cho kho lớn (>=30 từ) để UI <50ms
        except Exception as e:  # noqa: BLE001
            report_error("Lỗi khi lưu", e, _log)
            return
        if outcome.recalibrated:
            self._calibrated = True
        self._calib_pending = False
        self._update_scale_label()
        self._refresh(advance=True)

    # ------------------------------------------------------------ vẽ lại UI
    def _refresh(self, advance: bool = False) -> None:
        if advance and self.queue:
            self.queue.pop(0)
        self.qlist.delete(0, "end")
        for w in self.queue:
            self.qlist.insert("end", w)
        self.current = self.queue[0] if self.queue else None
        self.canvas.clear()
        self.canvas.draw_guides()
        if self.current:
            title = self.current + ("   (từ để hiệu chỉnh cỡ tay)" if self._calib_pending else "")
            self.word_lbl.configure(text=title)
            self.save_btn.state(["!disabled"])
        else:
            self.word_lbl.configure(text="(hàng đợi trống -- thêm từ ở trên)")
            self.save_btn.state(["disabled"])
