# Feature Specification: Cách ly Lỗi Muộn Worker, Đồng bộ Ngữ cảnh Đo Độ rộng Số và Chống Dính Nét Dấu câu

**Feature Branch**: `049-worker-error-guard-punct-spacing`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Rà soát commit 95c21bfd: sửa guard generation trong onerror và onmessageerror để sự kiện lỗi đến muộn từ Worker cũ không tác động tới Worker mới; bổ sung đầy đủ các bài kiểm thử hồi quy cho sự kiện lỗi muộn và trạng thái trung gian đa phiên; đồng bộ ngữ cảnh seed (heading/cell/text) giữa measure_text_width() và kết xuất số; cải thiện khoảng cách quang học cho dấu câu, dấu phẩy thập phân và dấu ngoặc toán học đang bị dính nét."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cách ly sự kiện lỗi đến muộn từ tiến trình Worker thế hệ cũ (Priority: P1)

Khi một tiến trình Worker nền thế hệ cũ (Worker A) đã bị thay thế bởi một tiến trình Worker thế hệ mới (Worker B), mọi sự kiện lỗi phát sinh muộn từ Worker A (bao gồm cả lỗi thực thi `onerror` và lỗi giải mã thông điệp `onmessageerror`) phải bị chặn đứng ngay từ đầu trình xử lý sự kiện. Hệ thống tuyệt đối không được để sự kiện lỗi của tiến trình cũ làm hủy các yêu cầu đang chờ xử lý của tiến trình mới hoặc đẩy giao diện người dùng sang trạng thái báo lỗi hệ thống.

**Why this priority**: Đây là lỗ hổng cạnh tranh trực tiếp có thể làm gián đoạn phiên làm việc hợp lệ của người dùng ngay sau khi hệ thống vừa phục hồi thành công sang Worker mới.

**Independent Test**: Khởi tạo Worker A, sau đó cưỡng chế phục hồi sang Worker B và cho Worker B hoàn tất trạng thái sẵn sàng rồi gửi một yêu cầu công việc đang chờ trên Worker B. Tiếp theo, kích hoạt sự kiện `onerror` và `onmessageerror` muộn trên đối tượng Worker A cũ; xác nhận yêu cầu đang chờ trên Worker B vẫn hoàn tất thành công, không bị hủy bỏ, và giao diện vẫn giữ trạng thái sẵn sàng ổn định.

**Acceptance Scenarios**:

1. **Given** Worker thế hệ A đã bị thay thế bởi Worker thế hệ B đang hoạt động, **When** đối tượng Worker A phát sinh sự kiện `onerror` đến muộn, **Then** hệ thống chỉ đóng phiên phục hồi gắn với A (nếu chưa đóng) và bỏ qua sự kiện đó mà không kích hoạt quy trình xử lý lỗi nghiêm trọng toàn cục.
2. **Given** Worker thế hệ A đã bị thay thế bởi Worker thế hệ B đang có các yêu cầu công việc đang chờ, **When** đối tượng Worker A phát sinh sự kiện `onmessageerror` đến muộn, **Then** hàng đợi yêu cầu đang chờ của Worker B không bị ảnh hưởng và trạng thái hiển thị không chuyển sang trạng thái lỗi.
3. **Given** Worker hiện hành (thế hệ mới nhất) gặp sự kiện `onerror` hoặc `onmessageerror`, **When** trình xử lý sự kiện kiểm tra khớp thế hệ hiện tại, **Then** hệ thống xử lý lỗi bình thường, dọn dẹp bộ đếm thời gian, từ chối các yêu cầu đang chờ của thế hệ đó và mở khóa nút "Thử lại".

---

### User Story 2 - Bộ kiểm thử hồi quy toàn diện bảo vệ vòng đời đa phiên Worker trong CI (Priority: P1)

Nhóm phát triển và quy trình Tích hợp Liên tục (CI) cần bộ kiểm thử tự động kiểm chứng đầy đủ các kịch bản cạnh tranh đa phiên Worker, lỗi đến muộn từ thế hệ cũ, quá hạn khởi tạo sau tín hiệu sẵn sàng, và tính lũy đẳng của các trình lắng nghe sự kiện giao diện khi khởi tạo lại.

**Why this priority**: Đảm bảo mọi nhánh xử lý sự cố và phục hồi của Worker đều có bài kiểm thử tự động bảo vệ trong lệnh kiểm thử đơn vị chuẩn của CI, ngăn ngừa lỗi hồi quy trong các đợt phát triển tiếp theo.

