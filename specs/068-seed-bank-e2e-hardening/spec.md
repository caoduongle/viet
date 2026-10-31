# Feature Specification: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

**Feature Branch**: `068-seed-bank-e2e-hardening`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Rà soát repository viet (commit 16a88fdd): P1 sửa lỗi chồng lấn prefix/suffix trong đối chiếu hạt giống khi prefix ngắn (1-2 phần tử), tích hợp đối chiếu hạt giống vào luồng viết thực tế và bảo toàn chỉ số xuất hiện qua nhiều lượt chỉnh sửa liên tiếp, khắc phục lỗi tham chiếu hồ sơ làm hỏng kiểm thử E2E trên trình duyệt và đồng bộ phiên bản kho mẫu qua thao tác lưu/khởi động lại tiến trình; P2 kiểm tra toàn vẹn lỗi từng danh mục trong bản chụp kho mẫu và chống chèn mã HTML trong thông báo lỗi; P3 bổ sung đo kiểm hiệu năng bản chụp kho mẫu lớn."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bảo toàn kiểu chữ chính xác khi chỉnh sửa tài liệu có tiền tố ngắn và qua nhiều lượt sửa liên tiếp (Priority: P1) 🎯 MVP

Là một người dùng soạn thảo và chỉnh sửa văn bản viết tay nhiều lần liên tiếp trong cùng một phiên làm việc, tôi muốn khi chèn, sửa hoặc xóa từ ngữ — kể cả khi đầu tài liệu chỉ có 1 hoặc 2 từ giữ nguyên và có các từ lặp lại ở cả đầu lẫn cuối câu, hoặc khi tôi thực hiện nhiều lượt chỉnh sửa nối tiếp nhau — toàn bộ các từ, ký hiệu và công thức không thay đổi đều giữ nguyên 100% biến thể nét chữ và hình thái hình học như ở lượt kết xuất trước đó.

**Why this priority**: Đây là mục tiêu cốt lõi của chế độ ổn định biến thể nét chữ. Nếu thuật toán cắt tiền tố/hậu tố để hậu tố chồng lấn lên tiền tố ngắn (1–2 từ), hoặc nếu luồng kết xuất thực tế phân tích lại tài liệu từ đầu mà không đối chiếu với tài liệu của lượt trước và không giữ lại chỉ số xuất hiện đã gán qua nhiều lần sửa, người dùng sẽ thấy các chữ cũ bị đổi kiểu nét ngay khi vừa gõ thêm từ mới.

**Independent Test**:
- Soạn tài liệu ban đầu có 1 hoặc 2 từ lặp ở đầu (ví dụ: `"là là đi học"`), kết xuất bản viết tay, sau đó chèn thêm từ mới có chứa từ trùng lặp vào ngay sau tiền tố (ví dụ: `"là là mới là đi học"`): xác nhận hai từ `"là"` đầu tiên và cụm `"đi học"` ở cuối giữ nguyên hoàn toàn chỉ số xuất hiện và hình học nét chữ; từ `"là"` mới chèn nhận chỉ số xuất hiện mới.
- Thực hiện chuỗi chỉnh sửa liên tiếp trên luồng viết thực tế: Tài liệu gốc $\to$ Chèn một từ trùng lặp (Lần sửa 1) $\to$ Chèn tiếp một đoạn văn khác ở vị trí bất kỳ (Lần sửa 2): xác nhận sau Lần sửa 2, toàn bộ nội dung cũ (bao gồm cả nội dung từ tài liệu gốc và nội dung đã chèn ở Lần sửa 1) giữ nguyên chỉ số xuất hiện và hình học nét chữ so với trạng thái ngay trước đó.

**Acceptance Scenarios**:

1. **Given** tài liệu ban đầu và tài liệu chỉnh sửa có phần đầu giống nhau dài 1, 2 hoặc 3 phần tử và có các từ lặp lại ở cả đầu lẫn cuối tài liệu, **When** hệ thống thực hiện đối chiếu hạt giống, **Then** phần hậu tố chung tuyệt đối không được quét chồng lấn qua các phần tử thuộc phần tiền tố chung thực tế, đảm bảo mọi phần tử không đổi ở đầu và cuối giữ nguyên chỉ số xuất hiện gốc.
2. **Given** một tài liệu đã được đối chiếu hạt giống ở lượt chỉnh sửa thứ nhất (các phần tử trong tài liệu đã mang chỉ số xuất hiện thực tế khác với thứ tự đếm tuần tự từ đầu), **When** người dùng tiếp tục chỉnh sửa tài liệu ở lượt thứ hai và các lượt tiếp theo, **Then** hệ thống đọc và bảo toàn đúng các chỉ số xuất hiện đã gán từ lượt trước thay vì đánh số lại tuần tự từ 0.
3. **Given** người dùng bật chế độ ổn định biến thể trong luồng viết văn bản hoặc cầu nối giao diện Web, **When** người dùng gửi văn bản chỉnh sửa để kết xuất lại trong cùng phiên làm việc (và cùng định dạng/tùy chọn hạt giống gốc), **Then** hệ thống tự động đối chiếu tài liệu mới với tài liệu của lượt kết xuất liền trước để giữ nguyên hình thái nét chữ của toàn bộ các phần tử không thay đổi.

