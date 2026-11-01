# Feature Specification: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử

**Feature Branch**: `070-render-generation-import-seed-hardening`  
**Created**: 2026-11-01  
**Updated**: 2026-11-01 (Bổ sung Two-Stage Stale Guard sau giải nén XOPP, Khóa xuất file khi kết quả cũ, Kiểm thử xác định và Xử lý lỗi reset seed)  
**Status**: Ready for Planning  
**Input**: Rà soát repository viet sau commit `7c74c23`, xử lý triệt để race condition trong khoảng chờ giải nén XOPP, khóa xuất file (.xopp, .pdf, .png, .svg, .zip) khi bản render chưa hoàn tất hoặc bị cũ, kiểm thử E2E race condition có tính xác định, củng cố unit test giải nén XOPP hợp lệ và xử lý chặn nạp tài liệu khi reset seed thất bại.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ngăn chặn kết quả kết xuất cũ ghi đè lên tài liệu mới và khóa xuất tệp khi bản kết xuất bị cũ (Priority: P1) 🎯 MVP

Khi người dùng đang soạn thảo hoặc mở một tài liệu mới trong lúc tài liệu trước đó vẫn đang được xử lý ở tiến trình nền (kể cả trong khoảng thời gian giải nén và phân tích tệp .xopp), hệ thống phải xác định và loại bỏ triệt để các kết quả kết xuất đã lỗi thời qua mô hình Cam kết Trạng thái Nguyên tử (Atomic State Commit). Đồng thời, hệ thống phải theo dõi trạng thái tính mới của bản kết xuất, khóa hoặc ngăn chặn người dùng xuất tệp (.xopp, .pdf, .png, .svg, .zip) khi nội dung soạn thảo hiện tại chưa khớp với bản kết xuất đã hoàn tất.

**Why this priority**: Triệt tiêu hoàn toàn rủi ro người dùng đang xem hoặc tải xuống tệp kết xuất của tài liệu cũ $A$ trong khi đang chỉnh sửa tài liệu mới $B$, bảo vệ tính toàn vẹn của dữ liệu xuất ra.

**Independent Test**:
1. Gửi yêu cầu kết xuất cho tài liệu $A$, trong lúc đang giải nén $A$ lập tức kích hoạt yêu cầu tài liệu $B$; xác nhận $A$ bị loại bỏ sau khi giải nén xong và chỉ $B$ được cam kết vào giao diện.
2. Soạn tài liệu $A$ đã render hoàn tất, sau đó gõ thêm nội dung $B$; khi $B$ chưa render xong, các nút xuất tệp phải bị khóa hoặc thông báo cảnh báo rõ ràng rằng bản xem trước đang cũ và không cho phép tải xuống tệp của $A$.

**Acceptance Scenarios**:
1. **Given** hệ thống đang giải nén kết quả XOPP của tài liệu $A$, **When** người dùng thay đổi nội dung sang tài liệu $B$, **Then** sau khi giải nén xong, kết quả của $A$ bị từ chối và không được ghi nhận vào `currentDoc` hay `currentXoppBase64`.
2. **Given** tài liệu $A$ đã kết xuất xong và người dùng sửa ô soạn thảo thành $B$, **When** người dùng bấm các nút xuất tệp (.xopp, .pdf, .png, .svg, .zip) trước khi $B$ kết xuất xong, **Then** hệ thống chặn hành động xuất tệp và hiển thị thông báo bản xem trước đang được cập nhật, ngăn ngừa tải nhầm dữ liệu của $A$.
3. **Given** quá trình giải nén hoặc phân tích cú pháp XOPP gặp sự cố dữ liệu không hợp lệ, **Then** hệ thống giữ nguyên trạng thái hợp lệ trước đó hoặc dọn dẹp sạch sẽ, tuyệt đối không gán dữ liệu XOPP chưa được kiểm chứng vào biến xuất tệp.

---

### User Story 2 - Kiểm chứng E2E việc xóa sạch lịch sử hạt giống khi mở tài liệu mới và xử lý an toàn khi reset lỗi (Priority: P1)

