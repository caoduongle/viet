# Feature Specification: Đo lường trực tiếp bộ nhớ PUA và kịch bản tái lập benchmark độc lập

**Feature Branch**: `065-pua-verification-reproducibility`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Tôi đã kiểm tra commit mới nhất của repo caoduongle/viet, đối chiếu với bản trước a9da0c2, đọc phần mã Markdown importer, các bài kiểm thử và bộ tài liệu Feature 064. Kết luận: bạn đã khắc phục đúng cả ba vấn đề chính của lần rà soát trước. Tôi không phát hiện lỗi chức năng nghiêm trọng mới trong phần thay đổi này. Tuy nhiên, vẫn còn một vài điểm P3 về độ tin cậy của kiểm thử và tính nhất quán của tài liệu nên hoàn thiện: (1) P3-1. Bài test mang tên kiểm tra bộ nhớ chưa đo trực tiếp bộ nhớ: Test test_pua_memory_bounded_multilingual kiểm tra các kết quả như U+E000 được chọn làm ký tự giữ chỗ tiếp theo, chuỗi va chạm trả về đúng ký tự và trường hợp cạn kiệt trả về None. Nó chưa trực tiếp đo bộ nhớ đỉnh hoặc kiểm tra số phần tử của tập hợp nội bộ. Nên cân nhắc bổ sung phép đo bộ nhớ có kiểm soát hoặc tách phần thu thập PUA thành một hàm nội bộ có thể kiểm thử trực tiếp; (2) P3-2. Số liệu benchmark trong tài liệu chưa có quy trình tái lập đi kèm: research.md đưa ra các số liệu thời gian cụ thể và mức tăng tốc khoảng 20–25 lần nhưng chưa có script benchmark độc lập kèm đủ thông tin môi trường và cách chạy để tái lập. Cần phân biệt số liệu của findall() trong bảng thực nghiệm với triển khai hiện tại sử dụng finditer(). Nên ghi rõ phương pháp được đo và môi trường thực nghiệm, hoặc chuyển các kết quả chưa tái lập được thành ước lượng thay vì kết luận chắc chắn."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đo lường trực tiếp và kiểm chứng số lượng phần tử tập hợp PUA (Priority: P1) 🎯 MVP

Là một kỹ sư duy trì chất lượng phần mềm, tôi muốn có cơ chế kiểm thử trực tiếp đo lường số lượng phần tử của tập hợp điểm mã PUA và giám sát mức đỉnh bộ nhớ tạm thời khi xử lý tài liệu đa ngữ lớn có chứa ký tự va chạm, nhằm bảo đảm lâu dài rằng hệ thống không bao giờ bùng nổ bộ nhớ theo số lượng ký tự phân biệt của tài liệu.

**Why this priority**: Các bài kiểm thử trước đây chỉ kiểm tra giá trị trả về của ký tự giữ chỗ (`\ue001`, `\ue00a`, `None`), chưa xác nhận trực tiếp rằng tập hợp nội bộ thực sự chỉ chứa đúng số lượng điểm mã PUA đã dùng và không giữ các ký tự ngoài dải PUA. Việc bổ sung kiểm chứng định lượng trực tiếp và đo lường bộ nhớ có kiểm soát giúp ngăn ngừa hoàn toàn các hồi quy ngầm về sau.

**Independent Test**:
- Kiểm tra trực tiếp hàm trích xuất điểm mã PUA với văn bản chứa 10.000 ký tự phân biệt (chữ Hán/Nôm) và ký tự `\ue000`: tập hợp kết quả chỉ chứa duy nhất 1 phần tử `{0xE000}`.
- Kiểm tra trực tiếp với chuỗi 10 ký tự PUA liên tiếp xen kẽ 10.000 ký tự đa ngữ: tập hợp kết quả chứa đúng 10 phần tử.
- Đo lường mức tăng bộ nhớ đỉnh (tracemalloc) trong quá trình quét tài liệu 10.000 ký tự đa ngữ có chứa `\ue000`: mức đỉnh bộ nhớ phụ phân bổ cho việc thu thập PUA nằm trong ngưỡng an toàn tuyệt đối ($\le 50\text{KB}$), chứng minh không bùng nổ theo kích thước bảng chữ cái tài liệu.

**Acceptance Scenarios**:
1. **Given** một văn bản lớn chứa 10.000 ký tự phân biệt ngoài dải PUA (như chữ Hán, chữ Nôm) và 1 ký tự `\ue000`, **When** gọi hàm thu thập điểm mã PUA, **Then** tập hợp thu được chỉ chứa duy nhất điểm mã `0xE000` và độ dài tập hợp chính xác bằng 1.
2. **Given** một văn bản chứa 10 ký tự PUA liên tiếp (`\ue000`..`\ue009`) xen kẽ trong 10.000 ký tự đa ngữ, **When** gọi hàm thu thập điểm mã PUA, **Then** tập hợp thu được chứa đúng 10 điểm mã tương ứng và độ dài tập hợp chính xác bằng 10.
3. **Given** văn bản thử nghiệm đa ngữ kích thước lớn có chứa ký tự va chạm, **When** chạy kiểm thử đo lường bộ nhớ đỉnh với công cụ theo dõi bộ nhớ chuẩn, **Then** bộ nhớ phụ cấp phát cho cấu trúc dữ liệu PUA không vượt quá 50KB và không tăng tỷ lệ thuận với số lượng ký tự phân biệt ngoài dải PUA.

