# Research: Chuẩn hóa Hình học, Kích thước và Vị trí Quang học cho Dấu câu

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Date**: 2026-10-20  
**Spec Reference**: [specs/050-punctuation-geometry-normalization/spec.md](spec.md)

---

## 1. Nghiên cứu & Phân tích Nguyên nhân Gốc rễ

### 1.1 Hiện trạng Thuộc tính Dấu câu Viết tay Trong Thực tế
Khi kiểm tra kho mẫu viết tay thực tế (ví dụ: `local data/kho_mau_v4.json.gz`), các mẫu dấu câu do người dùng nhập vào trên bảng vẽ hoặc lưới tập viết thường gặp các dị tật hình học nghiêm trọng:
1. **Dấu ngoặc đơn `(`, `)`**:
   - `xh ≈ 7.94pt`.
   - Mẫu `(`: `min_y = -5.79`, `max_y = -0.11`, chiều cao `h = 5.68pt` (`0.715 * xh`).
   - Mẫu `)`: `min_y = -5.16`, `max_y = +0.52`, chiều cao `h = 5.68pt` (`0.715 * xh`).
   - Trong khi đó, chữ số `1` (và các chữ số khác) có chiều cao chuẩn `1.20 * xh ≈ 9.53pt` (`min_y = -9.53`, `max_y = 0.0`).
   - **Hậu quả**: Dấu ngoặc lùn hơn chữ số rất nhiều. Khi dấu `)` đứng sau chữ số `1` (như trong `P(X >= 1)`, `k!(e^\lambda - 1)`, `(random_state=2026)`), đỉnh dấu ngoặc `-5.16` thấp hơn đỉnh chữ số `1` (`-9.53`), chân dấu ngoặc `+0.52` ngang đường cơ sở. Nét cong của `)` cắm thẳng vào giữa sống lưng nét sổ của `1`, tạo thành hình một vòng khép kín dính liền vào thân số `1` giống như chữ `D`.
2. **Dấu phẩy `,` và dấu chấm `.`**:
   - Dấu phẩy `,`: `min_y = -1.10`, `max_y = +0.79`, hoặc trong nhiều mẫu bị vẽ lơ lửng trên cao (`max_y < 0.0`), không hề chạm đường cơ sở.
   - Dấu chấm `.`: `min_y = -0.74`, `max_y = -0.02`, lơ lửng ở giữa dòng.
   - **Hậu quả**: Khi viết số thập phân hoặc danh sách `0,`, `1,`, `1, 2, 3, ...`, dấu phẩy lơ lửng như một dấu nháy apostrophe hoặc một nét gạch bay giữa dòng.
3. **Dấu hai chấm `:` và chấm phẩy `;`**:
   - Dấu `:`: chấm trên ở `[-3.72, -3.27]`, chấm dưới ở `[-0.74, 0.07]`. Hai chấm không đều cỡ, chấm dưới tràn qua đường cơ sở.
   - **Hậu quả**: Trong các cụm từ như `và xác suất lý thuyết:`, hai chấm bị xiêu vẹo, chấm dưới tụt xuống dưới đường cơ sở trông như dấu phẩy.
4. **Dấu ba chấm `...` bị báo thiếu mẫu sai (`miss = ['...']`)**:
   - Trong `Writer.token()`, khi `tok == "..."`, mã nguồn phân tích `lead = "", core = "", trail = "..."`.
   - Vòng lặp `for ch in trail:` lấy mẫu `.` thành công 3 lần và ghép nét vào `strokes`.
   - Tuy nhiên, khối mã kiểm tra ở cuối `Writer.token()` (dòng 955-961) nhận thấy `trail == tok` và `tok not in b.punct` nên ghi đè `miss = [tok]`, dẫn đến việc báo `"..."` là thiếu mẫu dù nét vẽ đã được tạo thành công!

---

## 2. Các Quyết định Kỹ thuật (Technical Decisions)

### Quyết định 1: Phân loại Ngữ nghĩa và Bảng Tham số Chuẩn hóa Hình học Dấu câu

