# Phase 0 Research: Cải tiến Seed Stability, Phân trang Bảng và Kế hoạch Dạy chữ

**Feature**: `036-seed-stability-and-teaching-plan`  
**Date**: 2026-10-13  
**Status**: Hoàn thành nghiên cứu kỹ thuật

---

## 1. Cơ chế sinh số ngẫu nhiên cục bộ (`chuviettay/model/rng.py`)

### Ngữ cảnh & Vấn đề
- Hiện tại, `Writer` và các engine bố cục sử dụng một cá thể `random.Random(seed)` toàn cục tuần tự. Khi người dùng soạn thảo văn bản, việc chèn thêm một từ hay ký tự ở đầu hoặc giữa tài liệu sẽ làm trượt toàn bộ chuỗi số ngẫu nhiên của các từ phía sau.
- Kết quả đo lường thực tế: Thêm tiền tố vào văn bản làm tỷ lệ nét giữ nguyên chỉ còn 13% - 22% ở chế độ mặc định, và ngay cả khi bật `stable_variants=True` với `jitter=0`, việc chèn từ "a" phía trước vẫn làm đổi hình thái của từ "nay".
- Kiểm thử cũ trong `tests/test_stable_variants.py` đọc `w.last.get("hôm")` trong khi khóa lưu trong `w.last` là `let:h`, `let:ô`, dẫn đến so sánh `None == None`.
- CPython không đảm bảo tính ổn định giữa các phiên bản (3.10 vs 3.12 vs 3.14) cho các hàm cấp cao của module `random` như `random.gauss()` (sử dụng thuật toán polar có biến cache trạng thái nội bộ). Chỉ có `random.Random.random()` được bảo đảm tính nhất quán trên nền tảng CPython và Pyodide/WASM.

### Quyết định kỹ thuật (Decision)
1. Xây dựng module thuần túy độc lập `chuviettay/model/rng.py`:
   - Hàm dẫn xuất hạt giống con: `derive_seed(master_seed: int, *keys: Any) -> int` sử dụng `hashlib.blake2b(digest_size=8)` trên chuỗi byte chính tắc phân tách bằng byte `\x00`.
   - Lớp `ScopedRNG(master_seed: int, *keys: Any)` bọc `random.Random(sub_seed)`.
   - **Chỉ phụ thuộc duy nhất vào `self._rnd.random()`**. Tự cài đặt các phương thức:
     - `random() -> float`: gọi trực tiếp `self._rnd.random()`.
     - `uniform(a: float, b: float) -> float`: tính theo công thức $a + (b - a) \times \text{random()}$.
     - `randrange(start: int, stop: int | None = None) -> int`: tính theo $\text{start} + \lfloor \text{random()} \times (\text{stop} - \text{start}) \rfloor$.
     - `choice(seq: Sequence[T]) -> T`: chọn theo `seq[self.randrange(len(seq))]`.
     - `gauss(mu: float = 0.0, sigma: float = 1.0) -> float`: cài đặt thuật toán **Box-Muller biến đổi trực tiếp** (stateless):
       $$u_1, u_2 \sim U(0, 1) \quad (u_1 > 10^{-15})$$
       $$z_0 = \sqrt{-2 \ln(u_1)} \cos(2 \pi u_2)$$
       $$\text{kết quả} = \mu + z_0 \times \sigma$$
2. **Hệ thống khóa neo ngữ cảnh (Contextual Anchor Keys)**:
   - **Biến thể & Nét của Token**: Neo theo `(master_seed, "tok", text, k, purpose, sub_idx)`, trong đó `text` là chuỗi ký tự chuẩn hóa NFC, `k` là số lần token đó đã xuất hiện trước đó trong tài liệu, `purpose` thuộc `{"variant", "jitter", "dgap", "scale", "rot", "dy", "wscale"}`.
   - **Khoảng cách từ (Word Gap)**: Neo theo `(master_seed, "wgap", prev_text, curr_text, k)`.
   - **Độ lượn của dòng chữ (Line Wave & Slope)**: Neo theo `(master_seed, "line", first_tok_text, line_idx)`.
   - **Viền ô bảng biểu (Table Border Jitter)**: Neo theo `(master_seed, "tbl_border", table_idx, slice_start_row, r, c)`.
   - **Công thức toán inline (Inline Math)**: Neo theo `(master_seed, "math", latex_str, k)`.
