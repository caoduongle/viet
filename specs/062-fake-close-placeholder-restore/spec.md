# Feature Specification: Khôi phục dấu đóng giả bằng dấu giữ chỗ riêng, bảo toàn nguyên vẹn công thức LaTeX

**Feature Branch**: `062-fake-close-placeholder-restore`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát sau commit 518a7e3 (CI 5/5 xanh). (P2) Khôi phục `\$\$` quá rộng: `_parse_blocks()` dùng `tok.content.strip().replace(r"\$\$", "$$")` áp dụng cho mọi nội dung token công thức, không chỉ dấu đóng giả do bộ tiền xử lý chủ động escape. Ví dụ `$$\text{\$\$}$$` bị biến thành `\text{$$}`, làm thay đổi dữ liệu đầu vào hợp lệ. Hướng sửa: dùng một dấu giữ chỗ riêng cho dấu đóng giả do bộ tiền xử lý tạo ra; khi dựng MathBlock chỉ khôi phục dấu giữ chỗ đó về `$$`, tuyệt đối không thay thế hàng loạt mọi `\$\$`. Bổ sung kiểm thử hồi quy xác nhận công thức chứa `\$\$` hợp lệ được giữ nguyên và kiểm thử blockquote lồng nhau hiện tại vẫn đạt. (P3) Trong `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close()`, phần kiểm tra `isolated_nested` vẫn chủ yếu dùng `endswith("$$")` và phép chứa chuỗi; cần so sánh toàn bộ chuỗi đầu ra với giá trị mong đợi (phản ánh chính xác biểu diễn sau biến đổi của dòng `>> $$`) và kiểm tra chính xác nội dung LaTeX sau khôi phục. Sau đó chạy lại toàn bộ CI (importer, Pyodide Golden Master, Playwright E2E)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Công thức LaTeX chứa ký hiệu đô-la được escape được bảo toàn nguyên vẹn (Priority: P1) 🎯 MVP

Là người soạn tài liệu Markdown có công thức toán, tôi cần mọi công thức hợp lệ — kể cả công thức chứa cặp ký hiệu đô-la đã escape như `\text{\$\$}` — được nhập vào tài liệu đúng từng ký tự như tôi đã viết, để chữ viết tay sinh ra phản ánh chính xác nội dung gốc.

**Why this priority**: Đây là lỗi làm sai lệch dữ liệu người dùng một cách âm thầm (CI vẫn xanh). Bước khôi phục hiện tại thay thế toàn cục mọi chuỗi `\$\$` trong nội dung công thức, nên biến `\text{\$\$}` thành `\text{$$}` — một công thức khác về ngữ nghĩa. Đã tái hiện được trên mã hiện tại cho cả công thức một dòng, nhiều dòng và trong trích dẫn.

**Independent Test**: Nhập tài liệu `$$\text{\$\$}$$` và xác nhận khối công thức thu được có nội dung đúng bằng `\text{\$\$}`; lặp lại với dạng nhiều dòng và dạng trong trích dẫn.

**Acceptance Scenarios**:

1. **Given** tài liệu chứa công thức một dòng `$$\text{\$\$}$$`, **When** nhập tài liệu, **Then** thu được đúng 1 khối công thức với nội dung chính xác `\text{\$\$}`.
2. **Given** tài liệu chứa công thức nhiều dòng có dòng `\text{\$\$}` ở giữa (cấp gốc và trong trích dẫn cấp 1), **When** nhập tài liệu, **Then** nội dung khối công thức vẫn chứa nguyên `\text{\$\$}` và không chứa `\text{$$}`.
3. **Given** công thức chứa ký hiệu đô-la escape đơn lẻ (`\$`) hoặc nhiều cặp (`\$\$\$\$`), **When** nhập tài liệu, **Then** toàn bộ ký tự được giữ nguyên, không bị rút gọn hay đổi dạng.

---

