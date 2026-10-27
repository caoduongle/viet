# Feature Specification: Theo dõi độ sâu trích dẫn cho trạng thái khối toán nhiều dòng và gia cố kiểm thử bảo toàn đầu ra Markdown

**Feature Branch**: `060-blockquote-math-state-hardening`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát sau commit 863ea25 (CI 5/5 xanh): Phát hiện 1 lỗi trạng thái cần sửa trong bộ cô lập công thức toán và các khoảng trống cần siết trong kiểm thử: (P2) Trạng thái khối toán nhiều dòng (in_display_math) chưa theo dõi độ sâu trích dẫn (blockquote depth) lúc mở công thức và chưa xử lý việc thoát khỏi trích dẫn trước khi xét nội dung dòng hiện tại, khiến dòng văn bản bên ngoài trích dẫn (ví dụ 'Ngoài trích dẫn:$$y=2$$') bị nuốt vào khối toán đang mở thay vì được tách thành khối toán độc lập; (Kiểm thử) Gia cố các bài kiểm thử đối kháng và hiệu năng để kiểm tra chính xác bất biến bảo toàn nội dung khối mã, kiểm tra đầy đủ các công thức toán bên ngoài khối mã/trích dẫn (bao gồm cả công thức thứ hai y=3 khi thoát trích dẫn), không chỉ kiểm tra đầu ra khác rỗng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Thoát trạng thái khối toán nhiều dòng khi kết thúc ngữ cảnh trích dẫn (Priority: P1)

Là người dùng nhập tài liệu Markdown có khối toán nhiều dòng mở bên trong trích dẫn (`> $$`) nhưng chưa đóng trước khi khối trích dẫn kết thúc, tôi cần các đoạn văn và công thức toán nằm ở ngoài trích dẫn (hoặc ở cấp trích dẫn nông hơn) được xử lý bình thường theo ngữ cảnh mới, không bị nuốt nhầm vào khối toán dở dang của trích dẫn trước đó.

**Why this priority**: Đây là lỗi logic trực tiếp trong máy trạng thái tiền xử lý Markdown: khi một khối toán nhiều dòng trong trích dẫn chưa đóng mà người dùng đã chuyển sang đoạn văn bản bên ngoài trích dẫn (ví dụ `Ngoài trích dẫn:$$y=2$$`), việc giữ nguyên trạng thái `in_display_math` sẽ bỏ qua hoàn toàn quy tắc tách công thức sau dấu hai chấm và làm mất khối công thức `MathBlock` hợp lệ của người dùng.

**Independent Test**: Nhập tài liệu gồm khối trích dẫn có công thức mở chưa đóng (`> $$\n> x = 1`), theo sau ngay bởi dòng ngoài trích dẫn `Ngoài trích dẫn:$$y=2$$` và `Đoạn văn tiếp theo`; xác nhận cả ở bước cô lập văn bản lẫn kết quả nhập tài liệu cuối cùng rằng `y=2` được tách thành khối công thức hiển thị (`MathBlock`) độc lập và đoạn văn tiếp theo được giữ nguyên.

**Acceptance Scenarios**:

1. **Given** một khối toán nhiều dòng được mở ở trích dẫn cấp 1 (`> $$\n> x = 1`) mà chưa có dấu đóng `$$`, **When** dòng tiếp theo nằm ở cấp gốc ngoài trích dẫn (`Ngoài trích dẫn:$$y=2$$`), **Then** hệ thống nhận diện ngữ cảnh trích dẫn cấp 1 đã kết thúc, tự động thoát trạng thái khối toán đang mở và tách `$$y=2$$` thành một khối công thức hiển thị hợp lệ.
2. **Given** một khối toán nhiều dòng được mở ở trích dẫn cấp 2 (`>> $$\n>> x = 1`) mà chưa đóng, **When** dòng tiếp theo lùi về trích dẫn cấp 1 (`> Trong trích dẫn cấp 1:$$y=2$$`), **Then** hệ thống nhận diện khối trích dẫn cấp 2 đã kết thúc, thoát trạng thái khối toán cấp 2 và xử lý dòng cấp 1 theo đúng quy tắc tách công thức để tạo khối công thức cho `y=2`.
3. **Given** một khối toán nhiều dòng được mở ở trích dẫn cấp 1 (`> $$`) và các dòng tiếp theo vẫn nằm ở cùng trích dẫn cấp 1 (`> x + y = 1\n> $$`), **When** gặp dòng đóng `> $$` ở cùng độ sâu trích dẫn và theo sau là dòng văn bản thường, **Then** khối toán nhiều dòng trong trích dẫn được đóng đúng vị trí và chèn dòng phân cách phù hợp mà không làm vỡ trích dẫn.
4. **Given** một khối toán nhiều dòng được mở ở trích dẫn cấp 1 (`> $$\n> x = 1`), **When** gặp dòng hoàn toàn trống (không có dấu `>`), **Then** trạng thái khối toán nhiều dòng trong trích dẫn được kết thúc ngay tại dòng trống đó theo đúng quy tắc kết thúc khối chứa của chuẩn Markdown.

---

### User Story 2 - Xác minh chặt chẽ bất biến bảo toàn nội dung và đầu ra công thức trong kiểm thử (Priority: P2)

Là người bảo trì dự án, tôi cần các bài kiểm thử đối kháng và kiểm thử hiệu năng không chỉ đo thời gian chạy hay kiểm tra chuỗi đầu ra khác rỗng, mà phải kiểm chứng trực tiếp rằng mọi khối mã (code fence, indented code block) được bảo toàn nguyên vẹn từng ký tự và mọi công thức toán hợp lệ bên ngoài khối mã đều được trích xuất đầy đủ.

**Why this priority**: Một bài kiểm thử hiệu năng chỉ kiểm tra `len(output) > 0` có thể vẫn báo xanh ngay cả khi bộ tiền xử lý làm hỏng nội dung mã hoặc bỏ sót công thức. Việc bổ sung kiểm tra bất biến nội dung giúp khóa chặt chất lượng hồi quy.

**Independent Test**: Chạy bộ kiểm thử tự động và xác nhận: (1) trong bài kiểm thử code fence tự đóng khi thoát trích dẫn, cả hai công thức `x=2` và `y=3` đều được xác nhận trong danh sách `MathBlock`; (2) trong bài kiểm thử đối kháng và hiệu năng, các đoạn code fence / indented code block được giữ nguyên từng ký tự và các công thức bên ngoài code được tách đúng như kỳ vọng.

**Acceptance Scenarios**:

1. **Given** bài kiểm thử khối mã rào chắn mở ở `>>` tự đóng khi lùi về `>` có hai công thức `> ta có:$$x=2$$` và `> \[y=3\]`, **When** thực thi kiểm thử qua luồng nhập tài liệu, **Then** bài kiểm thử xác nhận tường minh danh sách khối công thức đầu ra chứa đủ cả `x=2` lẫn `y=3` theo đúng thứ tự.
2. **Given** tài liệu kiểm thử kết hợp khối mã rào chắn (code fence), khối mã thụt lề (indented code block) và các công thức toán bên ngoài khối mã, **When** chạy qua toàn bộ chuỗi tiền xử lý, **Then** nội dung bên trong mọi khối mã được xác nhận trùng khớp từng ký tự với đầu vào ban đầu và các công thức bên ngoài khối mã được chuẩn hóa, tách khối chính xác.
3. **Given** bài kiểm thử hiệu năng tuyến tính với dữ liệu bất lợi đa độ dài backtick và dòng dài, **When** đo thời gian trên các kích thước $N, 2N, 4N$, **Then** ngoài việc thỏa mãn tỷ lệ thời gian $T(4N)/T(N) \le 6.0$, đầu ra của từng kích thước phải thỏa mãn các bất biến bảo toàn nội dung (giữ nguyên các phần tử mã và chuyển đổi đúng các công thức hợp lệ).

---

### Edge Cases

