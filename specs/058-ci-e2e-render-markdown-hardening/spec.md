# Feature Specification: Khôi phục CI xanh, sửa cấu hình Render và siết các trường hợp biên của Markdown importer

**Feature Branch**: `058-ci-e2e-render-markdown-hardening`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Rà soát sau commit 8a46ab0: CI vẫn thất bại ở job Web Client CI (Playwright `tests/e2e/sw-update.spec.ts` build lần hai vào cùng thư mục tạm mà không truyền `--force-clean`, bị cơ chế bảo vệ của `build_web.py` từ chối). Còn các vấn đề: (P1) `PYTHON_VERSION: 3.13` trong `render.yaml` có thể không hợp lệ vì Render yêu cầu biến môi trường là phiên bản đầy đủ; (P1) `_isolate_display_math_blocks()` chưa bảo vệ indented code block chứa `$$...$$`; (P2) tiền quét bảng GFM đánh dấu cả nhóm dòng là bảng nếu bất kỳ dòng nào giống hàng phân cách; (P2) `_split_code_segments()` lấy lát cắt `text[i:]` ở mỗi đầu dòng gây nguy cơ độ phức tạp bậc hai. Không được bỏ cơ chế bảo vệ trong `prepare_dist_dir()` chỉ để CI xanh."

## Bối cảnh đã xác minh

Các nhận định sau đã được đối chiếu trực tiếp với mã nguồn tại commit `8a46ab0`:

- `tests/e2e/sw-update.spec.ts`: hàm `runBuildWeb(distDir)` chỉ truyền `--dist`, và được gọi hai lần vào cùng `tmpDist` (lần 2 sau khi sửa `app.js`). Lần 2 bị `prepare_dist_dir()` từ chối vì thư mục nằm ngoài phạm vi mặc định, đã có dữ liệu, không có `--force-clean`.
- `scripts/build_web.py`: `prepare_dist_dir(dist_dir, force_clean=False)` từ chối dọn thư mục ngoài mặc định không rỗng khi thiếu `--force-clean` — đây là hành vi đúng thiết kế và phải được giữ nguyên.
- `render.yaml`: dịch vụ `runtime: static` chạy `python scripts/build_web.py` trong bước build, với `PYTHON_VERSION` = `3.13`. Repo đã có `.python-version` = `3.13`.
- `chuviettay/importer/markdown_importer.py`:
  - Pipeline: `_sanitize_html(_isolate_display_math_blocks(_normalize_math_delimiters(text)))`.
  - `_normalize_math_delimiters()` đã bỏ qua indented code nhờ `_split_code_segments()`, nhưng `_isolate_display_math_blocks()` chỉ theo dõi code fence, display math và bảng — không có trạng thái indented code.
  - Tiền quét `table_line_indices` đánh dấu toàn bộ nhóm dòng không trống liên tiếp là bảng nếu bất kỳ dòng nào khớp mẫu hàng phân cách.
  - `_split_code_segments()` gọi `re.match(..., text[i:])` tại mỗi đầu dòng.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI Web Client xanh trở lại mà vẫn giữ cơ chế bảo vệ dữ liệu khi build (Priority: P1)

Là người bảo trì, tôi cần bài kiểm thử cập nhật Service Worker build lại được vào thư mục tạm do chính nó tạo, để job Web Client CI vượt qua, trong khi quy tắc từ chối xoá thư mục ngoài có dữ liệu vẫn bảo vệ người dùng thông thường.

**Why this priority**: CI đang đỏ, chặn mọi lần merge/release. Đây là lỗi tích hợp giữa bài test và quy tắc an toàn mới.

**Independent Test**: Chạy riêng bài kiểm thử cập nhật Service Worker; nó build hai lần vào cùng thư mục tạm và xác nhận bộ nhớ đệm mới khác bộ nhớ đệm cũ. Đồng thời chạy lại các bài kiểm thử an toàn build hiện có để xác nhận quy tắc bảo vệ không bị nới lỏng.

**Acceptance Scenarios**:

