# Interface Contract: Worker Lifecycle & Recovery Protocol (CTR-044-WORKER-LIFECYCLE)

**Status**: Active
**Version**: 2.0.0
**Feature**: `specs/044-worker-and-seed-integrity`

---

## 1. Scope & Purpose
Hợp đồng này quy định chi tiết về cơ chế khởi tạo, xử lý sự cố, khôi phục và đồng bộ trạng thái của Pyodide Web Worker và Web Client UI.

---

## 2. Timeout Disaggregation Protocol

### 2.1 Ready Handshake Timeout
- Giai đoạn: Từ khi gọi `new Worker(...)` đến khi Worker gửi thông điệp `{ type: "READY" }` hoặc `{ type: "ERROR" }`.
- Thời hạn mặc định: 15,000ms.
- Hành vi bắt buộc:
  - Ngay khi nhận được `type === "READY"` hoặc `type === "ERROR"`, bộ đếm thời gian `readyTimer` **BẮT BUỘC ĐƯỢC CLEAR NGAY LẬP TỨC** (`clearTimeout(readyTimer); readyTimer = null;`).
  - Tuyệt đối không để `readyTimer` tiếp tục chạy trong suốt thời gian thực thi `onWorkerReady()` hoặc nạp kho mẫu.

### 2.2 Bank Reload Timeout
- Giai đoạn: Thực thi trong `onWorkerReady()`, gửi lệnh `load_bank` sang Worker qua `sendWorkerMessage("load_bank", { gzBytes, createIfMissing: false }, timeoutMs)`.
- Thời hạn: Sử dụng timeout độc lập của giao thức request/response (mặc định 60,000ms).
- Nếu nạp kho thất bại (do tệp hỏng hoặc lỗi logic), Worker không bị chấm dứt vật lý nếu lỗi chỉ xuất phát từ dữ liệu nạp. Giao diện hiển thị thông báo lỗi và mở lại nút "Thử lại".

---

## 3. Worker Generation Isolation Protocol

1. **Generation Counter**:
   - Khởi tạo `let workerGeneration = 0;`.
   - Mỗi lần chấm dứt hoặc khởi động lại Worker, biến này phải tăng nguyên tử: `workerGeneration++`.
2. **Message Filtering**:
   - Khi gắn `targetWorker.onmessage`, `targetWorker.onerror`, `targetWorker.onmessageerror`, lưu lại `const generation = activeGen;`.
   - Bất kỳ thông điệp nào đến từ một Worker có `generation !== workerGeneration` phải bị loại bỏ lập tức (`return;`).
3. **Async Callback Generation Check**:
   - Trong các bước bất đồng bộ của `onWorkerReady()`, kiểm tra lại `if (generation !== workerGeneration) return;` trước khi ghi nhận trạng thái lên giao diện.

---

## 4. Resilient UI Initialization Protocol

1. **One-Time Listener Attachment**:
   - Cờ `isDomListenersAttached` chỉ được phép chuyển sang `true` **SAU KHI** tất cả các listeners bắt buộc (`initBankTab`, `initWriteTab`, `TeachController.init`, `BroadcastChannel`, `visibilitychange`, `pagehide`) đã hoàn tất không có lỗi.
2. **Error Rollback**:
   - Nếu bất kỳ bước nào trong khối khởi tạo DOM ném ngoại lệ:
     ```javascript
     try {
       // ... đính kèm listeners ...
       isDomListenersAttached = true;
     } catch (err) {
       isDomListenersAttached = false;
       throw err;
     }
     ```
   - Lần khôi phục kế tiếp phải được phép thực thi lại toàn bộ khối này để không làm tê liệt giao diện người dùng.
