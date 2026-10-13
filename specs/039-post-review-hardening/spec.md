# Feature Specification: Củng cố và xử lý các vấn đề sau rà soát bản Web-only (Post-Review Hardening)

**Feature Branch**: `039-post-review-hardening`

**Created**: 2026-10-13

**Status**: Approved

**Input**: User description: "Kết quả rà soát mới nhất của repo viet (commit 46467eb). Xử lý các vấn đề: P1 Phạm vi DOCX fidelity trên Web-only; P2 Khóa RNG hình học theo token_id và loại nội dung; P2 Biến thể độc lập cho công thức toán lặp lại; P2 Đồng bộ metadata phiên bản; Củng cố hợp đồng RenderItem (hỗ trợ slice) và xác nhận CI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phân định rõ ràng năng lực xử lý tệp DOCX trên Web Client (Priority: P1)

Người dùng mở một tài liệu `.docx` có sẵn trong Web Client để chuyển đổi sang văn bản viết tay. Hệ thống thực hiện chuyển đổi nội dung văn bản, bảng biểu và công thức toán sang chữ viết tay theo luồng dàn trang của ứng dụng, đồng thời thông báo minh bạch về năng lực xử lý (chuyển đổi nội dung, không duy trì bố cục toạ độ cố định theo trang Word). Người dùng không bị nhầm lẫn hay kỳ vọng sai về việc giữ nguyên từng pixel vị trí ảnh/văn bản của Word.

**Why this priority**: Đây là hồi quy chức năng và sự thay đổi kỳ vọng người dùng lớn nhất khi chuyển từ Desktop sang Web-only. Nếu không phân định rõ ràng giữa chuyển đổi nội dung (Content Import) và giữ nguyên bố cục (Fidelity Layout), người dùng sẽ gặp thất vọng hoặc nghi ngờ độ tin cậy của phần mềm.

**Independent Test**: Nhập một tệp DOCX chứa bảng biểu và văn bản vào Web Client; xác nhận nội dung xuất hiện đầy đủ trong trình soạn thảo với thông báo định hướng rõ ràng, và tài liệu hướng dẫn/giao diện không còn cam kết giữ nguyên toạ độ in Word.

**Acceptance Scenarios**:

1. **Given** người dùng nạp một tệp DOCX vào Web Client, **When** hệ thống xử lý tệp, **Then** toàn bộ nội dung văn bản, tiêu đề, bảng biểu và công thức toán được chuyển đổi thành công sang định dạng soạn thảo của ứng dụng với thông điệp rõ ràng về chế độ nhập nội dung.
2. **Given** người dùng tra cứu tài liệu sản phẩm hoặc giao diện Web, **When** tìm hiểu về tính năng nhập tệp DOCX, **Then** thông tin thể hiện chính xác phạm vi hỗ trợ của bản Web tĩnh, không còn cam kết giữ nguyên bố cục trang in cố định của Microsoft Word.
3. **Given** yêu cầu kiến trúc Web-only, **When** xử lý các thành phần phụ thuộc Word COM / LibreOffice, **Then** hệ thống xác định rõ Web Client chỉ hỗ trợ Content-First Import (chuyển đổi nội dung bảng biểu, công thức sang Markdown để viết tay theo luồng DocumentLayoutEngine); đồng thời cập nhật UI và tài liệu README nêu rõ không hỗ trợ giữ nguyên toạ độ in Word, đánh dấu module `chuviettay/fidelity/` là legacy/archive để tránh gây hiểu nhầm.

---

### User Story 2 - Đảm bảo tính độc lập và ổn định biến thể nét chữ giữa các đối tượng (Priority: P2)

Người dùng soạn thảo tài liệu có các từ giống nhau xuất hiện ở nhiều vị trí (trong văn bản thường, trong bảng biểu) hoặc các công thức toán lặp lại (ví dụ $x + 1$ ở nhiều dòng). Khi bật chế độ biến thể ổn định (`stable_variants`), các lần xuất hiện độc lập này sở hữu nét chữ đa dạng tự nhiên (không bị trùng lặp nét chữ cứng nhắc giống hệt nhau), đồng thời việc chèn thêm từ ở đầu tài liệu không làm thay đổi nét chữ của các đoạn phía sau.

**Why this priority**: Viết tay tự nhiên đòi hỏi các chữ giống nhau không bị lặp lại đơn điệu như font chữ in vi tính, nhưng vẫn phải giữ tính ổn định cục bộ khi hiệu chỉnh văn bản xung quanh.

