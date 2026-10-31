# Feature Specification: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

**Feature Branch**: `069-seed-reset-bank-cache-hardening`  
**Created**: 2026-10-31  
**Status**: Draft  
**Input**: Phản hồi kiểm tra sau CI Run #71 (commit 5e571e7): Khắc phục 2 lỗi ranh giới luồng thực tế (P2) gồm xóa trắng/mở tài liệu mới chưa xóa lịch sử seed và cache snapshot cập nhật quá sớm trước khi render hoàn tất; bổ sung kiểm chứng hình thái nét toàn diện và mở rộng benchmark snapshot đa biến thể.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự động xóa lịch sử hạt giống khi xóa trắng hoặc mở tài liệu mới (Priority: P1) 🎯 MVP

Là một người dùng soạn thảo và in ấn chữ viết tay trên Web Client, tôi muốn khi tôi xóa toàn bộ nội dung trong trình soạn thảo hoặc mở/tải lên một tệp tài liệu mới (TXT, Markdown, DOCX), hệ thống phải coi đây là một tài liệu độc lập hoàn toàn mới và không tự động kế thừa biến thể hạt giống (seed occurrences) từ tài liệu cũ trước đó, để các từ ngữ trùng lặp trong tài liệu mới được gán biến thể tự nhiên theo đúng thứ tự xuất hiện ban đầu.

**Why this priority**: Nếu lịch sử tài liệu cũ vẫn tồn tại trong bộ điều khiển, việc người dùng viết tài liệu mới với cùng giá trị seed sẽ kích hoạt thuật toán căn chỉnh hạt giống nối ghép sai lệch với tài liệu cũ, khiến biến thể chữ của tài liệu mới bị xáo trộn hoặc chọn biến thể không mong muốn ngay từ những câu đầu tiên.

**Independent Test**:
- Kịch bản A (Xóa trắng rồi viết lại): Soạn thảo văn bản A gồm các từ lặp (ví dụ `"tôi đi học"`), sau đó xóa sạch ô soạn thảo (`Ctrl+A` $\to$ `Backspace`), tiếp tục nhập lại `"tôi đi học"` $\to$ xác nhận các từ trong văn bản mới nhận chỉ số biến thể xuất hiện ban đầu (`0, 0, 0`) và hình thái nét chữ trùng khớp 100% với lần đầu tiên viết văn bản A độc lập.
- Kịch bản B (Mở tài liệu mới): Soạn thảo văn bản A, sau đó mở tệp tài liệu B có chứa một số từ trùng với A $\to$ xác nhận các từ trong tài liệu B được gán biến thể tính từ đầu, hoàn toàn không bị ảnh hưởng bởi chỉ số của tài liệu A trước đó.

**Acceptance Scenarios**:
1. **Given** người dùng đang soạn thảo tài liệu có chữ trên giao diện, **When** người dùng xóa sạch toàn bộ văn bản trong ô soạn thảo khiến nội dung trở về rỗng, **Then** hệ thống tự động xóa sạch bản xem trước đồng thời phát tín hiệu xóa trắng lịch sử đối chiếu hạt giống xuống bộ điều khiển lõi.
2. **Given** người dùng vừa xóa trắng ô soạn thảo, **When** người dùng nhập một nội dung mới, **Then** hệ thống kết xuất nội dung mới như một tài liệu độc lập ban đầu, không đối chiếu với nội dung đã bị xóa.
3. **Given** người dùng đang có một tài liệu đang hiển thị trên giao diện, **When** người dùng chọn mở hoặc kéo thả một tệp tài liệu mới (TXT, Markdown hoặc DOCX), **Then** hệ thống xóa lịch sử đối chiếu của tài liệu cũ trước khi nạp và kết xuất tài liệu mới.

---

### User Story 2 - Cập nhật bộ nhớ đệm Kho mẫu an toàn chỉ sau khi dựng giao diện thành công (Priority: P1)

Là một người dùng xem và quản lý kho mẫu ký tự, tôi muốn thông tin danh mục mẫu chữ luôn được tải lại chính xác và hiển thị đầy đủ, ngay cả khi lần kết xuất trước đó bị gián đoạn do lỗi hiển thị hoặc phần tử DOM chưa sẵn sàng, để giao diện không bao giờ bị rơi vào trạng thái trống rỗng hoặc kẹt dữ liệu cũ.

