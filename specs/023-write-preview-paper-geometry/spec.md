# Feature Specification: Sửa kích thước xem trước giấy và hình học xem trước tab Viết chữ

**Feature Branch**: `specs/023-write-preview-paper-geometry`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Sửa lỗi chữ trong bản xem trước ở tab Viết chữ quá nhỏ, và sửa các lỗi liên quan trực tiếp tới khung xem trước giấy. Không làm tính năng mới ngoài danh sách bên dưới."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xem trước trang giấy đúng kích thước vật lý hiển thị (Priority: P1)

Là người dùng tab "Viết chữ", tôi muốn trang giấy xem trước hiển thị đúng kích thước tỷ lệ thực theo chuẩn hiển thị màn hình (100% zoom tương ứng 1 pt = 96/72 CSS pixel, ví dụ A4 rộng ~794 px thay vì bị co rút xuống 300 px), để chữ viết và bố cục trang giấy có kích thước tự nhiên, rõ ràng, dễ đọc, không bị chữ li ti.

**Why this priority**: Đây là lỗi cốt lõi (P0) khiến chữ xem trước quá nhỏ đến mức không đọc được, gây hiểu lầm rằng chất lượng tạo nét chữ bị lỗi hoặc kích thước font bị sai lệch.

**Independent Test**: Nạp kho mẫu thử bất kỳ hoặc gõ văn bản, kiểm tra trang giấy hiển thị ở mức zoom 100% có bề rộng thực khớp với khổ giấy (A4 dọc đạt ~794 px) và chữ viết có độ lớn chuẩn theo dòng kẻ.

**Acceptance Scenarios**:

1. **Given** Người dùng ở tab "Viết chữ" đã nạp kho mẫu và gõ nội dung, **When** Khung xem trước hiển thị ở mức zoom 100%, **Then** Khung giấy có bề rộng thực tương ứng đúng quy đổi điểm ảnh màn hình chuẩn (khổ A4 dọc đạt xấp xỉ 793,7 px, sai số layout < 2 px), chữ viết hiển thị rõ ràng, dễ đọc.
2. **Given** Người dùng chọn các khổ giấy khác nhau (A4, A5, Letter) hoặc đổi hướng trang (dọc / ngang), **When** Trang giấy render trong khung xem trước, **Then** Tỷ lệ chiều rộng / chiều cao của giấy phản ánh chính xác kích thước khổ trang đã chọn ở mức zoom 100%.

---

### User Story 2 - Điều khiển Zoom linh hoạt với các nút bấm và chế độ Fit tự động (Priority: P1)

Là người dùng tab "Viết chữ", tôi muốn có các nút điều khiển thu phóng trực quan (nút giảm `−`, tăng `+`, nút `Fit` vừa bề rộng khung và nhãn hiển thị phần trăm hiện tại), để tôi có thể phóng to kiểm tra chi tiết từng nét chữ hoặc thu nhỏ để xem toàn trang, và khi cửa sổ trình duyệt thay đổi kích thước thì chế độ Fit tự động căn chỉnh lại độ rộng giấy mà không gây vỡ bố cục hoặc cuộn ngang không mong muốn.

**Why this priority**: Giúp người dùng trên các màn hình có độ phân giải khác nhau (Full HD 1920×1080, laptop 1366×768) có thể quan sát trang giấy trọn vẹn mà không phải cuộn ngang khó chịu khi dùng chế độ Fit, đồng thời cuộn mượt mà chuẩn xác khi zoom lớn.

**Independent Test**: Bấm nút `−` và `+` để thay đổi độ phóng từ 50% đến 300%; bấm nút `Fit` kiểm tra bề rộng trang vừa khít khung xem trước (có lề đệm an toàn) và không xuất hiện thanh cuộn ngang; thay đổi kích thước cửa sổ khi đang ở Fit kiểm tra trang tự co giãn thích ứng.

**Acceptance Scenarios**:

1. **Given** Người dùng bấm nút `+` hoặc `−` trên thanh điều khiển zoom, **When** Mức zoom thay đổi, **Then** Nhãn phần trăm cập nhật giá trị tương ứng (nằm trong dải hợp lệ 50% – 300%), kích thước layout của khung giấy thay đổi thật theo tỷ lệ quy đổi pixel, vùng chứa kích hoạt thanh cuộn native chính xác khi giấy tràn ra ngoài khung nhìn.
2. **Given** Người dùng bấm nút `Fit`, **When** Chế độ Fit được kích hoạt, **Then** Giấy được co giãn vừa vặn chiều rộng của khung xem trước trừ đi khoảng đệm hiển thị, không xuất hiện thanh cuộn ngang ở vùng xem trước.
3. **Given** Khung xem trước đang ở chế độ `Fit`, **When** Kích thước cửa sổ trình duyệt thay đổi (ví dụ từ 1920×1020 sang 1366×768), **Then** Kích thước khung giấy tự động tính toán lại để tiếp tục vừa vặn khung nhìn mới mà người dùng không cần bấm lại nút.

---

### User Story 3 - Kiểu giấy nền khớp chuẩn Xournal++ và phản ánh đúng nhãn tiếng Việt (Priority: P2)

