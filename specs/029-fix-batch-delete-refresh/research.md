# Phase 0 Research: Khắc Phục Lỗi Làm Mới Khi Xóa Hàng Loạt Trên Web Client

**Feature Branch**: `specs/029-fix-batch-delete-refresh`
**Date**: 2026-10-07

## 1. Nghiên cứu Nguyên nhân Gốc rễ (Root Cause Analysis)

### Bối cảnh
Khi người dùng sử dụng tính năng "Xoá đã chọn" trên giao diện Web Client (tab Quản lý kho mẫu chữ), trình duyệt kích hoạt hàm `handleDeleteSelected()` trong `webapp/js/bank.js`.

### Phát hiện Lỗi
Tại dòng 392 của `webapp/js/bank.js`:
```javascript
await refreshBankTab();
```
Trong phạm vi mô-đun `webapp/js/bank.js`, hàm làm mới hiển thị kho mẫu được định nghĩa và xuất khẩu (export) ở dòng 133 với tên:
```javascript
export async function refreshBankView() { ... }
```
Đồng thời, hàm `handleDeleteLabel()` (khi xoá một nhãn đơn lẻ) ở dòng 539 gọi đúng:
```javascript
await refreshBankView();
```
Do đó, việc gọi `refreshBankTab()` là một lỗi typo tham chiếu (`ReferenceError: refreshBankTab is not defined`), khiến luồng xử lý bị văng ngoại lệ vào khối `catch (err)`, dẫn đến hộp thoại `alert("Lỗi khi xoá hàng loạt: " + err.message)`.

### Tác động tới bản build phân phối (`webapp/dist/`)
Thư mục `webapp/dist/js/bank.js` hiện cũng chứa chuỗi `await refreshBankTab();` (dòng 392). Do đó, cần đồng bộ cả tệp nguồn và chạy lại `python scripts/build_web.py` để cập nhật bản build phân phối.

---

## 2. Các Quyết định Kỹ thuật (Technical Decisions)

### Quyết định 1: Chuẩn hóa lời gọi hàm làm mới trong `handleDeleteSelected`
- **Quyết định**: Thay thế `await refreshBankTab();` bằng `await refreshBankView();`.
- **Lý do**: `refreshBankView()` là hàm chuẩn duy nhất trong `webapp/js/bank.js` chịu trách nhiệm lấy lại danh sách ký tự từ worker (`list_all_chars`), cập nhật số lượng từng phân loại (`updateCategoryCounts`), áp dụng bộ lọc và vẽ lại lưới thẻ (`applyFiltersAndRender`), đồng thời đặt lại thanh chọn hàng loạt (`updateBatchBar`).
- **Phương án thay thế đã xem xét**:
  - *Tạo alias `const refreshBankTab = refreshBankView;`*: Bị loại bỏ vì vi phạm nguyên tắc Clean Code và tạo dư thừa không cần thiết (KISS). Gọi trực tiếp `refreshBankView()` nhất quán 100% với `handleDeleteLabel()`.

### Quyết định 2: Tái đồng bộ bản phân phối Web (`webapp/dist/`)
- **Quyết định**: Cập nhật cả `webapp/js/bank.js` và `webapp/dist/js/bank.js`, sau đó chạy `python scripts/build_web.py` để đảm bảo tính toàn vẹn của bundle PWA / Service Worker.
- **Lý do**: Môi trường triển khai thực tế (như Render / GitHub Pages) phục vụ từ `webapp/dist/` hoặc tệp tĩnh đã build.

### Quyết định 3: Bổ sung Kịch bản Kiểm thử Tự động E2E
- **Quyết định**: Thêm bài kiểm thử trong `tests/e2e/bank.spec.ts` kiểm chứng toàn diện luồng:
  1. Tick chọn nhiều thẻ (hoặc "Chọn tất cả hiển thị").
  2. Bấm "Xoá đã chọn".
  3. Lắng nghe và chấp nhận hộp thoại `dialog`.
  4. Xác nhận không có alert lỗi nào xuất hiện, lưới thẻ cập nhật sạch sẽ và số lượng chọn trở về 0.
- **Lý do**: Ngăn chặn triệt để hồi quy (regression) và bảo đảm tuân thủ Điều III của Constitution (Comprehensive Automated Testing).