3. **Phạm vi chống lặp biến thể**:
   - Khi `stable_variants=True`, việc chống lặp biến thể (`self.last`) chỉ áp dụng trong phạm vi nội bộ của từng token đa ký tự (ví dụ: chữ 'n' xuất hiện 2 lần trong từ "ngang"), tuyệt đối không để biến thể của token trước làm lệch trạng thái chọn của token sau.

### Giải pháp thay thế đã xem xét (Alternatives Considered)
- *Neo theo tọa độ không gian tuyệt đối $(x, y)$*: Bị loại bỏ vì khi chèn một từ làm dòng chữ dạt sang phải hoặc xuống dòng dưới, toàn bộ tọa độ thay đổi sẽ phá vỡ tính ổn định của các từ còn lại.
- *Dùng bộ sinh LCG hoặc Xoroshiro viết bằng pure Python*: Bị loại bỏ vì tốc độ chậm hơn đáng kể so với `_random.Random.random()` viết bằng C trong CPython.

---

## 2. Kiểm chuẩn vòng đời Hạt giống ngẫu nhiên (WP1) & Nghi vấn `Random(-5)` vs `Random(5)`

### Ngữ cảnh & Vấn đề
- Đầu vào `seed` chưa được kiểm tra miền giá trị, chấp nhận cả số âm, số thực hoặc bool.
- Khi người dùng không truyền seed (`seed=None`), hệ thống không lưu lại hạt giống đã sinh, khiến người dùng không thể tái tạo lại trang viết tay ưng ý.
- Trên giao diện Web, biểu thức `parseInt(seedInput.value) || 42` làm mất khả năng nhập seed `0` (vì `0` là falsy trong JS và bị ép thành 42).
- Thử nghiệm CPython: `random.Random(-5)` và `random.Random(5)`.

### Kết quả kiểm chứng thực nghiệm
- Chạy thử nghiệm trên Python:
  ```python
  r1 = random.Random(5)
  r2 = random.Random(-5)
  r1.random() == r2.random()  # => True!
  ```
- **Lý do**: Thuật toán Mersenne Twister trong CPython xử lý hạt giống số nguyên bằng hàm băm hoặc lấy trị tuyệt đối `abs()`, khiến mọi số nguyên âm `-n` sinh ra luồng số ngẫu nhiên trùng khớp hoàn toàn 100% với số dương `n`.
- Do đó, việc chấp nhận số âm gây hiểu lầm nghiêm trọng cho người dùng (tưởng rằng `-5` là một thực nghiệm khác biệt với `5`).

### Quyết định kỹ thuật (Decision)
1. **Kiểm chuẩn `WriteOptions.validate()`**:
   - Chỉ chấp nhận `seed is None` hoặc `isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed < 2**32`.
   - Nếu vi phạm, ném `ValueError` với thông báo tiếng Việt: `"Hạt giống (seed) phải là số nguyên không âm trong khoảng [0, 4294967295] hoặc None."`
2. **Quy tắc xác định seed hiệu dụng (`seed_used`)**:
   - Nếu người dùng truyền `seed` hợp lệ: giữ nguyên.
   - Nếu `seed is None` và `stable_variants=False`: sinh bằng `secrets.randbits(32)`.
   - Nếu `seed is None` và `stable_variants=True`: ấn định giá trị `0` cố định.
   - Ghi nhận `seed_used` vào đối tượng `WriteResult.seed_used`.
