# Feature Specification: Kiểm soát thế hệ kết xuất, thế hệ nhập tệp, khóa xuất bản cũ và tăng cường tính xác định kiểm thử

**Feature Branch**: `070-render-generation-import-seed-hardening`  
**Created**: 2026-11-01  
**Updated**: 2026-11-01 (Hoàn thiện kiểm tra thế hệ & snapshot tùy chọn khi xuất tệp, bổ sung thế hệ nhập tệp chống ghi đè, kiểm thử Stage 2 giải nén XOPP, xác định hóa E2E race condition và khắc phục xung đột bất đồng bộ bài kiểm thử XSS trên CI)  
**Status**: Ready for Planning  
**Input**: Rà soát repository viet sau commit `53258d2`: (1) P1 - Hoàn thiện điều kiện kiểm tra xuất tệp đối chiếu thế hệ kết xuất đã cam kết cùng toàn bộ bản chụp nội dung, định dạng và tùy chọn viết chữ; (2) P2 - Kiểm thử đơn vị chuyên biệt cho giai đoạn giải nén XOPP bị trì hoãn (Stage 2 Stale Guard); (3) P2 - Kiểm soát thế hệ nhập tệp (`importGeneration`) chống ghi đè khi mở nhiều tệp liên tiếp; (4) P2 - Xác định hóa hoàn toàn bài kiểm thử E2E race condition bằng cách điều khiển thời điểm phản hồi của tiến trình nền; (5) P3 - Dọn dẹp bộ hẹn giờ chờ gõ phím trong kiểm thử và xử lý triệt để tranh chấp thời điểm khởi tạo kho mẫu làm ẩn thanh thông báo lỗi trong bài kiểm thử XSS trên CI.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Khóa xuất tệp nghiêm ngặt theo Thế hệ Kết xuất và Bản chụp Tùy chọn Đầy đủ (Priority: P1) 🎯 MVP

Khi người dùng xuất tài liệu (.xopp, .pdf, .png, .svg, .zip), hệ thống chỉ cho phép tải xuống khi bản kết xuất hiện có trên màn hình thực sự thuộc về thế hệ yêu cầu mới nhất đã hoàn tất thành công, đồng thời khớp tuyệt đối với văn bản hiện tại, định dạng hiện tại và toàn bộ các tùy chọn viết chữ hiện hành (cỡ chữ, khoảng cách, hạt giống, màu sắc, khổ giấy). Nếu người dùng thay đổi bất kỳ tùy chọn viết chữ nào hoặc nếu yêu cầu kết xuất mới nhất bị lỗi giữa chừng khiến màn hình vẫn giữ kết quả của thế hệ cũ, hệ thống phải khóa xuất tệp và cảnh báo rõ ràng.

**Why this priority**: Ngăn chặn triệt để mọi lỗ hổng khiến người dùng tải xuống bản kết xuất của thế hệ cũ khi yêu cầu kết xuất mới thất bại hoặc khi tùy chọn viết chữ đã bị thay đổi nhưng chưa được kết xuất lại.

**Independent Test**:
1. Kết xuất thành công tài liệu $A$, sau đó thay đổi tùy chọn viết chữ (như cỡ chữ, hạt giống hoặc khổ giấy) hoặc kích hoạt yêu cầu kết xuất $B$ nhưng $B$ gặp lỗi; xác nhận hệ thống từ chối xuất tệp và báo bản xem trước không khớp với trạng thái hiện hành.
2. Trong lúc tài liệu $A$ đã nhận kết quả từ tiến trình nền và đang trong giai đoạn giải nén dữ liệu XOPP, người dùng thay đổi nội dung sang tài liệu $B$; xác nhận khi giải nén $A$ hoàn tất, $A$ bị loại bỏ ở chốt chặn thứ hai (Stage 2) và tuyệt đối không được cam kết.

