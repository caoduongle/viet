# Technical Research & Architectural Decisions: Feature 042

**Feature Branch**: `042-sync-concurrency-worker-recovery`  
**Date**: 2026-10-17  
**Scope**: Kiểm soát cạnh tranh 3 trạng thái, phục hồi Worker tương tác, nguyên tử hóa Service Worker cache, và kiểm thử race condition đa tab.

---

## 1. Research Topic 1: Concurrency Control Semantics (3-State OCC in IndexedDB)

### Problem & Analysis
Trong `webapp/js/storage.js`, `saveProfile(profile, expectedUpdatedAt)` hiện tại kiểm tra:
```javascript
const existing = getReq.result;
if (existing && existing.updated_at !== expectedUpdatedAt) {
  // ConcurrencyConflictError
}
```
- **Lỗ hổng 1 (Resurrection Bug trong `saveProfile`)**: Nếu hồ sơ đã bị xóa bởi tab khác, `existing` là `undefined`. Biểu thức `existing && ...` đánh giá thành `false`, dẫn tới `store.put(payload)` được gọi và vô tình làm sống lại hồ sơ đã xóa.
- **Lỗ hổng 2 (Resurrection Bug ngay đầu `syncAndSaveActiveProfile`)**: Nếu Tab 1 xóa hồ sơ *trước khi* Tab 2 gọi `syncAndSaveActiveProfile()`, thì ngay ở `attempt = 0`, `getProfile(activeId)` trả về `null`. Nếu Tab 2 gán `baseUpdatedAt = null`, nó sẽ hiểu nhầm là đang tạo hồ sơ mới và làm sống lại hồ sơ đã xóa.
- **Lỗ hổng 3 (Concurrent Initial Creation)**: Nếu `expectedUpdatedAt === undefined`, kiểm tra bị bỏ qua hoàn toàn. Khi 2 tab cùng khởi tạo hồ sơ lần đầu, tab đến sau ghi đè mất dữ liệu tab trước.
- **Lỗ hổng 4 (Same-Millisecond Timestamp Collision)**: Trong kiểm thử tự động hoặc thao tác cực nhanh, hai lệnh lưu trong cùng 1ms có cùng `Date.now()`, làm `existing.updated_at === expectedUpdatedAt` dù dữ liệu đã đổi.

### Decision
Triển khai cơ chế 3 trạng thái rõ ràng (Explicit 3-State OCC) kèm dấu thời gian đơn điệu chặt (Monotonic Timestamp):
1. **Existing Version Expectation (`typeof expectedUpdatedAt === "number"`)**:
   - Yêu cầu hồ sơ **bắt buộc phải tồn tại** và `existing.updated_at === expectedUpdatedAt`.
   - Nếu `!existing`: Hủy transaction (`tx.abort()`), ném `ConcurrencyConflictError` (Hồ sơ đã bị xóa bởi tab khác).
   - Nếu `existing.updated_at !== expectedUpdatedAt`: Hủy transaction (`tx.abort()`), ném `ConcurrencyConflictError` (Hồ sơ đã bị sửa đổi bởi tab khác).
2. **Non-existence Expectation (`expectedUpdatedAt === null`)**:
   - Yêu cầu hồ sơ **chưa từng tồn tại** (dành cho khởi tạo mới).
   - Nếu `existing`: Hủy transaction (`tx.abort()`), ném `ConcurrencyConflictError` (Hồ sơ đã được tạo bởi tab khác).
3. **Unconditional Write (`expectedUpdatedAt === undefined`)**:
   - Ghi đè trực tiếp không kiểm tra phiên bản (chỉ dành cho thao tác nạp đè kho chủ đích của người dùng).
4. **Monotonic Timestamp**:
   - Khi ghi bản cập nhật, đảm bảo `payload.updated_at = Math.max(payload.updated_at, existing ? existing.updated_at + 1 : 1)`.
5. **Deleted Profile Protection in `syncAndSaveActiveProfile()`**:
   - Nếu `!currentProfile` nhưng `localSyncedTimestamp > 0` (tab hiện tại từng nạp hồ sơ có thật trước đó), ném ngay `ConcurrencyConflictError` (`codeName = "ProfileDeletedConflictError"`) và dừng vòng lặp retry, tuyệt đối không tái tạo hồ sơ.

---

## 2. Research Topic 2: Synchronous Exception Safety in `executeTransaction()`

### Problem & Analysis
Nếu `operationFn` đã gọi `store.put(data)` rồi ném một Exception đồng bộ (sync throw), `catch (err)` hiện tại chỉ gọi `safeReject(err)` mà **không** gọi `tx.abort()`. Khi microtask kết thúc, IndexedDB vẫn có thể tự động commit các request đã xếp hàng trước đó.

### Decision
Thêm `try { tx.abort(); } catch (_) {}` trong khối `catch (err)` của `executeTransaction` trước khi gọi `safeReject(err)`.

---

## 3. Research Topic 3: Interactive Worker Recovery & Timeout Idempotency

