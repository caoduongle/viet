# Feature Specification: 046-worker-seed-typography-hardening

**Feature Branch**: `046-worker-seed-typography-hardening`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Rà soát toàn diện và xử lý triệt để 5 nhóm vấn đề kỹ thuật sau commit ec448cc: (1) Phục hồi Worker có thể treo vô thời hạn do lệch thế hệ (workerGeneration); (2) Gắn trùng event listeners khi khởi tạo UI thất bại rồi thử lại; (3) Cách ly namespace seed cho Heading, chuyển tiếp occurrence của MathBlock trong ô bảng, và phản ánh sub_index vào định danh hình học của chunk; (4) Xử lý mẫu chữ số cực đoan, đồng bộ khoảng cách giữa hàm đo độ rộng và kết xuất thực tế, thu hẹp khoảng cách sau dấu âm ở đầu số; (5) Củng cố CI và bổ sung kiểm thử tự động toàn diện cho khả năng phục hồi Worker, tính toàn vẹn của seed và bố cục số học."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phục hồi Worker an toàn và triệt tiêu nguy cơ treo vô thời hạn (Priority: P1)

Khi Web Worker gặp sự cố, bị quá thời gian chờ (timeout) hoặc khi người dùng nhấp nút "Thử lại" (Retry), luồng phục hồi Worker (`recoverWorker`) phải diễn ra tin cậy, chuyển giao thế hệ Worker (`generation`) rõ ràng. Mọi trạng thái chờ bắt tay (handshake) và khởi tạo giao diện sau tín hiệu `READY` đều phải được bảo vệ bằng bộ đếm thời gian (timeout) và gắn liền với thế hệ Worker tương ứng; nếu thế hệ thay đổi trong quá trình xử lý bất đồng bộ, Promise chờ phải luôn được giải quyết (resolve/reject) dứt điểm đúng một lần, đảm bảo cờ `isRecovering` luôn được giải phóng trong khối `finally` và nút "Thử lại" không bao giờ bị vô hiệu hóa vĩnh viễn.

**Why this priority**: Lỗi treo vô thời hạn trong luồng phục hồi khiến toàn bộ ứng dụng web bị đóng băng ở trạng thái "Đang tải", người dùng không thể thao tác, xuất file hay thử lại, buộc phải tải lại trang và có nguy cơ mất dữ liệu phiên làm việc.

**Independent Test**: Kích hoạt `recoverWorker()`, mô phỏng tình huống tín hiệu `READY` được gửi nhưng thế hệ `workerGeneration` bị thay đổi (bumped) ngay trong khi `onWorkerReady()` đang chờ thao tác bất đồng bộ; xác nhận Promise phục hồi luôn kết thúc, cờ `isRecovering` được đặt lại về `false` và nút "Thử lại" khả dụng trở lại.

**Acceptance Scenarios**:

1. **Given** Worker gửi tín hiệu `READY` và bắt đầu khởi tạo giao diện (`onWorkerReady`), **When** thế hệ Worker bị thay đổi trước khi quá trình hoàn tất (ví dụ do người dùng nhấp thử lại tiếp hoặc có timeout mới), **Then** Promise chờ của thế hệ cũ được giải quyết dứt điểm (hủy bỏ an toàn), không bị bỏ lơ (leak promise), khối `finally` được thực thi và `isRecovering` trở về `false`.
2. **Given** Worker khởi động lại thành công, **When** giai đoạn khởi tạo giao diện (`onWorkerReady`) bị treo hoặc kéo dài quá hạn định mức, **Then** bộ đếm thời gian chờ bảo vệ toàn bộ giai đoạn phục hồi kích hoạt, báo lỗi và giải phóng cờ phục hồi thay vì treo mãi mãi.
3. **Given** một chuỗi nhiều yêu cầu phục hồi Worker diễn ra liên tiếp (`rapid retries`), **Then** chỉ thế hệ Worker mới nhất được phép cập nhật giao diện và các tài nguyên của thế hệ cũ được thu hồi sạch sẽ.

---

### User Story 2 - Idempotent UI Event Listeners và dọn dẹp bộ lắng nghe khi khởi tạo thất bại (Priority: P1)

Khi người dùng mở ứng dụng hoặc khi hệ thống thử lại khởi tạo giao diện sau một lần gặp lỗi (ví dụ nạp controller thất bại), việc gắn các bộ lắng nghe sự kiện (event listeners) trên các tab (Kho mẫu `bank.js`, Viết chữ `write.js`, Dạy chữ `teach.js`) phải có tính lũy suy (idempotent) hoặc hỗ trợ cơ chế hủy/dọn dẹp (cleanup/abortable). Một thao tác của người dùng (như bấm nút Xuất file, Thêm mẫu, Xóa mẫu) chỉ kích hoạt đúng một lần xử lý duy nhất, không bao giờ bị nhân bản hành động do gắn trùng listener.

