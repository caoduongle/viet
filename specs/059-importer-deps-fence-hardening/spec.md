# Feature Specification: Bảo toàn tính tùy chọn của phụ thuộc tài liệu và đồng bộ nhận diện khối mã trong bộ nhập Markdown

**Feature Branch**: `059-importer-deps-fence-hardening`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát sau commit 62a93b7 (CI 5/5 xanh): Phát hiện 1 lỗi tương thích phụ thuộc ảnh hưởng bản cài đặt tối giản và 2 điểm cần gia cố trong bộ phân tích Markdown, kèm 3 nhóm kiểm thử bổ sung: (P1) Bảo toàn tính tùy chọn của thư viện xử lý Markdown khi nạp gói bộ nhập để môi trường tối giản vẫn dùng được định dạng văn bản thuần và nhận thông báo hướng dẫn rõ ràng khi thiếu thư viện tùy chọn; (P2) Nhận diện khối mã rào chắn (code fence) trong trích dẫn (blockquote) phải xác minh ngữ cảnh trích dẫn của dòng đóng khớp với khối đã mở; (P2) Đồng bộ điều kiện mở khối mã rào chắn (chuỗi thông tin sau dấu backtick không được chứa backtick) giữa các bước tiền xử lý; bổ sung kiểm thử môi trường tối giản, kiểm thử đối kháng cho trích dẫn lồng nhau/thông tin rào chắn không hợp lệ, và kiểm thử hiệu năng tuyến tính với dữ liệu bất lợi đa dạng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sử dụng bản cài đặt tối giản không cần thư viện tài liệu mở rộng (Priority: P1)

Là người dùng hoặc nhà tích hợp chỉ cài đặt gói phần mềm lõi (không cài nhóm thư viện mở rộng cho tài liệu), tôi cần sử dụng được bình thường các chức năng cốt lõi và bộ nhập văn bản thuần (TXT), đồng thời nhận được thông báo hướng dẫn cài đặt rõ ràng khi gọi đến tính năng nhập Markdown.

**Why this priority**: Cấu hình gói phần mềm công bố nhóm thư viện tài liệu là tùy chọn (không bắt buộc cho bản cài đặt lõi). Nếu nạp gói bộ nhập làm phát sinh lỗi thiếu thư viện ngay lập tức, toàn bộ tính năng nhập văn bản thuần và bộ điều phối nhập tài liệu sẽ ngừng hoạt động trên môi trường tối giản, dù CI mặc định (có cài đủ thư viện) vẫn báo xanh.

**Independent Test**: Trong môi trường không có thư viện xử lý Markdown, thực hiện nạp gói bộ nhập, bộ điều phối nhập và nhập thử một tệp văn bản thuần (`.txt`) — tất cả phải thành công; sau đó gọi khởi tạo hoặc nhập tài liệu Markdown (`.md`) — hệ thống phải trả về đúng loại lỗi phụ thuộc tùy chọn kèm thông báo hướng dẫn cài đặt.

**Acceptance Scenarios**:

1. **Given** môi trường chỉ cài đặt gói lõi và không có thư viện xử lý Markdown, **When** người dùng hoặc hệ thống nạp gói bộ nhập tài liệu và bộ điều phối nhập, **Then** quá trình nạp diễn ra thành công mà không phát sinh lỗi thiếu thư viện.
2. **Given** môi trường không có thư viện xử lý Markdown, **When** người dùng chọn nhập tệp văn bản thuần (`.txt`) hoặc tra cứu bộ nhập cho định dạng văn bản thuần, **Then** tài liệu văn bản thuần được nhập và chuyển đổi đầy đủ như bình thường.
3. **Given** môi trường không có thư viện xử lý Markdown, **When** người dùng yêu cầu khởi tạo bộ nhập Markdown hoặc nhập tệp `.md`, **Then** hệ thống từ chối một cách có kiểm soát bằng lỗi phụ thuộc tùy chọn và hiển thị thông báo hướng dẫn cách cài đặt thư viện còn thiếu.
4. **Given** môi trường không có thư viện xử lý Markdown, **When** gọi trực tiếp các bước tiền xử lý văn bản thuần túy không phụ thuộc thư viện ngoài hoặc xử lý bảng khi đã qua bước kiểm tra phụ thuộc, **Then** hệ thống không bao giờ nạp thư viện tùy chọn ở thời điểm khởi동 module trước khi kiểm tra phụ thuộc.

---

### User Story 2 - Bảo toàn khối mã rào chắn trong các cấp trích dẫn (blockquote) lồng nhau (Priority: P2)

