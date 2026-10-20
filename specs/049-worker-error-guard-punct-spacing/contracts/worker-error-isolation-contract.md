# Contract: Worker Error Isolation

## Context
Trình xử lý sự kiện Worker trong `webapp/js/app.js` (`attachWorkerHandlers`).

## Invariant 1: Superseded Worker Isolation
Bất kỳ sự kiện nào (`onmessage`, `onerror`, `onmessageerror`) phát sinh từ đối tượng Worker có thế hệ `generation !== workerGeneration` **BẮT BUỘC** phải:
1. Giải quyết `boundSession.resolve(false)` nếu `boundSession` tồn tại và chưa giải quyết (`!boundSession.isResolved`).
2. Trả về ngay lập tức (`return;`).
3. **TUYỆT ĐỐI KHÔNG** gọi `handleWorkerFatalError()`.
4. **TUYỆT ĐỐI KHÔNG** kích hoạt từ chối các yêu cầu đang chờ (`pendingRequests`) của thế hệ hiện hành.
5. **TUYỆT ĐỐI KHÔNG** thay đổi giao diện người dùng (nút "Thử lại", thanh trạng thái).

## Invariant 2: Current Generation Error Handling
Khi sự kiện lỗi (`onerror` hoặc `onmessageerror` hoặc thông điệp `{ type: "ERROR" }`) phát sinh từ Worker có `generation === workerGeneration`:
1. Nếu có phiên phục hồi hiện hành (`currentSession.generation === generation`):
   - Xóa bộ đếm thời gian `currentSession.timer`.
   - Đóng phiên với `currentSession.resolve(false)`.
2. Gọi `handleWorkerFatalError(errorMessage)`:
   - Từ chối tất cả yêu cầu trong `pendingRequests` với lỗi rõ ràng.
   - Chuyển trạng thái giao diện sang `status_error`.
   - Hiển thị nút "Thử lại" và cho phép người dùng click để phục hồi.

## Invariant 3: Single Resolution Guarantee
Đối tượng `session.resolve(val)` chỉ được gọi một lần duy nhất trong toàn bộ vòng đời của nó; các lần gọi tiếp theo bị bỏ qua thông qua cờ `session.isResolved`.
