# Research: Loại Bỏ Từ Nguyên Khối, Chuyển Sang Thuần Ghép Ký Tự

**Feature**: `026-remove-whole-words`
**Date**: 2026-10-06

## 1. Nghiên cứu Kiến trúc Bộ máy Kết xuất (Writer & Fidelity Engine)

### Bối cảnh Hiện tại
Trong `chuviettay/model/writer.py`, phương thức `word()` và `token()` vẫn còn logic fallback:
1. Thử `assemble_word(c)` trước.
2. Nếu không ghép được, duyệt qua `self.b.words` để lấy mẫu từ nguyên khối (`inst = self.pick(self.b.words[c], c)`).
3. Nếu không có mẫu từ, gọi `self.substitute(c)` để thay thế dấu thanh dựa trên `self.b.tl` (vốn được xây dựng từ `self.b.words`).
4. Trong `token(tok)`, kiểm tra `tok in b.words` và trong vòng lặp lead/trail kiểm tra `ch in b.words`.
5. Trong `get_letter_sample(char)`, kiểm tra `len(char) == 1 and char in b.words`.
6. Trong `fidelity/engine.py`, khi sinh file lưới ô thiếu mẫu (`missing_grid`), hệ thống lấy `miss_keys = sorted(self.wr.missing)` và tra mẫu từ `self.bank.words`.

### Quyết định Thiết kế
- **Quyết định**:
  1. Loại bỏ hoàn toàn mọi truy vấn tới `b.words` trong `Writer` (`word()`, `token()`, `get_letter_sample()`).
  2. Xóa bỏ phương thức `substitute()` trong `Writer` và chỉ mục `self.tl` trong `Bank`.
  3. Cơ chế `assemble_word()` trở thành phương thức DUY NHẤT để kết xuất bất kỳ từ nào có chứa chữ cái. Nếu thiếu mẫu chữ cái hoặc dấu thanh, `word()` trả về `None` và ghi nhận danh sách các ký tự còn thiếu vào `self.missing`.
  4. Trong `fidelity/engine.py`, lưới ô thiếu mẫu được sinh từ danh sách ký tự đơn còn thiếu (`missing_letters_ranked`), xuất ra file lưới ô chữ cái chuẩn `hw3`.
- **Lý do**:
  - Đảm bảo tính nhất quán của chữ viết: mọi từ đều được tạo nên từ nét chữ cái tương đồng về phong cách, độ dày và khoảng cách quang học.
  - Ngăn ngừa hành vi không đồng nhất khi một số từ hiển thị dạng nguyên khối (không thể chỉnh kerning) còn các từ khác hiển thị dạng ghép nét.
- **Phương án thay thế đã bác bỏ**:
  - *Giữ fallback sang `b.words` nhưng thêm cảnh báo*: Bị bác bỏ vì mục tiêu người dùng là bỏ hoàn toàn từ nguyên khối, việc giữ fallback khiến người dùng không biết từ nào đang được ghép và từ nào dùng mẫu cũ.

---

## 2. Nghiên cứu Quản lý Kho mẫu (Bank & Backward Compatibility)

### Bối cảnh Hiện tại
Cấu trúc file `.json.gz` chứa trường `"words": {...}` lưu trữ các từ nguyên khối được dạy từ các phiên bản trước. `Bank.rebuild()` duyệt qua `self.words` để tính chỉ mục `self.tl` và gặt dấu thanh (`self._harvest`). Ngoài ra `Bank.has_word(w)` kiểm tra `w in self.words` hoặc `strip_tone(w) in self.tl`.

### Quyết định Thiết kế
- **Quyết định**:
  1. **Bảo toàn dữ liệu lịch sử**: Giữ trường `words` trong schema và trong thuộc tính `self.words` của `Bank` để khi mở file cũ và lưu lại không làm mất mát dữ liệu của người dùng.
  2. **Vô hiệu hóa trong vận hành**:
     - `Bank.rebuild()` không còn duyệt qua `self.words`. Chỉ mục `marks` được nạp từ `self.d["marks"]` (dấu thanh độc lập được dạy hoặc nạp từ lưới).
     - `Bank.has_word(w)` được cập nhật: Kiểm tra khả năng ghép của `w` bằng cách kiểm tra tất cả các ký tự thành phần trong `letters`, `digits`, `punct`, `symbols` và dấu thanh trong `marks`. Không tra `self.words`.
     - `Bank.add_sample()`: Mặc định phân loại token thành `letters`, `digits`, `punct`, `symbols` hoặc `marks`. Không còn ghi vào `self.words`.
     - Thuộc tính `bank_size`: Trả về tổng số ký tự đơn lẻ (`len(letters) + len(digits) + len(punct) + len(symbols) + len(marks)`).
- **Lý do**:
  - Tuân thủ nguyên tắc an toàn dữ liệu (Data Integrity): không tự ý xóa trường dữ liệu cũ của người dùng.
  - Tách bạch hoàn toàn luồng nghiệp vụ mới khỏi cấu trúc dữ liệu cũ.
- **Phương án thay thế đã bác bỏ**:
  - *Tự động xóa trường `words` khi mở kho*: Bị bác bỏ vì vi phạm hiến pháp bảo toàn dữ liệu và có thể gây mất mát vĩnh viễn nếu người dùng mở nhầm file kho cũ.

