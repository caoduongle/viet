# Feature Specification: Khống chế bộ nhớ tập hợp PUA và chuẩn hóa thống kê kiểm thử hiệu năng

**Feature Branch**: `064-pua-memory-and-benchmark`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát commit a9da0c2 trên nhánh main: thay đổi mới vượt qua CI và thuật toán chọn ký tự có logic đúng, nhưng vẫn còn một vấn đề về sử dụng bộ nhớ cùng hai điểm cần cải thiện trong kiểm thử và tài liệu: (1) P2 — Giới hạn tập hợp chỉ chứa ký tự PUA: Trong markdown_importer.py, set(text) tạo tập hợp toàn bộ ký tự phân biệt của tài liệu rồi mới lọc vùng PUA, có thể tiêu tốn bộ nhớ tạm lớn khi tài liệu đa ngữ/nhiều ký tự phân biệt chứa U+E000. Cần chỉ thu thập các ký tự thuộc vùng PUA ngay trong lúc duyệt văn bản để tập hợp kết quả luôn bị chặn cứng tối đa 6.400 phần tử; (2) P3 — Sửa các tuyên bố về O(1) và số lượt quét trong docstring và tài liệu kỹ thuật: Làm rõ phép kiểm tra first_pua not in text có thời gian xấu nhất là O(N), ưu điểm là bộ nhớ phụ O(1); nhánh va chạm thực hiện 2 lượt quét chuỗi; (3) P3 — Cải thiện cách đo benchmark hiệu năng: Trong test_adversarial_complexity_multi_length_backticks_and_long_lines, thay thế việc chọn kết quả thấp hơn bằng phương pháp thống kê ổn định và không thiên vị (như trung vị / median của nhiều lượt chạy), giữ lại thông tin từng lượt để dễ chẩn đoán khi CI thất bại."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Khống chế tuyệt đối mức sử dụng bộ nhớ tạm khi tài liệu chứa U+E000 (Priority: P1) 🎯 MVP

Là người sử dụng ứng dụng để nạp các tài liệu văn bản lớn có bảng chữ cái đa dạng (văn bản đa ngữ, tài liệu kỹ thuật, chứa chữ Hán, chữ Nôm, ký hiệu toán) và có chứa ký tự `U+E000`, tôi muốn quá trình tìm ký tự giữ chỗ thay thế không tiêu tốn bộ nhớ tạm tỉ lệ thuận với toàn bộ các ký tự phân biệt trong tài liệu, mà chỉ tiêu tốn bộ nhớ tối đa giới hạn ở số lượng ký tự PUA thực tế (không vượt quá 6.400 phần tử), nhằm đảm bảo ứng dụng hoạt động ổn định và an toàn ngay cả trong môi trường tài nguyên hạn chế (như trình duyệt Web / WebAssembly).

**Why this priority**: Hiện tại, khi gặp `U+E000`, hệ thống khởi tạo tập hợp từ toàn bộ chuỗi văn bản (`set(text)`), gom mọi ký tự phân biệt trước khi lọc dải PUA. Với tài liệu lớn chứa hàng nghìn ký tự Unicode khác nhau, điều này tạo ra một lượng bộ nhớ tạm không cần thiết, đi ngược lại thiết kế ban đầu vốn chỉ cần theo dõi tối đa 6.400 ký tự PUA. Việc lọc trực tiếp các ký tự thuộc dải PUA ngay trong quá trình quét giúp khống chế cứng dung lượng bộ nhớ phụ ở mức tối thiểu.

**Independent Test**: Nhập văn bản lớn chứa hàng nghìn ký tự phân biệt (chữ Hán/Nôm, ký hiệu, văn bản đa ngữ) kèm theo ký tự `U+E000`; xác nhận tập hợp bộ nhớ tạm chỉ lưu trữ các điểm mã PUA thực tế, bộ nhớ phụ không vượt quá 6.400 phần tử, và kết quả chọn ký tự giữ chỗ vẫn chính xác tuyệt đối.

**Acceptance Scenarios**:

1. **Given** một tài liệu văn bản lớn chứa nhiều ký tự Unicode phân biệt ngoài dải PUA (ví dụ: chữ Nôm, chữ Hán, ký hiệu kỹ thuật) và có chứa `U+E000`, **When** hệ thống tìm ký tự giữ chỗ, **Then** hệ thống chỉ thu thập các điểm mã thuộc dải PUA, tập hợp lưu trữ không chứa bất kỳ ký tự nào ngoài dải PUA, và kích thước tập hợp luôn $\le 6.400$.
2. **Given** văn bản chỉ chứa đúng một ký tự PUA `U+E000` và hàng chục nghìn ký tự văn bản thông thường, **When** hàm tìm kiếm thực thi, **Then** dung lượng tập hợp lưu trữ nội bộ đúng bằng 1 phần tử và ký tự tiếp theo `U+E001` được trả về chính xác.
3. **Given** văn bản chứa toàn bộ 6.400 ký tự PUA xen lẫn các ký tự văn bản thông thường, **When** hàm tìm kiếm thực thi, **Then** hàm nhận biết trạng thái cạn kiệt và trả về `None` an toàn.

---

### User Story 2 - Đánh giá hiệu năng khách quan và ổn định bằng thống kê trung vị (Priority: P2)

Là kỹ sư kiểm thử và bảo trì kho mã nguồn, tôi muốn bài kiểm thử hiệu năng đối kháng (`test_adversarial_complexity_multi_length_backticks_and_long_lines`) sử dụng phương pháp thống kê trung vị (median) trên một số lượt đo cố định thay vì tự động chọn lại kết quả thấp hơn, để kết quả kiểm thử phản ánh trung thực hành vi hệ thống, lọc bỏ nhiễu ngẫu nhiên của môi trường mà không che giấu sự suy giảm hiệu năng thực sự (regression).

**Why this priority**: Cơ chế thử lại và lấy giá trị cực tiểu (`min(ratio, ratio_retry)`) có xu hướng thiên vị kết quả đo thuận lợi hơn, có nguy cơ bỏ sót các đợt suy giảm hiệu năng thực sự nếu một lần đo ngẫu nhiên rơi vào ngưỡng đạt. Sử dụng giá trị trung vị (median) của một tập các lượt chạy cố định là chuẩn mực thống kê trong đo lường phần mềm, vừa kháng nhiễu đột biến hiệu quả, vừa giữ tính khách quan và có thể tái lập.

**Independent Test**: Chạy bài kiểm thử hiệu năng đối kháng; xác nhận thuật toán thực hiện đo lường nhiều lượt cố định, tính toán tỷ lệ tăng trưởng dựa trên giá trị trung vị của thời gian thực thi, ghi nhật ký chẩn đoán chi tiết từng lượt đo và xác nhận tỷ lệ đạt ngưỡng tuyến tính $T(4N)/T(N) \le 6.0$.

**Acceptance Scenarios**:

1. **Given** bài kiểm thử hiệu năng đối kháng trên tập dữ liệu $N$, $2N$, $4N$, **When** kiểm thử được kích hoạt, **Then** hệ thống thực hiện số lượt đo lặp lại cố định cho mỗi kích thước dữ liệu và lấy giá trị trung vị của từng tập đo.
2. **Given** một lượt đo bị nhiễu do xung đột tài nguyên nền của hệ điều hành, **When** tính toán tỷ lệ tăng trưởng thời gian, **Then** giá trị trung vị loại bỏ ngoại lai đó một cách tự nhiên mà không cần nhánh logic điều kiện ưu tiên giá trị nhỏ hơn.
3. **Given** bài kiểm thử hoàn thành hoặc thất bại, **When** kiểm tra thông điệp báo cáo, **Then** thông tin chi tiết về từng lượt chạy (thời gian $T(N)$, $T(4N)$ của từng lần đo) được ghi nhận rõ ràng phục vụ chẩn đoán trên CI.

---

### User Story 3 - Chuẩn hóa tài liệu kỹ thuật và làm rõ độ phức tạp tính toán (Priority: P3)