### User Story 2 - Dấu đóng giả ở trích dẫn lồng nhau vẫn được bảo vệ và khôi phục đúng (Priority: P1)

Là người bảo trì bộ nhập Markdown, tôi cần cơ chế bảo vệ dấu đóng giả ở độ sâu trích dẫn lồng nhau (`>> $$` trong khối toán mở ở `> $$`) tiếp tục ngăn việc đóng khối sớm, và khi dựng khối công thức chỉ chính những dấu do bộ tiền xử lý chèn vào mới được khôi phục về `$$`.

**Why this priority**: Sửa lỗi ở US1 không được phép làm hồi quy bản sửa của Feature 061. Hai yêu cầu phải đồng thời đúng: dấu đóng giả được đánh dấu bằng biểu diễn riêng không thể nhầm với nội dung người dùng, và chỉ biểu diễn riêng đó được khôi phục.

**Independent Test**: Nhập `> $$\n> x = 1\n>> $$\n> x = 2\n> $$` và xác nhận đúng 1 khối công thức chứa cả `x = 1`, `>> $$`, `x = 2`; nhập thêm một tài liệu kết hợp dấu đóng giả lồng nhau với dòng `\text{\$\$}` trong cùng khối và xác nhận cả hai được bảo toàn đúng.

**Acceptance Scenarios**:

1. **Given** khối toán mở ở trích dẫn cấp 1 có dòng đóng giả `>> $$` (kể cả khi kèm dấu câu và khoảng trắng như `>> $$,   `), **When** nhập tài liệu, **Then** thu được đúng 1 khối công thức, dòng đóng giả hiện lại nguyên dạng `$$` (kèm dấu câu/khoảng trắng gốc) trong nội dung công thức.
2. **Given** cùng một khối toán vừa có dòng đóng giả lồng nhau vừa có dòng chứa `\text{\$\$}`, **When** nhập tài liệu, **Then** dòng đóng giả được khôi phục về `$$` còn `\text{\$\$}` được giữ nguyên.
3. **Given** nội dung người dùng tình cờ chứa chuỗi trùng với biểu diễn đánh dấu nội bộ, **When** nhập tài liệu, **Then** nội dung đó không bị biến đổi (biểu diễn đánh dấu phải được chọn sao cho không thể xuất hiện trong đầu vào sau chuẩn hóa, hoặc đầu vào chứa nó phải được xử lý an toàn).

---

### User Story 3 - Kiểm thử so sánh chính xác toàn bộ chuỗi sau cô lập và nội dung khối công thức (Priority: P3)

Là người bảo trì bộ kiểm thử, tôi cần ca kiểm thử dấu đóng giả lồng nhau so sánh toàn bộ chuỗi đầu ra của bước cô lập khối toán với một giá trị mong đợi cố định, và so sánh chính xác nội dung khối công thức sau khôi phục, thay vì chỉ kiểm tra hậu tố hoặc phép chứa chuỗi.

**Why this priority**: Các phép kiểm tra `endswith("$$")` và "có chứa dòng X" vẫn có thể vượt qua khi biểu diễn trung gian sai (ví dụ dấu đánh dấu bị chèn sai vị trí, dòng phân cách thừa, hoặc nội dung khôi phục mất ký tự). So sánh toàn chuỗi là cách duy nhất ghi lại chính xác hợp đồng hành vi.

**Independent Test**: Chạy riêng `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` và xác nhận các phép so sánh bằng tuyệt đối (`==`) cho chuỗi sau cô lập và nội dung khối công thức đều vượt qua.

**Acceptance Scenarios**:

1. **Given** đầu vào `> $$\n> x = 1\n>> $$\n> x = 2\n> $$`, **When** chạy bước cô lập khối toán, **Then** chuỗi đầu ra bằng chính xác giá trị mong đợi, trong đó dòng `>> $$` mang biểu diễn đánh dấu nội bộ và mọi dòng khác giữ nguyên.
2. **Given** cùng đầu vào, **When** nhập tài liệu, **Then** nội dung khối công thức duy nhất bằng chính xác giá trị mong đợi (không mất ký tự, không chứa biểu diễn đánh dấu nội bộ, không có dấu phân cách ngoài dự kiến).

