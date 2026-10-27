# Feature Specification: Gia Cố An Toàn Xóa Thư Mục Build Và Hoàn Thiện Cú Pháp CommonMark/GFM (056-build-safety-and-markdown-hardening)

**Feature Branch**: `056-build-safety-and-markdown-hardening`  
**Created**: 2026-10-23  
**Status**: Draft  
**Input**: User description: "Rà soát commit 55ee06b (23/10/2026). Xử lý triệt để các vấn đề còn lại: P1 Nguy cơ xóa dữ liệu người dùng khi build lại vào thư mục ngoài do marker cũ tồn tại; P1 Bộ tách code chưa bảo vệ đầy đủ khối mã trong blockquote (> ~~~), indented code block (4 spaces) và backtick bị escape; P2 Nhận diện bảng GFM dựa vào dấu | còn quá rộng khi dòng đơn độc lập không có ngữ cảnh bảng; P2 Tệp marker nội bộ vẫn tồn tại trong thư mục phân phối web thành phẩm; P2 Chưa loại trừ thư mục ẩn khi duyệt os.walk() tạo Service Worker precache; Bổ sung kiểm thử hồi quy chi tiết cho nội dung ô bảng compact, đo độ phức tạp toàn bộ pipeline tiền xử lý, và kiểm thử bảo vệ tệp người dùng mới thêm vào thư mục ngoài."

---

## Bối cảnh và Mục tiêu (Context & Objectives)

Commit `55ee06b` đã khắc phục thành công nhiều vấn đề cốt lõi về CommonMark fence, inline code span, loại trừ marker khỏi `sw.js` precache và ổn định hóa CI test. Tuy nhiên, qua phân tích tĩnh chuyên sâu, 5 vấn đề còn tồn đọng cần được giải quyết dứt điểm để bảo đảm an toàn dữ liệu và tính toàn vẹn cú pháp:

1. **Rủi ro xóa dữ liệu người dùng khi build lại vào thư mục ngoài**:
   - Hàm `prepare_dist_dir()` cho phép `shutil.rmtree()` toàn bộ thư mục đích nếu thấy marker `.chuviettay_build_dist`. Nếu người dùng từng build vào một thư mục ngoài dự án với `--force-clean`, sau đó lưu thêm tài liệu quan trọng vào thư mục đó, việc chạy build lại sau này (dù không truyền `--force-clean`) sẽ vô tình xóa sạch mọi tài liệu mới của người dùng do marker cũ vẫn còn.
   - Nguyên tắc: Với bất kỳ thư mục nào nằm ngoài phạm vi mặc định `webapp/dist`, sự tồn tại của marker không bao giờ được coi là giấy phép vô điều kiện để xóa thư mục không rỗng. Mọi lần dọn dẹp thư mục ngoài không rỗng BẮT BUỘC phải có cờ `--force-clean` tường minh tại chính lần chạy đó.

2. **Cú pháp khối mã CommonMark lồng trong Blockquote, Indented Code và Escaped Backtick**:
   - Khi khối mã fence (backtick hoặc tilde) nằm bên trong trích dẫn blockquote (dòng bắt đầu bằng `>` hoặc `> `), bộ quét đầu dòng hiện tại bỏ qua do ký tự đầu là `>`, khiến các công thức toán bên trong khối mã blockquote bị biến đổi sai lệch.
   - Khối mã thụt lề 4 dấu cách (Indented Code Block) theo CommonMark chưa được bảo vệ khỏi phép biến đổi công thức.
   - Dấu backtick bị thoát bằng gạch ngược (`\``) đang bị nhận nhầm là dấu mở/đóng code span.

3. **Nhận diện bảng GFM compact dựa trên dấu `|` còn quá rộng**:
   - Một dòng đơn độc lập như `$$x=1$$ | 2` nếu không có hàng tiêu đề và hàng phân cách `---|---` thì không phải là bảng GFM hợp lệ. Việc nhận diện quá rộng làm mất cơ hội phân tách khối công thức display độc lập, khiến nó bị giữ lại dưới dạng đoạn văn thường.
   - Cần nhận diện ngữ cảnh bảng (sự hiện diện của hàng phân cách cột hoặc cấu trúc khối bảng) trước khi quyết định bỏ qua bước ngắt dòng.