**Independent Test**: Kết xuất một tài liệu có 2 từ giống nhau ở 2 đoạn và 2 công thức toán giống nhau; kiểm tra xem tọa độ nét chữ của hai lần xuất hiện có sự biến thiên tự nhiên, sau đó chèn thêm một đoạn mới ở đầu trang và xác minh các nét của đoạn ban đầu không thay đổi.

**Acceptance Scenarios**:

1. **Given** cùng một từ xuất hiện ở hai đoạn văn khác nhau hoặc một từ trong bảng và một từ ngoài văn bản, **When** kết xuất ở chế độ biến thể ổn định, Then khóa sinh ngẫu nhiên sử dụng định danh đối tượng và ngữ cảnh phân loại để tạo nét chữ tự nhiên, không bị trùng khóa jitter.
2. **Given** cùng một công thức toán (ví dụ `$x + 1$`) xuất hiện tại hai vị trí riêng biệt trong tài liệu, **When** bật biến thể ổn định, **Then** mỗi lần xuất hiện được gán ngữ cảnh định danh riêng biệt để tạo biến thể nét độc lập.
3. **Given** tài liệu đã kết xuất trước đó, **When** người dùng chèn thêm một câu mới vào đầu tài liệu, **Then** biến thể nét của các từ và công thức ở các đoạn phía sau hoàn toàn giữ nguyên.

---

### User Story 3 - Đồng bộ hóa metadata phiên bản phát hành xuyên suốt ứng dụng (Priority: P2)

Người dùng, nhà phát triển và các hệ thống CI/CD tra cứu thông tin phiên bản ở bất kỳ thành phần nào (Web UI, tệp cấu hình package, nhật ký thay đổi, tệp metadata phân phối) đều nhận được thông tin phiên bản nhất quán, rõ ràng và có thể kiểm chứng tự động.

**Why this priority**: Lệch phiên bản (ví dụ 2.1.0 ở CHANGELOG/Python, 2.0.0 ở pyproject, 1.0.0 ở Web) gây nhầm lẫn khi người dùng báo lỗi, khó khăn trong quản lý phát hành và giảm tính chuyên nghiệp của sản phẩm.

**Independent Test**: Chạy kịch bản kiểm tra metadata tự động; xác nhận mọi tệp định nghĩa phiên bản đều tuân thủ hợp đồng đồng bộ phiên bản đã quy ước.

**Acceptance Scenarios**:

1. **Given** các tệp quản lý phiên bản trong kho mã nguồn, **When** kiểm tra thông tin phiên bản, **Then** toàn bộ sản phẩm thống nhất một nguồn phiên bản chính thống duy nhất là `2.1.0`, đồng bộ xuyên suốt trên `pyproject.toml`, `package.json`, `chuviettay/__init__.py`, `CHANGELOG.md` và `version.json` do build tạo ra.
2. **Given** quy trình đóng gói Web tĩnh, **When** tệp `version.json` được tạo ra, **Then** thông tin phiên bản khớp chính xác với quy ước phiên bản đã xác định.
3. **Given** bộ kiểm thử tự động, **When** chạy bài kiểm tra phát hành, **Then** có một bài kiểm thử xác minh tính khớp nối 100% giữa các nguồn metadata phiên bản.

---

### User Story 4 - Hoàn thiện hợp đồng dữ liệu hiển thị RenderItem (Priority: P3)

Các lập trình viên và module xử lý bố cục có thể thao tác với đối tượng RenderItem một cách an toàn và linh hoạt: vừa có thể truy cập các thuộc tính định danh tường minh, vừa có thể trích xuất các tập con thuộc tính thông qua cú pháp cắt lát (slice indexing `item[:3]`), hoàn toàn đúng như docstring đã cam kết.

**Why this priority**: Tránh lỗi tiềm ẩn lúc chạy (`IndexError`) khi các hàm xử lý gọi lát cắt thay vì nén/giải nén thủ công, bảo vệ tính toàn vẹn của hợp đồng giao diện nội bộ.

**Independent Test**: Thực hiện gọi trực tiếp `item[:3]` và `item[1:4]` trên đối tượng `RenderItem` trong bài kiểm thử đơn vị; xác nhận kết quả trả về tương đương với thao tác trên tuple mà không phát sinh lỗi ngoại lệ.

**Acceptance Scenarios**:

1. **Given** một thể hiện của `RenderItem`, **When** mã nguồn thực thi thao tác cắt lát `item[:3]`, **Then** hệ thống trả về đúng bộ 3 phần tử đầu tiên `(start, strokes, width)`.
2. **Given** thao tác cắt lát với các dải chỉ số hợp lệ khác, **When** truy cập `item[start:stop:step]`, **Then** kết quả trả về danh sách các giá trị tương ứng chính xác.

---

### User Story 5 - Xác thực toàn diện bộ kiểm thử và quy trình CI trên commit Web-only (Priority: P3)

Đội ngũ phát triển và người dùng được bảo đảm rằng toàn bộ mã nguồn trên nhánh mặc định đã vượt qua 100% các bài kiểm tra chất lượng tự động (kiểm tra kiến trúc cấm Desktop, kiểm tra đơn vị, kiểm tra Golden Master và kiểm tra Lint), xác nhận trạng thái phát hành sạch.

**Why this priority**: Đảm bảo không có lỗi tiềm ẩn hay hồi quy chưa được phát hiện sau cuộc tái cấu trúc lớn loại bỏ giao diện Desktop.

**Independent Test**: Thực thi toàn bộ bộ kiểm thử tự động và công cụ phân tích tĩnh trong môi trường sạch; xác nhận tất cả đều báo trạng thái thành công.

**Acceptance Scenarios**:

1. **Given** kho mã nguồn sau khi hoàn tất các cải tiến, **When** chạy kiểm thử toàn diện, **Then** toàn bộ các bài kiểm thử tự động đều đạt kết quả thành công mà không có cảnh báo nghiêm trọng nào.
2. **Given** quy trình kiểm tra kiến trúc, **When** quét toàn bộ cây thư mục, **Then** không còn tệp dư thừa nào vi phạm quy tắc Web-only.

---

### Edge Cases

- Tệp DOCX tải lên chứa bảng lồng nhau hoặc các trường dữ liệu phức tạp: hệ thống cần trích xuất thông tin văn bản an toàn, ghi nhận cảnh báo nếu có phần tử bị giản lược thay vì làm sập ứng dụng.
- Công thức toán trống hoặc cú pháp LaTeX không hợp lệ: hệ thống xử lý nhẹ nhàng, không gây sập luồng dàn trang và không làm sai lệch bộ đếm seed của các công thức kế tiếp.
- Các token có chuỗi rỗng hoặc chỉ chứa ký tự khoảng trắng: cơ chế băm khóa RNG phải xử lý an toàn mà không ném lỗi băm.
- Thao tác cắt lát trên `RenderItem` với bước nhảy âm hoặc chỉ số vượt quá phạm vi: tuân thủ đúng hành vi chuẩn của Python slice trên chuỗi/bộ dữ liệu tuần tự.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST xử lý tệp `.docx` trong Web Client bằng cách nạp toàn bộ cấu trúc văn bản, bảng biểu và công thức toán học vào trình soạn thảo theo cơ chế Content-First.
- **FR-002**: Hệ thống MUST cung cấp thông báo rõ ràng trên giao diện và tài liệu về việc Web Client không hỗ trợ chế độ cố định toạ độ trang in Word (Fidelity Layout).
- **FR-003**: Hệ thống MUST xác định phạm vi Web Client là Content-First Import, cập nhật giao diện người dùng và tài liệu (README) nêu rõ không hỗ trợ giữ nguyên toạ độ trang in Word (Fidelity Layout), đồng thời đánh dấu module `chuviettay/fidelity/` là legacy/archive để phản ánh đúng thực tế kiến trúc Web tĩnh.
- **FR-004**: Bộ dàn trang MUST sử dụng `token_id` kết hợp với loại đối tượng nội dung (ví dụ: `text`, `symbol`, `math`, `table-cell`) làm khóa chính khi tạo bộ sinh ngẫu nhiên ScopedRNG cho biến dạng nét chữ.
- **FR-005**: Bộ dàn trang MUST quản lý bộ đếm xuất hiện theo ngữ cảnh khối văn bản hoặc toàn tài liệu để ngăn chặn trùng lặp khóa giữa các đoạn văn khác nhau.
- **FR-006**: Bộ xử lý công thức toán MUST đưa định danh xuất hiện hoặc ID khối công thức vào ngữ cảnh sinh seed, đảm bảo các công thức trùng nội dung LaTeX có biến thể nét tự nhiên riêng biệt.
- **FR-007**: Cơ chế sinh seed của công thức và token MUST duy trì tính ổn định: việc chèn thêm hoặc sửa đổi nội dung ở đoạn trước KHÔNG làm thay đổi seed hoặc biến dạng của các đoạn không bị sửa ở phía sau.
- **FR-008**: Hệ thống MUST định nghĩa một nguồn thông tin phiên bản duy nhất (Single Source of Truth) là `2.1.0`, đồng bộ nhất quán giữa tất cả các tệp khai báo metadata (`pyproject.toml`, `package.json`, `chuviettay/__init__.py`, `CHANGELOG.md`, `version.json`).
- **FR-009**: Script đóng gói Web MUST tự động đọc và đồng bộ thông tin phiên bản vào `version.json` từ nguồn phiên bản chính.
- **FR-010**: Bộ kiểm thử tự động MUST có bài kiểm tra đối chiếu tính nhất quán giữa tất cả các tệp khai báo phiên bản trong dự án.
- **FR-011**: Lớp `RenderItem` MUST hỗ trợ thao tác chỉ mục cắt lát (`__getitem__` với đối tượng `slice`), trả về danh sách hoặc tuple các phần tử tương ứng với dải chỉ số yêu cầu.
- **FR-012**: Toàn bộ bài kiểm thử tự động (Python core, kiến trúc Web-only, JS unit tests, lint) MUST vượt qua 100% trong quy trình CI.

