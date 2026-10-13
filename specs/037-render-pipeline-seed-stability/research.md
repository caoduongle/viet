# Technical Research: Ổn định Dòng kết xuất và Tính tái lập Hạt giống

**Feature**: `037-render-pipeline-seed-stability`  
**Date**: 2026-10-13  
**Status**: Completed  

---

## Nghiên cứu 1: Cấu trúc dữ liệu RenderItem trong Pipeline kết xuất

### Vấn đề
Trong `chuviettay/layout/engine.py` và `chuviettay/layout/table_layout.py`, danh sách các mục kết xuất trong dòng (`cur_line`, `render_items`, `l_items`) sử dụng tuple n-phần tử rời rạc (`(start, st, w)` hoặc `(start, st, w, miss, tok_str)`). Tại dòng 451 của `engine.py`, mảng `render_items` được nén lại chỉ còn 3 phần tử `[(start, st, w) for start, st, w, _, _ in cur_line]`. Khi truyền vào hàm `_render_text_line()`, mã nguồn cố gắng đọc `item[4]` để lấy `tok_str`, nhưng vì mảng chỉ có 3 phần tử, biến `tok_str` và `first_tok` luôn bị đánh rơi về chuỗi rỗng `""`.

### Quyết định
- **Lựa chọn**: Định nghĩa cấu trúc dữ liệu `RenderItem` dưới dạng lớp tối ưu `dataclass(slots=True)` lưu trữ tường minh:
  ```python
  @dataclass(slots=True)
  class RenderItem:
      start: float
      strokes: list[Stroke]
      width: float
      missing: list[str] = field(default_factory=list)
      token: str = ""
      token_id: str = ""
      occurrence: int = 0
  ```
- **Hỗ trợ truy cập chỉ số kiểu tuple**: Cài đặt phương thức `__getitem__` trên `RenderItem` ánh xạ:
  - `item[0] -> start`
  - `item[1] -> strokes`
  - `item[2] -> width`
  - `item[3] -> missing`
  - `item[4] -> token`
  - `item[5] -> token_id`
  - `item[6] -> occurrence`
- **Lý do**:
  1. Bảo toàn 100% khả năng tương thích ngược với mọi mã nguồn cũ đang đọc `item[0]`, `item[1]`, `item[2]`, `item[4]`.
  2. Cung cấp thuộc tính rõ ràng (`item.token`, `item.token_id`, `item.occurrence`) cho các bước dẫn xuất RNG trong tương lai mà không sợ lệch chỉ số tuple.
  3. Sử dụng `slots=True` giúp tốc độ khởi tạo và truy cập thuộc tính nhanh tương đương tuple, mức chiếm dụng bộ nhớ tối thiểu.

### Các phương án khác đã xem xét
- **Tiếp tục dùng tuple 5 phần tử hoặc 7 phần tử**: Bị từ chối vì rất dễ bị lỗi "off-by-one" khi sửa code, thiếu tính tự tài liệu hóa, vi phạm nguyên tắc Clean Code của Hiến chương.
- **Dùng dict**: Bị từ chối vì chiếm nhiều bộ nhớ và chậm hơn đáng kể so với `slots=True` khi render tài liệu hàng vạn nét.

---

## Nghiên cứu 2: Neo giữ Ngẫu nhiên Hình học Cục bộ (Decoupling from it_idx & base_y)

### Vấn đề
Trong `_render_text_line()` hiện tại:
1. `geom_rng = ScopedRNG(self.effective_seed, "tok", tok_str, "geom", it_idx)`: Khóa neo dựa vào `it_idx` (chỉ số phần tử trong dòng). Khi người dùng chèn thêm từ vào đầu đoạn, các từ phía sau bị dịch chỉ số trong dòng (ví dụ từ vị trí 2 sang vị trí 3), hoặc bị rớt dòng sang dòng mới (vị trí 0), làm `geom_rng` thay đổi hoàn toàn, làm đổi độ nghiêng, độ dập dềnh và độ dày nét.
2. `line_rng = ScopedRNG(self.effective_seed, "line", first_tok, round(base_y, 1))`: Khóa neo sóng dòng dựa vào `first_tok` và tọa độ dòng `base_y`. Khi chèn từ, từ đầu dòng thay đổi và tọa độ Y của dòng có thể dịch chuyển, dẫn đến độ trôi `xo` và độ lượn sóng của cả dòng bị biến đổi.

