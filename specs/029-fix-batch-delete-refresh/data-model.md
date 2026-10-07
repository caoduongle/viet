# Data Model: Khắc Phục Lỗi Làm Mới Khi Xóa Hàng Loạt Trên Web Client

**Feature Branch**: `specs/029-fix-batch-delete-refresh`
**Date**: 2026-10-07

## 1. Các Thực thể & Trạng thái (Entities & State)

### Entity: `BatchSelectionState`
Trạng thái lưu trữ các nhãn ký tự đang được người dùng chọn trong phiên giao diện tab Kho mẫu.

- **Vị trí**: Quản lý nội bộ trong `webapp/js/bank.js`.
- **Cấu trúc dữ liệu**:
  ```javascript
  let selectedLabels = new Set(); // Set<string>
  ```
- **Các trường & Thuộc tính**:
  - `selectedLabels`: Tập hợp các nhãn ký tự/dấu được tick chọn (ví dụ: `Set(["a", "b", "+", "1"])`).
  - `allBankItems`: Danh sách toàn bộ ký tự hiện có trong kho: `Array<{ category: string, label: string, count: number }>`.
- **Quy tắc chuyển đổi trạng thái (State Transitions)**:
  - **Trạng thái ban đầu**: `selectedLabels.size === 0`, checkbox `#chk-bank-select-all` unchecked, nút `#btn-bank-delete-selected` bị ẩn hoặc disable.
  - **Khi tick chọn thẻ / chọn tất cả**: Thêm/bớt nhãn trong `selectedLabels`, cập nhật văn bản nhãn `(Đã chọn N)`.
  - **Khi bấm xóa hàng loạt thành công**:
    - Gọi worker `drop_chars` với mảng nhãn `Array.from(selectedLabels)`.
    - Gọi `storage.syncAndSaveActiveProfile(...)`.
    - Gọi `selectedLabels.clear()`.
    - Gọi `refreshBankView()` để kéo danh sách mới và vẽ lại UI.

---

### Entity: `WorkerDropCharsMessage`
Cấu trúc thông điệp trao đổi giữa UI Thread và Pyodide Web Worker khi xóa hàng loạt:

- **Action**: `"drop_chars"`
- **Payload**:
  ```json
  {
    "chars": ["nhãn_1", "nhãn_2", "..."]
  }
  ```
- **Response**:
  ```json
  {
    "ok": true,
    "data": {
      "removed": {
        "nhãn_1": 2,
        "nhãn_2": 1
      }
    }
  }
  ```
- **Xử lý lỗi**:
  - Nếu `!res.ok`, quăng lỗi `Error(res.error)`.
  - Nếu thành công, tiến hành dọn dẹp `selectedLabels` và làm mới giao diện qua `refreshBankView()`.