Khi người dùng mở một tệp văn bản mới (.txt, .md, .docx), hệ thống phải đặt lại lịch sử đối chiếu hạt giống độc lập từ đầu (occurrence = 0). Nếu thao tác đặt lại lịch sử hạt giống gặp sự cố từ dịch vụ nền, hệ thống phải dừng quá trình nạp tệp và hiển thị cảnh báo lỗi rõ ràng, không âm thầm tiếp tục kết xuất tài liệu mới trên nền lịch sử cũ.

**Why this priority**: Đảm bảo các từ ngữ trong tài liệu mới mở không bị áp dụng sai biến thể nét chữ do kế thừa lịch sử cũ, và đảm bảo mọi lỗi đặt lại hạt giống đều được xử lý minh bạch thay vì bỏ qua âm thầm.

**Independent Test**:
1. Viết tài liệu chứa từ lặp `"xin xin chào ba"`, sau đó mở tệp mới chỉ chứa `"xin"`; xác nhận nét vẽ của từ `"xin"` trong tệp mới khớp 100% với baseline độc lập ban đầu.
2. Mô phỏng dịch vụ nền trả về lỗi khi đặt lại lịch sử hạt giống; xác nhận hệ thống hiển thị thông báo cảnh báo lỗi và không nạp nội dung tệp mới vào trình soạn thảo.

**Acceptance Scenarios**:
1. **Given** tài liệu cũ đã có từ lặp với occurrence $\ge 1$, **When** người dùng mở tệp .txt, .md hoặc .docx mới chứa từ đó, **Then** từ đó trong tài liệu mới được tạo hình với occurrence = 0 độc lập.
2. **Given** người dùng chọn mở một tệp văn bản, **When** lệnh đặt lại lịch sử hạt giống trả về trạng thái thất bại (`{ ok: false }`), **Then** hệ thống thông báo lỗi rõ ràng trên vùng cảnh báo và hủy thao tác nạp tài liệu.

---

### User Story 3 - Kiểm thử xác định (Deterministic Testing) và dọn dẹp tiến trình kiểm thử (Priority: P2)

Các bài kiểm thử tự động (cả kiểm thử đơn vị Node.js và kiểm thử đầu-cuối E2E trên trình duyệt) phải được thiết kế có tính xác định tuyệt đối (deterministic): kiểm thử E2E race condition phải chứng minh được yêu cầu render tài liệu cũ đã thực sự được gửi xuống Worker trước khi tài liệu mới ập tới; kiểm thử đơn vị Node.js phải sử dụng fixture XOPP gzip hợp lệ chứng minh giải nén, phân tích cú pháp và cập nhật giao diện thành công; đồng thời toàn bộ timer của yêu cầu Worker trong kiểm thử đơn vị phải được dọn dẹp triệt để không giữ tiến trình Node.js chạy ngầm.

**Why this priority**: Đảm bảo bộ kiểm thử không bị phụ thuộc vào tốc độ máy chủ CI (flaky tests), khẳng định đầy đủ chu trình render thành công của tài liệu mới và tối ưu hóa thời gian thực thi CI.

**Independent Test**: Chạy `node --test tests/js/render_generation.test.mjs` và `npx playwright test tests/e2e/write.spec.ts` xác nhận 100% kịch bản đạt kết quả xanh tức thì, tiến trình Node.js giải phóng ngay sau khi test hoàn tất.

**Acceptance Scenarios**:
1. **Given** kịch bản kiểm thử E2E race condition, **When** gửi tài liệu $A$, **Then** test chủ động xác nhận Worker đã tiếp nhận yêu cầu $A$ trước khi kích hoạt mở tệp $B$.
2. **Given** kịch bản kiểm thử đơn vị Node.js cho tài liệu $B$, **When** Worker trả về fixture XOPP gzip hợp lệ, **Then** test khẳng định tài liệu $B$ giải nén thành công, phân tích cú pháp thành công và trạng thái `currentDoc` được cập nhật chính xác.
3. **Given** các yêu cầu thông điệp Worker trong môi trường kiểm thử (như lệnh reset hạt giống), **Then** tất cả các Promise và timer nội bộ đều được giải phóng ngay lập tức sau khi test kết thúc.

---

### User Story 4 - Chuẩn hóa tài liệu kiểm thử và đo kiểm hiệu năng kho mẫu đa biến thể (Priority: P3)

