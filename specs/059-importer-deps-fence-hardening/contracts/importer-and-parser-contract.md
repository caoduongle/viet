# Contract: Phụ thuộc Tùy chọn & Nhận diện Khối Mã trong Bộ nhập Markdown

**Feature**: `059-importer-deps-fence-hardening`
**Date**: 2026-10-28

---

## 1. Hợp đồng Phụ thuộc Tùy chọn (`chuviettay.importer`)

1. **Không import thư viện tùy chọn ở cấp module**:
   - Việc thực thi `import chuviettay.importer`, `from chuviettay.importer.base import get_importer_for_path`, `from chuviettay.importer.txt_importer import TxtImporter`, hoặc `from chuviettay.importer.markdown_importer import MarkdownImporter` trong môi trường không có `markdown_it` và `mdit_py_plugins` **BẮT BUỘC** thành công mà không phát sinh `ImportError` / `ModuleNotFoundError`.
2. **Bảo toàn luồng TXT trong môi trường tối giản**:
   - `get_importer_for_path("sample.txt")` và `get_importer_for_path("sample.anything", format_name="txt")` trả về thực thể `TxtImporter` và thực hiện `import_text()` / `import_file()` thành công khi không có `markdown-it-py`.
3. **Báo lỗi có hướng dẫn khi gọi tính năng Markdown**:
   - Khi thiếu `markdown_it` hoặc `mdit_py_plugins`, gọi `MarkdownImporter()`, `get_importer_for_path("sample.md")`, hoặc `_escaped_split_table_row()` **BẮT BUỘC** ném `OptionalDependencyError` (kế thừa từ `RuntimeError`) với thuộc tính `package_name="markdown_it"` và `extra="docs"`.

---

## 2. Hợp đồng Đồng bộ Nhận diện Code Fence & Blockquote (`MarkdownImporter`)

1. **Quy tắc mở Code Fence (`_parse_fence_open_line`)**:
   - Áp dụng đồng nhất tại cả `_split_code_segments()` và `_isolate_display_math_blocks()`.
   - Chuẩn hóa CRLF: Loại bỏ `\r` cuối dòng (`line.rstrip("\r")`) trước khi phân tích cú pháp.
   - Sau tiền tố trích dẫn `bq_prefix` (có `bq_depth` dấu `>`), dòng mở phải có từ `0` đến `3` khoảng trắng, theo sau bởi dãy ký tự `fc` $\in$ `` { "`", "~" } `` có độ dài `flen >= 3`.
   - Nếu `fc == "`"` và phần còn lại của dòng (`info_str`) chứa ký tự `` "`" ``, dòng đó **KHÔNG** mở code fence nhiều dòng.
2. **Quy tắc đóng Code Fence (`_is_fence_close_line` & kiểm tra độ sâu trích dẫn)**:
   - Một khối mã rào chắn mở tại độ sâu trích dẫn `open_bq_depth` chỉ được đóng bởi dòng đóng rào chắn khi dòng đó có độ sâu trích dẫn `line_bq_depth == open_bq_depth` và phần sau tiền tố trích dẫn khớp `^[ ]{0,3}(fc{flen,})[ \t]*$`.
   - Nếu `line_bq_depth > open_bq_depth` (ví dụ mở ở `>` nhưng dòng bên trong có `>> ``` `), dòng đó **KHÔNG** đóng khối mã.
   - Nếu `line_bq_depth < open_bq_depth` (thoát khỏi khối trích dẫn chứa rào chắn, kể cả dòng trống hoàn toàn không có `>`), khối mã tự động đóng ngay trước dòng đó theo chuẩn CommonMark container block, và dòng đó được xử lý theo ngữ cảnh trích dẫn mới.
3. **Quy tắc Khối mã thụt lề (`Indented Code Block`) ở cấp gốc và trong Blockquote**:
   - Sau tiền tố trích dẫn `bq_prefix` tại độ sâu `bq_depth`, nếu dòng trước đó trong cùng ngữ cảnh là dòng trống (hoặc đầu tài liệu / bắt đầu khối trích dẫn mới) và phần còn lại sau `bq_prefix` bắt đầu bằng $\ge 4$ khoảng trắng hoặc `\t` (không rỗng), dòng đó mở khối mã thụt lề tại `bq_depth`.
   - Mọi nội dung bên trong (bao gồm `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, thẻ giống HTML) được giữ nguyên từng ký tự qua cả `_normalize_math_delimiters()`, `_isolate_display_math_blocks()` và `_sanitize_html()`.