- **Lựa chọn**: Định nghĩa hệ thống hồ sơ hình học dấu câu (`PUNCT_METRIC_PROFILES`) phân loại mọi ký tự dấu câu thành 8 nhóm hình học dựa trên chiều cao `xh` và đường cơ sở `baseline = 0.0`:
  1. `parens` (`() [] {}`):
     - `target_h = 1.45 * xh` (dải hợp lệ `[1.35 * xh, 1.55 * xh]`).
     - `target_min_y = -1.25 * xh`, `target_max_y = +0.20 * xh`.
     - Tỷ lệ co giãn bề rộng: `scale_x = min(scale_y, 1.25)`.
  2. `comma` (`,`):
     - `target_h = 0.38 * xh` (dải hợp lệ `[0.20 * xh, 0.50 * xh]`).
     - `target_min_y = -0.14 * xh`, `target_max_y = +0.24 * xh`.
  3. `dot` (`.`):
     - `target_h = 0.14 * xh` (ngưỡng tối đa `0.22 * xh`).
     - `target_max_y = 0.0` (chạm đường cơ sở), `target_min_y = -0.14 * xh`.
  4. `colon` (`:`):
     - Trục dọc căn thẳng, dải dọc `[-0.75 * xh, -0.05 * xh]`.
  5. `semicolon` (`;`):
     - Chấm trên tại `-0.75 * xh`, đuôi phẩy dưới tại `+0.24 * xh`, bề rộng `<= 0.32 * xh`.
  6. `excl_quest` (`!`, `?`):
     - `target_h = 1.18 * xh` (dải hợp lệ `[1.10 * xh, 1.25 * xh]`).
     - `target_max_y = 0.0`, `target_min_y = -1.18 * xh`.
  7. `quotes` (`'`, `"`, `“`, `”`, `‘`, `’`):
     - Neo ở vùng đỉnh chữ: `target_min_y = -1.20 * xh`, `target_max_y = -0.85 * xh`.
  8. `hyphen_dash` (`-`, `–`, `—`):
     - Căn giữa vùng chữ thường: tâm `y = -0.45 * xh`.

- **Cơ chế Bảo toàn Golden Master (Invariance Guard)**:
  - Trong kho chuẩn kiểm thử `tests/conftest.py` (`tiny_bank_dict()`), dấu `.` có `s = [[0, 0, 0.5, 0.5]]` (`y` từ `0.0` đến `0.5`, `h = 0.5 = 0.071 * xh`), dấu `,` có `s = [[0, 0, 0.5, 1.5]]` (`y` từ `0.0` đến `1.5`, `h = 1.5 = 0.214 * xh`). Cả hai đều đã bám đúng đường cơ sở `0.0` và nằm trong dải kích thước hợp lệ.
  - Bộ chuẩn hóa kiểm tra điều kiện dung sai: nếu mẫu đã thỏa mãn vị trí và kích thước hợp lệ (như trong `tiny_bank`), thuật toán sẽ **giữ nguyên 100% tọa độ y**, không thực hiện co giãn hay dịch chuyển. Nhờ đó, 9/9 ca kiểm thử Golden Master SHA-256 được bảo toàn tuyệt đối.

- **Các phương án thay thế bị loại bỏ**:
  - *Phương án thay thế A*: Thay toàn bộ dấu câu viết tay bằng ký hiệu vector định hình sẵn.
    - *Lý do loại bỏ*: Mất đi nét chữ viết tay tự nhiên của người dùng, vi phạm nguyên lý cốt lõi của ứng dụng.
  - *Phương án thay thế B*: Co giãn tất cả dấu câu theo cùng một tỷ lệ duy nhất.
    - *Lý do loại bỏ*: Dấu ngoặc cần vươn cao hơn chữ số (`1.45 * xh`), trong khi dấu chấm chỉ được phép cao `0.14 * xh`; mỗi loại dấu câu có sinh học hình học hoàn toàn khác nhau.

---

