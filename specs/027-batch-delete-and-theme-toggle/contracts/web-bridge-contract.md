# Web Bridge Contract: Xóa Hàng Loạt & Chủ Đề Giao Diện

**Feature**: `027-batch-delete-and-theme-toggle`

---

## 1. Web Worker & Bridge API

### Action: `drop_chars`
- **Gửi từ UI đến Web Worker**:
  ```json
  {
    "action": "drop_chars",
    "params": {
      "chars": ["a", "b", "c", "1"]
    }
  }
  ```
- **Phản hồi từ Worker**:
  ```json
  {
    "ok": true,
    "removed": {
      "a": 2,
      "b": 1,
      "c": 3,
      "1": 1
    },
    "total_chars": 4,
    "total_samples": 7
  }
  ```

---

## 2. Chủ Đề Giao Diện Web (DOM Attributes)

### Thẻ gốc `<html>`:
- `data-theme="light"`: Giao diện nền sáng.
- `data-theme="dark"`: Giao diện nền tối.

### Nút chuyển đổi trên Header:
- ID: `btnThemeToggle`
- Icon: ☀️ (khi đang ở dark mode để bấm về light) / 🌙 (khi đang ở light mode để bấm về dark).
- Sự kiện: click -> đảo giá trị `data-theme` trên `<html>`, cập nhật `localStorage.setItem("chuviettay_theme", currentTheme)`, kích hoạt vẽ lại canvas.
