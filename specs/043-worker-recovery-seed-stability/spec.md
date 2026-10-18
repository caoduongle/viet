# Feature Specification: Khôi phục Worker Tin cậy và Ổn định Ngữ cảnh Seed Kết xuất (Worker Recovery & Render Seed Pipeline Hardening)

**Feature Branch**: `043-worker-recovery-seed-stability`

**Created**: 2026-10-18

**Status**: Approved (Refined via Engineering Review)

**Input**: User description: "1. Kết quả rà soát commit mới nhất 14ae860: Khôi phục Worker có thể báo thành công giả và treo vô thời hạn khi gặp lỗi hoặc không nhận được tín hiệu READY. 2. Chuẩn hóa định danh và ngữ cảnh seed: Thống nhất định danh phần tử, giải quyết bất biến khi chèn nội dung, khoảng cách từ theo vị trí ổn định, ngữ cảnh riêng cho công thức và bảng, chuẩn hóa mã hóa khóa derive_seed() an toàn, và kiểm thử bảo toàn golden master."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Khôi phục Bộ xử lý Nền (Worker) Tương tác & Đáng tin cậy (Priority: P1) 🎯 MVP

Khi người dùng gặp sự cố kỹ thuật trong bộ xử lý nền (Web Worker bị sập, hết bộ nhớ, timeout khi xử lý văn bản lớn hoặc không gửi được dữ liệu), giao diện hiển thị thông báo lỗi rõ ràng cùng nút "Thử lại". Khi người dùng nhấn "Thử lại", hệ thống tiến hành khởi động lại bộ xử lý mới, khôi phục lại kho mẫu chữ đã lưu trữ, và chỉ xác nhận thành công (cũng như ẩn nút "Thử lại") sau khi bộ xử lý mới đã gửi tín hiệu sẵn sàng VÀ nạp kho mẫu thành công. Nếu quá trình khôi phục gặp lỗi ở bất kỳ bước nào hoặc quá thời gian chờ tối đa (10 giây), hệ thống giữ nguyên nút "Thử lại" và cảnh báo người dùng thay vì báo thành công giả mạo.

**Why this priority**: Ngăn chặn tình trạng ứng dụng bị đóng băng âm thầm (silent failure) hoặc hiển thị thành công giả tạo khiến người dùng mất dữ liệu hay thao tác vô vọng. Đây là yêu cầu tiên quyết cho sự tin cậy của ứng dụng web offline-first.

**Independent Test**: Giả lập các nhánh lỗi bộ xử lý nền (`ERROR`, `onerror`, `onmessageerror`, lỗi khi `load_bank`, hoặc treo quá hạn chờ 10 giây) rồi nhấn nút "Thử lại". Xác thực rằng `recoverWorker()` trả về `false`, nút "Thử lại" vẫn hiển thị và kích hoạt lại được; khi bộ xử lý mới phản hồi thành công toàn trình thì trả về `true` và ẩn nút "Thử lại".

**Acceptance Scenarios**:

1. **Given** Bộ xử lý nền gặp lỗi fatal hoặc quá thời hạn xử lý (timeout), **When** Người dùng nhấn nút "Thử lại", **Then** Hệ thống chấm dứt bộ xử lý cũ, tạo bộ xử lý mới, chờ tín hiệu sẵn sàng và hoàn tất nạp lại kho mẫu chữ từ bộ nhớ cục bộ trước khi ẩn nút "Thử lại", chuyển sang trạng thái "Sẵn sàng" và trả về `true`.
2. **Given** Bộ xử lý mới gặp lỗi trong quá trình khởi tạo hoặc phục hồi (lỗi khởi tạo đồng bộ, thông điệp `ERROR`, sự kiện `onerror`, lỗi giải mã thông điệp `messageerror`, lỗi khi nạp lại kho mẫu trong `onWorkerReady`, hoặc không phản hồi sau 10 giây), **When** Quá trình khôi phục được kích hoạt, **Then** Hệ thống chấm dứt Worker lỗi (nếu quá hạn), trả về `false`, giữ nguyên nút "Thử lại" ở trạng thái bật (`disabled = false`) trên thanh trạng thái và hiển thị thông báo lỗi cho người dùng.
3. **Given** Người dùng nhấn nút "Thử lại" liên tục nhiều lần trong khi quá trình khôi phục đang diễn ra, **When** Các lượt bấm tiếp theo được ghi nhận, **Then** Hệ thống chỉ thực thi một tiến trình khôi phục duy nhất (single-flight) và trả về cùng một tiến trình đang chạy.

