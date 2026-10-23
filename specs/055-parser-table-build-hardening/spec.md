# Feature Specification: Gia Cố Độ Chuẩn Xác CommonMark, Bảng GFM Và An Toàn Đóng Gói (055-parser-table-build-hardening)

**Feature Branch**: `055-parser-table-build-hardening`  
**Created**: 2026-10-23  
**Status**: Draft  
**Input**: User description: "Báo cáo rà soát repo viet — 23/10/2026 (Commit fd22bbaf). Khắc phục các vấn đề còn lại: P1 Bảo vệ code Markdown chưa bao phủ đầy đủ cú pháp CommonMark (code fence 4 backticks chứa 3 backticks, code span nhiều backtick); P1 Hàng bảng GFM compact không có thanh đứng ở hai đầu bị xé nhỏ khi ô đầu bắt đầu bằng $$; P2 Marker an toàn thư mục build bị lọt vào danh mục precache sw.js và gói zip web; P2 Ngưỡng thời gian cố định trong bài kiểm tra hiệu năng có thể gây không ổn định trên CI."

---

## Bối cảnh và Mục tiêu (Context & Objectives)

Tiếp nối đợt gia cố tại commit `fd22bbaf` (tính bất biến Document IR, chuẩn hóa băm Service Worker và đồng bộ revision giao diện), quá trình rà soát chuyên sâu các đường biên dữ liệu đã phát hiện 4 điểm rủi ro cần xử lý triệt để:

1. **Bảo vệ mã Markdown chưa bao phủ đầy đủ cú pháp CommonMark chuẩn**:
   - Khi khối mã mở bằng 4 ký tự backtick (```` ```` ````) nhưng chứa bên trong một dòng có 3 ký tự backtick, biểu thức chính quy hiện tại nhận nhầm dòng đó là dấu đóng fence sớm, khiến các công thức toán bên trong khối mã ở những dòng tiếp theo bị chuyển đổi sai lệch trong bước `_normalize_math_delimiters()`.
   - Hàm nhận diện đoạn mã nội tuyến `_is_inside_code_span()` chỉ kiểm tra cặp dấu backtick đơn (`` `...` ``), bỏ sót các đoạn mã nội tuyến sử dụng nhiều ký tự backtick (ví dụ ```` ``prefix:$$x=1$$`` ````), dẫn đến việc biểu thức toán nội tuyến bị phân tách thành khối độc lập ngoài ý muốn.
   - Cơ chế bảo vệ mã cần được thống nhất xuyên suốt toàn bộ luồng `import_text()`, bảo đảm dữ liệu mã nguồn của người dùng không bao giờ bị biến đổi.

2. **Hàng bảng GFM compact bị xé nhỏ khi ô đầu tiên chứa công thức toán**:
   - Cú pháp bảng GitHub Flavored Markdown (GFM) cho phép các hàng dữ liệu không có dấu gạch đứng ở hai đầu biên (ví dụ: `Col | Val\n---|---\n$$x=1$$ | 2`).
   - Điều kiện kiểm tra hàng bảng hiện tại loại trừ các dòng bắt đầu bằng `$$`, khiến ô đầu tiên của bảng dạng compact bị hiểu nhầm là khối công thức độc lập và bị chèn dòng ngắt, làm phá vỡ toàn bộ cấu trúc bảng của tài liệu.

3. **Tệp marker an toàn thư mục build bị lọt vào gói phát hành và bộ nhớ đệm Service Worker**:
   - Tệp định danh an toàn `.chuviettay_build_dist` (dùng để xác thực quyền dọn dẹp thư mục dist) bị script đóng gói thu thập nhầm vào danh sách `PRECACHE_URLS` của Service Worker và gói tệp tin phân phối (`.zip`).
   - Các tệp ẩn bắt đầu bằng dấu chấm không phải là tài nguyên phục vụ ứng dụng web, có thể gây lỗi mạng 404 trên các máy chủ web chặn tệp ẩn và làm tăng kích thước manifest vô ích.

