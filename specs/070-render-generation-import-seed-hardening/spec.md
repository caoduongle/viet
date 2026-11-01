# Feature Specification: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử

**Feature Branch**: `070-render-generation-import-seed-hardening`  
**Created**: 2026-11-01  
**Status**: Draft  
**Input**: Rà soát repository viet sau commit `57ca957`, xử lý triệt để race condition khi kết xuất tài liệu cũ ghi đè lên tài liệu mới (render generation), củng cố kiểm thử E2E về reset seed khi nhập file đa định dạng, chuẩn hóa kiểm tra phản hồi API reset và đồng bộ benchmark kho mẫu đa biến thể.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ngăn chặn kết quả kết xuất cũ ghi đè lên tài liệu mới (Priority: P1)

Khi người dùng đang soạn thảo hoặc mở một tài liệu mới trong lúc tài liệu trước đó vẫn đang được hệ thống xử lý kết xuất ở tiến trình nền, hệ thống phải xác định và loại bỏ các kết quả kết xuất đã lỗi thời, đảm bảo vùng xem trước và tệp xuất ra luôn tương ứng chính xác 100% với nội dung hiện có trên màn hình.

**Why this priority**: Tránh hiện tượng nội dung tài liệu cũ đột ngột chớp tắt hoặc ghi đè lên tài liệu mới, và ngăn ngừa nguy cơ nghiêm trọng khi người dùng tải xuống tệp kết xuất của tài liệu trước đó thay vì tài liệu mới đang hiển thị.

**Independent Test**: Gửi yêu cầu kết xuất cho tài liệu A, lập tức thay thế bằng tài liệu B trước khi A xử lý xong; xác nhận kết quả trả về của A bị từ chối và giao diện chỉ cập nhật bản xem trước tương ứng với tài liệu B.

**Acceptance Scenarios**:
1. **Given** người dùng bắt đầu kết xuất tài liệu $A$, **When** người dùng xóa hoặc thay thế bằng nội dung tài liệu $B$ trước khi kết quả của $A$ hoàn tất, **Then** kết quả của $A$ khi hoàn tất không được cập nhật vào vùng hiển thị và tệp xuất, đồng thời tài liệu $B$ được kết xuất chuẩn xác.
2. **Given** hệ thống đang trong quá trình kết xuất một tài liệu lớn, **When** người dùng xóa sạch toàn bộ nội dung trong ô soạn thảo, **Then** bản xem trước lập tức được xóa trắng và không bao giờ bị kết quả của tài liệu lớn ghi đè lại sau đó.
3. **Given** nhiều lượt chỉnh sửa liên tiếp tạo ra các yêu cầu kết xuất dồn dập, **When** các kết quả trả về không theo thứ tự thời gian gửi, **Then** hệ thống chỉ chấp nhận kết quả của lượt chỉnh sửa mới nhất và loại bỏ tất cả các kết quả cũ hơn.

---

### User Story 2 - Kiểm chứng E2E việc xóa sạch lịch sử hạt giống khi mở tài liệu mới (Priority: P1)

Khi người dùng mở một tệp văn bản mới (hỗ trợ cả định dạng văn bản thuần .txt, định dạng Markdown .md, và tài liệu Word .docx), hệ thống phải khởi tạo lại trạng thái đối chiếu hạt giống nét chữ độc lập từ đầu, không kế thừa chỉ số xuất hiện (occurrence) của các từ lặp từ tài liệu đã soạn thảo trước đó.

**Why this priority**: Đảm bảo tính nhất quán và nguyên bản của tài liệu mới nhập; các từ trong tài liệu mới không bị áp dụng sai biến thể nét chữ do ảnh hưởng từ tài liệu cũ còn lưu trong bộ nhớ phiên làm việc.

**Independent Test**: Viết tài liệu A chứa các từ lặp khiến biến thể nét chữ chuyển sang biến thể tiếp theo (occurrence $\ge 1$), sau đó mở tài liệu B chứa cùng các từ đó; xác nhận nét chữ của các từ trong tài liệu B khớp hoàn toàn với một tài liệu được mở mới từ đầu (occurrence = 0).

**Acceptance Scenarios**:
1. **Given** tài liệu cũ đã kích hoạt biến thể nâng cao cho từ lặp, **When** người dùng mở một tệp .txt mới chứa từ đó, **Then** từ đó trong tài liệu mới được tạo hình với biến thể ban đầu độc lập.
2. **Given** tài liệu cũ đã có lịch sử soạn thảo dài, **When** người dùng mở tệp .md hoặc .docx mới, **Then** quá trình chuyển đổi và nạp tài liệu tự động xóa sạch dấu vết đối chiếu cũ trước khi hiển thị.
3. **Given** hệ thống đang xử lý dở dang việc kết xuất tài liệu hiện tại, **When** người dùng kích hoạt mở một tệp mới, **Then** yêu cầu kết xuất cũ bị vô hiệu hóa ngay lập tức và tài liệu mới được kết xuất với trạng thái hạt giống sạch.

