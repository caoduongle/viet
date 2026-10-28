# Feature Specification: Tối ưu hóa tìm ký tự giữ chỗ PUA và kiểm thử cạn kiệt toàn bộ vùng giữ chỗ

**Feature Branch**: `063-pua-placeholder-optimization`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát sau commit 81df7a2 (CI 5/5 xanh): Bản sửa đã giải quyết đúng vấn đề bảo toàn LaTeX của vòng trước. Chưa phát hiện lỗi chức năng nghiêm trọng mới; còn một điểm tối ưu hiệu năng và một trường hợp biên nên bổ sung kiểm thử: (1) P3 · Hiệu năng: Tối ưu việc tìm ký tự PUA chưa sử dụng trong hàm chọn ký tự giữ chỗ — kiểm tra nhanh các ký tự đầu dãy trước; nếu có va chạm, xây dựng tập hợp các mã PUA đã xuất hiện trong đầu vào rồi tìm mã chưa dùng trong tập hợp đó để giữ chi phí thông thường thấp và tránh nhiều lần quét lại toàn bộ chuỗi khi gặp nhiều ký tự PUA đầu dãy. (2) P3 · Kiểm thử: Bổ sung kiểm thử riêng cho điều kiện cạn kiệt toàn bộ 6.400 ký tự thuộc vùng PUA, xác nhận hàm trả về None khi đầu vào chứa toàn bộ vùng PUA và kiểm tra luồng import_text() xử lý an toàn (graceful fallback), không làm sai lệch văn bản gốc hay để lộ dấu giữ chỗ."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tối ưu hóa hiệu năng tìm ký tự PUA khi xảy ra va chạm ký tự đầu dãy (Priority: P1) 🎯 MVP

Là người sử dụng và nhà phát triển xử lý các tài liệu Markdown lớn có chứa các ký tự đặc biệt hoặc ký tự thuộc vùng Private Use Area (PUA), tôi muốn hệ thống xác định nhanh chóng một ký tự giữ chỗ khả dụng mà không phải duyệt lặp lại toàn bộ văn bản nhiều lần, nhằm đảm bảo thời gian xử lý luôn nhanh và ổn định ngay cả với tài liệu phức tạp.

**Why this priority**: Trong tài liệu thông thường không chứa ký tự PUA đầu dãy, việc kiểm tra trực tiếp ký tự đầu tiên diễn ra tức thời. Tuy nhiên, nếu tài liệu chứa một chuỗi các ký tự PUA liên tiếp ở đầu khoảng (ví dụ các văn bản kỹ thuật hoặc tài liệu chứa icon/font tùy biến), việc lặp từng ký tự và quét lại toàn bộ chuỗi nhiều lần sẽ làm suy giảm hiệu năng. Bằng cách kiểm tra nhanh ký tự đầu tiên và chỉ thu thập tập hợp các ký tự PUA trong tối đa một lượt quét khi có va chạm, hiệu năng được bảo đảm ở mức tối ưu trong mọi trường hợp.

**Independent Test**: Nhập văn bản lớn chứa nhiều ký tự PUA liên tiếp từ đầu dãy (U+E000 trở đi) kết hợp các khối toán học; xác nhận hệ thống tìm được ký tự khả dụng kế tiếp chính xác và hoàn thành phân tích cú pháp mà không suy giảm tốc độ.

**Acceptance Scenarios**:

1. **Given** văn bản thông thường không chứa ký tự PUA đầu dãy (U+E000), **When** hệ thống tìm ký tự giữ chỗ, **Then** ký tự U+E000 được chọn ngay lập tức qua đường dẫn nhanh (fast-path) mà không tốn thêm chi phí khởi tạo tập hợp.
2. **Given** văn bản chứa các ký tự PUA từ U+E000 đến U+E009, **When** hệ thống tìm ký tự giữ chỗ, **Then** hệ thống thu thập các ký tự PUA có mặt qua đúng một lượt quét và chọn chính xác ký tự kế tiếp chưa xuất hiện (U+E00A).
3. **Given** văn bản chứa các ký tự PUA rải rác trong tài liệu kèm khối toán có dấu đóng giả, **When** tài liệu được nhập, **Then** ký tự giữ chỗ được gán chính xác, các công thức toán và dấu đóng giả được bảo toàn nguyên vẹn sau khi hoàn tất.