### Quyết định 2: Tách biệt Quang học Tuyệt đối giữa Chữ số 1 và Dấu ngoặc Đóng / Dấu phẩy

- **Lựa chọn**:
  - Trong `chuviettay/layout/math_layout.py`:
    - Cập nhật quy tắc khoảng hở giữa phần tử kết thúc bằng chữ số `1` (hoặc nét sổ thẳng đứng bên phải) và dấu ngoặc đóng `)`: nâng sàn khoảng hở quang học `min_clearance` từ `max(0.12 * xh, 0.85 * pen_w)` lên `max(0.18 * self.xh * eff, 1.0 * pen_w)`.
    - Trong `_m_Delimited`: đối với cụm ngoặc co giãn hoặc ngoặc thường, khoảng đệm `pad` giữa thân `body` và dấu đóng `right` được tính tối thiểu `max(1.2 * eff, 0.18 * self.xh * eff)` nếu phần tử cuối của `body` là chữ số `1`.
  - Trong `chuviettay/model/writer.py`:
    - Trong `Writer.token()`, khi vẽ dấu câu `trail` đứng sau phần thân `core` (đặc biệt khi `core.endswith("1")` hoặc là chữ số), sàn khoảng cách `clearance_gap` giữa nét mực cực phải của `core` và điểm bắt đầu của dấu câu đạt tối thiểu `max(0.18 * xh, 1.0 * pen_w)`.

- **Các phương án thay thế bị loại bỏ**:
  - *Chỉ tăng khoảng cách chữ mặc định (`gaps`)*: Không giải quyết được tận gốc vì các mẫu chữ viết tay có độ lệch mép (side-bearing) không đều; chỉ có sàn khoảng cách theo tọa độ nét mực thực tế (`ink_bounds`) mới đảm bảo không bao giờ dính nét trong mọi trường hợp.

---

### Quyết định 3: Sửa Lỗi Báo Thiếu Mẫu Chuỗi Dấu câu Liên tiếp (`...`)

- **Lựa chọn**:
  - Trong `chuviettay/model/writer.py` (cuối hàm `token()`):
    ```python
    if not core and not lead and trail == tok:
        # Nếu tất cả các ký tự trong trail đều đã được vẽ thành công (miss đang rỗng),
        # thì KHÔNG ĐƯỢC báo tok là thiếu mẫu!
        if miss:
            miss = [tok]
    ```
  - Khi người dùng viết `...`, cả 3 dấu chấm đều được kết xuất tuần tự từ `b.punct['.']` với khoảng hở quang học thích hợp (`0.14 * xh` đến `0.18 * xh`), `miss` vẫn rỗng và hệ thống không báo lỗi.

---

### Quyết định 4: Tự động Đồng bộ Gói Phân phối Ứng dụng Web (`webapp/dist`)

- **Lựa chọn**:
  - Tích hợp bước chạy `python scripts/build_web.py` vào quy trình hoàn tất tính năng.
  - Kiểm tra tính toàn vẹn của tệp `webapp/dist/pyodide/chuviettay.zip` và tệp service worker `webapp/dist/sw.js` bằng bài kiểm tra tự động `tests/test_build_web.py`.

---

## 3. Tổng kết Đánh giá Tương thích và Rủi ro

| Tiêu chí | Đánh giá | Giải pháp bảo đảm |
|----------|----------|-------------------|
| **Golden Master SHA-256** | Rủi ro cao nếu thay đổi tọa độ `tiny_bank` | Sử dụng dung sai bảo toàn: mẫu chuẩn đã nằm đúng baseline không bị dịch chuyển. |
| **Hiệu năng Bố cục** | Rủi ro thấp | Thuật toán chuẩn hóa O(P) với P là số điểm của dấu câu (< 30 điểm), thực hiện 1 lần duy nhất khi nạp mẫu hoặc đo kích thước. |
| **Độ ổn định Web Worker** | Rủi ro thấp | Các quy tắc thuần túy hình học không ảnh hưởng tới trạng thái giao tiếp Worker. |
