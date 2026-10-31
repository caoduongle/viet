# Feature Specification: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu (067-content-seed-bank-hardening)

**Feature Branch**: `067-content-seed-bank-hardening`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Rà soát repository viet (commit 3b20612): Ưu tiên P1 bảo toàn thông báo nội dung không hỗ trợ từ Markdown sang Web UI; P2 khắc phục va chạm PUA qua HTML entity, sửa nhận diện dấu escape chẵn/lẻ của công thức, tăng độ ổn định Seed khi tài liệu có nhiều từ lặp (300-1.000 lần), kiểm tra đầy đủ tham số chất lượng chữ viết và kiểu dữ liệu Boolean trong WriteOptions; P3 làm rõ chế độ nhập DOCX Content-First, tạo API snapshot một lượt cho tab Kho mẫu và bổ sung kiểm thử hồi quy hiệu năng."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Minh bạch hóa nội dung không hỗ trợ và bảo toàn thông báo khi nhập Markdown / DOCX (Priority: P1) 🎯 MVP

Là một người dùng biên soạn tài liệu Markdown hoặc nạp tệp DOCX trên giao diện Web để xuất bản viết tay, tôi muốn hệ thống hiển thị đầy đủ, rõ ràng mọi thành phần nội dung không được hỗ trợ hoặc bị giản lược cấu trúc (như khối mã, đường kẻ ngang, bảng lồng trong danh sách, hình ảnh, khối trích dẫn), kèm theo loại thành phần, vị trí dòng và cách hệ thống đã xử lý, nhằm đảm bảo không có bất kỳ nội dung nào của tôi bị lược bỏ âm thầm khi xuất ra trang viết tay.

**Why this priority**: Bảo toàn dữ liệu và sự minh bạch với người dùng là ưu tiên số một. Hiện tại, bộ nhập Markdown ghi nhận các phần tử không hỗ trợ nhưng cầu nối trình duyệt không chuyển tiếp danh sách này sang giao diện, dẫn đến việc người dùng xuất tài liệu bị mất khối mã, hình ảnh hoặc đường kẻ mà không hề hay biết. Ngoài ra, thông báo khi nạp tệp DOCX đang bị xóa mất ngay khi bản xem trước đầu tiên kết xuất xong.

**Independent Test**:
- Nhập một tài liệu Markdown chứa khối mã (code block), đường kẻ ngang (`---`), hình ảnh (`![ minh họa ](img.png)`), khối trích dẫn (`> trích dẫn`) và bảng nằm trong danh sách vào giao diện Web; xác nhận kết quả trả về từ cầu nối và khu vực thông báo trên giao diện hiển thị đầy đủ cả cảnh báo (`warnings`) lẫn danh sách thành phần không hỗ trợ/giản lược (`unsupported`) với thông tin loại thành phần, vị trí và cách xử lý.
- Nạp một tệp `.docx` có cảnh báo/thành phần không hỗ trợ vào trình soạn thảo; xác nhận sau khi bản xem trước tự động kết xuất hoàn tất, thông báo từ lần nạp DOCX vẫn được giữ lại và hiển thị rõ chế độ Content-First thay vì bị ghi đè mất.

**Acceptance Scenarios**:

1. **Given** tài liệu Markdown đầu vào có chứa khối mã (fenced/indented code block), đường kẻ ngang (`---`), hoặc bảng lồng trong mục danh sách, **When** người dùng kết xuất văn bản qua luồng Web, **Then** kết quả trả về chứa đầy đủ danh sách `unsupported` và giao diện hiển thị thông báo rõ loại thành phần, vị trí dòng trong tài liệu và trạng thái xử lý (đã lược bỏ hoặc giản lược).
2. **Given** tài liệu Markdown có chứa hình ảnh (`![alt](url)`) hoặc khối trích dẫn (`> ...`), **When** hệ thống phân tích tài liệu, **Then** hệ thống ghi nhận rõ thông báo rằng hình ảnh không được vẽ nét (giữ văn bản thay thế nếu có) và cấu trúc trích dẫn được làm phẳng thành đoạn văn chuẩn, đồng thời hiển thị thông báo này trên giao diện người dùng.
3. **Given** người dùng mở hoặc kéo thả một tệp `.docx` vào trình soạn thảo Web, **When** tệp được chuyển đổi sang Markdown và kích hoạt kết xuất xem trước ngay lập tức, **Then** các cảnh báo và mục không hỗ trợ phát sinh từ bước nhập `.docx` được bảo toàn trên bảng thông báo sau khi lượt kết xuất xem trước hoàn tất, kèm chỉ dẫn rõ đây là chế độ ưu tiên nội dung (Content-First).