Tài liệu hướng dẫn kiểm chứng (`quickstart.md`) và mã nguồn kiểm thử phải đồng bộ số liệu chính xác về số lượng bài test thực tế (23+ tests E2E) và cấu trúc dữ liệu đo kiểm kho mẫu quy mô lớn (1.050+ nhãn và 3.520 mẫu nét đa biến thể dưới 200ms).

**Why this priority**: Đảm bảo tính nhất quán và minh bạch 100% giữa tài liệu đặc tả, checklist nghiệm thu và kết quả chạy CI thực tế.

**Independent Test**: Chạy toàn bộ các bộ kiểm thử và đối chiếu bảng số liệu ghi nhận trong `quickstart.md`.

**Acceptance Scenarios**:
1. **Given** tài liệu `quickstart.md`, **When** người đọc đối chiếu phần quy trình hồi quy và bảng kết quả thực tế, **Then** số lượng bài test E2E đồng bộ nhất quán 100% với số test thực tế được thực thi trên Playwright.

---

### Edge Cases

- **Thay đổi tài liệu ngay trong lúc giải nén XOPP**: Người dùng gõ phím hoặc mở tệp mới đúng vào khoảnh khắc Worker đã tính toán xong nhưng giao diện đang giải nén tệp gzip XOPP.
- **Bấm nút xuất tệp khi đang gõ phím liên tục**: Người dùng vừa nhập xong một đoạn văn bản và lập tức bấm nút xuất file trong khi debounce 250ms chưa kết thúc hoặc Worker chưa trả về kết quả mới.
- **Lỗi giải nén tệp XOPP bị hỏng**: Tệp XOPP do Worker sinh ra bị suy hao dữ liệu khi nén/giải nén base64, giao diện không được cập nhật trạng thái xuất tệp rác.
- **Thất bại kết nối khi reset hạt giống**: Worker bị quá tải hoặc bận rộn khiến lệnh đặt lại lịch sử tài liệu trả về lỗi hoặc quá thời gian chờ (timeout).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST gán một mã định danh thế hệ kết xuất (`currentRenderGeneration` / `requestId`) tăng đơn điệu cho mỗi yêu cầu kết xuất được phát sinh từ ô soạn thảo hoặc lệnh mở tệp.
- **FR-002**: Hệ thống MUST áp dụng cơ chế bảo vệ Cam kết Nguyên tử (Two-Stage Stale Guard): kiểm tra thế hệ kết xuất lần 1 khi nhận kết quả từ Worker, và kiểm tra lại lần 2 SAU KHI hoàn tất giải nén XOPP và phân tích tài liệu XML.
- **FR-003**: Hệ thống MUST giữ kết quả giải nén XOPP và phân tích XML trong các biến cục bộ, chỉ cam kết ghi đè vào trạng thái toàn cục (`currentXoppBase64`, `currentDoc`, `currentMissingBoxes`, vùng hiển thị SVG) khi mã thế hệ tại thời điểm sau giải nén vẫn là mã thế hệ hiện hành và nội dung ô soạn thảo khớp với bản chụp tham số kết xuất.
- **FR-004**: Nếu quá trình giải nén hoặc phân tích cú pháp XOPP thất bại, hệ thống MUST giữ nguyên trạng thái kết xuất hợp lệ trước đó hoặc đưa về trạng thái rỗng an toàn; tuyệt đối không cập nhật `currentXoppBase64` bằng dữ liệu chưa được xác thực tính toàn vẹn.
- **FR-005**: Hệ thống MUST theo dõi trạng thái tính mới của bản kết xuất (`isRenderStale` / `isPreviewStale`). Ngay khi người dùng thay đổi nội dung ô soạn thảo hoặc thay đổi tùy chọn định dạng/bút vẽ, hệ thống MUST đánh dấu bản kết xuất hiện tại là cũ (stale).
- **FR-006**: Các chức năng xuất tệp (.xopp, .pdf, .png, .svg, .zip) MUST kiểm tra trạng thái tính mới của bản kết xuất trước khi thực hiện xuất; nếu bản kết xuất đang bị cũ (`isRenderStale === true`) hoặc đang trong quá trình kết xuất (`isRendering === true`), hệ thống MUST chặn thao tác xuất và thông báo cảnh báo rõ ràng cho người dùng, ngăn ngừa xuất nhầm tệp của nội dung trước đó.
- **FR-007**: Khi người dùng mở tệp mới (.txt, .md, .docx), hệ thống MUST gọi lệnh đặt lại lịch sử hạt giống (`resetDocumentSeedHistory`); nếu lệnh này trả về thất bại (`false`), hệ thống MUST hiển thị cảnh báo lỗi rõ ràng và dừng thao tác nạp tệp, KHÔNG tiếp tục kết xuất tài liệu mới trên nền lịch sử cũ.
- **FR-008**: Bài kiểm thử E2E race condition MUST được xây dựng có tính xác định (deterministic), xác nhận yêu cầu kết xuất của tài liệu cũ đã được gửi xuống Worker trước khi kích hoạt mở tệp mới.
- **FR-009**: Bài kiểm thử đơn vị Node.js MUST sử dụng fixture XOPP gzip hợp lệ để kiểm chứng luồng giải nén, phân tích cú pháp và cập nhật giao diện thành công của tài liệu mới, đồng thời giải phóng toàn bộ timer Worker để tiến trình Node.js không bị treo.
- **FR-010**: Tài liệu hướng dẫn kiểm chứng (`quickstart.md`) MUST đồng bộ thống nhất số lượng bài test E2E thực tế (23+ tests) giữa phần hướng dẫn và bảng ghi nhận kết quả.