Là người dùng soạn thảo tài liệu Markdown có khối mã rào chắn (code fence) đặt bên trong trích dẫn (`>`), tôi cần khối mã đó không bị đóng sớm bởi một dòng trông giống dấu đóng nhưng nằm ở cấp trích dẫn khác (ví dụ `>>`), để nội dung mã và các công thức toán bên trong hoặc ngay sau dòng đóng giả được giữ nguyên đúng ngữ cảnh.

**Why this priority**: Khi tài liệu chứa trích dẫn nhiều cấp (ví dụ trích dẫn câu trả lời hoặc ví dụ mã trong thảo luận), việc đóng nhầm khối mã làm các dòng mã phía sau bị biến đổi như văn bản thường (công thức bị tách, thẻ bị lọc), gây sai lệch nội dung tài liệu của người dùng.

**Independent Test**: Nhập một tài liệu có khối mã mở trong trích dẫn cấp 1 (`> ``` `), bên trong chứa dòng trích dẫn cấp 2 có dấu đóng giả (`>> ``` `) theo sau bởi dòng chứa ký tự công thức (`> $$x=1$$` hoặc `> \[x=1\]`), rồi mới đến dòng đóng thật ở cấp 1 (`> ``` `); xác nhận toàn bộ nội dung giữa dấu mở và dấu đóng thật được giữ nguyên vẹn từng ký tự như một khối mã duy nhất.

**Acceptance Scenarios**:

1. **Given** khối mã rào chắn được mở ở trích dẫn cấp 1 (`> ``` `), **When** bên trong xuất hiện dòng ở trích dẫn cấp 2 (`>> ``` `) rồi tới dòng `> $$x = 1$$` và `> \[y = 2\]` trước khi đóng ở cấp 1 (`> ``` `), **Then** dòng ở cấp 2 không kết thúc khối mã và các dòng công thức phía sau vẫn nằm nguyên vẹn trong khối mã.
2. **Given** khối mã rào chắn được mở ở trích dẫn cấp 2 (`>> ``` `), **When** gặp dòng đóng ở trích dẫn cấp 2 (`>> ``` `), **Then** khối mã được đóng đúng tại dòng đó và văn bản hoặc công thức ở các dòng tiếp theo được xử lý bình thường.
3. **Given** khối mã rào chắn được mở ở trích dẫn cấp 2 (`>> ``` `), **When** dòng tiếp theo rơi về trích dẫn cấp 1 (`> văn bản kèm $$x=1$$`) hoặc cấp gốc (thoát khỏi khối trích dẫn cấp 2 theo quy tắc chuẩn Markdown), **Then** khối mã rào chắn cấp 2 kết thúc khi ngữ cảnh trích dẫn chứa nó kết thúc, và công thức ở dòng sau được xử lý đúng như văn bản thường.
4. **Given** hai bước tiền xử lý liên tiếp (chuẩn hóa dấu phân cách toán và cô lập khối công thức), **When** xử lý cùng một khối mã trong trích dẫn nhiều cấp, **Then** cả hai bước đều xác định cùng một điểm bắt đầu và kết thúc cho khối mã đó.

---

### User Story 3 - Xử lý nhất quán dòng mở rào chắn mã có chuỗi thông tin không hợp lệ (Priority: P2)

Là người dùng nhập tài liệu Markdown có dòng chứa từ 3 dấu backtick trở lên kèm chuỗi thông tin phía sau cũng chứa dấu backtick (trường hợp theo chuẩn Markdown không phải là mở khối mã rào chắn mà là văn bản có đoạn mã nội dòng), tôi cần mọi bước tiền xử lý đều thống nhất coi dòng đó không mở khối mã, để các công thức toán ở dòng đó và các dòng tiếp theo được nhận diện và tách khối chính xác.

**Why this priority**: Nếu bước chuẩn hóa dấu phân cách coi dòng đó là văn bản thường (vì chuỗi thông tin chứa backtick) nhưng bước cô lập khối công thức lại coi đó là dòng mở khối mã rào chắn, thì toàn bộ các dòng văn bản và công thức phía sau sẽ bị khóa nhầm trong trạng thái khối mã và không được tách thành khối công thức hiển thị.

**Independent Test**: Nhập tài liệu có dòng ```` ```info`invalid ```` theo sau bởi dòng chứa `ta có:$$x=1$$` và `\[y=2\]`; đối chiếu kết quả qua từng bước tiền xử lý và kết quả nhập tài liệu cuối cùng để xác nhận các công thức được chuyển đổi và tách thành khối công thức đúng chuẩn.

**Acceptance Scenarios**:

1. **Given** một dòng bắt đầu bằng từ 3 dấu backtick trở lên nhưng phần thông tin trên cùng dòng có chứa dấu backtick (ví dụ ```` ```python` ```` hoặc ```` ```a`b``` ````), **When** tài liệu đi qua các bước tiền xử lý và nhập hoàn chỉnh, **Then** dòng đó không được coi là mở khối mã rào chắn ở bất kỳ bước nào.
2. **Given** dòng có dấu backtick không hợp lệ như trên và ngay các dòng tiếp theo có công thức dạng `ta có:$$x=1$$` hoặc `\[y=2\]`, **When** nhập tài liệu, **Then** công thức ở các dòng tiếp theo vẫn được chuẩn hóa và tách thành khối công thức hiển thị (`MathBlock`) bình thường.
3. **Given** một dòng bắt đầu bằng từ 3 dấu ngã (`~~~`) trở lên và phần thông tin phía sau có chứa dấu backtick (ví dụ `~~~python` `), **When** nhập tài liệu, **Then** dòng đó vẫn được coi là mở khối mã rào chắn hợp lệ theo chuẩn Markdown và bảo vệ toàn bộ nội dung bên trong cho đến khi đóng.

---

### User Story 4 - Đảm bảo độ ổn định và hiệu năng tuyến tính trước các mẫu dữ liệu đối kháng (Priority: P2)

Là người bảo trì và người dùng xử lý tài liệu lớn hoặc có cú pháp phức tạp, tôi cần hệ thống duy trì thời gian xử lý tăng tuyến tính và bảo toàn chính xác nội dung trên các mẫu dữ liệu bất lợi (nhiều dãy backtick không đóng với độ dài khác nhau, dòng rất dài, khối mã thụt lề trong trích dẫn).

**Why this priority**: Ngăn ngừa nguy cơ treo ứng dụng hoặc suy giảm hiệu năng đột biến khi người dùng dán tài liệu lớn có nhiều ký tự đánh dấu chưa đóng, đồng thời đảm bảo chất lượng toàn diện trước khi kết thúc đợt rà soát.

**Independent Test**: Chạy bộ kiểm thử đối kháng và kiểm thử hiệu năng với dữ liệu gồm nhiều độ dài dấu backtick không đóng xen kẽ trên các dòng dài và ngắn với kích thước tăng dần ($N, 2N, 4N$), xác nhận cả tỷ lệ thời gian chạy tuyến tính lẫn tính toàn vẹn từng ký tự của đầu ra.

**Acceptance Scenarios**:

1. **Given** tài liệu chứa hàng nghìn dãy backtick mở không có dấu đóng với nhiều độ dài khác nhau (1, 2, 3, 4, 5+ backticks) và các dòng văn bản dài, **When** chạy qua toàn bộ chuỗi tiền xử lý, **Then** thời gian xử lý khi tăng kích thước gấp 4 lần không vượt quá 6 lần và nội dung đầu ra được bảo toàn chính xác từng ký tự.
2. **Given** tài liệu kết hợp trích dẫn nhiều cấp, khối mã thụt lề trong trích dẫn, rào chắn có chuỗi thông tin chứa backtick và công thức nằm ngay sau dòng đóng giả, **When** tiền xử lý và nhập tài liệu, **Then** cả văn bản sau tiền xử lý lẫn cấu trúc tài liệu đầu ra đều khớp kỳ vọng, không làm hỏng mã cũng không bỏ sót khối công thức hợp lệ.

---

### Edge Cases

- Môi trường hoàn toàn không cài thư viện xử lý Markdown và plugin toán học: việc nạp gói gốc, gói bộ nhập, lớp cơ sở, bộ nhập TXT và hàm chọn bộ nhập theo đường dẫn `.txt` đều hoạt động bình thường; chỉ khi khởi tạo bộ nhập Markdown mới báo lỗi phụ thuộc tùy chọn.
- Tiền tố trích dẫn có khoảng trắng linh hoạt theo chuẩn Markdown (ví dụ `> `, ` >`, `  >  > `, `>>`): so sánh ngữ cảnh trích dẫn của dòng đóng phải dựa trên độ sâu (số cấp `>`) thay vì so khớp chuỗi ký tự khoảng trắng cứng nhắc.
- Khối mã rào chắn mở trong trích dẫn cấp $k$ nhưng dòng sau chỉ có độ sâu trích dẫn $< k$ (hoặc không có `>`): theo chuẩn CommonMark, khối trích dẫn cấp $k$ đã đóng nên khối mã bên trong nó cũng tự động đóng tại ranh giới đó.
- Dòng mở rào chắn bằng backtick có chuỗi thông tin chứa backtick trên cùng dòng (như ```` ```foo`bar ```` hoặc ```` ```code``` ```` trên một dòng đơn): được xử lý như đoạn mã nội dòng (inline code span), không mở rào chắn nhiều dòng.
- Bảng Markdown có ký tự `|` được thoát (`\|`) hoặc nằm trong đoạn mã nội dòng: việc tách ô tiêu đề bảng vẫn hoạt động chính xác mà không cần nạp thư viện tùy chọn ở cấp module khi chưa dùng đến.

## Requirements *(mandatory)*

### Functional Requirements

**Phụ thuộc tùy chọn & Môi trường tối giản (US1)**

- **FR-001**: Hệ thống MUST NOT nạp trực tiếp bất kỳ thư viện thuộc nhóm phụ thuộc tùy chọn (như thư viện phân tích Markdown hoặc plugin toán học) ở thời điểm nạp module của gói bộ nhập hoặc module bộ nhập Markdown trước khi thực hiện kiểm tra phụ thuộc.
- **FR-002**: Khi chạy trong môi trường chỉ có gói lõi (không có thư viện xử lý Markdown), các thao tác nạp gói bộ nhập, nạp lớp cơ sở, nạp bộ nhập văn bản thuần (`TxtImporter`), điều phối nhập và chọn bộ nhập cho tệp `.txt` MUST hoàn tất thành công.
- **FR-003**: Khi chạy trong môi trường không có thư viện xử lý Markdown, việc khởi tạo bộ nhập Markdown hoặc gọi nhập tài liệu `.md` MUST kích hoạt lỗi phụ thuộc tùy chọn (`OptionalDependencyError`) với thông báo hướng dẫn cài đặt rõ ràng.
- **FR-004**: Tiện ích tách ô bảng có xét ký tự thoát MUST được thực hiện an toàn mà không làm phát sinh phụ thuộc bắt buộc ở cấp module (hoặc chỉ nạp sau khi đã xác nhận phụ thuộc, hoặc dùng logic nội bộ tương đương đạt chuẩn GFM).

**Đồng bộ nhận diện khối mã rào chắn & Trích dẫn (US2, US3)**

- **FR-005**: Cả bước phân tách đoạn mã và bước cô lập khối công thức MUST áp dụng thống nhất điều kiện mở khối mã rào chắn theo chuẩn CommonMark: rào chắn mở bằng dấu backtick (` ``` `) chỉ hợp lệ khi phần chuỗi thông tin sau dãy backtick mở trên cùng dòng KHÔNG chứa bất kỳ ký tự backtick nào; rào chắn mở bằng dấu ngã (`~~~`) được phép chứa backtick trong chuỗi thông tin.
- **FR-006**: Khi một khối mã rào chắn được mở bên trong ngữ cảnh trích dẫn có độ sâu $k$ cấp (số dấu `>` trong tiền tố trích dẫn bằng $k \ge 1$), hệ thống MUST chỉ chấp nhận dòng đóng rào chắn khi dòng đó nằm ở cùng độ sâu trích dẫn $k$ và có dãy ký tự đóng hợp lệ (cùng loại ký tự rào chắn, độ dài $\ge$ độ dài mở, chỉ theo sau bởi khoảng trắng).
- **FR-007**: Một dòng có hình thức giống dấu đóng rào chắn nhưng nằm ở độ sâu trích dẫn lớn hơn ($> k$, ví dụ mở ở `>` nhưng dòng đó ở `>>`) MUST được coi là một dòng nội dung bên trong khối mã đang mở (với phần `>` dư ra là nội dung mã), tuyệt đối không được đóng khối mã sớm.
- **FR-008**: Nếu khối mã rào chắn đang mở ở độ sâu trích dẫn $k \ge 1$ mà gặp một dòng có độ sâu trích dẫn nhỏ hơn $k$ (kể cả dòng trống không đủ cấp `>` hoặc dòng văn bản ở cấp thấp hơn), khối mã rào chắn đó MUST tự động kết thúc trước dòng đó theo đúng quy tắc đóng khối chứa (container block) của chuẩn CommonMark.

