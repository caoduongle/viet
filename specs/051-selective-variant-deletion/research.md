# Technical Research: Chọn và Xóa Biến Thể Mẫu Nét Tùy Chọn

**Feature Branch**: `051-selective-variant-deletion`  
**Date**: 2026-10-20  
**Spec**: [spec.md](spec.md)

---

## 1. Mục tiêu Nghiên cứu

Giải quyết bài toán cho phép người dùng lựa chọn và xóa từng biến thể mẫu nét (sample variants) cụ thể của một nhãn trong cửa sổ chi tiết nhãn, thay vì chỉ có một lựa chọn duy nhất là xóa toàn bộ nhãn (`drop_label`). Cần đảm bảo:
1. Toàn vẹn dữ liệu kho mẫu nét ở tầng cốt lõi Python (`chuviettay.model.bank.Bank`).
2. Cơ chế xóa ổn định, không làm xáo trộn chỉ số khi xóa nhiều biến thể cùng lúc.
3. Xử lý chính xác trường hợp biên: khi toàn bộ biến thể bị xóa hết thì nhãn phải được dọn dẹp sạch sẽ (tạo tombstone để đồng bộ).
4. Phân phối lệnh qua cầu nối IPC (Worker Bridge & Pyodide).
5. Trải nghiệm người dùng mượt mà, trực quan, có hộp thoại xác nhận an toàn và tuân thủ hợp đồng bảo mật DOM (XSS Prevention).

---

## 2. Phân tích Hiện trạng Hệ thống

### 2.1. Cấu trúc lưu trữ mẫu nét trong `Bank`
Trong `chuviettay/model/bank.py`, các mẫu nét được lưu trữ theo từ điển phân loại:
- `self.words`: `dict[str, list[dict]]`
- `self.letters`: `dict[str, list[dict]]`
- `self.digits`: `dict[str, list[dict]]`
- `self.punct`: `dict[str, list[dict]]`
- `self.symbols`: `dict[str, list[dict]]`
- `self.marks`: `dict[str, list[dict]]`

Mỗi mẫu nét (`sample`) là một dictionary chứa:
```python
{
    "w": 5.33,               # Chiều rộng nét (width pt)
    "s": [[[x, y], ...]],   # Danh sách nét vẽ (strokes)
    "_sig": "...",          # Chữ ký hash chống trùng lặp
    # Đối với từ (words): có thể có thêm "T" (dấu thanh), "ti" (chỉ số nét thanh)
}
```

### 2.2. Cơ chế xóa hiện tại
Hiện tại, `Bank` chỉ cung cấp:
- `drop(word, category)`: Xóa toàn bộ danh sách `target_dict.pop(word, [])`.
- `drop_batch(items)`: Xóa hàng loạt nhãn.
- `drop_char(char)` / `drop_words(words)` trong `AppController`.
- `drop_label(label, category)` trong `BrowserBridge` và `py-worker.js`.

Chưa có hàm nào cho phép xóa một tập hợp con các mẫu nét (sub-list of samples) của một nhãn cụ thể.

---

## 3. Các Quyết định Kỹ thuật (Decisions & Rationales)

### Quyết định 1: Thuật toán xóa nhiều mẫu nét theo chỉ số (Reverse Index Removal)
- **Quyết định**: Nhận danh sách chỉ số 0-based `indices: list[int]`. Sắp xếp các chỉ số theo thứ tự giảm dần: `sorted(set(indices), reverse=True)`, sau đó lần lượt gọi `samples.pop(idx)`.
- **Lý do**:
  - Khi xóa phần tử khỏi mảng (Python `list`), nếu xóa từ vị trí nhỏ trước, các phần tử phía sau sẽ bị dịch chuyển chỉ số (index shift), dẫn đến xóa nhầm phần tử khác hoặc lỗi `IndexError`.
  - Xóa từ chỉ số lớn nhất về chỉ số nhỏ nhất đảm bảo các chỉ số còn lại không bị thay đổi vị trí.
- **Phương án khác đã cân nhắc**:
  - *Tạo mảng mới bằng filter list comprehension*: `[s for i, s in enumerate(samples) if i not in set(indices)]`. Phương án này cũng tốt và an toàn, tuy nhiên việc dùng `sorted(..., reverse=True)` kết hợp kiểm tra biên `0 <= idx < len(samples)` cho phép đếm chính xác số lượng mẫu thực tế đã loại bỏ và phát hiện chỉ số không hợp lệ. Chúng ta có thể dùng filter hoặc pop ngược; cả hai đều đạt độ phức tạp $O(N)$ với $N \le 20$ (số mẫu của 1 nhãn thường từ 1 đến 10 mẫu).

