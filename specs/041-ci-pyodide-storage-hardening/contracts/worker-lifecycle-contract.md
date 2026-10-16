# Interface Contract: Web Worker Lifecycle, Timeout & Error Protocol

**Document**: `worker-lifecycle-contract.md`  
**Feature**: `041-ci-pyodide-storage-hardening`  
**Consumer**: `webapp/js/app.js`, `webapp/js/worker/py-worker.js`  

---

## 1. Giao thức Gửi Yêu cầu (`sendWorkerMessage`)

```typescript
function sendWorkerMessage<T = any>(
  method: string,
  params?: Record<string, any>,
  timeoutMs?: number // Mặc định: 60000ms
): Promise<T>;
```

### Tiêu chuẩn xử lý:
1. **Quản lý Hàng đợi Yêu cầu**:
   - Mỗi yêu cầu được cấp một `id` duy nhất tăng dần và lưu vào `pendingRequests` Map kèm bộ hẹn giờ `setTimeout(timeoutMs)`.
2. **Quy tắc Quá hạn (Timeout Handling)**:
   - Khi hết hạn `timeoutMs` mà chưa nhận được thông điệp phản hồi từ Worker:
     - Gỡ bỏ `id` khỏi `pendingRequests`.
     - Reject Promise với `WorkerTimeoutError` (`"Yêu cầu xử lý Worker [method] đã hết hạn sau X ms"`).
     - Nếu thông điệp phản hồi đến muộn sau khi đã timeout, bỏ qua thông điệp mà không gây lỗi hoặc xung đột trạng thái.
3. **Quy tắc Sự cố Worker (Worker Crash & Error Handling)**:
   - Luồng chính đăng ký sự kiện `worker.onerror` và `worker.onmessageerror`.
   - Khi xảy ra lỗi sự cố Worker:
     - Toàn bộ các yêu cầu đang chờ trong `pendingRequests` bị reject với thông báo lỗi rõ ràng.
     - Dọn sạch `pendingRequests`.
     - Cập nhật trạng thái ứng dụng sang trạng thái lỗi (`status_error`) và hiển thị banner thông báo sự cố kèm nút "Thử lại".

---

## 2. Tiêu chuẩn Nạp Thư viện Lười DOCX trong Worker (`import_docx`)

Trong `py-worker.js`:

```typescript
const lazyWheels = [
  "typing_extensions-4.15.0-py3-none-any.whl",
  "python_docx-1.1.2-py3-none-any.whl",
  "lxml-6.1.3-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
];
```

### Quy tắc phản hồi lỗi (Fail-Fast Rule):
1. **Kiểm tra trạng thái mạng**:
   - Bắt buộc kiểm tra `resp.ok` sau khi gọi `fetch(whlUrl)`.
   - Nếu `resp.ok === false`: Lập tức ném ngoại lệ rõ ràng dạng:
     `"Không thể tải gói thư viện ${whl}: Máy chủ phản hồi mã lỗi HTTP ${resp.status} (${resp.statusText})"`
   - Tuyệt đối KHÔNG tiếp tục nạp các gói tiếp theo hoặc gọi `_bridge.import_docx()` khi có bất kỳ gói nào thất bại.
2. **Ghi nhận trạng thái gói**:
   - Chỉ thêm `whl` vào tập hợp `loadedWheels` sau khi đã tải thành công toàn bộ nội dung và giải nén hoàn tất vào `site_packages` của Pyodide.
