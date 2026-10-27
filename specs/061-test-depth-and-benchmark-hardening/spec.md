# Feature Specification: Gia cố kiểm thử đóng khối toán theo độ sâu và bổ sung bất biến công thức trong benchmark

**Feature Branch**: `061-test-depth-and-benchmark-hardening`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Rà soát sau commit 3cfdcd0 (CI 5/5 xanh): Bản sửa đã xử lý đúng hướng lỗi trạng thái công thức trong blockquote và bảo toàn mã nguồn. Cần khắc phục các điểm yếu còn lại trong bộ kiểm thử: (P2) Kiểm thử đóng công thức ở đúng độ sâu chưa đủ chặt: trong test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close(), ca kiểm thử có dòng đóng giả >> $$ trong khi công thức mở ở > $$, nhưng kết quả chỉ được xác nhận bằng assert isolated_nested.endswith('$$'). Cần kiểm tra kết quả đầy đủ của _isolate_display_math_blocks() và import_text() để xác nhận dòng >> $$ không đóng khối toán cấp 1, nội dung > x = 2 được giữ đúng ngữ cảnh và chỉ dòng đóng > $$ mới kết thúc khối; (P3) Bài benchmark test_adversarial_complexity_multi_length_backticks_and_long_lines() chưa xác nhận trực tiếp việc chuyển đổi công thức toán trong dữ liệu benchmark; (P3) Benchmark có thể thay đổi trạng thái garbage collector của môi trường kiểm thử do luôn gọi gc.enable() trong finally, cần lưu và khôi phục đúng trạng thái ban đầu qua gc.isenabled()."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Xác minh chặt chẽ quy tắc đóng khối toán đúng độ sâu trích dẫn (Priority: P1)

Là người bảo trì bộ tiền xử lý Markdown, tôi cần ca kiểm thử đóng khối toán trích dẫn xác minh cấu trúc chuỗi đầu ra đầy đủ và kết quả phân tích khối tài liệu hoàn chỉnh, nhằm chứng minh dứt điểm rằng dòng đóng giả ở độ sâu trích dẫn lồng nhau (`>> $$`) không bao giờ làm đóng sớm khối toán mở ở cấp ngoài (`> $$`).

**Why this priority**: Khẳng định `assert isolated_nested.endswith("$$")` hiện tại quá lỏng, có thể vô tình báo xanh ngay cả khi bộ tiền xử lý đóng nhầm khối toán sớm ở `>> $$` rồi xử lý các dòng tiếp theo theo một nhánh lỗi khác. Việc kiểm tra cấu trúc đầu ra chi tiết cả ở bước cô lập lẫn bước nhập tài liệu hoàn chỉnh là điều kiện tiên quyết để đảm bảo tính đúng đắn của máy trạng thái.

**Independent Test**: Chạy bài kiểm thử `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` với đầu vào lồng nhau:
```markdown
> $$
> x = 1
>> $$
> x = 2
> $$
```
Xác nhận rằng:
1. Ở bước `_isolate_display_math_blocks()`: dòng `>> $$` và `> x = 2` vẫn nằm nguyên vẹn bên trong khối toán `$$` bắt đầu từ dòng 1 và chỉ kết thúc ở dòng `> $$` cuối cùng; không sinh ra các khối phân cách ngắt quãng dở dang.
2. Ở bước `import_text()`: toàn bộ khối toán trích dẫn được trích xuất thành đúng 1 đối tượng `MathBlock` duy nhất chứa toàn bộ nội dung LaTeX (`x = 1\n>> $$\n> x = 2`), không bị xé nhỏ thành các khối toán rời hay đoạn văn bản bị lỗi.

**Acceptance Scenarios**:

1. **Given** tài liệu Markdown có khối toán nhiều dòng mở ở trích dẫn cấp 1 (`> $$`), tiếp theo là dòng `> x = 1`, một dòng đóng giả ở trích dẫn cấp 2 (`>> $$`), một dòng nội dung tiếp theo (`> x = 2`) và dòng đóng thật ở cấp 1 (`> $$`), **When** chạy qua `_isolate_display_math_blocks()`, **Then** kết quả đầu ra xác nhận khối toán duy nhất kéo dài từ dòng mở đầu tiên đến dòng đóng cuối cùng, không có dòng phân cách trống chen ngang trước dòng `>> $$`.
2. **Given** cùng đầu vào trên, **When** chạy qua `import_text()`, **Then** danh sách khối công thức `MathBlock` của tài liệu chứa chính xác 1 khối công thức duy nhất với nội dung LaTeX đầy đủ đại diện cho toàn bộ biểu thức nhiều dòng bên trong trích dẫn.

---

### User Story 2 - Xác nhận trực tiếp việc chuyển đổi công thức và tính toàn vẹn của mã trong benchmark (Priority: P2)

