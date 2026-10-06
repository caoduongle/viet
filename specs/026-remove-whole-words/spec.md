# Feature Specification: Loại Bỏ Từ Nguyên Khối, Chuyển Sang Thuần Ghép Ký Tự

**Feature Branch**: `026-remove-whole-words`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "rà soát toàn bộ dự án; tìm xem còn chỗ nào có sử dụng từ không; hãy bỏ các phần đó đi; dự hiện tại tôi chỉ muốn sử dụng mỗi các ký tự sau đó ghép thành từ thay vì dùng từ nguyên khối"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kết xuất văn bản thuần ghép ký tự và báo cáo thiếu theo ký tự (Priority: P1) 🎯 MVP

Là người dùng ứng dụng ChuVietTay, tôi muốn khi gõ bất kỳ đoạn văn bản nào để viết tay, hệ thống luôn luôn kết xuất văn bản bằng phương pháp ghép từ các ký tự mẫu đơn lẻ (`letters`, `digits`, `punct`, `symbols`, `marks`) mà không phụ thuộc, tìm kiếm hay fallback sang các mẫu từ nguyên khối (`bank.words`), đồng thời nếu thiếu nét thì chỉ cảnh báo chính xác danh sách các ký tự còn thiếu chứ không báo thiếu cả từ.

**Why this priority**: Đây là trọng tâm cốt lõi của yêu cầu. Loại bỏ hoàn toàn sự phụ thuộc vào từ nguyên khối trong bộ máy kết xuất chữ (`Writer` và `FidelityEngine`), đảm bảo trải nghiệm viết chữ nhất quán và kho mẫu tập trung vào ký tự.

**Independent Test**: Mở kho mẫu chứa các ký tự đơn lẻ, thực hiện viết một đoạn văn bản mới. Kiểm tra kết quả viết hoàn toàn được ghép từ các ký tự đơn; xóa một ký tự đơn trong kho (ví dụ chữ `a`), hệ thống báo thiếu đúng ký tự `a` thay vì báo thiếu từ (ví dụ `ba`, `nam`).

**Acceptance Scenarios**:

1. **Given** Người dùng nhập văn bản để viết tay qua CLI, Desktop GUI hoặc Web Client, **When** Hệ thống xử lý từng token và từ ngữ, **Then** Toàn bộ các từ ngữ đều được ghép bằng thuật toán ghép ký tự (`assemble_word`), không tra cứu hay trả về mẫu nguyên khối từ `bank.words`, và không sử dụng cơ chế thay thế dấu thanh cấp độ từ cũ (`substitute`).
2. **Given** Một từ chứa ký tự chưa có mẫu trong kho, **When** Hệ thống tổng hợp các phần tử còn thiếu, **Then** Danh sách thiếu trả về chính xác các ký tự đơn lẻ (`char`), sắp xếp theo tần suất xuất hiện và khả năng mở khóa từ, không trả về nguyên từ vựng chưa học.
3. **Given** Người dùng yêu cầu tạo lưới ô thiếu mẫu khi viết tài liệu (`--missing-grid` hoặc `FidelityEngine`), **When** File lưới thiếu được tạo ra, **Then** Các ô trong file lưới là các ký tự đơn còn thiếu (`char_grid`), không sinh lưới ô từ vựng nguyên khối.

---

### User Story 2 - Luồng dạy chữ và hàng đợi chỉ tiếp nhận ký tự đơn (Priority: P1)

Là người dùng đang bổ sung mẫu chữ viết tay, tôi muốn giao diện dạy chữ (cả Web Client và Desktop GUI) chỉ cho phép nạp, vẽ và lưu trữ các ký tự đơn lẻ (`letters`, `digits`, `punct`, `symbols`, `marks`), khi nhập văn bản vào ô thêm nhanh thì tự động bóc tách thành các ký tự đơn còn thiếu, không còn chức năng lưu mẫu từ nguyên khối nhiều ký tự hay dạy theo cụm từ.

**Why this priority**: Ngăn chặn việc tiếp tục nạp rác hoặc mẫu từ nguyên khối vào kho, đồng bộ hóa quy trình xây dựng kho mẫu xoay quanh ký tự chuẩn hóa.

