# Research & Technical Decisions: Feature 059

**Feature**: `059-importer-deps-fence-hardening`
**Date**: 2026-10-28

---

## 1. Bảo toàn tính tùy chọn của thư viện `markdown-it-py` (P1)

### Context
Trong `pyproject.toml`, gói lõi khai báo `dependencies = []`, còn `markdown-it-py` và `mdit-py-plugins` thuộc nhóm phụ thuộc tùy chọn `[project.optional-dependencies].docs`. Tuy nhiên:
- `chuviettay/importer/__init__.py` nạp `from chuviettay.importer.markdown_importer import MarkdownImporter` ngay khi gói `chuviettay.importer` được import.
- `chuviettay/importer/markdown_importer.py` (dòng 27) lại có câu lệnh `from markdown_it.rules_block.table import escapedSplit` ở cấp module.

Hệ quả là trong môi trường tối giản (chỉ cài gói lõi, không cài `.[docs]`), bất kỳ lệnh import nào chạm tới `chuviettay.importer` (bao gồm `from chuviettay.importer.base import get_importer_for_path` hoặc `from chuviettay.importer.txt_importer import TxtImporter`) đều thất bại ngay lập tức với `ModuleNotFoundError: No module named 'markdown_it'`, trước cả khi `require_dependency()` kịp ném `OptionalDependencyError` có hướng dẫn.

### Decision
1. **Xóa bỏ hoàn toàn import thư viện tùy chọn ở cấp module** trong `chuviettay/importer/markdown_importer.py` (cụ thể là dòng `from markdown_it.rules_block.table import escapedSplit`).
2. **Tạo hàm trợ giúp tĩnh `_escaped_split_table_row(line_str: str) -> list[str]`** trong `MarkdownImporter`:
   - Gọi `require_dependency("markdown_it", feature_desc="tệp Markdown (.md)")` trước khi thực hiện `from markdown_it.rules_block.table import escapedSplit`.
   - Gọi hàm này bên trong `_count_header_cols()` khi xử lý bảng Markdown.
3. Giữ nguyên danh sách xuất công khai (`__all__`) của `chuviettay/importer/__init__.py` để không phá vỡ khả năng tương thích ngược; vì `markdown_importer.py` không còn import thư viện tùy chọn ở cấp module, việc import `chuviettay.importer` trong môi trường tối giản sẽ hoàn toàn thành công, và chỉ khi khởi tạo `MarkdownImporter()` hoặc gọi hàm cần `markdown_it` mới kích hoạt `require_dependency()`.

### Rationale
- Đúng với yêu cầu thiết kế của kiến trúc plugin/importer: nạp module nhẹ, chỉ kiểm tra và nạp thư viện tùy chọn tại thời điểm sử dụng tính năng Markdown.
- Đảm bảo cả trường hợp gọi `MarkdownImporter()` lẫn trường hợp gọi trực tiếp phương thức xử lý bảng đều đi qua `require_dependency()` và ném `OptionalDependencyError` nhất quán.

### Alternatives Considered
- **Lazy import `MarkdownImporter` bằng `__getattr__` trong `chuviettay/importer/__init__.py`**: Chỉ giải quyết khi import từ `chuviettay.importer`, nhưng nếu người dùng import trực tiếp `from chuviettay.importer.markdown_importer import MarkdownImporter` để kiểm tra kiểu thì vẫn lỗi nếu còn import cấp module. Chuyển import `escapedSplit` vào hàm sau `require_dependency()` giải quyết tận gốc ở cả hai nơi.

---

## 2. Đồng bộ điều kiện mở/đóng Code Fence và ngữ cảnh Blockquote (P2)

### Context
Hiện tại có 2 điểm lệch chuẩn giữa `_split_code_segments()` và `_isolate_display_math_blocks()`:
1. **Ngữ cảnh trích dẫn (blockquote) của dòng đóng code fence**:
   - `_split_code_segments()` chỉ kiểm tra dòng đóng có khớp `_BQ_PREFIX_RE` hay không mà không đối chiếu độ sâu trích dẫn (`bq_depth`, tức số lượng dấu `>`) với dòng mở fence.
   - `_isolate_display_math_blocks()` dùng regex `^(([ ]{0,3}>[ ]?)*)[ ]{0,3}(`{3,}|~{3,})[ \t]*$` cho dòng đóng, chấp nhận mọi độ sâu trích dẫn (kể cả không có `>` hoặc nhiều `>` hơn dòng mở).
   - Hệ quả: Một fence mở ở `>` (`bq_depth = 1`) sẽ bị đóng giả bởi dòng `>> ``` ` (`bq_depth = 2`), khiến các dòng công thức phía sau (như `> $$x=1$$`) bị xử lý như văn bản thường. Ngược lại, nếu fence mở ở `>>` nhưng dòng kế tiếp tụt xuống `>` (thoát khỏi blockquote cấp 2), khối mã cần phải tự đóng theo quy tắc container block của CommonMark.
