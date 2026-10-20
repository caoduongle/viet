# Feature Specification: Đồng Bộ Kho Mẫu Và Kết Xuất Xem Trước Tab Viết Chữ (052-write-preview-bank-sync)

**Feature Branch**: `052-write-preview-bank-sync`  
**Created**: 2026-10-21  
**Status**: Draft  
**Input**: User description: "tôi gặp lỗi; rõ ràng đã đầy đủ ký tự rồi mà nó lại như này" kèm 3 ảnh chụp màn hình (Kho mẫu có 66 chữ cái / 192 ký tự đủ mẫu, Dạy chữ báo "Kho mẫu đã có đủ tất cả các ký tự trong nhóm này", nhưng Viết chữ báo toàn bộ ký tự `n, h, a, 0, i, t, 1...` thiếu mẫu và gạch đỏ toàn bộ trang).

---

## Bối cảnh và Vấn đề (Context & Problem Statement)

Khi người dùng mở ứng dụng Web Client (`chuviettay-web.onrender.com`):
1. **Tại Tab "Kho mẫu"**: Người dùng thấy kho cá nhân đã có đầy đủ 66 chữ cái (hoa + thường), 15 chữ số, 32 dấu câu, 74 ký hiệu, 5 dấu thanh (tổng cộng 192 ký tự với 695 mẫu nét).
2. **Tại Tab "Dạy chữ"**: Khi chọn nạp nhóm "Tất cả các ký tự (Đầy đủ)", ứng dụng hiển thị thông báo chính xác: *"Kho mẫu đã có đủ tất cả các ký tự trong nhóm này."*
3. **Tại Tab "Viết chữ"**: Khi soạn thảo hoặc tải lại trang có sẵn văn bản (ví dụ bài tập toán/văn bản tiếng Việt), toàn bộ các chữ cái và chữ số (`n (296)`, `h (223)`, `a (202)`, `0 (178)`, `i (170)`, `t (170)`, `1 (159)`...) đều bị liệt kê vào danh sách *"Từ thiếu mẫu trong kho (bấm để dạy ngay)"* và trên trang giấy xem trước chỉ hiển thị các nét gạch chân đứt đoạn màu đỏ (`missing-token-underline`) thay vì nét viết tay.

### Nguyên nhân cốt lõi (Root Cause)
- **Cuộc đua khởi tạo (Initialization Race Condition)**: Khi Web Worker Pyodide phát tín hiệu `READY`, hàm `onWorkerReady` khởi tạo Tab Viết (`initWriteTab`) và gọi render ngay lập tức (`triggerPreviewImmediate`) nếu textarea đã có nội dung (do trình duyệt tự động khôi phục form/bản nháp). Tại thời điểm này, tiến trình nạp dữ liệu kho mẫu từ IndexedDB (`load_bank`) **chưa hoàn thành**. Pyodide Worker thực hiện kết xuất trên kho rỗng mặc định ban đầu (`/tmp/active_bank.json.gz`, 0 ký tự), dẫn đến 100% ký tự bị đánh dấu là thiếu mẫu.
- **Thiếu cơ chế kích hoạt kết xuất lại khi nạp xong kho**: Khi tiến trình nạp kho hoàn tất (`sendWorkerMessage("load_bank", ...)`), hệ thống chỉ cập nhật Tab Kho mẫu (`refreshBankView`) và Tab Dạy chữ (`__teachController.refresh`), nhưng **hoàn toàn không thông báo hay kích hoạt kết xuất lại** cho Tab Viết chữ.
- **Chuyển tab không làm mới trạng thái**: Hàm chuyển tab (`switchTab`) khi chuyển sang Tab Viết (`targetTab === "write"`) không kiểm tra hay làm mới lại kết xuất nếu kho mẫu đã thay đổi hoặc vừa được nạp.
- **Bằng chứng xác thực thực tế (User Feedback)**: Người dùng ghi nhận khi vào modal "Tùy chọn", đổi giá trị `seed` hoặc bấm nút đổi hạt giống ngẫu nhiên rồi áp dụng thì trang giấy lập tức hiển thị bình thường, không còn gạch đỏ. Điều này khẳng định hạt giống (seed) không có lỗi về mặt toán học hay tạo nét, mà chính sự kiện đổi seed đã vô tình gọi lệnh `triggerPreviewImmediate()` vào thời điểm kho mẫu trong Worker đã nạp xong từ trước đó, giúp giải phóng Tab Viết khỏi bản kết xuất kho rỗng bị đóng băng.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự động đồng bộ và hiển thị đúng nét chữ khi mở trang hoặc tải lại (Priority: P1)

Người dùng mở lại trang web hoặc làm mới trình duyệt khi ô soạn thảo đã có sẵn văn bản. Sau khi ứng dụng và kho mẫu nạp xong từ bộ nhớ trình duyệt (IndexedDB), bản xem trước phải tự động hiển thị đầy đủ nét viết tay của các ký tự đã có trong kho mẫu mà không bị kẹt ở trạng thái "thiếu mẫu".

