# Contract: UI Lifecycle & Event Listener Management

## 1. `TeachController` Lifecycle Contract

### Khởi tạo và Dọn dẹp
```javascript
class TeachController {
  constructor(workerClient, options = {}) {
    this.signal = options.signal || null;
    this.cleanupHandlers = [];
  }

  async init(options = {}) {
    // Nếu options có signal mới, cập nhật signal
    if (options.signal) this.signal = options.signal;
    this._cacheDom();
    this._initCanvas();
    this._bindEvents();
    ...
  }

  destroy() {
    // Thu hồi toàn bộ listener đã gắn (bao gồm trên document)
    for (const cleanup of this.cleanupHandlers) {
      try { cleanup(); } catch (_) {}
    }
    this.cleanupHandlers = [];
    if (this.canvas && typeof this.canvas.destroy === "function") {
      this.canvas.destroy();
    }
    this.canvas = null;
  }
}
```

### Ràng buộc
- Mọi lời gọi `addEventListener` trong `TeachController` phải được bảo vệ bởi:
  1. `{ signal: this.signal }` (nếu môi trường hỗ trợ `AbortSignal`), VÀ
  2. Một hàm hủy đăng ký tương ứng được thêm vào `this.cleanupHandlers`.
- Khi `destroy()` hoặc khi `this.signal` phát tín hiệu `abort`, không còn bất kỳ sự kiện nào (đặc biệt là sự kiện `keydown` trên `document`) tồn tại.

---

## 2. `setupPreviewNavigation` ResizeObserver Contract

### Khởi tạo
```javascript
function setupPreviewNavigation(options = {}) {
  ...
  const stage = document.getElementById("preview-stage");
  if (stage && typeof ResizeObserver !== "undefined") {
    if (activePreviewResizeObserver) {
      activePreviewResizeObserver.disconnect();
      activePreviewResizeObserver = null;
    }
    const observer = new ResizeObserver(() => {
      if (isFitMode && currentDoc && currentDoc.pages.length) {
        applyPaperZoom(calculateFitZoom(), true);
      }
    });
    observer.observe(stage);
    activePreviewResizeObserver = observer;

    if (options.signal) {
      options.signal.addEventListener("abort", () => {
        observer.disconnect();
        if (activePreviewResizeObserver === observer) {
          activePreviewResizeObserver = null;
        }
      }, { once: true });
    }
  }
}
```

### Ràng buộc
- Không bao giờ tồn tại nhiều hơn 1 thể hiện `ResizeObserver` cùng quan sát `#preview-stage`.
- Khi nhận tín hiệu `abort` từ `options.signal`, observer phải được ngắt kết nối ngay lập tức.

---

## 3. `initQuotaAndBackupReminders` Idempotency Contract

### Ràng buộc
- Hàm `initQuotaAndBackupReminders(options = {})` phải kiểm tra cờ (ví dụ `el.__hasQuotaListener`) hoặc gắn kèm `options.signal`.
- Khi gọi liên tiếp n lần ($n \ge 2$), mỗi nút bấm chỉ được liên kết với duy nhất 1 callback xử lý sự kiện.
