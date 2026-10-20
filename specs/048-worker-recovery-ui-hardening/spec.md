# Feature Specification: Củng cố Phục hồi Worker, Quản lý Vòng đời Giao diện và Đo đạc Chữ số Đa biến thể

**Feature Branch**: `048-worker-recovery-ui-hardening`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Rà soát commit d3c93b4 và kiểm toán toàn diện hệ thống: sửa race condition khi phục hồi Worker trong app.js, tích hợp test worker resilience vào CI, thu hồi triệt để listener và observer khi khởi tạo hoặc hủy giao diện, dọn dẹp vật lý worker khi timeout sau READY, khử suy biến hình học chữ số và đồng bộ đo lường chữ số trong kho mẫu đa biến thể."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phiên phục hồi Worker độc lập và triệt tiêu xung đột trạng thái (Priority: P1)

Khi xảy ra sự cố nền (như Pyodide gặp lỗi nghiêm trọng hoặc quá hạn), người dùng có thể kích hoạt phục hồi Worker (tự động hoặc bấm nút "Thử lại"). Nếu nhiều yêu cầu phục hồi xuất hiện liên tiếp hoặc phiên mới được ép chạy (forced restart) trong khi phiên cũ chưa hoàn tất, hệ thống phải đảm bảo phiên cũ kết thúc không được can thiệp hay xóa bỏ trạng thái đang phục hồi của phiên mới.

**Why this priority**: Tránh tình trạng giao diện báo đã sẵn sàng hoặc cho phép người dùng thao tác tiếp trong khi Worker mới vẫn đang trong giai đoạn khởi tạo, dẫn đến gửi tác vụ vào Worker chưa sẵn sàng hoặc tạo thêm các phiên Worker dư thừa chạy song song gây nghẽn bộ nhớ.

**Independent Test**: Kích hoạt phiên phục hồi thứ nhất (giả lập khởi tạo chậm), sau đó ngay lập tức kích hoạt phiên phục hồi thứ hai với cờ cưỡng chế (force: true). Khi phiên thứ nhất hoàn tất thất bại hoặc bị hủy, xác nhận trạng thái phục hồi (`isRecovering`) vẫn tiếp tục duy trì giá trị đang chạy, nút "Thử lại" vẫn ở trạng thái vô hiệu hóa (disabled), và chỉ khi phiên thứ hai hoàn tất thì toàn bộ trạng thái phục hồi mới được cập nhật về trạng thái ổn định.

**Acceptance Scenarios**:

1. **Given** một phiên phục hồi Worker A đang chạy, **When** một phiên phục hồi cưỡng chế B được khởi tạo, **Then** phiên B trở thành phiên phục hồi hiện hành duy nhất và thế hệ Worker được tách biệt.
2. **Given** phiên A kết thúc sau khi phiên B đã bắt đầu, **When** khối dọn dẹp của phiên A thực thi, **Then** phiên A không được đặt lại cờ trạng thái phục hồi toàn cục (`isRecovering`), không được giải phóng Promise phục hồi đang theo dõi (`recoveryPromise`), và không được mở khóa nút "Thử lại" trên màn hình.
3. **Given** phiên phục hồi hiện hành B kết thúc (thành công hoặc thất bại), **When** khối dọn dẹp của phiên B thực thi, **Then** hệ thống cập nhật chính xác cờ phục hồi, trạng thái hiển thị của nút "Thử lại", và giải phóng Promise phiên hiện hành.

---

### User Story 2 - Kiểm thử tự động tính kiên cường của Worker trong quy trình CI (Priority: P1)

Nhóm phát triển và hệ thống Tích hợp Liên tục (CI) cần bộ kiểm thử tính kiên cường của Worker (xử lý timeout, hủy tác vụ treo, khởi động lại, phục hồi phiên) được tự động thực thi trong lệnh kiểm thử chuẩn của dự án (`npm run test:unit`), không để sót bất kỳ kịch bản nào ở ngoài quy trình kiểm tra tự động.

**Why this priority**: Đảm bảo không xảy ra hiện tượng "lọt lưới" lỗi Worker khi kiểm tra tự động trước mỗi lần tích hợp hoặc phát hành mã nguồn, duy trì nguyên tắc của Hiến chương dự án về kiểm thử hồi quy 100% tự động.

