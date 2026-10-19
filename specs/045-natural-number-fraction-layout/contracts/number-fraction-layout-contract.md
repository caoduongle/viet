# Interface Contract: Number & Fraction Typography Layout

**Feature**: `045-natural-number-fraction-layout`  
**Date**: 2026-10-20

## 1. Writer Module Contract (`chuviettay/model/writer.py`)

### `Writer.number(s: str)` & `Writer._normalize_digit_sample(inst: dict, ch: str)`
- **Đầu vào**: `s` (chuỗi số, ví dụ `"2024"`, `"0,39"`, `"0,0278"`, `"16"`, `"-228"`, `"25%"`).
- **Hành vi**:
  1. Với mỗi ký tự `ch` thuộc nhóm số/ký hiệu số:
     - Lấy mẫu từ `bank.digits` (hoặc fallback `bank.words`).
     - Với `ch in "0123456789%"`:
       - Baseline: Dịch `dy = -max_y` để chân chữ chạm đường cơ sở `y = 0.0`.
       - Chiều cao: Nếu `sample_h` nằm ngoài `[1.14 * xh, 1.26 * xh]`, co giãn dọc `scale_y = clamp(1.20 * xh / sample_h, 0.35, 1.85)` và co giãn ngang `scale_x = clamp(scale_y ** 0.5, 0.75, 1.30)`.
       - Hoành độ: Dịch `dx = -min_x` để nét bắt đầu từ gốc ngang `0.0`; `advance_width = (raw_max_x - raw_min_x) * scale_x`.
     - Với `ch == "-"`:
       - Dịch `dx = -min_x` về `0.0` và căn tâm dọc tại trục toán học `y = -0.45 * xh` (không kéo dấu âm xuống `y = 0.0` và không phóng chiều cao nét ngang).
  2. Đồng bộ hóa trên toàn bộ đường dẫn truy xuất của `Writer`:
     - `Writer.token(tok)` khi `tok` là chữ số đơn (`"0"`–`"9"`), `Writer.get_letter_sample(char)` khi ghép từ chứa chữ số (như `"A1"`, `"3D"`), và `Writer.get_char_advance_width(char)` / `Writer.measure_text_width(text)` PHẢI sử dụng cùng mẫu chữ số đã chuẩn hóa để thống nhất kích thước và ước lượng ngắt dòng.
  3. Khoảng cách giữa các chữ số liên tiếp (`dgap`):
     - Luôn bị kẹp chặt trong khoảng `[0.10 * xh, 0.18 * xh]`.
  4. Dấu thập phân (`,` hoặc `.`):
     - Chuẩn hóa gốc `min_x = 0.0`.
     - Đặt ngay sau phần nguyên với khoảng hở `0.08 * xh`.
     - Khoảng cách từ dấu thập phân đến chữ số đầu tiên sau dấu phẩy là `0.10 * xh`.
     - Các chữ số tiếp theo trong phần thập phân áp dụng `dgap` chuẩn (`0.10 * xh .. 0.18 * xh`), tạo sự đồng đều thị giác tuyệt đối.
- **Đầu ra**:
  - `strokes`: Danh sách nét đã dịch vị trí tuyệt đối trong hệ tọa độ của chuỗi số.
  - `total_width`: Độ rộng tiến của toàn bộ chuỗi số.
  - `missing`: Danh sách ký tự còn thiếu mẫu trong kho.
- **Bất biến**:
  - Mọi điểm thấp nhất của các chữ số `"0"`–`"9"` nằm sát đường cơ sở `y = 0.0` với sai số `<= 0.08 * xh`.
  - Độ lệch chiều cao giữa chữ số cao nhất và thấp nhất trong `"0"`–`"9"` không vượt quá `12%`.
  - Không có khoảng trống bất thường giữa các chữ số thập phân (`gap <= 0.20 * xh`).

---

## 2. LaTeX Math Parser Contract (`chuviettay/math/parser.py`)