3. **Parity trên Web & CLI**:
   - CLI in hướng dẫn tái tạo khi seed tự sinh: `"Seed đã dùng: N (chạy lại với --seed N để có đúng kết quả này)"`.
   - Web `write.js`: Tách hàm thuần `parseSeed(inputVal, currentSeed)` có test riêng bằng `node --test`. Chấp nhận `0`, khi nhập sai/rỗng thì giữ nguyên `currentSeed` và thông báo nhẹ.
   - `bridge.py`: Thu thập và trả về `ignored_options: list[str]` thay vì âm thầm bỏ qua.

---

## 3. An toàn hình học phân trang bảng và Bounding Box (P1/P2)

### Ngữ cảnh & Vấn đề
- Khi một ô gộp hàng (`rowspan > 1`) bắt đầu từ trang trước và tiếp tục tràn dòng ở trang hiện tại, mã nguồn cũ trong `chuviettay/layout/engine.py` chỉ tìm `source_cell_id` từ hàng `curr_row_idx` trở đi (`range(curr_row_idx, len(full_table_data.cells))`). Với ô gộp bắt đầu từ hàng 0 hoặc các hàng trước, vòng lặp này thất bại.
- Nhánh dự phòng cũ tìm ô theo cột (`orig_c.col == laid_cell.col` trong hàng `curr_row_idx + laid_cell.row`), dẫn đến nguy cơ ghi đè dữ liệu lên một ô hoàn toàn khác có cùng chỉ số cột.
- `TableLayoutEngine` hiện gán `cell.source_cell_id = r * 1000 + c` trực tiếp vào đối tượng `TableCell` trong Document IR, làm vi phạm nguyên tắc bất biến của mô hình IR.
- Trong `_render_text_line`, câu lệnh `pt_y = min(pt_y, max_y)` kẹp cơ học từng điểm toạ độ, làm dồn các đường cong phía dưới chân chữ (như đuôi 'g', 'y', 'p') thành một đường thẳng ngang bẹt dí (degenerate collinear segments).

### Quyết định kỹ thuật (Decision)
1. **Tìm kiếm toàn bảng (Full Table Search)**:
   - Khi chuyển tiếp các dòng chưa vẽ của một ô, duyệt tìm `source_cell_id` trên toàn bộ các hàng từ hàng `0` (`range(0, len(full_table_data.cells))`).
   - Xóa bỏ hoàn toàn nhánh fallback tìm kiếm theo chỉ số cột. Nếu không tìm thấy (trường hợp bất khả kháng), ghi cảnh báo bố cục mà tuyệt đối không ghi đè vào ô khác.
2. **Định danh ô cô lập tầng Layout**:
   - Tạo trường `source_cell_id` độc lập trong đối tượng `LaidOutCell`.
   - Bộ đếm monotonic trong phiên bố cục bảng cấp phát ID duy nhất cho mỗi ô hiển thị và ô tiếp nối, giữ nguyên tính bất biến của `TableCell` trong Document IR.
3. **Bảo toàn hình thái nét vẽ & Bounding Box Safety**:
   - Trước khi vẽ dòng chữ sát mép trang, hệ thống tính toán chiều cao khả dụng. Nếu dòng chữ vượt mép trang, ưu tiên chuyển tiếp sang trang mới.
   - Đối với phần tử bắt buộc phải vẽ trên trang hiện tại (ví dụ ô đơn lẻ không thể chia nhỏ), áp dụng hệ số co tỷ lệ đồng dạng `downscale` cho cả phương X và Y, bảo đảm tỷ lệ khung hình không đổi.
   - Sau khi áp dụng biến đổi, kiểm tra bounding box thực tế của nét chữ. Chỉ áp dụng giới hạn mềm và phát cảnh báo rõ ràng nếu có điểm chạm biên, không kẹp cơ học từng điểm làm biến dạng hình học.

---

## 4. Kế hoạch Dạy chữ 38 mục cốt lõi và Gỡ nghẽn Hàng đợi SEED