---

### User Story 2 - Thống nhất Định danh và Ngữ cảnh Seed Toàn Diện (Priority: P1)

Khi người dùng soạn thảo và xuất tài liệu chữ viết tay ở chế độ biến thể ổn định (`stable_variants=True`), các thành phần trong hệ thống kết xuất (`DocumentLayoutEngine`, `Writer`, `FidelityLayoutEngine`) sử dụng một ngữ cảnh định danh phần tử thống nhất xuyên suốt (`SeedContext`: loại nội dung, mã phần tử, số lần xuất hiện và mục đích sinh ngẫu nhiên). Việc chèn từ mới hoặc chỉnh sửa nội dung tuân theo cam kết bất biến rõ ràng: các phần tử cũ được nhận diện là giữ nguyên sẽ bảo toàn hoàn toàn lựa chọn mẫu chữ và biến đổi hình học (scale, rotation, jitter).

**Why this priority**: Giải quyết triệt để vấn đề lệch bộ đếm giữa tầng bố cục và tầng sinh nét chữ, cũng như sự thay đổi biến thể dây chuyền khi người dùng chỉnh sửa tài liệu.

**Independent Test**: Kết xuất một tài liệu mẫu, sau đó chèn thêm từ mới (cả từ không trùng lặp và từ trùng lặp có đối chiếu định danh) vào trước hoặc giữa tài liệu. So sánh các nét chữ của các từ cũ được giữ nguyên; xác nhận hình thái hình học tương đối của các từ cũ hoàn toàn bất biến.

**Acceptance Scenarios**:

1. **Given** Một tài liệu có văn bản thường (`text`), ký hiệu (`sym`) và ô bảng (`cell`), **When** Tài liệu được xử lý qua hệ thống bố cục và tạo nét viết, **Then** Tầng bố cục xác định `SeedContext` trước và truyền trực tiếp vào `Writer` cũng như bước biến đổi hình học, đảm bảo lựa chọn biến thể chữ, dấu thanh và biến đổi hình học dùng chung một định danh thống nhất và cô lập hoàn toàn giữa các không gian tên (`text`, `cell`, `sym`, `math`).
2. **Given** Một tài liệu được chỉnh sửa bằng cách chèn thêm từ không trùng lặp (trong chế độ đơn lẻ) hoặc chèn cả từ/công thức trùng lặp (khi áp dụng bộ đối chiếu định danh phiên bản trước/sau hoặc định danh bền vững `stable_id`), **When** Kết xuất lại tài liệu với cùng hạt giống, **Then** Toàn bộ các phần tử cũ được nhận diện giữ nguyên có hình thái nét vẽ bất biến 100%.

---

### User Story 3 - Ổn định Biến thể cho Khoảng cách Từ, Công thức và Bảng (Priority: P2)

Khi tài liệu chứa các phần tử phức tạp như công thức toán học (`MathInline`, `MathBlock`), bảng biểu (`Table`), hoặc chuỗi khoảng cách từ (`wgap`), hệ thống dẫn xuất hạt giống ngẫu nhiên dựa trên định danh cụ thể của từng thực thể và cặp định danh vị trí lân cận thay vì chỉ dựa vào chuỗi ký tự đơn thuần hay chỉ số thứ tự toàn cục.

