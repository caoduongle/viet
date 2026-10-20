# Interface Contract: Worker Resilience, Seed Integrity & Typography Hardening

**Feature**: `046-worker-seed-typography-hardening`  
**Date**: 2026-10-20

## 1. Web Worker Recovery Contract (`webapp/js/app.js`)

### `recoverWorker(WorkerClass = null, timeoutMs = 10000) -> Promise<boolean>`
- **Hành vi**:
  1. Tăng `workerGeneration++`.
  2. Hủy phiên phục hồi cũ nếu còn đang chờ (giải quyết `resolve(false)` cho promise cũ).
  3. Khởi tạo một đối tượng phiên mới:
     ```javascript
     activeRecovery = {
       generation: workerGeneration,
       resolve: null,
       timer: null
     };
     ```
  4. Bộ đếm thời gian `timer` được thiết lập một lần duy nhất với `timeoutMs`, bảo vệ toàn bộ tiến trình cho đến khi `onWorkerReady` kết thúc hoặc phát sinh lỗi.
  5. Khi nhận tín hiệu `READY`:
     - KHÔNG xóa timer.
     - Tiếp tục chạy `await onWorkerReady(generation)`.
     - Nếu thế hệ đã bị thay đổi trong lúc chạy: bỏ qua kết quả và giải quyết `resolve(false)`.
     - Nếu thành công và thế hệ vẫn hợp lệ: xóa timer, giải quyết `resolve(true)`.
  6. Trong khối `finally`:
     - Luôn dọn dẹp timer.
     - Cập nhật `isRecovering = false`.
     - Kích hoạt lại nút "Thử lại".
     - Xóa tham chiếu phiên phục hồi.

---

## 2. UI Idempotent Listener Contract (`webapp/js/bank.js`, `write.js`, `app.js`)

### `initBankTab(sendWorkerMessage, options = {})` & `initWriteTab(options = {})`
- **Đầu vào**: `options.signal` (`AbortSignal`, tùy chọn) hoặc cơ chế tự động dọn dẹp.
- **Hành vi**:
  - Gắn event listeners với `{ signal }` hoặc kiểm tra cờ đánh dấu `element.__hasListener = true`.
  - Cung cấp hàm `teardownBankTab()` và `teardownWriteTab()` để gỡ bỏ toàn bộ listeners khi khởi tạo gặp lỗi hoặc khi tái khởi tạo.
  - Đảm bảo việc gọi lặp lại `init*Tab()` nhiều lần không tạo ra nhiều hơn 1 handler cho mỗi sự kiện DOM.

---

## 3. Document IR & Seed Alignment Contract (`chuviettay/document/ir.py` & `engine.py`)

### `align_document_seeds(base_doc: Document, edited_doc: Document) -> Document`
- **Phân loại khối**:
  - Khối `Heading`: Trích xuất với `context_prefix="heading"`. Bộ đếm `counts[("heading", tok)]` hoàn toàn độc lập với `counts[("text", tok)]`.
  - Khối `Paragraph`: Trích xuất với `context_prefix="text"`.
  - Khối `TableCell`: Trích xuất với `context_prefix="cell"`.
- **Chuyển đổi bảng (`engine.py`)**:
  - Khối `MathBlock` trong ô bảng khi tạo `MathInline` chuyển tiếp:
    ```python
    MathInline(
        latex=b.latex,
        ast=b.ast,
        occurrence=getattr(b, "occurrence", None),
        stable_id=getattr(b, "stable_id", None),
    )
    ```

### `RenderItem` & Chunk Geometry ID (`chuviettay/layout/engine.py`)
- Khi một từ được chia thành nhiều chunk, `RenderItem.token_id` của chunk thứ `i` được gán:
  `token_id = f"{ctx.token_id}:{i}"` (nếu có nhiều hơn 1 chunk) hoặc giữ nguyên `ctx.token_id` (nếu chỉ có 1 chunk).

---

## 4. Typography & Robust Spacing Contract (`chuviettay/model/writer.py`)

### `Writer._normalize_digit_sample(inst: dict, ch: str, xh: float | None = None) -> tuple[list[Stroke], float]`
- Với mọi mẫu chữ số/ký hiệu số có `sample_h > 1e-4`:
  - `scale_y = clamp(target_h / sample_h, 0.10, 15.0)` với `target_h = 1.20 * xh`.
  - `scale_x = clamp(scale_y ** 0.5, 0.40, 2.50)`.
  - Căn chân chữ chạm baseline `y = 0.0` (`dy = -raw_max_y`) và biên trái `dx = -raw_min_x`.
  - Đảm bảo 100% mẫu số kết xuất có chiều cao nằm trong `[1.05 * xh, 1.30 * xh]`.
- Với mẫu rỗng hoặc suy biến không có điểm (`sample_h <= 1e-4`):
  - Trả về danh sách nét rỗng `[]` và độ rộng an toàn `0.6 * xh`.

### `Writer._resolve_dgap(first: bool, is_hyphen: bool = False, digit_idx: int = 0) -> float`
- Nếu `first`: trả về `0.0`.
- Nếu `is_hyphen` (bao gồm `ch == "-"` hoặc ký tự liền trước là `"-"`): trả về `0.5 * gap` (khoảng `0.05 * xh .. 0.09 * xh`), bảo đảm khoảng cách sau dấu âm `-` đứng đầu số chặt chẽ tự nhiên.
- Mặc định: trả về `gap` trong `[0.10 * xh, 0.18 * xh]`.

### `Writer.measure_text_width(text: str, scale: float = 1.0) -> float`
- Đồng bộ hoàn toàn logic khoảng cách với `Writer.number()`:
  - Dấu phẩy `,` / `.`: cộng `0.08 * xh` trước dấu và `0.10 * xh` sau dấu.
  - Chữ số sau dấu âm `-`: cộng khoảng cách thu hẹp `0.5 * dgap`.
  - Độ lệch đo đạc và kết xuất: `<= 0.05 * xh`.
