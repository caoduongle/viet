# Feature Specification: Chuyển sang sản phẩm chỉ có Web — Loại bỏ ứng dụng Desktop

**Feature Branch**: `038-web-only-remove-desktop`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "lập kế hoạch refactor; tôi chỉ muốn làm cho web; bỏ phần desktop đi"

## Bối cảnh

Sản phẩm hiện có hai giao diện cho người dùng cuối song song: **ứng dụng Desktop** (cửa sổ đồ hoạ chạy trên máy, có bản đóng gói thành tệp chạy độc lập) và **Web Client** (chạy hoàn toàn trong trình duyệt, lưu kho mẫu trong trình duyệt, cài được như ứng dụng). Web Client đã có đủ ba luồng chính: Viết chữ, Dạy chữ, Quản lý kho mẫu (kể cả sao lưu / nhập tệp kho).

Việc duy trì hai giao diện khiến mỗi tính năng phải làm hai lần (ví dụ tuỳ chọn "Kiểu chữ ổn định" ở feature 037 phải thêm vào cả hai), tăng chi phí kiểm thử (CI phải cài thư viện đồ hoạ và màn hình ảo chỉ để chạy test Desktop) và gây lệch hành vi giữa hai nơi. Feature này đưa sản phẩm về **một giao diện duy nhất là Web**, loại bỏ toàn bộ phần Desktop.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Người dùng dùng toàn bộ sản phẩm qua Web (Priority: P1)

Người dùng mở Web Client và thực hiện đầy đủ các việc trước đây làm trên Desktop: viết văn bản thành nét chữ tay, dạy chữ mới, quản lý kho mẫu, xuất tệp kết quả. Không còn hướng dẫn hay đường dẫn nào chỉ người dùng sang ứng dụng Desktop.

**Why this priority**: Đây là giá trị cốt lõi — sau khi bỏ Desktop, Web phải là nơi duy nhất và đầy đủ để dùng sản phẩm. Nếu thiếu luồng nào, người dùng bị mất chức năng.

**Independent Test**: Trên bản Web đã build, đi hết ba luồng Viết / Dạy / Kho mẫu bằng kịch bản kiểm thử trình duyệt tự động; tất cả hoàn tất mà không cần bất kỳ thành phần Desktop nào tồn tại trong kho mã.

**Acceptance Scenarios**:

1. **Given** kho mã đã gỡ bỏ phần Desktop, **When** build và mở Web Client, **Then** ba tab Viết chữ, Dạy chữ, Kho mẫu hoạt động đầy đủ như trước khi gỡ.
2. **Given** người dùng gõ văn bản có công thức toán và bảng, **When** xem trước và xuất tệp, **Then** kết quả giống hệt (từng byte với cùng hạt giống) kết quả trước khi gỡ Desktop.
3. **Given** người dùng đọc tài liệu hướng dẫn của dự án, **When** tìm cách sử dụng sản phẩm, **Then** tài liệu chỉ hướng dẫn dùng Web, không còn nhắc tới ứng dụng Desktop hay cách đóng gói tệp chạy Desktop.

---

### User Story 2 - Người dùng Desktop cũ chuyển kho mẫu sang Web (Priority: P1)

Người dùng đã từng dạy chữ trên Desktop có sẵn tệp kho mẫu cá nhân trên máy. Họ nhập tệp đó vào Web Client và tiếp tục dùng toàn bộ mẫu chữ đã dạy, không mất dữ liệu.

**Why this priority**: Bỏ Desktop không được làm mất công sức dạy chữ của người dùng hiện tại. Đây là điều kiện bắt buộc để việc gỡ bỏ an toàn.

**Independent Test**: Lấy một tệp kho mẫu do phiên bản Desktop tạo ra, nhập vào Web Client, kiểm tra số mẫu/ký tự hiển thị khớp với thống kê của tệp gốc và có thể viết chữ bằng kho đó.

**Acceptance Scenarios**:

1. **Given** một tệp kho mẫu tạo bởi phiên bản Desktop, **When** người dùng chọn "Nhập kho mẫu" trên Web, **Then** toàn bộ ký tự, chữ số, dấu câu, ký hiệu và hồ sơ cỡ tay được nạp đầy đủ, thống kê khớp với tệp gốc.
2. **Given** tài liệu hướng dẫn, **When** người dùng Desktop cũ đọc mục chuyển đổi, **Then** có hướng dẫn ngắn gọn cách tìm tệp kho trên máy và nhập vào Web.

---

### User Story 3 - Nhà phát triển duy trì một giao diện duy nhất (Priority: P2)

Nhà phát triển thêm hoặc sửa tính năng chỉ cần làm trên Web và lõi xử lý chung; quy trình kiểm thử tự động không còn cần môi trường đồ hoạ Desktop; kho mã không còn mã, test, cấu hình đóng gói hay tài liệu chỉ phục vụ Desktop hoặc dòng lệnh.