2. **Điều kiện mở code fence**:
   - `_split_code_segments()` kiểm tra quy tắc CommonMark 4.5: rào chắn mở bằng backtick (`` ` ``) không được chứa ký tự `` ` `` trong chuỗi thông tin (`info_line`) phía sau trên cùng dòng.
   - `_isolate_display_math_blocks()` dùng regex `^(([ ]{0,3}>[ ]?)*)[ ]{0,3}(`{3,}|~{3,})` mà không kiểm tra phần chuỗi thông tin phía sau, dẫn tới việc một dòng như ```` ```info`invalid ```` hoặc ```` ```a=1``` ```` được `_split_code_segments()` coi là văn bản/code span nhưng lại bị `_isolate_display_math_blocks()` coi là mở code fence nhiều dòng.

### Decision
Xây dựng bộ hàm trợ giúp dùng chung cấp lớp trong `MarkdownImporter` để cả `_split_code_segments()` và `_isolate_display_math_blocks()` dùng chung một nguồn chân lý (Single Source of Truth):
1. `_match_bq_prefix(text: str, pos: int = 0, end: int | None = None) -> tuple[int, int]`:
   - Khớp `_BQ_PREFIX_RE` tại đầu dòng `pos` (trong phạm vi `end`), trả về `(bq_depth, pos_after_bq)` với `bq_depth` là số dấu `>` trong tiền tố.
2. `_parse_fence_open(text: str, pos_after_bq: int, line_end: int) -> tuple[str, int] | None`:
   - Sau tiền tố blockquote (`pos_after_bq`), cho phép tối đa 0–3 khoảng trắng (`[ ]{0,3}`). Nếu có $\ge 4$ khoảng trắng hoặc tab thì trả về `None` (vì đó là indented code).
   - Kiểm tra dãy ký tự rào chắn liên tiếp `fc` $\in$ `{`"`, `"~"}` có độ dài `flen >= 3`.
   - Lấy phần chuỗi thông tin `info_str = text[idx_fence + flen : line_end]`.
   - Áp dụng quy tắc CommonMark: nếu `fc == "`"` và ``"`" in info_str`` thì trả về `None`.
   - Trả về `(fc, flen)`.
3. `_is_fence_close(text: str, pos_after_bq: int, line_end: int, fence_char: str, fence_len: int) -> bool`:
   - Chỉ được gọi khi `line_bq_depth == open_bq_depth`.
   - Sau tiền tố blockquote (`pos_after_bq`), cho phép 0–3 khoảng trắng, theo sau bởi ít nhất `fence_len` ký tự `fence_char` liên tiếp, và phần còn lại tới `line_end` chỉ gồm khoảng trắng hoặc tab (`[ \t]*`).
4. **Quy tắc đóng theo độ sâu trích dẫn (`open_bq_depth`)**:
   - Nếu `line_bq_depth < open_bq_depth`: khối trích dẫn chứa fence đã kết thúc trước dòng này $\rightarrow$ đóng khối mã ngay trước dòng hiện tại và xử lý lại dòng hiện tại ở ngữ cảnh mới.
   - Nếu `line_bq_depth > open_bq_depth`: các dấu `>` dư ra thuộc nội dung bên trong khối mã $\rightarrow$ tuyệt đối không phải dòng đóng fence, giữ nguyên trong khối mã.
   - Nếu `line_bq_depth == open_bq_depth`: kiểm tra `_is_fence_close(...)`; nếu khớp thì đóng khối mã tại hết dòng hiện tại.

### Rationale
- Loại bỏ hoàn toàn sự bất đồng giữa hai bước tiền xử lý.
- Xử lý chính xác mọi tổ hợp trích dẫn lồng nhau (`>`, `>>`, `> > `) dựa trên độ sâu ngữ nghĩa `bq_depth` thay vì chuỗi ký tự thô.

---

## 3. Bảo toàn Khối mã thụt lề (Indented Code Block) bên trong Blockquote (P2)

### Context
Yêu cầu kiểm thử đối kháng nêu rõ cần bảo toàn nội dung cho cả **"code block thụt lề trong blockquote"** (ví dụ `>     $$x=1$$` hoặc `>     prefix:$$x=1$$` đứng sau dòng trống `>`). Hiện tại:
- `_split_code_segments()` có điều kiện `if not bq_prefix and prev_line_blank:`, bỏ qua hoàn toàn khối mã thụt lề nằm trong blockquote.
- `_isolate_display_math_blocks()` kiểm tra `line.startswith("    ") or line.startswith("\t")` trên toàn dòng trước khi xét tiền tố blockquote, nên `>     prefix:$$x=1$$` bị bước tách dấu hai chấm (`colon_match`) xé thành nhiều dòng và làm vỡ khối trích dẫn.

### Decision
Mở rộng nhận diện khối mã thụt lề trong cả `_split_code_segments()` và `_isolate_display_math_blocks()` để hoạt động thống nhất ở mọi độ sâu trích dẫn `bq_depth >= 0`:
- Sau khi tách tiền tố blockquote có độ sâu `bq_depth` và vị trí `pos_after_bq`, phần nội dung sau tiền tố là `rest = line[pos_after_bq:]`.
- Một dòng được coi là dòng thụt lề mã tại độ sâu `bq_depth` nếu `rest.startswith("    ") or rest.startswith("\t")` và `rest.strip() != ""`.
- Trạng thái cho phép mở khối mã thụt lề (`prev_line_blank` / `can_start_indented`) được tính trên phần `rest` sau tiền tố blockquote (dòng trống trong blockquote như `>` có `rest.strip() == ""` nên cho phép dòng `>     code` ngay sau đó mở khối mã thụt lề; hoặc khi bắt đầu khối trích dẫn mới có `bq_depth > prev_bq_depth`).
- Khi đang ở trong khối mã thụt lề tại `indented_bq_depth`, khối mã tiếp tục chừng nào `line_bq_depth == indented_bq_depth` và `rest` thụt lề $\ge 4$ khoảng trắng/tab (hoặc dòng trống cùng cấp trích dẫn theo sau bởi dòng thụt lề cùng cấp trích dẫn).

### Rationale
- Cấp gốc (`bq_depth == 0`) là trường hợp riêng tự nhiên của quy tắc tổng quát (`bq_depth >= 0`), không làm phức tạp kiến trúc nhưng bảo vệ trọn vẹn nội dung mã thụt lề trong trích dẫn qua cả 3 bước `_normalize_math_delimiters()`, `_isolate_display_math_blocks()` và `_sanitize_html()`.
