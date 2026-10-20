# Contract: Writer Number Parity & Geometry Robustness

## 1. Chuẩn hóa hình học chữ số suy biến (`_normalize_digit_sample`)

### Ràng buộc
- Khi mẫu chữ số `inst` có:
  - `sample_h <= 1e-3` (chiều cao xấp xỉ 0), HOẶC
  - `bbox_w <= 1e-3` (chiều rộng xấp xỉ 0), HOẶC
  - Không có điểm nét hợp lệ:
- Phương thức `_normalize_digit_sample(inst, ch, xh)`:
  1. Không được chia cho `sample_h`.
  2. Áp dụng giá trị độ rộng dự phòng an toàn:
     $$\text{adv\_w} = \max(\text{raw\_w}, 0.60 \times x_h)$$
  3. Lấy nét dự phòng chuẩn từ `get_vector_glyph_fallback(ch, xh)` nếu các nét hiện có không thể hiển thị được.
  4. Trả về `(strokes, adv_w)` hợp lệ, không ném ngoại lệ hay trả về `NaN` / `Infinity`.

---

## 2. Đo đạc độ rộng số học (`measure_text_width` vs `number`)

### Ràng buộc
- Với bất kỳ chuỗi số $S$ hợp lệ (`NUMRE.match(S)`):
  $$|\text{Writer.measure\_text\_width}(S) - \text{Writer.number}(S)[1]| \le 0.05 \times x_h$$
- Hợp đồng này áp dụng cho:
  - Số nguyên đơn lẻ: `"0"`, `"5"`, `"9"`
  - Số nguyên dài: `"123456789"`
  - Số âm: `"-5"`, `"-12345"`
  - Số thập phân có dấu phẩy hoặc chấm: `"0,39"`, `"0,0278"`, `"-123,45"`, `"3.14159"`
  - Cả kho mẫu đơn biến thể và kho mẫu đa biến thể (`sample_bank_v4`, `kho_mau_tong_hop`, v.v.).
- Khi `self.stable_variants = True`, `measure_text_width(S)` không được làm biến đổi bộ đếm ngẫu nhiên nội bộ `self.last` hoặc làm thay đổi kết quả các lần tạo từ tiếp theo.