### Quyết định
- **Neo ngẫu nhiên hình học cấp token**:
  - Mỗi token trong tài liệu nhận một cặp định danh bền vững `(token_str, occurrence_k)` duy trì tăng đơn điệu theo thứ tự xuất hiện của token trong văn bản.
  - Khóa ngẫu nhiên hình học nét: `ScopedRNG(self.effective_seed, "tok", item.token, item.occurrence, "geom")`.
  - Khóa này hoàn toàn độc lập với việc token nằm ở dòng nào, cột nào hay vị trí thứ mấy trong dòng.
- **Xử lý trôi dạt sóng dòng cấp macro**:
  - Khi `stable_variants=True`: Để bảo đảm tính bất biến 100% khi ngắt dòng thay đổi, độ lệch trôi dạt dòng vĩ mô (`slope`, `amp`, `xo_offset` phụ thuộc dòng) được cố định hoặc triệt tiêu (`slope = 0.0, amp = 0.0, xo = start_x`). Toàn bộ hiệu ứng tự nhiên (run tay, nghiêng, dày nét, lệch vi mô $y$) do chính `geom_rng` của từng token đảm nhiệm độc lập.
  - Khi `stable_variants=False`: Giữ nguyên 100% hành vi cũ (phụ thuộc `self.rnd` tuần tự) để bảo vệ golden master byte-exact.

### Lý do
Khi người dùng sửa văn bản ở chế độ ổn định, kỳ vọng cao nhất là nét chữ của các từ cũ không nhấp nháy, không đổi dạng. Việc neo hình học hoàn toàn vào `(token, occurrence)` giải quyết triệt để bài toán bất biến khi chèn tiền tố (Prepend Invariance).

---

## Nghiên cứu 3: Ngữ cảnh Hạt giống Độc lập cho Chữ số và Công thức Toán học

### Vấn đề
1. Trong `math_layout.py`, hàm `_m_TextNode` gọi `self.writer.number(txt)` cho nút số. `Writer.number(txt)` không tự gán `self._current_tok` và `self._current_k` (khác với `Writer.token()`). Khi `_resolve_dgap()` được gọi để tính khoảng cách giữa các chữ số, nó lấy `_current_tok` còn sót lại từ từ văn bản trước công thức.
2. `MathLayoutEngine._scratch()` tạo một `Writer` độc lập với bộ đếm rỗng `_token_counts = {}`. Trong khi đó, `MathLayoutEngine` chính chia sẻ `self.wr` của toàn tài liệu (đã tích lũy `_token_counts` từ các đoạn văn trước). Do đó, lượt đo thử và lượt vẽ thật có thể chọn các biến thể khác nhau nếu có từ/ký hiệu trùng lặp.

### Quyết định
- **Trong `chuviettay/model/writer.py`**:
  - Cập nhật `Writer.number(s, k=None)`: Khi `self.stable_variants=True`, tự động thiết lập ngữ cảnh:
    ```python
    if self.stable_variants:
        if k is None:
            k_idx = self._token_counts.get(s, 0)
            self._token_counts[s] = k_idx + 1
        else:
            k_idx = k
        self._current_tok = s
        self._current_k = k_idx
        self._char_idx = 0
        self.last = {}
    ```
- **Trong `chuviettay/layout/math_layout.py`**:
  - Mỗi công thức toán học được gán một ngữ cảnh riêng biệt (ví dụ `formula_id` hoặc chuỗi LaTeX / AST).
  - Khi `stable_variants=True`, `MathLayoutEngine` sử dụng một `Writer` có hạt giống dẫn xuất riêng từ công thức: `ScopedRNG(self.effective_seed, "math", formula_key).seed`.
  - Bộ đo đạc kích thước `_scratch()` và bộ layout chính sử dụng cùng một cấu hình Writer dẫn xuất từ cùng công thức, bảo đảm `_token_counts` cục bộ trong công thức bắt đầu giống hệt nhau, loại bỏ hoàn toàn sự desync giữa đo thử và vẽ thật.

---

## Nghiên cứu 4: Kiểm thử Tích hợp Cả Hai Engine (Dual-Engine)

