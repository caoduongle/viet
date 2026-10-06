# Research: Xóa Hàng Loạt Kho Mẫu & Chuyển Đổi Giao Diện Sáng / Tối

**Feature**: `027-batch-delete-and-theme-toggle`
**Spec**: [spec.md](./spec.md)

---

## 1. Cơ Chế Xóa Hàng Loạt (Batch Deletion) Trong Kho Mẫu

### Vấn đề hiện tại
- Trong `BankTab` (Desktop GUI) và `bank.js` (Web Client), người dùng chỉ có thể chọn một ký tự duy nhất trong danh sách rồi nhấn "Xóa".
- Mỗi thao tác xóa gọi một lệnh riêng lẻ: lấy lock, duyệt danh sách, cập nhật tombstone, rebuild chỉ mục, và ghi đĩa file `.json.gz`. Nếu xóa 30 ký tự, hệ thống phải thực hiện 30 lần giải nén/nén gzip và I/O đĩa.

### Giải pháp kỹ thuật
1. **Lớp Mô hình (`Bank` & `AppController`)**:
   - Thêm phương thức `drop_chars(items: list[tuple[str, str]] | list[str]) -> DropResult`:
     - Thực hiện toàn bộ thao tác trong MỘT lần giữ `with self._lock:`.
     - Phân loại danh mục cho từng ký tự (`letters`, `digits`, `punct`, `symbols`, `marks`).
     - Xóa các mẫu khỏi dict tương ứng, ghi nhận tombstone dạng `<cat>:<label>`.
     - Gọi `rebuild()` (dọn dẹp chỉ mục `marks` và `tl` nếu có) đúng một lần duy nhất.
     - Đánh dấu `self._dirty = True` và ghi đĩa một lần duy nhất qua `self.save()`.
2. **Giao diện Desktop GUI (`BankTab`)**:
   - Cấu hình `Listbox` với `selectmode="extended"` (hỗ trợ Shift-click, Ctrl-click kéo chọn dải mục).
   - Bổ sung nút: "Chọn tất cả" (`Select All`), "Bỏ chọn" (`Deselect All`).
   - Nút xóa cập nhật động: khi chọn 0 mục -> disabled; khi chọn $N \ge 1$ mục -> hiển thị `Xóa đã chọn ($N$)`.
   - Hộp thoại xác nhận `messagebox.askyesno`: "Bạn có chắc muốn xóa $N$ ký tự đã chọn (tổng cộng $M$ mẫu nét) khỏi kho mẫu? Thao tác này không thể hoàn tác."
3. **Giao diện Web Client (`bank.js` / `index.html`)**:
   - Thêm checkbox trên từng thẻ ký tự (`char-card`) hoặc chế độ chọn nhiều.
   - Thêm thanh thao tác nhanh trên đầu danh sách: nút "Chọn tất cả", "Bỏ chọn", và nút "Xóa đã chọn ($N$)".
   - Hộp thoại Modal / Confirm hiển thị rõ số lượng ký tự và mẫu nét bị xóa.
   - Gửi yêu cầu qua Pyodide worker: `worker.request("drop_chars", { chars: [...] })`.

### Quyết định & Đánh giá
- **Quyết định**: Triển khai `drop_chars` dạng batch transaction trong `Bank` và `AppController`, đảm bảo $O(1)$ lần nén gzip và I/O đĩa.
- **Lý do**: Tối ưu hiệu năng vượt trội, an toàn dữ liệu, ngăn ngừa tình trạng file kho bị ghi đè dở dang giữa các lần xóa.
- **Phương án thay thế bị bác bỏ**: Lặp vòng gọi `drop_char` nhiều lần — bị loại vì gây giật lag I/O đĩa và có nguy cơ lỗi race condition.

---

## 2. Cơ Chế Chuyển Đổi Giao Diện Sáng / Tối (Theme Toggle)

### Yêu cầu kiến trúc
Hệ thống gồm 2 môi trường trình diễn giao diện:
1. **Web Client** (HTML5, Vanilla CSS, JS, Canvas).
2. **Desktop GUI** (Python Tkinter / ttk, Canvas).

### Phương án cho Web Client (`webapp/`)
- **CSS Design Tokens**:
  - Khai báo CSS custom properties trong `:root[data-theme="light"]` và `:root[data-theme="dark"]`.
  - Bộ token:
    - `--bg-body`: `#ffffff` (light) / `#121212` (dark)
    - `--bg-surface`: `#f8f9fa` (light) / `#1e1e1e` (dark)
    - `--bg-card`: `#ffffff` (light) / `#252525` (dark)
    - `--text-primary`: `#212529` (light) / `#f1f3f5` (dark)
    - `--text-secondary`: `#6c757d` (light) / `#adb5bd` (dark)
    - `--border-color`: `#dee2e6` (light) / `#373a40` (dark)
    - `--canvas-bg`: `#ffffff` (light) / `#1a1a1a` (dark)
    - `--canvas-guide`: `#cccccc` (light) / `#404040` (dark)
    - `--canvas-ink`: `#000000` (light) / `#4dabf7` hoặc `#ffffff` (dark)
- **Tương thích Canvas & Guide Lines**:
  - Canvas vẽ nét chữ và hiển thị xem trước trang: tự động cập nhật màu đường kẻ chân chữ, ascender, descender và màu nét vẽ theo theme đang chọn để không bị chìm màu.
- **Persistence & Detection**:
  - Kiểm tra `localStorage.getItem("chuviettay_theme")`.
  - Nếu chưa có: fallback vào `window.matchMedia("(prefers-color-scheme: dark)").matches`.
  - Gắn sự kiện chuyển đổi vào nút ☀️ / 🌙 trên thanh header.

### Phương án cho Desktop GUI (`chuviettay/view/` & `gui.py`)
- **Tkinter/ttk Styling**:
  - Khởi tạo bảng màu tập trung `THEME_PALETTES = {"light": {...}, "dark": {...}}`.
  - Hàm `apply_theme(style, root, theme_name)`:
    - Cấu hình style cho `TFrame`, `TLabel`, `TButton`, `TNotebook`, `TEntry`.
    - Cấu hình màu nền cho các widget chuẩn Tk (`Listbox`, `Text`, `Canvas`).
- **Canvas Nét Chữ**:
  - Cập nhật màu vẽ lưới ô mốc trong `WordCanvas` và `BankTab`: nét kẻ mốc màu sáng/tương phản khi ở nền tối.
- **Lưu cấu hình**:
  - Lưu tùy chọn `theme` vào tệp cấu hình JSON người dùng trong thư mục cấu hình ứng dụng (`chuviettay/paths.py`).

### Quyết định & Đánh giá
- **Quyết định**: Sử dụng CSS Variables cho Web và Theme Palette Manager cho Tkinter.
- **Lý do**: Không thêm dependency bên ngoài, chạy mượt mà trên cả trình duyệt và mọi môi trường Python Tkinter.
