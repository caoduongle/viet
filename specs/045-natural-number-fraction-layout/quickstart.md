# Quickstart & Verification Guide: Natural Number & Fraction Layout

**Feature**: `045-natural-number-fraction-layout`  
**Date**: 2026-10-20

## 1. Quick Verification via Automated Tests

### Chạy các bài kiểm tra hiện tại và kiểm tra hồi quy
```bash
pytest tests/test_writer.py tests/test_digits_and_punct.py tests/test_punctuation_spacing.py tests/test_math_layout.py -q
```
*Kỳ vọng: 100% test hiện có pass.*

### Chạy bài kiểm tra chuyên biệt cho Feature 045
```bash
pytest tests/test_number_fraction_typography.py -v
```
*File test `test_number_fraction_typography.py` sẽ bao phủ các ca kiểm tra:*
1. **Kiểm tra chuẩn hóa baseline và chiều cao chữ số**:
   - Mẫu chữ số có `max_y` bị lệch trong kho được đưa về `y = 0.0`.
   - Các chữ số từ `0` đến `9` có chiều cao hiển thị đồng đều trong `[1.05 * xh, 1.30 * xh]`.
2. **Kiểm tra khoảng cách số và số thập phân**:
   - Khoảng hở giữa các chữ số trong `16`, `25`, `36` đạt `0.10 * xh .. 0.18 * xh`.
   - Trong `0,39`, `0,20`, `0,0278`, khoảng cách quanh dấu phẩy và giữa các chữ số thập phân hài hòa, không bị dãn cách quá xa.
3. **Kiểm tra bộ phân tích cú pháp LaTeX toán (`LatexMathParser`)**:
   - `$0,39$` và `$0,0278$` được phân tích trực tiếp thành `TextNode(..., kind="num")`.
   - `$0,0278,   1 \le x < 2$` nhận diện đúng dấu phẩy thứ hai là `SymbolNode(",")`.
   - `$(0, 1)$` nhận diện đúng dấu phẩy liệt kê là `SymbolNode(",")`.
4. **Kiểm tra bố cục phân số (`MathLayoutEngine`)**:
   - Khoảng cách từ nét tử số đến gạch phân số và từ gạch phân số đến nét mẫu số trong `\frac{1}{36}` đạt `0.15 * xh .. 0.25 * xh`.
   - Độ dài gạch phân số thò ra hai bên gọn gàng trong `0.15 * xh .. 0.25 * xh`.
   - Tổng chiều cao phân số số học giảm tối thiểu 25% so với phiên bản cũ.

---

## 2. End-to-End Visual Verification via CLI

### Bước 1: Tạo file Markdown kiểm thử đại diện cho các ảnh chụp của người dùng
Tạo file `test_math_sample.md`:
```markdown
- Tính $P(X = 2)$ : $P(X = 2) = F_X(2) - F_X(1) = 0,39 - 0,19 = 0,20$
- Tính $P(X > 3)$ : $P(X > 3) = 1 - F_X(3) = 1 - 0,67 = 0,33$
- Tính $P(2 \le X \le 5)$ :
$P(2 \le X \le 5) = F_X(5) - F_X(1) = 0,97 - 0,19 = 0,78$

Hàm phân phối từng khúc:
$$
F_M(x) = \begin{cases}
0, & x < 1 \\
\frac{1}{36} \approx 0,0278, & 1 \le x < 2 \\
\frac{4}{36} \approx 0,1111, & 2 \le x < 3 \\
\frac{9}{36} = 0,25, & 3 \le x < 4 \\
\frac{16}{36} \approx 0,4444, & 4 \le x < 5 \\
\frac{25}{36} \approx 0,6944, & 5 \le x < 6 \\
1, & x \ge 6
\end{cases}
$$
```

### Bước 2: Kết xuất sang file `.xopp`
```bash
python -m chuviettay.cli write test_math_sample.md -o output_math_sample.xopp --bank local\ data/kho_mau_v4.json.gz
```

### Bước 3: Đánh giá trực quan
Mở `output_math_sample.xopp` trong Xournal++ hoặc công cụ xem XOPP:
1. **Các con số `0,39`, `0,19`, `0,20`, `0,0278`, `0,1111`**:
   - Tất cả chữ số cùng đứng ngay ngắn trên đường cơ sở.
   - Các chữ số trong cùng một số đi liền nhau mạch lạc, không còn khoảng trống rộng bất thường giữa các chữ số thập phân (`0,3 9`).
2. **Các phân số `\frac{1}{36}` đến `\frac{25}{36}`**:
   - Tử số và mẫu số áp sát thanh gạch ngang vừa vặn, không còn hai khoảng trống rỗng lớn ở giữa.
   - Thanh gạch phân số ôm gọn tử/mẫu, thẳng hàng với trục tâm của dấu `=` và `≈`.
   - Các dòng trong khối `cases` nằm cân đối trên nền giấy kẻ ngang.