4. **Kiểm thử hiệu năng phụ thuộc ngưỡng thời gian cứng gây thiếu ổn định trên CI**:
   - Kiểm thử tỷ lệ mở rộng tuyến tính của bộ phân tách công thức hiện đặt ngưỡng cứng $0.25$ giây cho 5.000 dòng.
   - Trên các máy chủ CI chia sẻ tài nguyên hoặc chịu tải cao, ngưỡng thời gian tuyệt đối này dễ gây ra lỗi kiểm thử ngắt quãng (flaky test) dù thuật toán hoàn toàn đạt hiệu năng tuyến tính $O(n)$.

Mục tiêu của đặc tả này là hoàn thiện tính chuẩn xác theo đặc tả CommonMark/GFM cho bộ nhập liệu Markdown, làm sạch danh mục phân phối web và thiết lập bài đo hiệu năng co giãn tương đối bền bỉ cho CI.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bảo toàn nguyên vẹn khối mã và đoạn mã theo chuẩn CommonMark xuyên suốt quá trình nhập Markdown (Priority: P1)

Là một người dùng soạn thảo tài liệu kỹ thuật có chứa các khối mã lồng nhau (với độ dài backtick khác nhau) hoặc các đoạn mã nội tuyến sử dụng nhiều ký tự backtick, tôi muốn toàn bộ nội dung bên trong các khối mã và đoạn mã được bảo toàn nguyên vẹn 100%, không bị chuyển đổi công thức hay chèn ngắt dòng ở bất kỳ bước nào trong quy trình nạp tài liệu.

**Why this priority**: Dữ liệu mã nguồn của người dùng (đặc biệt trong các tài liệu hướng dẫn lập trình, tài liệu Markdown chứa cú pháp Markdown mẫu) có giá trị cốt lõi; việc làm sai lệch nội dung bên trong khối mã phá hỏng tài liệu của người dùng.

**Independent Test**:
- Nạp một tài liệu Markdown chứa khối mã mở bằng 4 backtick ```` ```` ```` chứa dòng 3 backtick ```` ``` ```` và công thức `\[x=1\]`.
- Nạp một tài liệu chứa đoạn mã nội tuyến 2 backtick ```` ``prefix:$$x=1$$`` ````.
- Xác nhận sau khi gọi hàm nhập liệu `import_text()`, nội dung khối mã và đoạn mã hoàn toàn nguyên bản, không bị biến đổi thành công thức hay bị ngắt dòng sai lệch.

**Acceptance Scenarios**:
1. **Given** một khối mã được mở bằng $K$ ký tự backtick (với $K \ge 3$) hoặc $K$ ký tự tilde,  
   **When** bên trong khối mã xuất hiện các dòng chứa số lượng ký tự backtick/tilde nhỏ hơn $K$,  
   **Then** hệ thống tiếp tục duy trì trạng thái khối mã, không đóng khối sớm và không chuyển đổi bất kỳ cú pháp toán học nào (`\[...\]`, `\(...\)`, `$$...$$`) bên trong.
2. **Given** một khối mã mở bằng $K$ ký tự phân cách,  
   **When** gặp một dòng kết thúc có $M$ ký tự phân cách tương ứng với $M \ge K$,  
   **Then** hệ thống đóng khối mã chính xác và chuyển về trạng thái phân tích văn bản thông thường.
3. **Given** một đoạn mã nội tuyến được bao bọc bởi chuỗi $N$ ký tự backtick liên tiếp (ví dụ: `` ``, ```, v.v.),  
   **When** bên trong đoạn mã xuất hiện chuỗi ký tự `$$` hoặc ký hiệu toán,  
   **Then** hệ thống bảo vệ đoạn mã, không nhận diện là khối công thức display và chỉ kết thúc đoạn mã khi gặp chuỗi đúng $N$ ký tự backtick tương ứng.
4. **Given** toàn bộ pipeline nạp tài liệu `MarkdownImporter.import_text()`,  
   **When** xử lý tài liệu chứa đa dạng các loại khối mã và đoạn mã phức tạp,  
   **Then** văn bản đầu ra trong cây Document IR giữ đúng từng ký tự trong các nút mã nguồn tương ứng.

---

### User Story 2 - Bảo toàn cấu trúc bảng GFM compact khi ô đầu tiên chứa công thức toán (Priority: P1)