---

### User Story 2 - Xử lý an toàn và bảo toàn dữ liệu khi cạn kiệt toàn bộ vùng ký tự PUA (Priority: P2)

Là người dùng xử lý trường hợp biên cực đoan khi văn bản đầu vào chứa toàn bộ 6.400 ký tự thuộc vùng PUA BMP (U+E000 đến U+F8FF), tôi muốn hệ thống vẫn hoạt động an toàn, không ném ngoại lệ chưa xử lý, không làm sai hỏng văn bản gốc và không để lộ bất kỳ dấu giữ chỗ nội bộ nào ra kết quả.

**Why this priority**: Dù tình huống văn bản chứa đủ 6.400 ký tự PUA là cực kỳ hiếm, một kiến trúc phần mềm tin cậy bắt buộc phải có phương án dự phòng (graceful fallback) đã được kiểm chứng. Hệ thống phải xác định rõ ràng trạng thái cạn kiệt và duy trì tính toàn vẹn của dữ liệu đầu ra.

**Independent Test**: Cung cấp văn bản kiểm thử chứa đầy đủ 6.400 ký tự PUA; xác nhận hàm chọn ký tự giữ chỗ trả về kết quả rỗng/None, và luồng nhập tài liệu hoàn thành thành công mà không gây lỗi hoặc rò rỉ ký tự.

**Acceptance Scenarios**:

1. **Given** văn bản đầu vào chứa toàn bộ 6.400 ký tự thuộc vùng PUA (U+E000 đến U+F8FF), **When** hàm tìm ký tự giữ chỗ được gọi, **Then** kết quả trả về là không tìm thấy (`None`).
2. **Given** văn bản đầu vào chứa toàn bộ 6.400 ký tự PUA kèm theo khối toán học và trích dẫn, **When** thực hiện nhập tài liệu qua toàn bộ quy trình phân tích cú pháp, **Then** quy trình hoàn tất suôn sẻ, không phát sinh lỗi ngoại lệ.
3. **Given** kết quả tài liệu sau khi nhập trong điều kiện cạn kiệt PUA, **When** kiểm tra các khối nội dung và danh sách không hỗ trợ, **Then** văn bản gốc của người dùng được giữ nguyên vẹn và không chứa ký tự lạ nào do hệ thống tự sinh.

---

### User Story 3 - Kiểm thử hồi quy tự động siết chặt cho vùng PUA và tương thích toàn diện (Priority: P3)

Là kỹ sư kiểm thử và bảo trì hệ thống, tôi cần bộ kiểm thử hồi quy bao phủ đầy đủ các trường hợp biên của cơ chế PUA (từ va chạm cục bộ, va chạm diện rộng cho đến cạn kiệt tuyệt đối), đồng thời xác nhận toàn bộ quy trình CI hiện có tiếp tục vượt qua 100%.

**Why this priority**: Đảm bảo các thay đổi tối ưu hóa thuật toán và bổ sung trường hợp biên cạn kiệt không gây ảnh hưởng đến tính đúng đắn đã đạt được ở commit 81df7a2 (đặc biệt là bảo toàn công thức LaTeX có ký hiệu `\$\$` và xử lý blockquote lồng nhau).

**Independent Test**: Chạy toàn bộ bộ kiểm thử đơn vị, kiểm thử tích hợp Markdown importer và toàn bộ pipeline CI; xác nhận tất cả các bài kiểm thử đều đạt.

**Acceptance Scenarios**:

