# Research & Technical Decisions: Natural Number & Fraction Typography

**Feature**: `045-natural-number-fraction-layout`  
**Date**: 2026-10-20  
**Status**: Completed

## 1. Baseline Alignment and Height Normalization for Digits

### Context & Problem
Trong kho chữ số viết tay (`bank.digits`), các mẫu chữ số được người dùng viết vào lưới ô mẫu tự do hoặc thu thập qua nhiều phiên:
- **Lệch đường cơ sở (`baseline drift`)**: Trong `kho_mau_v4.json.gz`, chữ số `8` có `max_y = -0.90` (treo lơ lửng cách baseline gần 1 đơn vị), chữ số `4` có `max_y = -0.72`, `3` có `max_y = -0.65`, trong khi `1` chạm `+0.14`. Trong kho người dùng (`chu_cua_ban.json.gz`), độ lệch chân chữ còn lớn hơn nhiều (`max_y` dao động từ `-5.49` đến `+10.68`).
- **Lệch chiều cao chữ số (`height disparity`)**: Chữ số `4` chỉ cao `5.56` (`0.70 * xh`), `7` cao `5.80`, `6` và `8` cao `6.09`, trong khi `5` cao `9.88` (`1.24 * xh`) và `9` cao `8.79`. Khi đặt cạnh nhau trong các số như `16`, `25`, `36`, `0,6944`, `0,0278`, chữ số `4`, `6`, `7`, `8` trông còi cọc và nhấp nhô phi tự nhiên cạnh chữ số `5`, `9`.

#### Decision
Thực hiện chuẩn hóa hình học 2 chiều (`_normalize_digit_sample`) tại tầng `Writer` cho mọi truy xuất mẫu chữ số (`Writer.number()`, `Writer.token()`, `Writer.get_letter_sample()`):
1. **Phân tách rõ chữ số (`0`–`9`), dấu phần trăm (`%`) và dấu âm (`-`)**:
   - Chỉ áp dụng chuẩn hóa chân chữ về `y = 0.0` và chiều cao lining figures (`1.20 * xh`) cho các chữ số `"0"`–`"9"` và `"%"`.
   - Với dấu `"-"` trong `bank.digits` (khi viết số âm như `"-228"`): chuẩn hóa `min_x = 0.0` nhưng căn tâm dọc tại trục toán học `y = -0.45 * xh` (không kéo dấu âm xuống baseline `y = 0.0` và không phóng chiều cao nét ngang lên `1.20 * xh`).
2. **Chuẩn hóa chân chữ (baseline grounding)**:
   - Tính tọa độ `max_y` của tất cả điểm nét trong mẫu số: `sample_max_y = max(pt for st in strokes for pt in st[1::2])`.
   - Dịch chuyển theo phương dọc: `dy = -sample_max_y`. Sau phép dịch, điểm thấp nhất của chữ số luôn tiếp xúc chính xác tại `y = 0.0` (đường cơ sở).
3. **Quy chuẩn tỷ lệ chiều cao đồng nhất (uniform lining height)**:
   - Định nghĩa chiều cao mục tiêu chuẩn cho chữ số: `target_digit_h = 1.20 * xh` (chiều cao chuẩn của chữ số đồng cao - lining figures).
   - Chiều cao thực của mẫu: `sample_h = sample_max_y - min(pt for st in strokes for pt in st[1::2])`.
   - Nếu `sample_h > 1e-3` và nằm ngoài dải dung sai hẹp `[1.14 * xh, 1.26 * xh]` (`±5%` quanh `1.20 * xh`), tính hệ số co giãn dọc: `scale_y = clamp(target_digit_h / sample_h, 0.35, 1.85)` để bảo đảm 100% mẫu số (kể cả mẫu rất nhỏ `5.56` trong `kho_mau_v4` hay mẫu ngoại lai `20.35` trong `chu_cua_ban`) đều hội tụ về dải chiều cao đồng nhất (chênh lệch `< 12%`, thỏa mãn `SC-001` và `INV-002`).
   - Hệ số co giãn ngang được điều tiết nhẹ `scale_x = clamp(scale_y ** 0.5, 0.75, 1.30)` để giữ tỷ lệ nét tự nhiên, không làm chữ số bị quá béo hoặc quá gầy khi co giãn mạnh theo chiều dọc.
