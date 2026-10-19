# Feature Specification: Worker and Seed Integrity Hardening

**Feature Branch**: `044-worker-and-seed-integrity`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User review of commit c6bc265 identifying 5 residual issues: P1 SeedContext RNG scope binding, P1 worker recovery timeout isolation, P2 recursive list & chunked token alignment, P2 strict canonical key typing, and P2 resilient UI initialization state recovery.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tách biệt chu trình khởi động Worker và chu trình nạp kho mẫu (Priority: P1)

Là người dùng ứng dụng viết chữ tay, tôi muốn hệ thống phân định rõ ràng giữa giai đoạn khởi tạo tiến trình nền (Web Worker) và giai đoạn nạp kho dữ liệu mẫu chữ từ bộ nhớ máy tính, sao cho tiến trình nền đã sẵn sàng sẽ không bao giờ bị hủy ngang nhầm lẫn chỉ vì tệp kho mẫu lớn nạp chậm hơn dự kiến, và tôi luôn có thể thử lại an toàn khi gặp sự cố.

**Why this priority**:
Khi kho mẫu có dung lượng lớn hoặc khi thiết bị hoạt động chậm, việc gộp chung thời gian chờ khởi động tiến trình với thời gian nạp dữ liệu kho khiến tiến trình nền bị chấm dứt oan uổng ngay cả khi đã khởi động thành công. Điều này gây lỗi báo giả cho người dùng, làm gián đoạn trải nghiệm và khiến nút "Thử lại" bị vô hiệu hóa không đúng lúc.

**Independent Test**:
Có thể kiểm thử độc lập bằng cách giả lập một tiến trình nền gửi tín hiệu sẵn sàng trong vòng 100ms nhưng bước nạp kho dữ liệu kéo dài hơn 10 giây; hệ thống không được chấm dứt tiến trình nền, bảo toàn thế hệ tiến trình, chỉ áp dụng thời hạn chờ riêng cho bước nạp kho và giữ nguyên giao diện tương tác minh bạch cho người dùng.

**Acceptance Scenarios**:

1. **Given** người dùng kích hoạt khôi phục tiến trình nền, **When** tiến trình mới gửi tín hiệu sẵn sàng (READY) thành công, **Then** hệ thống lập tức hoàn thành giai đoạn chờ khởi động tiến trình, dừng bộ đếm thời gian khởi tạo và chuyển sang giai đoạn nạp kho mẫu độc lập.
2. **Given** tiến trình nền gửi tín hiệu sẵn sàng thành công nhưng bước nạp dữ liệu kho mẫu từ bộ nhớ gặp sự cố hoặc quá thời hạn cho phép nạp kho, **Then** hệ thống không chấm dứt nhầm tiến trình nền đang hoạt động tốt, hiển thị thông báo lỗi tương ứng với bước nạp dữ liệu và mở lại nút "Thử lại" cho người dùng.
3. **Given** một phản hồi hoặc tín hiệu lỗi từ thế hệ tiến trình nền cũ gửi đến muộn sau khi người dùng đã chuyển sang thế hệ tiến trình mới, **Then** hệ thống phát hiện sự khác biệt thế hệ và loại bỏ phản hồi muộn mà không làm sai lệch trạng thái tiến trình mới.

---

### User Story 2 - Toàn vẹn không gian tên sinh số ngẫu nhiên theo ngữ cảnh nội dung (Priority: P1)

Là người soạn thảo văn bản và bảng biểu, tôi muốn các từ ngữ hoặc ký tự giống nhau xuất hiện ở các vị trí có ngữ cảnh khác nhau (như văn bản thông thường, ô trong bảng tính, tiêu đề, công thức toán) luôn có nét chữ biến thiên sinh động, độc lập và không bị lặp lại cùng một biến thể hay độ rung nét chỉ vì có cùng số thứ tự xuất hiện.

**Why this priority**:
Người dùng kỳ vọng chữ viết tay mô phỏng tính ngẫu nhiên tự nhiên của con người. Nếu một từ xuất hiện trong ô bảng và trong đoạn văn bản dùng chung cùng một khóa ngẫu nhiên, hai vị trí này sẽ chọn cùng một nét chữ giống hệt nhau, làm mất tính đa dạng thị giác và vi phạm cam kết cách ly không gian tên giữa các thành phần tài liệu.

**Independent Test**:
So sánh khóa ngẫu nhiên dẫn xuất và biến thể nét vẽ của cùng một từ ngữ (cùng chỉ số thứ tự) khi đặt trong khối văn bản thông thường so với khi đặt trong ô bảng; hệ thống phải chứng minh hai ngữ cảnh này sinh ra hai khóa ngẫu nhiên hoàn toàn độc lập và không có sự can thiệp chéo.

**Acceptance Scenarios**:

1. **Given** cùng một từ ngữ xuất hiện ở lần xuất hiện thứ nhất trong đoạn văn bản và lần xuất hiện thứ nhất trong ô bảng, **When** hệ thống xác định khóa ngẫu nhiên để chọn biến thể mẫu chữ, độ rung nét (jitter) hoặc khoảng cách từ (gap), **Then** khóa ngẫu nhiên tại mỗi vị trí phải bao gồm đầy đủ phân loại nội dung tương ứng, đảm bảo hai luồng ngẫu nhiên hoàn toàn tách biệt.
2. **Given** một tài liệu chứa các ký hiệu toán học và chữ số xuất hiện xen kẽ trong nhiều cấu trúc khác nhau, **When** kết xuất tài liệu, **Then** việc chọn biến thể nét chữ cho ký hiệu trong công thức toán không làm ảnh hưởng đến biến thể của ký hiệu tương tự trong văn bản thường.

---

### User Story 3 - Ổn định hình thái nét chữ khi chỉnh sửa danh sách và phân đoạn từ dài (Priority: P2)

Là người dùng đang hiệu chỉnh tài liệu nhiều thành phần, tôi muốn khi tôi thêm một mục mới vào danh sách hoặc khi một từ ngữ dài bị ngắt dòng xuống hàng kế tiếp, toàn bộ các từ ngữ và mục danh sách cũ phía sau vẫn giữ nguyên 100% hình thái nét chữ đã có trước đó.

**Why this priority**:
Tính năng cốt lõi của ứng dụng là bảo toàn hình thái nét chữ của nội dung cũ khi người dùng bổ sung nội dung mới (Seed Stability). Nếu thuật toán đối chiếu bỏ qua danh sách lồng nhau hoặc tính lệch số thứ tự khi từ ngữ bị chia nhỏ thành nhiều phần, hình dáng chữ viết tay của trang cũ sẽ bị thay đổi đột ngột sau mỗi lần chỉnh sửa nhỏ.

**Independent Test**:
Tạo một tài liệu có danh sách lồng nhau và các từ dài, kết xuất ra tệp; sau đó chèn thêm một mục mới vào đầu danh sách hoặc thay đổi vị trí ngắt dòng, thực hiện đối chiếu và kết xuất lại; kiểm tra hình thái các nét vẽ của các mục danh sách cũ giữ nguyên độ sai lệch hình học dưới ngưỡng dung sai cho phép (<= 0.02 pt).

**Acceptance Scenarios**:

1. **Given** một tài liệu chứa khối danh sách (danh sách có thứ tự hoặc danh sách không có thứ tự), **When** người dùng chèn thêm một mục mới vào đầu danh sách, **Then** hệ thống duyệt đệ quy cấu trúc danh sách và bảo toàn chính xác danh tính cũng như số thứ tự của toàn bộ các mục danh sách ban đầu.
2. **Given** một từ hoặc khối nội dung dài vượt quá chiều rộng dòng hoặc chiều rộng ô bảng và bị chia thành nhiều đoạn, **When** tính toán bố cục và đối chiếu hạt giống, **Then** hệ thống đồng bộ cách gán định danh và số thứ tự giữa bước đối chiếu và bước bố cục, không để các đoạn sau bị tính lệch bước đếm.

---

### User Story 4 - Nghiêm ngặt hóa kiểu dữ liệu khóa hạt giống và khôi phục giao diện bền bỉ (Priority: P2)

Là người dùng và quản trị hệ thống, tôi muốn quy trình chuẩn hóa khóa ngẫu nhiên kiểm soát chặt chẽ kiểu dữ liệu đầu vào và quy trình khởi tạo giao diện người dùng có khả năng tự phục hồi trọn vẹn sau khi gặp lỗi, giúp phần mềm vận hành ổn định và không phát sinh lỗi tiềm ẩn.

**Why this priority**:
Việc tự động chuyển đổi các kiểu dữ liệu không xác định sang chuỗi ký tự có thể gây va chạm khóa ngoài ý muốn (ví dụ đối tượng có chuỗi biểu diễn giống nhau). Đồng thời, nếu việc đăng ký sự kiện giao diện bị đánh dấu thành công quá sớm khi chưa hoàn tất, một lỗi gián đoạn có thể khiến các nút bấm và bảng chức năng bị tê liệt vĩnh viễn trong phiên làm việc.

**Independent Test**:
- Kiểm thử truyền các kiểu dữ liệu ngoài danh mục cho phép vào bộ sinh khóa; hệ thống phải chủ động báo lỗi kiểu dữ liệu thay vì âm thầm ép kiểu.
- Giả lập một lỗi ném ra giữa chừng khi đang đăng ký bảng điều khiển giao diện, sau đó kích hoạt thử lại; hệ thống phải tiếp tục hoàn tất các sự kiện chưa đăng ký và đưa giao diện về trạng thái sẵn sàng.