**Independent Test**: Chạy lệnh kiểm thử đơn vị tiêu chuẩn `npm run test:unit`; xác nhận trình chạy kiểm thử phát hiện và thực thi thành công toàn bộ các bài kiểm thử hồi quy (bao gồm kiểm thử lỗi muộn `onerror`/`onmessageerror` từ thế hệ cũ, kiểm thử trạng thái trung gian khi phiên cũ kết thúc trong lúc phiên mới đang chờ, kiểm thử quá hạn sau `READY`, và kiểm thử thu hồi sự kiện giao diện).

**Acceptance Scenarios**:

1. **Given** bộ kiểm thử độ kiên cường của Worker, **When** chạy lệnh kiểm thử đơn vị trong CI, **Then** toàn bộ các ca kiểm thử về cách ly lỗi muộn từ Worker cũ, bảo vệ trạng thái trung gian đa phiên, quá hạn sau `READY` và thu hồi sự kiện giao diện đều được thực thi và vượt qua 100%.
2. **Given** kịch bản hai phiên phục hồi chồng lấn (phiên A kết thúc trong khi phiên B đang chờ), **When** bài kiểm thử kiểm tra trạng thái ngay sau khi phiên A kết thúc, **Then** bài kiểm thử xác nhận rõ ràng cờ đang phục hồi vẫn bật, tham chiếu tiến trình phục hồi vẫn trỏ tới phiên B, và nút "Thử lại" vẫn ở trạng thái khóa.

---

### User Story 3 - Đồng bộ ngữ cảnh hạt giống (Seed Context) khi đo độ rộng và kết xuất chuỗi số (Priority: P2)

Khi hệ thống bố cục văn bản tại các vùng có không gian tên hạt giống riêng biệt (như tiêu đề chương mục hoặc ô trong bảng biểu), hàm đo độ rộng văn bản (`measure_text_width`) dùng để quyết định ngắt dòng hoặc chia đoạn phải sử dụng cùng ngữ cảnh hạt giống với bước kết xuất nét chữ số thực tế.

**Why this priority**: Ngăn ngừa sai lệch độ rộng ước lượng và độ rộng thực tế khi kho mẫu có nhiều biến thể chữ số với bề rộng khác nhau, tránh hiện tượng ngắt dòng sớm hoặc tràn lề đối với các chuỗi số dài trong tiêu đề và bảng biểu.

**Independent Test**: Tạo kho mẫu chữ có nhiều biến thể chữ số với độ rộng khác nhau. Thực hiện đo độ rộng và kết xuất chuỗi số dài trong ngữ cảnh tiêu đề (`heading`) và ngữ cảnh ô bảng (`cell`) sát giới hạn chiều rộng dòng; xác nhận độ rộng đo trước và độ rộng kết xuất thực tế khớp nhau hoàn toàn (sai lệch <= 0.05 * xh) và quyết định chia dòng đồng nhất.

**Acceptance Scenarios**:

1. **Given** kho mẫu chữ có nhiều biến thể chữ số với bề rộng khác nhau và chế độ biến thể ổn định được bật, **When** đo độ rộng một chuỗi số kèm ngữ cảnh hạt giống (`heading`, `cell`, hoặc `text`), **Then** độ rộng trả về khớp với độ rộng khi kết xuất thực tế chuỗi số đó trong cùng ngữ cảnh (sai lệch <= 0.05 * xh).
2. **Given** một đoạn tiêu đề hoặc ô bảng chứa chuỗi số nằm sát giới hạn chiều rộng cho phép, **When** bộ bố cục đo độ rộng và thực hiện kết xuất, **Then** phép đo không làm biến đổi trạng thái bộ đếm nội bộ của bộ viết và kết quả ngắt dòng hoàn toàn nhất quán với bề rộng nét vẽ thực tế.

---

### User Story 4 - Tách rời quang học và chống dính nét cho dấu câu, dấu phẩy thập phân và dấu ngoặc toán học (Priority: P2)

Khi hiển thị các văn bản kết hợp lời giải và biểu thức toán học (như `ta có:`, `F_X(1)`, `F_X(4)`, `P(2 <= X <= 5)`, `0,39 - 0,19 = 0,20`), các dấu câu, dấu phẩy thập phân và dấu đóng/mở ngoặc phải có khoảng hở quang học rõ ràng so với chữ cái và chữ số liền kề, không bị dính sát hoặc đè nét lên nhau.

**Why this priority**: Nâng cao trực tiếp tính dễ đọc và thẩm mỹ tự nhiên của trang viết tay đối với các tài liệu toán học, thống kê và văn bản khoa học có mật độ số thập phân và ký hiệu ngoặc cao.

**Independent Test**: Kết xuất các chuỗi số thập phân (`0,39`, `0,19`, `0,97`), các biểu thức hàm số có ngoặc (`F_X(1)`, `F_X(4)`, `P(2 <= X <= 5)`) và từ có dấu câu đi kèm (`ta có:`); đo trực tiếp khoảng cách hình học giữa khung bao (bounding box) của các nét ký tự liền kề và xác nhận luôn tồn tại khe hở quang học dương rõ ràng, không chạm hoặc chồng lấn nét.