---

### User Story 2 - Đồng bộ nhất quán dữ liệu Kho mẫu trên giao diện Web và vượt qua toàn bộ kiểm thử E2E (Priority: P1)

Là một người dùng quản lý kho mẫu chữ viết tay trên trình duyệt (bao gồm nạp kho mẫu, nhập lưới tập viết, dạy chữ, xóa mẫu, hoạt động ngoại tuyến và mở nhiều tab cùng lúc), tôi muốn tab Kho mẫu luôn hiển thị chính xác số lượng và danh sách mẫu chữ ngay sau mọi thao tác cập nhật hoặc đồng bộ đa tab, không gặp lỗi dừng hình hay dùng lại dữ liệu cũ khi tiến trình nền khởi động lại.

**Why this priority**: Lỗi tham chiếu định danh hồ sơ và thiếu cập nhật phiên bản sau khi đồng bộ lưu trữ hoặc khi khởi tạo lại tiến trình nền đang trực tiếp làm hỏng giao diện Kho mẫu và khiến 6 bài kiểm thử tự động đầu-cuối (E2E) trên trình duyệt thất bại.

**Independent Test**:
- Mở ứng dụng Web, nạp kho mẫu hoặc nhập tệp lưới tập viết, chuyển sang tab Kho mẫu: xác nhận dòng tóm tắt hiển thị đúng số lượng chữ cái/mẫu nét và lưới thẻ hiển thị đầy đủ các ký tự vừa nạp.
- Mở hai tab trình duyệt cùng lúc, dạy và xóa ký tự xen kẽ giữa hai tab (có và không có cơ chế khóa trình duyệt): xác nhận sau khi đồng bộ lưu trữ, cả hai tab đều làm mới phiên bản dữ liệu và hiển thị hội tụ chính xác các ký tự mới mà không bị kẹt ở bộ nhớ đệm cũ.
- Mô phỏng tiến trình xử lý nền khởi động lại ở cùng số thứ tự phiên bản: xác nhận giao diện nhận biết thế hệ tiến trình mới và tải lại dữ liệu thay vì dùng nhầm bộ nhớ đệm của tiến trình cũ.

**Acceptance Scenarios**:

1. **Given** người dùng mở tab Kho mẫu, nạp tệp kho mẫu hoặc nhập lưới tập viết trên giao diện Web, **When** giao diện làm mới danh sách kho mẫu, **Then** hệ thống xác định hợp lệ hồ sơ đang hoạt động (hoặc giá trị mặc định an toàn), hiển thị đầy đủ thống kê tổng quan và danh sách thẻ ký tự mà không phát sinh bất kỳ lỗi dừng thực thi nào.
2. **Given** dữ liệu kho mẫu được lưu, xuất hoặc hợp nhất từ bộ nhớ lưu trữ chung giữa nhiều tab trình duyệt, **When** thao tác đồng bộ hoàn tất, **Then** số hiệu phiên bản kho mẫu phải được tăng lên để báo hiệu dữ liệu có thể đã thay đổi, buộc giao diện cập nhật lại danh sách hiển thị mới nhất.
3. **Given** giao diện đang lưu bộ nhớ đệm bản chụp kho mẫu của một tiến trình xử lý nền, **When** tiến trình xử lý nền bị khởi tạo lại (bắt đầu lại số thứ tự phiên bản từ đầu) hoặc người dùng chuyển đổi hồ sơ, **Then** định danh phiên/thế hệ tiến trình thay đổi khiến bộ nhớ đệm cũ tự động mất hiệu lực và giao diện nạp lại dữ liệu mới.

---

### User Story 3 - Đảm bảo tính nguyên tử của bản chụp Kho mẫu và hiển thị thông báo lỗi an toàn (Priority: P2)