---

### User Story 3 - Tăng cường độ bền vững cho kiểm thử hình thái nét vẽ và xử lý phản hồi API (Priority: P2)

Kiểm thử tự động đối chiếu hình thái nét chữ phải nhóm các nét vẽ theo thực thể từ hoặc khối ký tự thay vì phụ thuộc vào các vị trí chỉ số mảng cố định, đồng thời tầng giao diện phải kiểm tra đầy đủ cờ trạng thái thành công/thất bại từ dịch vụ lõi khi yêu cầu đặt lại lịch sử tài liệu.

**Why this priority**: Loại bỏ sự mong manh của bộ kiểm thử khi bộ ký tự mẫu trong kho được cập nhật, và đảm bảo bất kỳ sự cố nào ở dịch vụ xử lý nền khi xóa lịch sử hạt giống đều được phát hiện và cảnh báo kịp thời.

**Independent Test**: Thực hiện phân tách và so sánh các nét vẽ theo từng từ ngữ trong văn bản qua nhiều lượt chỉnh sửa; mô phỏng phản hồi lỗi từ dịch vụ nền và xác nhận giao diện bắt được trạng thái lỗi này.

**Acceptance Scenarios**:
1. **Given** hai lần kết xuất của một tài liệu có các từ được giữ nguyên và từ chèn thêm, **When** bộ kiểm thử so sánh hình thái nét chữ, **Then** các nét được định vị và đối chiếu dựa trên từ ngữ tương ứng mà không bị gãy vỡ bởi chỉ số mảng cố định.
2. **Given** lệnh đặt lại lịch sử hạt giống được gửi xuống dịch vụ nền, **When** dịch vụ nền trả về kết quả mang trạng thái thất bại, **Then** tầng giao diện ghi nhận lỗi và đưa ra cảnh báo thích hợp thay vì âm thầm bỏ qua.

---

### User Story 4 - Chuẩn hóa chú thích và số liệu đo kiểm hiệu năng kho mẫu đa biến thể (Priority: P3)

Tài liệu và mã nguồn kiểm thử hiệu năng bản chụp kho mẫu quy mô lớn phải đồng bộ chính xác giữa số liệu khai báo trong chú thích và cấu trúc dữ liệu thực tế được sinh ra trong bài đo.

**Why this priority**: Đảm bảo tính minh bạch, nhất quán và độ tin cậy tuyệt đối của các báo cáo đo kiểm kỹ thuật khi đối chiếu giữa tài liệu đặc tả và mã nguồn thực thi.

**Independent Test**: Chạy bài kiểm thử hiệu năng kho mẫu đa biến thể và đối chiếu cấu trúc dữ liệu tạo ra (số nhãn, số biến thể, tổng số mẫu) với phần chú thích kỹ thuật.

**Acceptance Scenarios**:
1. **Given** bài đo hiệu năng trích xuất bản chụp kho mẫu, **When** khởi tạo dữ liệu tổng hợp với 1.050+ nhãn và 3.520 mẫu nét, **Then** phần chú thích và các assertion kiểm tra số lượng mẫu khớp chính xác từng danh mục dữ liệu.

---

### Edge Cases

