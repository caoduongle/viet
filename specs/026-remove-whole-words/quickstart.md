# Quickstart Validation Guide: Thuần Ghép Ký Tự & Bỏ Từ Nguyên Khối

**Feature**: `026-remove-whole-words`
**Date**: 2026-10-06

Tài liệu này hướng dẫn cách kiểm thử và xác nhận các kịch bản thực thi chính của tính năng.

---

## 1. Chuẩn bị Môi trường

```powershell
# Kích hoạt môi trường và kiểm tra mã nguồn
pytest tests/test_writer.py tests/test_controller.py
```

---

## 2. Kịch bản Xác thực 1: Kết xuất thuần ghép ký tự (Không dùng `bank.words`)

### Mục tiêu
Chứng minh `Writer` chỉ sử dụng các mẫu trong `bank.letters` và không tra cứu `bank.words`.

### Các bước thực hiện
1. Tạo một kho mẫu tạm chỉ chứa các chữ cái `["t", "o", "i"]`.
2. Tạo trường `words` giả lập trong kho chứa từ `"tôi"` với nét vẽ khác biệt hoàn toàn (ví dụ: nét thẳng 1 nét).
3. Gọi lệnh kết xuất từ `"tôi"`.
4. **Kết quả mong đợi**:
   - Từ `"tôi"` được ghép từ 3 chữ cái `t`, `o`, `i` (`assemble_word`), độ rộng khớp tổng khoảng cách các chữ cái.
   - Nét vẽ của mẫu từ nguyên khối trong `bank.words` hoàn toàn không được sử dụng.
   - Thuộc tính `writer.assembled` ghi nhận `"tôi"`.

---

## 3. Kịch bản Xác thực 2: Báo cáo thiếu theo ký tự

### Mục tiêu
Chứng minh khi văn bản thiếu mẫu, hệ thống chỉ trả về danh sách các ký tự đơn lẻ còn thiếu.

### Các bước thực hiện
1. Sử dụng kho mẫu chỉ có chữ `["a", "b", "c"]`.
2. Yêu cầu viết câu `"chào bạn"`.
3. Kiểm tra danh sách thiếu mẫu trả về từ `Writer.token()` hoặc `missing_letters_ranked`.
4. **Kết quả mong đợi**:
   - Danh sách thiếu gồm các ký tự: `h`, `o`, `n`, và các dấu thanh tương ứng.
   - Không xuất hiện chuỗi nguyên từ `"chào"` hay `"bạn"` trong danh sách phần tử cần học.

---

## 4. Kịch bản Xác thực 3: Bóc tách văn bản vào hàng đợi dạy chữ

### Mục tiêu
Chứng minh khi gõ cụm từ vào ô thêm nhanh của hàng đợi, hệ thống tự động bóc tách thành các ký tự đơn lẻ.

### Các bước thực hiện
1. Mở giao diện Dạy chữ (Web hoặc Desktop).
2. Nhập vào ô "Thêm ký tự vào hàng đợi": `"ChuVietTay"`.
3. Nhấn nút "Thêm".
4. **Kết quả mong đợi**:
   - Hàng đợi xuất hiện các mục: `'C'`, `'h'`, `'u'`, `'V'`, `'i'`, `'e'`, `'t'`, `'T'`, `'a'`, `'y'`.
   - Không xuất hiện mục `"ChuVietTay"`.

---

## 5. Kịch bản Xác thực 4: Hiệu chỉnh cỡ tay bằng ký tự mốc

### Mục tiêu
Chứng minh tính năng hiệu chỉnh cỡ tay hoạt động bằng ký tự mốc `pick_calibration_char` thay vì từ mốc.

### Các bước thực hiện
1. Trong kho mẫu có sẵn các chữ cái tiếng Việt cơ bản.
2. Gọi `ctl.pick_calibration_char()`.
3. **Kết quả mong đợi**:
   - Trả về chữ cái mốc hợp lệ (như `'o'`, `'a'`, hoặc `'e'`).
   - Sau khi vẽ lại chữ cái đó và lưu, hệ số `ctl.session_scale` được cập nhật chính xác.
   - Mẫu mới được thêm vào `bank.letters`.