- Khối toán nhiều dòng mở trong trích dẫn (`> $$`) bị ngắt bởi một dòng trống không có dấu `>` trước khi đến dòng văn bản thường: dòng trống có độ sâu trích dẫn bằng 0 ($< 1$) nên cũng phải kết thúc trạng thái `in_display_math` ngay lập tức.
- Khối toán nhiều dòng mở ở cấp gốc (`$$` với độ sâu trích dẫn bằng 0) và bên trong có dòng bắt đầu bằng ký tự `>` (ví dụ biểu thức so sánh `> 0` ở đầu dòng tiếp theo): khi `math_bq_depth == 0`, dòng có `bq_depth >= 0` không bị coi là thoát khối chứa (vì cấp gốc là khối chứa ngoài cùng), nhưng nếu dòng đó thực sự đóng bằng `$$` thì kết thúc bình thường.
- Khối toán nhiều dòng mở trong trích dẫn cấp $k \ge 1$ nhưng dòng tiếp theo có dấu đóng giả ở cấp trích dẫn sâu hơn ($> k$, ví dụ `>> $$`): chỉ đóng khối toán khi dòng đóng nằm ở cùng độ sâu trích dẫn $k$ (hoặc hủy trạng thái khi thoát trích dẫn về độ sâu $< k$).
- Dòng ngay sau khối toán nhiều dòng bị hủy (do thoát trích dẫn) lại chính là một dòng mở code fence, khối mã thụt lề, bảng GFM, hoặc dòng chứa `prefix:$$math$$`: vì dòng hiện tại được xử lý lại từ đầu ở ngữ cảnh mới sau khi hủy `in_display_math`, mọi cấu trúc trên đều phải được nhận diện đầy đủ.

## Requirements *(mandatory)*

### Functional Requirements

**Quản lý trạng thái khối toán theo độ sâu trích dẫn (US1)**

- **FR-001**: Khi bắt đầu một khối toán hiển thị nhiều dòng (`in_display_math = True`), bộ cô lập khối công thức MUST lưu lại độ sâu trích dẫn tại dòng mở khối toán đó (`math_bq_depth`).
- **FR-002**: Khi đang ở trạng thái `in_display_math = True` với `math_bq_depth >= 1` mà gặp một dòng (kể cả dòng trống) có độ sâu trích dẫn `bq_depth < math_bq_depth`, hệ thống MUST lập tức kết thúc/hủy trạng thái `in_display_math` (đặt về `False`), khôi phục khả năng bắt đầu khối mã thụt lề nếu phù hợp, và MUST tiếp tục xử lý dòng hiện tại như một dòng mới bên ngoài khối toán đó (không bỏ qua dòng hiện tại bằng `continue`).
- **FR-003**: Khi đang ở trạng thái `in_display_math = True`, một dòng kết thúc bằng `$$` (hoặc `$$` kèm dấu câu) MUST chỉ được công nhận là dòng đóng hợp lệ của khối toán đó khi độ sâu trích dẫn của dòng khớp với `math_bq_depth` (hoặc khi `math_bq_depth == 0` ở cấp gốc).
- **FR-004**: Khi dòng ngoài trích dẫn (hoặc ở cấp trích dẫn nông hơn) xuất hiện ngay sau một khối toán trích dẫn chưa đóng và có chứa công thức dạng `nhãn:$$...$$` hoặc `$$...$$`, hệ thống MUST tách công thức đó thành `MathBlock` hợp lệ trong kết quả nhập tài liệu.

**Gia cố chất lượng kiểm thử & bất biến đầu ra (US2)**

