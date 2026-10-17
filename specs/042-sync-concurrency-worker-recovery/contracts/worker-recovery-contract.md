# Contract: Worker Lifecycle, Generation Isolation & Interactive Recovery

**Location**: `specs/042-sync-concurrency-worker-recovery/contracts/worker-recovery-contract.md`  
**Target Module**: `webapp/js/app.js` & `webapp/index.html`

---

## 1. UI Elements Contract

### Status Bar & Splash Error Recovery Controls
- Trong `.status-bar` của `webapp/index.html` (và tự động tạo động nếu chạy trong môi trường test DOM tối giản):
  - Element ID: `#btn-worker-retry`
  - Class: `btn-tool`
  - Text Content: `"Thử lại"`
  - Trạng thái mặc định: `display: none;`
  - Khi `handleWorkerFatalError()` được kích hoạt:
    - Hiển thị `#btn-worker-retry` (`display: inline-block`), cho phép người dùng bấm để khôi phục bộ xử lý nền ngay cả sau khi ứng dụng đã khởi động xong (màn hình splash đã ẩn) mà không làm mất văn bản đang soạn trong `#editor-text`.
    - Nếu màn hình `#splash-screen` vẫn đang hiển thị (lỗi trong lúc khởi động lần đầu), hiển thị thông báo lỗi kèm khả năng bấm `#btn-worker-retry`.

---

## 2. Generation Isolation & One-Time UI Initialization

### `workerGeneration` Counter
- Biến cấp module `let workerGeneration = 0;` tăng lên mỗi khi khởi tạo hoặc chấm dứt Worker.
- `attachWorkerHandlers(targetWorker, generation = workerGeneration)`:
  - Mọi callback `onmessage`, `onerror`, `onmessageerror` kiểm tra `if (generation !== workerGeneration) return;` ở dòng đầu tiên, đảm bảo thông điệp hoặc sự kiện muộn từ Worker cũ đã bị hủy không bao giờ ảnh hưởng đến phiên mới.

### Separation of UI Setup vs Worker Hydration in `onWorkerReady()`
- Biến cờ `let isUiInitialized = false;` bảo vệ phần đăng ký sự kiện giao diện một lần duy nhất:
  - Khi `onWorkerReady()` chạy lần đầu (`!isUiInitialized`): khởi tạo `initBankTab`, `initWriteTab`, `TeachController`, `storage.getSyncChannel`, `visibilitychange`, `pagehide`, `initQuotaAndBackupReminders`, `initGuideModal`, rồi đặt `isUiInitialized = true`.
  - Khi `onWorkerReady()` chạy ở các lần khôi phục tiếp theo (`isUiInitialized === true`): **không** đăng ký lại các DOM event listeners, chỉ thực hiện nạp lại dữ liệu hồ sơ đang hoạt động từ IndexedDB vào Worker mới:
    ```javascript
    await sendWorkerMessage("load_bank", {
      gzBytes: Array.from(new Uint8Array(profile.data)),
      createIfMissing: false,
    });
    await refreshBankView();
    if (window.__teachController) {
      await window.__teachController.refresh();
    }
    ```

---

## 3. Interactive Recovery Function Contract

### `recoverWorker()`
```typescript
function recoverWorker(): Promise<boolean>;
```

### Steps
1. Nếu `isRecovering === true`, trả về Promise đang chạy (chống bấm đúp nhiều lần liên tiếp).
2. Đặt `isRecovering = true`, khóa nút `#btn-worker-retry` (`disabled = true`) và đặt trạng thái `setStatus("status_loading", false, true)`.
3. Chấm dứt Worker cũ nếu tồn tại:
   - Tăng `workerGeneration++`.
   - Nếu `worker && typeof worker.terminate === "function"`, gọi `worker.terminate()`.
   - Đặt `worker = null`.
4. Dọn dẹp toàn bộ `pendingRequests`:
   - Xóa mọi `req.timer`, reject với `new Error("Bộ xử lý nền đã được khởi động lại.")`, và gọi `pendingRequests.clear()`.
5. Khởi tạo Worker mới và chờ tín hiệu `"READY"` (hoặc hoàn tất nạp lại kho mẫu `load_bank` với đúng tham số `{ gzBytes, createIfMissing: false }`).
6. Khi hoàn tất:
   - Ẩn nút `#btn-worker-retry` (`display: none`), mở khóa `disabled = false`, đặt `isRecovering = false`.
   - Đặt trạng thái `setStatus("status_ready")`.
   - Trả về `true`.

---

## 4. Worker Timeout & Idempotency Safety Contract

### Rules
1. Vì Pyodide thực thi đơn luồng trong Web Worker, khi bất kỳ yêu cầu nào trong `sendWorkerMessage(method, params, timeoutMs)` bị quá thời gian chờ (`WorkerTimeoutError`):
   - Worker đó đang bị treo trong lệnh gọi đồng bộ hoặc có nguy cơ hoàn tất muộn và làm biến đổi trạng thái MEMFS / toàn cục chồng lấn với lần thử lại tiếp theo.
   - Hệ thống **BẮT BUỘC**:
     1. Xóa yêu cầu quá hạn khỏi `pendingRequests`.
     2. Chấm dứt ngay lập tức Worker bị treo (`worker.terminate()`, tăng `workerGeneration++`, đặt `worker = null`) để hủy vật lý công việc đang chạy ngầm, ngăn chặn 100% nguy cơ thực thi trùng lặp khi người dùng thử lại.
     3. Kích hoạt `handleWorkerFatalError(...)` để từ chối các yêu cầu còn lại trong hàng đợi và hiển thị nút `#btn-worker-retry` trên giao diện.
     4. Reject Promise của yêu cầu bị quá hạn với `WorkerTimeoutError`.