### `LatexMathParser._parse_atom() & _NUM_RE`
- **Đầu vào**: Chuỗi con LaTeX toán học bắt đầu bằng chữ số (ví dụ `"0,39"`, `"0,0278,   1 \le x < 2"`, `"1/36"`).
- **Hành vi**:
  1. Biểu thức `_NUM_RE`:
     ```python
     _NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*(?:(?:\{,\}|,(?=[0-9]))[0-9]+)*")
     ```
  2. Khi gặp chuỗi số thập phân có dấu phẩy đi liền trước chữ số (ví dụ `"0,39"`, `"0,0278"`, `"194,9"`):
     - Khớp trọn vẹn cả phần nguyên, dấu phẩy và phần thập phân thành một `TextNode("0,39", kind="num")`.
  3. Khi gặp dấu phẩy kết thúc vế (ví dụ `"0,0278,"`):
     - Chỉ khớp `"0,0278"` là `TextNode("0,0278", kind="num")`.
     - Dấu phẩy ở cuối không đi liền trước chữ số nên được phân tích riêng thành `SymbolNode(",")`.
  4. Khi gặp dấu phẩy có khoảng trắng (ví dụ `(0, 1)`):
     - Phân tích thành `TextNode("0")`, `SymbolNode(",")`, `TextNode("1")`.
- **Đầu ra**: Cây AST phân loại đúng số thập phân tiếng Việt tự nhiên mà không cần bọc `{,}`.

---

## 3. Math Layout Engine Contract (`chuviettay/layout/math_layout.py`)

### `MathLayoutEngine._m_TextNode(node: TextNode)`
- **Đầu vào**: `node` với `kind == "num"` hoặc chuỗi chỉ chứa chữ số và dấu chấm/phẩy.
- **Hành vi**:
  - `descent` được tính theo nét vẽ thực: `max(0.0, max(ys) * eff)`. Không áp đặt `0.2 * xh` giả tạo khi chữ số không có nét chân thò xuống dưới baseline.
  - `ascent` được tính theo đỉnh nét thực: `max(0.85 * self.xh * eff, -min(ys) * eff)`.

### `MathLayoutEngine._m_Fraction(node: Fraction)` & `_m_Matrix(node: Matrix)`
- **Đầu vào**: `node` phân số gồm `node.num` và `node.den`.
- **Hành vi**:
  - `child_scale`: `scale * (0.78 if (self._frac_level > 0 or self._matrix_level > 0) else 0.80)`.
  - `gap`: `(0.20 if node.bar else 0.12) * self.xh * eff`.
  - `overhang` (độ dài thanh gạch nhô ra mỗi bên): `(0.18 if node.bar else 0.08) * self.xh * eff` (`pad = 2.0 * overhang`).
  - Định vị `num_y` và `den_y` dựa trên biên dọc thực tế của nét vẽ (`num_ink_bot`, `den_ink_top`) để triệt tiêu hoàn toàn khoảng đệm ảo từ `MathRow` hoặc ký tự không có nét sổ dưới.
  - Trong `_m_Matrix`, quản lý bộ đếm `self._matrix_level` và điều chỉnh `row_gap = 0.35 * xh` cho `cases` để nhịp dòng phân số vừa vặn với dòng kẻ vở.
- **Đầu ra**: `MathLayoutItem` có kích thước thanh mảnh, khoảng hở tử/mẫu đối xứng và gọn gàng.
- **Bất biến**:
  - Khoảng cách quang học thực tế từ nét thấp nhất của tử số đến gạch phân số (`node.bar=True`) nằm trong `[0.15 * xh, 0.25 * xh]`.
  - Khoảng cách quang học thực tế từ gạch phân số (`node.bar=True`) đến nét cao nhất của mẫu số nằm trong `[0.15 * xh, 0.25 * xh]`.
  - Thanh gạch phân số (`node.bar=True`) chỉ vươn ra mỗi bên từ `0.15 * xh` đến `0.25 * xh` so với phần tử rộng hơn.