**Why this priority**: Gắn trùng listener khi khởi tạo lại làm cho một cú nhấp chuột có thể gửi hàng loạt yêu cầu cùng lúc đến Worker, gây render lặp, tạo nhiều bản xuất file trùng lặp hoặc làm hỏng dữ liệu kho chữ.

**Independent Test**: Gọi hàm khởi tạo giao diện với một lỗi giả lập ở bước cuối (khiến lần khởi tạo đầu thất bại), sau đó gọi lại hàm khởi tạo thành công; mô phỏng sự kiện nhấp chuột trên các nút chức năng chính và xác minh mỗi hành động chỉ được thực thi chính xác 1 lần.

**Acceptance Scenarios**:

1. **Given** quá trình khởi tạo giao diện thất bại ở giữa chừng (ví dụ `TeachController.init()` ném lỗi), **When** hệ thống chạy lại chu trình khởi tạo khi phục hồi, **Then** các listener đã gắn từ các module trước đó (`bank.js`, `write.js`) được dọn dẹp sạch hoặc kiểm tra cờ gắn trùng để không có bất kỳ phần tử DOM nào bị gắn listener nhiều hơn một lần.
2. **Given** người dùng nhấp nút "Viết chữ" hoặc "Tải kho mẫu" sau khi ứng dụng trải qua một chu kỳ khởi tạo lại, **Then** yêu cầu gửi đến Worker hoặc bộ nhớ chỉ được kích hoạt đúng 1 lần.

---

### User Story 3 - Cô lập Seed Namespace cho Heading, Table MathBlock và Chunk Sub-index (Priority: P2)

Hệ thống kết xuất và thuật toán đối chiếu seed (`align_document_seeds`) phải bảo đảm tính ổn định và cô lập tuyệt đối của các biến thể chữ viết tay ngẫu nhiên:
- Tiêu đề (`Heading`) phải sở hữu namespace seed riêng biệt (`heading`), không bị gộp chung vào namespace văn bản thường (`text`). Việc thêm hoặc sửa nội dung trong đoạn văn không được làm thay đổi nét chữ của tiêu đề.
- Khối công thức toán lồng trong ô bảng (`MathBlock` trong `TableCell`) khi chuyển đổi thành dạng nội dòng để hiển thị phải chuyển tiếp đầy đủ thứ tự xuất hiện (`occurrence`) và định danh ổn định (`stable_id`).
- Các phân đoạn từ (`chunks`) sinh ra từ cùng một token dài hoặc lặp lại phải được phân biệt bằng định danh kết xuất/hình học riêng có chứa chỉ số phân đoạn (`sub_index`), bảo đảm khoảng cách từ và hình học nét không bị xung đột ngữ cảnh.

**Why this priority**: Đảm bảo cam kết "chỉnh sửa cục bộ không làm biến dạng chữ toàn tài liệu" (seed stability), tránh hiện tượng sửa một đoạn văn bản ở cuối trang làm toàn bộ tiêu đề ở đầu trang bị đổi nét chữ.

**Independent Test**:
- Kết xuất tài liệu gồm một `Heading` và một `Paragraph` có chứa các từ trùng nhau; chèn thêm một đoạn văn mới vào giữa; xác nhận nét vẽ và biến thể của `Heading` giữ nguyên 100%.
- Đặt một công thức toán vào trong ô bảng; chèn thêm nội dung vào ô phía trước; xác nhận công thức toán trong bảng không bị đổi nét.
- Kết xuất một token dài có các chunk con trùng nhau; xác nhận các chunk con nhận ngữ cảnh hình học độc lập và khoảng cách hiển thị tự nhiên.

**Acceptance Scenarios**:

1. **Given** tài liệu có chứa tiêu đề (`Heading`) và đoạn văn (`Paragraph`), **When** thuật toán `align_document_seeds` phân tích và động cơ bố cục kết xuất, **Then** tiêu đề sử dụng tiền tố ngữ cảnh `heading`, đoạn văn sử dụng tiền tố `text`; việc chèn từ mới vào đoạn văn không làm thay đổi thứ tự `occurrence` của từ trong tiêu đề.
2. **Given** một ô bảng chứa khối công thức toán `MathBlock`, **When** chuyển đổi thành phần tử nội dòng để đo đạc và bố cục trong ô, **Then** trường `occurrence` và `stable_id` từ khối gốc được bảo toàn trọn vẹn sang phần tử đích.
3. **Given** một từ dài bị ngắt thành nhiều chunk, **When** áp dụng seed hình học và tính khoảng cách từ, **Then** mỗi chunk được định danh phân biệt theo vị trí của nó (`sub_index`), không dùng chung một định danh hình học bị trùng lặp.

