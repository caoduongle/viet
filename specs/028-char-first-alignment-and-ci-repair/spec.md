# Feature Specification: Đồng Bộ Mô Hình Char-First, Khắc Phục Dấu Thanh & Sửa Lỗi CI Toàn Diện

**Feature Branch**: `specs/028-char-first-alignment-and-ci-repair`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Rà soát chuyển đổi mô hình char-first; khắc phục CI đỏ (14 test failure Python 3.12/3.14 & Playwright); sửa lỗi nạp nhãn dấu thanh catalog trên Web Client; thống nhất quy tắc kiểm tra khả năng viết giữa Bank.can() và Writer; xuất file kiểm tra .xopp đầy đủ marks; bảo toàn đa nét cho dấu thanh; cải thiện kiểm chứng hình học chống dính chữ; chuẩn hóa thống kê Desktop và đồng bộ tài liệu hướng dẫn."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Đồng bộ Hợp đồng Char-First & Kiểm tra Khả năng Viết Thống Nhất (Priority: P1) 🎯 MVP

Người dùng soạn thảo văn bản hoặc kiểm tra kho mẫu nhận được thông tin chính xác 100% về những từ/ký tự có thể viết được. Hệ thống không bao giờ báo một từ viết được khi thiếu các mẫu ký tự thành phần (chữ cái, dấu thanh, dấu câu), và không còn kiểm tra dựa trên các mẫu từ nguyên khối cũ đã ngừng hỗ trợ kết xuất.

**Why this priority**: Đây là nền tảng cốt lõi của tính năng ghép ký tự (char-first). Sự bất nhất giữa bộ kiểm tra kho (`Bank.can()`) và bộ tạo văn bản (`Writer`) gây ra lỗi hiển thị, đánh lừa người dùng và khiến CI kiểm thử thất bại.

**Independent Test**: Nạp một kho mẫu cũ chỉ có mẫu nguyên từ "xin" nhưng không có các chữ cái 'x', 'i', 'n'. Hệ thống phải xác định rõ ràng "xin" chưa thể viết được, yêu cầu người dùng học các chữ cái còn thiếu; bộ tạo văn bản và bộ kiểm tra kho trả về kết quả đồng nhất.

**Acceptance Scenarios**:
1. **Given** một kho mẫu không có đủ các chữ cái cấu thành một từ, **When** hệ thống kiểm tra khả năng viết của từ đó, **Then** hệ thống xác định từ đó chưa thể viết được và liệt kê đúng danh sách ký tự còn thiếu.
2. **Given** một từ có dấu thanh tiếng Việt (ví dụ "bà"), **When** kiểm tra khả năng viết, **Then** hệ thống yêu cầu đồng thời có mẫu chữ cái thân ("b", "a") và mẫu dấu thanh tương ứng ("dấu huyền" / combining mark).
3. **Given** các bài kiểm thử tự động trên CI (pytest và Playwright), **When** chạy kiểm thử, **Then** toàn bộ kịch bản kiểm thử phản ánh đúng quy tắc ghép ký tự char-first và đạt kết quả kiểm tra thành công (100% PASS).

---

### User Story 2 - Hoàn thiện Quy Trình Dạy & Kiểm Tra Toàn Diện Cho Dấu Thanh (Priority: P1)

Người dùng có thể nạp danh mục dấu thanh vào hàng đợi dạy chữ trên Web Client mà không bị chia cắt nhãn thành các chữ cái rời rạc (`d`, `ấ`, `u`...). Khi vẽ dấu thanh gồm nhiều nét (ví dụ dấu hỏi hoặc nét ngắt bút), toàn bộ các nét được lưu giữ nguyên vẹn. Khi xuất file `.xopp` kiểm tra kho mẫu, toàn bộ 5 dấu thanh được hiển thị trực quan và có thể xem lại.

**Why this priority**: Dấu thanh tiếng Việt là thành phần thiết yếu để ghép từ. Lỗi tách nhãn trên Web và lỗi cắt mất nét trong luồng lưu trực tiếp làm hỏng việc học dấu thanh, trực tiếp ảnh hưởng đến trải nghiệm người dùng và tính toàn vẹn dữ liệu.

**Independent Test**: Trên Web Client, mở bộ ký tự "Dấu thanh rời" và thêm vào hàng đợi; hàng đợi hiển thị đúng 5 nhãn nghiệp vụ (`dấu huyền`, `dấu sắc`, `dấu hỏi`, `dấu ngã`, `dấu nặng`). Vẽ một dấu thanh với 2 nét bút rời và bấm Lưu; nạp lại kho kiểm tra thấy đủ 2 nét. Xuất file `.xopp` kiểm tra kho mẫu và thấy đủ trang/ô chứa các mẫu dấu thanh này.