**Acceptance Scenarios**:
1. **Given** tài liệu $A$ đã kết xuất thành công ở thế hệ 1, **When** yêu cầu kết xuất tài liệu $B$ ở thế hệ 2 được khởi tạo nhưng thất bại (hoặc chưa hoàn tất), **Then** mã thế hệ đã cam kết (1) khác với mã thế hệ hiện hành (2) nên mọi thao tác xuất tệp bị chặn hoàn toàn.
2. **Given** tài liệu $A$ đã kết xuất thành công với bộ tùy chọn viết chữ $O_1$, **When** người dùng thay đổi bất kỳ thông số nào trong tùy chọn viết chữ sang $O_2$ (kể cả khi chưa áp dụng kết xuất lại), **Then** hệ thống nhận diện bản chụp tùy chọn không còn khớp với bản kết xuất hiện tại và khóa chức năng xuất tệp.
3. **Given** kết quả XOPP của tài liệu $A$ đang trong quá trình giải nén bất đồng bộ, **When** người dùng yêu cầu kết xuất tài liệu $B$ trước khi giải nén $A$ kết thúc, **Then** ngay khi giải nén $A$ hoàn tất, chốt chặn giai đoạn 2 phát hiện thế hệ đã cũ và hủy bỏ kết quả của $A$, bảo toàn trạng thái cho $B$.

---

### User Story 2 - Chống ghi đè khi Mở nhiều Tệp liên tiếp và Bảo toàn Hạt giống khi Nhập tệp (Priority: P1)

Khi người dùng chọn mở hoặc kéo thả liên tiếp nhiều tệp văn bản (ví dụ chọn một tệp `.docx` dung lượng lớn cần thời gian chuyển đổi rồi lập tức chọn sang một tệp `.txt` nhỏ gọn), hệ thống phải quản lý thứ tự thế hệ nhập tệp để chỉ áp dụng duy nhất tệp được chọn sau cùng. Tệp cũ hoàn tất muộn hơn phải bị loại bỏ hoàn toàn và không được ghi đè nội dung, định dạng, lịch sử hạt giống hay bản xem trước của tệp mới. Đồng thời, nếu việc đặt lại lịch sử hạt giống thất bại, quá trình nhập tệp phải dừng lại an toàn.

**Why this priority**: Đảm bảo tính nhất quán tuyệt đối khi người dùng thao tác chọn tệp nhanh liên tiếp giữa các định dạng có tốc độ xử lý khác nhau (.docx và .txt/.md).

**Independent Test**:
1. Mở tệp $A$ (`.docx`) có thời gian xử lý lâu, ngay lập tức mở tiếp tệp $B$ (`.txt`) hoàn tất trước; khi tệp $A$ xử lý xong muộn hơn, xác nhận ô soạn thảo và bản xem trước vẫn giữ nguyên nội dung của tệp $B$.
2. Thực hiện chiều ngược lại: mở tệp $A$ (`.txt`) đang chờ đặt lại hạt giống chậm, lập tức mở tệp $B$ (`.docx`) hoàn tất trước; xác nhận kết quả muộn của tệp $A$ bị hủy bỏ.

**Acceptance Scenarios**:
1. **Given** người dùng chọn mở tệp $A$ (`.docx`) và quá trình chuyển đổi đang diễn ra, **When** người dùng tiếp tục chọn mở tệp $B$ (`.txt`) và $B$ hoàn tất trước, **Then** khi quá trình chuyển đổi tệp $A$ kết thúc muộn hơn, toàn bộ kết quả của $A$ bị bỏ qua và giao diện giữ nguyên tệp $B$.
2. **Given** người dùng mở tệp $A$ (`.txt`) và ngay lập tức mở tệp $B$ (`.docx`), **When** tệp $B$ hoàn tất trước còn tệp $A$ hoàn tất sau, **Then** kết quả của tệp $A$ bị hủy bỏ tại mọi điểm kiểm tra thế hệ nhập tệp, không được cập nhật vào ô soạn thảo.
3. **Given** người dùng chọn mở một tệp mới, **When** lệnh đặt lại lịch sử hạt giống trả về thất bại, **Then** hệ thống hiển thị cảnh báo lỗi và hủy bỏ thao tác nạp tệp.

---

### User Story 3 - Kiểm thử Xác định 100% cho Race Condition và Giải phóng Tài nguyên Kiểm thử (Priority: P2)

Các bài kiểm thử tự động phải kiểm chứng chính xác từng giai đoạn của luồng bất đồng bộ mà không phụ thuộc vào tốc độ phần cứng hay thời gian chờ ngẫu nhiên:
1. Kiểm thử đơn vị phải tạm dừng có kiểm soát bước giải nén XOPP để chứng minh chốt chặn giai đoạn 2 (Stage 2 Stale Guard) thực sự hoạt động.
2. Kiểm thử E2E race condition phải điều khiển và giữ yêu cầu kết xuất của tài liệu $A$ ở trạng thái đang xử lý cho tới khi tệp $B$ được nạp xong, sau đó mới giải phóng phản hồi của $A$ để chứng minh $A$ không ghi đè $B$.
3. Toàn bộ bộ hẹn giờ chờ gõ phím (debounce timer) và bộ hẹn giờ chờ tiến trình nền phải được dọn dẹp sạch sẽ giữa các bài kiểm thử.