**Why this priority**: Ngăn chặn hiện tượng lặp lại máy móc khi các cụm từ giống nhau có cùng khoảng cách từ cứng nhắc, đồng thời bảo vệ công thức toán và bảng biểu khỏi bị biến đổi nét khi chèn thêm bảng hoặc công thức khác ở phía trước.

**Independent Test**: Tạo tài liệu có các cụm từ lặp lại, 2 bảng biểu và 2 công thức toán học; kiểm tra khoảng cách của 2 cụm từ lặp lại có sự biến thiên tự nhiên nhưng tái lập được, và khi chèn thêm một bảng/công thức độc lập vào trước thì nét viền cùng nét viết của bảng/công thức cũ không bị thay đổi.

**Acceptance Scenarios**:

1. **Given** Hai lần xuất hiện của cùng một cụm từ trong văn bản ở hai vị trí khác nhau, **When** Tính toán khoảng cách giữa các từ (`wgap`), **Then** Khoảng cách được dẫn xuất từ cặp định danh (`prev_token_id`, `curr_token_id`) của hai từ liền kề, vừa đảm bảo tái lập 100% khi kết xuất lại cùng vị trí, vừa tạo độ co giãn tự nhiên giữa các lần xuất hiện khác nhau.
2. **Given** Một tài liệu có chứa công thức toán học (`MathInline` hoặc `MathBlock`), **When** Hệ thống thực hiện bước đo thử kích thước (`_scratch`) và bước kết xuất chính thức, **Then** Bản sao đo thử bảo toàn toàn bộ trạng thái ngữ cảnh hạt giống và bộ chống lặp của `Writer`, đảm bảo mỗi phép đo thử và bước kết xuất thực tế dẫn xuất hạt giống trùng khớp tuyệt đối.
3. **Given** Bảng biểu với nhiều hàng và ô, **When** Kết xuất đường viền bảng và nội dung từng ô, **Then** Hạt giống ngẫu nhiên của đường viền được dẫn xuất từ định danh bảng ổn định (`table_id`) và chỉ số hàng thay vì tổng số bảng toàn cục, không bị biến đổi khi chèn một bảng khác vào phía trước.

---

### User Story 4 - Chuẩn tắc hóa Mã hóa Khóa Dẫn xuất Seed & Bảo toàn Golden Master (Priority: P2)

Hệ thống mã hóa khóa đầu vào để sinh hạt giống ngẫu nhiên theo định dạng chuẩn tắc (canonical encoding): có phân định kiểu dữ liệu rõ ràng (`int`, `str`, `bytes`, `bool`, `None`, `tuple`), chuẩn hóa Unicode NFC, có tiền tố độ dài 4 byte (length-prefixed) và có tiền tố phiên bản thuật toán (`rng-v2` cho chế độ biến thể ổn định). Cơ chế này loại bỏ hoàn toàn nguy cơ va chạm hạt giống giữa các kiểu dữ liệu khác nhau hoặc lỗi tràn số nguyên 64-bit, đồng thời bảo toàn 100% tính nguyên vẹn cho chế độ mặc định (`stable_variants=False`) để không làm ảnh hưởng 8 ca kiểm thử Golden Master.

**Why this priority**: Bảo đảm tính đúng đắn toán học của hệ thống sinh số ngẫu nhiên có kiểm soát, ngăn ngừa lỗi va chạm khóa tinh vi, và duy trì tính tương thích ngược hoàn toàn với kho kiểm thử hiện hành.

**Independent Test**: Chạy bộ kiểm thử cố định (test vectors) cho hàm sinh hạt giống với các loại khóa đặc biệt (số nguyên âm, số nguyên 64-bit không dấu `>= 2**63`, số `1` vs chuỗi `"1"`, chuỗi chứa byte `\x00`, ký tự Unicode NFC/NFD); xác nhận không có va chạm khóa hay lỗi tràn số, và 8/8 ca Golden Master mặc định khớp SHA-256 100%.

**Acceptance Scenarios**:

1. **Given** Các khóa đầu vào có nội dung tương đồng nhưng khác kiểu (ví dụ số nguyên `1`, chuỗi `"1"`, boolean `True`, hoặc chuỗi chứa ký tự `\x00`), **When** Thực hiện mã hóa khóa chuẩn tắc trong `derive_seed`, **Then** Bộ mã hóa sinh ra các chuỗi byte chuẩn tắc phân biệt tuyệt đối và tạo ra các hạt giống ngẫu nhiên khác nhau mà không gặp lỗi tràn số nguyên.
2. **Given** Chế độ kết xuất mặc định (`stable_variants=False`), **When** Thực thi toàn bộ bộ kiểm thử Golden Master (8/8 ca trên CPython và Pyodide), **Then** Tất cả các giá trị băm SHA-256 của file `.xopp` và `_thieu.xopp` xuất ra trùng khớp 100% với chuẩn gốc.

---

### User Story 5 - Bảo vệ Cạnh tranh Số lần Dạy chữ (Teach Count) trong Lưu trữ (Priority: P2)

Các thao tác tăng hoặc đặt lại số lần dạy mẫu chữ (`incrementTeachCount`, `resetTeachCount`) trong hệ thống lưu trữ phía client được thực hiện nguyên tử ngay trong một giao dịch IndexedDB (`readwrite` transaction), đảm bảo không bao giờ ghi đè dữ liệu kho mẫu (`data`) của tab khác, không làm hồi sinh hồ sơ đã xóa, và cập nhật đồng bộ `localSyncedTimestamp` để không gây hợp nhất giả (false-positive merge) khi tự động lưu.

**Why this priority**: Hoàn thiện toàn diện cơ chế kiểm soát cạnh tranh của tầng lưu trữ Web Client, loại bỏ lỗ hổng đọc-ghi tách rời không kiểm tra phiên bản còn sót lại trong `storage.js`.

**Independent Test**: Gọi `incrementTeachCount` và `resetTeachCount` trong kịch bản đơn tab (kiểm tra `localSyncedTimestamp` được cập nhật đồng bộ, không kích hoạt merge thừa) và kịch bản đa tab cạnh tranh hoặc sau khi hồ sơ bị xóa (kiểm tra không làm mất dữ liệu kho mẫu của tab khác và không hồi sinh hồ sơ đã xóa).

**Acceptance Scenarios**:

1. **Given** Một tab đang mở hồ sơ đồng bộ với IndexedDB, **When** Người dùng dạy mẫu chữ mới khiến `incrementTeachCount` chạy trước `syncAndSaveActiveProfile`, **Then** Giao dịch cập nhật nguyên tử `teach_count_since_backup` và đồng bộ `localSyncedTimestamp` nếu tab đang giữ phiên bản mới nhất, tránh kích hoạt hợp nhất dư thừa.
2. **Given** Hồ sơ đã bị xóa ở một tab khác, **When** Tab hiện tại gọi `incrementTeachCount` hoặc `resetTeachCount`, **Then** Giao dịch phát hiện hồ sơ không còn tồn tại và hủy bỏ thao tác ghi, tuyệt đối không làm sống lại hồ sơ đã xóa.

---

### Edge Cases