Là người bảo trì hiệu năng hệ thống, tôi cần bài đo hiệu năng đối kháng đa độ dài backtick và dòng dài không chỉ đo thời gian chạy $O(n)$ mà phải trực tiếp xác minh việc chuyển đổi các công thức toán hợp lệ và tính toàn vẹn của các khối mã nguồn trong dữ liệu benchmark.

**Why this priority**: Việc kiểm tra số lượng các đoạn văn bản dài hay chuỗi đại diện chưa đủ để khẳng định các bộ chuyển đổi công thức (`_normalize_math_delimiters` và `_isolate_display_math_blocks`) hoạt động chính xác trên dữ liệu có mật độ backtick phức tạp. Cần có các bất biến đầu ra cụ thể khẳng định các công thức toán được chuẩn hóa và tách khối đúng quy định.

**Independent Test**: Chạy bài benchmark `test_adversarial_complexity_multi_length_backticks_and_long_lines()` và xác nhận rằng trên cả 3 kích thước $N, 2N, 4N$, các chỉ số biến đổi công thức (như số lượng các mẫu công thức toán hiển thị hợp lệ ngoài vùng mã, các rào chắn mã và định dạng khối) khớp chính xác với tỷ lệ $N, 2N, 4N$ dự kiến.

**Acceptance Scenarios**:

1. **Given** dữ liệu kiểm thử đối kháng được sinh với $N, 2N, 4N$ đoạn, **When** chạy qua toàn bộ pipeline tiền xử lý, **Then** số lượng các cấu trúc công thức hiển thị hợp lệ sau chuẩn hóa (như các khối công thức tách dòng độc lập `$$display_formula$$` hoặc `$$x=1$$`) được đếm và xác nhận khớp với quy luật phân bổ dữ liệu sinh.
2. **Given** các đoạn mã nguồn và ký hiệu mã giả lập trong dữ liệu đối kháng, **When** kết thúc đo lường, **Then** tất cả các phần tử mã nguồn đại diện được xác nhận bảo toàn đầy đủ, đồng thời tỷ lệ thời gian $T(4N)/T(N) \le 6.0$ tiếp tục được thỏa mãn.

---

### User Story 3 - Bảo toàn trạng thái Garbage Collector ban đầu trong các bài benchmark (Priority: P3)

Là người bảo trì hạ tầng kiểm thử, tôi cần các bài kiểm thử hiệu năng đối kháng khi tạm thời vô hiệu hóa bộ thu gom rác (garbage collector) để đo đạc chính xác thì phải ghi nhớ trạng thái ban đầu và khôi phục đúng trạng thái đó sau khi chạy xong.

**Why this priority**: Việc luôn gọi `gc.enable()` trong khối `finally` sẽ vô tình kích hoạt lại garbage collector trong những môi trường kiểm thử hoặc tiến trình mà GC đã được chủ động tắt từ trước, vi phạm tính độc lập và vệ sinh của môi trường kiểm thử (test suite isolation).

**Independent Test**: Chạy kiểm thử khi GC đang tắt (`gc.disable()`); sau khi bài benchmark hoàn thành, kiểm tra `gc.isenabled()` vẫn phải là `False`. Chạy kiểm thử khi GC đang bật (`gc.enable()`); sau khi bài benchmark hoàn thành, `gc.isenabled()` vẫn là `True`.

**Acceptance Scenarios**:

1. **Given** môi trường kiểm thử đang có garbage collector hoạt động (`gc.isenabled() == True`), **When** bài benchmark kết thúc, **Then** garbage collector tiếp tục ở trạng thái hoạt động (`True`).
2. **Given** môi trường kiểm thử đã chủ động tắt garbage collector (`gc.isenabled() == False`), **When** bài benchmark kết thúc, **Then** garbage collector vẫn ở trạng thái tắt (`False`), không bị kích hoạt lại ngoài ý muốn.

---

### Edge Cases

- Dòng đóng giả trong trích dẫn có thêm khoảng trắng thụt lề hoặc ký tự phân cách (ví dụ `>>   $$   `): máy trạng thái vẫn nhận diện đúng độ sâu trích dẫn là 2 ($> 1$) và không kích hoạt đóng khối toán cấp 1.
- Khối toán mở ở trích dẫn cấp 2 (`>> $$`) và gặp dòng đóng ở trích dẫn cấp 1 (`> $$`): theo quy tắc thoát khối chứa, dòng này có độ sâu trích dẫn thấp hơn ($1 < 2$) nên phải thoát trạng thái khối toán cấp 2 chứ không phải đóng bình thường.
- Môi trường kiểm thử có ngoại lệ phát sinh giữa quá trình đo benchmark: khối `finally` bắt buộc phải được thực thi để đảm bảo trạng thái GC ban đầu luôn được khôi phục nguyên vẹn.