**Acceptance Scenarios**:

1. **Given** chuỗi số thập phân chứa dấu phẩy hoặc dấu chấm (ví dụ `0,39`, `0,19`, `0,97`) trong cả văn bản thường và biểu thức toán học, **When** kết xuất thành các nét vẽ, **Then** biên trái của dấu phẩy/chấm cách biên phải thực tế của chữ số đứng trước một khoảng hở quang học tối thiểu >= 0.10 * xh, và biên trái của chữ số tiếp theo cách biên phải thực tế của dấu phẩy/chấm tối thiểu >= 0.12 * xh.
2. **Given** biểu thức toán học có dấu ngoặc đơn bao quanh chữ số hoặc biến số (ví dụ `F_X(1)`, `F_X(3)`, `F_X(4)`, `P(2 <= X <= 5)`), **When** bố cục biểu thức toán học, **Then** giữa biên phải thực tế của nội dung bên trong và biên trái của dấu đóng ngoặc `)` (cũng như giữa dấu mở ngoặc `(` và nội dung bên trong) luôn có khoảng đệm quang học tối thiểu >= 0.10 * xh, ngăn chặn triệt để hiện tượng chữ số chạm vào dấu ngoặc.
3. **Given** từ hoặc cụm từ có dấu câu đi kèm phía sau (như `:`, `;`, `,`, `.`, `)`) hoặc dấu mở ngoặc phía trước, **When** ghép nét token, **Then** khoảng cách đặt dấu câu được tính từ biên phải thực tế cực đại của các nét đứng trước cộng với sàn khoảng hở quang học tối thiểu tính theo độ dày nét bút và chiều cao chữ, đảm bảo dấu câu không bao giờ dính vào thân chữ.

---

### Edge Cases

- **Sự kiện `onerror` và `onmessageerror` kích hoạt đồng thời trên Worker cũ**: Cả hai sự kiện đều bị chặn bởi điều kiện kiểm tra thế hệ ở đầu hàm, không gây tác dụng phụ kép.
- **Chuỗi số có nhiều dấu phân cách liên tiếp (ví dụ định dạng số dài `1.000.000,50`)**: Mỗi dấu chấm/phẩy đều được tính khoảng cách dựa trên biên phải thực tế của ký tự đứng ngay trước nó, không bị tích lũy sai số tọa độ.
- **Chữ số có nét vươn xa về bên phải (như chữ số `1`, `4`, `7`, `3`) đứng ngay trước dấu đóng ngoặc `)` hoặc dấu phẩy `,`**: Vị trí đặt dấu tiếp theo phải căn cứ vào cả độ rộng tiến bước và tọa độ biên phải cực đại (`max_x`) thực tế của nét chữ số vừa đặt để không bị đè nét.
- **Gọi `measure_text_width` không truyền ngữ cảnh hạt giống**: Hàm tự động sử dụng ngữ cảnh mặc định (`text`) và số thứ tự hiện tại của token để đảm bảo tương thích ngược 100% với mọi lời gọi hiện có.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Trình xử lý sự kiện `targetWorker.onerror` và `targetWorker.onmessageerror` MUST kiểm tra `generation !== workerGeneration` ngay tại đầu hàm; nếu thế hệ của đối tượng Worker không khớp với thế hệ hiện hành, hàm chỉ được phép đóng phiên phục hồi gắn liền với nó (`boundSession.resolve(false)`) và kết thúc ngay, tuyệt đối không được gọi `handleWorkerFatalError()`.
- **FR-002**: Bộ kiểm thử đơn vị JavaScript (`tests/js/worker_resilience.test.mjs`) MUST bao gồm các ca kiểm thử xác minh sự kiện `onerror` và `onmessageerror` đến muộn từ Worker thế hệ cũ không làm hủy các yêu cầu đang chờ của Worker thế hệ mới và không làm thay đổi trạng thái giao diện.
- **FR-003**: Hàm `Writer.measure_text_width(text, scale=1.0, context=None)` MUST hỗ trợ nhận tham số ngữ cảnh hạt giống tùy chọn (`context: SeedContext | None = None`) và chuyển tiếp ngữ cảnh này khi mô phỏng độ rộng chuỗi số qua `Writer.number()`, bảo đảm độ rộng đo được khớp với độ rộng kết xuất trong mọi không gian tên (`text`, `heading`, `cell`).
- **FR-004**: Bộ bố cục tài liệu (`DocumentLayoutEngine._layout_inlines`) MUST khởi tạo hoặc xác định ngữ cảnh hạt giống của phần tử văn bản trước khi gọi `measure_text_width` để phép đo độ rộng luôn sử dụng đúng `context_prefix` và số thứ tự xuất hiện (`occurrence`) của phần tử đó.
- **FR-005**: Trong `Writer.number()` và `MathLayoutEngine._layout_text()`, khi đặt dấu phân cách thập phân (`,` hoặc `.`) và chữ số theo sau, hệ thống MUST căn cứ vào biên phải thực tế (`max_x`) của nét đứng trước và đảm bảo khoảng hở quang học tối thiểu trước dấu phân cách `>= 0.12 * xh` và sau dấu phân cách `>= 0.14 * xh` (có tính đến độ dày nét bút).
- **FR-006**: Trong bố cục toán học (`MathLayoutEngine`), khoảng đệm quang học giữa dấu ngoặc mở/đóng (`(`, `)`, `[`, `]`) và phần tử liền kề bên trong (đặc biệt khi phần tử bên trong là chữ số hoặc biến số trong `RowNode` và `DelimitedNode`) MUST đạt tối thiểu `0.12 * xh` tính từ biên hình học thực tế của nét vẽ để ngăn chữ số chạm vào dấu ngoặc.
- **FR-007**: Trong `Writer.token()`, khi đặt các ký tự dấu mở đầu (`lead`) và dấu kết thúc (`trail`), hệ thống MUST cưỡng chế khoảng hở quang học tối thiểu giữa biên phải cực đại của nét trước và biên trái của nét sau dựa trên `max(0.85 * pen_w, 0.20 * xh)` (và giữa các dấu `trail` liên tiếp tối thiểu `max(0.60 * pen_w, 0.14 * xh)`).
- **FR-008**: Mọi cải tiến về khoảng cách dấu câu và chữ số MUST bảo toàn tính tương thích với bộ kiểm thử Golden Master hiện hành hoặc chỉ kích hoạt chuẩn xác trên các đường dẫn xử lý dấu phân cách số, toán học và khe hở bảo vệ nét mà không làm gãy bất kỳ bài kiểm thử hiện có nào trong hệ thống.

