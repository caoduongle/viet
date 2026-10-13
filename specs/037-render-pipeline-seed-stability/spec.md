# Feature Specification: Ổn định Dòng kết xuất và Tính tái lập Hạt giống (Render Pipeline Seed Stability)

**Feature Branch**: `feat/037-render-pipeline-seed-stability`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Kết quả rà soát repo viet — bản mới nhất (commit 4d7e5ba): Các thay đổi về quản lý seed đã tiến bộ rõ rệt. Tuy nhiên, chế độ ổn định khi chỉnh sửa văn bản vẫn còn lỗi quan trọng ở đường kết xuất thực tế: engine làm mất thông tin định danh token trước khi gọi hàm sinh nét. P1: Engine làm mất token trước khi sinh nét; P1: RNG của cả dòng vẫn phụ thuộc vào cấu trúc dòng hiện thời; P2: Các chữ số trong công thức toán có thể sử dụng ngữ cảnh seed sai; P2: Thiếu bằng chứng kiểm thử tính tái lập xuyên cả hai engine; P2: Tuyên bố bit-exact xuyên phiên bản chưa được chứng minh đầy đủ; Điểm cần làm rõ: Seed trong Desktop GUI và Phản hồi seed không hợp lệ trong Web Client."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bảo tồn định danh Token và Ngẫu nhiên hình học cục bộ trong Toàn bộ Pipeline Kết xuất (Priority: P1)

Khi người dùng làm việc trong chế độ kiểu chữ ổn định (`stable_variants=True`), họ chỉnh sửa văn bản (ví dụ: chèn thêm từ vào đầu đoạn, sửa câu phía trước, hoặc thêm nội dung vào ô bảng). Hệ thống bảo đảm rằng các từ/token cũ không bị thay đổi hình dạng nét chữ, độ nghiêng, độ run tay (jitter) hay độ dày nét vẽ chỉ vì vị trí dòng, điểm ngắt dòng hay chỉ số phần tử trong dòng bị dịch chuyển.

**Why this priority**: Đây là lỗ hổng cốt lõi khiến tính năng `stable_variants` chưa hoàn thành lời hứa thiết kế trên tài liệu thực tế: việc chọn mẫu ký tự có thể ổn định trong phạm vi kiểm thử hẹp của bộ viết, nhưng toàn bộ độ run và hình thái nét vẽ của trang in thực tế bị đảo lộn khi chỉnh sửa văn bản do mất định danh token khi chuyển tiếp qua pipeline kết xuất.

**Independent Test**:
- Kết xuất một đoạn văn bản hoặc bảng biểu nhiều dòng với `stable_variants=True` và `jitter > 0`.
- Chèn thêm một từ mới vào đầu tài liệu (hoặc đầu ô bảng) và kết xuất lại.
- Trích xuất dữ liệu nét vẽ XML của các token cũ không bị sửa đổi. Xác minh từng tọa độ nét tương đối, góc xoay, độ lệch $y$, độ dày nét và độ run của các token cũ hoàn toàn bất biến (100% khớp nhau).

**Acceptance Scenarios**:

1. **Given** văn bản đoạn văn thường hoặc nội dung trong ô bảng biểu, **When** chuyển tiếp qua các bước tính toán bố cục và sinh nét vẽ, **Then** toàn bộ thông tin định danh token (chuỗi ký tự, số thứ tự xuất hiện, kích thước, nét vẽ) được lưu giữ liên tục và nguyên vẹn đến tận bước sinh nét cuối cùng.
2. **Given** chế độ `stable_variants=True`, **When** sinh nét vẽ cho một mục token, **Then** các yếu tố biến dạng ngẫu nhiên hình học (độ nghiêng, độ dập dềnh, độ dày nét) được neo cố định vào định danh ổn định của token đó, không phụ thuộc vào chỉ số phần tử trong dòng (`it_idx`).
3. **Given** hiệu ứng lượn sóng hoặc nghiêng chung của dòng chữ, **When** văn bản bị ngắt dòng khác đi hoặc tọa độ dòng thay đổi do chèn từ phía trước, **Then** hiệu ứng nét của từng token vẫn giữ nguyên tính ổn định cục bộ và không bị xáo trộn hình thái do thay đổi tọa độ dòng hiện thời.