### Quyết định 2: Xử lý khi xóa hết mẫu nét (Empty Label Cleanup)
- **Quyết định**:
  - Nếu sau khi xóa, `len(samples) == 0`:
    - Xóa nhãn khỏi `target_dict`: `target_dict.pop(label, None)`.
    - Ghi nhận tombstone: `tomb_key = f"{cat}:{label}"` vào `self._tombstones` và `self._deleted_words`.
    - Dọn dẹp chỉ mục thay thế `tl` và `marks` (nếu là `words`).
    - Trả về `label_deleted = True`.
  - Nếu `len(samples) > 0`:
    - Nhãn vẫn tồn tại, không tạo tombstone.
    - Cập nhật `self._mutation_seq += 1`, `self._generation += 1`, `self._dirty = True`.
    - Tái lập chỉ mục `self.rebuild()` nếu thuộc phân loại `words` hoặc `marks`.
    - Trả về `label_deleted = False`.
- **Lý do**:
  - Một nhãn không còn mẫu nét nào sẽ gây lỗi cho engine kết xuất chữ viết tay (`Writer`) nếu vẫn còn giữ key trong từ điển với list rỗng `[]`.
  - Đồng bộ đa tab / IndexedDB phụ thuộc vào tombstone để biết nhãn nào đã bị xóa hoàn toàn.

### Quyết định 3: Giao diện người dùng trong Modal chi tiết nhãn
- **Quyết định**:
  - Thêm checkbox góc trên mỗi thẻ mẫu `.sample-item-card` (`.sample-item-checkbox`).
  - Thêm nút xóa nhanh (thùng rác) trên mỗi thẻ mẫu (`.sample-item-delete-btn`).
  - Thêm thanh công cụ hàng loạt ngay trên lưới mẫu:
    - Checkbox "Chọn tất cả" (`#chk-modal-select-all`).
    - Nút "Xoá [N] biến thể đã chọn" (`#btn-label-delete-selected`), chỉ hiển thị/kích hoạt khi `N > 0`.
  - Thao tác click vào thẻ mẫu nét (ngoài các nút chức năng) sẽ bật/tắt lựa chọn mẫu đó.
  - Khi đã chọn mẫu: thẻ có viền nổi bật `var(--primary)` và nền xanh nhạt.
- **Lý do**:
  - Đáp ứng trọn vẹn cả 2 kịch bản: muốn xóa nhanh 1 mẫu xấu (1 click) hoặc muốn dọn dẹp chọn lọc nhiều mẫu (multi-select batch delete).
  - Giữ nguyên nút "Xoá nhãn này" ở góc trên để người dùng vẫn có thể xóa toàn bộ nhãn tức thì khi cần.

### Quyết định 4: Hộp thoại xác nhận an toàn (Confirmation Dialogs)
- **Quyết định**:
  - Khi xóa 1 mẫu qua nút nhanh: `confirm('Bạn có chắc chắn muốn xoá Mẫu #{k} của nhãn "{label}" không?')`.
  - Khi xóa nhiều mẫu: `confirm('Bạn có chắc chắn muốn xoá {N} biến thể đã chọn của nhãn "{label}" không?\n(Lưu ý: Hành động này không thể hoàn tác)')`.
  - Khi số mẫu chọn bằng tổng số mẫu của nhãn: `confirm('Bạn có chắc chắn muốn xoá toàn bộ {N} biến thể của nhãn "{label}" không?\n(Hành động này sẽ xóa nhãn khỏi kho mẫu)')`.
- **Lý do**: Phòng tránh việc vô tình bấm nhầm làm mất dữ liệu nét viết quý giá của người dùng.

### Quyết định 5: Tuân thủ bảo mật DOM (XSS Prevention)
- **Quyết định**: Sử dụng `escapeHtml()` cho tất cả các chuỗi nội suy vào `innerHTML` (bao gồm `label`, `sample.w`, thông báo lỗi).
- **Lý do**: Đảm bảo an toàn tuyệt đối khi nhãn chứa các ký tự đặc biệt như `<`, `>`, `&`, `"`, `'` (ví dụ dấu câu toán học, nhãn HTML).

---

## 4. Đánh giá Tác động & Tương thích Ngược
- Không làm thay đổi cấu trúc schema của tệp `.json.gz`.
- Giữ nguyên tính năng của `drop_label` hiện hữu.
- Giữ nguyên cơ chế đồng bộ IndexedDB `storage.syncAndSaveActiveProfile` và kênh broadcast `chuviettay_sync`.
- Bản đóng gói web `scripts/build_web.py` sẽ cập nhật `chuviettay.zip` và frontend đồng bộ.
