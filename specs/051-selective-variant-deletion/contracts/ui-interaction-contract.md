# Contract: Tương tác Giao diện và Trạng thái DOM Modal Chi Tiết Nhãn

**Feature Branch**: `051-selective-variant-deletion`  
**Date**: 2026-10-20  
**Spec**: [spec.md](../spec.md)

---

## 1. Định danh Phần tử DOM (DOM Elements Contract)

| Phần tử DOM ID / Class | Thẻ HTML | Trách nhiệm |
|-------------------------|----------|-------------|
| `#modal-label-detail` | `<div>` | Hộp thoại modal hiển thị chi tiết nhãn. |
| `#modal-label-sample-count` | `<span>` | Hiển thị tổng số biến thể mẫu nét của nhãn. |
| `#modal-label-coverage` | `<span>` | Hiển thị chỉ báo độ phủ ("✓ Độ phủ tốt" nếu $\ge 2$ mẫu, "⚠️ Độ phủ thấp" nếu $< 2$). |
| `#modal-samples-batch-bar` | `<div>` | Thanh công cụ thao tác hàng loạt phía trên lưới mẫu. |
| `#chk-modal-select-all` | `<input type="checkbox">` | Hộp kiểm "Chọn tất cả" các biến thể của nhãn. |
| `#modal-selected-count` | `<span>` | Số lượng biến thể hiện đang được người dùng tích chọn. |
| `#btn-label-delete-selected` | `<button>` | Nút thực thi xóa các biến thể đã chọn (`display: none` khi số lượng chọn bằng 0). |
| `#btn-label-delete` | `<button>` | Nút "Xoá nhãn này" hiện hữu, giữ nguyên để xóa nhanh toàn bộ nhãn. |
| `.sample-item-card` | `<div>` | Thẻ đại diện cho một biến thể mẫu nét cụ thể. Nhận class `.selected` khi được chọn. |
| `.sample-item-checkbox` | `<input type="checkbox">` | Hộp kiểm chọn riêng lẻ đặt trên góc thẻ mẫu nét. |
| `.sample-item-delete-btn` | `<button>` | Nút icon thùng rác (🗑) đặt trên góc thẻ để xóa nhanh một mẫu nét. |

---

## 2. Quy tắc Quản lý Trạng thái (UI State Management)

### 2.1. Tập hợp các mẫu được chọn (`modalSelectedIndices`)
- Khởi tạo: `const modalSelectedIndices = new Set();`
- Reset: Xóa rỗng `modalSelectedIndices.clear()` khi:
  - Mở modal chi tiết nhãn mới (`openLabelDetail`).
  - Đóng modal.
  - Hoàn tất một thao tác xóa biến thể.
  - Tải lại danh sách mẫu nét.

### 2.2. Đồng bộ hiển thị Thanh công cụ hàng loạt
Hàm `updateModalBatchBar(totalCount)`:
1. `const count = modalSelectedIndices.size;`
2. Cập nhật nhãn số lượng: `#modal-selected-count.textContent = String(count);`.
3. Trạng thái hiển thị nút xóa hàng loạt `#btn-label-delete-selected`:
   - Nếu `count === 0`: `style.display = "none"`.
   - Nếu `count > 0`: `style.display = "inline-flex"`.
4. Trạng thái `#chk-modal-select-all`:
   - Nếu `totalCount > 0 && count === totalCount`: `checked = true`, `indeterminate = false`.
   - Nếu `count > 0 && count < totalCount`: `checked = false`, `indeterminate = true`.
   - Nếu `count === 0`: `checked = false`, `indeterminate = false`.

### 2.3. Trạng thái hiển thị Thẻ mẫu nét (`.sample-item-card`)
- Khi một biến thể có chỉ số `idx` nằm trong `modalSelectedIndices`:
  - Thẻ nhận thêm class `selected`.
  - Hộp kiểm `.sample-item-checkbox` tương ứng có `checked = true`.
- Khi loại bỏ:
  - Bỏ class `selected`.
  - Hộp kiểm có `checked = false`.

---

## 3. Quy trình Xử lý Sự kiện (Event Handling)