---

### User Story 2 - Chống biến đổi nội dung người dùng do va chạm ký tự giữ chỗ PUA và dấu thoát công thức (Priority: P1)

Là một người dùng soạn thảo tài liệu kỹ thuật hoặc toán học phức tạp có chứa mã thực thể HTML (HTML entities), ký tự Unicode vùng Private Use Area (PUA), công thức lồng trong khối trích dẫn và nhiều dấu gạch chéo ngược (`\`) liên tiếp trước dấu phân cách công thức, tôi muốn bộ phân tích Markdown bảo toàn tuyệt đối từng ký tự gốc của tôi và nhận diện chính xác khi nào dấu phân cách công thức thực sự bị thoát (escaped) hay hợp lệ.

**Why this priority**: Đây là các lỗi đường biên có khả năng làm thay đổi trực tiếp nội dung văn bản của người dùng (biến ký tự hợp lệ `&#xE000;` thành dấu `$$` hoặc nhận diện sai công thức `\\\(` có số chẵn dấu gạch chéo ngược phía trước).

**Independent Test**:
- Phân tích tài liệu Markdown có chứa chuỗi thực thể HTML `&#xE000;` (hoặc `&#57344;`) cùng với khối công thức `$$` lồng trong trích dẫn `>>`; xác nhận ký tự giải mã từ thực thể HTML được giữ nguyên là `U+E000`, tuyệt đối không bị biến thành `$$`.
- Phân tích tài liệu có 1, 2, 3 và 4 dấu `\` trước các dấu mở/đóng công thức `\(`, `\)`, `\[`, `\]` (cả bên ngoài và bên trong khối mã); xác nhận số lẻ dấu `\` phía trước delimiter sẽ thoát delimiter (giữ làm văn bản thường), còn số chẵn dấu `\` phía trước delimiter cho phép delimiter hoạt động như công thức toán hợp lệ.

**Acceptance Scenarios**:

1. **Given** văn bản Markdown chứa thực thể HTML biểu diễn ký tự vùng PUA (ví dụ `&#xE000;`, `&#57344;`) hoặc ký tự PUA trực tiếp đồng thời có khối công thức `$$` trong blockquote lồng nhau, **When** bộ nhập Markdown phân tích cú pháp và khôi phục dấu đóng giả, **Then** chỉ đúng những vị trí dấu đóng giả do hệ thống đánh dấu mới được khôi phục về `$$`, còn ký tự của người dùng (kể cả sau khi giải mã HTML entity) được giữ nguyên vẹn 100%.
2. **Given** văn bản có $k$ dấu gạch chéo ngược `\` liên tiếp đứng ngay trước dấu mở hoặc đóng công thức (`\(`, `\)`, `\[`, `\]`) ở ngoài khối mã, **When** hệ thống chuẩn hóa dấu phân cách công thức, **Then** nếu $k$ là số lẻ (ví dụ 1 hoặc 3 dấu `\` trước delimiter) thì delimiter được xem là bị thoát và giữ nguyên văn bản; nếu $k$ là số chẵn (ví dụ 0, 2 hoặc 4 dấu `\` trước delimiter) thì delimiter được nhận diện là công thức toán hợp lệ và bảo toàn các cặp `\\` phía trước.
3. **Given** các chuỗi chứa bất kỳ tổ hợp dấu `\` và `\(`, `\[` nào nằm bên trong khối mã (code fence, indented code block) hoặc đoạn mã nội dòng (code span), **When** hệ thống xử lý tài liệu, **Then** toàn bộ nội dung bên trong mã nguồn được giữ nguyên tuyệt đối không thay đổi.

---

### User Story 3 - Ổn định biến thể nét chữ khi chỉnh sửa tài liệu dài có tần suất từ lặp cao và kiểm soát chặt tham số viết (Priority: P2)

Là một người học hoặc giáo viên soạn thảo bài giảng dài có các từ phổ biến (như "là", "và", "của", "có", "trong") lặp lại hàng trăm đến hàng nghìn lần, tôi muốn khi chèn, sửa hoặc xóa một đoạn văn ở giữa tài liệu, toàn bộ các từ không thay đổi ở phía trước và phía sau vị trí chỉnh sửa vẫn giữ nguyên hoàn toàn biến thể nét chữ đã chọn trước đó; đồng thời mọi tham số cấu hình chất lượng chữ viết không hợp lệ phải bị chặn ngay từ đầu.

**Why this priority**: Mục tiêu cốt lõi của tính năng ổn định biến thể (`stable_variants`) là giữ cho trang viết tay không bị "nhảy" nét chữ khi người dùng chỉnh sửa tài liệu. Thuật toán đối chiếu mặc định hiện tại bỏ qua các từ xuất hiện phổ biến trong tài liệu dài, làm các từ phía sau điểm sửa bị đổi kiểu chữ. Bên cạnh đó, các tham số điều khiển khoảng cách chữ cái và độ cao chữ chưa được kiểm tra biên an toàn.

**Independent Test**:
- Tạo tài liệu có một từ tiếng Việt phổ biến lặp lại từ 300 đến 1.000 lần; kết xuất lần 1, sau đó chèn một đoạn văn mới vào giữa tài liệu và kết xuất lần 2; đối chiếu chỉ số lần xuất hiện (`occurrence`) và hình học nét chữ của tất cả các từ không đổi ở nửa sau tài liệu: phải trùng khớp 100% với trước khi chèn.
- Khởi tạo và kiểm tra hợp lệ tùy chọn viết với các giá trị biên hoặc sai kiểu (`letter_gap < 0`, `target_xh <= 0`, `pen_clearance_factor < 0`, `NaN`, `Infinity`, chuỗi ký tự, hoặc truyền số/chuỗi vào các cờ Boolean): hệ thống từ chối ngay với thông báo lỗi rõ ràng.

**Acceptance Scenarios**:

1. **Given** một tài liệu dài chứa từ 300 đến 1.000 lần xuất hiện của cùng một từ hoặc ký hiệu, **When** người dùng chèn, sửa hoặc xóa một đoạn văn ở giữa tài liệu và kết xuất lại với chế độ ổn định biến thể, **Then** 100% các từ không bị chỉnh sửa ở cả trước và sau vị trí can thiệp đều giữ nguyên chỉ số `occurrence` và hình học biến thể nét chữ như ban đầu.
2. **Given** bộ tùy chọn điều khiển chất lượng chữ viết, **When** người dùng hoặc lệnh gọi truyền giá trị âm, bằng 0 (đối với chiều cao chữ mục tiêu), `NaN`, vô cực (`Infinity`), vượt ngưỡng an toàn trên hoặc sai kiểu dữ liệu cho `letter_gap`, `target_xh`, `pen_clearance_factor`, **Then** hệ thống phát hiện và báo lỗi kiểm tra hợp lệ ngay lập tức trước khi dàn trang.
3. **Given** các tùy chọn kiểu logic (Boolean) như tự động chuẩn hóa chiều cao chữ, ổn định biến thể, ghép chữ cái, căn dòng kẻ và phân biệt hoa thường, **When** truyền giá trị không phải kiểu Boolean thực sự (ví dụ số nguyên, chuỗi `"false"`, `null`), **Then** bộ kiểm tra từ chối dữ liệu sai kiểu để ngăn ngừa hành vi ép kiểu ngầm định gây sai lệch kết xuất.

---

### User Story 4 - Tăng tốc tải tab Kho mẫu bằng cơ chế Snapshot một lượt và hiển thị lỗi minh bạch (Priority: P3)

Là một người dùng sở hữu kho mẫu chữ viết tay lớn (nhiều chữ cái, chữ số, dấu câu, ký hiệu toán học và dấu thanh), tôi muốn việc chuyển sang hoặc làm mới tab Kho mẫu diễn ra tức thì chỉ với một lần truy vấn dữ liệu tổng hợp và bỏ qua việc tải lại khi kho mẫu chưa có thay đổi mới, đồng thời mọi lỗi phát sinh khi đọc từng danh mục phải được thông báo rõ ràng thay vì bị ẩn đi.

**Why this priority**: Giảm độ trễ giao tiếp tuần tự giữa giao diện chính và tiến trình nền khi kho mẫu lớn, đồng thời loại bỏ việc nuốt lỗi âm thầm giúp người dùng và nhà phát triển nhận biết ngay khi dữ liệu danh mục gặp sự cố.

**Independent Test**:
- Mở tab Kho mẫu lần đầu: giao diện chỉ gửi một yêu cầu lấy bản chụp tổng hợp duy nhất để nhận đủ thống kê, toàn bộ danh mục và số hiệu phiên bản (`revision`).
- Gọi làm mới tab Kho mẫu lần thứ hai khi kho mẫu không có thay đổi: hệ thống đối chiếu `revision` không đổi và giữ nguyên danh sách hiển thị mà không phải dựng lại toàn bộ thẻ DOM.
- Mô phỏng lỗi khi tải dữ liệu kho mẫu: giao diện hiển thị thông báo lỗi rõ ràng cho người dùng thay vì bỏ qua âm thầm.

**Acceptance Scenarios**:

1. **Given** người dùng mở hoặc làm mới tab Kho mẫu, **When** giao diện yêu cầu dữ liệu từ tiến trình xử lý, **Then** toàn bộ thông tin thống kê, danh sách chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh và số hiệu phiên bản kho mẫu (`revision`) được trả về trong một phản hồi tổng hợp duy nhất.
2. **Given** tab Kho mẫu đã hiển thị dữ liệu ở phiên bản `revision` hiện tại, **When** hàm làm mới được gọi lại nhưng kho mẫu chưa có bất kỳ thao tác thêm, xóa hay nạp mới nào, **Then** giao diện nhận biết phiên bản không thay đổi và bỏ qua việc tải lại cũng như tránh vẽ lại toàn bộ lưới thẻ.
3. **Given** có lỗi xảy ra trong quá trình truy xuất toàn bộ kho mẫu hoặc một danh mục thành phần, **When** giao diện nhận phản hồi, **Then** giao diện hiển thị thông báo lỗi cụ thể trên màn hình thay vì âm thầm bỏ qua.

---

### User Story 5 - Kiểm thử hồi quy hiệu năng tự động cho các luồng xử lý cốt lõi (Priority: P3)

Là một kỹ sư duy trì hệ thống, tôi muốn có bộ công cụ và bài kiểm thử đo lường hiệu năng cho bộ phân tích Markdown (với các kích thước tài liệu tăng dần), thuật toán đối chiếu hạt giống tài liệu dài có nhiều từ lặp, và truy vấn bản chụp kho mẫu, nhằm phát hiện sớm các suy giảm hiệu năng hoặc độ phức tạp thuật toán bất thường qua các lần cập nhật mã nguồn.

**Why this priority**: Đảm bảo các cải tiến về độ chính xác (như đối chiếu hạt giống cho tài liệu lặp và xử lý placeholder an toàn) luôn duy trì tốc độ phản hồi nhanh và khả năng mở rộng ổn định.

**Independent Test**:
- Chạy kịch bản benchmark và bài kiểm thử smoke test hiệu năng: xác nhận việc phân tích tài liệu Markdown (10 KB, 100 KB, 1 MB), đối chiếu hạt giống tài liệu dài (300–1.000 từ lặp) và tạo bản chụp kho mẫu đều hoàn tất thành công và xuất báo cáo định lượng rõ ràng.

**Acceptance Scenarios**:

1. **Given** bộ kiểm thử hiệu năng của dự án, **When** thực thi kiểm tra trên tài liệu Markdown kích thước lớn và tài liệu có 1.000 từ lặp lại khi chỉnh sửa, **Then** quá trình xử lý hoàn tất trong giới hạn thời gian tuyến tính hợp lý mà không gây nghẽn tiến trình.
2. **Given** kịch bản đo hiệu năng chạy ở chế độ kiểm tra tự động (smoke test), **When** thực thi trong quy trình kiểm thử, **Then** kịch bản xuất đầy đủ số liệu thời gian xử lý và bộ nhớ tiêu thụ theo cấu trúc chuẩn để đối chiếu giữa các phiên bản.

---

### Edge Cases

- **Tài liệu chứa đồng thời ký tự PUA trực tiếp (`\uE000`), thực thể HTML thập lục phân (`&#xE000;`), thực thể thập phân (`&#57344;`) và công thức `$$` trong blockquote lồng nhiều cấp**: Cơ chế đánh dấu và khôi phục dấu đóng giả phải phân biệt chính xác tuyệt đối vị trí do hệ thống tạo ra với nội dung của người dùng.
- **Dấu gạch chéo ngược ở ngay đầu chuỗi hoặc liền kề nhiều công thức trên cùng một dòng (`\\(a\\) \\\(b\\\) \\\\(c\\\\)`)**: Bộ đếm dấu `\` liên tiếp hoạt động độc lập cho từng vị trí dấu mở và dấu đóng mà không bị lệch chỉ số chuỗi.
- **Tài liệu chỉnh sửa có toàn bộ nội dung chỉ gồm 1 từ duy nhất lặp lại 1.000 lần**: Khi chèn thêm 5 từ khác vào vị trí thứ 500, đúng 500 từ đầu và 500 từ cuối vẫn bảo toàn nguyên vẹn `occurrence` từ 0 đến 999 như tài liệu gốc.
- **Truyền giá trị kiểu `bool` (`True`/`False`) vào các trường số thực/số nguyên như `scale`, `letter_gap`, `target_xh`, `pen_clearance_factor`**: Trong một số ngôn ngữ, kiểu logic là lớp con của số nguyên (`True == 1`, `False == 0`); hệ thống kiểm tra hợp lệ phải từ chối tường minh giá trị `bool` ở tất cả các tham số số học.
- **Tài liệu Markdown có nhiều đoạn ngắt trang (`<!-- pagebreak -->`) và mỗi trang đều có thành phần không hỗ trợ**: Các cảnh báo và thành phần không hỗ trợ từ tất cả các phân đoạn trang phải được gom đầy đủ, không bị trùng lặp rác hoặc mất thông tin giữa các trang.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bộ nhập Markdown PHẢI ghi nhận đầy đủ các thành phần chưa được hỗ trợ kết xuất nét vẽ hoặc bị giản lược cấu trúc:
  - Giữ nguyên định dạng mã định danh chuẩn trong `ImportResult.unsupported` đối với `code_block` (`"code_block"` hoặc `"code_block: {info}"`), đường kẻ ngang (`"hr: horizontal rule"`), bảng nằm trong mục danh sách (`"table: table inside list item"`), và bổ sung ghi nhận hình ảnh (`"image"` hoặc `"image: {alt}"` khi có văn bản thay thế) vào `ImportResult.unsupported` để đảm bảo tương thích ngược 100% với bộ kiểm thử hợp đồng hiện có.
  - Ghi nhận thông báo làm phẳng khối trích dẫn (`blockquote`) vào `ImportResult.warnings` (tương tự như thông báo giản lược định dạng in đậm/in nghiêng/code nội dòng) vì nội dung văn bản và công thức bên trong trích dẫn vẫn được kết xuất đầy đủ.
- **FR-002**: Cầu nối trình duyệt (`BrowserBridge.write_text`) PHẢI chuyển tiếp đầy đủ cả danh sách `warnings` và danh sách `unsupported` từ bộ nhập tài liệu về cho giao diện Web.
- **FR-003**: Giao diện soạn thảo Web (`write.js`) PHẢI hiển thị rõ ràng cả cảnh báo (`warnings`) và thông báo nội dung không hỗ trợ (`unsupported` — được chuyển đổi sang thông điệp tiếng Việt thân thiện nêu rõ loại thành phần và cách xử lý), đồng thời bảo toàn các thông báo phát sinh khi nạp tệp `.docx` (chế độ Content-First) qua lượt kết xuất xem trước tự động ngay sau đó (và tự động xóa thông báo nạp tệp cũ khi người dùng mở tệp mới hoặc xóa trắng trình soạn thảo).
- **FR-004**: Bộ nhập Markdown PHẢI sử dụng cơ chế chọn ký tự giữ chỗ PUA an toàn trước va chạm: nhánh kiểm tra nhanh (`fast-path`) trong `_choose_fake_close_placeholder` PHẢI kiểm tra thêm điều kiện không có chuỗi thực thể số `"&#"` trong văn bản, và `_collect_used_pua_codepoints` PHẢI thu thập cả điểm mã PUA trực tiếp lẫn điểm mã PUA biểu diễn qua thực thể HTML thập lục phân/thập phân (`&#x...;`, `&#...;`, kể cả khi có số `0` đứng đầu), đảm bảo tuyệt đối không làm biến đổi các ký tự của người dùng sau khi giải mã thực thể.
- **FR-005**: Bộ chuẩn hóa dấu phân cách công thức (`\(`, `\)`, `\[`, `\]`) trong `_convert_delimited` PHẢI xác định trạng thái thoát (escaped) bằng cách đếm số lượng dấu gạch chéo ngược (`\`) liên tiếp đứng ngay trước dấu phân cách: số lẻ là bị thoát (giữ làm văn bản thường), số chẵn là dấu phân cách công thức hoạt động bình thường; đồng thời khi `strip=True` (đối với `\(...\)`) phải bảo vệ trường hợp nội dung công thức kết thúc bằng khoảng trắng có dấu thoát `\ ` để không vô tình biến dấu `$` đóng thành `\$`.
- **FR-006**: Thuật toán đối chiếu hạt giống tài liệu (`align_document_seeds`) PHẢI kết hợp bước cắt bỏ tiền tố/hậu tố chung không đổi trong thời gian tuyến tính $O(N)$ trước khi gọi `SequenceMatcher(..., autojunk=False)` trên vùng chỉnh sửa trung gian, bảo toàn chính xác 100% thứ tự xuất hiện (`occurrence`) và hình học nét chữ của các từ/ký hiệu không thay đổi khi tài liệu có từ lặp lại từ 300 đến 1.000+ lần mà không gây suy giảm hiệu năng bậc hai $O(N^2)$ trên tài liệu dài.
- **FR-007**: Phương thức kiểm tra tùy chọn viết (`WriteOptions.validate`) PHẢI kiểm tra kiểu số thực/số nguyên hợp lệ (`isinstance(val, (int, float)) and not isinstance(val, bool)`), tính hữu hạn (`math.isfinite`) và miền giá trị hợp lệ kèm ngưỡng chặn trên an toàn cho `letter_gap` ($0.0 \le x \le 10.0$), `target_xh` ($0.0 < x \le 100.0$), `pen_clearance_factor` ($0.0 \le x \le 10.0$) cũng như từ chối kiểu `bool` ở tất cả các tham số số học khác (`scale`, `line`, `width`, `space`, `jitter`, `wscale`, `paper_width`, `paper_height`, `margin_*`, `background_spacing`, `background_margin`).
- **FR-008**: Phương thức `WriteOptions.validate` PHẢI kiểm tra nghiêm ngặt kiểu dữ liệu Boolean thực sự (`isinstance(val, bool)`) cho các cờ cấu hình (`auto_xh`, `stable_variants`, `assemble_letters`, `snap_to_ruling`, `strict_case`, `missing_grid`).
- **FR-009**: Cầu nối trình duyệt (`BrowserBridge`), trình điều phối Worker (`py-worker.js`) và giao diện Kho mẫu (`bank.js`) PHẢI hỗ trợ truy vấn bản chụp tổng hợp (`get_bank_snapshot`) trả về thống kê, toàn bộ các danh mục mẫu (`letters`, `digits`, `punct`, `symbols`, `marks`) và số hiệu phiên bản (`revision`) trong một lượt gọi duy nhất, bỏ qua việc dựng lại DOM khi `(revision, profileId)` chưa đổi, tự động làm mới khi khởi động lại Worker hoặc đổi hồ sơ, và hiển thị thông báo rõ ràng khi có lỗi tải dữ liệu.
- **FR-010**: Hệ thống PHẢI có các bài kiểm thử tự động xác định (deterministic) cho CI và bài kiểm thử hiệu năng (`@pytest.mark.benchmark`) xác nhận tính đúng đắn và tốc độ xử lý cho các luồng phân tích Markdown, đối chiếu hạt giống tài liệu lặp và truy xuất bản chụp kho mẫu mà không gây lỗi dao động thời gian (flaky tests) trên CI.

### Key Entities *(include if feature involves data)*

- **Unsupported Content Notice**: Bản ghi thông báo về thành phần tài liệu không được hỗ trợ hoặc bị giản lược, bao gồm định danh loại thành phần (khối mã, hình ảnh, đường kẻ ngang, bảng lồng, khối trích dẫn), vị trí dòng trong văn bản nguồn và mô tả cách hệ thống xử lý.
- **Document Seed Alignment Mapping**: Cấu trúc ánh xạ bảo toàn chỉ số xuất hiện (`occurrence`) của từng từ, ký hiệu và công thức giữa tài liệu gốc và tài liệu đã chỉnh sửa, độc lập với tần suất lặp lại của từ trong tài liệu.
- **Bank Snapshot**: Gói dữ liệu tổng hợp trạng thái kho mẫu tại một thời điểm, bao gồm số hiệu phiên bản (`revision`), thống kê tổng quan (`stats`), và danh sách nhãn kèm số lượng mẫu của tất cả các danh mục (`letters`, `digits`, `punct`, `symbols`, `marks`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các thành phần không hỗ trợ hoặc bị giản lược trong Markdown (khối mã, đường kẻ ngang, bảng trong danh sách, hình ảnh, khối trích dẫn) và DOCX đều được trả về và hiển thị minh bạch trên giao diện Web; 0 trường hợp nội dung bị lược bỏ âm thầm không có thông báo.
- **SC-002**: 0 trường hợp ký tự người dùng (bao gồm ký tự vùng PUA và thực thể HTML `&#xE000;`, `&#57344;`) bị biến đổi sai lệch thành ký hiệu toán học `$$` sau khi phân tích cú pháp.
- **SC-003**: 100% các trường hợp có 1, 2, 3, 4 hoặc nhiều hơn dấu gạch chéo ngược `\` trước dấu mở/đóng công thức được phân loại đúng theo quy tắc chẵn/lẻ, và 100% nội dung trong khối mã được bảo toàn nguyên vẹn.
- **SC-004**: Trong tài liệu chứa từ 300 đến 1.000 lần xuất hiện của cùng một từ, khi chèn hoặc xóa một đoạn văn ở giữa tài liệu, 100% các từ không chỉnh sửa ở phần còn lại giữ nguyên chỉ số `occurrence` và tạo ra tọa độ hình học nét chữ giống hệt 100% so với trước khi chỉnh sửa.
- **SC-005**: 100% các giá trị đầu vào không hợp lệ (`NaN`, `Infinity`, số âm, vượt ngưỡng trên, sai kiểu dữ liệu giữa số và Boolean) trong tùy chọn viết đều bị phát hiện và chặn lại bởi bộ kiểm tra hợp lệ.
- **SC-006**: Số lần giao tiếp thông điệp với tiến trình nền khi làm mới tab Kho mẫu giảm từ 4 lượt gọi tuần tự xuống còn 1 lượt gọi duy nhất, và giảm xuống 0 lượt dựng lại lưới giao diện khi phiên bản kho mẫu (`revision`) không thay đổi.
- **SC-007**: Thời gian đối chiếu hạt giống cho tài liệu có 1.000 từ lặp lại hoàn tất trong dưới 200ms trên môi trường tiêu chuẩn mà không gây suy giảm trải nghiệm gõ phím.

---

## Assumptions

- Đối với các thành phần Markdown chưa có biểu diễn đồ họa viết tay riêng trong giai đoạn hiện tại (như hình ảnh nhúng, khối mã nguồn, đường kẻ ngang, bảng lồng trong danh sách), hành vi chuẩn của hệ thống ở chế độ ưu tiên nội dung (Content-First) là giữ lại văn bản thay thế/nội dung chữ (đối với hình ảnh và trích dẫn) hoặc bỏ qua khối không hỗ trợ (đối với khối mã, đường kẻ ngang, bảng trong danh sách) đồng thời thông báo chi tiết trên giao diện để người dùng chủ động kiểm soát.
- Các ngưỡng chặn trên hợp lý cho các tham số chất lượng chữ viết được thiết lập đủ rộng cho mọi nhu cầu sử dụng thực tế (ví dụ: `letter_gap` trong khoảng $[0.0, 10.0]$, `target_xh` trong khoảng $(0.0, 100.0]$ pt, `pen_clearance_factor` trong khoảng $[0.0, 10.0]$) để vừa chặn các giá trị cực đoan gây hỏng bố cục vừa không hạn chế khả năng tùy biến hợp lệ của người dùng.
- Chế độ nhập DOCX trên trình duyệt Web hoạt động theo hướng Content-First (chuyển đổi sang Markdown để tái dàn trang và chỉnh sửa trực tiếp), trong khi chế độ bảo toàn bố cục tuyệt đối (Fidelity) dành cho môi trường có công cụ kết xuất trang nền tương ứng; giao diện Web cần giải thích rõ đặc điểm này ngay khi người dùng nạp tệp DOCX.