**Independent Test**: Chạy lệnh `npm run test:unit` từ môi trường dòng lệnh sạch; toàn bộ các ca kiểm thử tính kiên cường của Worker (bao gồm phục hồi đa phiên, timeout sau READY, cách ly thế hệ, và tính lũy đẳng của listener) đều được phát hiện, thực thi và vượt qua với kết quả thành công.

**Acceptance Scenarios**:

1. **Given** tệp kiểm thử độ kiên cường của Worker, **When** thực thi `npm run test:unit`, **Then** trình chạy kiểm thử phải tự động nạp và thực thi toàn bộ các ca kiểm thử độ kiên cường của Worker mà không cần chỉ định đường dẫn tệp thủ công.
2. **Given** cấu hình kịch bản kiểm thử trong dự án, **When** quét cây thư mục kiểm thử JavaScript, **Then** không còn tệp kiểm thử Worker bị cô lập nằm ngoài vùng quét kiểm thử đơn vị của CI.

---

### User Story 3 - Thu hồi hoàn toàn sự kiện và quan sát viên khi giao diện làm mới hoặc hủy (Priority: P2)

Khi người dùng chuyển qua lại giữa các tab chức năng (Soạn thảo, Dạy mẫu, Kho mẫu) hoặc khi hệ thống khởi tạo lại các thành phần giao diện sau một sự cố Worker, toàn bộ các trình lắng nghe sự kiện (event listeners) và quan sát viên kích thước (ResizeObserver) đã gắn trước đó phải được dọn dẹp hoặc gỡ bỏ thông qua cơ chế hủy đồng bộ (AbortSignal / teardown).

**Why this priority**: Ngăn ngừa rò rỉ bộ nhớ, tránh tình trạng nhiều callback cùng lắng nghe một sự kiện bàn phím/chuột dẫn đến nhân đôi thao tác lưu mẫu chữ, gọi API nhiều lần, hoặc xung đột DOM khi hiển thị xem trước trang giấy.

**Independent Test**: Khởi tạo giao diện tab Dạy mẫu chữ và thanh điều hướng xem trước trang giấy kèm tín hiệu hủy (AbortSignal). Kích hoạt tín hiệu hủy và khởi tạo lại; xác minh trên các phần tử DOM mục tiêu chỉ có đúng một trình xử lý sự kiện hoạt động và quan sát viên khung hiển thị cũ đã được ngắt kết nối (`disconnect`).

**Acceptance Scenarios**:

1. **Given** bộ điều khiển tab Dạy mẫu chữ (`TeachController`), **When** phương thức khởi tạo được gọi kèm tín hiệu hủy hoặc gọi khởi tạo lại, **Then** toàn bộ các sự kiện nút bấm và sự kiện phím tắt toàn cục gắn trên tài liệu (`document`) phải được thu hồi sạch sẽ nếu phiên bị hủy.
2. **Given** bộ điều khiển hiển thị tài liệu trang giấy, **When** quan sát viên thay đổi kích thước khung xem (`ResizeObserver`) được thiết lập, **Then** quan sát viên phải tự động ngắt kết nối (`disconnect`) khi nhận tín hiệu hủy hoặc khi khởi tạo lại khung điều hướng.
3. **Given** các nút thông báo dung lượng và nhắc nhở sao lưu trong giao diện, **When** hàm gắn sự kiện được gọi lặp lại nhiều lần, **Then** không xuất hiện trình xử lý sự kiện trùng lặp trên các phần tử nút tương ứng.

---

### User Story 4 - Chấm dứt vật lý tiến trình Worker khi khởi tạo giao diện sau READY bị quá hạn (Priority: P2)

Khi Worker nền đã hoàn tất nạp mã nguồn và gửi tín hiệu sẵn sàng (`READY`), hệ thống chuyển sang bước khởi tạo giao diện và nạp lại kho mẫu chữ (`onWorkerReady`). Nếu bước khởi tạo giao diện này bị treo hoặc vượt quá ngưỡng thời gian chờ cho phép, hệ thống phải chấm dứt vật lý tiến trình Worker ngầm, tăng chỉ số thế hệ và hiển thị thông báo lỗi rõ ràng.

