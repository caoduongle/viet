# Research & Technical Decisions: Feature 060

**Feature**: `060-blockquote-math-state-hardening`
**Date**: 2026-10-28

---

## 1. Theo dõi độ sâu trích dẫn (`math_bq_depth`) cho trạng thái `in_display_math` (P2)

### Context
Trong `MarkdownImporter._isolate_display_math_blocks()` (`chuviettay/importer/markdown_importer.py`), khi gặp dòng mở khối toán nhiều dòng (ví dụ `> $$`), máy trạng thái bật cờ `in_display_math = True` và lưu `math_indent`. Tuy nhiên:
- Nhánh `if in_display_math:` hiện tại chỉ kiểm tra xem dòng có kết thúc bằng `$$` (hoặc `$$` kèm dấu câu) hay không, mà không lưu độ sâu trích dẫn lúc mở khối toán (`math_bq_depth`) và không kiểm tra xem dòng hiện tại còn nằm trong khối trích dẫn đó hay không.
- Nhánh `B. Dòng trống` (`if stripped == "":`) và `C. Bắt đầu khối mã lập trình` nằm phía trước nhánh `D. Đang ở trong khối toán display nhiều dòng (DISPLAY_MATH)`.
- Khi đầu vào có khối toán mở trong trích dẫn nhưng không đóng trước khi thoát trích dẫn:
  ```markdown
  > $$
  > x = 1
  Ngoài trích dẫn:$$y=2$$
  Đoạn văn tiếp theo
  ```
  Dòng `Ngoài trích dẫn:$$y=2$$` có `bq_depth = 0 < 1`, nhưng vì `in_display_math` vẫn bằng `True`, dòng này rơi vào nhánh `D`, chỉ được `out_lines.append(line)` rồi kiểm tra `endswith("$$")` và `continue` — bỏ qua hoàn toàn bước `G` (`colon_match` tách `Ngoài trích dẫn:` và `$$y=2$$`). Hệ quả là `$$y=2$$` không được tách thành `MathBlock`.

### Decision
1. **Bổ sung biến trạng thái `math_bq_depth: int = 0`** trong `_isolate_display_math_blocks()`, được gán bằng `bq_pref.count(">")` khi chuyển sang `in_display_math = True`.
2. **Đặt nhánh kiểm tra `if in_display_math:` ngay sau nhánh `if in_fence:` (trước nhánh dòng trống và các nhánh khối khác)** với quy tắc chuyển trạng thái đồng nhất với `in_fence`:
   - **Thoát khối chứa (`bq_depth < math_bq_depth`)**:
     - Khối trích dẫn chứa khối toán đã kết thúc trước dòng hiện tại.
     - Đặt `in_display_math = False`, `math_bq_depth = 0`, `math_indent = ""`, `can_start_indented = True`.
     - Nếu dòng trước đó trong `out_lines` không trống và dòng hiện tại không phải dòng trống (`stripped != ""`), chèn dòng trống phân cách (`""` nếu `bq_depth == 0`, hoặc tiền tố trích dẫn hiện tại) để đảm bảo `markdown-it` không gộp dòng mới thành *lazy continuation* của khối trích dẫn vừa kết thúc.
     - **Không `continue`**: để dòng hiện tại đi tiếp xuống các nhánh bên dưới (`B`, `C`, `E`, `F`, `G`, `H`) nhằm được xử lý đầy đủ theo ngữ cảnh mới.
   - **Đóng khối toán hợp lệ (`bq_depth == math_bq_depth` và dòng kết thúc bằng `$$` kèm dấu câu tùy chọn)**:
     - Ghi dòng hiện tại vào `out_lines`, đặt `in_display_math = False`, `math_bq_depth = 0`, `can_start_indented = True`.
     - Nếu dòng kế tiếp (`idx + 1 < n`) có nội dung (`lines[idx + 1].strip() != ""`), chèn dòng phân cách phù hợp (`""` nếu dòng kế tiếp có `next_bq_depth < bq_depth`, ngược lại `math_indent.rstrip()`).
     - `continue`.
   - **Dòng nội dung bên trong khối toán (`bq_depth >= math_bq_depth` và chưa đóng)**:
     - Ghi dòng hiện tại vào `out_lines` và `continue`.

