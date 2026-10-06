# Feature Specification: Kho Ký Tự Mẫu, Nạp File Lưới và Bỏ Mẫu Theo Từ

**Feature Branch**: `024-kho-ky-tu`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Bỏ phần tạo thành từ, chỉ giữ phần điền các chữ cái; phần điền từ thì bỏ đi; Thêm tính năng đọc file lưới để tạo kho ký tự mẫu; Nút điền bộ: thay vì bộ từ thì sẽ là bộ ký tự; Rà soát kỹ lưỡng."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chuyển đổi mô hình kho chữ sang thuần ký tự đơn & luôn ghép chữ khi viết (Priority: P1) 🎯 MVP

Là người dùng ứng dụng ChuVietTay, tôi muốn ứng dụng chỉ tập trung dạy, lưu trữ và quản lý các **ký tự đơn lẻ** (`letters`, `digits`, `punct`, `symbols`, `marks`), và khi tôi gõ bất kỳ đoạn văn bản nào thì ứng dụng luôn tự động ghép từ các ký tự mẫu một cách mượt mà và tự nhiên, không còn khái niệm "dạy theo từ" hay cờ bật/tắt ghép chữ phức tạp, để việc xây dựng kho chữ của tôi nhanh chóng, đầy đủ và không bị phân mảnh.

**Why this priority**: Đây là thay đổi cốt lõi (R1) chuyển đổi toàn bộ kiến trúc kho mẫu và bộ máy kết xuất văn bản từ dạng phụ thuộc từ vựng nguyên khối sang mô hình ký tự linh hoạt.

**Independent Test**: Mở kho mẫu mới hoặc kho hiện có, nhập văn bản bất kỳ ở tab "Viết chữ", hệ thống luôn kết xuất chữ viết bằng thuật toán ghép ký tự (không tra `bank.words`); giao diện soạn thảo chỉ cảnh báo các ký tự còn thiếu thay vì báo thiếu cả từ.

**Acceptance Scenarios**:

1. **Given** Người dùng ở tab "Viết chữ" gõ văn bản, **When** Hệ thống dàn trang và kết xuất chữ viết tay, **Then** Mọi từ ngữ luôn được tự động ghép từ các ký tự trong kho (`letters`, `digits`, `punct`, `symbols`, `marks`), không còn cờ `--assemble` hay tùy chọn checkbox "Ghép chữ từ ký tự".
2. **Given** Kho mẫu chứa các từ ngữ cũ được tạo từ các phiên bản trước (`bank.words`), **When** Mở kho và thực hiện viết văn bản hoặc lưu kho, **Then** Dữ liệu `words` cũ vẫn được bảo toàn nguyên vẹn trong tệp tin lưu trữ (không bị xóa hay ghi đè mất), nhưng không được sử dụng trong luồng viết chữ mới, và giao diện hiển thị thông tin rõ ràng về số lượng từ cũ tồn tại.
3. **Given** Người dùng gõ một từ có chứa ký tự chưa được học trong kho, **When** Xem kết quả kiểm tra từ thiếu, **Then** Hệ thống hiển thị danh sách các **ký tự còn thiếu** xếp theo thứ tự ưu tiên mở khóa nhiều từ nhất, bấm vào ký tự nào sẽ dẫn thẳng tới giao diện dạy ký tự đó.

---

### User Story 2 - Nạp file lưới tập viết (.xopp) để tự động trích xuất kho ký tự mẫu (Priority: P1)

Là người dùng đã viết tay trên các trang lưới tập viết (sinh ra từ công cụ tạo lưới của ứng dụng), tôi muốn nạp các tệp tin lưới `.xopp` này trực tiếp trên Giao diện Web, Desktop hoặc Dòng lệnh (CLI) để hệ thống tự động bóc tách nét chữ, nhận diện đúng ô ký tự, tính toán độ rộng khoảng đệm (bearings) chính xác và lưu vào kho ký tự, đồng thời hiển thị báo cáo chi tiết kết quả nạp.

**Why this priority**: Đáp ứng yêu cầu R2, mở ra phương thức nạp mẫu hàng loạt trực quan, tiện lợi nhất cho người dùng viết bằng bút cảm ứng trên máy tính bảng hoặc giấy xuất sang Xournal++.

**Independent Test**: Nạp một tệp lưới `.xopp` đã điền nét qua nút "Nạp từ file lưới (.xopp)…", kiểm tra kho mẫu được cập nhật đúng các ký tự tương ứng, khoảng cách ghép từ tự nhiên (không bị giãn cách gấp 10 lần do lỗi tọa độ lề ô), và nạp lại cùng file không làm nhân bản mẫu (idempotent).