### Key Entities *(include if feature involves data)*

- **RenderItem**: Đối tượng mang dữ liệu hiển thị của một mục trên dòng chữ (vị trí X, danh sách nét vẽ, độ rộng, token nội dung, `token_id` duy nhất, loại nội dung, thứ tự xuất hiện `occurrence`). Hỗ trợ cả truy cập thuộc tính, giải nén tuần tự và cắt lát `slice`.
- **ScopedRNG Context**: Cấu trúc ngữ cảnh dùng để dẫn xuất hạt giống ngẫu nhiên deterministically, bao gồm hạt giống tài liệu (`effective_seed`), loại nội dung (`content_type`), chuỗi token hoặc biểu thức, định danh duy nhất (`token_id` / `formula_id`), và kênh hiệu ứng (`"geom"`, `"width"`).
- **Release Metadata**: Tập hợp các thông số phiên bản sản phẩm gồm `version` (chuẩn SemVer), tên ứng dụng, thời điểm build, cam kết runtime, được chia sẻ nhất quán giữa backend lõi và frontend Web.
- **DocxImportDescriptor**: Mô hình dữ liệu mô tả kết quả nạp tệp DOCX gồm nội dung Markdown đã trích xuất, danh sách cảnh báo các thành phần không giữ nguyên định dạng gốc, và trạng thái hoàn tất.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% người dùng nạp tệp DOCX nhận được thông tin phản hồi rõ ràng về việc tài liệu được chuyển đổi nội dung vào trình soạn thảo và không cam kết giữ nguyên toạ độ in Word.
- **SC-002**: Tỉ lệ trùng lặp kiểu nét biến dạng giữa các từ giống nhau ở các khối khác nhau hoặc giữa các công thức toán giống nhau giảm về 0% (mỗi thực thể độc lập có biến thể riêng).
- **SC-003**: 100% các token ở các đoạn sau giữ nguyên biến thể nét vẽ khi thực hiện chèn thêm một câu vào đoạn đầu văn bản ở chế độ `stable_variants`.
- **SC-004**: Độ nhất quán phiên bản giữa các tệp khai báo (`pyproject.toml`, `package.json`, `CHANGELOG.md`, `__version__`, `version.json`) đạt 100% theo kiểm tra tự động.
- **SC-005**: 100% các bài kiểm thử tự động trong CI chạy thành công, thời gian thực thi toàn bộ test suite cục bộ dưới 45 giây.

## Assumptions

- Ứng dụng hiện tại định hướng phục vụ 100% người dùng qua giao diện Web Client (chạy trên trình duyệt qua WebAssembly/Pyodide); việc loại bỏ Desktop GUI và CLI là quyết định kiến trúc đã hoàn tất ở commit 46467eb.
- Việc xử lý DOCX trên trình duyệt ưu tiên tính độc lập của Client (Client-side tĩnh), không phụ thuộc vào máy chủ backend Windows để chạy Microsoft Word COM.
- Chế độ `stable_variants` ưu tiên tính ổn định cục bộ khi soạn thảo văn bản dài mà vẫn bảo tồn tính tự nhiên của chữ viết tay.
- Mọi thay đổi đều phải giữ nguyên tính tương thích với định dạng xuất `.xopp` của Xournal++ và chuẩn ảnh PNG/SVG.