4. **Chuẩn hóa biên ngang sát nét thực (tight optical width)**:
   - Dịch `min_x` về `0.0`, độ rộng tiến `advance_width = (raw_max_x - raw_min_x) * scale_x` (không cộng thêm lề phụ vào `advance_width` vì khoảng cách giữa các chữ số đã được kiểm soát hoàn toàn bởi `dgap`), đồng thời đồng bộ với `get_char_advance_width()` và `measure_text_width()`.

### Rationale
- Việc chuẩn hóa trực tiếp khi kết xuất đảm bảo 100% kho mẫu hiện có và kho mẫu cũ của người dùng tự động hiển thị đẹp ngay lập tức mà không yêu cầu người dùng phải vẽ lại kho chữ.
- Chữ số đồng cao (lining figures) là quy chuẩn quốc tế và sách giáo khoa cho toán học và khoa học, giúp biểu thức thẳng hàng, chữ số không bị nhảy nhót.

### Alternatives Considered
- *Bắt người dùng vẽ lại ô mẫu trong file XOPP*: Bị bác bỏ vì phá vỡ trải nghiệm người dùng, không giải quyết được các kho mẫu sẵn có.
- *Chỉ co giãn khi `sample_h` ngoài `[0.95 * xh, 1.45 * xh]` với clamp `[0.75, 1.40]`*: Bị bác bỏ vì để lọt độ lệch chiều cao lên tới 52% giữa các chữ số trong dải `[0.95, 1.45] * xh` và không xử lý triệt để mẫu quá lớn trong `chu_cua_ban.json.gz`.

---

## 2. Tight, Natural Inter-digit Spacing and Decimal Comma Spacing

### Context & Problem
- Trong `Writer._resolve_dgap()`, điều kiện lọc `valid_gaps = [float(g) for g in raw_gaps if 0.5 <= float(g) <= 0.55 * xh]` cho phép lấy các giá trị lên tới `0.55 * xh` (tương đương `~3.5` đến `4.3` pt). Trong khi đó, bề rộng thân của chữ số chỉ khoảng `3.5` đến `4.0` pt. Hậu quả là khoảng cách giữa 2 chữ số gần bằng bề rộng cả một con số, biến `36` thành `3  6`.
- Trong `Writer.number()`, khi gặp dấu phẩy `,`, biến `first` được đặt lại thành `True`. Chữ số đầu tiên sau dấu phẩy được áp dụng khoảng cách sát dấu phẩy (`0.10 * xh`), nhưng chữ số thứ hai trở đi lại bị cộng `dgap` lớn (`~3.5` pt). Điều này tạo ra hình ảnh dị dạng `0,3  9` và `0,0  2  7  8`.

### Decision
1. **Thu hẹp và chuẩn hóa `dgap`**:
   - Khoảng cách giữa hai chữ số liên tiếp trong cùng một số phải nằm trong dải quang học tự nhiên: `min_dgap = 0.10 * xh`, `max_dgap = 0.18 * xh`, giá trị danh định `default_dgap = 0.12 * xh`.
   - Nếu `raw_gaps` trong kho chứa giá trị, ánh xạ và kẹp chặt: `clamp(g * (xh / 7.94), 0.10 * xh, 0.18 * xh)`.
2. **Đồng bộ khoảng cách dấu thập phân**:
   - Sau dấu phẩy thập phân `,`, khoảng cách đến chữ số đầu tiên sau dấu phẩy là `0.10 * xh`.
   - Biến `first` sau dấu phẩy được xử lý sao cho khoảng cách giữa các chữ số tiếp theo trong phần thập phân sử dụng đúng `dgap` chuẩn (`0.10 * xh .. 0.18 * xh`), chênh lệch với khoảng cách sau dấu phẩy không quá `0.08 * xh`.
   - Nhờ đó, chuỗi `0,39` và `0,0278` tạo thành một dòng chảy số học liền mạch, chữ số không bị đứt rời.