1. **Given** ca kiểm thử cạn kiệt toàn bộ 6.400 ký tự PUA, **When** chạy bộ kiểm thử, **Then** bài kiểm tra xác nhận chính xác hàm chọn trả về `None` và kết quả nhập tài liệu bảo toàn dữ liệu gốc.
2. **Given** các ca kiểm thử bảo toàn công thức LaTeX có `\$\$` và dấu đóng giả lồng nhau của vòng trước, **When** chạy lại sau tối ưu hóa, **Then** tất cả các bài kiểm thử tiếp tục đạt 100%.
3. **Given** toàn bộ các tác vụ CI (lint, kiểm thử Python đa phiên bản, kiểm thử giao diện Web), **When** kích hoạt, **Then** toàn bộ các tác vụ đều hoàn thành thành công mà không có lỗi hồi quy.

---

### Edge Cases

- Văn bản rỗng hoặc văn bản không chứa ký hiệu khối toán `$$`: tiếp tục đi theo đường dẫn tắt an toàn, trả về ký tự mặc định hoặc bỏ qua bước xử lý mà không tốn tài nguyên.
- Văn bản chứa ký tự PUA ngắt quãng (ví dụ: U+E000, U+E002 có mặt, nhưng U+E001 còn trống): thuật toán phải chọn ngay ký tự trống đầu tiên (U+E001) chính xác.
- Văn bản cực lớn (hàng chục nghìn dòng): lượt quét một lần để thu thập ký tự PUA phải hoạt động với độ phức tạp tuyến tính O(N), không tạo thêm bản sao chuỗi không cần thiết.
- Tình trạng cạn kiệt PUA kết hợp với các cấu trúc Markdown phức tạp (bảng GFM, danh sách lồng nhau, khối mã indented/fenced): không làm ảnh hưởng đến việc phân tích các thành phần khác.

## Requirements *(mandatory)*

### Functional Requirements

**Tối ưu hóa tìm kiếm ký tự giữ chỗ (US1)**

- **FR-001**: Hệ thống MUST cung cấp đường dẫn nhanh kiểm tra ký tự PUA đầu tiên (U+E000); nếu ký tự này chưa xuất hiện trong văn bản, hệ thống MUST trả về ký tự này ngay lập tức mà không duyệt tiếp hoặc tạo tập hợp.
- **FR-002**: Khi ký tự PUA đầu tiên có va chạm, hệ thống MUST chỉ duyệt qua văn bản đúng một lần để thu thập tập hợp các ký tự thuộc vùng PUA BMP thực sự xuất hiện trong văn bản.
- **FR-003**: Sau khi thu thập tập hợp ký tự PUA xuất hiện, hệ thống MUST duyệt tuần tự qua dải mã PUA và chọn ngay ký tự đầu tiên không thuộc tập hợp đó, đảm bảo độ phức tạp tuyến tính đối với độ dài văn bản.

**Bảo vệ và xử lý an toàn khi cạn kiệt vùng PUA (US2)**

- **FR-004**: Hệ thống MUST trả về trạng thái rỗng (`None`) khi và chỉ khi toàn bộ 6.400 ký tự thuộc vùng PUA BMP (từ U+E000 đến U+F8FF) đều đã xuất hiện trong văn bản đầu vào.
- **FR-005**: Khi không có ký tự giữ chỗ khả dụng (`None`), các bước cô lập khối toán và nhập tài liệu MUST thực hiện cơ chế dự phòng an toàn (graceful fallback): giữ nguyên văn bản gốc, không làm gián đoạn quy trình và không ném ngoại lệ ra ngoài.
- **FR-006**: Trong điều kiện cạn kiệt ký tự giữ chỗ, hệ thống MUST NOT chèn hoặc để lộ bất kỳ ký tự thay thế nội bộ nào vào cây tài liệu hoặc danh sách thành phần không hỗ trợ.