Là người phát triển đọc mã nguồn và tài liệu kiến trúc, tôi muốn các tài liệu đặc tả, kế hoạch, mô hình dữ liệu, hợp đồng và docstring mô tả chính xác bản chất độ phức tạp tính toán của thuật toán (thời gian $O(N)$ cho thao tác tìm kiếm ký tự, bộ nhớ phụ $O(1)$ cho nhánh nhanh, và 2 lượt quét chuỗi khi xảy ra va chạm), nhằm duy trì tính liêm chính và sự nhất quán của tài liệu kỹ thuật.

**Why this priority**: Việc gọi phép kiểm tra chuỗi `first_pua not in text` là $O(1)$ là chưa chuẩn xác vì khi ký tự không xuất hiện trong chuỗi thì việc tìm kiếm đòi hỏi duyệt qua độ dài chuỗi $N$ ở mức độ mã máy (CPython Two-Way/Boyer-Moore). Tương tự, nhánh va chạm thực tế thực hiện 2 lượt quét chuỗi. Việc mô tả trung thực giúp lập trình viên hiểu rõ đặc tính vận hành của hệ thống.

**Independent Test**: Rà soát docstring của `_choose_fake_close_placeholder` và toàn bộ các tài liệu thuộc thư mục đặc tả; xác nhận mọi tuyên bố về độ phức tạp thời gian và không gian đều chuẩn xác và phân biệt rõ ràng.

**Acceptance Scenarios**:

1. **Given** docstring của hàm `_choose_fake_close_placeholder`, **When** đọc phần mô tả, **Then** nhánh kiểm tra nhanh được ghi nhận là thời gian duyệt chuỗi con $O(N)$ với bộ nhớ phụ $O(1)$ (không cấp phát tập hợp phụ).
2. **Given** tài liệu thiết kế và hợp đồng tính năng, **When** đọc phần phân tích độ phức tạp, **Then** nhánh va chạm được mô tả chính xác gồm lượt kiểm tra đầu tiên và lượt trích xuất ký tự PUA, với lượng bộ nhớ phụ bị chặn trên bởi $O(\min(N, 6400))$.

---

### Edge Cases

- Văn bản có hàng chục nghìn ký tự Unicode đa ngữ khác nhau (văn bản đa ngôn ngữ, font biểu tượng, ký hiệu toán học) kèm ký tự `U+E000`: tập hợp lưu trữ chỉ gom đúng các ký tự trong dải `[0xE000, 0xF8FF]`, tuyệt đối không lưu các ký tự khác.
- Văn bản không chứa bất kỳ ký tự PUA nào: nhánh kiểm tra nhanh tìm kiếm chuỗi con hoàn tất và trả về ngay `U+E000` mà không cấp phát bất kỳ tập hợp nào.
- Môi trường CI có tải nền dao động: thống kê trung vị trên 5 lượt đo đảm bảo kết quả đo đạc đại diện trung thực cho hiệu năng thuật toán, không bị sai lệch bởi một lần giật xung nhịp CPU.

## Requirements *(mandatory)*

### Functional Requirements

**Khống chế bộ nhớ tập hợp PUA (US1)**

- **FR-001**: Hệ thống MUST chỉ trích xuất và lưu trữ các điểm mã thuộc dải BMP PUA (từ `0xE000` đến `0xF8FF`) vào tập hợp điểm mã đã sử dụng (`used_cps`).
- **FR-002**: Quá trình thu thập ký tự PUA MUST NOT khởi tạo tập hợp chứa toàn bộ các ký tự phân biệt của chuỗi văn bản đầu vào.
- **FR-003**: Số lượng phần tử tối đa trong tập hợp điểm mã đã sử dụng MUST bị chặn cứng bởi hằng số `_FAKE_CLOSE_PUA_COUNT` (6.400 phần tử), hoàn toàn độc lập với độ dài hoặc tính đa dạng bảng chữ cái của văn bản đầu vào.
- **FR-004**: Kết quả lựa chọn ký tự giữ chỗ MUST tiếp tục bảo đảm tính tất định và chọn điểm mã nhỏ nhất khả dụng trong dải PUA chưa xuất hiện trong văn bản.