**Why this priority**: Giảm chi phí bảo trì là mục tiêu của refactor, nhưng chỉ có ý nghĩa khi Story 1 và 2 đã bảo đảm không mất chức năng.

**Independent Test**: Tìm kiếm toàn kho mã không còn tham chiếu tới thư viện giao diện Desktop, lối vào Desktop/CLI hay cấu hình đóng gói Desktop; quy trình CI chạy xanh mà không cài thư viện đồ hoạ hay màn hình ảo.

**Acceptance Scenarios**:

1. **Given** kho mã sau refactor, **When** tìm kiếm tham chiếu tới giao diện Desktop hoặc công cụ dòng lệnh (CLI), **Then** không còn kết quả nào ngoài lịch sử thay đổi (changelog) và các đặc tả cũ trong `specs/`.
2. **Given** quy trình CI, **When** chạy trên một nhánh mới, **Then** mọi bước kiểm thử xanh và không có bước nào cài thư viện đồ hoạ hoặc màn hình ảo.
3. **Given** bộ kiểm thử lõi xử lý chung (viết chữ, bố cục, toán, bảng, kho mẫu), **When** chạy sau refactor, **Then** toàn bộ vẫn xanh và các bài kiểm thử "golden master" giữ nguyên kết quả từng byte.

---

### Edge Cases

- Tệp kho mẫu Desktop cũ ở định dạng phiên bản schema cũ: Web phải nạp được (qua cơ chế nâng cấp schema sẵn có) hoặc báo lỗi rõ ràng, không làm hỏng kho hiện có trong trình duyệt.
- Tệp kho mẫu quá lớn so với dung lượng lưu trữ trình duyệt: Web báo lỗi dễ hiểu, không mất kho hiện có.
- Lõi xử lý chung có những đoạn mã từng chỉ được Desktop hoặc CLI gọi (ví dụ tìm kho mặc định cạnh tệp chạy đóng gói, theme sáng/tối Desktop): phải xác định rõ đoạn nào còn được Web dùng, đoạn nào trở thành mã chết cần gỡ.
- Chế độ Fidelity được bảo lưu phần lõi (`chuviettay/fidelity/`) để phục vụ đưa lên Web ở feature riêng sau này; feature này chỉ gỡ phần giao diện kết nối Fidelity trên Desktop và lối vào dòng lệnh.
- Thông điệp hướng dẫn đang in ra cho người dùng có nhắc tới lệnh CLI/giao diện Desktop (ví dụ gợi ý "chạy lệnh học tệp lưới") phải được rà soát để dọn dẹp hoặc chuyển hướng phù hợp với môi trường Web.
- Tuỳ chọn "Kiểu chữ ổn định" vừa thêm vào Desktop ở feature 037 sẽ bị gỡ cùng Desktop; Web đã có sẵn tuỳ chọn này.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Kho mã MUST NOT còn ứng dụng Desktop: không còn giao diện cửa sổ đồ hoạ, không còn lối vào khởi chạy Desktop, không còn lệnh cài đặt khởi chạy Desktop.
- **FR-002**: Kho mã MUST NOT còn cấu hình và kịch bản đóng gói tệp chạy Desktop độc lập, cùng các phụ thuộc chỉ phục vụ việc đóng gói đó.
- **FR-003**: Kho mã MUST NOT còn bài kiểm thử chỉ kiểm tra giao diện Desktop; những bài kiểm thử trộn lẫn (vừa kiểm tra lõi chung vừa kiểm tra Desktop) MUST được giữ lại phần kiểm tra lõi chung.
- **FR-004**: Quy trình CI MUST NOT cài thư viện đồ hoạ hay màn hình ảo chỉ để phục vụ Desktop, và MUST vẫn chạy đầy đủ lint, kiểm thử lõi, build Web, kiểm thử Web (đơn vị, cầu nối trình duyệt, đầu-cuối) và kiểm tra golden master trong môi trường Web.
- **FR-005**: Web Client MUST giữ nguyên 100% chức năng và hành vi hiện có (ba tab Viết chữ, Dạy chữ, Kho mẫu; nhập/xuất tệp kho; xuất kết quả; hạt giống; kiểu chữ ổn định); kết quả kết xuất với cùng đầu vào và hạt giống MUST trùng khớp từng byte với trước refactor.
- **FR-006**: Web Client MUST nạp được tệp kho mẫu do phiên bản Desktop tạo ra mà không mất mẫu nào; nếu không nạp được MUST báo lỗi rõ ràng bằng tiếng Việt và giữ nguyên kho hiện có.
- **FR-007**: Tài liệu dự án (README, hướng dẫn kiến trúc) MUST được cập nhật: bỏ mọi hướng dẫn cài đặt/chạy/đóng gói Desktop và dòng lệnh, mô tả Web là giao diện duy nhất, và có mục ngắn hướng dẫn người dùng Desktop cũ chuyển kho mẫu sang Web. Lịch sử thay đổi (changelog) MUST ghi nhận việc gỡ bỏ Desktop và CLI như một thay đổi phá vỡ tương thích.
- **FR-008**: Kho mã MUST NOT còn công cụ dòng lệnh: lối vào `hw_note.py`, mô-đun `chuviettay/cli.py`, cấu hình console script `hw-note` trong cấu hình dự án, và các bài kiểm thử chỉ phục vụ kiểm tra dòng lệnh MUST được gỡ bỏ hoàn toàn để Web Client trở thành giao diện sử dụng duy nhất của sản phẩm.
- **FR-009**: Mã nguồn lõi của chế độ "Khoá bố cục DOCX" (Fidelity) trong `chuviettay/fidelity/` MUST được bảo lưu nguyên vẹn để làm nền tảng đưa lên Web ở feature riêng tiếp theo; feature này chỉ gỡ bỏ phần giao diện kết nối tới Fidelity trên Desktop (`write_tab.py`) và lối vào dòng lệnh.
- **FR-010**: Mã trong lõi xử lý chung mà sau refactor không còn bất kỳ nơi nào sử dụng (không còn được Web Client hoặc mã lõi Fidelity bảo lưu sử dụng) MUST được gỡ bỏ; mã còn được dùng MUST giữ nguyên hành vi.
- **FR-011**: Các thông điệp hướng dẫn hiển thị cho người dùng MUST NOT nhắc tới giao diện hoặc lệnh đã bị gỡ bỏ.
- **FR-012**: Refactor MUST NOT thay đổi định dạng tệp kho mẫu, định dạng tệp kết quả, hay dữ liệu lưu trong trình duyệt của người dùng Web hiện tại.