Là một tác giả tài liệu sử dụng bảng compact chuẩn GitHub Flavored Markdown (không có dấu gạch đứng `|` ở đầu và cuối dòng), tôi muốn các hàng bảng có ô đầu tiên chứa biểu thức toán học (bắt đầu bằng `$$`) vẫn được nhận diện chính xác là hàng bảng, không bị xé thành nhiều dòng làm hỏng cấu trúc bảng.

**Why this priority**: Bảng biểu compact là cú pháp Markdown rất phổ biến và tiện dụng. Nếu ô đầu tiên chứa công thức bị xé dòng, toàn bộ bảng phía sau sẽ bị vỡ thành các đoạn văn bản rác.

**Independent Test**:
- Nhập tài liệu có bảng compact dạng:
  ```markdown
  Col | Val
  ---|---
  $$x=1$$ | 2
  ```
- Kiểm tra kết quả nhập liệu: bảng được nhận diện là một nút `Table` hoàn chỉnh trong cây Document IR với đúng 2 cột và 2 hàng.

**Acceptance Scenarios**:
1. **Given** một dòng dữ liệu bảng GFM không có dấu `|` ở đầu dòng và ô đầu tiên bắt đầu bằng `$$...$$`,  
   **When** dòng này chứa ký tự phân cách cột hợp lệ và nằm trong ngữ cảnh bảng biểu,  
   **Then** hệ thống nhận diện dòng này thuộc cấu trúc bảng và không thực hiện ngắt tách dòng công thức.
2. **Given** một bảng GFM đầy đủ (có hoặc không có dấu `|` ở hai biên),  
   **When** các ô ở bất kỳ cột nào chứa công thức toán học (`$$...$$` hoặc `$...$`),  
   **Then** cấu trúc dòng và ô của bảng được bảo toàn trọn vẹn khi chuyển đổi sang Document IR.

---

### User Story 3 - Làm sạch tệp marker nội bộ khỏi danh mục Service Worker và gói phát hành web (Priority: P2)

Là một người dùng hoặc quản trị viên triển khai ứng dụng web, tôi muốn gói phát hành web (`dist`) và danh sách nạp trước của Service Worker (`sw.js`) chỉ chứa các tài nguyên thực tế của ứng dụng web, không bao gồm các tệp ẩn nội bộ như `.chuviettay_build_dist` nhằm bảo đảm tính tương thích tối đa với mọi máy chủ web.

**Why this priority**: Các tệp ẩn bắt đầu bằng dấu chấm có thể bị máy chủ web từ chối phục vụ (trả về lỗi 404/403), dẫn đến việc Service Worker không thể hoàn tất cài đặt ngoại tuyến (precache failure) trên môi trường triển khai thực tế.

**Independent Test**:
- Thực hiện quy trình build gói web bằng lệnh đóng gói chuẩn.
- Đọc nội dung tệp `sw.js` sinh ra: xác nhận không có chuỗi `.chuviettay_build_dist` hoặc bất kỳ tệp ẩn nào trong danh sách `PRECACHE_URLS`.
- Kiểm tra danh sách tệp trong gói nén phân phối: xác nhận tệp marker kiểm tra thư mục không bị đưa vào gói zip.

**Acceptance Scenarios**:
1. **Given** thư mục build đầu ra chứa tệp marker `.chuviettay_build_dist`,  
   **When** script tạo file cấu hình Service Worker (`generate_sw_js`),  
   **Then** tệp marker và các tệp ẩn bắt đầu bằng dấu chấm bị loại trừ khỏi danh sách tài nguyên nạp trước.
2. **Given** script đóng gói gói nén phân phối ứng dụng web,  
   **When** tạo tệp nén sản phẩm cuối cùng,  
   **Then** gói phân phối không chứa tệp marker nội bộ của hệ thống build.
3. **Given** các lần chạy build kế tiếp với thư mục dist đã tồn tại,  
   **When** kiểm tra tính hợp lệ của thư mục để dọn dẹp,  
   **Then** cơ chế kiểm tra an toàn vẫn hoạt động chính xác dựa trên marker nội bộ mà không làm rò rỉ marker ra ngoài.

---

### User Story 4 - Kiểm thử hiệu năng co giãn tỷ lệ tuyến tính bền bỉ và không gây gián đoạn CI (Priority: P2)

