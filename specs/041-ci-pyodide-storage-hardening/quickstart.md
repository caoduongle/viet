# Quickstart Validation Guide: CI Pyodide Hardening, Storage & Worker

**Feature**: `041-ci-pyodide-storage-hardening`  
**Date**: 2026-10-16  
**Status**: Completed  

---

## 1. Điều kiện tiên quyết (Prerequisites)

- **Node.js**: >= 20.x
- **Python**: >= 3.12 (khuyên dùng Python 3.12 hoặc 3.13)
- **Dependencies**: `pip install -r requirements-dev.txt`, `npm ci`
- **Dist Web Client**: Phải được xây dựng trước (`python scripts/build_web.py`)

---

## 2. Kịch bản Xác thực 1: Khôi phục và Xác thực Golden Master trong Pyodide (US1)

Mục tiêu: Đảm bảo toàn bộ 8 ca kiểm thử Golden Master chạy thành công 100% trong môi trường WebAssembly (Pyodide v314.0.7), loại bỏ lỗi giả ở ca `markdown_list`.

### Lệnh thực thi:
```bash
node scripts/test_golden_pyodide.mjs
```

### Kết quả kỳ vọng:
- Console hiển thị danh sách 8 ca kiểm thử:
  ```text
  ================ KẾT QUẢ GOLDEN MASTER TRONG PYODIDE ================
    [PASS] co_ban: SHA-256 trùng khớp 100%
    [PASS] strict_case: SHA-256 trùng khớp 100%
    [PASS] tuy_chon: SHA-256 trùng khớp 100%
    [PASS] nhieu_trang: SHA-256 trùng khớp 100%
    [PASS] assemble_letters: SHA-256 trùng khớp 100%
    [PASS] math: SHA-256 trùng khớp 100%
    [PASS] table: SHA-256 trùng khớp 100%
    [PASS] markdown_list: SHA-256 trùng khớp 100% (tệp chính & lưới phụ)
  ====================================================================
  Tất cả 8 ca Golden Master trong Pyodide 314.0.7 đã VƯỢT QUA thành công!
  ```
- Mã thoát (exit code): `0`.

---

## 3. Kịch bản Xác thực 2: Kiểm thử Giao dịch Lưu trữ & Đồng bộ Đa tab (US2)

Mục tiêu: Đảm bảo các thao tác ghi vào IndexedDB chỉ xác nhận khi `tx.oncomplete` thành công; bắt đúng `QuotaExceededError` khi giao dịch bị hủy; và không xảy ra xung đột khi thiếu Web Locks.

### Lệnh thực thi:
```bash
# 1. Chạy unit tests Node.js
npm run test:unit

# 2. Chạy E2E đa tab (bao gồm kịch bản thiếu Web Locks)
npx playwright test tests/e2e/multitab.spec.ts
```

### Kết quả kỳ vọng:
- Các ca kiểm thử trong `tests/js/storage.test.mjs` xác nhận:
  - Giao dịch bị hủy (`tx.onabort`) trả về Promise rejected và bảo toàn mã lỗi `QuotaExceededError`.
  - Cập nhật dấu thời gian không bị lệch (`localSyncedTimestamp === savedProfile.updated_at`).
  - Khóa dự phòng hoạt động tuần tự khi `navigator.locks` là undefined.
- Kịch bản Playwright `tests/e2e/multitab.spec.ts` (cả có và không có Web Locks) đều hội tụ thành công, không mất dữ liệu.

---

## 4. Kịch bản Xác thực 3: Kiểm thử Khả năng Phục hồi Worker & Wheel DOCX (US3)

Mục tiêu: Kiểm thử cơ chế timeout và xử lý lỗi mạng khi tải wheel DOCX.

### Lệnh thực thi:
```bash
npm run test:unit
```

### Kết quả kỳ vọng:
- Các ca kiểm thử trong `tests/js/worker_resilience.test.mjs` mô phỏng:
  - Worker timeout sau khoảng thời gian quy định, tự động reject Promise và loại bỏ khỏi hàng đợi.
  - Phản hồi Worker đến muộn sau khi timeout được bỏ qua an toàn.
  - Sự kiện `worker.onerror` giải phóng toàn bộ pending requests và kích hoạt trạng thái lỗi.
  - Thao tác nạp wheel DOCX dừng ngay khi `resp.ok === false` (HTTP 404 hoặc lỗi mạng).

---

## 5. Kịch bản Xác thực 4: Kiểm tra Toàn diện CI Gates

Chạy toàn bộ chuỗi kiểm định chất lượng giống hệt luồng GitHub Actions:

```bash
# 1. Linting
ruff check .

# 2. Syntax verification
python -m compileall -q .

# 3. Python core test suite
python -m pytest -vv -s --timeout=60 -m "not benchmark"

# 4. Build web client
python scripts/build_web.py

# 5. Verify Pyodide Golden Master
node scripts/test_golden_pyodide.mjs

# 6. JavaScript & Browser bridge tests
npm run test:unit
npm run test:browser

# 7. Playwright E2E tests
npx playwright test tests/e2e/multitab.spec.ts
```

### Kết quả kỳ vọng:
- Tất cả các bước đều vượt qua với mã thoát `0`.
