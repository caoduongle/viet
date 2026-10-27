# Contract: Trạng thái Khối Toán theo Độ Sâu Trích Dẫn & Bất Biến Bảo Toàn Đầu Ra

**Feature**: `060-blockquote-math-state-hardening`
**Date**: 2026-10-28

---

## 1. Hợp đồng Trạng thái Khối Toán trong `_isolate_display_math_blocks()`

1. **Ghi nhận độ sâu trích dẫn khi mở khối toán nhiều dòng**:
   - Khi dòng bắt đầu bằng `$$` (sau tiền tố trích dẫn `bq_pref` có độ sâu `k = bq_pref.count(">")` và khoảng trắng thụt lề `< 4`) mà không đóng ngay trên cùng dòng, máy trạng thái **BẮT BUỘC** đặt `in_display_math = True` và `math_bq_depth = k`.
2. **Hủy trạng thái khối toán khi thoát khỏi khối trích dẫn chứa nó**:
   - Khi `in_display_math == True` và dòng hiện tại có độ sâu trích dẫn `bq_depth < math_bq_depth` (bao gồm cả dòng ở cấp gốc `bq_depth == 0`, dòng trích dẫn nông hơn, hoặc dòng trống không đủ dấu `>`):
     - Máy trạng thái **BẮT BUỘC** kết thúc `in_display_math` ngay trước dòng hiện tại (`in_display_math = False`, `math_bq_depth = 0`).
     - Dòng hiện tại **BẮT BUỘC** được đánh giá lại đầy đủ qua các bước tiếp theo (dòng trống, code fence, indented code block, bảng GFM, tách nhãn hai chấm `colon_match`, mở khối toán mới).
3. **Đóng khối toán hợp lệ trong cùng độ sâu trích dẫn**:
   - Chỉ đóng khối toán nhiều dòng khi dòng hiện tại có `bq_depth == math_bq_depth` và phần nội dung sau tiền tố trích dẫn kết thúc bằng `$$` (hoặc `$$` kèm dấu câu `[,.;:!?]`).

---

## 2. Hợp đồng Kiểm thử Bất biến Bảo toàn Nội dung (`tests/test_markdown_math_block_isolation.py`)

1. **Kiểm thử thoát trích dẫn cho cả Code Fence và Display Math**:
   - `test_code_fence_in_blockquote_auto_closes_on_dedent`: **BẮT BUỘC** xác nhận đầy đủ `[b.latex for b in math_blocks] == ["x=2", "y=3"]`.
   - `test_display_math_in_blockquote_exits_on_dedent`: **BẮT BUỘC** xác nhận cả `_isolate_display_math_blocks()` và `import_text()` tách đúng `MathBlock(latex="y=2")` khi dòng `Ngoài trích dẫn:$$y=2$$` (hoặc dòng trích dẫn cấp nông hơn) đi ngay sau khối toán trích dẫn chưa đóng `> $$\n> x = 1`.
2. **Kiểm thử bất biến bảo toàn khối mã & trích xuất công thức ngoài mã**:
   - Các đoạn code fence (backtick, tilde, trong blockquote) và indented code block (cấp gốc, trong blockquote) **BẮT BUỘC** được kiểm tra khớp chính xác từng ký tự sau khi chạy qua toàn bộ pipeline tiền xử lý (`_normalize_math_delimiters` $\rightarrow$ `_isolate_display_math_blocks` $\rightarrow$ `_sanitize_html`).
   - Trong `test_adversarial_complexity_multi_length_backticks_and_long_lines`, ngoài khẳng định $T(4N)/T(N) \le 6.0$, **BẮT BUỘC** kiểm tra các bất biến nội dung cụ thể trên `out_n`, `out_2n`, `out_4n`.