---

### User Story 2 - Ngữ cảnh Hạt giống Độc lập và Nhất quán cho Chữ số và Công thức Toán học (Priority: P1)

Người dùng kết xuất tài liệu có chứa các công thức toán học (inline và block) và các biểu thức số học. Hệ thống bảo đảm việc chọn mẫu chữ số, khoảng cách giữa các chữ số, và ký hiệu toán học trong công thức hoàn toàn độc lập với nội dung văn bản đứng trước, đồng thời nhất quán 100% giữa bước đo đạc kích thước thử nghiệm (`_scratch`) và bước kết xuất thực tế.

**Why this priority**: Hiện tại các chữ số trong công thức toán gọi hàm xử lý số mà không thiết lập ngữ cảnh token hiện hành, dẫn đến việc khoảng cách và biến thể số bị ảnh hưởng ngẫu nhiên bởi từ văn bản cuối cùng đứng trước công thức, làm sai lệch tính tất định của công thức toán.

**Independent Test**:
- Đặt cùng một công thức toán học (ví dụ: `$f(x) = 123.45$`) sau hai đoạn văn bản có nội dung hoàn toàn khác nhau.
- Kết xuất ở chế độ `stable_variants=True`.
- Xác minh hình dạng nét vẽ, khoảng cách giữa các chữ số và ký hiệu trong công thức toán hoàn toàn đồng nhất giữa hai vị trí.
- Xác minh kích thước đo đạc trong bước thử nghiệm khớp chính xác với kích thước kết xuất thực tế.

**Acceptance Scenarios**:

1. **Given** một công thức toán học chứa chữ số hoặc ký hiệu, **When** xử lý các nút toán học, **Then** hệ thống thiết lập ngữ cảnh hạt giống riêng biệt gắn với định danh công thức, bảo đảm không kế thừa ngữ cảnh token của đoạn văn trước.
2. **Given** một chuỗi số nằm trong công thức hoặc văn bản, **When** tính toán khoảng cách giữa các chữ số liên tiếp, **Then** bộ sinh ngẫu nhiên cục bộ dẫn xuất hạt giống từ chính ngữ cảnh của chuỗi số đó thay vì phụ thuộc vào trạng thái toàn cục cũ.
3. **Given** công thức toán học được đo đạc trong bộ layout thử nghiệm và bộ layout chính, **When** thực thi ở chế độ ổn định, **Then** cả hai bước sử dụng cùng một quy luật dẫn xuất hạt giống và cho ra kích thước hình học trùng khớp.

---

### User Story 3 - Kiểm thử Tích hợp Tính Tái lập Toàn diện trên Cả Hai Engine Kết xuất (Priority: P2)

Nhà phát triển và hệ thống kiểm chuẩn tự động cần bằng chứng vững chắc rằng cơ chế tái tạo hạt giống (`seed_used`) và chế độ kiểu chữ ổn định (`stable_variants`) hoạt động chính xác và đạt mức bit-exact trên cả hai luồng kết xuất: Luồng Ngữ nghĩa (`DocumentLayoutEngine`) và Luồng Khóa bố cục (`FidelityLayoutEngine`).

**Why this priority**: Hiện tại kiểm thử vòng đời seed mới chỉ kiểm tra qua engine ngữ nghĩa, chưa có kiểm thử tự động chứng minh tính tái tạo trên engine fidelity; kiểm thử biến thể ổn định mới chỉ đo ở cấp Writer tách rời mà chưa chạy qua pipeline kết xuất thực tế của tài liệu.

**Independent Test**:
- Chạy kiểm thử tự động kết xuất tệp Word (.docx) ở chế độ fidelity với `seed=None`. Lấy `seed_used` chạy lại và kiểm tra tệp XOPP đầu ra giống nhau 100% từng byte.
- Chạy kiểm thử tích hợp chèn từ đầu câu qua hàm điều khiển cấp cao (`write_text` / `write_document`) với `jitter=1.0` trên cả văn bản, bảng và công thức, xác nhận nét chữ của các phần tử cũ không thay đổi.