**Acceptance Scenarios**:

1. **Given** Người dùng có một hoặc nhiều tệp lưới `.xopp` chứa nét viết tay, **When** Người dùng chọn nạp tệp qua giao diện Web / Desktop / CLI, **Then** Hệ thống phân tích từng ô, trích xuất nét và đưa vào đúng danh mục (`letters`, `digits`, `punct`, `symbols`, `marks`), tính toán khoảng cách biên `lsb/rsb` chuẩn theo đường bao nét chứ không lấy theo lề ô giấy.
2. **Given** Một từ ghép (ví dụ "abc") được viết từ kho mẫu sinh ra từ file lưới, **When** Đo đạc độ rộng từ ghép, **Then** Độ rộng khớp trong khoảng sai số $\le 10\%$ so với cùng chữ cái được dạy vẽ trực tiếp trên canvas, không bị lỗi giãn chữ quá rộng hay dính chữ.
3. **Given** Người dùng nạp lại cùng một tệp lưới `.xopp` lần thứ hai mà không sửa đổi, **When** Quá trình nạp hoàn tất, **Then** Báo cáo kết quả ghi nhận $0$ mẫu mới được thêm (`n_added == 0`), không tạo ra mẫu trùng lặp.
4. **Given** File lưới chứa các ô đa ký tự (như tên hàm, đơn vị đo, nguyên tố hóa học) hoặc ô dấu thanh có nét quá khổ bất thường, **When** Nạp tệp lưới, **Then** Hệ thống tự động bỏ qua các ô này, ghi rõ lý do và liệt kê trong bảng báo cáo kết quả nạp.

---

### User Story 3 - Bộ ký tự chuẩn hóa và hàng đợi dạy ký tự trực quan (Priority: P2)

Là người dùng cần hoàn thiện kho mẫu chữ viết tay, tôi muốn có nút "Bộ ký tự…" với các tùy chọn bộ ký tự chọn lọc (Bộ cơ bản, Toán học & Hy Lạp, Ký hiệu mở rộng, Bộ đầy đủ) để nạp các ký tự còn thiếu vào hàng đợi dạy, thay thế cho các nút từ thông dụng cũ (SEED 700 từ), đồng thời có thể nhập bất kỳ đoạn văn bản nào để tự động bóc tách thành danh sách các ký tự đơn còn thiếu cần học.

**Why this priority**: Đáp ứng yêu cầu R3, định hình lại toàn bộ quy trình học chữ tập trung vào ký tự, loại bỏ các khái niệm "từ thông dụng" không còn phù hợp.

**Independent Test**: Bấm nút "Bộ ký tự…", chọn bộ "Cơ bản", kiểm tra hàng đợi dạy được bổ sung đúng các ký tự đơn còn thiếu; nhập một câu vào ô nhập nhanh, kiểm tra các ký tự cấu thành câu đó được đưa vào hàng đợi.

**Acceptance Scenarios**:

1. **Given** Người dùng ở tab "Dạy ký tự", **When** Bấm nút "Bộ ký tự…", **Then** Xuất hiện danh sách các bộ ký tự định sẵn kèm thống kê số lượng ký tự còn thiếu trong kho cho từng bộ.
2. **Given** Người dùng chọn một bộ ký tự và bấm nạp, **When** Hàng đợi được cập nhật, **Then** Chỉ các ký tự đơn lẻ thực sự chưa có mẫu (hoặc chưa đủ số lượng) mới được thêm vào hàng đợi. Nút "Từ thông dụng" và danh sách 700 từ cũ hoàn toàn không còn xuất hiện.
3. **Given** Người dùng dán một đoạn văn bản bất kỳ vào ô thêm ký tự, **When** Bấm nút thêm, **Then** Hệ thống tự động phân tách văn bản thành tập hợp các ký tự đơn phân biệt và nạp các ký tự còn thiếu vào hàng đợi.

---

### User Story 4 - Hiệu chỉnh cỡ tay bằng ký tự mốc chuẩn (Priority: P2)

Là người dùng đang vẽ trực tiếp trên canvas, tôi muốn tính năng "Hiệu chỉnh cỡ tay" chọn một **ký tự mốc** phù hợp trong kho (thay vì phụ thuộc vào một từ nguyên khối có sẵn trong `bank.words`) để tôi viết lại ký tự đó và tính toán hệ số co giãn cỡ tay chính xác.

**Why this priority**: Giải quyết F6 khi bỏ `bank.words`, bảo đảm tính năng hiệu chỉnh cỡ tay quan trọng tiếp tục vận hành chuẩn xác.