---

## 3. Nghiên cứu Hiệu chỉnh Cỡ tay (Calibration)

### Bối cảnh Hiện tại
`pick_calib_word()` trong `xopp.py` và `ctl.pick_calibration_word()` trong `app_controller.py` tìm một từ trong `bank.words` có từ 5 mẫu trở lên và độ lệch chuẩn nhỏ nhất để làm mốc hiệu chỉnh. Khi không còn dùng `bank.words`, hàm này trả về `None`, khiến chức năng hiệu chỉnh cỡ tay bị tê liệt.

### Quyết định Thiết kế
- **Quyết định**:
  1. Chuẩn hóa sang hàm `pick_calibration_char(bank)`:
     - Duyệt danh mục `bank.letters`.
     - Ưu tiên các chữ cái x-height ổn định: `["o", "a", "e", "n", "u", "c", "m"]`.
     - Lọc các chữ cái có ít nhất 3 mẫu, tính hệ số biến thiên $\text{CV} = \sigma / \mu$, chọn chữ cái có điểm số cao nhất ($\text{score} = \text{count} - 6 \times \text{CV}$).
     - Nếu không có chữ cái nào trong danh sách ưu tiên đủ 3 mẫu, chọn bất kỳ chữ cái nào có nhiều mẫu nhất trong `bank.letters`.
     - Nếu `bank.letters` hoàn toàn chưa có mẫu nào, trả về `None`.
  2. Thay thế hoàn toàn các hàm `pick_calibration_word` bằng `pick_calibration_char` trên:
     - `xopp.py`
     - `app_controller.py`
     - `bridge.py`
     - `py-worker.js`
     - `teach_tab.py` (Desktop GUI)
     - `teach.js` (Web Client)
- **Lý do**:
  - Chữ cái đơn lẻ (đặc biệt là các chữ cái tròn hoặc thân thấp như `o`, `n`) phản ánh trung thực nhất chiều cao x-height và cỡ tay tự nhiên của người viết mà không bị ảnh hưởng bởi độ dài từ hay kerning.

---

## 4. Nghiên cứu Luồng Dạy Chữ & Hàng đợi (Teach Queue & Canvas)

### Bối cảnh Hiện tại
Trong `teach_tab.py` và `teach.js`:
- Người dùng có thể gõ cụm từ (ví dụ `"cà phê"`) và nhấn Thêm, hệ thống sẽ đưa cả cụm `"cà phê"` vào hàng đợi. Khi bấm Lưu, hệ thống gọi `ctl.teach_word()` và lưu cả cụm vào `bank.words`.
- Vẫn còn nút "Từ thông dụng" gọi `missing_seed_words` (700 từ tĩnh trong `seed_words.py`).

### Quyết định Thiết kế
- **Quyết định**:
  1. **Bóc tách tự động**: Khi người dùng nhập văn bản vào ô "Thêm ký tự vào hàng đợi":
     - Chuẩn hóa Unicode NFC (`unicodedata.normalize('NFC', text)`).
     - Bóc tách chuỗi thành các ký tự đơn lẻ phân biệt (bỏ khoảng trắng và ký tự điều khiển).
     - Chỉ thêm các ký tự còn thiếu mẫu (hoặc chưa có trong hàng đợi) vào hàng đợi.
  2. **Thao tác lưu nét**:
     - Bỏ hoàn toàn `teach_word()`.
     - Luôn gọi `teach_char()` (hoặc `teach_letter()` / `add_tone_sample()` tùy thuộc loại ký tự).
     - Khi hiệu chỉnh cỡ tay, lưu nét vào chữ cái mốc trong `bank.letters` và cập nhật `session_scale`.
  3. **Loại bỏ Seed Words 700 từ**:
     - Loại bỏ module tĩnh `seed_words.py` và lệnh CLI `seed`.
     - Thay thế hoàn toàn bằng `CharCatalog` với 4 bộ ký tự chuẩn hóa (`co_ban`, `toan_hy_lap`, `mo_rong`, `day_du`).

---

## 5. Nghiên cứu Giao diện Người dùng (Web Client & Desktop GUI)

### Bối cảnh Hiện tại
- `webapp/index.html` có nút lọc `<button data-cat="words">Từ vựng</button>`.
- `webapp/js/bank.js` tải danh sách từ qua `list_words` và hiển thị tab từ vựng.
- `chuviettay/view/bank_tab.py` hiển thị `_all_words` từ `ctl.list_words()`.

### Quyết định Thiết kế
- **Quyết định**:
  1. Xóa bỏ nút lọc "Từ vựng" trên `webapp/index.html`.
  2. Chuyển danh mục mặc định của tab Kho mẫu trên Web Client sang "Chữ cái (`letters`)".
  3. Cập nhật `chuviettay/view/bank_tab.py`: Thay đổi bảng danh sách hiển thị các ký tự (`letters`, `digits`, `punct`, `symbols`, `marks`) thay vì `_all_words`.
  4. Chuẩn hóa chuỗi hiển thị thống kê:
     - Web Client: `"Kho mẫu hiện có {n_letters} chữ cái, {n_samples} mẫu nét."`
     - Desktop GUI & CLI stats: Thống kê số chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh.
