# Contract: Web Worker Recovery & Lifecycle

## 1. Phương thức `recoverWorker(WorkerClass = null, timeoutMs = 10000, options = {})`

### Tham số
- `WorkerClass`: Constructor Worker tùy chọn (dùng cho môi trường thử nghiệm MockWorker).
- `timeoutMs`: Thời gian chờ tối đa cho bước bắt tay ban đầu (mặc định 10.000ms).
- `options.force`: `boolean` - Khi `true`, cho phép ép khởi động một phiên phục hồi mới ngay cả khi đang có phiên phục hồi khác đang chạy.

### Ràng buộc thực thi (Contract Invariants)
1. **Khử trùng lặp**: Nếu `!options.force && isRecovering && recoveryPromise`, hàm trả về ngay `recoveryPromise` hiện tại mà không tạo phiên mới.
2. **Thay thế phiên an toàn**: Khi `options.force === true` và phiên cũ đang chạy:
   - Phiên cũ bị đánh dấu `isResolved = true` và hàm `resolve(false)` của nó được gọi ngay lập tức.
   - `workerGeneration` tăng lên 1 đơn vị.
   - Tiến trình Worker cũ bị gọi `terminate()`.
   - Toàn bộ `pendingRequests` của thế hệ trước bị reject với thông báo tái khởi động.
3. **Bảo vệ khối `finally`**:
   - Khi một phiên `session` kết thúc, các biến toàn cục:
     - `isRecovering = false`
     - `recoveryPromise = null`
     - `clearHandshakeTimer = null`
     - `btnRetry.disabled = false`
     **CHỈ ĐƯỢC PHÉP CẬP NHẬT** khi và chỉ khi `activeRecoverySession === session`.
   - Nếu `activeRecoverySession !== session` (phiên này đã bị thay thế), phiên này kết thúc trong im lặng và không làm biến đổi bất kỳ biến toàn cục nào nêu trên.
4. **Post-READY Timeout Termination**:
   - Trong `attachWorkerHandlers`, nếu bước khởi tạo sau `READY` (`initTimeout`) bị quá hạn:
     - Gọi vật lý `targetWorker.terminate()`.
     - Tăng `workerGeneration`.
     - Đặt `worker = null` (nếu `worker === targetWorker`).
     - Gọi `handleWorkerFatalError()`.
     - Gọi `currentSession.resolve(false)`.