---

### User Story 4 - Chuẩn hóa hình học số học bền vững, thu hẹp khoảng cách dấu âm và đồng bộ đo lường (Priority: P2)

Hệ thống kết xuất chữ số, số âm và số thập phân phải có độ tin cậy hình học cao trong mọi trường hợp:
- Mẫu chữ số dị biệt cực đoan (kích thước quá nhỏ hoặc quá lớn nằm ngoài biên co giãn an toàn) phải được xử lý theo chính sách rõ ràng: chuẩn hóa tỷ lệ về kích thước mục tiêu hoặc kích hoạt nét vector dự phòng chuẩn mực, chấm dứt hiện tượng chữ số bị tí hon hoặc khổng lồ.
- Hàm ước lượng độ rộng văn bản trước khi ngắt dòng (`measure_text_width`) và hàm kết xuất số thực tế (`number`) phải đồng bộ 100% về quy tắc tính khoảng hở trước/sau dấu thập phân (`,` và `.`), ngăn ngừa việc ước lượng sai lệch dẫn đến ngắt dòng số thập phân oan uổng.
- Khoảng cách sau dấu âm (`-`) đứng ở đầu số âm (như `-25`, `-0,39`) phải được thu hẹp tự nhiên, đồng bộ với khoảng cách chặt chẽ giữa các chữ số, không để dấu trừ bị tách rời xa chữ số đầu tiên.

**Why this priority**: Mang lại chất lượng hiển thị số học hoàn hảo cho cả các kho mẫu chữ dị biệt, chống ngắt dòng lỗi số thập phân và giúp các số âm hiển thị liền khối, tự nhiên.

**Independent Test**:
- Nạp mẫu chữ số tổng hợp cực nhỏ (`0.10 * xh`) và cực lớn (`4.0 * xh`); kết xuất và xác nhận chiều cao hiển thị cuối cùng nằm trong khung quy chuẩn.
- Đo độ rộng chuỗi số `0,39` và `0,0278` qua `measure_text_width` và so sánh với độ rộng thực tế từ `number()`; xác nhận sai số giữa phép đo và kết xuất `<= 0.05 * xh`.
- Kết xuất `-25` và `-0,39`; đo khoảng cách ngang giữa mép phải dấu trừ và mép trái chữ số đầu tiên; xác nhận khoảng cách nằm trong khoảng tự nhiên `0.05 * xh .. 0.12 * xh`.

**Acceptance Scenarios**:

1. **Given** một kho chữ có mẫu chữ số dị biệt cực đoan (chiều cao thô `< 0.35 * xh` hoặc `> 2.5 * xh`), **When** chữ số được kết xuất, **Then** hệ thống tự động co giãn về đúng chiều cao chuẩn `1.20 * xh` (hoặc thay thế bằng mẫu vector chuẩn tương ứng), không để lọt chữ số lệch chuẩn ra trang viết.
2. **Given** các chuỗi số thập phân (`0,39`, `0,0278`, `194,5`), **When** tính toán độ rộng để ngắt dòng, **Then** độ rộng ước lượng khớp chính xác với độ rộng thực tế của nét vẽ sau kết xuất, không làm số thập phân bị nhảy dòng bất thường.
3. **Given** một số âm có dấu trừ ở đầu (`-25`, `-0,39`), **When** kết xuất nét, **Then** khoảng cách ngang từ dấu trừ đến chữ số đầu tiên được thu hẹp tương ứng với khoảng cách liên kết nội bộ số học, không bị áp khoảng cách mặc định như từ riêng lẻ.

---

### User Story 5 - Xác thực CI, kiểm thử Resilience, Seed Integrity và Typography (Priority: P2)

Toàn bộ hệ thống kiểm thử tự động (CI và local test suite) phải được mở rộng để bao phủ toàn bộ các kịch bản biên: phục hồi Worker đa thế hệ, kiểm tra chống nhân bản event listeners, tính cô lập seed giữa các loại khối, và kiểm thử đo đạc hình học chữ số/phân số/dấu âm. Toàn bộ 100% bài kiểm tra phải chạy thành công và ổn định trong cả môi trường Node.js / Pyodide và CPython.

**Why this priority**: Bảo đảm chất lượng mã nguồn lâu dài, ngăn ngừa lỗi hồi quy và mang lại độ tin cậy tuyệt đối trước khi phát hành.