Là một người dùng sử dụng tab Kho mẫu trên giao diện Web, tôi muốn bản chụp kho mẫu chỉ được coi là thành công khi tất cả các danh mục thành phần (thống kê, chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh) đều được trích xuất hợp lệ, và mọi thông báo lỗi hiển thị trên màn hình phải được xử lý văn bản thuần an toàn tuyệt đối.

**Why this priority**: Ngăn ngừa tình trạng một danh mục bị lỗi nhưng hệ thống vẫn báo thành công với danh sách rỗng làm người dùng tưởng nhầm bị mất mẫu chữ, đồng thời loại bỏ nguy cơ chèn mã độc (HTML/script injection) qua thông điệp lỗi khi người dùng nạp tệp từ bên ngoài.

**Independent Test**:
- Mô phỏng lỗi khi truy vấn một trong các danh mục con (chữ cái, ký hiệu hoặc dấu thanh) trong lúc tạo bản chụp kho mẫu: xác nhận hệ thống trả về trạng thái thất bại kèm thông điệp lỗi rõ ràng thay vì trả về bản chụp thiếu dữ liệu với trạng thái thành công.
- Truyền một thông điệp lỗi có chứa các thẻ đánh dấu đặc biệt (như `<img src=x onerror=...>`) vào hàm hiển thị lỗi của tab Kho mẫu: xác nhận thông điệp được hiển thị dưới dạng văn bản thuần túy, không có bất kỳ phần tử đánh dấu nào được trình duyệt thực thi.

**Acceptance Scenarios**:

1. **Given** yêu cầu lấy bản chụp tổng hợp kho mẫu, **When** bất kỳ truy vấn thành phần nào (thống kê chung, danh sách chữ cái, ký hiệu, hoặc dấu thanh) gặp lỗi không thành công, **Then** toàn bộ yêu cầu bản chụp trả về trạng thái thất bại cùng nguyên nhân lỗi tương ứng, tuyệt đối không trả về trạng thái thành công với dữ liệu danh mục bị rỗng giả tạo.
2. **Given** có thông báo lỗi cần hiển thị trên thanh cảnh báo của tab Kho mẫu, **When** giao diện dựng phần tử thông báo trên màn hình, **Then** nội dung lỗi được gán dưới dạng văn bản thuần (plain text) an toàn và đi kèm nút đóng hoạt động bình thường mà không sử dụng phép nối chuỗi mã đánh dấu trực tiếp.

---

### User Story 4 - Đo kiểm hiệu năng bản chụp Kho mẫu quy mô lớn (Priority: P3)

Là một kỹ sư phát triển hệ thống, tôi muốn có bài kiểm thử đo lường hiệu năng tạo bản chụp kho mẫu khi kho chứa hàng nghìn nhãn từ/ký tự và nhiều biến thể mẫu nét, nhằm đảm bảo thao tác mở tab Kho mẫu luôn duy trì tốc độ phản hồi tức thì khi dữ liệu của người dùng phình to theo thời gian.

**Why this priority**: Bổ sung mảnh ghép còn thiếu trong bộ kiểm thử hồi quy hiệu năng để kiểm chứng khả năng mở rộng của cơ chế bản chụp kho mẫu một lượt trên dữ liệu lớn.

**Independent Test**:
- Tạo một kho mẫu quy mô lớn (từ 1.000 nhãn trở lên với nhiều biến thể mẫu nét cho mỗi nhãn) và thực thi bài đo kiểm bản chụp kho mẫu: xác nhận dữ liệu trả về đầy đủ, chính xác và hoàn tất trong ngưỡng thời gian phản hồi nhanh.

**Acceptance Scenarios**:

1. **Given** một kho mẫu có quy mô lớn chứa từ 1.000 nhãn trở lên thuộc đầy đủ các danh mục (chữ cái, chữ số, dấu câu, ký hiệu, dấu thanh, từ vựng) và nhiều mẫu nét trên mỗi nhãn, **When** hệ thống thực thi truy vấn bản chụp kho mẫu, **Then** toàn bộ bản chụp được tổng hợp đầy đủ, hợp lệ và hoàn tất trong dưới 200ms.

---

### Edge Cases