**Why this priority**: Đây là luồng trải nghiệm trực quan quan trọng nhất (MVP), giải quyết trực tiếp tình trạng người dùng rõ ràng đã có đủ mẫu chữ nhưng màn hình lại báo thiếu toàn bộ và gạch đỏ.

**Independent Test**:
- Nạp sẵn một kho mẫu có đủ chữ cái vào IndexedDB, đặt sẵn văn bản tiếng Việt trong ô soạn thảo, tải lại trang web.
- Xác nhận bản xem trước hiển thị nét viết tay đầy đủ, danh sách "Từ thiếu mẫu trong kho" rỗng (hoặc chỉ chứa các ký tự thực sự chưa dạy), không có chip báo thiếu sai cho các chữ cái đã học.

**Acceptance Scenarios**:
1. **Given** ô soạn thảo có văn bản và kho mẫu đã lưu trong IndexedDB có đầy đủ các ký tự đó,  
   **When** người dùng tải lại trang web hoặc mở ứng dụng,  
   **Then** sau khi kho mẫu nạp xong vào Worker, bản xem trước tự động cập nhật kết xuất nét viết tay chuẩn và không hiển thị chip báo thiếu sai.
2. **Given** văn bản được kết xuất lần đầu trong khi kho mẫu đang nạp,  
   **When** lệnh nạp kho mẫu (`load_bank`) hoàn tất thành công,  
   **Then** hệ thống tự động kích hoạt kết xuất lại (re-render) nội dung soạn thảo với kho mẫu thực tế.

---

### User Story 2 - Tự động cập nhật kết xuất khi chuyển đổi hoặc nạp kho mẫu mới (Priority: P2)

Khi người dùng đổi hồ sơ kho mẫu, nạp file sao lưu `.json.gz`, hoặc vừa hoàn thành nạp file lưới ô tập viết `.xopp`, Tab Viết chữ phải ngay lập tức nhận biết kho mẫu mới và cập nhật lại bản xem trước trang giấy.

**Why this priority**: Đảm bảo tính nhất quán dữ liệu xuyên suốt giữa các tab và các hành động quản trị kho mẫu mà không yêu cầu người dùng phải gõ thêm ký tự thừa để kích hoạt lại render.

**Independent Test**:
- Đang ở Tab Viết với một số từ bị thiếu mẫu, chuyển sang Tab Kho mẫu nạp file `.json.gz` bổ sung, rồi quay lại Tab Viết.
- Xác minh bản xem trước tự động cập nhật và các từ vừa được bổ sung mẫu nét hiển thị bình thường.

**Acceptance Scenarios**:
1. **Given** người dùng đang có văn bản trong Tab Viết chữ,  
   **When** người dùng nạp file kho `.json.gz` mới hoặc hoàn thành nạp lưới `.xopp` ở tab khác,  
   **Then** Tab Viết chữ tự động kết xuất lại với kho mẫu mới cập nhật.
2. **Given** người dùng chuyển từ Tab Kho mẫu hoặc Tab Dạy chữ về Tab Viết chữ (`switchTab("write")`),  
   **When** kho mẫu đã có sự thay đổi hoặc chưa từng được kết xuất với kho mẫu hiện hành,  
   **Then** giao diện Tab Viết chữ tự động đồng bộ và hiển thị bản xem trước chính xác nhất.

---

### User Story 3 - Xử lý mượt mà khi phục hồi Web Worker (Priority: P3)

Khi Web Worker bị khởi động lại do sự cố hoặc phục hồi sau lỗi (`recoverWorker`), trạng thái kho mẫu và bản xem trước của Tab Viết chữ phải được khôi phục toàn vẹn mà không gây lỗi hoặc treo trạng thái thiếu mẫu vĩnh viễn.

**Why this priority**: Bảo vệ ứng dụng trước các sự cố ngắt quãng nền của trình duyệt (memory pressure / crash), duy trì tính ổn định liên tục.

**Independent Test**:
- Gọi hàm phục hồi Worker nhân tạo trong khi đang có văn bản hiển thị trên trang giấy, kiểm tra sau khi Worker mới sẵn sàng và kho mẫu nạp lại, trang giấy vẫn hiển thị đúng nét chữ.

**Acceptance Scenarios**:
1. **Given** Worker nền bị khởi động lại,  
   **When** Worker mới sẵn sàng và nạp lại kho mẫu thành công từ IndexedDB,  
   **Then** bản xem trước Tab Viết chữ tự động được dựng lại chuẩn xác theo dữ liệu kho vừa khôi phục.

---

### Edge Cases