---

### Edge Cases

- Công thức một dòng chứa `\$\$` sát dấu đóng thật (`$$a\$\$$$`): bước cô lập khối toán hiện đã tách sai ranh giới từ trước feature này (tái hiện: thu được khối `a\$\` và đoạn `$`). Đây là lỗi có sẵn, độc lập với cơ chế khôi phục, nên **nằm ngoài phạm vi** feature 062; feature này chỉ yêu cầu không làm hành vi đó tệ hơn.
- Dòng đóng giả lồng nhau kèm dấu câu và khoảng trắng cuối (`>> $$,   `): khôi phục giữ đúng dấu câu và khoảng trắng.
- Dòng đóng giả ở độ sâu lồng nhau lớn hơn 2 (`>>> $$` trong khối mở ở `> $$`): vẫn được bảo vệ và khôi phục như cấp 2.
- Dấu đánh dấu nội bộ không được rò rỉ ra ngoài khối công thức (đoạn văn, ô bảng, khối mã, công thức nội dòng) trong bất kỳ trường hợp nào, kể cả khi khối toán không có dấu đóng. Tái hiện cho thấy với khối toán trích dẫn không đóng (`> $$ / > x = 1 / >> $$ / > x = 2` rồi hết tài liệu), các dòng rơi vào đoạn văn và dòng đóng giả hiện thành chữ `$$`; hành vi hiển thị chữ `$$` này phải được giữ nguyên.
- Khối mã (fenced/indented) chứa `\$\$` hoặc chuỗi giống dấu đánh dấu: giữ nguyên từng ký tự.
- Văn bản không chứa `$$`: không bị ảnh hưởng (đường tắt hiện có được giữ).

## Requirements *(mandatory)*

### Functional Requirements

**Bảo toàn nội dung công thức (US1)**

- **FR-001**: Bước dựng khối công thức MUST NOT thay thế hàng loạt chuỗi `\$\$` (hay bất kỳ chuỗi do người dùng viết) trong nội dung công thức.
- **FR-002**: Công thức hợp lệ chứa ký hiệu đô-la escape (`\$`, `\$\$`, nhiều cặp liên tiếp) MUST được nhập với nội dung đúng từng ký tự so với đầu vào (sau phần cắt khoảng trắng đầu/cuối vốn có).

**Dấu đánh dấu riêng cho dấu đóng giả (US2)**

- **FR-003**: Bộ tiền xử lý MUST đánh dấu dấu đóng giả ở độ sâu trích dẫn lồng nhau bằng một biểu diễn riêng, không trùng với bất kỳ cú pháp LaTeX/Markdown hợp lệ nào người dùng có thể viết, và vẫn ngăn bộ phân tích đóng khối toán sớm.
- **FR-004**: Khi dựng khối công thức, hệ thống MUST chỉ khôi phục biểu diễn riêng đó về `$$`, giữ nguyên dấu câu và khoảng trắng gốc đi kèm.
- **FR-005**: Biểu diễn riêng MUST NOT xuất hiện trong bất kỳ thành phần nào của tài liệu đầu ra (khối công thức, đoạn văn, bảng, danh sách, khối mã).
- **FR-006**: Nếu đầu vào của người dùng chứa sẵn chuỗi trùng biểu diễn riêng, hệ thống MUST bảo toàn nội dung đó (không khôi phục nhầm thành `$$`).
- **FR-007**: Hành vi đóng khối đúng độ sâu của Feature 060/061 MUST được giữ nguyên: ca `> $$ / > x = 1 / >> $$ / > x = 2 / > $$` cho đúng 1 khối công thức chứa cả `x = 1` và `x = 2`.

**Độ chặt kiểm thử (US3)**

- **FR-008**: Bài kiểm thử `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` MUST so sánh bằng tuyệt đối toàn bộ chuỗi đầu ra của bước cô lập khối toán cho ca lồng nhau với giá trị mong đợi cố định.
- **FR-009**: Bài kiểm thử MUST so sánh bằng tuyệt đối nội dung khối công thức sau khôi phục cho ca lồng nhau (và ca kèm dấu câu `>> $$,   `).
- **FR-010**: MUST bổ sung kiểm thử hồi quy cho công thức chứa `\$\$` hợp lệ ở dạng một dòng, nhiều dòng, trong trích dẫn, và dạng kết hợp với dấu đóng giả lồng nhau trong cùng khối.

### Key Entities

- **Dấu đóng giả (Fake Close Marker)**: Dòng nằm trong khối toán đang mở, có độ sâu trích dẫn lớn hơn độ sâu lúc mở khối và kết thúc bằng `$$` (có thể kèm dấu câu/khoảng trắng); không được phép đóng khối.
- **Biểu diễn đánh dấu nội bộ (Internal Placeholder)**: Chuỗi do bộ tiền xử lý tự sinh thay cho `$$` của dấu đóng giả; tồn tại chỉ trong giai đoạn trung gian và phải được khôi phục/loại bỏ trước khi tài liệu đầu ra được trả về.
- **Nội dung công thức người dùng**: Chuỗi LaTeX gốc trong khối công thức; là dữ liệu bất biến mà hệ thống không được sửa đổi.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các ca hồi quy công thức chứa ký hiệu đô-la escape (tối thiểu 4 dạng: một dòng, nhiều dòng, trong trích dẫn, kết hợp dấu đóng giả) cho nội dung khối công thức trùng khớp từng ký tự với đầu vào.
- **SC-002**: 100% các ca dấu đóng giả lồng nhau hiện có (Feature 061) tiếp tục cho đúng 1 khối công thức với nội dung chính xác như mong đợi.
- **SC-003**: 0 lần xuất hiện biểu diễn đánh dấu nội bộ trong bất kỳ tài liệu đầu ra nào của toàn bộ bộ kiểm thử.
- **SC-004**: Ca kiểm thử lồng nhau dùng so sánh bằng tuyệt đối cho cả chuỗi sau cô lập và nội dung khối công thức (không còn kiểm tra chỉ dựa trên hậu tố cho ca này).
- **SC-005**: Toàn bộ cổng chất lượng đạt 100%: lint 0 lỗi, toàn bộ kiểm thử Python, kiểm thử đơn vị/trình duyệt Web Client, Golden Master Pyodide 8/8 trùng khớp, 19 kiểm thử E2E.

## Assumptions

- Phạm vi giới hạn trong bộ nhập Markdown (`chuviettay/importer/markdown_importer.py`) và bộ kiểm thử `tests/test_markdown_math_block_isolation.py`; không thay đổi thư viện phân tích Markdown bên thứ ba hay plugin công thức.
- Golden Master không chứa công thức có `\$\$` nên mã băm đầu ra dự kiến không đổi; nếu thay đổi, đó là tín hiệu cần điều tra chứ không cập nhật mã băm.
- Hiện tượng nội dung khối công thức trong trích dẫn còn giữ tiền tố `> ` (quan sát được khi tái hiện, ví dụ `> x = 1\n>> $$\n> x = 2\n>`) là hành vi có sẵn từ trước, nằm ngoài phạm vi feature này; giá trị mong đợi trong kiểm thử phản ánh đúng hành vi hiện tại đó.
- Biểu diễn đánh dấu nội bộ có thể dùng ký tự thuộc vùng dùng riêng (Private Use Area) hoặc ký tự điều khiển không xuất hiện trong văn bản Markdown thông thường; lựa chọn cụ thể được quyết định ở bước lập kế hoạch.
