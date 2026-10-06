# Quickstart & Verification Guide: Xóa Hàng Loạt & Chủ Đề Sáng Tối

**Feature**: `027-batch-delete-and-theme-toggle`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

---

## 1. Kịch Bản Xác Thực Kiểm Thử Tự Động (Automated Testing)

### 1.1 Kiểm thử tầng Controller & Bank (Xóa hàng loạt)
Chạy bài kiểm thử unit test cho phương thức `drop_chars`:
```bash
pytest tests/test_controller.py -k "test_drop_chars_batch"
```
- **Kỳ vọng**: Xóa đồng thời nhiều ký tự thuộc các nhóm khác nhau (`letters`, `digits`, `punct`), chỉ gọi `save()` một lần, số mẫu trong kho giảm chính xác.

### 1.2 Kiểm thử Web Bridge & Worker
Chạy kiểm thử Web Worker / Bridge cho hành động `drop_chars`:
```bash
pytest tests/test_bridge.py -k "test_drop_chars"
```

---

## 2. Kịch Bản Xác Thực Thủ Công (Manual Verification)

### 2.1 Web Client
1. Mở Web Client: Chạy `node scripts/serve.mjs` hoặc mở `webapp/index.html`.
2. **Kiểm tra chuyển đổi chủ đề Sáng / Tối**:
   - Nhấn nút ☀️ / 🌙 trên thanh Header.
   - Xác nhận màu nền chuyển sang tối (#121212) / sáng, các chữ và thẻ hiển thị rõ ràng.
   - Nhấn F5 tải lại trang: Giao diện vẫn duy trì chế độ vừa chọn.
   - Chuyển sang tab "Tập viết": Khung vẽ canvas hiển thị đường kẻ mốc tương phản rõ nét.
3. **Kiểm tra xóa hàng loạt trong Kho mẫu**:
   - Chuyển sang tab "Kho mẫu".
   - Tích chọn 3 ký tự (hoặc bấm "Chọn tất cả").
   - Nút "Xóa đã chọn (3)" sáng lên.
   - Bấm nút "Xóa đã chọn": Hộp thoại xác nhận hiển thị thông tin chi tiết.
   - Bấm "Đồng ý": 3 ký tự biến mất khỏi danh sách, số lượng mẫu thống kê giảm tương ứng.

### 2.2 Desktop GUI
1. Khởi chạy: `python -m chuviettay.gui`.
2. **Kiểm tra chuyển đổi chủ đề**:
   - Bấm nút chuyển chủ đề Sáng / Tối trên thanh tiêu đề/menu.
   - Toàn bộ các widget ttk và Listbox chuyển màu đồng bộ.
3. **Kiểm tra xóa hàng loạt**:
   - Mở tab "Kho mẫu".
   - Giữ phím `Ctrl` hoặc `Shift` để chọn nhiều mục trong danh sách.
   - Nút "Xóa đã chọn" hiển thị số lượng mục.
   - Nhấn nút, xác nhận trong hộp thoại và kiểm tra kho được lưu an toàn.