**Why this priority**: Triệt tiêu hoàn toàn độ trễ ngẫu nhiên (flakiness) trên môi trường CI đa luồng và chứng minh bằng thực nghiệm mọi nhánh điều kiện bảo vệ.

**Independent Test**: Chạy bộ kiểm thử đơn vị và bộ kiểm thử E2E trên trình duyệt (kể cả chế độ nhiều worker song song `--workers=2`), xác nhận 100% kịch bản vượt qua ổn định tuyệt đối.

**Acceptance Scenarios**:
1. **Given** bài kiểm thử đơn vị kiểm tra chốt chặn giải nén (Stage 2), **When** quá trình giải nén của tài liệu $A$ bị tạm dừng chủ động và tài liệu $B$ được kích hoạt trong lúc đó, **Then** khi giải nén $A$ tiếp tục và hoàn tất, dữ liệu của $A$ bị từ chối và chỉ dữ liệu của $B$ được ghi nhận.
2. **Given** bài kiểm thử E2E race condition trên trình duyệt, **When** yêu cầu kết xuất văn bản $A$ được gửi đi và bị giữ lại có kiểm soát cho đến khi tệp $B$ nạp xong, **Then** khi phản hồi của $A$ trả về muộn sau đó, bản xem trước vẫn hiển thị đúng nét vẽ của tệp $B$.
3. **Given** một ca kiểm thử phát sinh sự kiện gõ phím tạo bộ hẹn giờ chờ (debounce timer), **When** ca kiểm thử kết thúc và hàm đặt lại trạng thái kiểm thử được gọi, **Then** bộ hẹn giờ chờ bị hủy ngay lập tức và không kích hoạt yêu cầu kết xuất ngầm ở ca kiểm thử tiếp theo.

---

### User Story 4 - Ổn định hóa Kiểm thử Bảo mật XSS trên CI và Đồng bộ Tài liệu (Priority: P2)

Bài kiểm thử E2E xác minh tính năng chống tấn công chèn mã độc (XSS) trên thanh thông báo lỗi của Kho mẫu chữ phải hoạt động ổn định 100% trên môi trường CI đa luồng, không bị quá trình làm mới kho mẫu bất đồng bộ lúc khởi tạo ứng dụng xóa mất thông báo lỗi đang kiểm thử.

**Why this priority**: Khắc phục trực tiếp nguyên nhân gây đỏ hệ thống CI trên GitHub Actions, đảm bảo toàn bộ các quy trình kiểm tra tự động đều vượt qua bền vững.

**Independent Test**: Chạy `npx playwright test tests/e2e/bank.spec.ts --workers=2` nhiều lần liên tiếp, xác nhận thanh thông báo lỗi `#bank-error-banner` luôn hiển thị đúng nội dung đã được làm sạch mã độc và không bị ẩn đi bởi các tác vụ nền.

**Acceptance Scenarios**:
1. **Given** ứng dụng vừa khởi chạy và quá trình nạp/làm mới danh sách Kho mẫu chữ ban đầu hoàn tất ổn định, **When** hàm hiển thị thông báo lỗi kho mẫu được gọi với chuỗi chứa thẻ HTML độc hại, **Then** thanh thông báo lỗi `#bank-error-banner` hiển thị bền vững trên màn hình, không bị tác vụ làm mới nền xóa mất, và hiển thị nguyên văn thẻ HTML dưới dạng văn bản thuần an toàn.

---

### Edge Cases