**Independent Test**: Nhập chuỗi `"cà phê"` vào ô "Thêm ký tự vào hàng đợi", hệ thống tự động bóc tách và thêm các ký tự còn thiếu (`c`, `a`, `p`, `h`, `e`, dấu huyền, dấu ê) vào hàng đợi thay vì thêm cả nhãn `"cà phê"`.

**Acceptance Scenarios**:

1. **Given** Người dùng nhập một từ hoặc một câu vào ô thêm của hàng đợi dạy chữ, **When** Người dùng nhấn "Thêm" hoặc Enter, **Then** Hệ thống phân tách chuỗi thành tập các ký tự đơn phân biệt và chỉ nạp các ký tự còn thiếu mẫu vào hàng đợi.
2. **Given** Người dùng vẽ nét trên canvas và nhấn "Lưu", **When** Mẫu được ghi vào kho, **Then** Mẫu luôn được phân loại và lưu vào đúng danh mục ký tự (`letters`, `digits`, `punct`, `symbols`, `marks`), không còn luồng ghi đè vào `bank.words`.
3. **Given** Danh sách gợi ý nạp sẵn, **When** Người dùng mở chức năng nạp mẫu hàng loạt, **Then** Hệ thống chỉ cung cấp các "Bộ ký tự" (Cơ bản, Toán học & Hy Lạp, Ký hiệu mở rộng, Toàn bộ), hoàn toàn loại bỏ nút nạp 700 từ thông dụng (`seed_words`).

---

### User Story 3 - Hiệu chỉnh cỡ tay và kiểm tra kho mẫu bằng ký tự mốc chuẩn (Priority: P2)

Là người dùng hiệu chỉnh kích thước nét viết tay hoặc kiểm tra kho mẫu, tôi muốn hệ thống chọn một **ký tự mốc** chuẩn (`pick_calibration_char`) từ các chữ cái có chiều cao x-height ổn định (như `o`, `a`, `e`, `n`...) và xuất lưới kiểm tra kho (`check`) gồm toàn bộ các ký tự đã học, thay vì tìm kiếm từ ngữ nguyên khối trong `bank.words`.

**Why this priority**: Đảm bảo hai nghiệp vụ quan trọng phụ thuộc trước đây vào `bank.words` (đo cỡ tay và xuất file kiểm tra) vận hành hoàn hảo trên mô hình thuần ký tự.

**Independent Test**: Bấm "Hiệu chỉnh cỡ tay" khi kho đã có mẫu chữ cái, hệ thống chọn một chữ cái mốc chuẩn (ví dụ chữ `o`) để vẽ lại; chạy lệnh `check`, file lưới sinh ra hiển thị tất cả ký tự trong kho (`letters`, `digits`, `punct`, `symbols`, `marks`).

**Acceptance Scenarios**:

1. **Given** Kho mẫu đã có một số chữ cái đơn được dạy, **When** Người dùng bấm "Hiệu chỉnh cỡ tay" trên Web hoặc Desktop, **Then** Hệ thống gọi `pick_calibration_char` và đưa ký tự mốc được chọn lên đầu hàng đợi.
2. **Given** Người dùng vẽ ký tự mốc và lưu, **When** Hệ số cỡ tay được tính toán lại, **Then** Mẫu ký tự mốc được lưu vào `letters`, hệ số co giãn `session_scale` được cập nhật cho phiên làm việc.
3. **Given** Người dùng thực hiện lệnh kiểm tra kho (`export_check` / CLI `check`), **When** File lưới kiểm tra được tạo ra, **Then** Toàn bộ các nhãn ký tự từ `letters`, `digits`, `punct`, `symbols`, `marks` được đưa vào lưới, không còn dựa vào `bank.words`.

---

### User Story 4 - Tinh gọn giao diện và cấu trúc quản lý kho (Priority: P3)

Là người dùng quản lý kho mẫu trên Web Client hoặc Desktop GUI, tôi muốn giao diện kho mẫu chỉ hiển thị và quản lý các danh mục ký tự (`letters`, `digits`, `punct`, `symbols`, `marks`), số lượng mẫu thống kê theo số lượng ký tự và nét, không còn xuất hiện thẻ/tab "Từ vựng" hay đếm `n_words`.

**Why this priority**: Đem lại giao diện gọn gàng, trực quan, loại bỏ các thuật ngữ gây bối rối cho người dùng về việc còn hay không còn dùng từ vựng nguyên khối.