- **Bộ xử lý nền không phản hồi tín hiệu**: Nếu Worker bị treo ngay khi khởi động và không bao giờ gửi thông điệp `READY`, bộ đếm thời gian 10 giây (timeout) tự động chấm dứt Worker bị treo (`terminate()`), giải quyết Promise với `false` và giữ nguyên trạng thái lỗi kèm nút "Thử lại".
- **Lỗi khởi tạo hoặc nạp kho mẫu trong `onWorkerReady()`**: Nếu Worker gửi `READY` nhưng bước đọc IndexedDB hoặc `load_bank` thất bại, nút "Thử lại" không bị ẩn đi mà được bật lại cùng thông báo lỗi.
- **Lỗi giải mã thông điệp (`messageerror`) hoặc thông điệp `ERROR`**: Khi Worker gửi thông điệp `ERROR` hoặc sự kiện `onmessageerror` trong lúc khởi tạo/phục hồi, hệ thống gọi `handleWorkerFatalError` và lập tức giải quyết Promise chờ sẵn sàng với `false`.
- **Hạt giống con 64-bit không dấu (`>= 2**63`) hoặc số âm**: Khi `math_seed` (số nguyên 64-bit từ `ScopedRNG.seed`) được truyền làm `master_seed` cho `Writer` của công thức toán, hoặc người dùng truyền `seed < 0`, bộ mã hóa chuẩn tắc xử lý an toàn không gây `OverflowError`.
- **Token chứa số kèm dấu câu bao quanh (như `(123)`)**: Khi `Writer.token("(123)")` gọi `Writer.number("123")` cho phần lõi số, ngữ cảnh của token bao ngoài được bảo toàn để dấu đóng ngoặc `")"` phía sau không bị lệch khóa hạt giống.
- **Bật/tắt `jitter` không làm lệch biến thể dấu thanh**: Trong `Writer.assemble_word()`, việc tính nhiễu khoảng cách ký tự khi `jitter > 0` sử dụng chỉ số vị trí ký tự tường minh thay vì làm tăng bộ đếm `_char_idx` dùng cho việc chọn mẫu chữ và dấu thanh.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Quá trình khôi phục bộ xử lý nền (`recoverWorker`) CHỈ ĐƯỢC COI LÀ THÀNH CÔNG (`return true`) khi đáp ứng đồng thời 3 điều kiện: (1) Nhận được tín hiệu `READY` từ Worker mới trong vòng 10 giây, (2) Nạp lại kho mẫu chữ (`load_bank`) và làm mới giao diện trong `onWorkerReady()` thành công không ném lỗi, và (3) Giao diện đã chuyển sang trạng thái sẵn sàng.
- **FR-002**: Hệ thống PHẢI áp dụng giới hạn thời gian chờ tối đa 10 giây (`WORKER_INIT_TIMEOUT_MS = 10000`) cho bước chờ Worker sẵn sàng trong `recoverWorker()`; nếu quá hạn, hệ thống PHẢI gọi `worker.terminate()`, kích hoạt `handleWorkerFatalError()` và trả về `false`.
- **FR-003**: Khi khôi phục thất bại vì bất kỳ nguyên nhân nào (lỗi khởi tạo Worker, thông điệp `ERROR`, sự kiện `onerror`, sự kiện `onmessageerror`, quá hạn chờ 10s, hoặc lỗi trong `onWorkerReady()`), hệ thống PHẢI trả về `false`, giữ nguyên thông báo lỗi và hiển thị nút "Thử lại" ở trạng thái bật (`disabled = false`). Nút "Thử lại" CHỈ ĐƯỢC ẨN sau khi toàn bộ `onWorkerReady()` hoàn tất thành công.
- **FR-004**: Thao tác khôi phục Worker PHẢI sử dụng cờ kiểm soát đơn tuyến (`isRecovering` và `recoveryPromise`) để ngăn chặn việc tạo trùng lặp nhiều Worker khi người dùng nhấp nút liên tục.
- **FR-005**: Hệ thống PHẢI thiết lập cấu trúc ngữ cảnh hạt giống ngẫu nhiên bất biến (`SeedContext`) bao gồm: loại nội dung (`content_type`), định danh phần tử (`element_id`), số lần xuất hiện (`occurrence`), mục đích tạo ngẫu nhiên (`purpose`), và chỉ số phụ (`sub_index`).
- **FR-006**: `DocumentLayoutEngine` và `FidelityLayoutEngine` PHẢI xác định `SeedContext` trước khi gọi `Writer.token()`, `Writer.symbol()`, `Writer.number()` và truyền cùng `SeedContext` đó cho cả `Writer` lẫn bước biến đổi hình học (`geom`), loại bỏ hoàn toàn tình trạng đếm lệch giữa các tầng.
- **FR-007**: Trong `Writer`, bộ nhớ tránh lặp biến thể (`_token_last`) PHẢI được phân tách theo `(content_type, element_id, tag)` để các vùng nội dung khác nhau (`text`, `cell`, `sym`, `math`) không làm rò rỉ trạng thái ngẫu nhiên sang nhau. Ngoài ra, `Writer.number()` khi được gọi từ bên trong `Writer.token()` KHÔNG ĐƯỢC ghi đè ngữ cảnh của token cha, và `Writer.assemble_word()` KHÔNG ĐƯỢC làm dịch chuyển chỉ số chọn biến thể dấu thanh khi thay đổi `jitter`.
- **FR-008**: Khi ở chế độ biến thể ổn định (`stable_variants=True`), hệ thống PHẢI đảm bảo tính bất biến hình thái nét vẽ khi chỉnh sửa: (a) Chèn nội dung không trùng lặp ở bất kỳ đâu không làm đổi nét của các phần tử hiện có; (b) Hỗ trợ định danh bền vững (`stable_id`) trên các nút tài liệu hoặc bộ đối chiếu chuỗi LCS (`align_document_seeds`) giữa phiên bản trước và sau chỉnh sửa để bảo toàn `occurrence` của các từ, công thức và bảng cũ ngay cả khi chèn phần tử trùng lặp vào phía trước.
- **FR-009**: Khoảng cách giữa hai từ liên tiếp (`wgap`) trong chế độ ổn định PHẢI được dẫn xuất từ cặp mã định danh đầy đủ của hai token liền kề `(prev_token_id, curr_token_id)` thay vì chỉ dùng cặp chuỗi ký tự.
- **FR-010**: Các khối công thức toán học (`MathInline`, `MathBlock`) PHẢI dẫn xuất hạt giống từ định danh phần tử toán học độc lập, và `MathLayoutEngine._scratch()` PHẢI sao chép đầy đủ trạng thái bộ đếm/chống lặp của `Writer` cho từng lượt đo thử để bước đo thử và bước kết xuất chính thức sinh ra kết quả trùng khớp 100%.
- **FR-011**: Đường viền bảng (`tbl_border`) PHẢI dẫn xuất hạt giống từ định danh bảng ổn định (`table_id` dựa trên `stable_id` hoặc chữ ký cấu trúc bảng kèm số lần xuất hiện) và chỉ số hàng thay vì tổng số bảng toàn cục `total_tables`.
- **FR-012**: Hàm dẫn xuất hạt giống (`derive_seed`) PHẢI áp dụng cơ chế mã hóa khóa chuẩn tắc (canonical encoding) có tiền tố phiên bản thuật toán `rng-v2\x00`, nhãn kiểu dữ liệu tường minh (`int`, `str` chuẩn hóa NFC, `bytes`, `bool`, `None`, `tuple`), và tiền tố độ dài 4-byte big-endian, xử lý an toàn số nguyên âm và số nguyên 64-bit không dấu mà không gây tràn số.
- **FR-013**: Chế độ mặc định (`stable_variants=False`) PHẢI giữ nguyên luồng sinh số ngẫu nhiên ban đầu để đảm bảo 100% các ca kiểm thử Golden Master (8/8 ca) không bị biến đổi kết quả băm SHA-256.
- **FR-014**: Các hàm `incrementTeachCount()` và `resetTeachCount()` trong `webapp/js/storage.js` PHẢI thực hiện đọc-sửa-ghi nguyên tử bên trong một giao dịch `executeTransaction` duy nhất trên `profiles` store, không ghi lại nếu hồ sơ đã bị xóa, và cập nhật đồng bộ `localSyncedTimestamp` khi tab hiện tại đang giữ phiên bản mới nhất.