**Why this priority**: Tránh hiện tượng tạo ra tiến trình "Worker ma" (zombie worker) vẫn ngầm chạy và tiêu tốn CPU/bộ nhớ hoặc bất ngờ gửi thông điệp muộn làm sai lệch trạng thái của phiên Worker thay thế tiếp theo.

**Independent Test**: Giả lập kịch bản Worker gửi tín hiệu `READY` nhưng bước khởi tạo giao diện bị treo quá thời gian quy định (`initTimeout`). Kiểm tra đối tượng Worker cũ đã bị gọi lệnh chấm dứt vật lý (`terminate()`), thế hệ Worker (`workerGeneration`) được tăng lên, và thông điệp lỗi quá hạn được hiển thị cho người dùng.

**Acceptance Scenarios**:

1. **Given** Worker phát tín hiệu `READY`, **When** quá trình khởi tạo giao diện và kho mẫu sau tín hiệu `READY` vượt quá thời gian chờ, **Then** hệ thống kích hoạt thông báo lỗi nghiêm trọng, chấm dứt vật lý đối tượng Worker đó và tăng chỉ số thế hệ Worker.
2. **Given** Worker cũ đã bị chấm dứt do quá hạn sau `READY`, **When** có bất kỳ thông điệp nào từ Worker cũ đến muộn, **Then** thông điệp đó bị loại bỏ hoàn toàn và không tác động đến trạng thái hệ thống.

---

### User Story 5 - Khử suy biến hình học chữ số và đồng bộ đo độ rộng số trong kho mẫu đa biến thể (Priority: P2)

Khi người dùng sử dụng kho mẫu chữ viết tay có chứa nhiều biến thể mẫu cho mỗi chữ số, hoặc khi gặp các mẫu chữ số có kích thước hình học bất thường (chiều cao cực nhỏ xấp xỉ 0 hoặc tỷ lệ co giãn vượt ngưỡng thông thường), hệ thống phải chuẩn hóa an toàn mà không phát sinh lỗi số học và đảm bảo hàm tính độ rộng văn bản (`measure_text_width`) phản ánh trung thực độ rộng thực tế khi hiển thị của chuỗi số với sai lệch không vượt quá ngưỡng thị giác cho phép (<= 0.05 * xh).

**Why this priority**: Bảo đảm bố cục dòng, căn lề đoạn văn và ngắt dòng trong văn bản chứa công thức toán/số học luôn chính xác tuyệt đối, không gây hiện tượng chữ số bị tràn lề hoặc co rúm hình học.

**Independent Test**:
1. Cung cấp mẫu chữ số suy biến (chiều cao bằng 0 hoặc các điểm nét trùng nhau); bộ vẽ phải trả về kích thước dự phòng hợp lệ và không gây lỗi chia cho 0 hay hệ số co giãn vô hạn.
2. So sánh độ rộng tính bởi `measure_text_width` và độ rộng trả về bởi `Writer.number()` trên một chuỗi số chứa số âm, số thập phân và dấu phân cách với kho mẫu đa biến thể; độ chênh lệch tuyệt đối giữa hai giá trị phải luôn nhỏ hơn hoặc bằng 0.05 * chiều cao chữ xh.

**Acceptance Scenarios**:

1. **Given** mẫu chữ số có chiều cao hình học cực nhỏ (<= 1e-3), **When** thực hiện chuẩn hóa mẫu chữ số, **Then** hệ thống áp dụng kích thước dự phòng an toàn, duy trì hệ số co giãn hữu hạn và không ném ngoại lệ.
2. **Given** kho mẫu chữ có nhiều biến thể chữ số và các biến thể khoảng cách khác nhau, **When** tính toán độ rộng của chuỗi số dạng số nguyên, số âm và số thập phân, **Then** sai lệch giữa độ rộng đo trước và độ rộng thực tế sau khi tạo nét không vượt quá 0.05 * xh.
3. **Given** các bài kiểm tra bố cục khoảng cách chữ số, **When** xác minh khoảng cách quang học, **Then** việc kiểm tra phải dựa trên khung chữ nhật bao thực tế (bounding box) của từng ký tự sau khi kết xuất.