---

### User Story 2 - Kịch bản thực nghiệm benchmark độc lập có thể tái lập (Priority: P2)

Là một nhà phát triển hoặc người đánh giá bên ngoài, tôi muốn có một kịch bản đo lường hiệu năng độc lập, có thể thực thi trực tiếp từ dòng lệnh để tái lập và đối chiếu các số liệu so sánh giữa các phương pháp thu thập PUA (`set(text)`, `findall`, `finditer`), kèm đầy đủ thông tin môi trường thực thi (phiên bản phần mềm, hệ điều hành, cấu hình vi xử lý).

**Why this priority**: Tính minh bạch và khả năng tái lập (reproducibility) là tiêu chuẩn hàng đầu trong kỹ thuật phần mềm. Việc cung cấp script độc lập giúp mọi bên có thể tự kiểm chứng các tuyên bố hiệu năng (như tốc độ tăng tốc và mức tiêu thụ bộ nhớ) trên chính môi trường của mình mà không cần đoán định.

**Independent Test**:
- Chạy một kịch bản dòng lệnh độc lập `python scripts/benchmark_pua_memory.py`. Kịch bản tự động sinh dữ liệu mẫu đa ngữ 1MB (10.000 ký tự phân biệt), thực hiện đo lường cả ba phương pháp và xuất báo cáo so sánh chi tiết gồm thời gian chạy trung bình, bộ nhớ đỉnh và tỷ lệ tăng tốc.

**Acceptance Scenarios**:
1. **Given** môi trường dòng lệnh đã cài đặt Python, **When** người dùng thực thi `python scripts/benchmark_pua_memory.py`, **Then** kịch bản thực thi thành công từ đầu đến cuối mà không yêu cầu thêm phụ thuộc ngoài thư viện chuẩn.
2. **Given** kịch bản benchmark đang chạy, **When** hoàn tất các vòng đo, **Then** kịch bản in ra bảng tổng kết chứa thông tin môi trường (phiên bản Python, hệ điều hành, vi xử lý) và các chỉ số định lượng rõ ràng cho cả 3 phương án: Baseline `set(text)`, Regex `findall()` và Triển khai `finditer()` có thoát sớm.
3. **Given** kết quả thực nghiệm từ kịch bản, **When** đối chiếu giữa `finditer` và `set(text)` trên dữ liệu đa ngữ 1MB, **Then** phương pháp `finditer` thể hiện thời gian thực thi nhanh hơn rõ rệt ($\ge 10\text{x}$) và bộ nhớ đỉnh thấp hơn đáng kể.

---

### User Story 3 - Chuẩn hóa tài liệu thực nghiệm và phân định đặc tính kỹ thuật (Priority: P3)

Là một người đọc tài liệu dự án, tôi muốn tài liệu kỹ thuật phân định rõ ràng giữa phương pháp `finditer()` (đang được triển khai trong mã nguồn) với `findall()` và `set(text)`, giải thích rõ ràng sự khác biệt về đặc tính cấp phát bộ nhớ trung gian và cung cấp hướng dẫn cách tự chạy script tái lập.

**Why this priority**: Tránh gây nhầm lẫn giữa dữ liệu thực nghiệm sơ bộ (sử dụng `findall`) với mã nguồn thực tế (sử dụng `finditer` để tránh tạo danh sách trung gian), đảm bảo tính nhất quán tuyệt đối giữa mã nguồn, kiểm thử và tài liệu.

**Independent Test**:
- Rà soát các tài liệu thiết kế và kiểm tra xem có mô tả rõ ràng sự khác biệt giữa `finditer` và `findall`, kèm hướng dẫn lệnh chạy kịch bản tái lập.

**Acceptance Scenarios**:
1. **Given** tài liệu nghiên cứu và thiết kế, **When** người đọc xem phần so sánh các phương án, **Then** tài liệu phân biệt tường minh sự khác biệt về bộ nhớ giữa `findall()` (tạo danh sách đối sánh trung gian) và `finditer()` (lặp luồng đối sánh trực tiếp, không cấp phát danh sách).
2. **Given** tài liệu hướng dẫn kiểm chứng (quickstart), **When** người dùng muốn tái lập số liệu, **Then** tài liệu cung cấp cú pháp dòng lệnh chính xác để kích hoạt kịch bản benchmark độc lập.

---

### Edge Cases

