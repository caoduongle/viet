# Research & Technical Decisions: Feature 061

**Feature**: `061-test-depth-and-benchmark-hardening`
**Date**: 2026-10-28

---

## 1. Nghiên cứu & Quyết định Kỹ thuật

### Quyết định 1: Cấu trúc xác minh chi tiết cho ca đóng khối toán trích dẫn lồng nhau
- **Vấn đề**:
  Trong `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close()`, ca kiểm thử lồng nhau:
  ```markdown
  > $$
  > x = 1
  >> $$
  > x = 2
  > $$
  ```
  Trước đây chỉ được kiểm tra bằng `assert isolated_nested.endswith("$$")`. Khẳng định này quá lỏng và không chứng minh được dòng `>> $$` có bị đóng nhầm hay không.
- **Giải pháp lựa chọn**:
  1. **Tại bước `_isolate_display_math_blocks()`**:
     - Kiểm tra toàn bộ chuỗi đầu ra `isolated_nested`. Khối toán mở tại dòng 1 (`> $$`) và chỉ đóng tại dòng 5 (`> $$`). Dòng 3 (`>> $$`) và dòng 4 (`> x = 2`) phải nằm liên tục bên trong khối mà không có dòng phân cách nào chen ngang.
     - Xác nhận `isolated_nested.strip() == "> $$\n> x = 1\n>> $$\n> x = 2\n> $$"`.
  2. **Tại bước `import_text()`**:
     - Gọi `importer.import_text(text_nested_close)`.
     - Lọc danh sách `MathBlock`: `math_blocks = [b for b in res_nested.document.blocks if isinstance(b, MathBlock)]`.
     - Khẳng định `len(math_blocks) == 1`: Chỉ có đúng 1 khối `MathBlock` duy nhất được tạo ra (không bị tách thành 2 khối rời do đóng sớm).
     - Khẳng định `math_blocks[0].latex` chứa đầy đủ cả `x = 1` và `x = 2`.
- **Lý do**:
  Đảm bảo cả hai giai đoạn (chuẩn hóa/cô lập dòng và phân tích cú pháp AST token) đều hoạt động đúng quy tắc độ sâu trích dẫn và không bị hồi quy.

---

### Quyết định 2: Bổ sung bất biến đầu ra công thức toán trong bài đo hiệu năng đối kháng
- **Vấn đề**:
  `test_adversarial_complexity_multi_length_backticks_and_long_lines()` đo tỷ lệ thời gian $T(4N)/T(N) \le 6.0$ và đã kiểm tra số lượng các đoạn văn bản bảo toàn (`x*80`, `y*60`, `code_span`), nhưng cần kiểm chứng trực tiếp sự hiện diện của các công thức toán học sau khi đi qua chuỗi tiền xử lý (`_normalize_math_delimiters` $\rightarrow$ `_isolate_display_math_blocks` $\rightarrow$ `_sanitize_html`).
- **Giải pháp lựa chọn**:
  - Trong dữ liệu đối kháng sinh ra:
    - Mẫu `mod == 1`: `> {bts}unclosed_depth1_{i} và $$display_formula$$` chứa công thức `$$display_formula$$`.
    - Mẫu `mod == 3`: `Dòng cấp gốc {bts}unclosed_{i} kèm $$x=1$$ và 'chuỗi dài {'y'*60}'` chứa công thức `$$x=1$$`.
  - Khẳng định các bất biến đầu ra:
    - `out_n.count("$$display_formula$$") == 250`, `out_2n.count("$$display_formula$$") == 500`, `out_4n.count("$$display_formula$$") == 1000`.
    - `out_n.count("$$x=1$$") == 250`, `out_2n.count("$$x=1$$") == 500`, `out_4n.count("$$x=1$$") == 1000`.
- **Lý do**:
  Khóa chặt cả 2 khía cạnh: (1) tính nguyên vẹn của văn bản mã nguồn và (2) tính toàn vẹn của các công thức toán sau tiền xử lý khi mật độ backtick thay đổi liên tục.

---

### Quyết định 3: Bảo toàn trạng thái ban đầu của Garbage Collector
- **Vấn đề**:
  Trong hai bài benchmark đối kháng (`test_adversarial_complexity_unclosed_backticks_and_blockquotes` và `test_adversarial_complexity_multi_length_backticks_and_long_lines`), khối `finally` luôn gọi `gc.enable()`. Nếu môi trường kiểm thử bên ngoài đã chủ động tắt GC từ trước, việc này sẽ làm bật lại GC ngoài ý muốn, vi phạm nguyên tắc cô lập trạng thái kiểm thử.
- **Giải pháp lựa chọn**:
  ```python
  was_gc_enabled = gc.isenabled()
  gc.collect()
  try:
      gc.disable()
      # Thực thi các vòng lặp đo lường
  finally:
      if was_gc_enabled:
          gc.enable()
      else:
          gc.disable()
  ```
- **Lý do**:
  Bảo toàn tuyệt đối trạng thái GC của môi trường gọi kiểm thử, tuân thủ nguyên tắc độc lập và vệ sinh của bộ kiểm thử tự động.