**Kiểm thử & Hiệu năng đối kháng (US4)**

- **FR-009**: Bộ kiểm thử tự động MUST bao gồm các ca kiểm thử mô phỏng môi trường thiếu thư viện Markdown để xác minh (a) nạp gói bộ nhập và dùng `TxtImporter` thành công, và (b) khởi tạo `MarkdownImporter` báo lỗi `OptionalDependencyError` đúng thiết kế.
- **FR-010**: Bộ kiểm thử tự động MUST bao gồm các ca kiểm thử đối kháng cho Markdown: rào chắn mã trong các cấp trích dẫn khác nhau (`>` so với `>>`), rào chắn backtick có chuỗi thông tin chứa backtick, khối mã thụt lề trong trích dẫn, và công thức toán nằm ngay sau dòng đóng giả — kiểm tra cả nội dung văn bản sau từng bước tiền xử lý lẫn cấu trúc tài liệu kết quả.
- **FR-011**: Bộ kiểm thử hiệu năng MUST kiểm tra thêm các mẫu dữ liệu bất lợi kết hợp: nhiều dãy backtick không đóng có độ dài khác nhau (1 đến 6+ backticks), các dòng dài và tiền tố trích dẫn, xác minh đồng thời tính toàn vẹn nội dung đầu ra và tỷ lệ thời gian chạy tuyến tính ($T(4N)/T(N) \le 6.0$).
- **FR-012**: Toàn bộ 8 ca chuẩn Golden Master MUST giữ nguyên mã băm SHA-256 100%, và toàn bộ các bộ kiểm thử hiện có trên CI MUST tiếp tục vượt qua.