4. **Làm sạch hoàn toàn tệp marker nội bộ và thư mục ẩn khỏi gói phân phối web**:
   - Tệp `.chuviettay_build_dist` không được phép tồn tại trong thư mục xuất xưởng cuối cùng (`dist_dir`). Marker quản lý an toàn cần được lưu bên ngoài thư mục đích hoặc dọn dẹp trước khi hoàn tất build.
   - Vòng lặp `os.walk(dist_dir)` cần lọc danh sách `dirs` in-place (`dirs[:] = [d for d in dirs if not d.startswith('.')]`) để ngăn chặn việc thu thập các tệp nằm bên trong thư mục ẩn (ví dụ `.internal/secret.js`).

5. **Nâng cao tính nghiêm ngặt của bộ kiểm thử**:
   - Kiểm tra chi tiết giá trị nội dung trong ô bảng compact (ô 1 là math, ô 2 là Text("2")).
   - Đo tỷ lệ mở rộng $T(2N) / T(N) \le 3.5$ trên toàn bộ hàm `_split_code_segments` và pipeline tiền xử lý, không chỉ đo riêng `_isolate_display_math_blocks`.
   - Kiểm thử bảo vệ tệp người dùng khi thư mục ngoài đã có marker nhưng chứa tệp mới thêm vào.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bảo vệ dữ liệu người dùng trong thư mục ngoài dự án khi thực hiện Build Web (Priority: P1)

Là một lập trình viên hoặc người dùng chạy script build web với tham số thư mục tùy chọn `--dist` trỏ tới một thư mục ngoài dự án, tôi muốn script build từ chối xóa thư mục nếu thư mục đó không rỗng và tôi không truyền cờ `--force-clean` tại lần chạy hiện tại, ngay cả khi thư mục đó từng là đích của một lần build trước đây.

**Why this priority**: Nguy cơ mất mát dữ liệu người dùng (data loss) là lỗi nghiêm trọng nhất ở mức P1. Marker của lần build cũ không được phép trở thành "cửa sau" để xóa sạch các tệp tài liệu mới mà người dùng vừa lưu vào thư mục đó.

**Independent Test**:
- Tạo một thư mục ngoài dự án, chạy build với `--force-clean`.
- Tạo thêm một tệp dữ liệu người dùng `important_user_doc.pdf` vào thư mục đó.
- Chạy lại lệnh build trỏ tới thư mục đó mà KHÔNG truyền `--force-clean`.
- Lệnh build phải dừng lại với thông báo lỗi an toàn rõ ràng (`SystemExit`), và tệp `important_user_doc.pdf` được bảo toàn 100%.

**Acceptance Scenarios**:
1. **Given** thư mục đích nằm ngoài phạm vi mặc định `webapp/dist` và đang chứa dữ liệu,  
   **When** người dùng chạy lệnh build mà không cung cấp cờ `--force-clean`,  
   **Then** hệ thống dừng thực thi, từ chối xóa thư mục và giữ nguyên vẹn 100% tệp tin hiện có, bất kể thư mục đó có chứa marker build cũ hay không.
2. **Given** thư mục đích là thư mục mặc định của dự án (`webapp/dist`),  
   **When** chạy lệnh build thông thường,  
   **Then** hệ thống tự động dọn dẹp và tái tạo thư mục phân phối mà không đòi hỏi cờ `--force-clean`.
3. **Given** người dùng truyền cờ `--force-clean` tường minh khi build vào thư mục ngoài không rỗng,  
   **When** thực hiện đóng gói,  
   **Then** hệ thống cho phép làm sạch và tiến hành build bình thường.

---

### User Story 2 - Bảo toàn khối mã trong Blockquote, Indented Code và Escaped Backtick theo CommonMark (Priority: P1)

Là một người dùng soạn thảo tài liệu kỹ thuật có chứa trích dẫn blockquote bao bọc khối mã (`> ~~~latex ...`), khối mã thụt lề 4 dấu cách, hoặc các đoạn văn bản có ký tự backtick bị escape (`\``), tôi muốn toàn bộ các khối mã và ký tự escaped này được bảo vệ tuyệt đối qua toàn bộ quy trình `import_text()`, không bị chuyển đổi công thức hay hiểu nhầm thành dấu mở/đóng code span.

**Why this priority**: Bảo toàn 100% tính toàn vẹn của mã nguồn trong mọi cấu trúc hợp lệ của CommonMark; ngăn ngừa việc làm biến đổi tài liệu bài giảng/kỹ thuật của người dùng.

**Independent Test**:
- Nạp tài liệu chứa trích dẫn blockquote bao bọc khối mã tilde:
  ```markdown
  > ~~~latex
  > \[x=1\]
  > ~~~
  ```
- Nạp tài liệu chứa khối mã thụt lề 4 dấu cách:
  ```markdown
      \[x=1\]
  ```