**Acceptance Scenarios**:
1. **Given** người dùng chọn nạp nhóm danh mục dấu thanh từ bộ ký tự có sẵn, **When** đưa vào hàng đợi học, **Then** hệ thống giữ nguyên nhãn nghiệp vụ (không bị phân rã thành từng ký tự 'd', 'ấ', 'u'...).
2. **Given** người dùng vẽ dấu thanh với nhiều nét rời rạc trên bảng vẽ, **When** lưu mẫu, **Then** toàn bộ các nét được lưu trữ trọn vẹn trong kho mẫu, không bị cắt bớt nét thứ hai trở đi.
3. **Given** kho mẫu có chứa các mẫu dấu thanh, **When** người dùng xuất file kiểm tra lại kho mẫu (.xopp), **Then** file xuất ra chứa đầy đủ các ô mẫu dấu thanh với nhãn hiển thị trực quan.

---

### User Story 3 - Củng Cố Kiểm Chứng Hình Học Chống Dính Nét & Chuẩn Hóa Giao Diện/Tài Liệu (Priority: P2)

Người dùng viết chữ nhận được văn bản ghép chữ tự nhiên, các ký tự liền kề không bị dính nét bết mực vào nhau kể cả với các mẫu chữ viết tay có độ vươn dài phức tạp. Giao diện Desktop và tài liệu hướng dẫn hiển thị thống kê rõ ràng theo số lượng ký tự/mẫu nét thay vì lấy số từ nguyên khối cũ làm chỉ số chính.

**Why this priority**: Nâng cao chất lượng thẩm mỹ của trang viết tay và loại bỏ hoàn toàn các thông tin hướng dẫn sai lệch, tạo sự nhất quán trên cả ứng dụng Desktop, Web và tài liệu README.

**Independent Test**: Viết các từ tiếng Việt phức tạp có dấu thanh, chữ vươn cao/dài (như "thuyền", "nghiêng"); thuật toán ghép chữ duy trì khe hở hình học an toàn giữa các nét liền kề. Trên giao diện Desktop, dòng thống kê thể hiện rõ tổng số ký tự và mẫu nét của các nhóm (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh).

**Acceptance Scenarios**:
1. **Given** hai ký tự liên tiếp có nét vươn dài (ascender/descender), **When** thuật toán ghép từ thực thi, **Then** khoảng cách tối thiểu giữa các đoạn nét liền kề luôn đảm bảo ngưỡng khe hở an toàn chống bết mực.
2. **Given** người dùng xem thống kê kho mẫu trên Desktop GUI, **When** màn hình hiển thị, **Then** chỉ số chính hiển thị số ký tự và số mẫu nét của các phân loại hiện hành; thông tin mẫu từ cũ chỉ hiển thị phụ trợ tương thích nếu có.
3. **Given** người dùng đọc tài liệu hướng dẫn (README, trợ giúp), **When** tra cứu, **Then** toàn bộ nội dung hướng dẫn quy trình dạy theo từng ký tự/nhãn và nêu rõ kho mẫu ghép từ ký tự rời rạc.

---

### Edge Cases