---

### Edge Cases

- **Hai yêu cầu phục hồi Worker đồng thời**: Yêu cầu thứ nhất bị ghi đè ngay lập tức bởi yêu cầu thứ hai; phiên thứ nhất được giải quyết với kết quả `false` và không làm gián đoạn tiến trình khởi tạo của phiên thứ hai.
- **Worker bị crash ngay trước khi gửi READY**: Sự kiện lỗi `onerror` hoặc `onmessageerror` được kích hoạt; hệ thống dọn dẹp bộ đếm thời gian bắt tay, mở khóa nút thử lại và hiển thị cảnh báo lỗi chi tiết.
- **Trình duyệt không hỗ trợ ResizeObserver**: Giao diện tự động lùi về sử dụng sự kiện `window.resize` với cơ chế quản lý hủy sự kiện tương ứng.
- **Mẫu chữ số bị trống hoàn toàn (rỗng nét)**: Bộ chuẩn hóa trả về danh sách nét rỗng và độ rộng tiến bước dự phòng theo chiều cao chữ tiêu chuẩn.
- **Ký tự dấu trừ trong số âm đứng đầu dòng**: Khoảng cách giữa dấu trừ và chữ số theo sau được thu hẹp tự nhiên theo tỷ lệ quy định mà không làm lệch trục tọa độ toán học.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST chỉ cho phép phiên phục hồi Worker hiện hành (`activeRecoverySession`) được phép giải phóng cờ trạng thái phục hồi (`isRecovering`), xóa tham chiếu Promise phục hồi (`recoveryPromise`), xóa bộ đếm thời gian bắt tay (`clearHandshakeTimer`), và thay đổi trạng thái khả dụng của nút thử lại trên giao diện người dùng.
- **FR-002**: Hệ thống MUST giải quyết Promise của phiên phục hồi cũ với giá trị `false` ngay khi một phiên phục hồi mới được khởi chạy cưỡng chế.
- **FR-003**: Cấu hình kiểm thử đơn vị của dự án MUST quét và thực thi đầy đủ toàn bộ các tệp kiểm thử độ kiên cường của Worker khi chạy lệnh kiểm thử tiêu chuẩn `npm run test:unit`.
- **FR-004**: Không được tồn tại các tệp kiểm thử mã nguồn JavaScript trùng lặp hoặc bị bỏ quên bên ngoài cấu trúc thư mục được giám sát bởi CI.
- **FR-005**: Bộ điều khiển tab Dạy mẫu chữ (`TeachController`) MUST hỗ trợ cơ chế dọn dẹp các trình lắng nghe sự kiện DOM và sự kiện phím bấm trên tài liệu khi bị hủy hoặc khởi tạo lại thông qua `AbortSignal` hoặc phương thức hủy tường minh.
- **FR-006**: Trình quan sát kích thước vùng xem trước (`ResizeObserver`) trong tab Soạn thảo MUST được ngắt kết nối (`disconnect()`) khi giao diện điều hướng được khởi tạo lại hoặc khi nhận tín hiệu hủy sự kiện.
- **FR-007**: Các hàm đăng ký sự kiện cho nút sao lưu và thông báo dung lượng lưu trữ MUST có tính lũy đẳng (idempotent), không gắn thêm trình xử lý sự kiện trùng lặp khi được gọi nhiều lần.
- **FR-008**: Khi bước nạp giao diện và kho mẫu sau tín hiệu `READY` (`onWorkerReady`) bị vượt quá thời gian chờ quy định (`initTimeout`), hệ thống MUST gọi lệnh chấm dứt vật lý tiến trình Worker hiện hành (`worker.terminate()`), tăng chỉ số thế hệ Worker (`workerGeneration`), đặt tham chiếu Worker về `null`, và thông báo lỗi cho người dùng.
- **FR-009**: Các thông điệp gửi đến từ một tiến trình Worker thuộc thế hệ cũ hơn thế hệ Worker hiện hành MUST bị loại bỏ hoàn toàn mà không làm biến đổi trạng thái của phiên làm việc hiện tại.
- **FR-010**: Thuật toán chuẩn hóa mẫu chữ số (`_normalize_digit_sample`) MUST xử lý an toàn các trường hợp mẫu bị suy biến hình học (chiều cao mẫu <= 1e-3 hoặc không có tọa độ hợp lệ), bảo đảm không phát sinh phép chia cho 0 hoặc giá trị co giãn không xác định.
- **FR-011**: Hàm đo độ rộng văn bản (`measure_text_width`) đối với chuỗi số MUST đồng bộ logic tính bước tiến ký tự và khoảng cách chữ số với hàm kết xuất chữ số (`Writer.number()`) sao cho sai lệch độ rộng giữa hai hàm không vượt quá 0.05 * xh trên các kho mẫu đơn và đa biến thể.
- **FR-012**: Các bài kiểm thử đơn vị về kiểu chữ (typography) số học MUST khẳng định độ chính xác dựa trên tọa độ hình học thực tế (bounding boxes) của các nét vẽ sau khi kết xuất.