### Key Entities

- **SeedContext**: Thực thể bất biến đại diện cho ngữ cảnh sinh số ngẫu nhiên của một phần tử kết xuất (`content_type`, `element_id`, `occurrence`, `purpose`, `sub_index`), cung cấp `token_id` chuẩn hóa `f"{content_type}:{element_id}#{occurrence}"`.
- **WorkerRecoverySession**: Thực thể quản lý vòng đời một phiên khôi phục bộ xử lý nền, bao gồm `workerGeneration`, bộ đếm thời gian chờ 10s, Promise quản lý trạng thái đơn tuyến, và xác nhận hoàn tất `onWorkerReady()`.
- **CanonicalKey**: Quy tắc tuần tự hóa khóa đầu vào chuẩn tắc dùng trong `derive_seed` (`rng-v2`), phân định rõ nhãn kiểu 1-byte, độ dài dữ liệu 4-byte uint32 big-endian và chuỗi byte payload đã chuẩn hóa.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các trường hợp khôi phục Worker bị lỗi (`ERROR`, `onerror`, `onmessageerror`, timeout 10 giây, lỗi nạp dữ liệu trong `onWorkerReady`) trả về `false`, giữ nguyên nút "Thử lại" ở trạng thái bật trên giao diện và hiển thị thông báo lỗi chính xác (0% false positives).
- **SC-002**: Khi chèn thêm từ, công thức hoặc bảng mới vào văn bản trong chế độ ổn định, 100% các nét vẽ của những phần tử cũ được nhận diện giữ nguyên có hình thái hình học tương đối trùng khớp trong phạm vi dung sai tuần tự hóa XML (`<= 0.02 pt`).
- **SC-003**: 100% các ca kiểm thử trong bộ test vector của `derive_seed` v2 phân biệt tuyệt đối các khóa khác kiểu hoặc chứa ký tự phân tách (`\x00`), và 100% các bài kiểm thử Golden Master (8/8 ca) ở chế độ mặc định (`stable_variants=False`) đạt kết quả trùng khớp băm SHA-256 tuyệt đối.
- **SC-004**: Thời gian thực thi toàn bộ pipeline kết xuất trên tài liệu lớn với ngữ cảnh định danh mới không suy giảm đáng kể (chênh lệch trung vị `<= 10%` trong benchmark tự động).
- **SC-005**: 100% các ca kiểm thử đơn vị Python & JS, kiểm thử tích hợp đa tab, kiểm thử khả năng phục hồi Worker, kiểm thử Golden Master Pyodide và kiểm thử E2E Playwright đều vượt qua thành công.