- Nạp tài liệu chứa backtick bị escape: `dấu \` không đóng code`.
- Xác nhận qua `MarkdownImporter.import_text()`: công thức `\[x=1\]` bên trong không bị chuyển đổi thành `$$x=1$$`.

**Acceptance Scenarios**:
1. **Given** một khối mã mở bằng ```` ``` ```` hoặc `~~~` nằm bên trong trích dẫn blockquote (tiền tố `>` hoặc `> `),  
   **When** tài liệu đi qua toàn bộ pipeline `import_text()`,  
   **Then** nội dung bên trong khối mã blockquote được giữ nguyên vẹn, không bị chuyển đổi dấu phân cách toán học.
2. **Given** một khối mã thụt lề 4 dấu cách (Indented Code Block) theo CommonMark,  
   **When** thực hiện nhập tài liệu,  
   **Then** các ký hiệu toán học bên trong khối thụt lề không bị chuyển đổi sang cú pháp display math.
3. **Given** văn bản chứa ký tự backtick đứng sau dấu gạch ngược thoát (`\``),  
   **When** phân tích các đoạn mã nội dòng,  
   **Then** ký tự backtick bị thoát được xem là ký tự dữ liệu thông thường, không được xem là dấu mở hoặc đóng code span.

---

### User Story 3 - Nhận diện ngữ cảnh Bảng GFM chặt chẽ và bảo toàn giá trị ô (Priority: P2)

Là một người dùng viết tài liệu Markdown có chứa bảng GFM compact hoặc công thức toán học có ký tự gạch đứng `|`, tôi muốn hệ thống chỉ xem một dòng là hàng bảng khi dòng đó thực sự nằm trong một cấu trúc bảng hợp lệ (có hàng phân cách `---|---`), tránh nhận nhầm các dòng văn bản đơn độc có dấu `|` thành bảng biểu, đồng thời bảo toàn chính xác từng giá trị của các ô trong bảng sau khi nạp.

**Why this priority**: Tránh nhận diện nhầm dòng toán đơn lẻ có chứa `|` là hàng bảng (làm mất định dạng MathBlock), đồng thời bảo đảm dữ liệu trong bảng compact (như ô số 2) không bị mất mát hay làm sai lệch.

**Independent Test**:
- Nạp dòng đơn độc lập `$$x=1$$ | 2` (không có header/separator): hệ thống phân tách thành MathBlock và đoạn văn riêng biệt.
- Nạp bảng compact hợp lệ:
  ```markdown
  Col | Val
  ---|---
  $$x=1$$ | 2
  ```
  Hệ thống tạo đúng 1 đối tượng `Table`, hàng 1 chứa tiêu đề `"Col"`, `"Val"`, hàng 2 ô 1 chứa công thức `x=1` và ô 2 chứa văn bản `"2"`.

**Acceptance Scenarios**:
1. **Given** một dòng văn bản chứa ký tự `|` đứng đơn lẻ không có hàng tiêu đề và hàng phân cách cột `---|---`,  
   **When** bộ phân tích kiểm tra ngữ cảnh bảng,  
   **Then** dòng này không được coi là hàng bảng và tiếp tục được xử lý phân tách công thức display bình thường.
2. **Given** một bảng GFM compact hợp lệ có hàng phân cách cột,  
   **When** ô đầu tiên bắt đầu bằng `$$...$$`,  
   **Then** bảng được bảo toàn trọn vẹn cấu trúc và toàn bộ dữ liệu của từng ô được giữ chính xác trong cây Document IR.

---

### User Story 4 - Làm sạch hoàn toàn Artifact thành phẩm và loại trừ thư mục ẩn khỏi Service Worker (Priority: P2)

Là một kỹ sư vận hành triển khai Web Client, tôi muốn thư mục xuất xưởng phân phối web (`dist_dir`) sạch hoàn toàn các tệp marker nội bộ của hệ thống build, đồng thời Service Worker tuyệt đối không thu thập bất kỳ tệp nào nằm trong các thư mục ẩn (dot-directories).

**Why this priority**: Bảo đảm tính tinh gọn, chuẩn tắc và an toàn của gói phát hành; ngăn chặn việc lộ lọt các tệp nội bộ hoặc tệp nhạy cảm trong thư mục ẩn vào bộ nhớ đệm ngoại tuyến của trình duyệt.