### Vấn đề
Kiểm thử `test_seed_lifecycle.py` hiện mới chỉ kiểm tra `DocumentLayoutEngine`. `FidelityLayoutEngine` chưa có kiểm thử tự động chứng minh tái lập byte-exact qua `seed_used`. Ngoài ra, `test_stable_variants.py` mới chỉ test cô lập `Writer` ở `jitter=0.0`.

### Quyết định
- Bổ sung test kiểm chứng byte-exact cho `FidelityLayoutEngine`:
  - Đọc tệp `.docx` mẫu, kết xuất lần 1 với `seed=None`.
  - Thu thập `res1.seed_used`, chạy lần 2 với `seed=res1.seed_used`.
  - So sánh SHA-256 tệp `.xopp` giải nén, xác nhận trùng khớp 100%.
- Bổ sung test kiểm chứng Prepend Invariance cho toàn bộ pipeline (`write_text` / `write_document`):
  - Chạy với `stable_variants=True` và `jitter=1.0` (độ run tay bật thực tế).
  - Văn bản 1: `"Hôm nay trời rất đẹp."`
  - Văn bản 2: `"Buổi sáng hôm nay trời rất đẹp."`
  - Tách tọa độ nét tương đối của các token `"hôm"`, `"nay"`, `"trời"`, `"rất"`, `"đẹp"`, khẳng định 100% nét vẽ của chúng không đổi.

---

## Nghiên cứu 5: Đồng bộ Giao diện Desktop GUI và Web Client

### Quyết định
1. **Desktop GUI (`chuviettay/view/write_tab.py`)**:
   - Thêm biến `self.v_stable_variants = tk.BooleanVar(value=False)`.
   - Thêm checkbox *"Kiểu chữ ổn định"* vào hàng cấu hình nâng cao.
   - Truyền `stable_variants=self.v_stable_variants.get()` vào `WriteOptions`.
   - Trong `chuviettay/formatting.py:write_report_lines()`, bổ sung dòng:
     `if getattr(result, "seed_used", None) is not None and getattr(result, "opts_had_no_seed", False):` -> `"Seed đã dùng: %d (chạy lại với --seed %d để có đúng kết quả này)"`. Nhờ đó, cả Desktop GUI và CLI đều tự động hiển thị dòng này mà không cần trùng lặp mã nguồn.
2. **Web Client (`webapp/js/write.js`)**:
   - Bổ sung thẻ `<div id="opt-seed-error" class="text-danger small" style="display:none;"></div>` ngay dưới ô `#opt-seed`.
   - Khi `parseSeed()` trả về `valid: false` và có `message`: hiển thị dòng thông báo lỗi tại `#opt-seed-error`, thêm viền đỏ `is-invalid` cho `#opt-seed`.
   - Khi `valid: true`: ẩn `#opt-seed-error` và xóa viền đỏ.

---

## Nghiên cứu 6: Phân định Phạm vi Cam kết Bit-Exact của ScopedRNG

### Quyết định
- **Tài liệu hóa rõ ràng trong `chuviettay/model/rng.py`**:
  - **Phạm vi 1 (Trong cùng môi trường)**: Đảm bảo 100% bit-exact khi chạy trên cùng runtime CPython và cùng hệ điều hành.
  - **Phạm vi 2 (Xuyên môi trường / WebAssembly)**: Thuật toán Box-Muller sử dụng `math.log`, `math.sqrt`, `math.cos`. Do các hàm này phụ thuộc vào thư viện `libm` của C trên từng hệ điều hành / trình biên dịch WebAssembly, sai số số thực $10^{-16}$ có thể xuất hiện ở các bit cuối của mantissa. Do đó, giữa CPython và Pyodide WASM, cam kết hiện tại là **tương đương về mặt phân phối thống kê**, không cam kết byte-exact tuyệt đối cho đến khi có cơ chế fixed-point hoặc kiểm chuẩn đa nền tảng trong CI.
  - Việc lựa chọn biến thể mẫu (`choice`) và sinh số nguyên (`randint`) dựa trên phép chia nguyên thủy của `random()`, hoàn toàn không phụ thuộc vào `libm`, nên vẫn giữ tính tất định cao trên mọi nền tảng.