**Bảo toàn tính toàn vẹn và kiểm thử hồi quy (US3)**

- **FR-007**: Hệ thống MUST tiếp tục bảo toàn tuyệt đối mọi công thức LaTeX của người dùng (bao gồm các ký hiệu `\$`, `\$\$` escape) và khôi phục chính xác các dấu đóng giả ở khối trích dẫn lồng nhau như đã được thiết lập ở commit 81df7a2.
- **FR-008**: Bộ kiểm thử MUST bổ sung ca kiểm thử tự động xác nhận trực tiếp rằng hàm chọn ký tự trả về `None` khi chuỗi đầu vào chứa toàn bộ 6.400 ký tự PUA.
- **FR-009**: Bộ kiểm thử MUST bổ sung ca kiểm thử tự động xác nhận quy trình nhập tài liệu đầy đủ (`import_text`) hoạt động an toàn và bảo toàn dữ liệu gốc trong tình huống cạn kiệt toàn bộ 6.400 ký tự PUA.
- **FR-010**: Bộ kiểm thử MUST bao phủ tình huống va chạm một phần nhiều ký tự PUA liên tiếp để kiểm chứng tính đúng đắn và hiệu năng của thuật toán tối ưu.

### Key Entities

- **Vùng ký tự giữ chỗ PUA (BMP PUA Range)**: Dải ký tự Unicode từ U+E000 đến U+F8FF gồm 6.400 điểm mã được dành riêng cho mục đích nội bộ và không trùng với các ký tự chuẩn.
- **Tập hợp ký tự PUA hiện diện (Present PUA Set)**: Cấu trúc dữ liệu dạng tập hợp chứa các ký tự PUA được tìm thấy qua một lượt duyệt chuỗi đầu vào khi xảy ra va chạm ký tự đầu dãy.
- **Chế độ dự phòng cạn kiệt (Exhaustion Fallback)**: Trạng thái vận hành an toàn khi toàn bộ vùng PUA bị chiếm dụng, hệ thống xử lý nội dung mà không áp dụng dấu giữ chỗ, đảm bảo không làm hư hại dữ liệu người dùng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trong trường hợp phổ biến (không có ký tự U+E000 trong văn bản), tốc độ chọn ký tự giữ chỗ đạt độ phức tạp thời gian O(1) và không tiêu tốn bộ nhớ phụ.
- **SC-002**: Trong trường hợp có nhiều ký tự PUA va chạm ở đầu dãy, thời gian chọn ký tự giữ chỗ chỉ phụ thuộc tuyến tính vào độ dài văn bản O(N), loại bỏ hoàn toàn hiện tượng quét lặp lại toàn chuỗi O(k × N).
- **SC-003**: 100% bài kiểm thử đơn vị, kiểm thử tích hợp và kiểm thử hồi quy trong toàn bộ kho mã nguồn đều vượt qua thành công trên tất cả các môi trường CI.
- **SC-004**: Ca kiểm thử cạn kiệt 6.400 ký tự PUA xác nhận kết quả trả về `None` và quy trình nhập tài liệu diễn ra trơn tru mà không làm thay đổi bất kỳ ký tự nào của người dùng.

## Assumptions

- Vùng ký tự PUA được sử dụng là vùng Basic Multilingual Plane (BMP) Private Use Area với 6.400 ký tự từ U+E000 đến U+F8FF (`0xE000` đến `0xF8FF`).
- Trường hợp văn bản đầu vào chứa đủ 6.400 ký tự PUA là cực kỳ hiếm trong môi trường thực tế, do đó hành vi dự phòng an toàn (không thay thế dấu đóng giả) là lựa chọn hợp lý nhất mà không cần mở rộng sang các vùng PUA phụ khác.
- Việc tối ưu hóa thuật toán lựa chọn ký tự giữ chỗ không làm thay đổi hợp đồng giao diện công khai của bộ nhập Markdown.