- **Thay đổi tùy chọn viết chữ nhưng đóng cửa sổ không bấm Áp dụng**: Người dùng mở bảng tùy chọn, kéo thanh trượt thay đổi tỷ lệ chữ hoặc đổi hạt giống, sau đó đóng bảng tùy chọn và bấm xuất tệp; hệ thống không được phép để các thay đổi chưa áp dụng làm sai lệch trạng thái hoặc cho phép xuất tệp không đồng nhất với cấu hình đã kết xuất.
- **Yêu cầu kết xuất mới gặp lỗi từ tiến trình nền**: Tài liệu $A$ đã kết xuất xong, người dùng sửa văn bản hoặc đổi tùy chọn để kết xuất $B$ nhưng tiến trình nền báo lỗi; lúc này màn hình không được phép xuất tệp cũ của $A$ dưới danh nghĩa là kết quả của $B$.
- **Mở liên tiếp 3 tệp với tốc độ hoàn tất đảo ngược**: Người dùng chọn tệp 1 (.docx chậm), tệp 2 (.txt nhanh), tệp 3 (.md trung bình); hệ thống chỉ được phép hiển thị và kết xuất nội dung của tệp 3.
- **Tranh chấp thời điểm khởi tạo Kho mẫu và hiển thị lỗi**: Tác vụ làm mới giao diện kho mẫu khi ứng dụng mới khởi động hoàn tất ngay sau khi một thông báo lỗi vừa được bật lên.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST gán mã thế hệ kết xuất (`currentRenderGeneration`) tăng đơn điệu cho mỗi yêu cầu kết xuất và đánh dấu ngay trạng thái bản xem trước là cũ (`isRenderStale = true`) khi một thế hệ kết xuất mới bắt đầu.
- **FR-002**: Hệ thống MUST lưu trữ bản chụp đầy đủ của yêu cầu kết xuất đã được cam kết thành công (`renderedSnapshot`), bao gồm: mã thế hệ (`generation`), toàn bộ nội dung văn bản (`text`), định dạng (`format`) và bản sao sâu của toàn bộ tùy chọn viết chữ (`options`).
- **FR-003**: Chức năng kiểm tra điều kiện xuất tệp (`canExport`) MUST trả về `false` nếu bất kỳ điều kiện nào sau đây xảy ra:
  1. Hệ thống đang trong quá trình kết xuất (`isRendering === true`) hoặc bản xem trước đang bị đánh dấu cũ (`isRenderStale === true`).
  2. Mã thế hệ đã cam kết không khớp với mã thế hệ kết xuất hiện hành (`renderedGeneration !== currentRenderGeneration` hoặc `renderedGeneration === 0`).
  3. Chưa có dữ liệu XOPP hoặc tài liệu đã phân tích (`!currentXoppBase64 || !currentDoc`).
  4. Nội dung ô soạn thảo hiện tại, định dạng hiện tại hoặc các tùy chọn viết chữ hiện hành không khớp hoàn toàn (so sánh sâu) với `renderedSnapshot`.
- **FR-004**: Khi người dùng thay đổi bất kỳ thông số nào trong tùy chọn viết chữ hoặc khi một yêu cầu kết xuất thất bại, hệ thống MUST đảm bảo trạng thái xuất tệp bị khóa cho đến khi một bản kết xuất mới với đầy đủ thông số hiện hành được cam kết thành công.
- **FR-005**: Hệ thống MUST thực thi chốt chặn hai giai đoạn (Two-Stage Stale Guard): kiểm tra thế hệ kết xuất và nội dung văn bản tại Giai đoạn 1 (ngay khi Worker trả kết quả) và kiểm tra lại tại Giai đoạn 2 (ngay sau khi giải nén XOPP và phân tích cú pháp XML hoàn tất) trước khi thực hiện cam kết nguyên tử vào trạng thái toàn cục.
- **FR-006**: Hệ thống MUST duy trì một bộ đếm thế hệ nhập tệp (`currentImportGeneration`) tăng đơn điệu mỗi khi người dùng khởi tạo thao tác mở tệp hoặc kéo thả tệp (.txt, .md, .docx).
- **FR-007**: Trong toàn bộ luồng xử lý nhập tệp bất đồng bộ (đọc tệp, đặt lại hạt giống, chuyển đổi tài liệu qua Worker), hệ thống MUST kiểm tra mã thế hệ nhập tệp của thao tác đó trước khi cập nhật giao diện; nếu mã thế hệ nhập tệp không còn là mới nhất, toàn bộ kết quả của lần nhập tệp cũ MUST bị hủy bỏ hoàn toàn.
- **FR-008**: Khi mở tệp mới, nếu lệnh đặt lại lịch sử hạt giống (`resetDocumentSeedHistory`) thất bại, hệ thống MUST hiển thị cảnh báo lỗi và dừng ngay quá trình nhập tệp.
- **FR-009**: Bộ kiểm thử đơn vị MUST có cơ chế kiểm chứng trực tiếp Giai đoạn 2 của Stale Guard bằng cách tạm dừng có kiểm soát quá trình giải nén XOPP của yêu cầu cũ trong khi yêu cầu mới được phát sinh.
- **FR-010**: Bài kiểm thử E2E race condition MUST kiểm soát xác định thời điểm phản hồi của tiến trình nền để đảm bảo yêu cầu kết xuất cũ thực sự vẫn đang chờ xử lý khi tệp mới được nạp vào.
- **FR-011**: Hàm đặt lại trạng thái phục vụ kiểm thử (`resetWriteSyncStateForTesting`) MUST hủy và xóa sạch bộ hẹn giờ chờ gõ phím (`debounceTimer`) cũng như đặt lại toàn bộ các biến thế hệ kết xuất, thế hệ nhập tệp và bản chụp đã cam kết.
- **FR-012**: Bài kiểm thử E2E kiểm tra chống XSS trên thanh thông báo lỗi Kho mẫu chữ MUST đảm bảo quá trình tải dữ liệu kho mẫu ban đầu đã ổn định trước khi kích hoạt hiển thị thông báo lỗi kiểm thử, loại bỏ hoàn toàn xung đột làm ẩn thông báo trên CI.