**Acceptance Scenarios**:

1. **Given** một khóa hạt giống đầu vào chứa kiểu dữ liệu không nằm trong danh mục hỗ trợ chuẩn tắc (như kiểu tập hợp `set`, từ điển `dict`, hoặc đối tượng tùy ý), **When** thực hiện mã hóa chuẩn tắc, **Then** hệ thống từ chối ngay bằng lỗi kiểu dữ liệu rõ ràng, ngăn chặn việc ép chuỗi tùy tiện.
2. **Given** quá trình chuẩn bị các trình điều khiển giao diện bị gián đoạn ở bước trung gian, **When** người dùng bấm "Thử lại" hoặc hệ thống tự phục hồi, **Then** trạng thái sẵn sàng của giao diện không bị ghi nhận sai lệch, toàn bộ các sự kiện bảng điều khiển được gắn kết đầy đủ và người dùng sử dụng được mọi tính năng bình thường.

---

### Edge Cases

- **Mạng chập chờn / IndexedDB bị khóa**: Khi IndexedDB đang bị một tiến trình khác khóa hoặc phản hồi chậm, chu kỳ nạp kho có thời hạn chờ độc lập và trả về lỗi rõ ràng thay vì làm crash Web Worker nền.
- **Tiến trình gửi nhiều thông điệp READY liên tiếp**: Hệ thống chỉ xử lý tín hiệu READY đầu tiên của thế hệ hiện tại, bỏ qua các tín hiệu dư thừa để tránh kích hoạt lại chuỗi xử lý khởi tạo.
- **Danh sách lồng nhau nhiều cấp độ với các đoạn văn phức hợp**: Việc duyệt đệ quy khối danh sách xử lý an toàn các cấu trúc lồng sâu không giới hạn, không gây tràn ngăn xếp và giữ đúng thứ tự nội dung.
- **Token dài chứa ký tự đặc biệt bị cắt nhỏ**: Các đoạn cắt của token duy trì mối liên hệ với định danh token mẹ, đảm bảo việc xác định khoảng cách từ và biến thể không gây xung đột giữa các dòng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST tách biệt cơ chế giới hạn thời gian (timeout) của bước khởi tạo tiến trình nền khỏi bước nạp kho dữ liệu mẫu. Thời hạn chờ tín hiệu tiến trình sẵn sàng chỉ áp dụng cho quá trình tải và khởi động tiến trình, và MUST được dừng lại ngay khi nhận được tín hiệu sẵn sàng (READY).
- **FR-002**: Hệ thống MUST định danh mỗi chu kỳ khởi tạo tiến trình bằng một mã thế hệ (generation) duy nhất. Mọi phản hồi, tín hiệu lỗi, hoặc kết quả từ thế hệ cũ MUST bị từ chối và không được phép can thiệp vào tiến trình của thế hệ hiện tại.
- **FR-003**: Hệ thống MUST dẫn xuất mọi luồng sinh số ngẫu nhiên phục vụ lựa chọn biến thể mẫu chữ, độ rung nét (jitter), khoảng cách từ (gap) và khoảng cách nét dấu (dgap) từ ngữ cảnh chuẩn hóa (`SeedContext`), bắt buộc chứa định danh loại nội dung (`content_type`), định danh phần tử (`element_id`), số lần xuất hiện (`occurrence`), mục đích sử dụng (`purpose`) và chỉ số thứ tự phụ (`sub_index`).
- **FR-004**: Hệ thống MUST bảo đảm tính độc lập không gian tên giữa các phân loại nội dung khác nhau (văn bản đoạn văn `text`, ô bảng `cell`, ký hiệu `sym`, tiêu đề `heading`, công thức `math`). Cùng một từ và cùng một số lần xuất hiện khi nằm ở hai phân loại nội dung khác nhau MUST sinh ra các khóa ngẫu nhiên khác nhau.
- **FR-005**: Hệ thống MUST thực hiện đối chiếu hạt giống đệ quy trên toàn bộ cấu trúc tài liệu, bao gồm các khối danh sách (`ListBlock`), các mục danh sách (`items: list[list[Block]]`) và mọi đoạn văn bản lồng bên trong mục danh sách.
- **FR-006**: Hệ thống MUST duy trì quy tắc đồng bộ hóa bộ đếm token và số lần xuất hiện giữa bước đối chiếu tài liệu và bước tính toán bố cục, kể cả đối với các từ ngữ hoặc token dài bị chia thành nhiều đoạn (chunk) khi ngắt dòng.
- **FR-007**: Hệ thống MUST kiểm soát chặt chẽ kiểu dữ liệu đầu vào trong hàm mã hóa khóa chuẩn tắc. Hàm chỉ chấp nhận các kiểu dữ liệu được định nghĩa trong hợp đồng (`None`, `bool`, `int`, `float`, `str`, `bytes`, `SeedContext`, `tuple`, `list`); mọi kiểu dữ liệu không xác định MUST bị từ chối bằng lỗi kiểu dữ liệu (`TypeError`).
- **FR-008**: Hệ thống MUST chỉ xác nhận hoàn tất việc đăng ký sự kiện và giao diện người dùng sau khi tất cả các bước chuẩn bị giao diện bắt buộc đã hoàn tất thành công. Nếu xảy ra lỗi giữa chừng, trạng thái hoàn tất MUST không được ghi nhận để cho phép chu kỳ khôi phục kế tiếp thực hiện lại đầy đủ các bước cần thiết.