### Problem & Analysis
1. `handleWorkerFatalError()` hiện tại chỉ ghi text yêu cầu tải lại trang, chưa có nút `#btn-worker-retry` tương tác.
2. Trong `webapp/js/app.js`, khi Worker mới gửi `{ type: "READY" }`, `attachWorkerHandlers()` gọi `onWorkerReady()`. Nếu gọi `onWorkerReady()` lần thứ 2 mà không có cờ bảo vệ `isUiInitialized`, toàn bộ DOM event listeners sẽ bị đăng ký trùng lặp.
3. Trong `webapp/js/worker/py-worker.js` (dòng 120), phương thức `"load_bank"` nhận `{ gzBytes, createIfMissing: false }` (không phải `{ bytes }`).
4. Vì Pyodide chạy đơn luồng trong Web Worker, khi bất kỳ yêu cầu nào bị `WorkerTimeoutError`, Worker đang bị treo hoặc vẫn đang chạy ngầm. Nếu không chấm dứt vật lý Worker cũ trước khi thử lại, tác vụ ngầm có thể hoàn tất muộn và gây thực thi trùng lặp.

### Decision
1. **Interactive Worker Recovery (`recoverWorker()`)**:
   - Có khóa `isRecovering` chống bấm đúp.
   - Tăng `workerGeneration++`, gọi `worker.terminate()`, dọn sạch `pendingRequests`.
   - Khởi tạo Worker mới với `attachWorkerHandlers(worker, workerGeneration)` (bỏ qua mọi thông điệp từ `generation` cũ).
   - Trong `onWorkerReady()`: dùng cờ `isUiInitialized` để chỉ khởi tạo DOM listeners ở lần đầu tiên; ở các lần phục hồi tiếp theo chỉ nạp lại `activeProfile` qua `sendWorkerMessage("load_bank", { gzBytes: Array.from(new Uint8Array(profile.data)), createIfMissing: false })` và làm mới view.
   - Hiển thị nút `#btn-worker-retry` trên thanh trạng thái `.status-bar` khi gặp lỗi.
2. **Timeout Physical Termination**:
   - Khi một yêu cầu bị `WorkerTimeoutError`, hệ thống lập tức gọi `worker.terminate()`, tăng `workerGeneration++`, và chuyển sang trạng thái lỗi qua `handleWorkerFatalError()` để ngăn chặn 100% việc thực thi trùng lặp ở hậu cảnh.

---

## 4. Research Topic 4: Atomic Service Worker Offline Cache

### Problem & Analysis
1. `webapp/sw.js` cần phiên bản hóa tên cache rõ ràng và chỉ gọi `self.skipWaiting()` bên trong `event.waitUntil` sau khi toàn bộ tài nguyên bắt buộc đã nạp thành công.
2. Nếu ghi từng tệp vào cache ngay khi từng `fetch` hoàn tất, một lỗi ở tệp cuối cùng sẽ để lại cache dở dang.
3. Các wheel DOCX lười (`stage: "lazy"` trong `scripts/vendor_lock.json`: `python_docx`, `lxml`, `typing_extensions`) cần tách sang `OPTIONAL_LAZY_URLS`, giữ nguyên tên `PRECACHE_URLS` cho tài nguyên cốt lõi để tương thích với `scripts/build_web.py` và `tests/e2e/sw-update.spec.ts`.

### Decision
1. **Fetch-All-First Atomic Precache**:
   - Tải và kiểm tra `resp.ok` cho toàn bộ `PRECACHE_URLS` trong bộ nhớ trước khi mở và ghi vào `CACHE_NAME`.
   - Nếu có bất kỳ lỗi nào, gọi `await caches.delete(CACHE_NAME)` trong khối `catch` và ném lỗi để hủy cài đặt nguyên tử.
   - Chỉ gọi `await self.skipWaiting()` sau khi mọi `cache.put()` đã hoàn tất.
2. **Tách `PRECACHE_URLS` và `OPTIONAL_LAZY_URLS`**:
   - Cập nhật `scripts/build_web.py` đọc `scripts/vendor_lock.json` để phân tách các wheel `"stage": "lazy"` vào `OPTIONAL_LAZY_URLS`, trong khi vẫn băm toàn bộ tệp trong `dist` để tính `CACHE_NAME`.

---

## 5. Research Topic 5: True Concurrent Multi-tab Race Condition Testing

### Decision
1. **E2E Race Test (`tests/e2e/multitab.spec.ts`)**:
   - Hai page cùng đọc phiên bản ban đầu, vẽ nét cho 2 ký tự khác nhau (hoặc 1 bên xóa, 1 bên thêm) và kích hoạt lưu chồng lấn qua `Promise.all([page1.click("#btn-teach-save"), page2.click("#btn-teach-save")])`.
   - Xác nhận cả hai thay đổi đều hội tụ, lệnh xóa không bị hồi sinh và không nhân đôi mẫu chữ.
2. **Unit Race Test (`tests/js/storage.test.mjs`)**:
   - Kiểm thử trực tiếp `ConcurrencyConflictError` $\rightarrow$ retry $\rightarrow$ merge $\rightarrow$ save, kiểm thử chặn hồi sinh hồ sơ đã xóa và kiểm thử hủy giao dịch khi lỗi đồng bộ.