- Kho mẫu cũ chỉ chứa mẫu từ nguyên khối (`words`) và hoàn toàn không có mẫu chữ cái: Hệ thống hiển thị thông báo rõ ràng cho người dùng rằng kho cần được dạy thêm các chữ cái để có thể kết xuất văn bản bằng bộ ghép mới, không gây crash ứng dụng.
- Dấu thanh vẽ có kích thước siêu nhỏ hoặc nét đơn điểm (dot/dấu nặng): Hệ thống bảo toàn tọa độ tương đối, không bị thuật toán khử nhiễu lọc nhầm làm mất nét.
- Người dùng nhập một đoạn văn bản dài có cả ký tự thông thường và nhãn đặc biệt vào ô dạy từ: Hệ thống phân biệt rõ ràng luồng nhập văn bản thông thường (tách thành các ký tự) và luồng nạp nhãn danh mục (giữ nguyên nhãn nghiệp vụ).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST áp dụng một quy tắc kiểm tra khả năng viết duy nhất và nhất quán giữa bộ kiểm tra kho mẫu và bộ kết xuất văn bản, yêu cầu đầy đủ mẫu của các ký tự cấu thành (thân chữ cái, dấu thanh, dấu câu, ký hiệu).
- **FR-002**: Hệ thống MUST KHÔNG xem một từ là viết được chỉ dựa trên sự tồn tại của mẫu nguyên từ cũ trong kho mẫu khi thiếu các ký tự thành phần.
- **FR-003**: Web Client MUST phân biệt rõ ràng giữa thao tác nạp văn bản từ ô nhập (tách thành các ký tự riêng lẻ) và thao tác nạp danh mục ký tự/dấu thanh (giữ nguyên nhãn danh mục nguyên vẹn).
- **FR-004**: Khi nạp danh mục dấu thanh vào hàng đợi học chữ, hệ thống MUST giữ nguyên nhãn nghiệp vụ (`dấu sắc`, `dấu huyền`, `dấu hỏi`, `dấu ngã`, `dấu nặng`) mà không phân rã thành các ký tự code point.
- **FR-005**: Luồng dạy và lưu mẫu dấu thanh trực tiếp MUST bảo toàn toàn bộ danh sách nét vẽ của người dùng (hỗ trợ mẫu nhiều nét rời rạc), không cắt bỏ các nét sau nét đầu tiên.
- **FR-006**: Chức năng xuất file kiểm tra kho mẫu (.xopp) MUST bao gồm đầy đủ các mẫu dấu thanh từ kho lưu trữ với nhãn hiển thị dễ hiểu bên cạnh các nhóm chữ cái, chữ số, dấu câu và ký hiệu.
- **FR-007**: Thuật toán tính toán khe hở chống dính chữ MUST kiểm chứng khoảng cách an toàn dựa trên đoạn nét (segment-to-segment distance) và phạm vi bao quanh của các nét liền kề.
- **FR-008**: Bảng thống kê kho mẫu trên Desktop GUI MUST hiển thị trọng tâm là tổng số ký tự có mẫu, số mẫu theo từng phân loại và tình trạng dấu thanh; không dùng số từ nguyên khối cũ làm chỉ số chính.
- **FR-009**: Toàn bộ tài liệu hướng dẫn (README.md, trợ giúp giao diện, CLI help) MUST được cập nhật đồng bộ để phản ánh chính xác mô hình học và ghép ký tự char-first.
- **FR-010**: Toàn bộ bộ kiểm thử tự động (pytest unit/integration tests và Playwright E2E tests) MUST được cập nhật để phù hợp với đặc tả ghép ký tự char-first và đạt trạng thái 100% kiểm tra thành công (CI xanh).

---

### Key Entities

- **CharCatalogLabel**: Nhãn nghiệp vụ đại diện cho một mục học (ví dụ: chữ cái 'a', chữ số '1', hoặc nhãn danh mục dấu thanh như 'dấu sắc').
- **CharSample**: Mẫu nét vẽ viết tay tương đối của một ký tự hoặc dấu thanh, bao gồm danh sách các nét (mỗi nét gồm chuỗi điểm tọa độ) và độ rộng tham chiếu.
- **RenderReadinessResult**: Kết quả kiểm tra tính khả thi khi kết xuất một đoạn văn bản, báo cáo trạng thái thành công hoặc danh sách cụ thể các ký tự/dấu thanh còn thiếu.
- **StrokeClearanceMetric**: Độ đo khoảng cách hình học nhỏ nhất giữa các đoạn nét liền kề để đảm bảo chống dính nét và bết mực khi ghép từ.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các bài kiểm thử tự động trên CI (Python 3.12, Python 3.14, Playwright E2E) vượt qua thành công (0 test failures), giải quyết triệt để 14 lỗi pytest và 4 lỗi Playwright hiện tại.
- **SC-002**: Tỷ lệ đồng nhất 100% giữa bộ kiểm tra kho và bộ tạo văn bản: bất kỳ từ nào được báo là viết được thì bộ tạo văn bản phải kết xuất thành công ra trang viết tay.
- **SC-003**: 100% nhãn dấu thanh nạp từ danh mục trên Web Client được bảo toàn nguyên vẹn tên nhãn khi đưa vào hàng đợi học.
- **SC-004**: 100% các nét vẽ của mẫu dấu thanh nhiều nét được lưu trữ trọn vẹn và đọc lại chính xác sau khi lưu kho mẫu.
- **SC-005**: File kiểm tra kho mẫu (.xopp) bao phủ đầy đủ 100% các nhóm mẫu hiện diện trong kho, bao gồm toàn bộ các dấu thanh đã học.
- **SC-006**: Văn bản xuất ra loại bỏ hiện tượng dính nét giữa các ký tự liền kề trên các mẫu chữ viết tay có độ vươn phức tạp.

---

## Assumptions

- Kho mẫu tiếp tục duy trì cấu trúc dữ liệu tương thích ngược cho các kho cũ, nhưng quyền ưu tiên kết xuất thuộc về các ký tự thành phần.
- Các nhãn dấu thanh tiếng Việt tuân thủ danh mục chuẩn 5 dấu thanh: sắc, huyền, hỏi, ngã, nặng.
- Các môi trường CI được cấu hình đầy đủ tài nguyên cần thiết để chạy kiểm thử Playwright và pytest mà không gặp lỗi môi trường thiếu dependencies.
