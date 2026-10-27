# Research & Technical Decisions: Feature 058

**Feature**: `058-ci-e2e-render-markdown-hardening`  
**Date**: 2026-10-27

---

## R1. Tương thích E2E Playwright (`sw-update.spec.ts`) với Cơ chế Bảo vệ Build (`prepare_dist_dir`)

- **Decision**: Mở rộng hàm tiện ích `runBuildWeb(distDir: string, forceClean = false): void` trong `tests/e2e/sw-update.spec.ts` để nhận tham số tùy chọn `forceClean` (mặc định `false`). Lần gọi đầu tiên trên `tmpDist` mới tạo giữ nguyên `runBuildWeb(tmpDist)` (không truyền `--force-clean`); lần gọi thứ hai trên cùng `tmpDist` truyền `runBuildWeb(tmpDist, true)` để đính kèm cờ `--force-clean`. Tuyệt đối giữ nguyên logic bảo vệ trong `prepare_dist_dir()` của `scripts/build_web.py`.
- **Rationale**:
  - `prepare_dist_dir()` từ chối xóa thư mục nằm ngoài `DEFAULT_DIST_DIR` khi thư mục đã có dữ liệu và không có `--force-clean`. Đây là chốt chặn an toàn cốt lõi được thiết kế ở feature 056 nhằm bảo vệ dữ liệu người dùng.
  - Bài kiểm thử `sw-update.spec.ts` tạo thư mục tạm riêng `tmpDist` bằng `fs.mkdtempSync(...)` và chủ đích build hai lần liên tiếp vào cùng `tmpDist` để kiểm tra khả năng phát hiện bản cập nhật của Service Worker. Vì `tmpDist` thuộc quyền sở hữu hoàn toàn của bài test và lần build thứ hai ghi đè lên lần build đầu, việc truyền `--force-clean` ở lần gọi thứ hai vừa phản ánh đúng hợp đồng CLI vừa giữ nguyên vẹn cơ chế an toàn của `build_web.py`.
- **Alternatives considered**:
  - *Bỏ hoặc nới lỏng kiểm tra trong `prepare_dist_dir()` đối với `/tmp`*: Bị loại bỏ vì vi phạm nguyên tắc bảo vệ tường minh (FR-003) và làm suy yếu rào chắn an toàn của công cụ build.
  - *Tạo thư mục `tmpDist` thứ hai cho lần build thứ hai*: Bị loại bỏ vì server HTTP tĩnh (`scripts/serve.mjs`) đang chạy và phục vụ trực tiếp từ đường dẫn `tmpDist` ban đầu ở cổng `8101`.

---

## R2. Cấu hình Phiên bản Python trên Render (`render.yaml` vs `.python-version`)

- **Decision**: Loại bỏ khai báo biến môi trường `PYTHON_VERSION` khỏi `render.yaml`, giữ nguyên tệp `.python-version` (`3.13`) làm nguồn định nghĩa phiên bản Python duy nhất (Single Source of Truth) cho cả GitHub Actions CI và Render. Cập nhật bài kiểm thử trong `tests/test_version_metadata.py` để xác nhận `.python-version` là `3.13` và `render.yaml` không chứa khai báo `PYTHON_VERSION` dạng rút gọn `Major.Minor`.
- **Rationale**:
  - Theo tài liệu chính thức của Render (Setting Your Python Version), biến môi trường `PYTHON_VERSION` có độ ưu tiên cao hơn `.python-version` và yêu cầu định dạng phiên bản đầy đủ `Major.Minor.Patch` (ví dụ `3.13.5`), trong khi tệp `.python-version` hỗ trợ khai báo dòng phiên bản `Major.Minor` (`3.13`).
  - Việc bỏ `PYTHON_VERSION` khỏi `render.yaml` giúp Render tự động đọc `.python-version` (`3.13`), đồng thời loại bỏ hoàn toàn nguy cơ lệch cấu hình hoặc lỗi thiếu bản vá cụ thể trên cả GitHub Actions lẫn Render.
- **Alternatives considered**:
  - *Ghim `PYTHON_VERSION: 3.13.x` cụ thể trong `render.yaml`*: Bị loại bỏ vì gây phân mảnh nguồn cấu hình với `.python-version` và dễ lỗi thời khi nền tảng cập nhật image.

---

## R3. Bảo toàn Khối Mã Thụt Lề (Indented Code Block) trong `_isolate_display_math_blocks()`