- **Tài liệu hoàn toàn không có ký tự PUA**: Hàm thu thập PUA trả về tập hợp rỗng (`set()`), bộ nhớ phụ bằng $0$.
- **Tài liệu chứa toàn bộ 6.400 ký tự PUA ở ngay đầu văn bản**: Hàm thu thập PUA đạt trần 6.400 phần tử và kích hoạt cơ chế thoát sớm ngay lập tức, không quét tiếp phần văn bản còn lại.
- **Tài liệu có ký tự Unicode ngoài BMP (Surrogate / Supplementary Planes như Emoji, CJK Extension B/C)**: Biểu thức chính quy không đối sánh nhầm các ký tự này vào tập hợp BMP PUA, bảo đảm tập hợp chỉ chứa các điểm mã từ `0xE000` đến `0xF8FF`.
- **Môi trường chạy có biến động tải CPU**: Script benchmark độc lập thực hiện nhiều lượt lặp (ít nhất 5 lượt) và tính giá trị trung bình/trung vị để giảm thiểu ảnh hưởng của nhiễu điều phối hệ điều hành.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI cung cấp phương thức nội bộ cho phép trích xuất trực tiếp tập hợp các điểm mã PUA xuất hiện trong văn bản mà không bị phụ thuộc vào logic tìm kiếm ký tự giữ chỗ bên ngoài.
- **FR-002**: Tập hợp điểm mã PUA thu được từ phương thức nội bộ PHẢI có kích thước không bao giờ vượt quá 6.400 phần tử và chỉ chứa các số nguyên trong đoạn `[0xE000, 0xF8FF]`.
- **FR-003**: Bộ kiểm thử PHẢI có bài kiểm tra trực tiếp số lượng phần tử của tập hợp PUA thu thập được trên văn bản chứa nhiều ký tự phân biệt ngoài dải PUA (như chữ Hán/Nôm).
- **FR-004**: Bộ kiểm thử PHẢI có bài kiểm tra đo lường bộ nhớ đỉnh có kiểm soát (sử dụng `tracemalloc`), xác nhận mức phân bổ bộ nhớ phụ cho tập hợp PUA không tăng theo quy mô số lượng ký tự phân biệt của tài liệu và duy trì dưới ngưỡng an toàn 50KB.
- **FR-005**: Dự án PHẢI cung cấp một kịch bản dòng lệnh độc lập để đo đạc và tái lập số liệu hiệu năng (thời gian, bộ nhớ) giữa các phương án `set(text)`, `findall` và `finditer`.
- **FR-006**: Kịch bản benchmark độc lập PHẢI tự động phát hiện và hiển thị siêu dữ liệu môi trường (phiên bản Python, hệ điều hành, nền tảng phần cứng) cùng kết quả so sánh định lượng.
- **FR-007**: Tài liệu nghiên cứu và đặc tả PHẢI phản ánh chính xác phương pháp `finditer` đang triển khai thực tế, ghi rõ điều kiện môi trường đo đạc và hướng dẫn tái lập.

---

### Key Entities *(include if feature involves data)*

- **PUA Codepoint Set (`used_cps`)**: Tập hợp các số nguyên biểu diễn điểm mã Unicode trong khoảng `[0xE000, 0xF8FF]` xuất hiện trong văn bản. Kích thước tập hợp bị chặn cứng ở mức tối đa 6.400 phần tử.
- **Benchmark Metric Report**: Bản ghi cấu trúc kết quả đo lường hiệu năng gồm phương pháp (`set_text`, `regex_findall`, `regex_finditer`), kích thước dữ liệu thử nghiệm, thời gian thực thi trung bình, bộ nhớ đỉnh và tỷ lệ tăng tốc tương đối.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các bài kiểm thử đơn vị về số lượng phần tử tập hợp PUA và kiểm thử đo lường bộ nhớ đỉnh `tracemalloc` vượt qua thành công trên môi trường CI.
- **SC-002**: Kịch bản benchmark độc lập có thể thực thi trơn tru bằng một lệnh duy nhất (`python scripts/benchmark_pua_memory.py`) trong thời gian dưới 15 giây và xuất đầy đủ bảng số liệu so sánh.
- **SC-003**: Mức tăng bộ nhớ phụ đo được khi quét 10.000 ký tự phân biệt có chứa `\ue000` được chứng minh thấp hơn ít nhất 5 lần so với phương pháp `set(text)` ban đầu.
- **SC-004**: Tài liệu kỹ thuật cung cấp đầy đủ thông tin môi trường và hướng dẫn từng bước để bất kỳ bên thứ ba nào cũng có thể tái lập được kết quả đo lường.

---

## Assumptions

- Môi trường thử nghiệm hỗ trợ thư viện chuẩn `tracemalloc` của Python (sẵn có từ Python 3.4+ trên mọi nền tảng Windows, Linux, macOS).
- Kịch bản benchmark được thiết kế bằng thư viện chuẩn của Python (`re`, `time`, `tracemalloc`, `platform`, `sys`), không yêu cầu thêm bất kỳ thư viện bên ngoài nào để đảm bảo tính độc lập tối đa.
- Việc tách hàm nội bộ trích xuất điểm mã PUA giữ nguyên tính toàn vẹn và giao diện công khai của `MarkdownImporter._choose_fake_close_placeholder`.