### Key Entities

- **Worker Generation Guard**: Cơ chế kiểm tra đối chiếu chỉ số thế hệ của tiến trình Worker tại điểm đầu vào của mọi luồng sự kiện (`onmessage`, `onerror`, `onmessageerror`) nhằm cô lập tuyệt đối các tiến trình đã bị thay thế.
- **Context-Aware Width Measurement**: Phép đo độ rộng hình học nhận biết ngữ cảnh hạt giống (`SeedContext`) của phần tử tài liệu mà không làm đột biến trạng thái bộ sinh số ngẫu nhiên hoặc bộ đếm của `Writer`.
- **Optical Punctuation Clearance**: Khoảng hở hình học thực tế giữa biên phải (`max_x`) của nét ký tự đứng trước và biên trái (`min_x`) của nét dấu câu/dấu ngoặc/chữ số đứng sau, có tính đến bề dày nét bút.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các sự kiện lỗi (`onerror`, `onmessageerror`, `ERROR`) phát sinh muộn từ tiến trình Worker thế hệ cũ bị loại bỏ an toàn mà không làm gián đoạn yêu cầu đang chạy của Worker thế hệ mới.
- **SC-002**: Sai lệch độ rộng giữa `measure_text_width` và kết xuất thực tế đối với chuỗi số trong mọi không gian tên (`text`, `heading`, `cell`) trên kho mẫu đa biến thể luôn đạt `<= 0.05 * xh`.
- **SC-003**: Khoảng hở khung bao (bounding-box gap) giữa chữ số và dấu phẩy thập phân trong chuỗi số thập phân (ví dụ `0,39`, `0,19`), cũng như giữa chữ số và dấu đóng ngoặc trong biểu thức toán (`F_X(1)`, `F_X(4)`), luôn đạt giá trị dương tối thiểu `>= 0.10 * xh` (không bao giờ âm hoặc bằng 0).
- **SC-004**: 100% bộ kiểm thử đơn vị JavaScript (`npm run test:unit`), bộ kiểm thử Python (`pytest`), và bộ kiểm thử Golden Master Pyodide (`npm run test:golden`) vượt qua sạch sẽ.

## Assumptions

- Kích thước chiều cao chữ cơ sở `xh` và độ dày nét bút `pen_w` luôn có sẵn trong cấu hình kho mẫu chữ (mặc định `xh = 7.94`, `pen_w = 1.41`).
- Các bài kiểm thử Golden Master hiện có sử dụng kho mẫu tổng hợp cố định (`tests/data/kho_mau_tong_hop.json.gz`), do đó các điều chỉnh khoảng cách cần được thiết kế cẩn trọng để không làm sai lệch băm SHA-256 của 8 kịch bản Golden Master chuẩn.