**Independent Test**: Mở tab "Kho mẫu" trên Web Client và Desktop GUI, thanh phân loại danh mục chỉ gồm: Chữ cái, Chữ số, Dấu câu, Ký hiệu, Dấu thanh; thông tin tóm tắt hiển thị tổng số ký tự và tổng số mẫu nét.

**Acceptance Scenarios**:

1. **Given** Người dùng xem tab "Kho mẫu" trên Web Client, **When** Danh sách phân loại được hiển thị, **Then** Tab "Từ vựng (words)" không còn xuất hiện; danh mục mặc định chuyển sang "Chữ cái (letters)".
2. **Given** Thống kê kho mẫu (`get_stats` / CLI `stats`), **When** Người dùng xem báo cáo, **Then** Thống kê phản ánh số lượng chữ cái (`n_letters`), chữ số, dấu câu, ký hiệu và dấu thanh; không còn báo cáo số từ vựng nguyên khối làm chỉ số chính.
3. **Given** Kho mẫu chứa dữ liệu lịch sử với khóa `words` từ các phiên bản cũ, **When** Ứng dụng đọc và lưu lại kho mẫu, **Then** Khóa `words` cũ vẫn được giữ nguyên vẹn trong tệp tin để bảo vệ dữ liệu người dùng, nhưng hệ thống không sử dụng trường này trong bất kỳ quy trình xử lý nào.

---

### Edge Cases