- **FR-005**: Bộ kiểm thử MUST có ca kiểm thử xác minh cả kết quả của bước cô lập công thức lẫn kết quả nhập tài liệu hoàn chỉnh cho trường hợp khối toán mở trong trích dẫn (`> $$\n> x = 1`) bị kết thúc bởi dòng ngoài trích dẫn (`Ngoài trích dẫn:$$y=2$$`) và trường hợp lùi cấp trích dẫn (`>>` về `>`).
- **FR-006**: Ca kiểm thử rào chắn mã tự đóng khi thoát trích dẫn MUST kiểm tra tường minh tất cả các khối công thức được tạo ra (xác nhận cả `x=2` và `y=3`), không chỉ kiểm tra một phần.
- **FR-007**: Bộ kiểm thử MUST kiểm tra chính xác tính bất biến bảo toàn từng ký tự của các đoạn code fence và indented code block đi qua toàn bộ chuỗi tiền xử lý, đồng thời xác nhận các công thức bên ngoài khối mã được chuẩn hóa và tách khối đúng kỳ vọng.
- **FR-008**: Bài kiểm thử hiệu năng đối kháng đa độ dài backtick và dòng dài MUST kết hợp kiểm tra tỷ lệ thời gian tuyến tính ($T(4N)/T(N) \le 6.0$) với các phép kiểm tra nội dung đầu ra cụ thể (xác nhận các mẫu công thức hợp lệ được chuyển đổi đúng và các chuỗi mã/văn bản mục tiêu được bảo toàn đúng số lượng tương ứng với $N, 2N, 4N$).
- **FR-009**: Toàn bộ 8 ca chuẩn Golden Master MUST giữ nguyên mã băm SHA-256 100%, lỗi phụ thuộc tùy chọn đã sửa ở Feature 059 không được tái phát, và toàn bộ kiểm thử hiện có MUST tiếp tục vượt qua.

### Key Entities

- **Độ sâu trích dẫn của khối toán (`math_bq_depth`)**: Số lượng dấu `>` trong tiền tố trích dẫn của dòng mở đầu khối toán hiển thị nhiều dòng (`$$`), xác định phạm vi khối chứa mà khối toán đó tồn tại.
- **Bất biến bảo toàn nội dung (Content Preservation Invariant)**: Điều kiện khẳng định mọi ký tự nằm trong vùng mã (code fence, indented code, inline code span) không bị biến đổi sau toàn bộ các bước tiền xử lý, trong khi mọi công thức toán hợp lệ bên ngoài vùng mã được chuẩn hóa và tách khối đầy đủ.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% ca kiểm thử khối toán nhiều dòng thoát khỏi trích dẫn (từ `>` ra cấp gốc và từ `>>` về `>`) tách đúng khối công thức `MathBlock` ở dòng tiếp theo và vượt qua cả kiểm thử đơn vị lẫn kiểm thử tích hợp.
- **SC-002**: 100% ca kiểm thử bảo toàn nội dung xác nhận khớp chính xác từng ký tự cho các khối mã (code fence, indented code) và khớp đầy đủ 100% số lượng cũng như nội dung LaTeX của các khối `MathBlock` ngoài vùng mã.
- **SC-003**: Bài kiểm thử hiệu năng đối kháng đạt tỷ lệ $T(4N)/T(N) \le 6.0$ đồng thời vượt qua 100% các khẳng định về nội dung đầu ra trên cả 3 kích thước $N, 2N, 4N$.
- **SC-004**: 8/8 ca Golden Master khớp tuyệt đối SHA-256 và toàn bộ các công việc kiểm tra chất lượng (lint, Python unit/integration, Web Client unit, Pyodide, Playwright E2E) vượt qua 100%.

## Assumptions

- Theo chuẩn CommonMark, một khối trích dẫn (`blockquote`) là khối chứa (container block); khi dòng tiếp theo có ít dấu `>` hơn độ sâu của khối trích dẫn đang mở, khối trích dẫn đó đã kết thúc, do đó bất kỳ khối toán hiển thị nhiều dòng nào được mở bên trong nó cũng không thể kéo dài sang các dòng bên ngoài khối trích dẫn.
- Đối với khối toán nhiều dòng mở ở cấp gốc (`math_bq_depth == 0`), ranh giới khối chứa là toàn bộ tài liệu nên hành vi hiện tại đối với các dòng bên trong khối toán cấp gốc được giữ nguyên để đảm bảo tương thích ngược.
- Không thay đổi giao diện người dùng hay hợp đồng API công khai của bộ nhập tài liệu.