Là một kỹ sư phát triển phần mềm và duy trì CI/CD, tôi muốn các bài kiểm tra hiệu năng co giãn đối với các tài liệu Markdown dị thường (chứa hàng nghìn ký tự `$$` mở không đóng) hoạt động ổn định trên mọi môi trường chạy tự động, sử dụng tỷ lệ tăng trưởng thời gian tương đối thay vì ngưỡng giây cố định.

**Why this priority**: Các runner CI công cộng có cấu hình phần cứng và tải CPU biến động lớn. Việc dùng ngưỡng thời gian cố định gây ra các cảnh báo đỏ giả (false positive failures), làm chậm tiến độ tích hợp liên tục của dự án.

**Independent Test**:
- Chạy bài kiểm thử hiệu năng với hai quy mô kích thước tài liệu $N$ và $2N$ (hoặc so sánh kích thước lớn với kích thước chuẩn).
- Xác nhận bài kiểm thử đánh giá tỷ lệ thời gian xử lý thỏa mãn tính chất tuyến tính $T(2N) / T(N) \le 3.5$ và vượt qua ổn định trên cả máy phát triển cục bộ và CI.

**Acceptance Scenarios**:
1. **Given** bộ kiểm thử hiệu năng cho trường hợp tài liệu chứa hàng nghìn dòng `$$` không đóng,  
   **When** đo đạc thời gian thực thi với hai kích thước đầu vào khác nhau (ví dụ: $N$ dòng và $2N$ dòng),  
   **Then** bài kiểm tra xác nhận tỷ lệ gia tăng thời gian nằm trong phạm vi tiệm cận tuyến tính (nhỏ hơn tỷ lệ bậc hai $4.0$).
2. **Given** một ngưỡng trần bảo vệ thời gian tối đa để phát hiện trường hợp treo tiến trình (hang/timeout),  
   **When** chạy kiểm thử trên máy chủ CI tải nặng,  
   **Then** ngưỡng trần được thiết lập đủ rộng và hợp lý (ví dụ: $\ge 2.0$ giây) để không gây lỗi ngắt quãng ngoài ý muốn.

---

## Edge Cases

- **Khối mã chưa đóng ở cuối tài liệu (EOF)**: Nếu tài liệu kết thúc khi khối mã (4 backticks) chưa có dấu đóng, toàn bộ phần còn lại đến hết tệp phải được xem là nội dung mã nguồn an toàn, không bị biến đổi công thức.
- **Đoạn mã nội tuyến chứa ký tự backtick lồng nhau**: Cú pháp ```` `` `foo` `` ```` (đoạn mã mở bằng 2 backtick chứa 1 backtick bên trong) phải được nhận diện chính xác là một code span duy nhất kết thúc ở cặp 2 backtick.
- **Ký tự `|` nằm trong công thức toán học của ô bảng**: Ví dụ ô chứa `$$|x| > 0$$ | 2`, dấu gạch đứng nằm trong công thức không được xem là dấu phân cách cột làm gãy bảng.
- **Bảng compact chỉ có 1 cột hoặc định dạng tối giản**: Kiểm tra cấu trúc dòng dựa trên đường phân cách `---|---` và ngữ cảnh bảng để phân biệt với dòng văn bản thường bắt đầu bằng `$$`.
- **Tệp marker build bị xóa thủ công hoặc thư mục trống**: Hệ thống build vẫn xử lý an toàn theo các nguyên tắc đã thiết lập ở đặc tả 054.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Bộ nhập liệu `MarkdownImporter` PHẢI sử dụng một cơ chế phân tích dấu phân cách mã (code delimiter parser) thống nhất và tuân thủ CommonMark cho cả hai giai đoạn: chuẩn hóa dấu công thức (`_normalize_math_delimiters`) và tách khối công thức (`_isolate_display_math_blocks`).
- **FR-002**: Cơ chế phân tích mã PHẢI ghi nhận chính xác độ dài ký tự phân cách mở của khối mã (ví dụ: $K \ge 3$ ký tự backtick hoặc tilde) và CHỈ đóng khối mã khi gặp dòng có số lượng ký tự phân cách tương ứng lớn hơn hoặc bằng $K$.
- **FR-003**: Cơ chế phân tích mã PHẢI hỗ trợ các đoạn mã nội tuyến (code span) được bao bọc bởi chuỗi $N \ge 1$ ký tự backtick liên tiếp, và CHỈ đóng đoạn mã khi gặp chuỗi đúng $N$ ký tự backtick.
- **FR-004**: Toàn bộ nội dung nằm bên trong khối mã và đoạn mã nội tuyến PHẢI được bảo vệ tuyệt đối không bị thay thế dấu phân cách toán học hay bị tách dòng qua phương thức `import_text()`.
- **FR-005**: Bộ phân tích khối công thức PHẢI nhận diện chính xác các hàng bảng GFM dạng compact (không có dấu `|` ở hai biên ngoài) ngay cả khi ô dữ liệu đầu tiên bắt đầu bằng `$$`, bảo đảm không xé hàng bảng thành nhiều dòng.
- **FR-006**: Script build `scripts/build_web.py` PHẢI loại trừ tệp marker `.chuviettay_build_dist` (và các tệp ẩn bắt đầu bằng dấu chấm) khỏi danh sách `PRECACHE_URLS` trong `sw.js` và khỏi tệp lưu trữ nén phân phối web.
- **FR-007**: Bài kiểm thử hiệu năng đối với tài liệu chứa ký hiệu mở `$$` không đóng PHẢI sử dụng phương pháp đo tỷ lệ tăng trưởng thời gian tương đối giữa hai kích thước đầu vào để chứng minh độ phức tạp tuyến tính $O(n)$, kết hợp ngưỡng trần an toàn không gây lỗi ngắt quãng trên CI.