## Requirements *(mandatory)*

### Functional Requirements

**Độ chặt kiểm thử đóng khối toán trích dẫn (US1)**

- **FR-001**: Bài kiểm thử `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` MUST kiểm tra chuỗi đầu ra hoàn chỉnh của `_isolate_display_math_blocks()` đối với ca kiểm thử lồng nhau (`> $$\n> x = 1\n>> $$\n> x = 2\n> $$`), xác nhận dòng `>> $$` không bị tách thành dòng đóng dở dang và nội dung `> x = 2` tiếp tục được giữ trong khối toán.
- **FR-002**: Bài kiểm thử MUST kiểm tra kết quả qua `import_text()`, khẳng định toàn bộ khối toán trích dẫn được trích xuất thành đúng 1 đối tượng `MathBlock` duy nhất chứa đầy đủ nội dung các dòng toán học bên trong, không có thêm khối toán thừa hay đoạn văn bản bị lỗi.

**Bất biến công thức trong benchmark (US2)**

- **FR-003**: Bài kiểm thử `test_adversarial_complexity_multi_length_backticks_and_long_lines` MUST bổ sung các khẳng định kiểm tra số lượng xuất hiện của các công thức toán học hợp lệ sau khi chạy qua toàn bộ pipeline tiền xử lý trên cả 3 kích thước $N, 2N, 4N$.
- **FR-004**: Tỷ lệ thời gian thực thi $T(4N)/T(N) \le 6.0$ MUST tiếp tục được duy trì ổn định cùng với việc thỏa mãn 100% các khẳng định bất biến bảo toàn mã và chuyển đổi công thức.

**Vệ sinh trạng thái Garbage Collector (US3)**

- **FR-005**: Các bài kiểm thử đối kháng đo hiệu năng (`test_adversarial_complexity_unclosed_backticks_and_blockquotes` và `test_adversarial_complexity_multi_length_backticks_and_long_lines`) MUST ghi nhớ trạng thái kích hoạt của bộ thu gom rác trước khi đo thông qua `gc.isenabled()`.
- **FR-006**: Trong khối `finally`, hệ thống MUST chỉ kích hoạt lại garbage collector nếu trạng thái ghi nhớ ban đầu là đang bật (`if was_gc_enabled: gc.enable()`), đảm bảo không làm thay đổi trạng thái môi trường kiểm thử bên ngoài.

### Key Entities

- **Độ sâu trích dẫn hợp lệ khi đóng công thức**: Độ sâu trích dẫn của dòng kết thúc công thức phải trùng khớp tuyệt đối với độ sâu trích dẫn tại thời điểm mở khối toán (`bq_depth == math_bq_depth`).
- **Trạng thái bộ thu gom rác (GC State)**: Cờ boolean xác định bộ thu gom rác tự động của môi trường Python đang bật hay tắt tại thời điểm bắt đầu một ca kiểm thử.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các khẳng định về cấu trúc đầu ra của `_isolate_display_math_blocks()` và danh sách khối `MathBlock` từ `import_text()` trong ca kiểm thử đóng lồng nhau vượt qua với độ chính xác tuyệt đối.
- **SC-002**: Bài kiểm thử hiệu năng đối kháng xác nhận 100% các bất biến về số lượng công thức toán học và cấu trúc mã nguồn trên cả 3 kích thước $N, 2N, 4N$ trong khi vẫn duy trì tỷ lệ thời gian $T(4N)/T(N) \le 6.0$.
- **SC-003**: 100% các bài kiểm thử benchmark khôi phục nguyên vẹn trạng thái ban đầu của Garbage Collector khi chạy kiểm thử trong cả hai trường hợp GC đang bật và GC đang tắt.
- **SC-004**: Toàn bộ hệ thống kiểm tra chất lượng (Ruff, 1,325+ bài test Pytest, Node test runner, Pyodide Golden Master 8/8 và 19 bài test Playwright E2E) đạt 100% thành công.

## Assumptions

- Quy tắc máy trạng thái trong `MarkdownImporter` đã được triển khai chính xác tại Feature 060; các điểm cần xử lý trong tính năng này tập trung vào việc nâng cấp độ chặt của bộ kiểm thử, hoàn thiện các khẳng định bất biến và vệ sinh môi trường đo lường.
- Việc kiểm tra chi tiết cấu trúc đầu ra của `_isolate_display_math_blocks()` và `import_text()` không làm ảnh hưởng đến hiệu năng thời gian chạy của bộ kiểm thử chính.
- Không thay đổi mã nguồn triển khai nghiệp vụ của `chuviettay` trừ khi phát hiện thêm trường hợp biên thực tế trong quá trình siết chặt kiểm thử.