**Independent Test**:
- Chạy lệnh build tạo thư mục `dist`.
- Kiểm tra toàn bộ cây thư mục `dist`: không tồn tại tệp `.chuviettay_build_dist` trong thư mục thành phẩm.
- Tạo thư mục giả lập `.internal/sub.js` trong thư mục dist thử nghiệm và chạy `generate_sw_js`: xác nhận tệp trong thư mục ẩn không xuất hiện trong `sw.js`.

**Acceptance Scenarios**:
1. **Given** quy trình build hoàn tất,  
   **When** kiểm tra thư mục phân phối `dist`,  
   **Then** không có tệp marker `.chuviettay_build_dist` tồn tại trong thư mục thành phẩm.
2. **Given** quá trình duyệt tệp tạo danh sách nạp trước Service Worker (`generate_sw_js`),  
   **When** phát hiện thư mục có tên bắt đầu bằng dấu chấm (`.`),  
   **Then** vòng lặp `os.walk` loại bỏ thư mục đó in-place (`dirs[:] = [...]`), không duyệt sâu vào bên trong.

---

### User Story 5 - Bộ kiểm thử hồi quy độ phức tạp tuyến tính và an toàn dữ liệu toàn diện (Priority: P2)

Là một kỹ sư duy trì chất lượng hệ thống, tôi muốn các bài kiểm thử hiệu năng đo lường trên toàn bộ pipeline tiền xử lý (bao gồm `_split_code_segments`), và các bài kiểm thử an toàn thư mục bao phủ kịch bản người dùng thêm tệp mới vào thư mục build cũ.

**Why this priority**: Bảo đảm không bỏ sót điểm nghẽn hiệu năng ở các hàm phân tách chuỗi mới thêm vào, và bảo đảm các ca biên an toàn dữ liệu được tự động kiểm tra trên CI.

**Independent Test**:
- Chạy bài kiểm thử hiệu năng với $N = 2,500$ cặp dòng và $2N = 5,000$ cặp dòng trên toàn bộ luồng `_split_code_segments` và `_isolate_display_math_blocks`, kiểm tra tỷ lệ $T(2N) / T(N) \le 3.5$.
- Chạy bài kiểm thử an toàn thư mục ngoài với kịch bản có tệp người dùng mới thêm vào sau lần build trước.

**Acceptance Scenarios**:
1. **Given** tài liệu Markdown có kích thước lớn chứa nhiều dấu `$$` mở không đóng,  
   **When** đo đạc thời gian thực thi của cả bộ tách mã `_split_code_segments` và phân tách khối toán,  
   **Then** tỷ lệ tăng trưởng thời gian giữa $2N$ và $N$ thỏa mãn điều kiện tuyến tính $T(2N) / T(N) \le 3.5$.
2. **Given** thư mục ngoài chứa marker cũ nhưng có tệp mới do người dùng thêm vào,  
   **When** chạy build không có `--force-clean`,  
   **Then** bài kiểm tra xác nhận thao tác bị từ chối và tệp người dùng không bị xóa.

---

## Edge Cases

