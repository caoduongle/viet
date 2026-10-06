# Báo cáo Giai đoạn 1 (G1): MVP Kỹ thuật & Cầu nối Browser

**Ngày**: 2026-10-06  
**Trạng thái**: HOÀN THÀNH — ĐÃ ĐẠT TOÀN BỘ TIÊU CHÍ CHECKPOINT G1  
**Mục tiêu**: Kiểm chứng chạy lõi Python trong trình duyệt qua Pyodide 314.0.7, ranh giới kiến trúc MVC, build tĩnh dist sạch, và khởi chạy webapp tối thiểu nạp kho tổng hợp.

---

## 1. Kết quả Kiểm thử & Độ bao phủ

1. **Bộ kiểm thử CPython (`pytest`)**:
   - Tổng cộng: **1.087 passed, 8 skipped** (do môi trường không có Tkinter), **0 failed**.
   - Toàn bộ các thay đổi lõi trong danh sách đóng (3.1, 3.2, 3.3) và test D6 đều xanh 100%.
2. **Golden Master trong Pyodide 314.0.7 (`node scripts/test_golden_pyodide.mjs`)**:
   - Cả **8/8 ca kiểm thử trùng khớp 100% từng byte mã băm SHA-256** của file `.xopp` và `_thieu.xopp`:
     - `co_ban`: PASS
     - `nhieu_trang`: PASS
     - `strict_case`: PASS
     - `tuy_chon`: PASS
     - `assemble_letters`: PASS
     - `math`: PASS
     - `table`: PASS
     - `markdown_list`: PASS
3. **Kiểm tra rủi ro hợp nhất đa tab MEMFS (`test_bank_merge_memfs.mjs`)**:
   - Thử nghiệm hai phiên bản `Bank` độc lập cùng thao tác ghi/xóa trên một file trong MEMFS.
   - Cơ chế `mtime`/`size` và `merge_bank_dicts()` bảo toàn toàn bộ mẫu, tombstones hoạt động đúng không bị hồi sinh. Không cần kích hoạt thay đổi 3.4.
4. **Kiểm tra kiến trúc & cách ly Tkinter (`test_bridge_no_tkinter.mjs`)**:
   - Khi nạp `chuviettay.browser.bridge` trong Pyodide Web Worker, `sys.modules` hoàn toàn KHÔNG có `tkinter`, `chuviettay.view`, `gui`, hay `cli`.
   - `tests/test_architecture.py` mở rộng quét đệ quy đạt 17/17 checks.

---

## 2. Các Thay đổi Lõi đã Thực hiện (Danh sách đóng)

- **Thay đổi 3.1**: Thêm tham số `timer_factory` tiêm được vào `AppController.__init__` (mặc định giữ nguyên `threading.Timer` cho CLI/Desktop; Web Client tiêm dummy timer không thread).
- **Thay đổi 3.2**: Tách toàn bộ logic hình học canvas và quy đổi `strokes_to_bank_units` từ `view/word_canvas.py` sang module độc lập `controller/teach_geometry.py`. `word_canvas.py` re-export nguyên vẹn.
- **Thay đổi 3.3**: Thêm accessor chỉ đọc `list_label_samples(label, category)` trả bản sao mẫu chữ an toàn tại `AppController`.
- **D3 (Đã duyệt)**: Thêm thuộc tính `stable_variants: bool = False` vào `WriteOptions`.
- **D6 (Đã duyệt)**: Sửa `tests/test_paths_logging.py` bằng `monkeypatch` / `tmp_path`, loại bỏ phụ thuộc vào file kho thật ở gốc repo.

---

## 3. Bản Đóng Gói Phân Phối (`webapp/dist/`)

- File zip mã nguồn sạch: `chuviettay.zip` chỉ nặng **134 KB**.
- Runtime Pyodide 314.0.7 tự host toàn bộ trong `dist/pyodide/`.
- 3 Pure-python wheels khởi động: `markdown-it-py 4.2.0`, `mdit-py-plugins 0.6.1`, `mdurl 0.1.2`.
- 2 Wheels nạp lười: `python-docx 1.1.2`, `lxml 6.1.3` (WASM).
- **Sanity Check**: Quét đệ quy `dist/` đạt chuẩn 100% không chứa bất kỳ file `*.json.gz`, `tests/`, `specs/`, hay mã desktop `view/`, `cli.py`, `gui.py`.

---

## 4. Xác nhận Checkpoint Server Tĩnh (`verify_g1_server.mjs`)

- Đã khởi chạy máy chủ thử nghiệm HTTP tại `http://localhost:8000`.
- Nạp thành công kho mẫu tổng hợp fixture `tests/data/kho_mau_tong_hop.json.gz`.
- Thống kê kho mẫu hiển thị chính xác: **13 từ, 99 mẫu nét**.