**Acceptance Scenarios**:

1. **Given** một tài liệu được kết xuất qua `FidelityLayoutEngine` với `seed=None`, **When** lấy giá trị `result.seed_used` để kết xuất lại tài liệu đó, **Then** kết quả đầu ra giống nhau từng byte (SHA-256 trùng khớp 100%).
2. **Given** một tài liệu chứa hỗn hợp văn bản thường, bảng biểu và công thức toán học, **When** chèn thêm từ vào đầu tài liệu ở chế độ `stable_variants=True` với độ run tay bật (`jitter > 0`), **Then** dữ liệu nét vẽ XML của các từ cũ giữ nguyên vẹn tọa độ tương đối và hình thái nét.

---

### User Story 4 - Đồng bộ Hiển thị Seed và Phản hồi Người dùng trên Mọi Giao diện (Priority: P2)

Người dùng kết xuất tài liệu qua Desktop GUI hoặc Web Client. Hệ thống hiển thị rõ ràng hạt giống hiệu dụng đã sử dụng (`seed_used`) trong bảng thông tin/báo cáo kết quả của Desktop GUI (tương tự như CLI và Web). Đồng thời, khi người dùng nhập giá trị hạt giống không hợp lệ trên Web Client, giao diện hiển thị phản hồi trực quan ngay cạnh ô nhập liệu thay vì chỉ ghi log vào bảng điều khiển trình duyệt (`console.warn`). Desktop GUI cũng cung cấp checkbox cấu hình chế độ `stable_variants` tương đương Web và CLI.

**Why this priority**: Nâng cao trải nghiệm người dùng và tính minh bạch của quy trình tái tạo tài liệu: người dùng máy tính để bàn có thể xem và lưu lại seed để chạy lại sau này, chủ động bật/tắt chế độ chữ ổn định; người dùng web nhận biết tức thì khi nhập seed ngoài phạm vi hợp lệ.

**Independent Test**:
- Mở Desktop GUI, thực hiện kết xuất văn bản với ô seed để trống. Xác minh trong ô báo cáo trạng thái hiển thị rõ dòng thông tin `Seed đã dùng: <seed_used>` cùng hướng dẫn tái tạo. Kiểm tra có checkbox "Kiểu chữ ổn định (stable_variants)" và bật/tắt thành công.
- Mở Web Client, nhập seed âm hoặc chữ cái vào ô cấu hình seed. Xác minh giao diện hiển thị thông báo phản hồi trực quan màu đỏ/cam ngay dưới ô nhập liệu (`#opt-seed-error`) và giữ nguyên seed hợp lệ hiện tại.

**Acceptance Scenarios**:

1. **Given** người dùng thực hiện kết xuất trong Desktop GUI không chỉ định seed, **When** quá trình kết xuất hoàn tất, **Then** ô báo cáo kết quả hiển thị thông tin hạt giống đã dùng (`seed_used`) kèm gợi ý cách tái tạo.
2. **Given** người dùng Web Client nhập giá trị hạt giống không hợp lệ vào ô cài đặt, **When** sự kiện thay đổi giá trị kích hoạt, **Then** giao diện hiển thị một nhãn cảnh báo nhỏ màu đỏ/cam ngay dưới ô nhập seed (`#opt-seed-error`), tự động ẩn khi nhập lại seed hợp lệ, đồng thời giữ nguyên hạt giống hợp lệ trước đó.
3. **Given** tùy chọn kiểu chữ ổn định trong Desktop GUI, **When** người dùng thao tác trên tab Viết, **Then** giao diện cung cấp checkbox "Kiểu chữ ổn định (stable_variants)" cho phép người dùng chủ động bật/tắt chế độ chỉnh sửa không đổi nét chữ.

---

### Edge Cases