### Key Entities

- **Tệp kho mẫu cá nhân**: Tệp chứa toàn bộ mẫu chữ người dùng đã dạy (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh, hồ sơ cỡ tay). Là cầu nối duy nhất để người dùng Desktop cũ mang dữ liệu sang Web.
- **Lõi xử lý chung**: Phần xử lý viết chữ, bố cục trang, toán, bảng, nhập tài liệu, mã nguồn lõi Fidelity, quản lý kho — phục vụ Web Client. Không thay đổi hành vi trong feature này.
- **Thành phần chỉ dành cho Desktop và dòng lệnh**: Giao diện cửa sổ đồ hoạ, lối vào khởi chạy Desktop/CLI, kịch bản & cấu hình đóng gói, theme Desktop, bài kiểm thử Desktop/CLI, bước CI cài môi trường đồ hoạ — đối tượng bị gỡ bỏ.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% luồng người dùng chính trên Web (Viết chữ, Dạy chữ, Kho mẫu, nhập/xuất kho, xuất kết quả) vượt qua kiểm thử đầu-cuối sau refactor.
- **SC-002**: 100% bài kiểm thử golden master (cả môi trường Python thường và môi trường Web) cho kết quả trùng khớp từng byte với trước refactor.
- **SC-003**: 0 tham chiếu tới giao diện Desktop, công cụ dòng lệnh (CLI), lối vào khởi chạy hay cấu hình đóng gói Desktop trong mã nguồn, cấu hình CI, kịch bản build và tài liệu hướng dẫn hiện hành (không tính changelog và `specs/` lịch sử).
- **SC-004**: Một tệp kho mẫu do Desktop tạo được nhập vào Web với 100% số mẫu được giữ nguyên.
- **SC-005**: Thời gian chạy CI trên mỗi nhánh giảm hoặc không tăng so với trước refactor, và không còn bước nào phụ thuộc môi trường đồ hoạ.
- **SC-006**: Mỗi tính năng mới sau refactor chỉ cần triển khai ở một giao diện người dùng duy nhất.

## Assumptions

- "Refactor" ở đây được hiểu là **gỡ bỏ Desktop và công cụ dòng lệnh, dọn mã chết phát sinh**, không phải tái cấu trúc lại lõi xử lý chung hay thiết kế lại giao diện Web. Lõi giữ nguyên hành vi.
- Web Client hiện tại đã đạt tương đương chức năng với Desktop cho ba luồng chính (Viết, Dạy, Kho mẫu) và đã có nhập/xuất tệp kho; chế độ Fidelity được bảo lưu phần mã lõi theo quyết định Q2: C để phát triển cho Web ở feature kế tiếp.
- Công cụ dòng lệnh (`hw_note.py`, `chuviettay/cli.py`, `hw-note`) được loại bỏ hoàn toàn theo quyết định Q1: B để tập trung 100% vào Web Client.
- Không cần duy trì bản phát hành Desktop cũ (không vá lỗi, không phát hành thêm). Người dùng cần Desktop có thể dùng bản phát hành cũ từ lịch sử phiên bản.
- Các đặc tả cũ trong `specs/` (kể cả 037) được giữ nguyên làm tài liệu lịch sử, không sửa lại.
- Dự án không có số liệu người dùng; mục chuyển đổi trong tài liệu là kênh thông báo duy nhất cho người dùng Desktop cũ.
- Việc triển khai Web hiện tại (trang tĩnh) giữ nguyên, không đổi nền tảng lưu trữ hay triển khai.