### Rationale
- Hoàn toàn đối xứng với cơ chế xử lý `in_fence` và `fence_bq_depth` đã được kiểm chứng ở Feature 059.
- Xử lý triệt để cả trường hợp thoát từ `>` ra cấp gốc (`0`), thoát từ `>>` về `>`, và gặp dòng trống không có `>` sau khối toán trích dẫn dở dang.
- Ngăn chặn hiệu ứng phụ *lazy continuation* của CommonMark khi một blockquote dở dang đứng ngay trước một đoạn văn cấp gốc.

### Alternatives Considered
- **Chỉ kiểm tra `bq_depth < math_bq_depth` bên trong nhánh `D` ở vị trí cũ (sau nhánh dòng trống và mở fence)**: Nếu dòng kế tiếp là dòng trống `""` (không có `>`), nhánh `B` sẽ chạy trước và `continue` mà không tắt `in_display_math`, khiến dòng sau dòng trống vẫn bị coi là đang trong `in_display_math`. Đặt kiểm tra `in_display_math` trước nhánh `B` giải quyết luôn cả trường hợp dòng trống ngắt blockquote.

---

## 2. Gia cố kiểm thử bất biến bảo toàn nội dung (Content Preservation Invariants)

### Context
1. Trong `test_code_fence_in_blockquote_auto_closes_on_dedent()`, chú thích ghi *"Cả x=2 và y=3 (được normalize từ \[y=3\]) đều được tách thành MathBlock"*, nhưng lệnh `assert` mới chỉ kiểm tra `any(b.latex == "x=2" for b in math_blocks)`.
2. Trong `test_adversarial_complexity_multi_length_backticks_and_long_lines()`, bài kiểm thử mới chỉ khẳng định `len(out_n) > 0` và tỷ lệ thời gian `ratio <= 6.0`, chưa kiểm tra nội dung đầu ra có bảo toàn các khối mã và chuyển đổi đúng các công thức hay không.

### Decision
1. Cập nhật `test_code_fence_in_blockquote_auto_closes_on_dedent()` để kiểm tra chính xác `[b.latex for b in math_blocks] == ["x=2", "y=3"]`.
2. Bổ sung bài kiểm thử chuyên biệt `test_display_math_in_blockquote_exits_on_dedent()` kiểm tra cả `_isolate_display_math_blocks()` và `import_text()` cho:
   - Khối toán mở ở `>` thoát ra cấp gốc (`Ngoài trích dẫn:$$y=2$$`).
   - Khối toán mở ở `>>` lùi về `>` (`> Trong trích dẫn cấp 1:$$y=2$$`).
   - Khối toán mở ở `>` bị ngắt bởi dòng trống không có `>`.
3. Bổ sung bài kiểm thử `test_pipeline_code_preservation_and_outside_math_invariants()` xác nhận chính xác từng ký tự của code fence và indented code block (cấp gốc và trong blockquote) không thay đổi sau toàn bộ pipeline, đồng thời mọi công thức ngoài code được tách thành `MathBlock` đúng thứ tự.
4. Nâng cấp `test_adversarial_complexity_multi_length_backticks_and_long_lines()` để kiểm tra bất biến nội dung trực tiếp trên `out_n`, `out_2n`, `out_4n` (bảo toàn nguyên vẹn các khối code fence/indented code mẫu và khớp chính xác số lượng công thức được chuẩn hóa/cô lập theo hệ số $N, 2N, 4N$).

### Rationale
- Đảm bảo bài kiểm thử hiệu năng vừa chứng minh độ phức tạp thời gian tuyến tính $O(n)$, vừa chứng minh tính đúng đắn của đầu ra.