---

### Key Entities

- **Committed Render Snapshot (`renderedSnapshot`)**: Bản chụp bất biến của lần kết xuất thành công gần nhất đã được đưa lên giao diện, chứa `{ generation, text, format, options }` (trong đó `options` là bản sao độc lập của các tùy chọn viết chữ).
- **Import Generation Counter (`currentImportGeneration`)**: Bộ đếm tăng đơn điệu định danh cho từng thao tác mở tệp của người dùng, dùng để cô lập và hủy bỏ các tác vụ đọc/chuyển đổi tệp hoàn tất muộn.
- **Render Freshness & Generation State**: Tập hợp các biến kiểm soát tính hợp lệ của bản xem trước gồm `currentRenderGeneration`, `renderedGeneration`, `isRendering` và `isRenderStale`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% thao tác xuất tệp (.xopp, .pdf, .png, .svg, .zip) bị chặn an toàn khi thế hệ kết xuất đã cam kết khác với thế hệ hiện hành, khi yêu cầu kết xuất mới nhất bị lỗi, hoặc khi nội dung/định dạng/tùy chọn viết chữ khác với bản chụp đã cam kết.
- **SC-002**: 100% kết quả kết xuất cũ hoàn tất giải nén muộn (Stage 2) bị loại bỏ và không bao giờ ghi đè lên dữ liệu hoặc giao diện của yêu cầu mới hơn, được chứng minh bằng bài kiểm thử đơn vị có kiểm soát thời điểm giải nén.
- **SC-003**: 100% trường hợp mở nhiều tệp liên tiếp (.docx và .txt/.md) hoàn tất lệch thứ tự đều giữ đúng nội dung và định dạng của tệp được chọn cuối cùng.
- **SC-004**: Bài kiểm thử E2E race condition đạt tính xác định 100% thông qua cơ chế điều khiển phản hồi tiến trình nền, không phụ thuộc vào việc phỏng đoán thời gian chạy.
- **SC-005**: 100% các bài kiểm thử đơn vị Node.js, Golden Master Pyodide, kiểm thử Python pytest (>1.427 tests) và toàn bộ 24 bài kiểm thử E2E Playwright (bao gồm bài kiểm thử XSS kho mẫu chạy với `--workers=2`) vượt qua xanh 100% không còn lỗi chập chờn.

---

## Assumptions

- Đối tượng `writeOptions` chứa các giá trị nguyên thủy (số, chuỗi, boolean, hoặc null) đại diện cho cấu hình trang giấy và nét chữ, cho phép sao chép sâu và so sánh tương đương một cách tường minh, nhanh chóng.
- Trong giao diện Modal Tùy chọn viết chữ, các thao tác chỉnh sửa trực tiếp trên các điều khiển giao diện nếu làm thay đổi cấu hình hiện hành so với `renderedSnapshot.options` sẽ ngay lập tức phản ánh vào kiểm tra `canExport()`, đảm bảo người dùng chỉ có thể xuất tệp sau khi bấm "Áp dụng" và quá trình kết xuất mới hoàn tất.
- Môi trường kiểm thử đơn vị và E2E cho phép can thiệp có kiểm soát vào hàm giải nén hoặc thông điệp phản hồi của Worker thông qua các hook kiểm thử chuyên dụng mà không làm thay đổi kiến trúc đóng gói của ứng dụng.