1. **Given** bài kiểm thử đã tạo một thư mục tạm và build lần đầu vào đó, **When** bài kiểm thử build lần thứ hai vào cùng thư mục và chủ động khai báo quyền dọn dẹp, **Then** build thành công và Service Worker nhận được phiên bản mới.
2. **Given** lần build đầu tiên vào thư mục tạm rỗng, **When** bài kiểm thử build mà không khai báo quyền dọn dẹp, **Then** build thành công như mặc định (không cần quyền dọn dẹp cho thư mục rỗng).
3. **Given** một thư mục ngoài phạm vi mặc định đang chứa dữ liệu, **When** build được gọi mà không có quyền dọn dẹp tường minh, **Then** build vẫn bị từ chối với thông báo an toàn như hiện tại.

---

### User Story 2 - Bước build trên Render dùng phiên bản Python hợp lệ (Priority: P1)

Là người vận hành, tôi cần cấu hình triển khai Render chọn được một phiên bản Python hợp lệ, để bước build không thất bại dù GitHub Actions đã xanh.

**Why this priority**: Một cấu hình phiên bản không hợp lệ làm hỏng việc triển khai production và các bản xem trước PR.

**Independent Test**: Kiểm thử tự động xác nhận cấu hình triển khai không còn khai báo phiên bản Python dạng rút gọn qua biến môi trường, và nguồn phiên bản duy nhất là tệp phiên bản của repo; sau đó xác minh bằng một lần deploy thực tế.

**Acceptance Scenarios**:

1. **Given** repo có tệp phiên bản Python khai báo `3.13`, **When** Render build dịch vụ, **Then** Render chọn một bản vá 3.13.x hợp lệ và build hoàn tất.
2. **Given** ai đó thêm lại biến môi trường phiên bản Python dạng `Major.Minor` vào cấu hình triển khai, **When** bộ kiểm thử chạy, **Then** kiểm thử thất bại và chỉ rõ lý do.
3. **Given** cấu hình đã sửa, **When** CI GitHub Actions chạy, **Then** việc thiết lập Python trên CI không bị ảnh hưởng (vẫn đọc tệp phiên bản `3.13`).

---

### User Story 3 - Nội dung trong khối mã thụt lề được bảo toàn nguyên vẹn qua toàn bộ quá trình nhập Markdown (Priority: P1)

Là người dùng nhập tài liệu Markdown có khối mã thụt lề (4 khoảng trắng hoặc tab), tôi cần nội dung mã — kể cả các chuỗi trông giống công thức (`$$...$$`, `\[...\]`) hoặc thẻ HTML — được giữ nguyên từng ký tự.

**Why this priority**: Làm sai lệch mã nguồn trong tài liệu là lỗi mất tính toàn vẹn dữ liệu người dùng.