**Chuẩn hóa phương pháp thống kê đo lường hiệu năng (US2)**

- **FR-005**: Bài kiểm thử hiệu năng đối kháng `test_adversarial_complexity_multi_length_backticks_and_long_lines` MUST thực hiện số lượt đo lặp lại cố định (tối thiểu 3 lượt, khuyến nghị 5 lượt) cho mỗi kích thước dữ liệu $N$, $2N$, $4N$.
- **FR-006**: Tỷ lệ tăng trưởng thời gian MUST được tính toán dựa trên giá trị thống kê trung vị (median) của các lượt đo tương ứng, không sử dụng cơ chế chọn lọc nhánh có kết quả thấp nhất (`min`).
- **FR-007**: Bài kiểm thử MUST cung cấp thông tin chi tiết về các giá trị đo đạc thành phần trong thông điệp khẳng định (assertion message) để hỗ trợ chẩn đoán chính xác khi kiểm thử không đạt.

**Chuẩn hóa tài liệu kỹ thuật và độ phức tạp (US3)**

- **FR-008**: Docstring của hàm `_choose_fake_close_placeholder` MUST mô tả chính xác:
  - Nhánh kiểm tra nhanh: thời gian tìm chuỗi con $O(N)$ (tối ưu hóa ở tầng C), bộ nhớ phụ $O(1)$.
  - Nhánh va chạm: thực hiện quét chuỗi trích xuất PUA với bộ nhớ phụ bị chặn $O(\min(N, 6400))$.
- **FR-009**: Toàn bộ tài liệu đặc tả, kế hoạch triển khai, mô hình dữ liệu và hợp đồng MUST phân định rõ ràng giữa độ phức tạp thời gian thực thi và độ phức tạp không gian bộ nhớ phụ.

### Key Entities

- **Tập hợp PUA bị chặn cứng (Bounded PUA Set)**: Cấu trúc tập hợp số nguyên chứa duy nhất các điểm mã trong khoảng $[0xE000, 0xF8FF]$ xuất hiện trong văn bản, kích thước tối đa 6.400 phần tử.
- **Thống kê trung vị benchmark (Median Benchmark Statistic)**: Giá trị nằm ở vị trí chính giữa của dãy số đo thời gian thực thi được sắp xếp, đóng vai trò đại diện tin cậy cho thời gian xử lý và triệt tiêu các giá trị ngoại lai ngẫu nhiên.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Kích thước tập hợp bộ nhớ tạm trong hàm chọn ký tự PUA không bao giờ vượt quá 6.400 phần tử trên bất kỳ văn bản đầu vào nào (kể cả văn bản hàng triệu ký tự với hơn 50.000 ký tự phân biệt).
- **SC-002**: Bài kiểm thử hiệu năng đối kháng chạy ổn định trên các nền tảng kiểm thử (Windows, Linux CI, Python 3.12, 3.13, 3.14) với tỷ lệ trung vị $T(4N)/T(N) \le 6.0$, không phát sinh tình trạng kết quả dao động thiếu ổn định.
- **SC-003**: 100% tài liệu kỹ thuật, docstring và hợp đồng phản ánh chính xác độ phức tạp thời gian và không gian, không còn tuyên bố thời gian $O(1)$ cho thao tác quét chuỗi con.
- **SC-004**: Toàn bộ 1.327+ bài kiểm thử hiện có của hệ thống tiếp tục vượt qua 100% mà không có bất kỳ hồi quy nào về bảo toàn LaTeX hay xử lý Markdown.

## Assumptions

- Việc sử dụng cơ chế quét trực tiếp ký tự PUA (ví dụ biểu thức chính quy pre-compile `[\uE000-\uF8FF]` hoặc duyệt lọc) ở tầng C đem lại hiệu năng tương đương hoặc vượt trội mà không cần phân bổ bộ nhớ cho toàn bộ ký tự trong văn bản.
- Đo đạc với mẫu 5 lượt chạy và lấy trung vị là đủ để triệt tiêu nhiễu môi trường trên các hệ thống CI ảo hóa mà không kéo dài đáng kể thời gian chạy test suite.
