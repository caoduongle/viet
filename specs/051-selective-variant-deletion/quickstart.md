# Quickstart Guide: Kiểm thử và Xác thực Tính năng Xóa Biến Thể Mẫu Nét

**Feature Branch**: `051-selective-variant-deletion`  
**Date**: 2026-10-20  
**Spec**: [spec.md](spec.md)

---

## 1. Tổng quan Kịch bản Xác thực

Tài liệu này cung cấp các kịch bản kiểm thử tự động và hướng dẫn kiểm chứng thủ công end-to-end cho tính năng chọn và xóa biến thể mẫu nét tùy chọn.

---

## 2. Kịch bản Kiểm thử Tự động (Automated Verification)

### 2.1. Kiểm thử Tầng Cốt lõi Python (`Bank`, `AppController`, `BrowserBridge`)
Chạy bộ kiểm thử mới kiểm tra toàn diện nghiệp vụ xóa biến thể mẫu nét:

```bash
pytest tests/test_bank_variant_deletion.py -v
```

**Các ca kiểm thử trọng tâm**:
1. `test_drop_single_variant`: Thêm 3 mẫu nét cho chữ cái `"Ơ"`, xóa Mẫu #2 (chỉ số 1). Xác minh còn đúng 2 mẫu (#1 và #3), thứ tự bảo toàn, không ghi tombstone.
2. `test_drop_multiple_variants`: Thêm 4 mẫu nét, xóa đồng thời các chỉ số `[0, 2]`. Xác minh còn lại 2 mẫu ban đầu ở vị trí 1 và 3, độ rộng và nét nguyên vẹn.
3. `test_drop_all_variants_cleans_label`: Xóa tất cả các chỉ số của nhãn. Xác minh nhãn bị xóa hoàn toàn khỏi `bank.letters`, tombstone được tạo, `label_deleted == True`.
4. `test_drop_invalid_indices_safe`: Truyền chỉ số ngoài biên (âm hoặc vượt quá số mẫu) hoặc danh sách rỗng. Xác minh hệ thống không sập, trả về `removed_count == 0`.
5. `test_drop_word_variant_rebuilds_tl`: Xóa biến thể của từ trong `bank.words`. Xác minh chỉ mục tìm kiếm thân chữ `self.tl` và dấu thanh `self.marks` được tái lập chính xác.
6. `test_controller_and_bridge_parity`: Xác thực `AppController` lưu đĩa đúng và `BrowserBridge` trả về cấu trúc `{"ok": True, "data": ...}`.

---

### 2.2. Kiểm thử Tầng Frontend & Hợp đồng Bảo mật DOM
Chạy kiểm thử JavaScript với bộ test runner tích hợp của Node.js:

```bash
node --test tests/js/bank_safety.test.mjs
```

**Xác minh**:
- Đảm bảo mã nguồn `bank.js` và `index.html` tuân thủ các hợp đồng:
  * Không nội suy chuỗi thô mà chưa qua `escapeHtml()`.
  * Có đầy đủ các phần tử điều khiển `#btn-label-delete-selected`, `#chk-modal-select-all`, `.sample-item-checkbox`, `.sample-item-delete-btn`.

---

### 2.3. Kiểm thử Đóng gói và Phân phối Web
Đóng gói lại ứng dụng web tĩnh và kiểm tra tính toàn vẹn:

```bash
python scripts/build_web.py
pytest tests/test_build_web.py -v
```

---

## 3. Kịch bản Kiểm chứng Thủ công trên Trình duyệt (E2E Verification)

1. **Khởi chạy ứng dụng**:
   Mở trình duyệt truy cập ứng dụng web ChuVietTay (chế độ local hoặc qua dev server).
2. **Mở modal chi tiết nhãn**:
   - Chuyển sang tab **"Kho mẫu nét"**.
   - Bấm vào một nhãn có nhiều mẫu (ví dụ nhãn có $\ge 3$ mẫu nét).
   - Kiểm tra giao diện modal:
     * Mỗi thẻ biến thể mẫu nét hiển thị thumbnail, hộp kiểm ở góc, và nút icon thùng rác (🗑).
     * Phía trên lưới mẫu có thanh điều khiển gồm hộp kiểm "Chọn tất cả" và nút "Xoá biến thể đã chọn" (đang ẩn vì chưa chọn mẫu nào).
3. **Thao tác xóa nhanh 1 mẫu (User Story 2)**:
   - Bấm vào biểu tượng thùng rác trên Mẫu #2.
   - Hộp thoại hỏi: `"Bạn có chắc chắn muốn xoá Mẫu #2 của nhãn ... không?"`.
   - Bấm **OK**.
   - Kiểm tra: Mẫu #2 biến mất, các mẫu còn lại được đánh số lại (#1, #2,...), số lượng mẫu trên tiêu đề giảm đi 1.
4. **Thao tác chọn và xóa nhiều mẫu (User Story 1)**:
   - Tích chọn 2 thẻ mẫu bất kỳ.
   - Thẻ mẫu chuyển sang trạng thái viền xanh nổi bật (`selected`).
   - Nút phía trên hiển thị: `"🗑 Xoá 2 biến thể đã chọn"`.
   - Bấm nút xóa, xác nhận trong hộp thoại.
   - Kiểm tra: Đúng 2 mẫu đã chọn bị xóa, các mẫu khác không bị ảnh hưởng.
5. **Thao tác xóa toàn bộ biến thể (User Story 3)**:
   - Tích chọn tất cả các mẫu còn lại (hoặc tích vào "Chọn tất cả").
   - Nút hiển thị: `"🗑 Xoá N biến thể đã chọn"`.
   - Bấm nút xóa và xác nhận.
   - Kiểm tra: Modal tự động đóng lại, thẻ nhãn được dọn dẹp biến mất khỏi danh sách kho mẫu bên ngoài.