**Independent Test**: Nhập một tài liệu có đoạn văn, dòng trống, khối mã thụt lề chứa `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, `<b>tag</b>`, rồi đoạn văn tiếp theo; xác nhận khối mã đầu ra trùng khớp ký tự với đầu vào và đoạn văn xung quanh vẫn được xử lý bình thường.

**Acceptance Scenarios**:

1. **Given** khối mã thụt lề chứa `prefix:$$x=1$$`, **When** tài liệu được nhập qua luồng nhập đầy đủ, **Then** khối mã đầu ra chứa đúng dòng `prefix:$$x=1$$`, không bị chèn ngắt dòng hay tách thành công thức.
2. **Given** khối mã thụt lề chứa dòng bắt đầu bằng `$$` hoặc `\[...\]`, **When** nhập, **Then** nội dung được giữ nguyên và không sinh khối công thức.
3. **Given** khối mã thụt lề chứa chuỗi giống thẻ HTML, **When** nhập, **Then** chuỗi đó vẫn hiển thị nguyên văn trong khối mã.
4. **Given** một đoạn văn thường ngay sau khối mã thụt lề chứa `ta có:$$a=b$$`, **When** nhập, **Then** công thức trong đoạn văn thường vẫn được tách thành khối công thức như trước.
5. **Given** dòng thụt lề 4 khoảng trắng nằm ngay sau một dòng văn bản (không có dòng trống phân cách — tức là dòng tiếp nối đoạn văn, không phải khối mã), **When** nhập, **Then** hành vi xử lý công thức trên dòng đó không thay đổi so với hiện tại.

---

### User Story 4 - Đoạn văn chứa ký tự `|` không bị nhận nhầm là bảng (Priority: P2)

Là người dùng, tôi cần công thức trong đoạn văn thường vẫn được tách thành khối công thức kể cả khi đoạn văn chứa ký tự `|` và nằm liền kề một bảng thật hoặc một chuỗi giống hàng phân cách.

**Why this priority**: Gây sai bố cục công thức trong trường hợp ít gặp hơn; không làm mất dữ liệu.

**Independent Test**: Nhập tài liệu có một dòng văn bản chứa `|` và công thức `$$...$$`, theo sau (trong cùng nhóm dòng, không có dòng trống) bởi một bảng hoặc chuỗi giống hàng phân cách không đứng ngay sau hàng tiêu đề; xác nhận công thức của đoạn văn được tách thành khối công thức.

**Acceptance Scenarios**:

1. **Given** một nhóm dòng mà hàng phân cách đứng ngay sau hàng tiêu đề, **When** nhập, **Then** hàng tiêu đề, hàng phân cách và các hàng dữ liệu liền sau được nhận là bảng và nội dung ô (kể cả công thức) không bị tách ra ngoài bảng.
2. **Given** một dòng văn bản chứa `|` và `$$x=1$$` đứng trước hàng tiêu đề của bảng trong cùng nhóm dòng, **When** nhập, **Then** dòng văn bản đó không bị coi là hàng bảng và quy tắc tách công thức vẫn áp dụng.
3. **Given** một nhóm dòng có chuỗi giống hàng phân cách nhưng dòng ngay trước nó không phải hàng tiêu đề hợp lệ, **When** nhập, **Then** không dòng nào trong nhóm bị đánh dấu là bảng chỉ vì chuỗi đó.
4. **Given** các trường hợp bảng đã được hỗ trợ (bảng compact có công thức ở ô đầu, dòng đơn `$$x=1$$ | 2` không có hàng phân cách), **When** nhập, **Then** kết quả giữ nguyên như hiện tại.

---

### User Story 5 - Tiền xử lý Markdown giữ thời gian xử lý tuyến tính với tài liệu lớn (Priority: P2)

Là người dùng nhập tài liệu dài, tôi cần thời gian tiền xử lý tăng tỷ lệ thuận với kích thước tài liệu, kể cả với đầu vào bất lợi (nhiều dòng, nhiều backtick không đóng).

**Why this priority**: Rủi ro hiệu năng/treo trình duyệt với tài liệu lớn; chưa có báo cáo lỗi thực tế.

**Independent Test**: Đo thời gian tiền xử lý trên các đầu vào bất lợi có kích thước tăng gấp đôi liên tiếp; xác nhận thời gian tăng xấp xỉ tuyến tính, không bậc hai.

**Acceptance Scenarios**:

1. **Given** tài liệu gồm hàng chục nghìn dòng ngắn, **When** tiền xử lý, **Then** khi kích thước tăng gấp 4 lần thì thời gian tăng không quá khoảng 6 lần (biên an toàn cho nhiễu đo).
2. **Given** tài liệu có nhiều backtick mở không có dấu đóng, **When** tiền xử lý, **Then** cùng tiêu chí tăng trưởng gần tuyến tính được thỏa mãn.
3. **Given** mọi tài liệu hợp lệ, **When** tiền xử lý sau khi tối ưu, **Then** kết quả phân tách đoạn mã trùng khớp ký tự với kết quả trước khi tối ưu.

### Edge Cases

- Thư mục tạm của bài kiểm thử bị xoá giữa chừng hoặc build lần đầu thất bại: bài kiểm thử phải báo lỗi build thật, không nuốt lỗi, và vẫn dọn dẹp thư mục tạm cùng khôi phục tệp nguồn đã sửa.
- Quyền dọn dẹp chỉ được trao cho thư mục do chính bài kiểm thử tạo; không thư mục nào khác được build với quyền này.
- Tệp phiên bản Python bị thiếu: kiểm thử phát hiện và báo rõ, vì đó là nguồn phiên bản duy nhất cho Render và CI.
- Khối mã thụt lề có dòng trống ở giữa, kết thúc ở cuối tài liệu, hoặc dùng tab thay khoảng trắng.
- Khối mã thụt lề nằm trong mục danh sách hoặc blockquote: giữ hành vi hiện tại (ngoài phạm vi thay đổi), không được hồi quy.
- Ngắt dòng CRLF trong tài liệu chứa khối mã thụt lề và bảng.
- Bảng không có hàng dữ liệu (chỉ tiêu đề + phân cách); bảng có số cột hàng tiêu đề khác số cột hàng phân cách (GFM không coi là bảng).
- Tài liệu rỗng, chỉ có khoảng trắng, hoặc chỉ có một dòng.

## Requirements *(mandatory)*

### Functional Requirements

**Build & CI (US1)**

- **FR-001**: Tiện ích build trong bài kiểm thử cập nhật Service Worker MUST cho phép tùy chọn khai báo quyền dọn dẹp tường minh; mặc định là không có quyền.
- **FR-002**: Lần build đầu vào thư mục tạm MUST dùng mặc định (không quyền dọn dẹp); lần build thứ hai vào cùng thư mục tạm do bài kiểm thử tự tạo MUST khai báo quyền dọn dẹp.
- **FR-003**: Quy tắc từ chối dọn thư mục ngoài phạm vi mặc định đang có dữ liệu khi thiếu quyền dọn dẹp MUST được giữ nguyên; không được nới lỏng, bỏ qua hay thêm đường tắt chỉ phục vụ kiểm thử.
- **FR-004**: Bài kiểm thử MUST tiếp tục báo lỗi build thật ngay lập tức (không nuốt lỗi) và MUST khôi phục tệp nguồn đã sửa cùng dọn thư mục tạm kể cả khi thất bại.

**Render (US2)**

- **FR-005**: Cấu hình triển khai Render MUST NOT khai báo phiên bản Python dạng `Major.Minor` qua biến môi trường. Mặc định được chọn: bỏ biến môi trường phiên bản Python để Render dùng tệp phiên bản của repo làm nguồn duy nhất.
- **FR-006**: Bộ kiểm thử MUST xác nhận (a) cấu hình triển khai không chứa biến môi trường phiên bản Python dạng rút gọn và (b) tệp phiên bản của repo tồn tại với định dạng `Major.Minor` = `3.13`. Kiểm thử cũ của feature 057 yêu cầu biến môi trường bằng `3.13` MUST được thay thế tương ứng.
- **FR-007**: Các khai báo khác trong cấu hình triển khai (phiên bản Node, lệnh build, header bảo mật, định tuyến) MUST giữ nguyên.

**Markdown importer (US3–US5)**

- **FR-008**: Bước cô lập khối công thức display MUST nhận diện khối mã thụt lề theo đúng chuẩn CommonMark 4.4 đồng nhất với bộ phân tách đoạn mã (dòng thụt ≥4 khoảng trắng hoặc tab không thể ngắt đoạn văn đang mở, nhưng bắt đầu khối mã thụt lề khi đứng ở đầu tài liệu, sau dòng trống, hoặc sau khối không phải đoạn văn; cho phép dòng trống ở giữa nếu theo sau là dòng thụt lề) và MUST giữ nguyên mọi dòng thuộc khối đó.
- **FR-009**: Nội dung khối mã thụt lề MUST được bảo toàn ký tự qua toàn bộ luồng nhập, bao gồm `$$...$$`, `\[...\]`, `\(...\)` và chuỗi giống thẻ HTML.
- **FR-010**: Dòng thụt lề ≥4 khoảng trắng là dòng tiếp nối đoạn văn (đứng ngay sau dòng đoạn văn thường, không có dòng trống) MUST NOT bị coi là khối mã; khi dòng đó bắt đầu bằng `$$...$$` ở cấp gốc, bước cô lập MUST tách thành `MathBlock` mà không để khoảng trắng đầu dòng sau dòng trống mới chèn biến nó thành khối mã thụt lề ở bước tiếp theo.
- **FR-011**: Việc nhận diện bảng trong bước cô lập công thức MUST chỉ đánh dấu bảng khi có hàng tiêu đề chứa `|` ngay trước hàng phân cách và số cột khớp ($C_{\text{header}} == C_{\text{delim}} \ge 1$); các hàng dữ liệu liên tiếp ngay sau (đến dòng trống, khối chắn hoặc dòng không chứa `|` ngoài code/công thức) thuộc bảng. Các dòng khác trong cùng nhóm (đặc biệt là các dòng đoạn văn đứng trước hàng tiêu đề) MUST NOT bị đánh dấu là bảng.
- **FR-012**: Các hành vi bảng đã hỗ trợ (bảng compact có công thức ở ô đầu; dòng đơn có `|` ngoài công thức không có hàng phân cách) MUST giữ nguyên kết quả.
- **FR-013**: Bộ phân tách đoạn mã và bộ tìm code span MUST NOT sao chép phần đuôi tài liệu tại mỗi đầu dòng và MUST NOT quét lặp bậc hai khi gặp nhiều dấu backtick mở không có dấu đóng; tổng chi phí xử lý MUST tăng tuyến tính theo kích thước đầu vào.
- **FR-014**: Kết quả của bộ phân tách đoạn mã sau tối ưu MUST trùng khớp ký tự với kết quả trước tối ưu trên toàn bộ ca kiểm thử hiện có và ca bất lợi mới.
- **FR-015**: MUST bổ sung kiểm thử độ phức tạp chạy trực tiếp trong CI với đầu vào bất lợi (nhiều dòng chứa tiền tố blockquote và nhiều dấu backtick mở không có dấu đóng ở các độ dài khác nhau), đo trên ba kích thước tăng dần ($N, 2N, 4N$) và kiểm tra tỷ lệ tăng thời gian vô điều kiện ($T(4N)/T(N) \le 6.0$, không dùng nhánh `if t1 > 0.01` có thể bỏ qua phép kiểm tra).

**Phạm vi & hồi quy**

- **FR-016**: Golden Master (8 ca) MUST trùng khớp SHA-256 100% sau thay đổi.
- **FR-017**: Toàn bộ kiểm thử Python, JavaScript, Playwright và build web hiện có MUST tiếp tục vượt qua.

### Key Entities

- **Thư mục build tạm của bài kiểm thử**: Do bài kiểm thử tạo và sở hữu; là thư mục duy nhất được build với quyền dọn dẹp trong luồng E2E.
- **Nguồn phiên bản Python**: Tệp phiên bản của repo (`3.13`), dùng chung cho CI và Render.
- **Khối mã thụt lề**: Vùng dòng thụt lề đứng sau dòng trống; nội dung bất khả xâm phạm qua mọi bước tiền xử lý.
- **Khối bảng GFM**: Hàng tiêu đề + hàng phân cách liền sau + các hàng dữ liệu liên tiếp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Lần chạy CI tiếp theo trên nhánh chính có 5/5 job thành công, trong đó Web Client CI vượt qua 19/19 bài kiểm thử E2E.
- **SC-002**: 100% kiểm thử an toàn build hiện có (từ chối dọn thư mục ngoài có dữ liệu khi thiếu quyền) vẫn vượt qua mà không sửa kỳ vọng.
- **SC-003**: Một lần deploy Render thực tế sau khi merge build thành công với Python 3.13.x (xác minh thủ công, do CI không kiểm tra môi trường Render).
- **SC-004**: 100% ca kiểm thử khối mã thụt lề mới (tối thiểu 5 ca: `$$` sau tiền tố, `$$` đầu dòng, `\[...\]`, chuỗi HTML, dòng trống giữa khối) giữ nguyên nội dung mã từng ký tự.
- **SC-005**: 100% ca kiểm thử nhận diện bảng mới (tối thiểu 3 ca) và 100% ca bảng hiện có vượt qua.
- **SC-006**: Trên đầu vào bất lợi, tăng kích thước 4 lần làm thời gian tiền xử lý tăng không quá 6 lần.
- **SC-007**: Golden Master 8/8 trùng khớp; tổng số kiểm thử thất bại = 0.

## Assumptions

- Theo tài liệu Render, biến môi trường phiên bản Python cần phiên bản đầy đủ và được ưu tiên hơn tệp phiên bản; tệp phiên bản chấp nhận dạng `Major.Minor`. Vì vậy chọn mặc định bỏ biến môi trường thay vì ghim bản vá cụ thể (tránh lặp lại lỗi "phiên bản không có sẵn" của feature 057). Nếu Render không đọc tệp phiên bản cho dịch vụ static, phương án dự phòng là ghim một phiên bản đầy đủ được Render hỗ trợ — chỉ xác định được qua deploy thực tế.
- Feature này điều chỉnh lại một phần quyết định của feature 057 về `render.yaml`; `.python-version` = `3.13` giữ nguyên.
- Khối mã thụt lề lồng trong danh sách/blockquote nằm ngoài phạm vi; chỉ yêu cầu không hồi quy.
- Ngưỡng tăng trưởng 6 lần cho 4 lần kích thước là biên an toàn trước nhiễu đo trên runner chia sẻ; kiểm thử benchmark không chặn CI mặc định.
- Không thay đổi giao diện người dùng, định dạng dữ liệu hay API công khai của importer.