**Why this priority**: Cập nhật bộ nhớ đệm snapshot thành công quá sớm (trước khi quá trình render thẻ mẫu hoàn tất) sẽ khiến hệ thống lầm tưởng dữ liệu đã hiển thị thành công. Khi lần render đầu tiên thất bại, các lần gọi tiếp theo sẽ bị bỏ qua và người dùng nhìn thấy danh sách trống mà không có cách nào tự phục hồi.

**Independent Test**:
- Giả lập tình huống tiến trình dựng danh sách thẻ mẫu gặp lỗi ở lần gọi đầu tiên $\to$ xác nhận bộ nhớ đệm snapshot không bị ghi nhận thành công, trạng thái cache bị hủy kích hoạt (invalidated).
- Gọi làm mới giao diện lần thứ hai $\to$ hệ thống nhận diện cache chưa hoàn tất, tự động thử lại quá trình kết xuất và hiển thị trọn vẹn danh sách thẻ mẫu.

**Acceptance Scenarios**:
1. **Given** giao diện nhận được bản chụp kho mẫu hợp lệ từ tiến trình nền, **When** quá trình dựng danh sách thẻ mẫu chữ lên màn hình gặp lỗi hoặc vùng chứa thẻ chưa hiển thị, **Then** hệ thống giữ trạng thái bộ nhớ đệm là chưa hoàn tất (vô hiệu hóa cache) và thông báo lỗi an toàn cho người dùng.
2. **Given** một lần dựng giao diện kho mẫu từng thất bại trước đó, **When** hàm làm mới giao diện kho mẫu được gọi lại, **Then** hệ thống bỏ qua kiểm tra bỏ sót cache và thực hiện lại toàn bộ quy trình dựng giao diện.
3. **Given** quá trình tổng hợp và dựng toàn bộ danh sách thẻ mẫu chữ thành công 100%, **When** bước kết xuất cuối cùng kết thúc an toàn, **Then** hệ thống mới chính thức ghi nhận khóa phiên bản snapshot vào bộ nhớ đệm.

---

### User Story 3 - Kiểm chứng nâng cao chất lượng hạt giống và bảo toàn hình thái nét vẽ toàn diện (Priority: P2)

Là một kỹ sư kiểm thử và bảo trì hệ thống, tôi muốn bộ kiểm thử thuật toán đối chiếu hạt giống kiểm tra chi tiết toàn bộ các nét vẽ (all strokes) của các từ được giữ lại qua nhiều bước chỉnh sửa liên tiếp (thay vì chỉ so sánh nét đầu tiên), đồng thời kiểm tra chặt chẽ các chỉ số xuất hiện tại các vị trí chèn mới, để đảm bảo tính ổn định tuyệt đối của công cụ kết xuất chữ viết tay.

**Why this priority**: Chỉ so sánh nét đầu tiên (`strokes1[0] == strokes2[0]`) có thể che giấu các lỗi biến dạng ở các nét vẽ tiếp theo của một ký tự hoặc các từ phía sau. Đảm bảo toàn bộ các nét của các từ giữ lại trùng khớp 100% giúp người dùng hoàn toàn tin tưởng rằng việc gõ thêm câu chữ không làm thay đổi các đoạn văn đã viết trước.

**Independent Test**:
- Chạy kịch bản kiểm thử chỉnh sửa liên tiếp $D_0 \to D_1 \to D_2 \to D_3$, kiểm tra khẳng định (assertion) chỉ số xuất hiện của từ mới chèn vào giữa câu (`occs_d3[3] == 1`).
- Đọc toàn bộ danh sách nét vẽ (stroke data) của các từ cũ trước và sau nhiều lượt chỉnh sửa, xác nhận 100% chuỗi toạ độ các nét giữ nguyên vẹn không sai lệch.

**Acceptance Scenarios**:
1. **Given** chuỗi 3 lượt chỉnh sửa liên tiếp $D_0 \to D_1 \to D_2 \to D_3$, **When** từ mới được chèn vào vị trí giữa câu, **Then** chỉ số xuất hiện tại vị trí đó được kiểm tra chính xác bằng assertion tự động.
2. **Given** hai phiên bản tài liệu kết xuất trước và sau khi bổ sung văn bản mới, **When** trích xuất dữ liệu nét vẽ của tất cả các từ thuộc phần nội dung không thay đổi, **Then** toàn bộ các nét vẽ của từng từ giữ nguyên 100% toạ độ và thứ tự nét.

---

### User Story 4 - Mở rộng kiểm thử hiệu năng Kho mẫu đa biến thể và đồng bộ hóa tài liệu kỹ thuật (Priority: P3)