Là người dùng cần viết chữ và xuất file sang định dạng Xournal++ (`.xopp`), tôi muốn các kiểu giấy nền như dòng kẻ ngang có lề dọc đỏ (`lined`) và chỉ dòng kẻ ngang (`ruled`) được đặt tên, hiển thị trên giao diện, và xuất ra file hoàn toàn đồng nhất với quy ước chuẩn của Xournal++, đồng thời kiểu giấy mặc định là dòng kẻ tập vở thông dụng (`lined`), để bản xem trước trên web phản ánh chính xác những gì xuất ra.

**Why this priority**: Tránh sự nhầm lẫn giữa hai kiểu giấy phổ biến nhất khi xuất file và giúp trải nghiệm viết chữ tự nhiên ngay khi mở ứng dụng với kiểu giấy có dòng kẻ mặc định.

**Independent Test**: Chọn kiểu giấy "Có dòng kẻ & lề" (`lined`) và "Chỉ dòng kẻ" (`ruled`), quan sát trên khung xem trước: kiểu `lined` phải có lề dọc đỏ và dòng ngang, kiểu `ruled` chỉ có dòng ngang. Kiểm tra xuất file `.xopp` bảo toàn đúng quy ước này.

**Acceptance Scenarios**:

1. **Given** Ứng dụng ở trạng thái ban đầu khi tải trang, **When** Mở tab "Viết chữ", **Then** Kiểu giấy nền mặc định là `lined` (Dòng kẻ & lề dọc).
2. **Given** Người dùng chọn kiểu giấy `lined`, **When** Trang giấy hiển thị trên màn hình xem trước, **Then** Giấy hiển thị các dòng kẻ ngang và một đường vạch lề dọc màu đỏ ở phía bên trái.
3. **Given** Người dùng chọn kiểu giấy `ruled`, **When** Trang giấy hiển thị trên màn hình xem trước, **Then** Giấy chỉ hiển thị các dòng kẻ ngang song song, không có đường vạch lề dọc màu đỏ.
4. **Given** Danh sách lựa chọn kiểu giấy trên giao diện web, **When** Người dùng quan sát nhãn tiếng Việt, **Then** Nhãn mô tả chính xác trực quan từng loại giấy (Trắng trơn, Dòng kẻ & lề, Chỉ dòng kẻ, Ô ly vuông, Chấm bi).

---

### User Story 4 - Đồng bộ tài liệu hướng dẫn vận hành cổng chạy thử cục bộ (Priority: P3)

Là lập trình viên phát triển repo, tôi muốn tài liệu `README.md` hướng dẫn đúng lệnh và cổng phục vụ cục bộ (`http://localhost:8000`), để có thể chạy thử nghiệm và kiểm thử ngay lập tức mà không gặp lỗi kết nối sai cổng.

**Why this priority**: Đảm bảo tài liệu dự án đồng bộ với cấu hình thực tế của script máy chủ phát triển `scripts/serve.mjs`.

**Independent Test**: Đọc tài liệu `README.md` và kiểm tra lệnh chạy máy chủ cục bộ hướng dẫn đúng cổng 8000.

**Acceptance Scenarios**:

1. **Given** Tài liệu `README.md`, **When** Kiểm tra phần hướng dẫn chạy thử web cục bộ, **Then** Cổng hiển thị là 8000, khớp với cổng mặc định trong `scripts/serve.mjs`.

---

### Edge Cases