### Key Entities

- **SeedContext**: Ngữ cảnh hạt giống đại diện cho vị trí và thuộc tính cấu trúc của một phần tử trong tài liệu, gồm:
  - `content_type`: Phân loại nội dung ngữ cảnh (`text`, `cell`, `sym`, `heading`, `math`).
  - `element_id`: Chuỗi văn bản hoặc ký hiệu định danh cốt lõi.
  - `occurrence`: Thứ tự xuất hiện chuẩn tắc của phần tử trong phạm vi tài liệu.
  - `purpose`: Mục đích lấy mẫu ngẫu nhiên (`variant`, `jitter`, `wgap`, `dgap`, `baseline`).
  - `sub_index`: Chỉ số phụ (chỉ số ký tự trong từ, chỉ số nét, hoặc chỉ số phân đoạn).
- **WorkerLifecycleSession**: Thực thể quản lý chu kỳ sống của tiến trình nền Web Worker, gồm:
  - `generation`: Số nguyên tăng dần định danh phiên bản tiến trình nền.
  - `ready_state`: Trạng thái sẵn sàng của tiến trình (`initializing`, `ready`, `failed`).
  - `bank_loading_state`: Trạng thái nạp dữ liệu kho (`idle`, `loading`, `loaded`, `error`).
  - `timeout_handles`: Bộ quản lý các bộ đếm thời gian độc lập cho từng giai đoạn.
- **DocumentIR**: Mô hình đại diện cấu trúc tài liệu phân cấp hỗ trợ duyệt đệ quy toàn diện, bao gồm các khối đoạn văn, tiêu đề, bảng biểu, công thức toán và danh sách lồng nhau nhiều cấp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Quá trình khôi phục tiến trình nền đạt tỷ lệ thành công 100% trong các tình huống kho dữ liệu mẫu lớn mất hơn 10 giây để nạp từ bộ nhớ cục bộ, không xảy ra hiện tượng hủy ngang tiến trình nền khi đã nhận tín hiệu READY.
- **SC-002**: 100% các từ ngữ và ký hiệu xuất hiện cùng số thứ tự giữa văn bản thông thường và ô bảng tạo ra các chuỗi nét vẽ có phân bổ biến thể độc lập, độ trùng khớp khóa ngẫu nhiên giữa các phân loại nội dung bằng 0%.
- **SC-003**: 100% các nét vẽ của các mục danh sách cũ và các từ ngữ sau khi chia dòng giữ nguyên hình thái hình học (độ lệch chuẩn hóa <= 0.02 pt) khi người dùng chèn thêm mục mới vào đầu danh sách tài liệu.
- **SC-004**: 100% các kiểu dữ liệu không hợp lệ truyền vào bộ mã hóa chuẩn tắc bị từ chối với thông báo lỗi tường minh, không có bất kỳ chuyển đổi ép chuỗi ngầm định nào được thực thi.
- **SC-005**: Giao diện người dùng khôi phục đầy đủ 100% chức năng tương tác (các tab Viết, Kho mẫu, Dạy mẫu và thanh trạng thái) sau bất kỳ lần khôi phục tiến trình nào, không phát sinh lỗi rò rỉ listener hoặc listener bị bỏ sót.

## Assumptions

- Môi trường trình duyệt hỗ trợ đầy đủ các chuẩn Web Worker và IndexedDB cơ bản.
- Dung sai hình học <= 0.02 pt là ngưỡng chuẩn được xác lập trong các đặc tả ổn định hạt giống của dự án để đánh giá tính bất biến của nét chữ viết tay.
- Kho mẫu chữ cục bộ lưu trong IndexedDB là nguồn dữ liệu hợp lệ và có thể nạp lại bất kỳ lúc nào sau khi tiến trình nền sẵn sàng.
- Các quy tắc kiến trúc không phụ thuộc Tkinter/GUI và bảo toàn chuẩn đầu ra Golden Master của dự án được duy trì nghiêm ngặt.
