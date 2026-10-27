# Contract: Siết Chặt Kiểm Thử Độ Sâu Khối Toán & Bất Biến Benchmark

**Feature**: `061-test-depth-and-benchmark-hardening`
**Date**: 2026-10-28

---

## 1. Hợp đồng Xử lý Dấu Đóng Giả ở Độ Sâu Lồng Nhau

1. **Tại `MarkdownImporter._isolate_display_math_blocks()`**:
   - Khi `in_display_math == True`:
     - Nếu `bq_depth > math_bq_depth` và dòng kết thúc bằng `$$` (ví dụ `>> $$` khi `math_bq_depth == 1`):
       - Đây là dấu đóng giả ở cấp khối chứa sâu hơn; máy trạng thái **BẮT BUỘC** giữ nguyên `in_display_math = True` và thoát chuỗi `$$` cuối dòng thành `\$\$` (để `dollarmath_plugin` của `markdown-it-py` không đóng sớm khối toán ở cấp ngoài).
2. **Tại `MarkdownImporter._parse_blocks()`**:
   - Khi chuyển đổi token `math_block` thành đối tượng `MathBlock`:
     - **BẮT BUỘC** hoàn nguyên các chuỗi `\$\$` đã được thoát trong bộ tiền xử lý về lại `$$` để bảo toàn nội dung toán học gốc.

---

## 2. Hợp đồng Kiểm thử Khối Toán Đóng Lồng Nhau

Trong `tests/test_markdown_math_block_isolation.py`, hàm `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close`:

1. **Khẳng định cấp chuỗi cô lập**:
   - `isolated_nested` **BẮT BUỘC** kết thúc bằng `$$`.
   - `"> x = 1"` và `"> x = 2"` **BẮT BUỘC** có mặt trong `isolated_nested`.
2. **Khẳng định cấp AST / Document IR**:
   - Chạy `res_nested = importer.import_text(text_nested_close)`.
   - `math_blocks = [b for b in res_nested.document.blocks if isinstance(b, MathBlock)]`.
   - `len(math_blocks)` **BẮT BUỘC** bằng `1`.
   - `math_blocks[0].latex` **BẮT BUỘC** chứa cả `"x = 1"` và `"x = 2"`.

---

## 3. Hợp đồng Bất biến Đầu Ra Benchmark Đối Kháng

Trong `tests/test_markdown_math_block_isolation.py`, hàm `test_adversarial_complexity_multi_length_backticks_and_long_lines`:

1. **Khẳng định công thức toán học**:
   - `out_n.count("$$display_formula$$")` **BẮT BUỘC** bằng `250`.
   - `out_2n.count("$$display_formula$$")` **BẮT BUỘC** bằng `500`.
   - `out_4n.count("$$display_formula$$")` **BẮT BUỘC** bằng `1000`.
   - `out_n.count("$$x=1$$")` **BẮT BUỘC** bằng `250`.
   - `out_2n.count("$$x=1$$")` **BẮT BUỘC** bằng `500`.
   - `out_4n.count("$$x=1$$")` **BẮT BUỘC** bằng `1000`.
2. **Khẳng định tính tuyến tính**:
   - Tỷ lệ thời gian $T(4N)/T(N) \le 6.0$ và $T(4N) < 2.0s$.

---

## 4. Hợp đồng Vệ sinh Trạng thái Garbage Collector

Trong `test_adversarial_complexity_unclosed_backticks_and_blockquotes` và `test_adversarial_complexity_multi_length_backticks_and_long_lines`:

1. `was_gc_enabled = gc.isenabled()` **BẮT BUỘC** được gọi trước khi `gc.disable()`.
2. Khối `finally` **BẮT BUỘC** khôi phục đúng trạng thái:
   ```python
   if was_gc_enabled:
       gc.enable()
   else:
       gc.disable()
   ```
3. Sau khi kết thúc hàm kiểm thử, trạng thái `gc.isenabled()` **BẮT BUỘC** trùng khớp hoàn toàn với trạng thái trước khi vào hàm.