Là một kỹ sư duy trì dự án, tôi muốn bài đo hiệu năng bản chụp kho mẫu phản ánh đúng thực tế với kho có nhiều mẫu biến thể trên mỗi nhãn (3–5 biến thể/ký tự, quy mô 3.000+ mẫu nét), đồng thời các tài liệu kỹ thuật của dự án phải chuẩn hóa nhất quán đường dẫn tệp kiểm thử và số liệu kết quả CI/Local.

**Why this priority**: Kho mẫu thực tế của người dùng luôn chứa nhiều biến thể cho mỗi chữ cái để tạo nét tự nhiên. Đo kiểm với nhiều biến thể trên 1.000+ nhãn đảm bảo hệ thống không bị nghẽn cổ chai khi dữ liệu lớn. Chuẩn hóa tài liệu kỹ thuật giúp cộng tác nhóm và báo cáo kiểm toán CI minh bạch, chính xác.

**Independent Test**:
- Chạy bài đo hiệu năng bản chụp kho mẫu với 1.000+ nhãn và 3.000+ mẫu nét đa dạng $\to$ xác nhận thời gian trích xuất snapshot hoàn tất dưới 200ms.
- Kiểm tra tài liệu `tasks.md` và `quickstart.md` $\to$ đường dẫn tệp kiểm thử đồng nhất (`tests/test_bridge.py`), số lượng test E2E ghi nhận chính xác 20 tests, số liệu kiểm thử Python phân định rõ giữa CI (1.405 passed · 14 skipped · 7 deselected) và máy phát triển (1.426 passed).

**Acceptance Scenarios**:
1. **Given** kho mẫu quy mô lớn với hơn 1.000 nhãn và trung bình 3 biến thể nét cho mỗi nhãn (tổng cộng trên 3.000 mẫu nét), **When** trích xuất bản chụp kho mẫu tổng thể, **Then** thời gian xử lý hoàn tất trong dưới 200 mili-giây.
2. **Given** tài liệu kế hoạch và kiểm chứng, **When** đối chiếu với cấu trúc kho mã nguồn và nhật ký CI thực tế, **Then** toàn bộ đường dẫn tệp tin, số lượng bài kiểm thử E2E và phân tích số liệu Python đều trùng khớp chính xác 100%.

---

### Edge Cases

- Người dùng gõ một khoảng trắng hoặc ký tự xuống dòng rồi xóa ngay: Hệ thống phải nhận diện nội dung đã xóa trắng và kích hoạt xóa lịch sử seed mà không gây lỗi phân tích.
- Người dùng mở một tệp văn bản rỗng (0 bytes): Trình soạn thảo xóa sạch nội dung, giao diện xóa bản xem trước và lịch sử đối chiếu seed được xóa hoàn toàn.
- Đang tải một tệp tài liệu mới thì tệp bị lỗi định dạng hoặc người dùng hủy: Nội dung cũ và lịch sử seed cũ được giữ an toàn hoặc đặt lại về trạng thái sạch có thể dự đoán được.
- Quá trình kết xuất thẻ mẫu trong Tab Kho bị ném biệt lệ bất ngờ (exception): Biến tạm lưu cache bị hủy, thẻ lỗi hiển thị thông báo an toàn, lần nhấn làm mới tiếp theo chạy lại từ đầu mà không bị cache chặn.
- Tài liệu lớn có hàng trăm từ lặp lại khi xóa trắng rồi gõ lại: Quá trình phân bổ seed bắt đầu từ số 0 mượt mà, không gặp hiện tượng tràn ngăn xếp hay rò rỉ bộ nhớ.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST cung cấp thao tác xóa lịch sử đối chiếu hạt giống đi xuyên suốt từ giao diện soạn thảo (`write.js`) qua tiến trình xử lý nền (`Worker`), lớp cầu nối (`BrowserBridge`) tới bộ điều khiển trung tâm (`AppController`).
- **FR-002**: Trình soạn thảo văn bản (`write.js`) MUST tự động kích hoạt thao tác xóa lịch sử đối chiếu hạt giống khi người dùng xóa sạch toàn bộ nội dung trong ô nhập liệu (nội dung rỗng sau khi cắt tỉa khoảng trắng).
- **FR-003**: Trình xử lý mở tệp (`handleFileImport`) MUST tự động kích hoạt thao tác xóa lịch sử đối chiếu hạt giống trước khi tải nội dung mới từ các định dạng TXT, Markdown hoặc DOCX vào ô soạn thảo.
- **FR-004**: Giao diện quản lý Kho mẫu (`bank.js`) MUST chỉ ghi nhận khóa phiên bản bản chụp (`lastBankSnapshotCache`) vào bộ nhớ đệm sau khi toàn bộ quy trình tổng hợp và dựng thẻ giao diện (`applyFiltersAndRender`) hoàn tất thành công.
- **FR-005**: Giao diện quản lý Kho mẫu (`bank.js`) MUST vô hiệu hóa trạng thái bộ nhớ đệm tạm thời nếu phát sinh lỗi trong quá trình kết xuất danh sách mẫu, cho phép lượt yêu cầu tiếp theo thực hiện lại đầy đủ.
- **FR-006**: Bộ kiểm thử đối chiếu hạt giống (`test_stable_variants.py`) MUST bổ sung kiểm tra khẳng định chỉ số xuất hiện của các từ chèn mới trong chuỗi nhiều lượt sửa liên tiếp, đồng thời kiểm tra so sánh 100% hình thái nét vẽ của toàn bộ các từ được bảo toàn.
- **FR-007**: Kịch bản đo kiểm hiệu năng bản chụp kho mẫu (`test_performance_regression.py`) MUST kiểm thử trên kho mẫu chứa hơn 1.000 nhãn với nhiều mẫu biến thể trên mỗi nhãn (tổng cộng trên 3.000 mẫu nét) và hoàn tất dưới 200 mili-giây.
- **FR-008**: Toàn bộ tài liệu kỹ thuật (`tasks.md`, `quickstart.md`) MUST đồng bộ hóa chính xác đường dẫn tệp kiểm thử `tests/test_bridge.py`, số lượng bài kiểm thử Playwright E2E (20 tests) và ghi chú rõ ràng sai biệt số liệu kiểm thử môi trường CI so với môi trường máy phát triển.