- **Blockquote lồng nhau nhiều cấp (`>> ~~~`)**: Chuỗi tiền tố trích dẫn có thể có nhiều ký tự `>` kèm khoảng trắng; bộ phân tích cần tách tiền tố blockquote để nhận diện đúng code fence bên trong.
- **Dấu gạch ngược kép đứng trước backtick (`\\` `)**: Dấu gạch ngược bị thoát thì backtick phía sau không bị thoát (vẫn là backtick hợp lệ).
- **Indented code block nằm sau danh sách**: Các dòng thụt lề 4 dấu cách có thể là continuation của list item hoặc indented code block; cả hai đều là ngữ cảnh mã hoặc ngữ cảnh không được tự ý chèn ngắt dòng công thức.
- **Bảng compact chỉ có 1 dòng dữ liệu và dòng kết thúc ngay sau đó**: Cần kiểm tra dòng separator trước hoặc sau để phân biệt với câu văn chứa `|`.
- **Thư mục ngoài là đường dẫn tương đối hoặc chứa ký tự đặc biệt**: Chuẩn hóa `resolve()` an toàn trước khi kiểm tra đường dẫn.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hàm `prepare_dist_dir()` trong `scripts/build_web.py` TUYỆT ĐỐI KHÔNG được xóa thư mục đích nằm ngoài `webapp/dist` nếu thư mục đó không rỗng và người dùng không cung cấp cờ `--force-clean` tại chính lần chạy đó, bất kể thư mục đó có chứa tệp marker hay không.
- **FR-002**: Cơ chế lưu vết an toàn build PHẢI lưu trữ marker bên ngoài thư mục xuất xưởng phân phối (ví dụ trong `.cache/build_marker/` hoặc thư mục tạm an toàn của hệ thống), bảo đảm thư mục phân phối web thành phẩm hoàn toàn sạch tệp marker nội bộ.
- **FR-003**: Hàm `generate_sw_js()` PHẢI lọc danh sách thư mục `dirs[:] = [d for d in dirs if not d.startswith('.')]` trong vòng lặp `os.walk()` để ngăn chặn việc duyệt và nạp các tệp nằm trong thư mục ẩn vào danh mục Service Worker precache.
- **FR-004**: Bộ tách mã `_split_code_segments()` và `_isolate_display_math_blocks()` PHẢI nhận diện chính xác các khối mã fence nằm bên trong trích dẫn blockquote (tiền tố `>` hoặc `> `) và bảo toàn tuyệt đối công thức bên trong.
- **FR-005**: Bộ tách mã PHẢI bảo vệ các khối mã thụt lề 4 dấu cách (Indented Code Block) theo chuẩn CommonMark khỏi việc chuyển đổi dấu phân cách toán học.
- **FR-006**: Bộ quét đoạn mã nội tuyến `_find_code_spans()` PHẢI kiểm tra tính hợp lệ của dấu backtick, bỏ qua các backtick bị thoát bởi dấu gạch ngược đơn lẻ (`(?<!\\)\``).
- **FR-007**: Hàm kiểm tra hàng bảng `_is_table_line()` PHẢI kết hợp kiểm tra ngữ cảnh bảng (sự tồn tại của hàng phân cách cột `---|---` trong khối bảng), bảo đảm một dòng đơn độc lập chứa ký tự `|` không bị nhận nhầm là bảng GFM.
- **FR-008**: Bài kiểm thử hiệu năng mở rộng PHẢI kiểm tra thời gian thực thi của cả `_split_code_segments` và pipeline tiền xử lý, khẳng định tỷ lệ tăng trưởng $T(2N) / T(N) \le 3.5$.

### Key Entities

- **External Target Safety Guard**: Quy tắc kiểm soát an toàn thư mục ngoài: chỉ dọn dẹp khi thư mục rỗng HOẶC có cờ `--force-clean` tại phiên chạy hiện tại.
- **Contextual Code Fence**: Khối mã được nhận diện trong ngữ cảnh thông thường hoặc ngữ cảnh trích dẫn blockquote.
- **Table Block Context**: Ngữ cảnh khối bảng GFM xác định bởi tập hợp dòng tiêu đề, hàng phân cách cột và các hàng dữ liệu liền kề.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 trường hợp dữ liệu người dùng trong thư mục ngoài bị xóa khi chạy lệnh build không có cờ `--force-clean`.
- **SC-002**: 100% nội dung bên trong code fence blockquote (`> ~~~ ...`) và indented code blocks được bảo toàn nguyên vẹn sau khi nạp qua `import_text()`.
- **SC-003**: 0 tệp marker nội bộ (`.chuviettay_build_dist`) hoặc tệp nằm trong thư mục ẩn xuất hiện trong thư mục `webapp/dist` và danh sách precache của `sw.js`.
- **SC-004**: Dòng đơn độc lập `$$x=1$$ | 2` (không có ngữ cảnh bảng) được phân tách chính xác thành `MathBlock` và `Paragraph`, không bị bỏ sót.
- **SC-005**: 100% dữ liệu từng ô trong bảng compact (bao gồm ô công thức và ô dữ liệu kế tiếp) được bảo toàn nguyên vẹn trong Document IR.
- **SC-006**: Tỷ lệ mở rộng thời gian $T(2N) / T(N) \le 3.5$ trên toàn bộ bộ tiền xử lý Markdown.
- **SC-007**: 100% toàn bộ bộ kiểm thử của dự án (hơn 1.300 bài kiểm thử Python và toàn bộ kiểm thử JavaScript) tiếp tục vượt qua mà không có bất kỳ hồi quy nào.

---

## Assumptions

- Thư mục mặc định `webapp/dist` là thư mục phân phối chuẩn của dự án và được phép tự động làm sạch trong quy trình build chuẩn.
- Người dùng chấp nhận rằng việc dọn dẹp một thư mục ngoài dự án đang chứa dữ liệu luôn đòi hỏi sự xác nhận chủ động qua cờ `--force-clean`.
- Chuẩn CommonMark quy định dòng thụt lề từ 4 khoảng trắng trở lên ở cấp độ gốc (không thuộc list item) là indented code block.
- Khối trích dẫn blockquote có thể bao bọc bất kỳ khối CommonMark nào khác, bao gồm cả code fence.
