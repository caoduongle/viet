# Data Model: 048-worker-recovery-ui-hardening

## 1. Web Worker Recovery Session (`RecoverySession`)

Đối tượng mô tả phiên phục hồi Worker, được quản lý nội bộ trong `webapp/js/app.js`.

### Cấu trúc dữ liệu
```typescript
interface RecoverySession {
  /** Thế hệ Worker mục tiêu được phiên này khởi tạo */
  generation: number;

  /** Cờ đánh dấu phiên đã hoàn tất giải quyết (true/false) */
  isResolved: boolean;

  /** Bộ đếm thời gian kiểm soát timeout (handshake hoặc UI init) */
  timer: NodeJS.Timeout | number | null;

  /** Hàm giải quyết Promise của phiên */
  resolve: (success: boolean) => void;
}
```

### Các ràng buộc trạng thái (State Transitions)
- **Khởi tạo**: `isResolved = false`, `timer` được gắn timeout bắt tay (`timeoutMs`).
- **Khi nhận `READY`**: `timer` bắt tay được hủy; nếu khởi tạo UI, gắn `timer` mới (`initTimeout`).
- **Khi bị phiên mới thay thế (`force: true`)**: Gọi `resolve(false)`, `isResolved = true`, hủy `timer`. Phiên cũ KHÔNG được phép giải phóng `activeRecoverySession` hay `isRecovering`.
- **Khi hoàn tất**: Gọi `resolve(true|false)`, `isResolved = true`, hủy `timer`. Chỉ khi `activeRecoverySession === session`, cờ toàn cục `isRecovering = false` và `recoveryPromise = null` mới được xóa.

---

## 2. UI Lifecycle Controller State (`UiLifecycle`)

Quản lý vòng đời gỡ bỏ của các thành phần giao diện.

### Cấu trúc dữ liệu
```typescript
interface UiControllerOptions {
  /** Tín hiệu hủy đồng bộ toàn bộ listener */
  signal?: AbortSignal;
}

interface TeachControllerState {
  /** Tham chiếu canvas vẽ */
  canvas: TeachCanvas | null;

  /** Danh sách các trình dọn dẹp nội bộ khi không dùng AbortSignal native */
  cleanupFns: Array<() => void>;

  /** Tín hiệu hủy hiện hành */
  signal: AbortSignal | null;
}
```

### Quy tắc vòng đời
- Khi `TeachController.destroy()` hoặc `options.signal.abort()` được gọi:
  1. Toàn bộ listener trên các phần tử DOM tab Dạy chữ bị gỡ bỏ.
  2. Listener `keydown` toàn cục trên `document` bị gỡ bỏ ngay lập tức.
  3. `TeachCanvas` được giải phóng.

- Đối với `ResizeObserver`:
  ```typescript
  let activePreviewResizeObserver: ResizeObserver | null = null;
  ```
  - Trước khi khởi tạo observer mới: `if (activePreviewResizeObserver) activePreviewResizeObserver.disconnect()`.
  - Nếu có `options.signal`: `signal.addEventListener("abort", () => observer.disconnect(), { once: true })`.

---

## 3. Digit Normalization & Width Synchronization Model

### Chuẩn hóa mẫu chữ số suy biến
```typescript
interface DigitSampleNormalization {
  /** Danh sách nét chuẩn hóa */
  strokes: Stroke[];

  /** Chiều rộng tiến bước (advance width) */
  advanceWidth: number;
}
```

### Quy tắc chuẩn hóa
1. **Mẫu bình thường**:
   - $sample\_h = \max(y) - \min(y)$
   - $target\_h = 1.20 \times x_h$
   - $scale\_y = \text{clamp}(target\_h / sample\_h, 0.10, 15.0)$
   - $scale\_x = \text{clamp}(scale\_y^{0.5}, 0.40, 2.50)$
2. **Mẫu suy biến ($sample\_h \le 10^{-3}$ hoặc $bbox\_w \le 10^{-3}$)**:
   - Sử dụng vector glyph fallback hoặc giữ nguyên tỷ lệ với kích thước tối thiểu:
     $adv\_w = \max(raw\_w, 0.60 \times x_h)$
   - Không thực hiện phép chia cho $sample\_h$, tránh hệ số vô hạn.

### Quy tắc đồng bộ đo độ rộng (`measure_text_width` vs `number`)
- Với mọi chuỗi số $S \in \text{NUMRE}$:
  $$|\text{measure\_text\_width}(S) - \text{number}(S)[1]| \le 0.05 \times x_h$$
- Trên mọi kho mẫu (kể cả đa biến thể hoặc biến thể ngẫu nhiên).
