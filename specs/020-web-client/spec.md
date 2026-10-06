# Feature Specification: 020 — Web Client tĩnh 100% phía trình duyệt

**Feature Branch**: `feat/020-web-client`  
**Created**: 2026-10-06  
**Status**: Draft (GĐ0 — chờ duyệt D1–D8)  
**Input**: User description: "Chuyển app 'Chữ viết tay của bạn' (Python, MVC, CLI + Tkinter) thành web app tĩnh 100% client-side (HTML/CSS/JS + Pyodide), deploy lên Render Static Site. Ba sản phẩm: chuyển văn bản thành ảnh chữ viết tay; trình soạn thảo trực tiếp có xem trước; kho mẫu nhiều kiểu cho mỗi nhãn. Mọi dữ liệu ở lại trình duyệt. Lõi Python giữ nguyên hành vi; CLI và Tkinter không bị đụng tới." (bản đầy đủ: prompt người dùng ngày 2026-10-06, mục 0–10)

> Ghi chú phạm vi: spec này mô tả **cái gì** và **vì sao**. Các ràng buộc công nghệ (Pyodide, Render, không framework…) là **ràng buộc cứng do người dùng chốt**, được ghi riêng ở mục *Ràng buộc* chứ không phải lựa chọn thiết kế mở. Chi tiết cách làm thuộc `plan.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mở web, nạp kho mẫu của mình, thấy thống kê (Priority: P1 — G1)

Là người đã có kho chữ viết tay (`.json.gz`) từ bản desktop,
tôi muốn mở một trang web, nạp kho của mình (hoặc tạo kho trống) và thấy ngay thống kê kho,
để dùng app trên mọi máy mà không cài Python và không gửi dữ liệu đi đâu.

**Why this priority**: Là nền cho mọi tính năng khác; không nạp được kho thì không viết, không dạy được.
**Independent Test**: Mở bản build trên localhost, chọn "Nhập kho có sẵn" với `tests/data/kho_mau_tong_hop.json.gz`, thấy đúng số nhãn theo từng loại; tải lại trang, kho vẫn còn.

**Acceptance Scenarios**:
1. **Given** trình duyệt chưa có kho nào, **When** mở app, **Then** thấy màn hình chào với 3 lựa chọn: Nhập kho có sẵn / Tạo kho trống và bắt đầu dạy / Xem hướng dẫn; app không tự tải kho nào từ máy chủ.
2. **Given** màn hình khởi động, **When** runtime đang nạp, **Then** có thanh tiến trình phản ánh tiến độ thật và chấm trạng thái chuyển "Đang khởi động" → "Sẵn sàng".
3. **Given** đã nhập kho, **When** đóng và mở lại trang, **Then** kho được nạp lại từ bộ nhớ trình duyệt, không cần nhập lại.
4. **Given** đã có một kho, **When** tạo kho mới, **Then** kho cũ không bao giờ bị ghi đè (mỗi kho là một hồ sơ có tên).

---

### User Story 2 - Viết văn bản thành chữ viết tay của tôi, xem trước trực tiếp và xuất file (Priority: P1 — G2)

Là người dùng,
tôi muốn gõ (hoặc mở/kéo-thả `.txt/.md/.docx`) và thấy chữ viết tay của chính mình hiện trên trang giấy sau khi ngừng gõ, rồi tải về `.xopp`, PNG, SVG hoặc in/PDF,
để tạo ghi chú viết tay mà không cần CLI.

**Why this priority**: Giá trị cốt lõi của sản phẩm.
**Independent Test**: Với kho tổng hợp, gõ một đoạn có công thức `$...$` và bảng, chờ xem trước, tải `.xopp`; so byte với CLI cùng văn bản/seed/tuỳ chọn → giống hệt.

**Acceptance Scenarios**:
1. **Given** kho đã nạp, **When** ngừng gõ ~250 ms, **Then** trang xem trước cập nhật mà không chớp trắng và giao diện không bị khựng.
2. **Given** đang gõ tiếng Việt bằng bộ gõ Telex/VNI, **When** đang trong chuỗi soạn ký tự, **Then** xem trước chỉ cập nhật sau khi soạn xong ký tự.
3. **Given** gõ nhanh liên tục, **When** nhiều yêu cầu xem trước phát sinh, **Then** chỉ bản mới nhất được hiển thị (bản cũ bị bỏ, tối đa một yêu cầu chờ).
4. **Given** cùng văn bản, seed và tuỳ chọn, **When** tải `.xopp` từ web và chạy CLI, **Then** hai file giống hệt từng byte (nếu D3 bật thì CLI dùng cờ ổn định tương ứng).
5. **Given** seed hiển thị trên giao diện, **When** xuất file, **Then** file xuất dùng đúng seed của bản xem trước ("thấy gì tải nấy"); nút xúc xắc đổi seed.
6. **Given** văn bản có từ chưa có mẫu, **When** xem trước, **Then** bảng "từ thiếu mẫu" liệt kê theo số lần xuất hiện giảm dần rồi theo bảng chữ cái; bấm một từ → sang tab Dạy với từ đó đã nạp (và gạch đứt đỏ trên trang nếu D2 được duyệt).
7. **Given** chế độ Markdown, **When** dùng thanh công cụ (tiêu đề 1–3, danh sách •/1., chèn bảng hàng×cột, công thức dòng/khối, ngắt trang), **Then** ô văn bản nhận đúng cú pháp mà bộ nhập Markdown của lõi hiểu.
8. **Given** bảng ký hiệu toán, **When** mở, **Then** danh sách ký hiệu lấy từ lõi (không chép tay), nhóm theo loại; bấm để chèn.
9. **Given** importer trả cảnh báo/lỗi, **When** xem trước, **Then** cảnh báo hiển thị cho người dùng.
10. **Given** tài liệu nhiều trang, **When** xuất ảnh, **Then** chọn được trang hiện tại hoặc tất cả, độ phân giải 1x/2x/3x, nền giấy hoặc trong suốt; nhiều trang tải riêng từng trang hoặc một file ZIP; SVG/PNG khớp nét trong `.xopp` và vẽ cả nền giấy (lined/ruled/graph/dotted).
11. **Given** bộ đếm, **When** gõ, **Then** hiển thị "N từ | M ký tự | X/Y từ có mẫu".

---

### User Story 3 - Dạy mẫu chữ bằng chuột/bút/cảm ứng (Priority: P1 — G3)

Là người dùng,
tôi muốn vẽ mẫu cho mọi loại nhãn mà tab Dạy desktop đang hỗ trợ (từ/cụm từ, chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh) trên máy tính hoặc iPad/Android bằng bút,
để bổ sung kho ngay trên web với cùng tỉ lệ như mẫu dạy trên desktop.

**Why this priority**: Không dạy được thì kho không lớn lên; từ thiếu mẫu không có cách sửa.
**Independent Test**: Phát lại cùng một chuỗi điểm qua đường desktop (hàm quy đổi + teach) và đường web → kho JSON thu được giống hệt.

**Acceptance Scenarios**:
1. **Given** một nhãn trong hàng đợi, **When** vẽ và nhấn Enter, **Then** mẫu được lưu, chuyển sang nhãn kế; Esc bỏ qua; Ctrl+Z hoàn tác nét.
2. **Given** vùng vẽ, **When** hiển thị, **Then** có đường dóng có nhãn (chân chữ, mốc chiều cao chữ thường từ kho; với chữ cái là 4 dòng của lưới hw3 lấy từ cấu hình lõi) và chữ mẫu mờ bật/tắt được.
3. **Given** vẽ bằng bút trên máy tính bảng, **When** lòng bàn tay chạm màn hình, **Then** chạm của lòng bàn tay bị bỏ qua ở mức cơ bản; trang không cuộn khi vẽ.
4. **Given** nét vừa vẽ, **When** lưu, **Then** dữ liệu lưu là điểm thô đã lọc khoảng cách tối thiểu như desktop (làm mượt chỉ để hiển thị; không lưu áp lực bút).
5. **Given** người dùng muốn, **When** dùng các chức năng thêm từ/cụm từ, nạp từ thông dụng còn thiếu, hiệu chỉnh cỡ tay, **Then** hành vi giống tab Dạy desktop.
6. **Given** một loại nhãn mà controller chưa phủ, **When** khảo sát GĐ0, **Then** được báo cáo thay vì tự thêm.

---

### User Story 4 - Quản lý kho mẫu nhiều kiểu cho mỗi nhãn (Priority: P2 — G4)

Là người dùng,
tôi muốn xem thống kê, tìm kiếm, mở một nhãn để xem các kiểu chữ cạnh nhau, thêm kiểu mới, xem thử ngẫu nhiên, xoá nhãn (có Hoàn tác), sao lưu/nhập kho và chuyển hồ sơ,
để kiểm soát chất lượng và độ đa dạng của kho.

**Why this priority**: Tăng chất lượng đầu ra; cần cho an toàn dữ liệu (sao lưu).
**Independent Test**: File kho xuất từ web mở được bằng CLI `stats`; kho cũ nhập vào dùng được; mở một nhãn có 4 mẫu thấy 4 hình thu nhỏ.

**Acceptance Scenarios**:
1. **Given** kho đã nạp, **When** mở tab Kho, **Then** có thẻ thống kê theo loại, ô tìm kiếm lọc tức thì, lưới nhãn kèm hình thu nhỏ và số mẫu.
2. **Given** một nhãn, **When** mở thư viện mẫu, **Then** thấy từng kiểu cạnh nhau; nút "Thêm kiểu mới" (sang tab Dạy), nút "Xem thử ngẫu nhiên" (viết lại nhãn vài lần với seed khác); chỉ báo độ phủ khi chữ cái/dấu có ít hơn 2 mẫu.
3. **Given** xoá cả nhãn, **When** xác nhận, **Then** nhãn biến mất và toast có nút Hoàn tác; Hoàn tác khôi phục nhãn (chỉ bật khi đã kiểm chứng bằng test cơ chế tombstone/readded_at an toàn).
4. **Given** nút Sao lưu, **When** bấm, **Then** tải về `.json.gz` tương thích 100% với file kho và CLI hiện có.
5. **Given** nhiều hồ sơ, **When** chuyển hồ sơ qua chip tên kho, **Then** mọi tab dùng kho mới; kho cũ nguyên vẹn.

---

### User Story 5 - Không mất dữ liệu khi mở nhiều tab (Priority: P2 — G4)

Là người dùng hay mở nhiều tab,
tôi muốn hai tab cùng dạy/xoá trên cùng một kho mà không mất mẫu và không làm "sống lại" nhãn đã xoá,
để yên tâm dùng như app desktop.

**Why this priority**: Rủi ro mất dữ liệu cá nhân là rủi ro lớn nhất của bản web.
**Independent Test**: Kiểm thử e2e hai tab: tab A dạy từ X, tab B xoá từ Y cùng lúc → cả hai tab hội tụ: X có, Y không.

**Acceptance Scenarios**:
1. **Given** hai tab cùng hồ sơ, **When** cả hai cùng lưu, **Then** kết quả là hợp nhất theo đúng cơ chế hợp nhất của lõi (không viết lại logic hợp nhất ở giao diện).
2. **Given** tab A xoá nhãn, **When** tab B (dữ liệu cũ) lưu sau, **Then** nhãn không hồi sinh.
3. **Given** trạng thái lưu, **When** đang ghi/ghi xong/lỗi, **Then** hiển thị "Đang lưu" / "Đã lưu vào trình duyệt" / "Lỗi lưu"; lỗi dung lượng có cảnh báo rõ.

---

### User Story 6 - Dùng offline, cài như app, cập nhật an toàn (Priority: P3 — G5)

Là người dùng,
tôi muốn sau lần mở đầu tiên app chạy được khi mất mạng, có thể cài như ứng dụng, và được báo khi có bản mới,
để dùng ổn định ở mọi nơi.

**Independent Test**: Mở app một lần, ngắt mạng, tải lại → app chạy, viết và dạy được.

**Acceptance Scenarios**:
1. **Given** đã mở app một lần, **When** offline, **Then** app khởi động và hoạt động đầy đủ (trừ mở `.docx` nếu thành phần đọc `.docx` chưa từng được nạp).
2. **Given** có bản deploy mới, **When** mở app, **Then** thấy thông báo "Có bản mới — tải lại".
3. **Given** dữ liệu trình duyệt có thể bị xoá, **When** dùng app, **Then** app xin quyền lưu trữ bền vững, nút Sao lưu nổi bật, nhắc sao lưu sau N lần dạy hoặc theo thời gian (tắt được).

---

### User Story 7 - Triển khai và bảo trì (Priority: P2 — G1/G5)

Là người bảo trì,
tôi muốn deploy bằng một Blueprint lên Render Static Site, có PR preview, có CI kiểm golden master trong runtime trình duyệt và e2e trên bản build,
để mỗi thay đổi lõi được chứng minh không làm lệch đầu ra trên web.

**Acceptance Scenarios**:
1. **Given** repo kết nối Render, **When** push, **Then** bước build tạo bản tĩnh và publish; PR có bản preview.
2. **Given** CI, **When** chạy, **Then** job web build + golden master (đủ 8 ca, SHA-256 `.xopp` trùng CPython) + e2e đều xanh; các job cũ không đổi.
3. **Given** bản build, **When** kiểm tra, **Then** không chứa `*.json.gz`, `tests/`, `specs/`, `docs/img`, mã giao diện desktop, CLI, fidelity.

---

### Edge Cases

- **Kho lớn / văn bản dài**: xem trước 1 trang vượt 1 s hoặc main thread bị chặn > 50 ms → báo cáo và đề xuất phương án, không tự đổi hướng. Nếu lõi không cho dựng riêng trang đầu, ghi thành hạn chế.
- **Kiểu chữ xáo trộn khi sửa giữa văn bản**: cùng seed nhưng chèn một từ ở đầu làm các từ sau đổi kiểu (do một dòng random chung). Hành vi khi D3 chưa duyệt: chấp nhận và ghi chú; khi D3 duyệt: bật chế độ ổn định trên web.
- **Ký hiệu toán chưa có mẫu**: vẽ tạm bằng nét vector và vào bảng thiếu.
- **LaTeX sai cú pháp**: hiển thị cảnh báo importer; nếu parser nuốt lỗi im lặng thì ghi vào báo cáo, không tự sửa.
- **Ô văn bản thuần chứa `$...$`**: chế độ văn bản thuần không hiểu công thức — giao diện phải cho chọn chế độ Markdown.
- **File kho hỏng / sai schema / schema cũ**: báo lỗi rõ, không ghi đè kho đang có; schema cũ được lõi nâng cấp.
- **Hết dung lượng / trình duyệt xoá dữ liệu**: cảnh báo, gợi ý Sao lưu.
- **Mở `.docx` khi offline lần đầu**: báo cần mạng một lần để tải thành phần đọc `.docx`.
- **Phát hiện file đổi trong hệ file ảo**: nếu cơ chế phát hiện (mtime/size) của lõi không tin cậy trong runtime trình duyệt → dùng thay đổi 3.4 (hàm hợp nhất ở controller).
- **Hẹn giờ lưu hoãn**: runtime trình duyệt không tạo được thread → web không dùng bộ hẹn giờ của lõi; giao diện tự debounce rồi gọi lưu.
- **Màn hình hẹp (~768 px), chế độ tối**: bố cục vẫn dùng được; trang giấy luôn sáng.

---

## Requirements *(mandatory)*

### Functional Requirements

**Nền tảng & dữ liệu**
- **FR-001**: Toàn bộ xử lý (viết, dạy, hợp nhất kho) MUST chạy trong trình duyệt; không request mạng nào mang văn bản, nét vẽ hay kho của người dùng; không analytics/telemetry/endpoint ghi.
- **FR-002**: Lõi Python hiện có MUST là nguồn sự thật duy nhất cho thuật toán; không có bản cài đặt thuật toán thứ hai (không port sang JS).
- **FR-003**: Đầu ra `.xopp` trên web MUST giống từng byte CPython/CLI cho cùng đầu vào/seed/tuỳ chọn; golden master đủ 8 ca chạy trong runtime trình duyệt (môi trường Node) và khớp SHA-256.
- **FR-004**: Kho MUST lưu trong bộ nhớ trình duyệt theo hồ sơ có tên; tạo kho mới không ghi đè kho có sẵn; nhập/xuất `.json.gz` tương thích 100% với CLI.
- **FR-005**: Đồng bộ đa tab MUST dùng lại đúng cơ chế hợp nhất của lõi (tombstone/readded_at) trong một khoá độc quyền theo hồ sơ, và báo các tab khác nạp lại.
- **FR-006**: App MUST xin lưu trữ bền vững, có nút Sao lưu nổi bật, nhắc sao lưu (tắt được), cảnh báo lỗi dung lượng.
- **FR-007**: Lần đầu (không có kho) MUST hiện màn hình chào 3 lựa chọn; không tự tải kho từ máy chủ; bản deploy không chứa kho demo (trừ khi D7 được duyệt).

**Viết chữ**
- **FR-010**: Trình soạn thảo 2 cột (văn bản | trang giấy) MUST cập nhật xem trước sau ~250 ms ngừng gõ, chờ kết thúc soạn IME, giữ tối đa một yêu cầu chờ, không chặn giao diện, không chớp trắng.
- **FR-011**: MUST có chế độ văn bản thuần và chế độ Markdown; thanh công cụ CHỈ sinh cú pháp Markdown mà lõi hỗ trợ: tiêu đề 1–3, danh sách • và 1., bảng hàng×cột, công thức dòng `$...$` và khối `$$...$$`, ngắt trang; hoàn tác/làm lại; đếm từ/ký tự/độ phủ mẫu.
- **FR-012**: Bảng ký hiệu toán MUST lấy danh sách từ lõi, nhóm theo loại, bấm để chèn.
- **FR-013**: MUST mở/kéo-thả `.txt`, `.md`, `.docx`; thành phần đọc `.docx` chỉ tải khi cần.
- **FR-014**: Tuỳ chọn viết MUST phủ đúng các tuỳ chọn của lõi (cỡ chữ, dòng cách, bề rộng dòng, khoảng cách từ, độ run, độ dày nét, seed, màu mực, khổ/hướng/lề/nền giấy; nâng cao: strict-case, ghép chữ cái, auto x-height, khoảng cách chữ cái, khoảng hở bút); giá trị mặc định lấy từ lõi, có nút đặt lại.
- **FR-015**: Seed MUST luôn hiển thị và đổi được; xem trước và xuất dùng cùng seed.
- **FR-016**: Bảng từ thiếu MUST theo thứ tự `missing_sorted` của lõi; bấm từ → tab Dạy với từ đó.
- **FR-017**: Xuất MUST gồm `.xopp` (chính), PNG/SVG (trang hiện tại/tất cả; 1x/2x/3x; nền giấy/trong suốt; nhiều trang: từng trang hoặc ZIP không nén, không thêm thư viện), và In/PDF qua trình in của trình duyệt. Ảnh MUST dựng từ nét trong `.xopp` và vẽ nền giấy theo thông số.
- **FR-018**: Không có chế độ Fidelity (DOCX) trên web; không có định dạng đậm/nghiêng/màu theo đoạn (trừ khi D5/G8 được duyệt).

**Dạy mẫu**
- **FR-020**: MUST dạy được mọi loại nhãn mà tab Dạy desktop dạy, bằng đúng các thao tác dạy của controller.
- **FR-021**: Vùng vẽ MUST dùng hệ toạ độ logic cố định do lõi cung cấp (760×230 hiện nay), co giãn hiển thị; quy đổi sang đơn vị kho MUST do lõi thực hiện (giao diện không chép hằng số).
- **FR-022**: Lọc điểm theo khoảng cách tối thiểu như desktop; lưu điểm thô đã lọc; bỏ qua áp lực bút; hỗ trợ chuột/bút/cảm ứng, chặn cuộn khi vẽ, từ chối lòng bàn tay cơ bản.
- **FR-023**: Đường dóng có nhãn lấy số đo từ kho/cấu hình lõi; chữ mẫu mờ bật/tắt.
- **FR-024**: Hàng đợi có tiến độ; xem mẫu đã có của nhãn; bút/gôm, độ dày, undo/redo/xoá; phím tắt Enter/Ctrl+Z/Esc; thêm từ/cụm từ; nạp từ thông dụng còn thiếu; hiệu chỉnh cỡ tay.

**Kho mẫu**
- **FR-030**: Thẻ thống kê theo loại; tìm kiếm tức thì; lưới nhãn + hình thu nhỏ + số mẫu.
- **FR-031**: Thư viện mẫu theo nhãn: xem các kiểu, thêm kiểu mới, xem thử ngẫu nhiên, chỉ báo độ phủ (< 2 mẫu).
- **FR-032**: Xoá cả nhãn có xác nhận + Hoàn tác (sau khi test chứng minh an toàn). Xoá từng mẫu KHÔNG thuộc v1 (D4/G5b).
- **FR-033**: Xuất file kiểm tra `.xopp`, Sao lưu/Nhập kho, chuyển hồ sơ.

**Giao diện chung**
- **FR-040**: Giao diện tiếng Việt, có chuỗi tiếng Anh dự phòng, mọi chuỗi tập trung một chỗ; chuyển VI/EN.
- **FR-041**: Header (logo, tab, VI/EN, Hướng dẫn, chấm trạng thái: Đang khởi động / Sẵn sàng / Đang xử lý / Đã lưu / Lỗi); chip tên kho + menu; màn hình khởi động có tiến trình thật; Hướng dẫn gộp mục lưu ý khi vẽ của README; toast thay hộp thoại.
- **FR-042**: Chế độ tối theo cài đặt hệ thống (trang giấy vẫn sáng); responsive tới ~768 px; chuyển động ≤ 150 ms; skeleton; a11y cơ bản (nhãn, focus, bàn phím).

**Offline, triển khai, CI**
- **FR-050**: Sau lần mở đầu, app MUST chạy offline; cài được như PWA; thông báo khi có bản mới.
- **FR-051**: Runtime và mọi tài nguyên MUST tự phục vụ từ cùng origin (không CDN lúc chạy); phiên bản runtime ghim và ghi vào README.
- **FR-052**: Bản build MUST không chứa dữ liệu cá nhân, kho, test, specs, ảnh docs, mã desktop/CLI/fidelity; CI fail nếu vi phạm.
- **FR-053**: Triển khai bằng Blueprint Render Static Site có PR preview, rewrite mọi đường dẫn về trang chính, header cache/MIME/bảo mật (CSP chặt nhất mà runtime vẫn chạy).
- **FR-054**: CI thêm job (chỉ ubuntu): build web, golden master trong runtime trình duyệt, e2e trên bản build (gồm kiểm tra không có request ra ngoài origin); không sửa job cũ.
- **FR-055**: README thêm mục Triển khai lên Render và Chạy thử cục bộ; sửa tên file golden master; cập nhật CHANGELOG.

**Thay đổi lõi (danh sách đóng — mọi thứ khác phải hỏi)**
- **FR-060**: AppController nhận bộ hẹn giờ tiêm được; mặc định giữ hành vi cũ.
- **FR-061**: Chuyển hàm quy đổi nét canvas và hằng số canvas sang module không phụ thuộc Tk; module desktop re-export; có test tương đương.
- **FR-062**: Accessor chỉ-đọc liệt kê mẫu của một nhãn theo loại (words/letters/digits/punct/symbols/marks); có test.
- **FR-063**: Hàm hợp nhất kho ở controller CHỈ khi lưu kho của lõi không đủ cho đa tab; có test.
- **FR-064**: Luật MVC một chiều giữ nguyên và test kiến trúc được mở rộng (quét thêm lớp cầu nối và các gói layout/document/importer/math) mà không nới luật cũ.

### Key Entities

- **Hồ sơ kho (Profile)**: một kho mẫu có tên trong trình duyệt; nội dung là bản `.json.gz` schema v4 y như file desktop; có thời điểm sao lưu gần nhất, số lần dạy từ lần sao lưu trước.
- **Nhãn (Label)**: từ/cụm từ, chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh; mỗi nhãn có nhiều **Mẫu (Sample)** = các nét (x,y) + độ rộng.
- **Tài liệu (Document)**: văn bản người dùng + chế độ (thuần/Markdown) + tuỳ chọn viết + seed.
- **Kết quả viết (Write Result)**: các trang nét (từ `.xopp`), danh sách từ thiếu đã sắp xếp, cảnh báo importer.
- **Đặc tả canvas (Canvas Spec)**: kích thước logic, vị trí chân chữ, hệ số phóng, khoảng cách điểm tối thiểu, các dòng lưới — do lõi cung cấp.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% test hiện có xanh trên CPython (ngoại lệ duy nhất được ghi rõ: test phụ thuộc kho cá nhân, chờ D6); golden master 8/8 ca trùng SHA-256 trong runtime trình duyệt.
- **SC-002**: File `.xopp` tải từ web giống từng byte CLI cùng đầu vào trong 100% ca kiểm thử e2e.
- **SC-003**: Phát lại cùng chuỗi điểm qua đường desktop và đường web cho kho giống hệt (100%).
- **SC-004**: Lần mở thứ hai (đã cache) dùng được trong vài giây trên laptop trung bình; số đo thật (kích thước tải sau nén, thời gian tới khi dùng được lần 1/lần 2, độ trễ xem trước 1 trang, long task) được báo cáo.
- **SC-005**: Xem trước 1 trang ≤ 1 s và không có tác vụ nào chặn giao diện > 50 ms; nếu vượt → có báo cáo + đề xuất thay thế.
- **SC-006**: Hai tab cùng dạy/xoá: 0 mẫu bị mất, 0 nhãn đã xoá hồi sinh.
- **SC-007**: 0 request mạng ra ngoài origin của app trong toàn bộ luồng e2e.
- **SC-008**: App chạy offline sau lần mở đầu (e2e kiểm chứng).
- **SC-009**: File kho xuất từ web mở được bằng CLI `stats`; kho desktop nhập vào web dùng được ngay.
- **SC-010**: Người dùng mới đi hết luồng "nhập kho → gõ → thấy xem trước → bấm từ thiếu → dạy → xem trước cập nhật → tải `.xopp`" không cần đọc tài liệu ngoài.

---

## Ràng buộc cứng (do người dùng chốt — vi phạm = làm lại)

1. Không sửa `chuviettay/config.py` và ngưỡng trong `text_utils.find_tone`.
2. Không đọc/ghi `chu_cua_ban.json.gz` trong test/script/build; không commit/đóng gói dữ liệu cá nhân; kho tổng hợp `tests/data` chỉ để test.
3. Toàn bộ test cũ xanh; golden master chạy trong Pyodide (Node + npm `pyodide`, chỉ dev/CI), đủ 8 ca.
4. MVC một chiều: lớp cầu nối và JS không đụng `model/*`; `model/`, `controller/` không biết Pyodide/JS/trình duyệt.
5. Lõi Zero Core Dependencies; frontend HTML/CSS/JS thuần, không framework, không bundler cho mã chạy, không CDN lúc chạy; công cụ build/dev chỉ ở build/dev.
6. Không endpoint ghi/analytics/telemetry; nội dung và nét vẽ không rời trình duyệt.
7. Không thêm tính năng ngoài danh sách; mục tuỳ chọn (G5b, G6, G7, G8, G9) phải hỏi trước.
8. Không đổi đầu ra thuật toán mặc định; thay đổi hành vi nào cũng sau cờ opt-in mặc định tắt.
9. Công nghệ đã chốt: Pyodide (ghim 314.0.7, kiểm bản mới nhất khi bắt đầu) trong Web Worker, tự host; Render Static Site qua `render.yaml`.
10. Thay đổi lõi chỉ trong danh sách đóng FR-060..FR-063 và D1–D5 khi được duyệt; mọi sửa khác trong `model/` → dừng và hỏi.

## Quyết định kiến trúc (Người dùng đã duyệt ngày 2026-10-06)

| Mã | Chủ đề | Kết quả phê duyệt | Giải pháp thực thi |
|----|--------|-------------------|-------------------|
| D1 | Dữ liệu xem trước | **Đã duyệt**: Giữ mặc định | JS đọc lại file `.xopp` từ MEMFS và dựng SVG (không đổi lõi) |
| D2 | Toạ độ token (gạch đỏ từ thiếu trên trang) | **Đã duyệt**: Chấp nhận | Callback tuỳ chọn `token_layout_callback` trong engine (mặc định None) |
| D3 | Kiểu chữ ổn định khi sửa giữa văn bản | **Đã duyệt**: Chấp nhận | `WriteOptions.stable_variants` (mặc định False, CLI có `--stable`, web bật) dùng `hashlib.sha256` |
| D4 | Xoá từng mẫu | **Đã duyệt**: Giữ v1 | Xem từng mẫu + xoá cả nhãn (có Hoàn tác); hoãn xoá từng mẫu sang G5b |
| D5 | Định dạng theo đoạn chữ | **Đã duyệt**: Không | Giữ nguyên KISS/YAGNI, hoãn sang G8 |
| D6 | Sửa test phụ thuộc kho cá nhân | **Đã duyệt**: Sửa test | Dùng monkeypatch/tmp_path trong `test_paths_logging.py` |
| D7 | Kho demo trong bản deploy | **Đã duyệt**: Không | Màn hình chào 3 lựa chọn, không kèm kho demo |
| D8 | Python 3.14 trong CI (job riêng) | **Đã duyệt**: Đồng ý | Thêm job riêng trong CI workflow |

**Cú pháp ngắt trang (Đã chốt)**:
- Nút "Ngắt trang" trên thanh công cụ Markdown sẽ chèn `<!-- pagebreak -->`.
- Tại tầng cầu nối `bridge.py`, bộ xử lý nhận diện cả `<!-- pagebreak -->` và `\pagebreak` để tách tài liệu thành các khối ngăn cách bởi `PageBreak()`, đảm bảo tương thích 100% mà không sửa đổi `MarkdownImporter`.

## Giai đoạn

G0 Khảo sát (báo cáo → CHỜ DUYỆT) → G1 Nền → G2 Viết + xem trước + xuất → G3 Dạy mẫu → G4 Kho + nhập/xuất + đa tab → G5 Hoàn thiện + PWA + hiệu năng + tài liệu. Tuỳ chọn (hỏi trước): G5b, G6, G7, G8, G9. Tiêu chí hoàn thành từng giai đoạn: theo mục 9 của prompt, chi tiết trong `plan.md`/`tasks.md`. Báo cáo từng giai đoạn lưu trong thư mục này.

---

## Assumptions

- **A-001**: Số liệu "hiện trạng đã kiểm chứng" trong prompt (1.073 test, 7/8 ca golden trùng trong Pyodide, `threading.Timer` lỗi trong Pyodide…) là điểm xuất phát; GĐ0 đo lại và ghi kết quả thực tế vào báo cáo.
- **A-002**: Đã đối chiếu nhanh với mã: `AppController.schedule_save` dùng `threading.Timer`; `strokes_to_bank_units` và `ZOOM/BASE_PX/MIN_POINT_DIST` nằm trong `view/word_canvas.py` (import `tkinter` ở đầu file); tab Dạy gọi `teach_letter` cho chữ cái/dấu thanh và `teach_word` cho mọi nhãn còn lại (chữ số/dấu câu/ký hiệu đi qua `teach_word` → phân loại trong kho — GĐ0 kiểm chứng). Chưa thấy mâu thuẫn với prompt.
- **A-003**: Khi `teach_*` gọi với `deferred_save=False`, lõi lưu đồng bộ vào hệ file ảo; web dùng chế độ này (hoặc bộ hẹn giờ tiêm no-op) rồi tự debounce đồng bộ sang bộ nhớ trình duyệt — chốt ở `plan.md`.
- **A-004**: Người dùng dùng trình duyệt hiện đại hỗ trợ Web Worker, WebAssembly, IndexedDB, Web Locks, BroadcastChannel, Pointer Events, Service Worker.
- **A-005**: Ảnh build của Render Static Site có Python — CHƯA kiểm chứng; GĐ0 deploy trang thử để xác nhận.
- **A-006**: `python-docx` + `lxml` chạy được trong Pyodide — CHƯA kiểm chứng; nếu không, mở `.docx` trên web được báo là hạn chế.