**Independent Test**: Chạy `pytest` toàn bộ dự án, chạy test suite JavaScript/Worker bằng Node.js và xác nhận 100% test pass không có cảnh báo hay lỗi tiềm ẩn.

**Acceptance Scenarios**:

1. **Given** bộ test suite được kích hoạt trên CI hoặc máy nội bộ, **When** chạy các test case phục hồi Worker, chống gắn trùng listener, seed isolation và typography, **Then** toàn bộ các bài kiểm tra đều vượt qua thành công (zero regression).

---

### Edge Cases

- **Worker bị crash liên tục trong vòng lặp thử lại**: Hệ thống phải ngăn chặn việc kích hoạt đệ quy vô hạn của `recoverWorker` bằng cờ kiểm soát và giới hạn thời gian chờ.
- **Thế hệ Worker thay đổi nhiều lần trong mili-giây**: Khi người dùng click nút Retry liên tiếp nhiều lần, các thế hệ trung gian phải bị hủy ngay lập tức mà không để lại timer rác hay promise treo.
- **Kho mẫu có mẫu chữ số rỗng hoặc chỉ có 1 điểm tọa độ**: Hệ thống phải phát hiện mẫu suy biến và chuyển sang mẫu nét vector dự phòng thay vì chia cho 0 hoặc tính sai bounding box.
- **Dấu trừ kép hoặc dấu trừ toán học trong công thức**: Phân biệt rõ dấu trừ số âm trong văn bản thường (`-25`) và toán tử trừ hai ngôi trong công thức toán (`a - b`) để áp dụng đúng khoảng cách tương ứng.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống Web Client PHẢI quản lý trạng thái hoàn tất của luồng phục hồi Worker (`recoverWorker`) theo từng thế hệ (`workerGeneration`), bảo đảm mọi Promise chờ được giải quyết đúng một lần trong mọi tình huống (thành công, lỗi, hết giờ, hoặc thế hệ bị thay thế).
- **FR-002**: Bộ đếm thời gian chờ phục hồi Worker PHẢI bao bọc và bảo vệ cả giai đoạn bắt tay ban đầu (`READY`) lẫn giai đoạn nạp kho/khởi tạo giao diện sau đó (`onWorkerReady`), giải phóng cờ `isRecovering` và khôi phục nút "Thử lại" khi quá hạn.
- **FR-003**: Quá trình khởi tạo các bộ lắng nghe sự kiện DOM (`initBankTab`, `initWriteTab`, `initTeachTab`) PHẢI có tính lũy suy (idempotent) hoặc được quản lý bởi cơ chế có thể dọn dẹp (như `AbortController` / cờ đánh dấu gắn kết), bảo đảm không có event listener nào bị gắn trùng lặp khi khởi tạo lại sau thất bại.
- **FR-004**: Thuật toán phân bổ seed (`align_document_seeds`) và bộ bố cục (`engine.py`) PHẢI phân tách không gian tên (`namespace`) của `Heading` (`heading`) độc lập hoàn toàn với `Paragraph` (`text`), bảo đảm biến thể chữ viết tay của tiêu đề không bị ảnh hưởng bởi thay đổi nội dung trong đoạn văn.
- **FR-005**: Khi chuyển đổi khối công thức `MathBlock` trong ô bảng thành phần tử nội dòng (`MathInline`), hệ thống PHẢI chuyển tiếp đầy đủ trường `occurrence` và `stable_id` từ khối gốc để bảo toàn biến thể công thức toán trong bảng.
- **FR-006**: Hệ thống PHẢI phản ánh chỉ số phân đoạn (`sub_index`) vào định danh kết xuất/hình học của các chunk trong token dài hoặc token lặp lại, bảo đảm các chunk khác vị trí nhận được ngữ cảnh hình học độc lập.
- **FR-007**: Hàm chuẩn hóa chữ số `_normalize_digit_sample` PHẢI áp dụng chính sách co giãn thích ứng trực tiếp cho các mẫu chữ số dị biệt cực đoan (kích thước `< 0.35 * xh` hoặc `> 2.5 * xh`), bảo đảm chiều cao hiển thị luôn đạt chuẩn lining figures `1.20 * xh` (`[1.05 * xh, 1.30 * xh]`) và bảo vệ an toàn trước mẫu rỗng.
- **FR-008**: Hàm đo độ rộng văn bản trước khi ngắt dòng `measure_text_width` PHẢI sử dụng cùng công thức và tham số khoảng cách trước/sau dấu thập phân (`,` và `.`) như hàm kết xuất nét thực tế `number()`, triệt tiêu sai số ước lượng độ rộng của số thập phân.
- **FR-009**: Hệ thống PHẢI thu hẹp khoảng cách ngang giữa dấu trừ (`-`) và chữ số đầu tiên trong các số âm (`-25`, `-0,39`) về dải hẹp tự nhiên (`0.05 * xh .. 0.12 * xh`), thay vì áp dụng khoảng cách dgap đầy đủ của hai chữ số thông thường.
- **FR-010**: Hệ thống PHẢI bổ sung bộ kiểm thử tự động kiểm chứng khả năng phục hồi Worker khi generation thay đổi, kiểm tra chống trùng listener UI, kiểm tra tính cô lập seed giữa Heading và Paragraph, kiểm tra chuyển tiếp seed trong ô bảng, và đo đạc khoảng cách dấu âm cùng mẫu số cực đoan.