- **Xóa trắng và nhập nhanh nội dung mới**: Người dùng xóa toàn bộ nội dung tài liệu A rồi dán ngay nội dung tài liệu B trong vòng vài mili-giây khi kết xuất của A vẫn đang chạy.
- **Mở tệp bị lỗi hoặc tệp rỗng**: Khi người dùng chọn mở một tệp văn bản rỗng hoặc tệp bị hỏng định dạng, hệ thống phải xử lý an toàn, không để sót trạng thái kết xuất rác.
- **Kết quả trả về chậm bất thường từ dịch vụ nền**: Một tác vụ kết xuất phức tạp của tài liệu A bị nghẽn và trả về sau khi người dùng đã chỉnh sửa qua các tài liệu B, C, D.
- **Nhiều thao tác mở tệp liên tiếp**: Người dùng chọn mở tệp 1 rồi lập tức bấm chọn mở tiếp tệp 2 khi tệp 1 chưa kịp nạp xong.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST gán một mã định danh thế hệ kết xuất (Render Generation / Request ID) tăng đơn điệu cho mỗi yêu cầu kết xuất được phát ra từ trình soạn thảo.
- **FR-002**: Hệ thống MUST chỉ áp dụng dữ liệu kết xuất (bản xem trước, dữ liệu tệp xuất, thông tin trang) vào giao diện người dùng khi mã định danh của kết quả trả về trùng khớp với mã định danh thế hệ kết xuất mới nhất đang kích hoạt.
- **FR-003**: Hệ thống MUST hủy bỏ và không cập nhật giao diện đối với bất kỳ kết quả kết xuất nào có mã định danh thế hệ cũ hơn mã hiện hành, ngay cả khi nội dung ô soạn thảo hiện tại không rỗng.
- **FR-004**: Hệ thống MUST lưu giữ ảnh chụp tham số kết xuất (nội dung văn bản, định dạng tài liệu, các tùy chọn liên quan) tại thời điểm phát yêu cầu và kiểm tra tính tương hợp của ảnh chụp này trước khi dựng giao diện.
- **FR-005**: Hệ thống MUST tự động gửi yêu cầu đặt lại lịch sử đối chiếu hạt giống xuống dịch vụ nền khi người dùng mở thành công một tài liệu mới (áp dụng cho cả tệp văn bản .txt, Markdown .md và Word .docx).
- **FR-006**: Tầng giao diện người dùng MUST kiểm tra tường minh trạng thái thành công của phản hồi từ lệnh đặt lại lịch sử hạt giống, không chỉ dừng lại ở việc bắt ngoại lệ kết nối.
- **FR-007**: Bài kiểm thử tự động đầu-cuối (E2E) MUST xác nhận rằng từ ngữ trong tài liệu mới mở không kế thừa chỉ số biến thể nét chữ (occurrence) từ tài liệu đã soạn thảo trước đó, thông qua việc đối sánh hình học nét vẽ với một bản kết xuất độc lập.
- **FR-008**: Bài đo kiểm hiệu năng bản chụp kho mẫu quy mô lớn MUST đồng bộ chuẩn xác phần chú thích kỹ thuật với số lượng thực tế: 1.050+ nhãn và 3.520 mẫu nét đa biến thể, duy trì thời gian thực thi dưới ngưỡng 200 mili-giây.

---

### Key Entities

- **Render Request**: Đại diện cho một yêu cầu kết xuất từ trình soạn thảo, gồm mã định danh thế hệ tăng đơn điệu (`requestId`), nội dung văn bản, định dạng (txt/md), tùy chọn nét chữ và mốc thời gian tạo.
- **Render Generation State**: Trạng thái quản lý thế hệ kết xuất hiện hành trong phiên làm việc, lưu giữ mã định danh mới nhất (`activeRequestId`) và tham số của yêu cầu đang chờ xử lý (`pendingRequest`).
- **Document History State**: Trạng thái lịch sử tài liệu lưu trong dịch vụ nền phục vụ thuật toán căn chỉnh hạt giống, bao gồm cấu trúc tài liệu của lượt kết xuất gần nhất (`_last_doc`) và hạt giống ngẫu nhiên tương ứng (`_last_seed`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Loại bỏ 100% hiện tượng kết quả kết xuất cũ ghi đè lên bản xem trước hoặc tệp xuất khi nội dung ô soạn thảo đã thay đổi sang tài liệu khác.
- **SC-002**: 100% các thao tác mở tài liệu mới (.txt, .md, .docx) đều khởi tạo trạng thái đối chiếu hạt giống độc lập, với độ sai lệch hình thái nét vẽ so với bản kết xuất gốc bằng 0.
- **SC-003**: Toàn bộ bộ kiểm thử tự động đầu-cuối (E2E) trên trình duyệt (bao gồm các kịch bản kiểm tra mở tài liệu và race condition kết xuất dồn dập) vượt qua (PASS) mà không có lỗi bảng điều khiển (Console errors).
- **SC-004**: Toàn bộ bộ kiểm thử đơn vị, kiểm thử tích hợp và kiểm thử hồi quy của hệ thống đạt tỷ lệ thành công 100% trên tất cả các môi trường hỗ trợ.
- **SC-005**: Thời gian tổng hợp và trích xuất bản chụp kho mẫu quy mô lớn (1.050+ nhãn và 3.520 mẫu nét) duy trì dưới 200 mili-giây.

---

## Assumptions

- Trình duyệt người dùng hỗ trợ Web Worker và chia sẻ thông điệp bất đồng bộ tiêu chuẩn.
- Các định dạng tệp nhập vào (.txt, .md, .docx) tuân thủ đúng định dạng mà hệ thống đang hỗ trợ phân tích cú pháp.
- Người dùng tương tác trên một luồng soạn thảo đơn tại mỗi thời điểm trong một tab làm việc, nhưng các thao tác gõ, xóa và mở tệp có thể diễn ra với tần suất cao (dưới 200ms giữa các thao tác).
- Môi trường thực thi của dịch vụ nền duy trì tính tất định đối với các hạt giống ngẫu nhiên đã cho.