### Rationale
- Đảm bảo tính nhất quán thị giác giữa phần nguyên, dấu ngăn cách và phần thập phân.
- Tuân thủ nguyên tắc typographic: các chữ số trong cùng một số cần liên kết chặt chẽ (tight tracking) để phân biệt rõ ràng với khoảng cách giữa các từ riêng biệt (`wgaps ~ 0.8 * xh .. 1.8 * xh`).

---

## 3. Vietnamese Decimal Comma in LaTeX Math (`LatexMathParser`)

### Context & Problem
Trong LaTeX chuẩn TeX, dấu phẩy `,` luôn được coi là dấu câu (`SymbolNode(",")`, class `"punct"`). Khi người dùng viết `$0,39$` hoặc `$0,0278$` mà không dùng cú pháp TeX phức tạp `$0{,}39$`:
- Bộ phân tích cú pháp `LatexMathParser` tách thành: `TextNode("0")`, `SymbolNode(",")`, `TextNode("39")`.
- `MathLayoutEngine` áp dụng khoảng cách giữa `"ord"` và `"punct"` (`0.17 * xh`) rồi giữa `"punct"` và `"ord"` (`0.32 * xh`), biến biểu thức số học thành 3 nguyên tử rời rạc.

### Decision
Cải tiến biểu thức chính quy số học `_NUM_RE` trong `chuviettay/math/parser.py`:
- Cũ: `_NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*(?:\{,\}[0-9]+)?")`
- Mới: `_NUM_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*(?:(?:\{,\}|,(?=[0-9]))[0-9]+)*")`
- **Cơ chế**: Dùng lookahead `,(?=[0-9])` để nhận diện dấu phẩy thập phân:
  - Khi dấu phẩy đứng ngay trước chữ số mà không có khoảng trắng (ví dụ `0,39`, `0,0278`, `194,9`), nó được nhận diện trực tiếp là dấu phẩy thập phân và gộp thành một `TextNode("0,39", kind="num")`.
  - Khi có dấu phẩy đứng sau số nhưng tiếp theo không phải chữ số (ví dụ `0,0278,   1 ≤ x < 2`), dấu phẩy cuối câu không khớp `lookahead` và được tách độc lập thành `SymbolNode(",")` (dấu câu ngăn cách mệnh đề).
  - Khi có khoảng trắng sau dấu phẩy (ví dụ `(0, 1)` hoặc `1, 2, 3`), dấu phẩy là dấu liệt kê TeX tiêu chuẩn.
  - Lưu ý: Đối với `_parse_single_token` (khi đọc đối số đơn của `^` hoặc `_` không có ngoặc nhọn như `x_1,2`), vẫn chỉ đọc đúng 1 chữ số theo chuẩn TeX; còn trong `x_{0,5}` (có ngoặc nhọn gọi `parse_row` -> `_parse_atom`), `_NUM_RE` nhận diện đúng `0,5` là một số thập phân.

### Rationale
- Người dùng Việt Nam viết tài liệu, đề thi, bài tập toán luôn viết số thập phân tự nhiên như `$0,39$` mà không cần phải gõ `$0{,}39$`.
- Lookahead `,(?=[0-9])` giữ nguyên 100% tính đúng đắn cho các trường hợp tọa độ `(0, 1)`, dãy số `x_1, x_2`, và dấu phẩy ngắt vế trong hệ phương trình.

---

## 4. Compact Fraction Vertical Clearance, Overhang and Row Alignment

### Context & Problem
Trong `MathLayoutEngine._m_Fraction`:
1. **Khoảng cách tử số / mẫu số với thanh gạch ngang bị thổi phồng**:
   - `_m_TextNode` và `_m_MathRow` luôn gán `descent = 0.2 * xh * eff` mặc định cho mọi số và chữ cái không có nét sổ dưới.
   - Khi đo tử số `num_y = -math_axis - gap - num_item.size.descent` với `gap = 3.0 * eff`, tổng khoảng cách từ nét đáy của chữ số tử đến gạch phân số lên tới `~5.0 * eff` (`> 0.62 * xh`).
   - Mẫu số `den_y = -math_axis + gap + den_item.size.ascent` cũng bị đẩy xuống quá xa (`~3.6 * eff`).