### Key Entities

- **Recovery Session**: Đại diện cho một phiên nỗ lực phục hồi tiến trình Worker; bao gồm định danh thế hệ Worker mục tiêu, trạng thái đã giải quyết (`isResolved`), bộ đếm thời gian kiểm soát (`timer`), và hàm hoàn tất (`resolve`).
- **Worker Generation**: Số nguyên đơn điệu tăng dùng để gắn thẻ phiên bản của tiến trình Worker nhằm loại bỏ hoàn toàn các thông điệp đến muộn từ các tiến trình cũ đã bị hủy bỏ.
- **UI Lifecycle Controller**: Quản lý vòng đời gắn và gỡ các sự kiện tương tác người dùng, phím tắt toàn cục và quan sát viên bố cục DOM đảm bảo khả năng tái thiết lập không để lại tác dụng phụ.
- **Digit Normalization Spec**: Tập hợp các tham số hình học (độ dịch trục, hệ số co giãn ngang dọc, đường cơ sở, đường trục giữa) dùng để chuẩn hóa các nét vẽ chữ số về tỷ lệ hài hòa với chiều cao chữ viết tay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các phiên phục hồi Worker bị thay thế giữa chừng không để lại bất kỳ tác động làm sai lệch trạng thái hiển thị của phiên phục hồi mới đang chạy.
- **SC-002**: Lệnh kiểm thử `npm run test:unit` thực thi thành công 100% các ca kiểm thử độ kiên cường của Worker trên môi trường CI mà không cần can thiệp thủ công.
- **SC-003**: Số lượng trình xử lý sự kiện tồn đọng sau n chu kỳ khởi tạo lại giao diện (với n >= 3) trên mỗi phần tử DOM mục tiêu luôn bằng đúng 1 (không phát sinh nhân bản).
- **SC-004**: Không có bất kỳ tiến trình Worker ma nào tiếp tục sống sót trong bộ nhớ sau khi xảy ra tình huống quá thời gian chờ (timeout) ở bất kỳ giai đoạn nào (bắt tay hoặc sau `READY`).
- **SC-005**: Sai lệch độ rộng giữa phép đo trước (`measure_text_width`) và phép tạo nét thực tế (`number`) đối với mọi định dạng số học luôn nằm trong biên độ an toàn <= 0.05 * xh.
- **SC-006**: Toàn bộ 1265+ bài kiểm thử Python và 45+ bài kiểm thử JavaScript của dự án đều vượt qua sạch sẽ (100% pass rate).

## Assumptions

- Môi trường trình duyệt mục tiêu hỗ trợ chuẩn `AbortController` và `AbortSignal` (đã là chuẩn trên mọi trình duyệt hiện đại).
- Cấu hình CI sử dụng Node.js với cờ kiểm thử `--test` tích hợp sẵn.
- Kích thước chiều cao chữ viết tay cơ sở xh luôn là một số thực dương hữu hạn (mặc định 7.94 mm).
- Trạng thái kho mẫu tổng hợp chuẩn (`tests/data/kho_mau_tong_hop.json.gz`) được giữ nguyên vẹn để bảo toàn tính bất biến băm SHA-256 của các bài kiểm thử Golden Master hiện có.
