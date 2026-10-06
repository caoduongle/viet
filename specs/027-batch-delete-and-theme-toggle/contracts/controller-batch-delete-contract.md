# Controller Contract: Xóa Hàng Loạt & Quản Lý Chủ Đề

**Feature**: `027-batch-delete-and-theme-toggle`

---

## 1. Phương Thức Xóa Hàng Loạt Trên `AppController`

### `drop_chars(chars: list[str]) -> DropResult`
Thực hiện xóa hàng loạt danh sách các ký tự khỏi kho mẫu trong một giao dịch an toàn:

- **Tham số**:
  - `chars`: Danh sách các nhãn ký tự cần xóa (ví dụ `['a', 'b', '1', ',']`).
- **Xử lý**:
  - Thu nạp khóa `_lock` của kho mẫu.
  - Tự động phân loại từng ký tự vào nhóm tương ứng (`letters`, `digits`, `punct`, `symbols`, `marks`).
  - Xóa toàn bộ mẫu của ký tự đó và ghi nhận tombstone dạng `<cat>:<label>`.
  - Tái thiết lập chỉ mục (`rebuild()`) một lần duy nhất khi kết thúc danh sách.
  - Lưu file kho mẫu xuống đĩa (`save()`).
- **Trả về**:
  - `DropResult`:
    - `removed`: `{nhãn: số_mẫu_bị_xóa}`
    - `total_removed_samples`: Tổng số mẫu nét bị xóa.
    - `total_removed_chars`: Số lượng ký tự bị xóa.

---

## 2. Quản Lý Chủ Đề Trên `AppController` / `GUI`

### `get_theme_preference() -> str`
- Trả về `'light'` hoặc `'dark'` dựa trên cấu hình lưu trữ hoặc cấu hình mặc định hệ thống.

### `set_theme_preference(theme: str) -> None`
- Lưu cấu hình chủ đề `'light'` hoặc `'dark'` vào tệp cấu hình ứng dụng người dùng.
