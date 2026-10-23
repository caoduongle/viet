# Feature Specification: Gia Cố Nền Tảng Kho Mã Nguồn Hậu Rà Soát (054-repo-audit-hardening)

**Feature Branch**: `054-repo-audit-hardening`  
**Created**: 2026-10-23  
**Status**: Draft  
**Input**: User description: "Báo cáo rà soát repo viet — 23/10/2026. Ưu tiên cao nhất là bộ tiền xử lý công thức Markdown, tính bất biến của cây tài liệu khi kết xuất, và tính an toàn của hệ thống build/cache. Tiếp theo là xử lý race condition của preview và minh bạch hóa hợp đồng import DOCX."

---

## Bối cảnh và Mục tiêu (Context & Objectives)

Sau đợt rà soát toàn diện kho mã nguồn ngày 23/10/2026 trên nhánh `main`, hệ thống hiện tại đã có nền tảng kiến trúc phân tầng rõ ràng và kiểm thử CI toàn diện. Tuy nhiên, qua phân tích tĩnh và thẩm định các đường biên xử lý, 5 vấn đề cốt lõi tiềm ẩn rủi ro hồi quy và an toàn hệ thống đã được nhận diện:
1. **Bộ tách khối công thức Markdown (`_isolate_display_math_blocks`)**: Thiếu khả năng nhận biết khối mã (code fence ```` ``` ```` và `~~~`) và đoạn mã nội tuyến (code span), dẫn đến việc làm biến đổi sai lệch nội dung mã mẫu; đồng thời cơ chế quét nhìn trước nhiều dòng có độ phức tạp thời gian bậc hai $O(n^2)$ khi gặp tài liệu lớn chứa các dấu `$$` mở mà không có dấu đóng, gây nguy cơ treo Web Worker.
2. **Đột biến cây tài liệu gốc khi dàn trang (`_layout_inlines`)**: Quá trình gộp các đoạn văn bản liền nhau chỉnh sửa trực tiếp thuộc tính `text` của các nút `Text` trong cây Document IR đầu vào, khiến việc tái sử dụng cùng một đối tượng `Document` cho các lần kết xuất tiếp theo bị nhân đôi văn bản và làm sai lệch nội dung.
3. **Khóa cache Service Worker chưa phản ánh danh tính tài nguyên (`generate_sw_js`)**: Băm cache key chỉ dựa trên chuỗi digest nội dung mà không kèm đường dẫn tương đối đã chuẩn hóa theo thứ tự bảng chữ cái, có thể tạo ra cache key trùng lặp khi hoán đổi file hoặc không ổn định giữa các môi trường build khác nhau.
4. **Nguy cơ xóa nhầm thư mục dữ liệu ngoài kho lưu trữ (`prepare_dist_dir`)**: Tham số thư mục đầu ra của script build chưa có cơ chế kiểm tra an toàn thư mục ngoài, có thể tự động xóa vĩnh viễn dữ liệu người dùng nếu truyền nhầm đường dẫn.
5. **Đồng bộ hóa Preview và kho mẫu có nguy cơ hiển thị kết quả cũ do race condition (`write.js`)**: Trạng thái bẩn `isBankDirty` bị xóa dựa trên hoàn tất của request đang chạy thay vì đối chiếu với phiên bản sửa đổi kho mẫu, khiến giao diện có thể báo "đã đồng bộ" dù đang hiển thị bản kết xuất cũ khi có yêu cầu cập nhật chen ngang.

Mục tiêu của đặc tả này là thiết lập các tiêu chuẩn hành vi và tiêu chí nghiệm thu chặt chẽ để loại bỏ hoàn toàn các rủi ro nền tảng trên trước khi tiếp tục mở rộng các tính năng mới.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tuyến tính hóa bộ tách công thức Markdown và bảo vệ tuyệt đối khối mã (Priority: P1)

Là một người dùng soạn thảo tài liệu kỹ thuật có chứa cả khối mã lập trình (code fence), đoạn mã nội dòng (code span) và công thức toán học, tôi muốn hệ thống phân tách chính xác các khối công thức display mà tuyệt đối không làm biến đổi bất kỳ nội dung nào bên trong khối mã, đồng thời xử lý các tài liệu lớn có lỗi cú pháp một cách nhanh chóng với độ phức tạp tuyến tính $O(n)$ mà không làm treo trình duyệt.

**Why this priority**: Lỗi làm biến đổi nội dung code fence phá hủy dữ liệu người dùng khi viết tài liệu kỹ thuật/bài giảng tin học; trong khi việc bùng nổ thời gian xử lý bậc hai $O(n^2)$ làm sập Web Worker khi người dùng dán tài liệu lớn có công thức chưa hoàn thiện.

**Independent Test**:
- Nhập một đoạn tài liệu chứa khối mã ```` ```latex prefix:$$x=1$$ ``` ```` và xác nhận chuỗi bên trong code fence được giữ nguyên 100%, không bị chèn dòng trống hay tách khối.
- Nhập một tài liệu gồm 5,000 dòng có nhiều ký tự `$$` mở không đóng; đo thời gian xử lý: quá trình nhập phải kết thúc trong dưới 100ms, không tăng theo hàm mũ hay bình phương.

**Acceptance Scenarios**:
1. **Given** văn bản Markdown chứa khối mã mở bằng ```` ``` ```` hoặc `~~~`,  
   **When** bộ tách khối công thức xử lý văn bản,  
   **Then** toàn bộ nội dung nằm giữa cặp dấu mở và đóng khối mã được giữ nguyên vẹn tuyệt đối, không có dòng trống hoặc phép ngắt dòng nào được chèn vào.
2. **Given** văn bản chứa đoạn mã nội dòng đặt trong cặp dấu backtick `` `...` ``,  
   **When** văn bản chứa ký hiệu `$$` nằm bên trong đoạn mã nội dòng,  
   **Then** hệ thống không nhận diện đó là điểm bắt đầu của khối công thức display.
3. **Given** tài liệu Markdown có kích thước lớn chứa nhiều dấu `$$` chưa đóng hoặc sai cú pháp,  
   **When** hệ thống thực hiện nhập tài liệu,  
   **Then** bộ phân tích cú pháp hoạt động theo máy trạng thái một lượt (single-pass state machine) với thời gian thực thi tỷ lệ thuận tuyến tính $O(n)$ với độ dài văn bản, không làm nghẽn tiến trình nền.
4. **Given** các cấu trúc bảng GFM, danh sách thụt lề hoặc công thức đa dòng hợp lệ,  
   **When** bộ phân tích một lượt xử lý,  
   **Then** các cấu trúc này tiếp tục hoạt động chính xác theo chuẩn CommonMark.

---

### User Story 2 - Bảo đảm tính bất biến của Document IR trong toàn bộ quá trình dàn trang (Priority: P1)

Là một nhà phát triển tích hợp hoặc hệ thống chạy nhiều tác vụ kết xuất lặp lại, tôi muốn khi truyền cùng một đối tượng cây tài liệu `Document` vào bộ dàn trang nhiều lần (với các cấu hình hoặc hạt giống ngẫu nhiên khác nhau), cây tài liệu gốc phải được bảo toàn tính bất biến (immutability), không bị thay đổi hoặc nối thêm chuỗi vào các nút văn bản.

**Why this priority**: Việc thay đổi trực tiếp (mutation) lên các node của đối tượng nguồn truyền vào vi phạm nghiêm trọng tính đóng gói của kiến trúc hệ thống, gây ra lỗi tích lũy dữ liệu âm thầm khi ứng dụng tái sử dụng cây tài liệu cho các trang in tiếp theo hoặc trong các tác vụ render nền.

**Independent Test**:
- Tạo một đối tượng `Document` chứa đoạn văn với hai phần tử `Text("Xin chào ")` và `Text("Việt Nam")`.
- Gọi hàm kết xuất `write_document(doc)` lần thứ nhất, sau đó gọi lại `write_document(doc)` lần thứ hai trên cùng đối tượng `doc`.
- Kiểm tra nội dung văn bản: các nút trong `doc` giữ nguyên vẹn nội dung ban đầu, văn bản kết xuất của cả hai lần hiển thị giống hệt nhau mà không bị lặp thành `"Xin chào Việt Nam Việt Nam"`.

**Acceptance Scenarios**:
1. **Given** một cây `Document` đầu vào chứa các nút `Text` liền kề trong cùng một dòng/đoạn văn,  
   **When** bộ dàn trang thực hiện tối ưu hóa gộp các phần tử văn bản để đo đạc và tính toán nét chữ,  
   **Then** bộ dàn trang tạo ra cấu trúc dữ liệu bản sao mới hoặc danh sách trung gian độc lập, tuyệt đối không sửa đổi thuộc tính `text` của đối tượng gốc do caller sở hữu.
2. **Given** cùng một đối tượng `Document` được đưa vào kết xuất $N$ lần liên tiếp với cùng seed ngẫu nhiên,  
   **When** so sánh kết quả kết xuất giữa các lần chạy,  
   **Then** hình ảnh và tọa độ nét vẽ của các lần chạy phải giống hệt nhau 100%, và cấu trúc cây `Document` trước và sau mỗi lần chạy hoàn toàn không suy suyển.

---

### User Story 3 - Chuẩn hóa khóa bộ nhớ đệm Service Worker định danh tài nguyên và tái lập (Priority: P2)

Là một người dùng ứng dụng Web PWA, tôi muốn ứng dụng luôn cập nhật bộ nhớ đệm (cache) chính xác ngay khi có bất kỳ thay đổi nào về nội dung tệp hoặc vị trí tệp trong gói phát hành, đồng thời việc xây dựng gói ứng dụng trên các máy chủ CI khác nhau phải cho ra cùng một khóa bộ nhớ đệm nhất quán khi mã nguồn không đổi.

**Why this priority**: Khóa cache không ổn định hoặc bỏ sót đường dẫn tệp dẫn đến nguy cơ người dùng tiếp tục tải tài nguyên cũ bị hỏng phiên bản, hoặc tạo ra các bản build không có tính tái lập (reproducible build).

**Independent Test**:
- Chạy script sinh Service Worker trên hai môi trường có thứ tự duyệt tệp ngẫu nhiên khác nhau nhưng cùng nội dung tệp; xác nhận khóa `CACHE_NAME` và manifest sinh ra trùng khớp từng ký tự.
- Đổi tên hoặc đổi đường dẫn của một tệp tài nguyên mà không đổi nội dung; xác nhận khóa `CACHE_NAME` thay đổi tương ứng.

**Acceptance Scenarios**:
1. **Given** danh sách tài nguyên tĩnh được đóng gói vào Web Client,  
   **When** script tạo file `sw.js` tính toán khóa `CACHE_NAME`,  
   **Then** dữ liệu đầu vào để băm bao gồm đường dẫn tương đối chuẩn tắc và chuỗi SHA-256 của từng tệp, được sắp xếp thứ tự bảng chữ cái theo đường dẫn tương đối.
2. **Given** hai lần chạy build trên cùng một tập tin nguồn,  
   **When** hệ thống xuất bản gói phân phối,  
   **Then** nội dung tệp Service Worker và khóa cache tạo ra hoàn toàn đồng nhất.
3. **Given** có sự thay đổi về đường dẫn tệp (dù nội dung file giữ nguyên) hoặc thay đổi nội dung tệp,  
   **When** xây dựng lại gói ứng dụng,  
   **Then** khóa cache phải tự động thay đổi để kích hoạt chu trình cập nhật Service Worker trên trình duyệt người dùng.

---

### User Story 4 - Bảo vệ an toàn đường dẫn và ngăn chặn xóa dữ liệu ngoài ý muốn khi Build Web (Priority: P2)

Là một lập trình viên hoặc kỹ sư CI thực hiện lệnh đóng gói ứng dụng web với tham số thư mục tùy ý `--dist`, tôi muốn script build chỉ tự động dọn dẹp các thư mục nằm trong phạm vi an toàn được định nghĩa trước, và từ chối dọn dẹp các thư mục không rỗng ngoài dự án nếu không có cờ xác nhận tường minh, nhằm ngăn chặn nguy cơ xóa nhầm dữ liệu quan trọng của máy chủ hoặc người dùng.

**Why this priority**: Lệnh dọn dẹp thư mục tự động (`shutil.rmtree`) nếu không được kiểm soát ranh giới nghiêm ngặt có thể xóa sạch các thư mục chứa mã nguồn hoặc dữ liệu cá nhân nếu người dùng gõ nhầm đường dẫn đích (ví dụ truyền nhầm thư mục Desktop hoặc thư mục gốc hệ thống).

**Independent Test**:
- Tạo một thư mục thử nghiệm bên ngoài dự án chứa các tệp dữ liệu giả định và chạy lệnh build trỏ `--dist` tới thư mục đó mà không kèm cờ xác nhận; lệnh build phải dừng lại với thông báo lỗi rõ ràng và bảo toàn 100% dữ liệu trong thư mục đó.
- Chạy lệnh build trỏ tới thư mục mặc định `webapp/dist`; quá trình dọn dẹp và đóng gói diễn ra bình thường, trơn tru.

**Acceptance Scenarios**:
1. **Given** đường dẫn `--dist` trỏ tới thư mục phân phối chuẩn của dự án (`webapp/dist`),  
   **When** thực thi quy trình build,  
   **Then** hệ thống tự động dọn dẹp và tái tạo thư mục đích an toàn.
2. **Given** đường dẫn `--dist` trỏ tới một thư mục nằm ngoài phạm vi kho mã nguồn và thư mục này đang chứa các tệp tin không do build sinh ra,  
   **When** người dùng không truyền cờ cho phép ghi đè tường minh (`--force-clean`),  
   **Then** script build từ chối xóa thư mục, dừng chương trình và in thông báo cảnh báo an toàn.
3. **Given** người dùng truyền cờ `--force-clean` hoặc thư mục đích là thư mục rỗng/chứa chữ ký build hợp lệ,  
   **When** thực thi build,  
   **Then** hệ thống cho phép tiếp tục quy trình đóng gói.

---

### User Story 5 - Đồng bộ hóa trạng thái Preview theo số hiệu phiên bản kho mẫu đơn điệu (Priority: P2)

Là một người dùng đang luyện viết và bổ sung mẫu chữ mới trong khi hệ thống đang dựng hình bản xem trước (preview), tôi muốn giao diện luôn phản ánh trung thực trạng thái đồng bộ của bản xem trước, không bao giờ đánh dấu "đã đồng bộ" nếu bản xem trước hiển thị trên màn hình chưa chứa các nét chữ mới nhất do tôi vừa dạy.

**Why this priority**: Tình huống tranh chấp giữa yêu cầu kết xuất đang chạy và thay đổi kho mẫu mới có thể xóa cờ bẩn `isBankDirty` sai lệch khi render cũ hoàn tất nhưng render mới bị lỗi, làm người dùng tin rằng tài liệu đã được cập nhật kho mới trong khi thực tế vẫn hiển thị kho cũ.

**Independent Test**:
- Mô phỏng một yêu cầu kết xuất $A$ đang chạy; trong lúc đó tăng phiên bản kho mẫu và yêu cầu kết xuất $B$; kết xuất $A$ hoàn tất thành công, sau đó kết xuất $B$ bị lỗi mạng/worker; giao diện phải giữ nguyên trạng thái "kho mẫu chưa đồng bộ" (dirty) và hiển thị nút/thông báo cho phép người dùng thử lại.

**Acceptance Scenarios**:
1. **Given** kho mẫu được chỉnh sửa hoặc nạp mới,  
   **When** có bất kỳ thay đổi nào trong kho mẫu,  
   **Then** hệ thống tăng số hiệu phiên bản kho mẫu (`bankRevision`) theo hàm tăng đơn điệu.
2. **Given** một tác vụ kết xuất preview được gửi tới Worker,  
   **When** tác vụ bắt đầu,  
   **Then** tác vụ ghi nhận số hiệu phiên bản kho mẫu tại thời điểm gửi (`requestRevision`).
3. **Given** tác vụ kết xuất hoàn thành thành công,  
   **When** cập nhật giao diện xem trước,  
   **Then** hệ thống chỉ xóa cờ `isBankDirty` nếu `requestRevision` trùng khớp với `bankRevision` hiện tại; nếu `bankRevision` đã tăng trong lúc render, cờ `isBankDirty` vẫn được duy trì và tự động kích hoạt kết xuất mới.
4. **Given** tác vụ kết xuất preview bị lỗi hoặc quá thời gian chờ,  
   **When** xử lý lỗi,  
   **Then** hệ thống giữ nguyên trạng thái bẩn và cung cấp cơ chế để người dùng kích hoạt vẽ lại.

---

### User Story 6 - Minh bạch hóa hợp đồng nhập tài liệu Word (DOCX Content-First Transparency) (Priority: P3)

Là một người dùng nhập tệp `.docx` chứa các thành phần phức tạp (như hình ảnh, bảng lồng nhau, công thức MathType cũ), tôi muốn hệ thống thông báo rõ ràng các phần tử nội dung nào đã được chuyển đổi và phần tử nào bị lược bỏ hoặc làm phẳng, để tôi nắm rõ giới hạn của chế độ "Ưu tiên nội dung" (Content-First) mà không bị nhầm lẫn với việc tái tạo chính xác 100% bố cục trang in của Microsoft Word.

**Why this priority**: Tránh kỳ vọng sai của người dùng về việc ứng dụng web viết tay có thể sao chép nguyên vẹn bố cục đồ họa của Word, đồng thời tạo cơ sở kỹ thuật minh bạch cho các bước phát triển pipeline đồ họa trung thực trong tương lai.

**Independent Test**:
- Nạp tệp `.docx` chứa hình ảnh và bảng lồng nhau; kiểm tra danh sách cảnh báo `warnings` trả về từ bộ nhập liệu: phải liệt kê chi tiết vị trí các hình ảnh bị bỏ qua và bảng lồng nhau được làm phẳng thành văn bản tóm tắt.

**Acceptance Scenarios**:
1. **Given** tệp `.docx` chứa hình vẽ hoặc hình ảnh đồ họa (`drawing`/`pict`),  
   **When** nạp vào hệ thống theo chế độ Content-First,  
   **Then** bộ nhập liệu trích xuất toàn bộ văn bản và công thức xung quanh, đồng thời ghi nhận cảnh báo rõ ràng về việc hình ảnh chưa được đưa vào luồng viết tay.
2. **Given** tệp `.docx` có bảng lồng bên trong một ô của bảng cha,  
   **When** nạp vào hệ thống,  
   **Then** cấu trúc ô cha giữ chuỗi tóm tắt rõ ràng và cảnh báo cấu trúc bảng lồng nhau đã được làm phẳng.

---

### Edge Cases

- **Khối mã sử dụng số lượng backtick khác nhau (```` ```` hoặc nhiều hơn)**: Bộ phân tích phải theo dõi đúng độ dài của dãy backtick mở và chỉ đóng khối mã khi gặp dãy backtick có độ dài tương đương hoặc lớn hơn.
- **Khối mã lồng ký tự tilde (`~~~`)**: Hỗ trợ đầy đủ cú pháp CommonMark cho code fence dùng dấu ngã, không nhầm lẫn với ký tự gạch ngang `~~`.
- **Dấu hai chấm nằm trong chuỗi URL hoặc code span**: Ví dụ `https://example.com/$$foo$$` hoặc `` `ta có:$$x$$` `` không được hiểu nhầm thành nhãn dẫn nhập công thức display.
- **Hàng bảng Markdown thiếu dấu gạch đứng kết thúc dòng (`| a | b`)**: Bộ phân tích nhận diện các dòng thuộc bảng dựa trên cấu trúc cột để không chèn dòng trống làm hỏng bảng thiếu dấu gạch cuối.
- **Đầu vào kết thúc bằng ký tự xuống dòng kiểu Windows (`\r\n`) hoặc hỗn hợp (`\r`, `\n`)**: Bộ máy trạng thái chuẩn hóa dòng an toàn, không tạo ra các dòng trống rác chứa `\r`.
- **Tài liệu tái sử dụng chứa cây IR nhiều tầng (Table, List, Paragraph)**: Đảm bảo toàn bộ các nút con ở mọi cấp độ không bị biến đổi thuộc tính khi chạy dàn trang.
- **Tham số `--dist` trỏ tới liên kết mềm (Symlink) hoặc thư mục cha của dự án**: Script build kiểm tra và từ chối xử lý đối với các thư mục hệ thống nhạy cảm hoặc đường dẫn vòng lặp.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI thay thế thuật toán quét nhìn trước của `_isolate_display_math_blocks` bằng một bộ phân tích một lượt (single-pass scanner) hoạt động theo máy trạng thái xác định, bảo đảm thời gian thực thi tỷ lệ tuyến tính $O(n)$ với độ dài tài liệu.
- **FR-002**: Máy trạng thái PHẢI quản lý tối thiểu 4 trạng thái ngữ cảnh: `NORMAL` (văn bản thường), `FENCED_CODE` (khối mã mở bằng ```` ``` ```` hoặc `~~~`), `DISPLAY_MATH` (khối công thức đang mở), và `INLINE_CODE` (đoạn mã nội dòng).
- **FR-003**: Khi ở trạng thái `FENCED_CODE` hoặc `INLINE_CODE`, hệ thống TUYỆT ĐỐI KHÔNG thực hiện bất kỳ phép thay thế, chèn dòng trống hoặc tách khối nào lên nội dung bên trong.
- **FR-004**: Khi phát hiện tài liệu chứa các ký hiệu mở khối công thức `$$` không có dấu đóng tương ứng, bộ phân tích PHẢI kết thúc quét an toàn trong thời gian tuyến tính mà không lặp lại việc tìm kiếm trên các dòng tiếp theo.
- **FR-005**: Bộ dàn trang `DocumentLayoutEngine` TUYỆT ĐỐI KHÔNG được sửa đổi (mutate) các đối tượng trong cây `Document` đầu vào. Khi cần gộp các nút `Text` liền kề để tối ưu hóa nét viết, hệ thống PHẢI tạo ra đối tượng `Text` mới độc lập.
- **FR-006**: Việc gọi phương thức dàn trang nhiều lần trên cùng một đối tượng `Document` PHẢI trả về kết quả hình học đồng nhất và bảo toàn trạng thái ban đầu của đối tượng `Document`.
- **FR-007**: Script tạo Service Worker (`generate_sw_js`) PHẢI tạo khóa `CACHE_NAME` và manifest dựa trên danh sách tài nguyên được sắp xếp theo thứ tự bảng chữ cái của đường dẫn tương đối, kết hợp cặp `relative_path:sha256` chuẩn tắc.
- **FR-008**: Script build (`prepare_dist_dir`) PHẢI bảo vệ các thư mục ngoài kho mã nguồn, chỉ tự động xóa thư mục phân phối mặc định `webapp/dist`; đối với các thư mục khác, hệ thống PHẢI kiểm tra thư mục rỗng hoặc yêu cầu cờ tường minh trước khi thực hiện dọn dẹp.
- **FR-009**: Trình điều khiển giao diện (`write.js`) PHẢI quản lý `bankRevision` tăng đơn điệu mỗi khi kho mẫu thay đổi, và chỉ xóa cờ `isBankDirty` khi phiên bản của bản vẽ hoàn thành khớp chính xác với `bankRevision` hiện hành.
- **FR-010**: Bộ nạp tài liệu `DocxImporter` PHẢI ghi nhận báo cáo chi tiết trong danh sách `warnings` khi phát hiện các đối tượng đồ họa (`drawing`/`pict`) hoặc bảng lồng nhau bị giản lược về dạng chuỗi tóm tắt.

### Key Entities

- **Scanner State**: Trạng thái ngữ cảnh của bộ phân tích cú pháp (văn bản thông thường, khối mã, đoạn mã nội dòng, khối toán học).
- **Document IR (Intermediate Representation)**: Cây dữ liệu tài liệu bất biến đại diện cho các khối (Đoạn văn, Bảng, Danh sách, Khối toán) và các phần tử nội dòng.
- **Bank Revision**: Số nguyên tăng đơn điệu đại diện cho phiên bản trạng thái của kho mẫu chữ viết tay trong phiên làm việc.
- **Build Manifest**: Danh mục chuẩn tắc gồm các cặp đường dẫn tương đối và mã băm nội dung đại diện cho gói ứng dụng tĩnh.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Thời gian xử lý của bộ tiền xử lý Markdown đối với tài liệu lỗi chứa 5,000 ký hiệu `$$` mở không đóng giảm từ trên 5,000ms (hoặc treo tiến trình) xuống dưới 100ms trên môi trường thử nghiệm tiêu chuẩn.
- **SC-002**: 100% nội dung bên trong các khối mã (```` ``` ```` và `~~~`) và đoạn mã nội dòng (`` `...` ``) được bảo toàn nguyên vẹn ký tự sau khi đi qua bộ nhập liệu Markdown.
- **SC-003**: 0 trường hợp đối tượng `Document` đầu vào bị thay đổi thuộc tính `text` sau $N$ lần kết xuất liên tiếp; kết quả kết xuất giữa các lần hoàn toàn giống nhau (độ tương đồng 100%).
- **SC-004**: 100% các lần build trên cùng một mã nguồn cho ra cùng một khóa `CACHE_NAME` của Service Worker, không phụ thuộc vào thứ tự duyệt tệp tin của hệ điều hành.
- **SC-005**: 0 rủi ro xóa nhầm thư mục dữ liệu ngoài dự án khi chạy script đóng gói với tham số `--dist`.
- **SC-006**: 0 trường hợp giao diện thông báo kho mẫu "đã đồng bộ" khi bản xem trước đang hiển thị dữ liệu của phiên bản kho cũ.
- **SC-007**: 100% toàn bộ bộ kiểm thử hiện hữu của dự án (hơn 1,290 bài kiểm thử Python và toàn bộ kiểm thử JavaScript) tiếp tục vượt qua mà không bị hồi quy.

---

## Assumptions

- Việc sử dụng máy trạng thái một lượt trong bộ tiền xử lý Markdown tuân thủ các quy tắc chuẩn của CommonMark về code fence và code span.
- Việc tạo mới các đối tượng `Text` trung gian trong bộ dàn trang không gây suy giảm đáng kể hiệu năng bộ nhớ hay tốc độ thực thi của quá trình kết xuất tài liệu thông thường.
- Các nhà phát triển và hệ thống tự động hóa build chấp nhận việc cung cấp thêm cờ tường minh khi muốn làm sạch một thư mục đích nằm ngoài thư mục phân phối mặc định của dự án.
- Người dùng chấp nhận rằng chế độ nhập tài liệu DOCX hiện tại là chế độ "Ưu tiên nội dung" (Content-First), phục vụ mục đích chuyển đổi văn bản và công thức sang chữ viết tay chứ không phải trình đọc tài liệu Word đa năng.