- **Tiền tố chung ngắn kèm từ lặp ở ranh giới**: Tài liệu có đúng 1 hoặc 2 từ đầu tiên không đổi (nhỏ hơn ngưỡng cắt nhanh) và từ ngay sau vị trí chèn trùng với từ ở cuối tiền tố (ví dụ `"là đi"` $\to$ `"là mới là đi"` hoặc `"là là đi học"` $\to$ `"là là mới là đi học"`).
- **Đồng bộ hóa chuẩn hóa văn bản (Normalization Sync)**: Văn bản chứa ký tự khoảng trắng không ngắt (`\u00a0`), tab (`\t`) hoặc ký tự điều khiển: việc phân tách token `token_occurrences` PHẢI sử dụng hàm `_normalize_text(node.text or "").split()` thay vì `node.text.split()` để bảo đảm số lượng phần tử trùng khớp tuyệt đối với `DocumentLayoutEngine`.
- **Khởi tạo lại trạng thái khi nạp kho mẫu mới hoặc tài liệu rỗng**: Khi người dùng nạp một tệp kho mẫu mới (`load_bank`), hoặc xóa trắng nội dung tài liệu, hệ thống PHẢI tự động làm mới lịch sử căn chỉnh hạt giống (`_last_doc = None`, `_last_seed = None`) để tránh dùng lại biến thể của kho mẫu cũ.
- **Tài liệu rỗng hoặc thay đổi hoàn toàn**: Chuyển từ tài liệu rỗng sang tài liệu có chữ, xóa trắng tài liệu rồi viết lại, hoặc đổi chế độ định dạng (từ văn bản thuần sang Markdown): hệ thống phải xử lý trơn tru và làm mới trạng thái đối chiếu phù hợp.
- **Nhiều lượt chỉnh sửa xóa rồi chèn lại cùng một từ**: Người dùng có từ `"học"` (chỉ số 0 và 1), xóa từ `"học"` thứ nhất ở lượt sửa 1 (chỉ còn từ `"học"` mang chỉ số 1), sau đó chèn một từ `"học"` mới ở cuối trong lượt sửa 2: từ `"học"` mới chèn phải nhận chỉ số chưa sử dụng tiếp theo (chỉ số 2) thay vì trùng với chỉ số 1 đang tồn tại trong tài liệu.
- **Khởi tạo lại tiến trình nền khi số phiên bản trùng khớp**: Tiến trình cũ đang ở phiên bản số 2 thì gặp sự cố và khởi tạo lại; tiến trình mới sau khi nạp kho cũng có phiên bản số 2: giao diện vẫn phải phát hiện đây là thế hệ tiến trình mới để làm mới dữ liệu.
- **Thông điệp lỗi chứa ký tự điều khiển hoặc mã đánh dấu HTML**: Khi tệp nạp vào bị hỏng hoặc chứa tên nhãn độc hại gây lỗi, thông báo hiển thị trên thanh cảnh báo không được làm vỡ cấu trúc giao diện hay thực thi mã kịch bản.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Thuật toán đối chiếu hạt giống tài liệu PHẢI giới hạn phạm vi quét hậu tố chung sao cho không bao giờ vượt qua hoặc chồng lấn lên phạm vi tiền tố chung thực tế của hai tài liệu, ngay cả khi độ dài tiền tố chung thực tế nhỏ hơn ngưỡng cắt nhanh.
- **FR-002**: Khi trích xuất danh sách phần tử từ tài liệu gốc để đối chiếu hạt giống, hệ thống PHẢI ưu tiên đọc và bảo toàn các chỉ số xuất hiện (`occurrence`) đã được gắn sẵn trên từng phần tử của tài liệu đó từ các lượt đối chiếu trước, đồng thời theo dõi giá trị chỉ số lớn nhất của từng khóa phần tử để cấp phát chỉ số mới không bao giờ bị trùng lặp qua nhiều lượt chỉnh sửa liên tiếp.
- **FR-003**: Luồng kết xuất văn bản thực tế (cả ở tầng điều khiển trung tâm và cầu nối trình duyệt) khi bật tùy chọn ổn định biến thể (`stable_variants`) PHẢI lưu giữ bản sao cấu trúc tài liệu đã đối chiếu của lượt kết xuất thành công liền trước (gắn với ngữ cảnh hạt giống gốc) và tự động đối chiếu tài liệu mới với tài liệu liền trước trước khi dàn trang.
- **FR-004**: Truy vấn bản chụp kho mẫu PHẢI kiểm tra trạng thái thành công của tất cả các truy vấn danh mục thành phần (thống kê, chữ cái, ký hiệu, dấu thanh); nếu bất kỳ truy vấn con nào thất bại, bản chụp phải trả về trạng thái lỗi tường minh thay vì trả về thành công với dữ liệu rỗng.
- **FR-005**: Mọi thao tác trên cầu nối và tiến trình xử lý nền có khả năng làm thay đổi hoặc hợp nhất dữ liệu kho mẫu (bao gồm nạp kho, dạy mẫu, nhập lưới, xóa mẫu, và đồng bộ/lưu xuất kho mẫu giữa các tab) PHẢI tăng số hiệu phiên bản kho mẫu và cung cấp kèm định danh thế hệ phiên xử lý duy nhất.
- **FR-006**: Giao diện tab Kho mẫu PHẢI xác định an toàn định danh hồ sơ hiện hành (không gây lỗi tham chiếu biến chưa khai báo), kiểm tra bộ nhớ đệm dựa trên tổ hợp `(định danh thế hệ tiến trình, số hiệu phiên bản kho, định danh hồ sơ)`, và dựng thanh thông báo lỗi bằng các phần tử văn bản thuần an toàn (không chèn chuỗi HTML trực tiếp).
- **FR-007**: Toàn bộ các bài kiểm thử tự động đầu-cuối (E2E) trên trình duyệt (quản lý kho mẫu, nhập lưới tập viết, đồng bộ đa tab có và không có khóa, hoạt động ngoại tuyến và nhập tài liệu) PHẢI vượt qua 100% không còn lỗi.
- **FR-008**: Bộ kiểm thử hồi quy hiệu năng PHẢI bao gồm bài kiểm tra đo lường thời gian tạo bản chụp kho mẫu trên kho dữ liệu lớn (từ 1.000 nhãn trở lên với nhiều mẫu nét).

