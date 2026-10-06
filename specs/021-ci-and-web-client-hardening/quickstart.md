# Quickstart & Verification Guide: 021 — Sửa lỗi CI và hoàn thiện Web Client

## Mục đích
Tài liệu hướng dẫn từng bước kiểm chứng độc lập các sửa đổi và tính năng mới trên môi trường phát triển cục bộ và CI.

---

## 1. Nghiệm thu Phần A (Sửa 2 lỗi CI)

### A.1. Kiểm thử cách ly `test_build_web.py`
1. Khi có `node_modules` và đặt `REQUIRE_WEB_BUILD=1`:
   ```bash
   $env:REQUIRE_WEB_BUILD="1"
   python -m pytest tests/test_build_web.py -vv --timeout=300
   ```
   **Kết quả mong đợi**: Toàn bộ tests trong `test_build_web.py` PASS, thư mục `webapp/dist/` không bị thay đổi mtime.

2. Thử nghiệm hành vi khi thiếu `node_modules`:
   - Nếu đổi tên tạm `node_modules/pyodide` và chạy `pytest tests/test_build_web.py` (không có env `REQUIRE_WEB_BUILD`):
     **Kết quả**: Skipped với thông báo rõ ràng.
   - Nếu chạy với `REQUIRE_WEB_BUILD=1`:
     **Kết quả**: Failed ngay lập tức (không skip).

### A.2. Kiểm thử an toàn đường dẫn `build_web.py`
```bash
python scripts/build_web.py --dist .
python scripts/build_web.py --dist /
python scripts/build_web.py --dist webapp/css
```
**Kết quả mong đợi**: Thoát với mã lỗi `exit != 0`, in cảnh báo từ chối xoá thư mục, mã nguồn repo nguyên vẹn 100%.

### A.3. Cài đặt trên Python 3.14
```bash
pip install -r requirements-dev.txt
```
**Kết quả mong đợi**: Cài đặt thành công, không gặp lỗi `Requires-Python <3.14` từ `pyinstaller`.

---

## 2. Nghiệm thu Phần B (Sửa lỗi thực tế phát hiện được)

### B.1. Kiểm thử Service Worker cập nhật
1. Chạy `python scripts/build_web.py`.
2. Kiểm tra `webapp/dist/sw.js`:
   - `CACHE_NAME` chứa chuỗi hash 12 ký tự ngẫu nhiên dựa trên nội dung tệp.
   - `PRECACHE_URLS` chỉ chứa các tệp thực sự tồn tại trong `dist`.
3. Chạy Playwright test xác nhận cập nhật SW khi có bản build mới.

### B.2. Kiểm thử mở tệp `.docx` trong trình duyệt
1. Chạy Playwright test upload file `tests/fixtures/sample.docx` vào `#input-open-file`.
2. Kiểm tra nội dung text trích xuất hiển thị trong ô soạn thảo `#editor-text`.

### B.3. Chạy toàn bộ bộ kiểm thử JS và Browser
```bash
npm run test:unit
npm run test:browser
```
**Kết quả mong đợi**: PASS 100% trên cả Windows và Linux.

### B.4. Kiểm tra Golden Master Pyodide 314.0.7
```bash
node scripts/test_golden_pyodide.mjs
```
**Kết quả mong đợi**: 8/8 test cases PASS (SHA-256 các tệp `.xopp` trùng khớp từng byte).
