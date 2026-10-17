# Quickstart Validation Guide: Feature 042

**Feature Branch**: `042-sync-concurrency-worker-recovery`  
**Date**: 2026-10-17

Hướng dẫn này cung cấp các kịch bản kiểm thử tự động và thủ công để xác thực độc lập 4 User Stories của Feature 042.

---

## 1. Môi trường & Điều kiện tiên quyết

- Đảm bảo môi trường đã cài đặt đầy đủ dependencies:
  - Python >= 3.10 (khuyến nghị Python 3.12, 3.13 hoặc 3.14).
  - Node.js >= 18.
  - Các gói npm đã cài đặt (`npm install` hoặc `npm ci`).

---

## 2. Kịch bản Kiểm thử Tự động

### Kịch bản 1: Kiểm thử Đơn vị Quản lý Lưu trữ & Xung đột 3 Trạng thái (US1)
Xác thực:
- `saveProfile` bắt lỗi khi lưu hồ sơ đã bị xóa (`expectedUpdatedAt` là số nhưng hồ sơ không còn).
- `saveProfile` bắt lỗi khi 2 phiên cùng khởi tạo mới đồng thời (`expectedUpdatedAt === null` nhưng hồ sơ đã có).
- `executeTransaction` tự động gọi `tx.abort()` khi có ngoại lệ đồng bộ trong `operationFn`.
- `syncAndSaveActiveProfile` ném lỗi `ProfileDeletedConflictError` khi hồ sơ bị xóa trong lúc đồng bộ.

```powershell
npm run test:unit
```
*Kết quả kỳ vọng*: Toàn bộ các test suite JavaScript (bao gồm `tests/js/storage.test.mjs`) pass 100%.

---

### Kịch bản 2: Kiểm thử Cuộc đua Đa tab Thực sự & Không hồi sinh Ký tự đã xóa (US2)
Xác thực:
- Hai context/tab cùng đọc phiên bản ban đầu, kích hoạt lưu đồng thời (không có sleep giữa chừng).
- Tab chậm hơn phát hiện `ConcurrencyConflictError`, tự động kích hoạt retry hợp nhất.
- Bộ mẫu chữ hội tụ giữ đủ nét của cả 2 tab.
- Xóa ký tự ở một tab không bị tab kia phục hồi lại (tombstone preservation).
- Chạy cả trong chế độ có Web Locks và khi `navigator.locks = undefined`.

```powershell
npx playwright test tests/e2e/multitab.spec.ts
```
*Kết quả kỳ vọng*: Cả 3 test case đa tab (tuần tự, không có Web Locks, và cuộc đua đồng thời thực sự) đều PASS.

---

### Kịch bản 3: Kiểm thử Khôi phục Worker Tương tác & An toàn Timeout (US3)
Xác thực:
- Giả lập lỗi Worker (`onerror` hoặc `onmessageerror`) sau khi ứng dụng đã chạy.
- Nút "Thử lại" xuất hiện trên banner lỗi.
- Gọi `recoverWorker()`: Worker cũ bị terminate, Worker mới được tạo, nạp lại kho mẫu thành công và hệ thống trở lại trạng thái `READY`.
- Timeout với mutating method kích hoạt khởi động lại an toàn, ngăn duplicate execution.

```powershell
node --test tests/js/worker_resilience.test.mjs
```
*Kết quả kỳ vọng*: 100% test case trong `tests/js/worker_resilience.test.mjs` pass.

---

### Kịch bản 4: Kiểm thử Tính nguyên tử của Service Worker Cache (US4)
Xác thực:
- Build static web app với script đóng gói:
  ```powershell
  python scripts/build_web.py
  ```
- Kiểm tra file `webapp/dist/sw.js`:
  - `PRECACHE_URLS` chỉ chứa các file khởi động cốt lõi, trong khi `python_docx`, `lxml`, `typing_extensions` được tách sang `OPTIONAL_LAZY_URLS`.
  - Quá trình `install` tải toàn bộ `PRECACHE_URLS` vào bộ nhớ trước khi ghi và có khối `try/catch` bọc ngoài gọi `caches.delete(CACHE_NAME)` trước khi ném lỗi.
  - `await self.skipWaiting()` chỉ được gọi bên trong `event.waitUntil` sau khi toàn bộ tệp cốt lõi được nạp thành công.

---

## 3. Chạy Toàn bộ Chuỗi Cổng Chất lượng (Quality Gates)

```powershell
# 1. Lint Python
ruff check .

# 2. Bytecode compile
python -m compileall -q .

# 3. Core Python suite (1235+ tests)
python -m pytest -q -m "not benchmark"

# 4. Build web static
python scripts/build_web.py

# 5. Unit JS tests
npm run test:unit

# 6. Browser Bridge tests
npm run test:browser

# 7. Pyodide Golden Master
node scripts/test_golden_pyodide.mjs

# 8. Playwright E2E multitab
npx playwright test tests/e2e/multitab.spec.ts
```