- **Token rỗng hoặc ký tự đặc biệt**: Khi dòng chỉ chứa ký tự khoảng trắng, ngắt dòng (`\n`), hoặc ký hiệu chưa có mẫu trong kho, pipeline vẫn duy trì cấu trúc định danh token mà không gây lỗi chỉ số.
- **Dòng bị tràn và ngắt sang trang mới trong ô bảng**: Khi ô bảng có nhiều dòng tràn qua mép trang in, metadata của từng token trên các dòng bị ngắt và chuyển tiếp sang trang sau vẫn được bảo toàn nguyên vẹn.
- **Biểu thức toán học bắt đầu bằng số**: Khi công thức toán bắt đầu bằng số (ví dụ: `$1/2 + x$`), chữ số đầu tiên nhận đúng ngữ cảnh toán học thay vì bị gán token rỗng hoặc token văn bản trước đó.
- **Nhập hạt giống biên**: Khi người dùng nhập hạt giống bằng $0$ hoặc $4294967295$ ($2^{32}-1$), tất cả các giao diện (CLI, GUI, Web) đều chấp nhận là giá trị hợp lệ và không tự động thay thế bằng giá trị mặc định.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI sử dụng một cấu trúc dữ liệu tường minh (thay vì tuple rời rạc dễ mất trường) để đại diện cho các mục hiển thị trong pipeline kết xuất dòng chữ và ô bảng, lưu giữ tối thiểu: định danh token, chuỗi văn bản, số thứ tự xuất hiện, danh sách nét vẽ, độ rộng và trạng thái thiếu mẫu.
- **FR-002**: Hệ thống PHẢI dẫn xuất số ngẫu nhiên cho hình dạng nét vẽ (độ nghiêng, độ dập dềnh, độ dày nét) từ định danh ổn định của token và thứ tự xuất hiện của token trong tài liệu, TUYỆT ĐỐI KHÔNG phụ thuộc vào chỉ số phần tử trong dòng (`it_idx`).
- **FR-003**: Hệ thống PHẢI loại bỏ sự phụ thuộc của biến dạng dòng chữ vào tọa độ thực tế `base_y` hoặc token đầu dòng hiện thời khi ở chế độ `stable_variants=True`, bảo đảm việc đẩy dòng do chèn từ phía trước không làm biến đổi hình thái nét chữ của các dòng phía sau.
- **FR-004**: Bộ bố cục công thức toán học PHẢI thiết lập ngữ cảnh hạt giống độc lập (dựa trên định danh công thức hoặc cây cú pháp) cho mọi thao tác xử lý chữ số, ký hiệu và tính toán khoảng cách số trong công thức.
- **FR-005**: Thao tác đo đạc kích thước thử nghiệm trong toán học (`_scratch`) và thao tác kết xuất toán học chính thức PHẢI chia sẻ cùng quy tắc dẫn xuất hạt giống để bảo đảm kết quả đo đạc và vẽ thực tế trùng khớp tuyệt đối.
- **FR-006**: Hàm định dạng báo cáo kết xuất chung (`write_report_lines`) PHẢI bổ sung dòng thông tin hiển thị hạt giống đã dùng (`seed_used`) khi người dùng không chỉ định seed ban đầu, giúp cả CLI và Desktop GUI tự động đồng bộ hiển thị mà không cần lặp lại mã nguồn.
- **FR-007**: Giao diện Web Client PHẢI hiển thị thông báo lỗi trực quan dạng nhãn cảnh báo ngay dưới trường nhập hạt giống (`#opt-seed-error`) khi giá trị nhập vào không hợp lệ (ngoài khoảng $[0, 4294967295]$, số âm, số thực hoặc chữ cái), và tự động xóa cảnh báo khi nhập giá trị hợp lệ.
- **FR-008**: Bộ kiểm thử tự động PHẢI bao gồm bài kiểm thử tích hợp cấp cao (end-to-end qua `write_text` / `write_document`) chứng minh tính bất biến của nét vẽ khi chèn từ phía trước với `jitter > 0`, trên văn bản thường, bảng biểu và công thức toán học.
- **FR-009**: Bộ kiểm thử tự động PHẢI bổ sung kiểm chứng tái tạo tệp đầu ra giống nhau 100% từng byte qua `seed_used` trên `FidelityLayoutEngine` (song song với `DocumentLayoutEngine`).
- **FR-010**: Tài liệu kỹ thuật và mã nguồn PHẢI phân định rõ ràng hai phạm vi cam kết tính tái lập của `ScopedRNG`: (1) Cam kết 100% bit-exact trên cùng môi trường/runtime CPython hiện tại; (2) Đối với đa môi trường (CPython vs Pyodide WASM, Windows vs Linux) cam kết tương đương về mặt phân phối thống kê, chỉ nâng lên cam kết bit-exact xuyên môi trường khi có bộ kiểm thử đối soát đa nền tảng trong CI.
- **FR-011**: Giao diện Desktop GUI (`chuviettay/view/write_tab.py`) PHẢI bổ sung checkbox "Kiểu chữ ổn định (stable_variants)" liên kết với `WriteOptions(stable_variants=...)`, đồng bộ đầy đủ khả năng bật/tắt tính năng với CLI và Web Client.