- **Zoom ở ngưỡng biên giới hạn**: Khi người dùng nhấn giảm khi đang ở mức 50%, nút `−` bị vô hiệu hóa hoặc không giảm quá 50%; khi tăng tới mức 300%, nút `+` bị vô hiệu hóa hoặc không vượt quá 300%.
- **Khung xem trước rất hẹp hoặc rất rộng**: Khi màn hình bị thu nhỏ tối đa hoặc mở siêu rộng, chế độ `Fit` vẫn tính toán tỷ lệ zoom dương hợp lệ (> 10%), không gây tràn lỗi toán học (chia cho 0 hoặc giá trị NaN/âm).
- **Chuyển đổi qua lại giữa Zoom thủ công và Fit**: Khi đang ở Fit mà người dùng bấm nút `+` hoặc `−`, ứng dụng chuyển về mức zoom cố định gần nhất và hủy bỏ trạng thái tự động co giãn theo kích thước cửa sổ.
- **Văn bản nhiều trang**: Khi nội dung dài sinh ra nhiều trang giấy, tất cả các trang đều áp dụng cùng kích thước layout hình học chuẩn và cuộn trang theo trục dọc mượt mà.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI hiển thị kích thước khung giấy xem trước theo tỷ lệ vật lý thực tế: $px = pt \times \frac{96}{72} \times zoom$. Ở mức zoom 100%, trang A4 chuẩn (595,28 pt × 841,89 pt) phải có kích thước hiển thị xấp xỉ 793,7 px × 1122,5 px.
- **FR-002**: Hệ thống PHẢI bảo toàn tỷ lệ khung hình chuẩn của mọi khổ giấy được hỗ trợ (A4, A5, Letter) ở cả hai hướng trang (dọc và ngang).
- **FR-003**: Hệ thống PHẢI thay đổi kích thước layout thực tế của phần tử giấy (layout width/height) thay vì chỉ áp dụng phép biến đổi hiển thị thu nhỏ/phóng to (`transform: scale(...)`), nhằm kích hoạt thanh cuộn trình duyệt tự nhiên khi kích thước giấy vượt quá khung nhìn.
- **FR-004**: Giao diện PHẢI cung cấp bộ điều khiển Zoom gồm nút giảm (`−`), nút tăng (`+`), nút vừa khung (`Fit`), và nhãn hiển thị mức phần trăm zoom hiện tại.
- **FR-005**: Dải zoom cho phép điều khiển bằng nút bấm PHẢI nằm trong khoảng từ 50% đến 300%.
- **FR-006**: Khi ở chế độ `Fit`, hệ thống PHẢI tự động tính toán tỷ lệ zoom sao cho bề rộng của trang giấy vừa khít với bề rộng của vùng chứa xem trước trừ đi khoảng đệm an toàn, đảm bảo không làm xuất hiện thanh cuộn ngang.
- **FR-007**: Khi đang ở chế độ `Fit` và kích thước cửa sổ trình duyệt thay đổi, hệ thống PHẢI tự động tính toán lại mức zoom để duy trì trạng thái vừa khung.
- **FR-008**: Hệ thống PHẢI chuẩn hóa kiểu giấy nền theo chuẩn Xournal++ v1.2.6:
  - Kiểu `lined`: Vẽ các dòng kẻ ngang và vạch lề dọc màu đỏ bên trái.
  - Kiểu `ruled`: Chỉ vẽ các dòng kẻ ngang, không có vạch lề dọc.
- **FR-009**: Nhãn hiển thị tiếng Việt cho các tùy chọn kiểu giấy trong danh sách lựa chọn PHẢI phản ánh chính xác đặc điểm của kiểu giấy:
  - `plain`: Giấy trắng trơn
  - `lined`: Dòng kẻ & lề
  - `ruled`: Chỉ dòng kẻ
  - `graph`: Ô ly vuông
  - `dotted`: Chấm bi
- **FR-010**: Kiểu giấy nền mặc định khi khởi tạo giao diện viết chữ PHẢI là `lined`.
- **FR-011**: Quá trình xuất tài liệu sang định dạng Xournal++ (`.xopp`) PHẢI giữ tính nhất quán với định nghĩa `lined` và `ruled` chuẩn của Xournal++.
- **FR-012**: Tài liệu `README.md` PHẢI cập nhật hướng dẫn cổng chạy máy chủ phát triển cục bộ về cổng 8000.

### Key Entities

- **PaperGeometry**: Đại diện cho thông số hình học của trang giấy (chiều rộng điểm pt, chiều cao điểm pt, tỷ lệ quy đổi màn hình 96/72, hệ số zoom hiện tại, kích thước điểm ảnh thực tế hiển thị).
- **ZoomState**: Trạng thái điều khiển hiển thị của khung xem trước, gồm mức tỷ lệ phần trăm (50% – 300%), chế độ tự động căn vừa (`isFitMode: boolean`), và kích thước vùng chứa (`stageWidth`).
- **PaperBackgroundStyle**: Kiểu nền trang giấy tuân theo chuẩn Xournal++, bao gồm các giá trị hợp lệ: `plain`, `lined` (dòng kẻ + lề), `ruled` (chỉ dòng kẻ), `graph`, `dotted`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ở độ phân giải 1920×1020 và 1366×768, khi nạp kho mẫu và gõ chữ, trang giấy A4 dọc ở mức zoom 100% có chiều rộng đo được trên DOM đạt $\ge 700\text{ px}$ (chuẩn $595,28 \times 96 / 72 \approx 793,7\text{ px}$, sai lệch $< 2\text{ px}$).
- **SC-002**: Ở chế độ `Fit`, khung xem trước hoàn toàn không xuất hiện thanh cuộn ngang ở cả hai kích thước màn hình thử nghiệm (1920×1020 và 1366×768).
- **SC-003**: Khi chuyển đổi giữa các khổ giấy A5, A4, Letter và đổi hướng xoay trang, tỷ lệ khung hình chiều rộng / chiều cao đo được trên phần tử SVG khớp với tỷ lệ chuẩn của khổ giấy với sai số dưới 1%.
- **SC-004**: 100% các bài test Playwright E2E và test Pytest hiện có trong repo vượt qua thành công (`passed`).

## Assumptions

- Màn hình tiêu chuẩn hiển thị web áp dụng tỷ lệ CSS 96 DPI (1 inch = 72 pt = 96 px), do đó hệ số chuyển đổi cơ sở là 1 pt = 4/3 px (~1.3333 px).
- Người dùng sử dụng các trình duyệt hiện đại hỗ trợ `ResizeObserver` hoặc sự kiện `resize` của cửa sổ để phản ứng tự động với thay đổi kích thước khung nhìn.
- Các hằng số cấu hình trong `chuviettay/config.py` và kiến trúc lõi Python qua `bridge.py` không bị thay đổi.