### Key Entities

- **Phụ thuộc tùy chọn (Optional Dependency)**: Thư viện mở rộng phục vụ định dạng tài liệu cụ thể (như Markdown), chỉ bắt buộc khi người dùng kích hoạt tính năng của định dạng đó, không bắt buộc cho bản cài đặt lõi.
- **Độ sâu trích dẫn (Blockquote Depth)**: Số lượng dấu `>` hợp lệ tạo nên tiền tố trích dẫn ở đầu dòng theo chuẩn CommonMark, quyết định phạm vi khối chứa của khối mã bên trong.
- **Khối mã rào chắn (Fenced Code Block)**: Vùng văn bản mở đầu bằng dãy $\ge 3$ ký tự `` ` `` hoặc `~` hợp lệ (tuân thủ quy tắc chuỗi thông tin) và kết thúc khi gặp dòng đóng cùng cấp trích dẫn hoặc khi khối trích dẫn chứa nó kết thúc.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trong môi trường kiểm thử không có thư viện xử lý Markdown, 100% thao tác nạp bộ điều phối, `TxtImporter` và nhập tệp `.txt` thành công; 100% thao tác khởi tạo `MarkdownImporter` báo đúng lỗi `OptionalDependencyError`.
- **SC-002**: 100% ca kiểm thử đối kháng về trích dẫn lồng nhau (`>` với dòng đóng giả `>>`, thoát trích dẫn sớm) và rào chắn có chuỗi thông tin chứa backtick cho kết quả đồng nhất giữa các bước tiền xử lý và bảo toàn 100% nội dung mã cũng như khối công thức hợp lệ.
- **SC-003**: Trên bộ dữ liệu bất lợi đa độ dài backtick và dòng dài, thời gian thực thi khi kích thước đầu vào tăng gấp 4 lần không vượt quá 6.0 lần ($T(4N)/T(N) \le 6.0$) và nội dung đầu ra khớp 100% từng ký tự.
- **SC-004**: 8/8 ca kiểm thử Golden Master đạt khớp tuyệt đối SHA-256 và 5/5 công việc trên CI vượt qua 100%.

## Assumptions

- Việc so khớp ngữ cảnh trích dẫn cho khối mã rào chắn tuân theo chuẩn CommonMark: độ sâu trích dẫn được tính bằng số lượng dấu `>` trong tiền tố trích dẫn đầu dòng (mỗi dấu `>` có thể có tối đa 3 khoảng trắng phía trước và 1 khoảng trắng tùy chọn phía sau).
- Đối với khối mã thụt lề bên trong trích dẫn (ví dụ `>     code`), hệ thống đảm bảo bảo toàn nội dung theo đúng quy tắc sau tiền tố trích dẫn khi dòng trước đó trong cùng ngữ cảnh trích dẫn là dòng trống.
- Không thay đổi giao diện người dùng, cấu trúc dữ liệu đầu ra hay hợp đồng công khai của các lớp bộ nhập.
