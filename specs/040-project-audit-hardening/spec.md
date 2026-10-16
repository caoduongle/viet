# Feature Specification: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng (Project Audit & Hardening)

**Feature Branch**: `040-project-audit-hardening`  
**Created**: 2026-10-16  
**Status**: Approved  
**Input**: User description: "rà soát toàn bộ dự án; lập kế hoạch cải thiện. Quyết định: bỏ cơ chế missing_grid tự động đẻ file _thieu.xopp; bỏ hẳn sinh lưới hw2; giữ fidelity/ làm archive; cho phép xóa repro_viet_baseline.py sau khi migrate test."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bảo toàn toàn vẹn nội dung khi nạp tệp DOCX vào Web Client qua Round-trip Markdown (Priority: P1)

Người dùng mở một tệp `.docx` chứa tiêu đề (Heading), phương trình toán độc lập (Display Math / `m:oMathPara`), công thức toán trong ô bảng, ký tự đặc biệt có ý nghĩa trong Markdown (`*`, `_`, `~`, `#`, `$`, `|`, `\`, `<`), ngắt dòng mềm (`LineBreak`) và danh sách. Hệ thống trích xuất toàn bộ sang Markdown với cơ chế escape ký tự đặc biệt an toàn, để khi nạp vào trình soạn thảo và biên dịch ngược lại qua `MarkdownImporter`, 100% nội dung gốc được bảo toàn mà không bị mất công thức toán, không vỡ cột bảng, và không biến các ký tự toán học thành thẻ định dạng kiểu chữ.

**Why this priority**: Hiện tại cầu nối `BrowserBridge._document_to_markdown_dict` chỉ duyệt các khối có `inlines` và bỏ sót hoàn toàn `MathBlock`. Khi chuyển sang Markdown, việc thiếu escape khiến `2*3*4` bị biến thành `234`, `$\|x\|$` làm vỡ bảng, và `LineBreak` trong ô bảng làm cắt đứt hàng của bảng.

**Independent Test**: Nạp một tệp `.docx` (hoặc Document IR) chứa tiêu đề, phương trình toán độc lập, bảng chứa công thức toán có dấu `|` và text chứa dấu `*`, `#`, `~`; kiểm tra chuỗi Markdown sinh ra được escape đúng và khi chạy qua `MarkdownImporter.import_text` tái tạo đúng 100% các khối và ký tự.

**Acceptance Scenarios**:
1. **Given** một tệp `.docx` có công thức toán độc lập (`MathBlock`) và công thức trong ô bảng, **When** nạp vào Web Client, **Then** các công thức xuất hiện đầy đủ dạng `$$...$$` (đoạn) và `$...$` (ô bảng có escape `\|`).
2. **Given** đoạn văn bản trong `.docx` chứa các ký tự Markdown đặc biệt (`*`, `_`, `~`, `#`, `$`, `\`), **When** chuyển sang Markdown, **Then** các ký tự được escape bằng dấu gạch chéo ngược `\` để không bị hiểu nhầm thành in đậm/nghiêng/tiêu đề.
3. **Given** ô bảng có nhiều dòng hoặc ngắt dòng mềm (`LineBreak`), **When** chuyển sang bảng Markdown, **Then** ngắt dòng được thay thế bằng khoảng trắng hợp lệ thay vì ký tự xuống dòng `\n` thô làm vỡ cấu trúc bảng.

---

### User Story 2 - Hỗ trợ căn lề đoạn văn (`left`, `center`, `right`, `justify`) ở cấp độ Core Engine & IR (Priority: P1)

Lập trình viên và các luồng xử lý tài liệu đưa vào `DocumentLayoutEngine` các đoạn văn (`Paragraph`) có thuộc tính `align` là `"left"`, `"center"`, `"right"`, hoặc `"justify"`. Bộ dàn trang tính toán chính xác tọa độ ngang `line_start_x` đối xứng theo khổ giấy cho căn giữa/phải, và phân bổ đều khoảng cách từ (word gaps) cho các dòng tràn trong chế độ căn đều hai bên (`justify`), đồng thời cập nhật đúng tọa độ hộp bao quanh từ (`token_layout_callback`).

**Why this priority**: `Paragraph.align` đã được định nghĩa trong mô hình IR và được `DocxImporter` trích xuất, nhưng `DocumentLayoutEngine` đang bỏ qua thuộc tính này. Việc chuẩn hóa thuật toán hình học tại Core Engine bảo đảm tính toàn vẹn của thư viện xử lý chữ viết tay.

**Independent Test**: Khởi tạo `Document` với 4 đoạn văn có `align` lần lượt là `left`, `center`, `right`, `justify`; chạy `render` và kiểm tra tọa độ `x` của từng dòng cùng tọa độ `TokenBox` ghi nhận được.

**Acceptance Scenarios**:
1. **Given** đoạn văn có `align="center"`, **When** dàn trang, **Then** `line_start_x` đặt chính giữa lề trang khả dụng `self.x0 + indent + rem_space / 2.0`.
2. **Given** đoạn văn có `align="right"`, **When** dàn trang, **Then** mép phải dòng chữ bám sát lề phải `self.x0 + indent + rem_space`.
3. **Given** đoạn văn nhiều dòng có `align="justify"`, **When** dàn trang, **Then** các dòng tràn được phân bổ khoảng cách đều giữa các từ; dòng kết thúc bởi `LineBreak` hoặc dòng cuối đoạn giữ căn trái tự nhiên.
4. **Given** đoạn văn căn trái mặc định `align="left"`, **When** dàn trang, **Then** kết quả tọa độ và nét vẽ khớp 100% với Golden Master hiện tại.

---

### User Story 3 - Bảo mật DOM chống XSS và Hiển thị SVG Xem thử thật trong Quản lý Kho mẫu (Priority: P1)

Người dùng mở tab Quản lý Kho mẫu để duyệt các ký tự (kể cả ký tự đặc biệt `<`, `>`, `&`, `"`, `'`) hoặc nhấn "Xem thử ngẫu nhiên". Giao diện mã hóa an toàn mọi nhãn ký tự và thông báo lỗi qua module tiện ích dùng chung trước khi đưa vào DOM; đồng thời hộp thoại "Xem thử ngẫu nhiên" giải nén dữ liệu `.xopp` từ Worker và dựng trực quan hình ảnh SVG nét chữ viết tay tương ứng với từng hạt giống ngẫu nhiên (cắt viewBox vừa vặn vùng nét vẽ, không render toàn bộ trang giấy A4 kẻ dòng).

**Why this priority**: Kho mẫu chứa các ký tự toán học `<`, `>`, `&`. Việc nối trực tiếp chuỗi vào `innerHTML` làm vỡ DOM và gây nguy cơ XSS khi nhập file kho mẫu từ bên ngoài. Ngoài ra modal xem thử trước đây chỉ in số `seed` mà không có hình vẽ nét chữ.

**Independent Test**: Nạp kho mẫu chứa các ký tự `<`, `>`, `&`, mở danh sách thẻ kho mẫu; xác nhận hiển thị text an toàn không có script execution; nhấn "Xem thử ngẫu nhiên" và xác nhận các khung xem thử vẽ hình ảnh nét chữ SVG với viewBox gọn gàng.

**Acceptance Scenarios**:
1. **Given** nhãn ký tự hoặc thông báo lỗi chứa ký tự HTML đặc biệt, **When** hiển thị trong danh sách thẻ hoặc modal, **Then** chuỗi được escape qua hàm `escapeHtml` dùng chung, không làm biến đổi cấu trúc HTML.
2. **Given** người dùng nhấn "Xem thử ngẫu nhiên", **When** Worker trả về kết quả, **Then** giao diện giải nén và vẽ SVG nét chữ tương ứng với từng seed, gửi kèm tùy chọn `missing_grid: false` để tránh rác MEMFS, và xử lý hủy kết quả cũ nếu người dùng chuyển nhãn khác.

---

### User Story 4 - Xử lý cú pháp Gạch ngang (`~~...~~`) và Cảnh báo định dạng chữ giàu trong `MarkdownImporter` (Priority: P2)

Người dùng soạn thảo Markdown có chứa cú pháp gạch ngang `~~văn bản~~` hoặc các kiểu chữ giàu (`**đậm**`, `*nghiêng*`, `` `mã` ``). Hệ thống loại bỏ cặp dấu `~~` thừa trong nét viết tay và ghi nhận cảnh báo rõ ràng vào danh sách `warnings` khi phát hiện các định dạng kiểu chữ giàu được giản lược về nét viết tay chuẩn.

**Why this priority**: Tránh để sót các ký tự `~~` thô trên trang giấy viết tay và thông báo minh bạch cho người dùng về việc làm phẳng định dạng kiểu chữ.

**Independent Test**: Chạy `import_text("~~chữ gạch~~ và **đậm**")`; xác nhận văn bản đầu ra là `chữ gạch và đậm` (không có `~~`) và `ImportResult.warnings` chứa thông điệp cảnh báo.

**Acceptance Scenarios**:
1. **Given** văn bản chứa `~~gạch ngang~~`, **When** phân tích cú pháp, **Then** nội dung chữ bên trong được trích xuất sạch sẽ không còn cặp dấu `~~`.
2. **Given** văn bản chứa các thẻ định dạng in đậm, in nghiêng, gạch ngang, mã nội tuyến, **When** chuyển sang Document IR, **Then** kết quả trả về ghi nhận cảnh báo kiểu chữ đã được chuyển về nét viết tay chuẩn.

---

### User Story 5 - Loại bỏ Cơ chế Desktop Cũ & Chuẩn hóa Kho Mã nguồn (Priority: P3)

Loại bỏ hoàn toàn các tàn dư từ thời Desktop: (1) Bỏ cơ chế tự động sinh file `*_thieu.xopp` trong luồng dàn trang (`missing_grid=False`), loại bỏ rò rỉ bộ nhớ MEMFS; (2) Bỏ hoàn toàn nhánh sinh lưới cũ `hw2` (chỉ tạo chuẩn `hw3`); (3) Chuyển toàn bộ các ca kiểm thử có giá trị từ `repro_viet_baseline.py` và `test_web_parse_seed.test.mjs` vào bộ test chính thức, sau đó xóa tệp `repro_viet_baseline.py` và tệp test trùng lặp; (4) Giữ `chuviettay/fidelity/` ở trạng thái archive cách ly.

**Why this priority**: Đảm bảo kho mã nguồn Web-only gọn gàng, chấm dứt rò rỉ tài nguyên bộ nhớ trên trình duyệt, và thống nhất bộ test tự động trong CI.

**Independent Test**: Chạy `write_text` khi thiếu mẫu và xác nhận không có file `*_thieu.xopp` nào được ghi vào đĩa/MEMFS; kiểm tra hàm `make_grid` chỉ sinh chuẩn `hw3`; xác nhận `git status` không còn `repro_viet_baseline.py` và toàn bộ test CI pass 100%.

**Acceptance Scenarios**:
1. **Given** tùy chọn `WriteOptions`, **When** khởi tạo mặc định, **Then** `missing_grid` có giá trị mặc định là `False`, và khi chạy dàn trang thiếu mẫu không còn tự động tạo file `*_thieu.xopp`.
2. **Given** hàm `make_grid`, **When** tạo lưới luyện viết chữ, **Then** hệ thống chỉ hỗ trợ sinh định dạng chuẩn `hw3`, loại bỏ nhánh `grid_version == "hw2"`.
3. **Given** tệp `repro_viet_baseline.py` và `tests/test_web_parse_seed.test.mjs`, **When** hoàn tất di trú các ca kiểm thử, **Then** hai tệp này được xóa khỏi git repository và bộ test trong `tests/` bao phủ đầy đủ các ca kiểm tra hồi quy.

---

### Edge Cases
- Đoạn văn căn đều (`justify`) chỉ có 1 từ hoặc là dòng cuối đoạn: Giữ nguyên căn lề trái tự nhiên.
- Dòng kết thúc bằng ngắt dòng mềm (`LineBreak`): Không thực hiện kéo giãn khoảng cách từ trong chế độ `justify`.
- Nhãn ký tự đặc biệt chứa cú pháp giả mạo `<script>` hoặc `<img onerror=...>`: Mã hóa HTML an toàn, tuyệt đối không kích hoạt mã độc.
- Ô bảng chứa phương trình toán học có dấu trị tuyệt đối `$|x|$`: Phải được escape thành `$\|x\|$` khi xuất Markdown bảng để không làm vỡ phân tách cột.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Bộ chuyển đổi `BrowserBridge._document_to_markdown_dict` MUST trích xuất đầy đủ `MathBlock` (`$$...$$` ở cấp tài liệu, `$...$` trong ô bảng) và tiêu đề `Heading` (`#`..`######`).
- **FR-002**: Khi trích xuất văn bản từ `DocumentIR` sang Markdown, hệ thống MUST escape các ký tự điều khiển Markdown (`*`, `_`, `~`, `#`, `$`, `\`, `|`) để bảo đảm tính toàn vẹn khi re-import.
- **FR-003**: Trong ô bảng Markdown, ngắt dòng mềm `LineBreak` MUST được chuyển thành khoảng cách trắng để tránh làm vỡ hàng bảng; dấu gạch đứng `|` trong công thức LaTeX MUST được escape thành `\|`.
- **FR-004**: Bộ dàn trang `DocumentLayoutEngine` MUST hỗ trợ thuộc tính `Paragraph.align` (`left`, `center`, `right`, `justify`), tính toán tọa độ ngang đối xứng theo hình học trang giấy và phân bổ khoảng cách từ cho dòng tràn trong chế độ `justify`.
- **FR-005**: `token_layout_callback` trong `DocumentLayoutEngine` MUST nhận tọa độ chính xác của các từ sau khi đã căn lề và kéo giãn.
- **FR-006**: Tách hàm `escapeHtml` thành module dùng chung trong `webapp/js/html-utils.js` và áp dụng cho toàn bộ các điểm nội suy DOM trong `webapp/js/bank.js` và `webapp/js/write.js`.
- **FR-007**: Modal "Xem thử ngẫu nhiên" trong `bank.js` MUST giải nén `xopp_base64` và dựng hình SVG nét chữ viết tay trực quan, gửi tùy chọn `missing_grid: false` và cắt gọn viewBox theo kích thước nét vẽ.
- **FR-008**: `MarkdownImporter` MUST kích hoạt plugin `.enable("strikethrough")` của `markdown-it-py` để loại bỏ cặp dấu `~~` thừa.
- **FR-009**: `MarkdownImporter` MUST ghi nhận cảnh báo vào `ImportResult.warnings` khi tài liệu nguồn chứa các thẻ kiểu chữ giàu (in đậm, in nghiêng, gạch ngang, mã nội tuyến).
- **FR-010**: Đổi giá trị mặc định của `WriteOptions.missing_grid` thành `False`, ngăn chặn việc tự động sinh file `*_thieu.xopp` gây rác MEMFS trên Web.
- **FR-011**: Loại bỏ nhánh sinh lưới ô cũ `hw2` trong `chuviettay/model/xopp.py` (chỉ tạo chuẩn `hw3`), cập nhật thông điệp hướng dẫn trên trang lưới ô theo đúng nhãn giao diện Web hiện hành.
- **FR-012**: Di chuyển test còn thiếu từ `tests/test_web_parse_seed.test.mjs` sang `tests/js/parse_seed.test.mjs` rồi xóa file trùng; di chuyển các ca kiểm thử hồi quy từ `repro_viet_baseline.py` vào `tests/test_regression_audit.py` rồi xóa `repro_viet_baseline.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: 100% các khối `MathBlock`, `Heading` và ký tự đặc biệt trong DOCX được bảo toàn qua round-trip Markdown (`DocumentIR` -> Markdown -> `DocumentIR`).
- **SC-002**: Tọa độ ngang của 4 chế độ căn lề trong `DocumentLayoutEngine` khớp chuẩn hình học với sai số < 0.1 pt; căn lề trái giữ nguyên 100% byte kết xuất của Golden Master.
- **SC-003**: 0 lỗ hổng XSS trong Quản lý Kho mẫu; 100% khung xem thử ngẫu nhiên vẽ SVG nét chữ thực tế.
- **SC-004**: Cú pháp `~~text~~` được loại bỏ sạch sẽ; cảnh báo định dạng xuất hiện trong `warnings`.
- **SC-005**: 0 file `*_thieu.xopp` bị ghi ngầm vào MEMFS khi chạy dàn trang mặc định; 0 tệp trùng lặp hoặc script chẩn đoán lỗi thời ở thư mục gốc; 100% bài kiểm thử CI chạy thành công (exit 0).