---

### Key Entities

- **WorkerLifecycleController**: Đối tượng/cơ chế quản lý vòng đời và thế hệ của Web Worker, kiểm soát các giai đoạn bắt tay, khởi tạo giao diện và xử lý hủy bỏ/hết giờ một cách tất định.
- **IdempotentListenerRegistry**: Cơ chế đăng ký bộ lắng nghe sự kiện DOM cho phép kiểm tra trạng thái gắn kết hoặc hủy bỏ toàn bộ listener thông qua bộ điều khiển hủy (`AbortController`).
- **IsolatedSeedNamespace**: Không gian tên hạt giống phân cấp phân định rõ ràng giữa các loại phần tử (`text`, `heading`, `cell`, `sym`, `math_inline`, `math_block`), ngăn ngừa ô nhiễm chéo seed.
- **RobustDigitGeometryModel**: Mô hình hình học chuẩn hóa chữ số chịu lỗi cao, xử lý ổn định cả mẫu chữ thông thường lẫn mẫu dị biệt cực đoan và thống nhất khoảng cách giữa bước đo đạc và bước kết xuất.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các tình huống phục hồi Worker bị gián đoạn hoặc đổi thế hệ giữa chừng đều giải phóng cờ phục hồi và đưa nút "Thử lại" về trạng thái sẵn sàng trong thời gian không quá 10 giây (thời gian timeout định mức), không có bất kỳ trường hợp nào bị kẹt vô thời hạn.
- **SC-002**: Sau 3 chu kỳ khởi tạo giao diện bị lỗi liên tiếp rồi khởi tạo thành công, số lượng listener gắn trên các nút hành động chính (Xuất file, Thêm mẫu, Xóa mẫu) trên mỗi phần tử DOM bằng đúng 1 (không xảy ra kích hoạt trùng lặp).
- **SC-003**: 100% các biến thể chữ viết tay trong `Heading` giữ nguyên không đổi khi người dùng chèn thêm, xóa hoặc chỉnh sửa nội dung văn bản trong các khối `Paragraph` có chứa từ trùng lặp.
- **SC-004**: Độ lệch giữa độ rộng ước lượng từ `measure_text_width()` và độ rộng thực tế từ `number()` cho các số thập phân (`0,39`, `0,0278`, `194,5`) không vượt quá `0.05 * xh`, loại bỏ hoàn toàn hiện tượng ngắt dòng oan cho số thập phân.
- **SC-005**: Khoảng cách ngang giữa mép phải dấu trừ và mép trái chữ số đầu tiên trong các số âm (`-25`, `-0,39`) đạt dải tự nhiên `0.05 * xh .. 0.12 * xh`, giảm tối thiểu 40% khoảng hở so với phiên bản trước.
- **SC-006**: 100% các bài kiểm thử tự động mới và toàn bộ bài kiểm thử hiện có (CI test suite) đều vượt qua thành công, đạt 0 regression.

---

## Assumptions

- Trình duyệt hiện đại hỗ trợ `AbortController` và `addEventListener(..., { signal })` để quản lý dọn dẹp event listener một cách nhẹ nhàng, chuẩn Web API tiêu chuẩn.
- Các mẫu chữ số cực đoan trong kho mẫu được chuẩn hóa bằng cơ chế co giãn tỷ lệ thích ứng trực tiếp trên mẫu thực tế của người dùng để bảo toàn phong cách viết tay nguyên bản mà vẫn đảm bảo tính mỹ thuật và khả năng đọc của trang văn bản.
- Tiêu đề (`Heading`) có ngữ nghĩa văn bản độc lập với thân bài (`Paragraph`), do đó việc phân tách không gian tên seed phản ánh đúng cấu trúc tài liệu ngữ nghĩa.