- **Decision**: Bổ sung trạng thái nhận diện khối mã thụt lề (`in_indented_code` kết hợp theo dõi `can_start_indented_code` / `not in_paragraph` trên dòng đầu vào) vào máy trạng thái dòng trong `MarkdownImporter._isolate_display_math_blocks()` và đồng bộ với `_split_code_segments()`. Đồng thời, khi tách dòng `$$...$$` có thụt lề $\ge 4$ khoảng trắng đang là dòng tiếp nối đoạn văn (lazy continuation line ở cấp gốc, không nằm trong danh sách), chuẩn hóa khoảng trắng đầu dòng của khối `$$...$$` xuống tối đa 3 khoảng trắng (hoặc `""`) để dòng trống mới chèn phía trước không vô tình biến công thức đó thành khối mã thụt lề ở bước `_sanitize_html()` và `markdown-it`.
- **Rationale**:
  - Theo CommonMark 4.4, quy tắc cốt lõi là: *khối mã thụt lề ($\ge 4$ khoảng trắng hoặc `\t`) không thể ngắt một đoạn văn đang mở (paragraph)*, nhưng có thể bắt đầu ở đầu tài liệu, sau dòng trống, hoặc ngay sau một khối không phải đoạn văn (như code fence, heading, horizontal rule, table).
  - Nếu một dòng có $\ge 4$ khoảng trắng đứng ngay sau dòng đoạn văn thường (không có dòng trống ngăn cách), đó là dòng tiếp nối đoạn văn (lazy paragraph continuation). Nếu dòng đó bắt đầu bằng `    $$x=1$$` và bước `_isolate_display_math_blocks()` chèn dòng trống phía trước nhưng vẫn giữ nguyên 4 khoảng trắng (`\n    \n    $$x=1$$`), thì `markdown-it` ở bước sau sẽ nhìn thấy dòng trống + 4 khoảng trắng và phân tích nhầm `    $$x=1$$` thành `code_block` thay vì `MathBlock`. Việc chuẩn hóa indent khi tách dòng tiếp nối giải quyết triệt để điểm mù này.
  - Khi đang ở trong `in_indented_code`, mọi dòng thụt lề $\ge 4$ khoảng trắng (hoặc `\t`) và các dòng trống xen giữa được đẩy nguyên vẹn vào `out_lines`, bảo toàn 100% ký tự (`prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, `<b>tag</b>`) qua toàn bộ chuỗi `_normalize_math_delimiters` $\to$ `_isolate_display_math_blocks` $\to$ `_sanitize_html` $\to$ `md.parse`.
- **Alternatives considered**:
  - *Chỉ chạy `_isolate_display_math_blocks()` trên các phân đoạn `is_code=False` từ `_split_code_segments()`*: Không khả thi trực tiếp nếu cắt rời từng đoạn inline code span vì `_isolate_display_math_blocks()` cần ngữ cảnh đầu dòng và toàn dòng để nhận diện `prefix: $$...$$` hoặc bảng GFM chứa code span nội dòng. Do đó, giữ máy trạng thái dòng trong `_isolate_display_math_blocks()` với trạng thái `in_indented_code` là thiết kế nhất quán, tự chủ (kể cả khi gọi trực tiếp `_isolate_display_math_blocks` trong unit test) và đạt chuẩn $O(n)$.

---

## R4. Nhận diện Chính xác Ngữ cảnh Bảng GFM trong `_isolate_display_math_blocks()`

- **Decision**: Thay thế cơ chế đánh dấu cả nhóm dòng liên tiếp (`group_start..i_line`) bằng thuật toán xác thực cấu trúc bảng GFM thực sự (khớp với `markdown_it.rules_block.table`):
  1. Dòng phân cách `d` (`d >= 1`) phải khớp mẫu hàng phân cách GFM (chỉ gồm `|`, `-`, `:`, khoảng trắng; chứa ít nhất một dấu `|` hoặc cấu trúc cột hợp lệ; không thụt lề $\ge 4$ khoảng trắng) và xác định số lượng cột $C_{\text{delim}} \ge 1$.
  2. Dòng ngay phía trước `h = d - 1` phải là dòng tiêu đề hợp lệ: không trống, không thụt lề $\ge 4$ khoảng trắng, không thuộc khối mã hoặc bảng trước đó, có chứa ký tự `|` phân cách cột bên ngoài công thức/code span (`_is_table_line`), và có số cột $C_{\text{header}} == C_{\text{delim}}$.
  3. Khi cặp `(h, d)` hợp lệ, đánh dấu `h` và `d` vào `table_line_indices`, sau đó chỉ đánh dấu tiếp các dòng dữ liệu liền kề `k = d + 1, d + 2, ...` chừng nào dòng `k` không trống, không thụt lề $\ge 4$ khoảng trắng, không mở khối chắn (code fence, blockquote, heading, list, hr) và thỏa mãn `_is_table_line(lines[k])`.
  4. Mọi dòng nằm trước `h` (tức `< d - 1`) trong cùng nhóm dòng không trống **tuyệt đối không** được đưa vào `table_line_indices`.
- **Rationale**:
  - Trong `markdown-it`, quy tắc `table` nằm trong danh sách `paragraph` terminators, nghĩa là một đoạn văn chứa `|` ở dòng `0` sẽ kết thúc tại dòng `1` nếu dòng `1` (header) và dòng `2` (delimiter) tạo thành bảng hợp lệ. Dòng `0` vẫn là `Paragraph`, không phải một phần của bảng.
  - Thuật toán mới đảm bảo đoạn văn chứa `|` và `$$x=1$$` đứng ngay trước bảng hoặc đứng trước một dòng giả phân cách (không khớp số cột với dòng liền trước) vẫn được tách `MathBlock` chuẩn xác, đồng thời bảo toàn 100% các trường hợp bảng GFM chuẩn và bảng compact đã hỗ trợ.
- **Alternatives considered**:
  - *Bỏ qua tiền quét bảng*: Sẽ làm hỏng các ô bảng bắt đầu bằng `$$x=1$$ | 2` trong bảng compact (regression đối với feature 055).

---

## R5. Đảm bảo Độ phức tạp Tuyến tính $O(n)$ trong `_split_code_segments()` và `_find_code_spans()`

- **Decision**:
  1. Thay thế hoàn toàn `re.match(r"^([ ]{0,3}>[ ]?)+", text[i:])` trong `_split_code_segments()` bằng biểu thức chính quy biên dịch sẵn ở cấp lớp `_BQ_PREFIX_RE = re.compile(r"([ ]{0,3}>[ ]?)+")` và gọi `_BQ_PREFIX_RE.match(text, i, eol)` trực tiếp trên chuỗi gốc `text` tại chỉ số `i` (không cắt lát chuỗi `text[i:]`).
  2. Trong nhánh kiểm tra dòng trống giữa khối mã thụt lề (lines 264-283), khi xác nhận các dòng trống dẫn tới một dòng thụt lề tiếp theo (`not is_trailing_blank`), nhảy trực tiếp `curr_line_start = peek` thay vì chỉ tiến từng dòng trống, tránh quét lặp lại các dòng trống liên tiếp.
  3. Trong cả `_split_code_segments()` và `_find_code_spans()`, áp dụng cơ chế bộ nhớ đệm vị trí backtick tối đa (`backticks_scanned: bool` và `backticks_max_pos: dict[int, int]`, tương tự `markdown_it.rules_inline.backticks`): khi quét tìm chuỗi đóng có độ dài `span_len`, đo độ dài thực tế `closer_len` của từng cụm backtick liên tiếp gặp trên đường đi; nếu không khớp thì ghi nhận `backticks_max_pos[closer_len] = match_start` và nhảy qua toàn bộ cụm backtick đó (`j = match_end`). Nếu quét tới cuối chuỗi mà không tìm thấy, bật `backticks_scanned = True` để mọi cụm backtick mở sau đó có `backticks_max_pos.get(span_len, 0) <= start` dừng ngay trong $O(1)$.
- **Rationale**:
  - Loại bỏ `text[i:]` xóa bỏ hoàn toàn việc cấp phát và sao chép bộ nhớ $\Theta(L \cdot n)$ trên tài liệu nhiều dòng.
  - Cơ chế `backticks_scanned` + `backticks_max_pos` ngăn chặn triệt để kịch bản suy biến $\Theta(n^2)$ khi tài liệu chứa hàng nghìn dấu backtick mở không có dấu đóng thuộc nhiều độ dài khác nhau, đảm bảo mỗi cụm backtick chỉ bị duyệt tối đa 2 lần trên toàn văn bản.
- **Alternatives considered**:
  - *Chỉ sửa `text[i:]` mà giữ nguyên vòng lặp `text.find(closer, j)`*: Sẽ vẫn bị $\Theta(n^2)$ khi gặp đầu vào bất lợi có nhiều dấu backtick mở không có dấu đóng như yêu cầu kiểm thử của người dùng.