**Independent Test**: Bấm nút "Hiệu chỉnh cỡ tay" khi kho đã có mẫu các chữ cái cơ bản (`o`, `a`, `e`, `n`...), hệ thống đề xuất ký tự mốc ổn định nhất để người dùng viết lại và tính hệ số scale.

**Acceptance Scenarios**:

1. **Given** Kho mẫu đã có một số ký tự đơn được dạy, **When** Người dùng bấm "Hiệu chỉnh cỡ tay", **Then** Hệ thống tự động chọn một ký tự x-height ổn định (như `o`, `a`, `e`, `n`, `u`...) có từ 3 mẫu trở lên để làm mốc so sánh.
2. **Given** Người dùng viết lại ký tự mốc trên canvas, **When** Bấm lưu, **Then** Hệ số cỡ tay được tính toán và áp dụng cho toàn bộ các ký tự được vẽ tiếp theo trong phiên.

---

### Edge Cases

- **File lưới không có nét nào được nhận dạng**: Người dùng nạp nhầm file lưới trắng chưa viết hoặc dùng màu mực trùng màu lưới; hệ thống hiển thị cảnh báo rõ ràng thay vì im lặng.
- **File lưới bị thiếu thẻ nhận diện chuẩn (`hw3`)**: Hệ thống cảnh báo file không đúng định dạng lưới chuẩn nhưng vẫn hỗ trợ đọc nếu tọa độ các ô khớp quy chuẩn.
- **Dấu thanh rời vẽ quá to hoặc lệch vị trí**: Ô dấu thanh có nét cao vượt quá $0,75 \times x\text{-height}$ hoặc rộng vượt $0,95 \times x\text{-height}$ được ghi nhận từ chối và liệt kê trong mục `rejected` của báo cáo để người dùng biết và viết lại.
- **Ký tự chỉ số trên/dưới (`²`, `₂`...)**: Phân loại chuẩn xác vào nhóm ký hiệu (`symbols`) thay vì bị nhầm sang chữ số (`digits`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI loại bỏ hoàn toàn các chức năng dạy từ, lưu trữ từ và tra cứu từ nguyên khối trong luồng nghiệp vụ viết chữ và dạy chữ trên toàn bộ các nền tảng (Web Client, Desktop GUI, CLI).
- **FR-002**: Cơ chế lưu trữ kho mẫu PHẢI bảo toàn nguyên vẹn trường dữ liệu `words` có sẵn từ các kho mẫu cũ khi mở và lưu lại tệp tin, không được tự ý xóa hoặc thay đổi cấu trúc dữ liệu người dùng.
- **FR-003**: Hệ thống PHẢI thiết lập cơ chế ghép chữ từ ký tự đơn (`assemble`) làm phương thức duy nhất và luôn luôn kích hoạt khi kết xuất văn bản; loại bỏ cờ `--assemble` và tùy chọn bật/tắt ghép chữ trên giao diện.
- **FR-004**: Hệ thống PHẢI cung cấp mô-đun danh mục ký tự chuẩn (`char_catalog.py`) làm nguồn dữ liệu duy nhất cho việc định nghĩa các bộ ký tự (`co_ban`, `toan_hy_lap`, `mo_rong`, `day_du`) và phục vụ việc sinh lưới cũng như nạp lưới.
- **FR-005**: Hệ thống PHẢI chuẩn hóa hàm phân loại ký tự (`classify_char`) áp dụng thống nhất cho toàn bộ các luồng (dạy trên canvas, nạp từ file lưới, tra cứu kho mẫu, xuất file kiểm tra).
- **FR-006**: Khi nạp nét chữ từ tệp lưới `.xopp` hoặc dạy trên canvas, hệ thống PHẢI tính toán khoảng cách biên `lsb/rsb` dựa trên đường bao nét thực tế thay vì dựa vào vị trí tương đối của nét so với lề ô giấy, đảm bảo khoảng cách giữa các chữ cái khi ghép không bị sai lệch.
- **FR-007**: Thuật toán ghép từ PHẢI áp dụng giới hạn an toàn cho khoảng đệm biên (`lsb`, `rsb` không vượt quá $0,3 \times x\text{-height}$) để tự động khắc phục các kho mẫu cũ từng bị nạp sai tọa độ.
- **FR-008**: Hệ thống PHẢI hỗ trợ nạp tệp lưới `.xopp` từ mảng byte nhị phân để cho phép Web Client nạp trực tiếp qua trình duyệt mà không cần đường dẫn tệp đĩa cục bộ.
- **FR-009**: Thao tác nạp tệp lưới PHẢI có tính chất lũy nghiệm (idempotent): nạp lại cùng một tệp tin nhiều lần mà không sửa đổi nét sẽ không sinh thêm mẫu trùng lặp (`n_added == 0`).
- **FR-010**: Quá trình nạp tệp lưới PHẢI trả về đối tượng kết quả chi tiết (`GridImportResult`) bao gồm: tổng số ô có mực, số mẫu thêm mới, số mẫu theo từng danh mục, số mẫu trùng lặp, số ô trống, danh sách các ô đa ký tự bị bỏ qua, danh sách các nét bị từ chối kèm lý do và các cảnh báo liên quan.
- **FR-011**: Hệ thống PHẢI thay thế các nút "Bộ tối thiểu" và "Từ thông dụng" bằng nút "Bộ ký tự…" trên cả giao diện Web và Desktop, cho phép nạp các ký tự còn thiếu theo từng bộ chọn lọc.
- **FR-012**: Hệ thống PHẢI chuyển đổi cơ chế hiệu chỉnh cỡ tay sang sử dụng ký tự mốc (`pick_calibration_char`), lựa chọn từ các ký tự có chiều cao x-height ổn định có sẵn trong kho.
- **FR-013**: Trên giao diện Web Client, tính năng nạp tệp lưới PHẢI hoạt động hoàn toàn ngoại tuyến và tự động đồng bộ xuống cơ sở dữ liệu IndexedDB an toàn với Web Locks.
- **FR-014**: Dòng lệnh CLI PHẢI cập nhật lệnh `grid` hỗ trợ chọn bộ ký tự qua cờ `--set` và lệnh `learn` hiển thị báo cáo chi tiết theo cấu trúc mới.

### Key Entities

- **CharCatalog**: Danh mục ký tự tập trung định nghĩa các nhóm (`CharGroup`), bộ ký tự (`CharSet`), và các nhãn ký tự được chuẩn hóa NFC.
- **GridImportResult**: Bản ghi kết quả phân tích và nạp tệp lưới, chứa các chỉ số thống kê định lượng và danh sách chi tiết các ô được xử lý, bỏ qua hoặc từ chối.
- **LetterSample**: Mẫu ký tự đơn chứa các nét tương đối, độ rộng nét, thông tin chân chữ, x-height và khoảng đệm biên hợp lệ.
- **CalibrationChar**: Ký tự được thuật toán lựa chọn làm mốc để đo lường và hiệu chỉnh tỷ lệ cỡ tay vẽ của người dùng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sau khi nạp một tệp lưới ký tự hoàn chỉnh vào kho trống, số lượng khóa trong `bank.words` đo được chính xác bằng $0$ (`len(bank.words) == 0`).
- **SC-002**: Độ rộng của một từ mẫu ("abc") khi ghép từ kho nạp từ lưới và kho dạy vẽ tay chênh lệch không quá $10\%$ (khắc phục hoàn toàn độ lệch 10 lần trước đây: từ ~215 pt xuống ~21.5 pt).
- **SC-003**: Nạp lại một tệp lưới `.xopp` lần thứ 2 liên tiếp cho kết quả chính xác $0$ mẫu thêm mới (`n_added == 0`).
- **SC-004**: Tỷ lệ nạp ô ký tự đơn từ tệp lưới chuẩn đạt $100\%$ đối với các ô có nét hợp lệ; $343$ ô đa ký tự trong lưới đầy đủ được tự động bỏ qua an toàn và báo cáo đầy đủ.
- **SC-005**: Toàn bộ các chuỗi giao diện người dùng chứa "Từ thông dụng", "Bộ tối thiểu", "Dạy từ mới", "Từ thiếu mẫu" trong mã nguồn web và desktop được loại bỏ $100\%$, thay thế bằng các thuật ngữ về ký tự.
- **SC-006**: $100\%$ các bài kiểm thử tự động trong kho (`pytest`, Playwright E2E, Golden-master) vượt qua thành công sau khi hoàn tất các pha triển khai.

## Assumptions

- Người dùng hiểu rằng việc bỏ mẫu theo từ đồng nghĩa với việc toàn bộ chữ viết tay tạo ra sẽ dựa trên cơ chế ghép từ các ký tự đơn lẻ trong kho.
- Các kho mẫu cũ chứa dữ liệu từ vựng nguyên khối (`words`) khi được mở ra vẫn giữ nguyên vẹn nội dung tệp tin để tránh mất mát dữ liệu lịch sử của người dùng, nhưng các từ này không tham gia vào quá trình sinh văn bản mới.
- Các tệp lưới tập viết tuân theo bố cục lưới chuẩn 4 dòng kẻ và nhãn định danh tương thích với công cụ tạo lưới của ứng dụng.