### Key Entities *(include if feature involves data)*

- **Bản đối chiếu Hạt giống Đa bước (Multi-Step Seed Alignment State)**: Trạng thái lưu giữ tài liệu đã gán chỉ số xuất hiện của lượt kết xuất trước cùng ngữ cảnh hạt giống, cho phép bảo toàn biến thể nét chữ xuyên suốt chuỗi thao tác thêm, sửa, xóa liên tiếp của người dùng.
- **Định danh Phiên bản Kho mẫu Toàn cục (Composite Bank Revision)**: Tổ hợp gồm định danh thế hệ tiến trình xử lý (`epoch`/`instance_id`), số thứ tự phiên bản kho mẫu (`revision`) và định danh hồ sơ (`profile_id`), dùng để xác định tính mới của dữ liệu kho mẫu trên giao diện.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các từ, ký hiệu và công thức không thay đổi giữ nguyên chỉ số xuất hiện và hình thái nét chữ (sai số hình học $\le 0.02$ pt) khi chèn nội dung mới sau tiền tố chung dài 1, 2, 3 phần tử và qua chuỗi từ 2 đến 5 lượt chỉnh sửa liên tiếp trên luồng viết thực tế.
- **SC-002**: 100% bộ kiểm thử tự động đầu-cuối (E2E) trên trình duyệt (19/19 kịch bản kiểm thử gồm kho mẫu, lưới tập viết, đa tab, ngoại tuyến, viết chữ) và toàn bộ bộ kiểm thử đơn vị/tích hợp hiện có đều vượt qua (PASS) mà không phát sinh lỗi bảng điều khiển (Console ReferenceError/TypeError).
- **SC-003**: 100% các lỗi truy xuất danh mục con trong bản chụp kho mẫu được phát hiện và báo lỗi minh bạch lên giao diện bằng văn bản thuần an toàn (0 lỗ hổng chèn mã đánh dấu HTML).
- **SC-004**: Thời gian tạo bản chụp kho mẫu trên kho dữ liệu lớn (1.000+ nhãn, nhiều biến thể nét) hoàn tất dưới 200ms trong bài kiểm thử hiệu năng.

---

## Assumptions

- Trong một phiên soạn thảo trên giao diện Web hoặc bộ điều khiển, việc đối chiếu hạt giống tự động giữa các lần kết xuất liên tiếp được áp dụng khi người dùng bật cờ ổn định biến thể (`stable_variants=True`) và giữ nguyên hạt giống gốc (`seed`); nếu người dùng chủ động đổi `seed` khác hoặc xóa rỗng hoàn toàn văn bản, hệ thống sẽ khởi tạo lại mốc tài liệu cơ sở mới.
- Định danh hồ sơ trên giao diện Kho mẫu khi chưa được thiết lập tường minh sẽ sử dụng giá trị mặc định chuẩn của hệ thống lưu trữ mà không làm gián đoạn luồng hiển thị.