2. **Gạch phân số vươn ra hai đầu quá dài**:
   - `pad = 8.0 if node.bar else 2.0` (`8.0 * eff ~ 1.0 * xh`). Thanh gạch ngang thò ra mỗi bên `0.5 * xh`, dài hơn hẳn độ rộng cần thiết.
3. **Phân số trong hệ `cases` làm giãn toạc dòng kẻ**:
   - Tỷ lệ co phân số `child_scale = scale * 0.85` kết hợp khoảng đệm thừa làm mỗi phân số cao `~23.0` pt, cộng thêm `row_gap = 0.5 * xh` trong `_m_Matrix`, khiến mỗi dòng phân số nuốt trọn 1.5 đến 2 dòng kẻ vở, không thể căn khớp với dòng kẻ ngang.

### Decision
1. **Khoảng cách quang học thực tế dựa trên biên nét (`ink bounds`)**:
   - Trong `_m_TextNode`, với `kind == "num"` hoặc chuỗi chỉ gồm chữ số và dấu chấm/phẩy:
     - `descent = max(0.0, max(ys) * eff)` (chỉ dương nếu thực sự có nét thò dưới baseline, không áp đặt `0.2 * xh` giả tạo).
     - `ascent = max(0.85 * self.xh * eff, -min(ys) * eff)`.
   - Trong `_m_Fraction`:
     - Tính khoảng hở theo tỷ lệ `xh` (thay vì hằng số tuyệt đối): `gap = (0.20 if node.bar else 0.12) * self.xh * eff`.
     - Đo biên dọc thực tế của các nét vẽ (`ink_top`, `ink_bot`) trong `num_item` và `den_item` (nếu có nét vẽ; ngược lại dùng `-size.ascent` và `size.descent`).
     - Đặt `num_y = -math_axis - gap - num_ink_bot` và `den_y = -math_axis + gap - den_ink_top`. Nhờ đó, khoảng hở quang học thực sự từ điểm thấp nhất của tử số đến gạch ngang và từ gạch ngang đến điểm cao nhất của mẫu số luôn bằng đúng `0.20 * xh * eff` (nằm chính giữa dải `[0.15 * xh, 0.25 * xh]` cho mọi `xh` và mọi loại tử/mẫu).
2. **Gọn gàng độ vươn gạch phân số (bar overhang)**:
   - Tính `overhang = (0.18 if node.bar else 0.08) * self.xh * eff` cho mỗi bên (`pad = 2.0 * overhang`).
   - Độ vươn mỗi bên luôn bằng `0.18 * xh * eff` (nằm gọn trong `[0.15 * xh, 0.25 * xh]`), đồng thời giữ nguyên nhánh `node.bar=False` cho tổ hợp `\binom{n}{k}`.
3. **Cân đối tỷ lệ trong môi trường bảng / hệ `cases`**:
   - Bổ sung bộ đếm `self._matrix_level` trong `MathLayoutEngine._m_Matrix`.
   - Đối với phân số đơn thông thường: `child_scale = scale * 0.80`; khi phân số lồng nhau hoặc nằm trong ma trận/cases (`self._frac_level > 0 or self._matrix_level > 0`), dùng `child_scale = scale * 0.78`, đồng thời giảm `row_gap` của `cases` xuống `0.35 * xh` để các dòng phân số nằm gọn gàng trong nhịp dòng kẻ ngang (`line_h = 24.0` pt).

### Rationale
- Mang lại diện mạo phân số viết tay học trò thanh thoát, cân đối.
- Giúp các biểu thức nhánh như `F_M(x) = { ... }` căn hàng gọn gàng, tương xứng với các toán tử `≈`, `=` và điều kiện bên cạnh.
