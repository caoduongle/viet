# Contract: Khống chế bộ nhớ tập hợp PUA và chuẩn hóa kiểm thử hiệu năng

**Branch**: `064-pua-memory-and-benchmark` | **Date**: 2026-10-28 | **Spec**: [spec.md](../spec.md)

---

## 1. Phương thức: `MarkdownImporter._choose_fake_close_placeholder`

```python
@classmethod
def _choose_fake_close_placeholder(cls, text: str) -> str | None:
    """Chọn ký tự giữ chỗ cho dấu đóng giả từ vùng Private Use Area của BMP (U+E000..U+F8FF).

    Độ phức tạp tính toán:
    - Nhánh nhanh (khi U+E000 không có trong text): Thời gian tìm chuỗi con O(N) ở tầng C
      (thuật toán Two-Way), bộ nhớ phụ O(1) (không cấp phát tập hợp phụ hay danh sách trung gian).
    - Nhánh va chạm (khi U+E000 xuất hiện): Thực hiện 2 lượt quét chuỗi O(N) ở tầng C
      (lượt 1: kiểm tra sự hiện diện, lượt 2: _PUA_RE.finditer trích xuất các ký tự PUA),
      bộ nhớ phụ O(min(N, 6400)) bị chặn cứng bởi 6.400 phần tử và không tạo danh sách trung gian.
    """
```

### Tiền điều kiện (Preconditions)
- `text`: Chuỗi bất kỳ (`str`), có thể rỗng hoặc chứa hàng triệu ký tự với bảng chữ cái Unicode bất kỳ.

### Hậu điều kiện (Postconditions)
1. **Kiểu trả về (`str | None`)**:
   - Trả về `str` có độ dài 1 nằm trong dải `[0xE000, 0xF8FF]` sao cho `result not in text`.
   - Trả về `None` khi và chỉ khi toàn bộ 6.400 ký tự trong dải đều xuất hiện trong `text`.
2. **Khống chế bộ nhớ**:
   - Tập hợp điểm mã `used_cps` chỉ chứa số nguyên nằm trong đoạn $[0xE000, 0xF8FF]$.
   - Dung lượng phần tử của `used_cps` luôn thỏa mãn $0 \le |\text{used\_cps}| \le 6.400$.
   - Không khởi tạo cấu trúc dữ liệu lưu trữ toàn bộ các ký tự phân biệt của `text`.

---

## 2. Hợp đồng Kiểm thử Hiệu năng đối kháng

### Phương thức: `test_adversarial_complexity_multi_length_backticks_and_long_lines`

1. **Số lượng mẫu đo**: Thực hiện cố định $M = 5$ lượt đo cho mỗi kích thước dữ liệu $N$ (1.000 chunks) và $4N$ (4.000 chunks).
2. **Công thức tính tỷ lệ đại diện**:
   $$\text{ratios} = [ R_1, R_2, R_3, R_4, R_5 ] \quad \text{với} \quad R_k = \frac{T(4N)_k}{\max(T(N)_k, 0.001)}$$
   $$\text{ratio}_{\text{med}} = \operatorname{statistics.median}(\text{ratios})$$
3. **Tiêu chuẩn nghiệm thu**:
   $$\text{ratio}_{\text{med}} \le 6.0$$
4. **Tính minh bạch**: Thông điệp lỗi khi không đạt phải in rõ toàn bộ danh sách 5 tỷ lệ $[R_1, \dots, R_5]$ và các giá trị trung vị $T(N)$, $T(4N)$.

---

## 3. Bảng ca kiểm thử chi tiết

| Mã ca kiểm thử | Mục đích kiểm thử | Dữ liệu đầu vào | Kết quả mong đợi |
| :--- | :--- | :--- | :--- |
| **C-MEM-MULTILINGUAL** | Kiểm tra khống chế bộ nhớ khi văn bản đa ngữ chứa hàng nghìn ký tự phân biệt và có `\ue000` | Chuỗi 10.000 ký tự chữ Hán/Nôm khác nhau + `\ue000` | Trả về `\ue001`, tập hợp nội bộ chỉ có đúng 1 phần tử |
| **C-MEM-BOUNDED-CHAIN** | Kiểm tra khống chế bộ nhớ khi có chuỗi va chạm PUA trong văn bản đa ngữ lớn | Chuỗi 10.000 ký tự đa ngữ + 10 ký tự `\ue000`..`\ue009` | Trả về `\ue00a`, tập hợp nội bộ chỉ có đúng 10 phần tử |
| **C-MEDIAN-BENCHMARK** | Đánh giá tỷ lệ tăng trưởng tuyến tính bằng trung vị | Văn bản đối kháng 1.000 chunks ($N$) và 4.000 chunks ($4N$) | $\operatorname{median}(\text{ratios}) \le 6.0$, không sử dụng `min(ratio, retry)` |