### Key Entities

- **Code Delimiter State**: Cấu trúc theo dõi trạng thái phân cách mã (loại ký tự backtick/tilde, số lượng ký tự phân cách mở, ngữ cảnh khối mã hay đoạn mã nội tuyến).
- **GFM Table Context**: Ngữ cảnh nhận diện bảng biểu Markdown bao gồm dòng tiêu đề, dòng phân cách cột (`---|---`) và các dòng dữ liệu (có hoặc không có thanh đứng biên).
- **Distribution Exclusions**: Danh mục các mẫu tệp tin nội bộ cần loại trừ khi sinh manifest Service Worker và đóng gói phân phối.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% nội dung bên trong các khối mã (mở bằng 3, 4, 5+ backticks hoặc tildes) và đoạn mã nội tuyến (1, 2+ backticks) được giữ nguyên vẹn ký tự sau khi xử lý qua `import_text()`.
- **SC-002**: 100% các bảng GFM compact có ô đầu tiên chứa công thức `$$...$$` được chuyển đổi thành công thành các đối tượng `Table` nguyên vẹn trong Document IR.
- **SC-003**: 0 tệp marker nội bộ (`.chuviettay_build_dist`) hoặc tệp ẩn xuất hiện trong danh sách nạp trước của `sw.js` và gói phát hành web.
- **SC-004**: Bài kiểm thử hiệu năng mở rộng đạt tỷ lệ tăng trưởng $T(2N) / T(N) \le 3.5$, bảo đảm độ phức tạp tiệm cận tuyến tính và vượt qua 100% các lần chạy kiểm thử tự động trên CI.
- **SC-005**: 100% toàn bộ bộ kiểm thử của dự án (hơn 1.300 bài kiểm thử Python và toàn bộ kiểm thử JavaScript) tiếp tục vượt qua mà không có bất kỳ hồi quy nào.

---

## Assumptions

- Chuẩn CommonMark quy định khối mã mở bằng $K$ backtick chỉ có thể được đóng bởi dòng chứa $M \ge K$ backtick (không có ký tự nào khác ngoại trừ khoảng trắng thụt lề cho phép tối đa 3 dấu cách).
- Đoạn mã nội tuyến mở bằng $N$ backtick chỉ kết thúc khi gặp đúng $N$ backtick liên tiếp.
- Tệp marker `.chuviettay_build_dist` tiếp tục được tạo trong thư mục dist để nhận diện thư mục build hợp lệ cho các lần dọn dẹp sau, nhưng được loại trừ ở các bước sinh manifest và nén tệp.
- Việc kiểm thử tỷ lệ hiệu năng trên môi trường CI cung cấp kết quả đo lường khách quan và ổn định hơn so với việc so sánh ngưỡng mili-giây tuyệt đối.