- **Kho mẫu cũ chỉ có mẫu từ nguyên khối mà chưa có chữ cái rời**: Khi người dùng viết văn bản, hệ thống sẽ báo thiếu các chữ cái cấu thành và hướng dẫn người dùng dạy hoặc nạp lưới ký tự, chứ không tự động dùng từ nguyên khối để viết.
- **Văn bản nhập vào có ký tự phức hợp nhiều codepoint (dấu tiếng Việt dạng tổ hợp NFD)**: Hệ thống phải chuẩn hóa Unicode sang dạng dựng sẵn (NFC) trước khi phân tách ký tự để đảm bảo mỗi chữ cái tiếng Việt là một ký tự duy nhất (ví dụ `ề` thay vì `e` + `^` + `\`).
- **Xóa mẫu ký tự (`drop`)**: Thao tác xóa ký tự loại bỏ mẫu khỏi đúng nhóm (`letters`, `digits`, `punct`, `symbols`, `marks`), không gây ảnh hưởng hay lỗi chỉ mục tới các nhóm khác.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI loại bỏ hoàn toàn việc tìm kiếm và sử dụng mẫu từ nguyên khối (`b.words`) trong phương thức ghép từ của `Writer` (`writer.py`), biến cơ chế ghép từ các ký tự đơn lẻ (`assemble_word`) thành phương thức kết xuất duy nhất.
- **FR-002**: Hệ thống PHẢI loại bỏ phương thức thay thế dấu thanh cấp từ cũ (`substitute`) và cấu trúc chỉ mục `tl` dựa trên từ vựng nguyên khối trong `Bank.rebuild()`.
- **FR-003**: Hệ thống PHẢI cập nhật hàm xác định thành phần còn thiếu (`missing_letters_ranked` và `token`) để chỉ ghi nhận và trả về các ký tự đơn lẻ còn thiếu, không bỏ qua ký tự khi từ nguyên khối trùng tên tồn tại trong kho cũ.
- **FR-004**: Hệ thống PHẢI loại bỏ phương thức lưu mẫu từ nguyên khối (`teach_word`) trong `AppController` và `Bridge`, hợp nhất luồng lưu mẫu vẽ trực tiếp vào `teach_letter` / `teach_char`.
- **FR-005**: Hệ thống PHẢI chuyển đổi toàn bộ cơ chế hiệu chỉnh cỡ tay sang ký tự mốc (`pick_calibration_char`), thay thế hoàn toàn `pick_calib_word` và `pick_calibration_word` trên Controller, Bridge, Web Worker, Desktop GUI và Web Client.
- **FR-006**: Ô nhập liệu thêm vào hàng đợi trên Desktop GUI (`TeachTab`) và Web Client (`teach.js`) PHẢI tự động bóc tách chuỗi văn bản thành danh sách các ký tự đơn lẻ còn thiếu, ngăn chặn việc thêm chuỗi đa ký tự vào hàng đợi.
- **FR-007**: Hệ thống PHẢI loại bỏ danh mục tĩnh 700 từ thông dụng (`seed_words.py` và lệnh CLI `seed`), thay thế bằng danh mục bộ ký tự chuẩn hóa (`CharCatalog`).
- **FR-008**: Hệ thống PHẢI cập nhật lệnh kiểm tra kho (`export_check` / CLI `check`) để xuất toàn bộ các ký tự có trong kho (`letters`, `digits`, `punct`, `symbols`, `marks`) ra lưới kiểm tra thay vì duyệt `bank.words`.
- **FR-009**: Hệ thống PHẢI cập nhật công cụ tạo lưới ô thiếu mẫu khi viết tài liệu (`FidelityEngine`) để tạo lưới gồm các ký tự đơn còn thiếu thay vì từ ngữ nguyên khối.
- **FR-010**: Giao diện Web Client và Desktop GUI PHẢI loại bỏ nút/tab "Từ vựng", cập nhật thống kê kho mẫu tập trung vào tổng số ký tự đơn và tổng số mẫu nét.
- **FR-011**: Thuộc tính kích thước kho mẫu (`bank_size`) trên `AppController` PHẢI phản ánh tổng số lượng ký tự đơn (`letters + digits + punct + symbols + marks`) thay vì đếm `len(bank.words)`.
- **FR-012**: Hệ thống PHẢI bảo đảm tính tương thích ngược cho tệp tin lưu trữ: nếu tệp kho mẫu chứa khóa `words`, dữ liệu này không bị xóa khi đọc/ghi nhưng hoàn toàn bị cô lập khỏi luồng xử lý của ứng dụng.

### Key Entities

- **CharSample**: Mẫu nét của một ký tự đơn lẻ, được lưu trữ trong một trong các danh mục chuyên biệt (`letters`, `digits`, `punct`, `symbols`, `marks`).
- **CalibrationChar**: Chữ cái mốc được lựa chọn tự động dựa trên độ ổn định của chiều cao và độ rộng từ danh mục `letters` để đo lường hệ số cỡ tay của người dùng.
- **CharQueue**: Hàng đợi các ký tự đơn lẻ cần dạy, được bổ sung từ các bộ ký tự mẫu hoặc phân tách từ văn bản người dùng nhập.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các từ ngữ trong quá trình kết xuất văn bản được tạo ra qua thuật toán ghép ký tự (`assemble_word`); số lần truy vấn `bank.words` trong `Writer` đo được bằng 0.
- **SC-002**: Khi nhập một đoạn văn bản thiếu mẫu (ví dụ "tiếng Việt"), danh sách thành phần còn thiếu trả về 100% là các ký tự đơn lẻ (chữ cái, dấu thanh), 0% là từ nguyên khối.
- **SC-003**: 100% các thành phần UI (Web Client và Desktop GUI) không còn xuất hiện từ khóa "Từ vựng (words)", "SEED 700 từ" hay "Dạy từ mới"; chuyển toàn bộ sang "Ký tự" và "Bộ ký tự".
- **SC-004**: Tính năng hiệu chỉnh cỡ tay thành công 100% dựa trên chữ cái mốc đơn lẻ (`pick_calibration_char`) mà không cần bất kỳ mẫu từ nguyên khối nào trong kho.
- **SC-005**: 100% các bài kiểm thử tự động trong kho (`pytest`) và kiểm thử giao diện vượt qua thành công sau khi hoàn tất loại bỏ và chuẩn hóa.

## Assumptions

- Người dùng đồng thuận việc tập trung toàn bộ nguồn lực vào việc hoàn thiện kho ký tự đơn lẻ để hệ thống tự động ghép chữ mượt mà, thay vì dạy từng từ nguyên khối.
- Các tệp kho mẫu đã có từ trước (`.json.gz`) có chứa trường `words` vẫn được mở và bảo toàn dữ liệu khi lưu lại để tránh làm hỏng tệp dữ liệu của người dùng, nhưng các mẫu từ này không tham gia vào việc viết chữ.
- Thuật toán ghép chữ (`assemble_word`) đã có đầy đủ khả năng ghép mượt mà các chữ cái và dấu thanh tiếng Việt thông qua cơ chế Dual-Path (mẫu nguyên chữ hoặc phân rã dấu thanh) và tính toán khoảng cách quang học.