### Ngữ cảnh & Vấn đề
- Kho mẫu cơ bản chứa 104 mục trong `CO_BAN_CHARS` (33 chữ cái thường, 33 chữ cái hoa, 10 chữ số, 23 dấu câu, 5 dấu thanh rời). Trong đó, 5 dấu thanh rời nằm ở cuối cùng (vị trí 100-104).
- Người dùng chỉ dạy 33 chữ cái thường đầu tiên thì chỉ ghép được 185/700 từ khóa trong tập `SEED`. Nhưng nếu có thêm 5 dấu thanh rời (tổng cộng 38 mục), hệ thống ghép được **700/700 từ khóa** (100% độ phủ).
- Hàm `get_minimal_essentials(60)` hiện trả về 10 chữ số + 11 dấu câu + 60 từ đa ký tự. Khi người dùng dạy từ "tôi" thông qua `teach_char("tôi")`, hệ thống lưu vào `bank.words["tôi"]`.
- Tuy nhiên, hàm `Bank.can("tôi")` theo chuẩn char-first chỉ kiểm tra `letters`, `digits`, `punct`, `symbols`, `marks` mà bỏ qua `bank.words`. Do đó `Bank.can("tôi")` trả về `False`, khiến từ "tôi" bị kẹt vĩnh viễn trong hàng đợi `missing_minimal_essentials()`.

### Quyết định kỹ thuật (Decision)
1. **Đồng bộ `Bank.can()` với `bank.words`**:
   - Cập nhật `Bank.can(w)`: Nếu `w_clean in getattr(self, "words", {}) and bool(self.words.get(w_clean))`, trả về `True`.
   - Khi đó, các từ nguyên khối đã được dạy trong `bank.words` sẽ được `Bank.can()` công nhận ngay lập tức, gỡ bỏ khỏi hàng đợi học.
2. **Ưu tiên 38 mục cốt lõi**:
   - Định nghĩa hằng số `CORE_ESSENTIALS_38` trong `chuviettay/model/seed_words.py` gồm:
     - 33 chữ cái tiếng Việt viết thường (`VIETNAMESE_LOWERCASE`)
     - 5 dấu thanh rời chuẩn hw3 (`TONE_MARKS`)
   - Cung cấp hàm `get_core_essentials_38() -> list[str]`.
   - Đồng bộ thứ tự gợi ý dạy chữ ưu tiên 38 mục này trước khi gợi ý các từ đa ký tự.

---

## 5. Xác minh Nghi vấn Kỹ thuật (WP4)

1. **`MathLayoutEngine._scratch()`**:
   - Hiện tại khởi tạo `Writer` mà không truyền `letter_gap`, `pen_clearance_factor`, `stable_variants`, `seed`.
   - Quyết định: Truyền đầy đủ các tham số này từ `self.writer` sang đối tượng scratch writer để kết quả đo kích thước thử nghiệm hoàn toàn đồng nhất với kết quả vẽ thật.
2. **`Writer.measure_text_width` vs `Writer.word`**:
   - `Writer.word()` luôn ưu tiên ghép từ các chữ cái mẫu (`assemble_word`).
   - `measure_text_width()` trước đây kiểm tra `bank.words` trước. Nếu kho mẫu có từ cũ trong `bank.words` có độ rộng khác với từ được ghép từ chữ cái, kết quả đo sẽ lệch.
   - Quyết định: Trong `measure_text_width`, nếu kho có đủ chữ cái để ghép từ, ưu tiên đo độ rộng từ chữ cái ghép để khớp 100% với `Writer.word()`.
3. **Cờ `assemble_letters`**:
   - Đã kiểm tra mã nguồn: `Writer.word()` hiện luôn gọi `self.assemble_word(c)` mà không kiểm tra cờ `self.assemble_letters`.
   - Ghi nhận báo cáo kỹ thuật rõ ràng trong tài liệu và CHANGELOG mà không tự ý sửa đổi ngoài phạm vi.