### Key Entities

- **Document Alignment History**: Trạng thái lưu giữ cấu trúc tài liệu IR và hạt giống của lượt kết xuất gần nhất trong bộ điều khiển, dùng để ánh xạ biến thể nét chữ giữa các lần gõ văn bản liên tiếp; được xóa sạch khi văn bản rỗng hoặc khi mở tài liệu mới.
- **Bank Snapshot Cache Key**: Bộ ba định danh trạng thái hiển thị của kho mẫu (`epoch`, `revision`, `profileId`), chỉ được lưu vào bộ nhớ đệm khi DOM giao diện đã hiển thị thành công.
- **Stroke Geometry**: Tập hợp danh sách toạ độ điểm của toàn bộ các nét vẽ tạo nên hình thái trực quan của một từ hoặc ký tự trong tệp đầu ra XOPP.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các từ trong tài liệu mới sau khi xóa trắng hoặc mở file mới đều nhận chỉ số biến thể bắt đầu từ xuất hiện ban đầu (`occurrence = 0`), không kế thừa bất kỳ biến thể nào của tài liệu cũ trước đó.
- **SC-002**: Khi quá trình dựng giao diện kho mẫu gặp sự cố ở lần đầu, 100% các lần làm mới tiếp theo sẽ tự động thử lại thành công và hiển thị đủ danh sách thẻ chữ mà không bị chặn bởi bộ nhớ đệm.
- **SC-003**: 100% nét vẽ của toàn bộ các từ được bảo toàn qua các lượt chỉnh sửa liên tiếp trong bài kiểm thử hình học giữ nguyên vẹn toạ độ nét vẽ (sai lệch 0.00 pt).
- **SC-004**: Thời gian trích xuất bản chụp kho mẫu với 1.000+ nhãn và 3.000+ mẫu nét đa dạng hoàn tất trong thời gian dưới 200 mili-giây.
- **SC-005**: 100% các bài kiểm thử E2E trên trình duyệt (20/20 tests) và kiểm thử hồi quy Python đạt trạng thái xanh (PASS).

---

## Assumptions

- Trình duyệt hỗ trợ đầy đủ các cơ chế giao tiếp thông điệp bất đồng bộ hai chiều giữa luồng chính UI và Web Worker.
- Khi người dùng xóa trắng văn bản, việc xóa lịch sử seed được thực hiện theo cơ chế "gửi và quên" (fire-and-forget) hoặc đồng bộ nhanh mà không gây đơ giật giao diện người dùng.
- Thao tác mở tệp mới luôn thay thế toàn bộ nội dung của phiên soạn thảo hiện tại, trừ khi có tính năng ghép tệp được yêu cầu riêng trong tương lai.