- **EC-001**: Ô soạn thảo hoàn toàn rỗng khi khởi động -> Không phát sinh yêu cầu kết xuất thừa gây lãng phí tài nguyên.
- **EC-002**: Người dùng gõ phím liên tục trong lúc kho mẫu đang nạp từ IndexedDB -> Cơ chế debounce và hàng đợi chờ (`hasPendingRequest`) phải bảo đảm lượt kết xuất cuối cùng luôn sử dụng kho mẫu đã nạp xong, không bị ghi đè bởi kết quả cũ.
- **EC-003**: Nạp kho mẫu bị lỗi hoặc kho mẫu rỗng thực sự -> Hiển thị cảnh báo rõ ràng, danh sách từ thiếu phản ánh đúng trạng thái kho rỗng thay vì gây treo giao diện.
- **EC-004**: Người dùng chuyển qua lại giữa các tab với tốc độ cao -> Không gây xung đột luồng hoặc gửi dồn dập các yêu cầu kết xuất trùng lặp.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST đồng bộ chu trình nạp kho mẫu (`load_bank`) với chu trình khởi tạo Tab Viết chữ, bảo đảm không hiển thị kết quả kết xuất từ kho mẫu rỗng khi kho mẫu thực tế của người dùng đang tồn tại trong IndexedDB.
- **FR-002**: Khi tiến trình `load_bank` hoàn tất thành công trong `onWorkerReady`, hệ thống MUST kiểm tra và tự động kích hoạt kết xuất lại văn bản trong Tab Viết chữ (`triggerPreviewImmediate`) nếu ô soạn thảo có nội dung.
- **FR-003**: Khi người dùng chuyển sang Tab Viết chữ (`switchTab("write")`), hệ thống MUST kiểm tra xem bản xem trước đã được dựng với phiên bản kho mẫu hiện hành hay chưa; nếu chưa, MUST thực hiện kết xuất cập nhật ngay lập tức.
- **FR-004**: Khi người dùng nạp kho mẫu mới (qua file `.json.gz` hoặc nhập lưới `.xopp`) hoặc khi nhận tín hiệu đồng bộ đa tab (`BANK_SYNCHRONIZED`), hệ thống MUST tự động làm mới bản xem trước Tab Viết chữ song song với việc cập nhật Tab Kho mẫu và Tab Dạy chữ.
- **FR-005**: Danh sách "Từ thiếu mẫu trong kho" (`missing-tokens-box`) và các đường gạch chân cảnh báo trên trang giấy MUST phản ánh trung thực dữ liệu từ kho mẫu đang hoạt động, loại bỏ hoàn toàn các cảnh báo thiếu mẫu giả tạo (false positives) đối với các ký tự đã được học trong kho.
- **FR-006**: Trạng thái tải của bộ kết xuất (Rendering Indicator) MUST hiển thị đúng tiến trình khi hệ thống tự động kết xuất lại sau khi nạp kho.

---

### Key Entities

- **Active Bank State**: Trạng thái kho mẫu đang được nạp trong bộ nhớ Worker (bao gồm phiên bản/timestamp và số lượng mẫu nét).
- **Write Preview State**: Trạng thái xem trước hiện tại của Tab Viết chữ (bao gồm tài liệu đã dàn trang, danh sách toạ độ từ thiếu `missing_token_boxes`, và danh sách từ thiếu đã xếp hạng `missing_sorted`).
- **Profile Bank Data**: Dữ liệu nén `.json.gz` của kho mẫu được lưu trữ bền vững trong IndexedDB và gắn với `active_profile_id`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các ký tự đã có mẫu trong kho mẫu người dùng (bao gồm chữ cái, chữ số, dấu câu, ký hiệu) không bị xuất hiện trong danh sách "Từ thiếu mẫu trong kho" khi mở hoặc tải lại trang web.
- **SC-002**: Thời gian từ khi kho mẫu nạp xong từ IndexedDB đến khi bản xem trước Tab Viết chữ được cập nhật nét viết tay hoàn tất không vượt quá 500ms đối với tài liệu thông thường (< 5 trang).
- **SC-003**: Loại bỏ hoàn toàn tình trạng lệch pha dữ liệu (data desynchronization) giữa Tab Kho mẫu (báo đủ ký tự), Tab Dạy chữ (báo không còn ký tự thiếu), và Tab Viết chữ (báo thiếu mẫu nét).
- **SC-004**: Tất cả các kịch bản kiểm thử tích hợp (integration tests) và kiểm thử giao diện tự động (Playwright/Node tests) liên quan đến vòng đời Worker và hiển thị trang giấy đều vượt qua (100% pass).

---

## Assumptions

- Kho mẫu của người dùng đã được lưu hợp lệ trong IndexedDB dưới hồ sơ hoạt động (`active_profile_id`).
- Trình duyệt hỗ trợ Web Worker, WebAssembly và IndexedDB tiêu chuẩn.
- Các ký tự xuất hiện trong văn bản là các ký tự Unicode chuẩn (NFC) tương thích với bảng danh mục ký tự `char_catalog`.