### 3.1. Nhấp chuột vào Thẻ mẫu nét hoặc Hộp kiểm
- Sự kiện `click` trên `.sample-item-checkbox`:
  - `e.stopPropagation()`.
  - Bật/tắt chỉ số trong `modalSelectedIndices`.
  - Cập nhật giao diện thẻ và thanh công cụ.
- Sự kiện `click` trên `.sample-item-card`:
  - Nếu click vào `.sample-item-delete-btn` hoặc `.sample-item-checkbox`: để handler chuyên biệt xử lý.
  - Nếu click vào vùng thẻ: đảo trạng thái chọn của `idx`, cập nhật checkbox và thanh công cụ.

### 3.2. Nhấp vào Nút xóa nhanh trên thẻ (`.sample-item-delete-btn`)
1. `e.stopPropagation()`.
2. Lấy `idx` của thẻ mẫu nét.
3. Hiển thị xác nhận:
   ```javascript
   const ok = confirm(`Bạn có chắc chắn muốn xoá Mẫu #${idx + 1} của nhãn "${label}" không?\n(Lưu ý: Hành động này không thể hoàn tác)`);
   ```
4. Nếu `ok === true`: Gửi yêu cầu xóa với `indices = [idx]`.

### 3.3. Nhấp vào Nút xóa các biến thể đã chọn (`#btn-label-delete-selected`)
1. Kiểm tra `const count = modalSelectedIndices.size;` nếu `count === 0` thì dừng.
2. Kiểm tra nếu `count === totalCount`:
   ```javascript
   const ok = confirm(`Bạn có chắc chắn muốn xoá toàn bộ ${count} biến thể của nhãn "${label}" không?\n(Hành động này sẽ xóa nhãn khỏi kho mẫu)`);
   ```
   Nếu `count < totalCount`:
   ```javascript
   const ok = confirm(`Bạn có chắc chắn muốn xoá ${count} biến thể đã chọn của nhãn "${label}" không?\n(Lưu ý: Hành động này không thể hoàn tác)`);
   ```
3. Nếu `ok === true`: Gửi yêu cầu xóa với `indices = Array.from(modalSelectedIndices)`.

### 3.4. Xử lý sau khi xóa thành công và Bảo vệ Chống xung đột (In-Flight Guard)
- Sử dụng cờ khóa `let isDeletingVariants = false;` trong suốt quá trình từ lúc bắt đầu gọi worker cho tới khi kết thúc.
- Vô hiệu hóa nút xóa và cập nhật giao diện trong khi chờ phản hồi để triệt tiêu nguy cơ gửi lệnh trùng lặp khi người dùng nhấp đúp.
- Ẩn khung xem thử ngẫu nhiên (`#modal-random-preview-box.style.display = "none"`) để tránh hiển thị nét vẽ cũ của mẫu đã xóa.
- Nếu `res.data.label_deleted === true`:
  - Đóng modal `#modal-label-detail.style.display = "none"`.
  - Đồng bộ lưu trữ `await storage.syncAndSaveActiveProfile(sendWorkerFn)`.
  - Cập nhật kho mẫu `await refreshBankView()`.
  - Hiển thị thông báo hoàn tất: `alert('Đã xoá toàn bộ biến thể và gỡ nhãn khỏi kho mẫu.')`.
- Nếu `res.data.label_deleted === false`:
  - Đồng bộ lưu trữ `await storage.syncAndSaveActiveProfile(sendWorkerFn)`.
  - Nạp lại danh sách mẫu nét `await loadAndRenderModalSamples(label, category)`.
  - Cập nhật thống kê nhãn trên kho `await refreshBankView()`.
- Khi đăng ký sự kiện qua `bindBankEvent`, luôn sử dụng hàm có tên (named functions) thay vì hàm ẩn danh (anonymous arrow functions) để cơ chế chống gắn lặp listener hoạt động chuẩn xác theo `__bank_bound_${evt}_${fn.name}`.

---

## 4. An toàn XSS và Thoát chuỗi DOM (XSS Guard)
- Bắt buộc gọi `escapeHtml(label)` và `escapeHtml(sample.w)` trước khi đưa vào template string.
- Tuyệt đối không nhúng chuỗi thô từ dữ liệu người dùng vào `innerHTML`.