---

### Key Entities

- **Render Generation State**: Trạng thái quản lý thế hệ kết xuất, gồm `currentRenderGeneration` (mã thế hệ hiện hành tăng đơn điệu) và `currentRenderSnapshot` (bản chụp `generation`, `text`, `format`).
- **Render Freshness State**: Trạng thái tính mới của bản kết xuất, gồm `renderedGeneration` (thế hệ của bản kết xuất đã hoàn tất và hiển thị thành công) và cờ `isRenderStale` (bằng `true` khi nội dung ô soạn thảo hoặc tùy chọn khác với bản kết xuất hiện tại).
- **XOPP Export Payload**: Dữ liệu xuất tệp đã được kiểm chứng tính toàn vẹn thông qua giải nén và phân tích cú pháp thành công (`currentXoppBase64`), chỉ được phép sử dụng khi `isRenderStale === false`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Loại bỏ 100% rủi ro kết quả kết xuất cũ ghi đè lên giao diện người dùng, kể cả trong khoảng thời gian chờ giải nén và phân tích tệp XOPP.
- **SC-002**: Loại bỏ 100% rủi ro người dùng xuất tệp (.xopp, .pdf, .png, .svg, .zip) chứa nội dung tài liệu cũ khi đang soạn thảo hoặc mở tài liệu mới.
- **SC-003**: 100% thao tác mở tệp mới khi gặp lỗi đặt lại lịch sử hạt giống đều được chặn an toàn và thông báo cảnh báo minh bạch trên giao diện người dùng.
- **SC-004**: Bộ kiểm thử đơn vị Node.js giải phóng 100% tài nguyên và timer ngay sau khi hoàn thành, không có tiến trình treo quá 1 giây.
- **SC-005**: Toàn bộ các bài kiểm thử E2E Playwright (23+ tests) và Python pytest (>1.427 tests) vượt qua (PASS) 100% trên môi trường kiểm thử.
- **SC-006**: Tài liệu kỹ thuật, bảng đo kiểm hiệu năng và checklist nghiệm thu đạt tính nhất quán 100%.

---

## Assumptions

- Quá trình giải nén XOPP trên Web Client sử dụng hàm bất đồng bộ `decompressXoppBase64` dựa trên `DecompressionStream` hoặc thư viện nén thuần chạy trên luồng chính của trình duyệt.
- Các nút xuất tệp trên giao diện (`#btn-export-xopp`, `#btn-export-pdf`, `#btn-export-png`, `#btn-export-svg`, `#btn-export-zip`) được kết nối tập trung qua một hàm điều phối kiểm tra tính mới trước khi kích hoạt tải xuống.
- Khi người dùng đang soạn thảo nhanh, việc giữ lại hình ảnh xem trước cũ kèm thông báo "Đang cập nhật..." là trải nghiệm thị giác tốt hơn việc xóa trắng màn hình gây nhấp nháy, miễn là chức năng xuất tệp bị khóa an toàn trong khoảng thời gian này.