---

## Assumptions

- **Thời hạn chờ Worker**: Giới hạn thời gian 10 giây là mặc định cho bước chờ tín hiệu `READY` khi khôi phục Worker (có thể truyền tham số `timeoutMs` ngắn hơn trong unit test để kiểm thử nhanh).
- **Cam kết tính bất biến khi chỉnh sửa**:
  - Ở chế độ kết xuất đơn lẻ không trạng thái (stateless), định danh phần tử dựa trên `(content_type, element_id, occurrence)` đảm bảo bất biến hoàn toàn khi chèn các từ/công thức/bảng không trùng lặp.
  - Ở chế độ chỉnh sửa có đối chiếu phiên bản trước/sau (qua `align_document_seeds(base_doc, edited_doc)` hoặc `stable_id` gắn trên nút IR), thuật toán đối chiếu chuỗi con chung dài nhất (LCS / `SequenceMatcher`) bảo toàn `occurrence` cho cả các từ, công thức và bảng trùng lặp.
- **Môi trường thực thi**: Cam kết bit-exact SHA-256 áp dụng trên cùng runtime, cùng phiên bản mã nguồn, cùng kho mẫu và cùng cấu hình. Giữa CPython và Pyodide WASM, chế độ mặc định (`stable_variants=False`) đạt 100% bit-exact trên cả 8 ca Golden Master, trong khi chế độ `stable_variants=True` (có `gauss` Box-Muller) cam kết bit-exact trong cùng runtime và tương đương hình học/thống kê xuyên runtime.