### Key Entities

- **RenderItem**: Đối tượng cấu trúc dữ liệu lưu giữ đầy đủ thông tin một mục kết xuất trong dòng chữ (tọa độ tương đối, nét vẽ, độ rộng, định danh token gốc, chuỗi ký tự, số thứ tự xuất hiện).
- **TokenIdentifier**: Định danh duy nhất và bền vững của một token trong toàn bộ phạm vi tài liệu, cho phép dẫn xuất bộ sinh ngẫu nhiên cục bộ không bị ảnh hưởng bởi quá trình phân dòng hay phân trang.
- **MathRenderContext**: Ngữ cảnh sinh số ngẫu nhiên cô lập dành riêng cho một biểu thức toán học cụ thể, ngăn ngừa rò rỉ trạng thái giữa toán học và văn bản thông thường.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Khi chèn thêm 1 hoặc nhiều từ vào bất kỳ vị trí nào trong tài liệu ở chế độ `stable_variants=True` với độ run tay bật (`jitter > 0`), 100% các từ cũ không bị sửa đổi giữ nguyên tọa độ nét vẽ tương đối và hình thái nét (độ lệch kiểm tra bằng 0).
- **SC-002**: 100% các công thức toán học chứa chữ số cho ra hình thái và khoảng cách chữ số giống hệt nhau bất kể nội dung văn bản đứng trước công thức là gì.
- **SC-003**: 100% các lượt kết xuất tự động với `seed_used` trên cả hai engine (Semantic và Fidelity) tạo ra tệp đầu ra có mã băm SHA-256 trùng khớp hoàn toàn với lượt kết xuất ban đầu.
- **SC-004**: Người dùng trên cả 3 giao diện (CLI, Desktop GUI, Web Client) đều nhận được thông tin hạt giống đã dùng sau khi kết xuất thành công với `seed=None`.
- **SC-005**: 100% trường hợp người dùng nhập giá trị seed sai trên Web Client đều kích hoạt thông báo trực quan trên giao diện và ngăn chặn việc áp dụng giá trị sai vào phiên làm việc.
- **SC-006**: Người dùng Desktop GUI có thể bật/tắt chế độ `stable_variants` trực tiếp qua giao diện đồ họa và kiểm chứng kết quả phản hồi nhất quán với CLI.

## Assumptions

- Thuật toán băm phân tách hạt giống hiện tại (`blake2b` trong `ScopedRNG`) đã đủ nhanh và ổn định về mặt mật mã học cho việc dẫn xuất hạt giống cục bộ.
- Việc chuyển đổi bộ tuple `cur_line` / `render_items` sang cấu trúc dữ liệu tường minh không làm giảm hiệu năng kết xuất tài liệu lớn (dưới 100ms cho trang văn bản tiêu chuẩn).
- Các hàm toán học số thực (`math.log`, `math.sqrt`, `math.cos`) trong phép biến đổi Box-Muller đảm bảo tính nhất quán hoàn toàn trên cùng một nền tảng và runtime CPython chuẩn.
- Giao diện Desktop GUI sử dụng thư viện đồ họa Tkinter tiêu chuẩn, việc bổ sung checkbox và nhãn thông báo không đòi hỏi thêm bất kỳ thư viện phụ thuộc ngoài nào.
