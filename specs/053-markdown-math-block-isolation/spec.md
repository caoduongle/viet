# Feature Specification: Nhận Diện Khối Công Thức Toán Display Khi Xuống Dòng Và Ngăn Ngừa Đè Nét Cận Toán Tử (053-markdown-math-block-isolation)

**Feature Branch**: `053-markdown-math-block-isolation`  
**Created**: 2026-10-21  
**Status**: Draft  
**Input**: User description: "tôi gặp lỗi này" kèm 3 ảnh chụp màn hình minh họa:
- Ảnh 1: Khi có dòng trống giữa đoạn văn bản `a` và khối `$$\sum_{j=1}^9 ...$$`, công thức toán hiển thị chuẩn dạng khối display math nhiều dòng, dấu tổng có cận trên và cận dưới dạng xếp chồng rõ ràng (`9` ở trên, `j=1` ở dưới).
- Ảnh 2: Khi xóa dòng trống giữa `a` và `$$\sum...$$` (chỉ cách nhau bằng một dấu xuống dòng đơn `\n`), công thức toán bị nhận diện sai thành công thức nội dòng (`MathInline`), bị ép co nhỏ trên một dòng kẻ, dấu tổng chuyển sang dạng cận bên và nét mực của chỉ số trên `9` đè nát lên chỉ số dưới `j=1`.
- Ảnh 3: Khi xóa ký tự `a` (dòng trên trở thành dòng trống), công thức lập tức được nhận diện lại đúng dạng khối display math nhiều dòng.

---

## Bối cảnh và Vấn đề (Context & Problem Statement)

Trong ứng dụng Chữ Viết Tay, người dùng thường xuyên soạn thảo bài tập toán, bài giảng và tài liệu khoa học bằng cú pháp Markdown kết hợp LaTeX. 

### Hiện tượng quan sát được qua 3 ảnh chụp màn hình:
1. **Ảnh 1 (Hoạt động đúng khi có dòng trống)**:
   - Người dùng nhập văn bản có dòng trống phân cách giữa dòng chữ `a` và công thức `$$\sum_{j=1}^9 P(D = j) = ...$$`.
   - Hệ thống chuyển đổi đúng thành khối công thức độc lập (`MathBlock`): công thức được trình bày ở chế độ display math, dấu $\sum$ có cận trên ($9$) và cận dưới ($j=1$) xếp chồng theo trục dọc tự nhiên, công thức tự ngắt dòng xuống 2 hàng vừa vặn với trang giấy.
2. **Ảnh 2 (Lỗi khi xuống dòng không có dòng trống)**:
   - Người dùng xóa dòng trống, để `$$\sum...$$` ngay ở dòng kế tiếp sau chữ `a` (`a\n$$\sum...$$`).
   - Khối công thức không còn được nhận diện là khối độc lập (`MathBlock`) mà bị coi là công thức nội dòng (`MathInline`) nằm chung trong đoạn văn bản chứa chữ `a`.
   - Kết quả hiển thị bị hỏng hoàn toàn:
     - Công thức bị ép hiển thị ở chế độ nội dòng, dấu $\sum$ chuyển từ cận xếp chồng (stacked limits) sang cận bên (side limits).
     - Thuật toán căn chỉnh cận bên của toán tử lớn đặt chỉ số trên `9` và chỉ số dưới `j=1` tại cùng một hoành độ ngang mà không có đủ khoảng hở dọc, khiến nét mực chữ số `9` đè bẹp trực tiếp lên chữ `j=1`, tạo thành một vết mực lem luốc không thể đọc được.
     - Toàn bộ phương trình toán học rất dài bị co ép (thu nhỏ tỉ lệ xuống ~50%) để cố nhét vào một dòng kẻ giấy viết, làm chữ bị méo mó và mất tính thẩm mỹ của trang vở.
3. **Ảnh 3 (Phục hồi khi dòng trước là dòng trống)**:
   - Người dùng xóa ký tự `a`, để lại con trỏ tại dòng trống trước `$$\sum...$$`.
   - Hệ thống lập tức nhận diện lại khối công thức là `MathBlock` và hiển thị hoàn hảo như Ảnh 1.

### Nguyên nhân cốt lõi:
- **Cơ chế phân tách đoạn văn của chuẩn CommonMark**: Bộ phân tích cú pháp Markdown mặc định yêu cầu phải có một dòng trống (`\n\n`) để kết thúc một đoạn văn bản (`Paragraph`) trước khi bắt đầu một khối công thức độc lập (`MathBlock`). Nếu chỉ có một dấu xuống dòng đơn (`\n`), trình phân tích xem `$$\sum...$$` là công thức nội dòng hai dấu đô la (`math_inline_double`) thuộc cùng đoạn văn trước đó.
- **Thiếu bước tiền chuẩn hóa cách ly khối công thức**: Cú pháp toán học LaTeX chuẩn luôn coi `$$...$$` nằm trên dòng riêng là công thức display độc lập. Ứng dụng chưa có bước tự động chèn ranh giới dòng trống trước và sau các cặp `$$...$$` bắt đầu ở dòng mới trước khi chuyển vào bộ phân tích cú pháp.
- **Lỗi đè nét trong thuật toán bố cục cận bên (Side Limits Layout)**: Khi một toán tử lớn (như $\sum, \prod$) có cả cận trên và cận dưới ở chế độ nội dòng, hoành độ của cả hai chỉ số bị gán trùng nhau mà cao độ của chúng không được đẩy ra xa trục toán học để đảm bảo khoảng cách an toàn, dẫn đến tình trạng nét mực đè lên nhau.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tự động nhận diện khối công thức độc lập trên dòng mới mà không cần dòng trống (Priority: P1)

Là một người dùng soạn thảo tài liệu toán, tôi muốn khi gõ `$$...$$` ở một dòng mới ngay sau bất kỳ dòng văn bản nào, công thức phải luôn được nhận diện và hiển thị như một khối công thức toán độc lập (display math), để công thức được trình bày trang trọng, có cận xếp chồng trên/dưới và tự ngắt dòng đẹp mắt mà không bắt buộc tôi phải gõ thêm dòng trống thừa.

**Why this priority**: Đây là lỗi trực quan nghiêm trọng nhất thể hiện trong cả 3 ảnh chụp của người dùng. Người dùng soạn thảo tự nhiên thường nhấn Enter xuống dòng rồi gõ `$$...$$`, việc bắt buộc phải có dòng trống mới nhận diện đúng khối công thức là hành vi phản trực giác và gây ức chế lớn.

**Independent Test**:
- Nhập đoạn văn bản gồm một chữ hoặc câu ngắn, nhấn Enter xuống dòng (chỉ 1 dấu `\n`), gõ tiếp `$$\sum_{j=1}^9 x = 1$$`.
- Kiểm tra kết quả hiển thị trên trang giấy: công thức được hiển thị độc lập, dấu $\sum$ có cận `9` ở trên và `j=1` ở dưới dạng xếp chồng, không bị ép thành công thức nội dòng trên một hàng kẻ.

**Acceptance Scenarios**:
1. **Given** người dùng có một dòng văn bản bất kỳ (ví dụ `a` hoặc `Với mọi số nguyên k:`),  
   **When** người dùng xuống dòng đơn (`\n`) và nhập công thức bắt đầu bằng `$$` và kết thúc bằng `$$`,  
   **Then** hệ thống tự động nhận diện đó là khối công thức độc lập (`MathBlock`), hiển thị với cận trên/dưới dạng xếp chồng và tự động co giãn/ngắt dòng nhiều hàng nếu công thức dài.
2. **Given** văn bản chứa nhiều khối `$$...$$` liên tiếp trên các dòng riêng biệt không có dòng trống xen giữa,  
   **When** hệ thống phân tích và kết xuất tài liệu,  
   **Then** mỗi khối `$$...$$` đều được phân tích thành một khối công thức độc lập riêng biệt.

---

### User Story 2 - Ngăn ngừa đè nét giữa chỉ số trên và chỉ số dưới khi toán tử lớn hiển thị cận bên (Priority: P2)

Là một người dùng đọc hoặc viết công thức toán học có chứa toán tử lớn (như $\sum, \prod$), tôi muốn khi công thức nằm ở chế độ nội dòng (ví dụ `$ \sum_{j=1}^k x $`), chỉ số trên và chỉ số dưới phải có khoảng cách an toàn và không bao giờ bị đè nét mực lên nhau, để nội dung toán học luôn rõ ràng và dễ đọc.

**Why this priority**: Ngay cả trong trường hợp công thức thực sự là nội dòng (nằm trong cặp `$ $`), việc chỉ số trên `k` hoặc `9` đè trực tiếp lên chỉ số dưới `j=1` (như xuất hiện ở Ảnh 2) là lỗi bố cục toán học nghiêm trọng, vi phạm quy tắc thẩm mỹ và tính chính xác của tài liệu khoa học.

**Independent Test**:
- Nhập công thức nội dòng chứa toán tử lớn có cả cận trên và cận dưới: `$ \sum_{j=1}^9 P(D = j) $`.
- Kiểm tra các nét mực viết tay của chỉ số trên `9` và chỉ số dưới `j=1`: hai ký tự phải tách bạch rõ ràng về cao độ hoặc có độ lệch ngang hợp lý, khoảng cách giữa nét thấp nhất của chỉ số trên và nét cao nhất của chỉ số dưới phải lớn hơn ngưỡng tối thiểu xác định.

**Acceptance Scenarios**:
1. **Given** một công thức toán học có chứa toán tử lớn với cả chỉ số trên và chỉ số dưới ở chế độ cận bên (side limits),  
   **When** engine bố cục tính toán vị trí hiển thị của hai chỉ số,  
   **Then** chỉ số trên được nâng lên và chỉ số dưới được hạ xuống đủ để bảo đảm khoảng cách an toàn thẳng đứng giữa biên nét mực thực tế của hai chỉ số.
2. **Given** các ký tự viết tay có nét nhô cao hoặc nét kéo dài xuống dưới (ascender/descender),  
   **When** hiển thị đồng thời ở vị trí cận trên và cận dưới của toán tử,  
   **Then** hệ thống tự động điều chỉnh cao độ để nét nhô không chạm hoặc đè vào nét kéo dài.

---

### User Story 3 - Tự động tách biệt công thức display khi người dùng viết liền sau dấu hai chấm (Priority: P3)

Là một người dùng gõ văn bản theo thói quen tự nhiên như `ta có:$$công\_thức$$`, tôi muốn hệ thống nhận biết phần chữ dẫn nhập và khối công thức display để định dạng đúng ý định trình bày, tránh việc công thức bị dính liền vào đoạn văn bản trước đó.

**Why this priority**: Trong tiếng Việt và văn phong toán học, người dùng rất hay viết chữ dẫn nhập kết thúc bằng dấu hai chấm liền ngay trước dấu `$$` (như xuất hiện ở dòng đầu tiên trong ảnh người dùng: `ta có:$$F_D(k)...$$`).

**Independent Test**:
- Nhập dòng chữ `Ta có:$$E = mc^2$$`.
- Xác nhận phần chữ `Ta có:` hiển thị như văn bản và công thức `E = mc^2` được tách thành dòng công thức rõ ràng.

**Acceptance Scenarios**:
1. **Given** văn bản có dạng `[chữ dẫn nhập]:$$[công thức]$$`,  
   **When** hệ thống chuẩn hóa cú pháp trước khi phân tích,  
   **Then** hệ thống nhận diện `$$[công thức]$$` là công thức display và hiển thị tách bạch khỏi dòng dẫn nhập.

---

### Edge Cases

- **Bảng Markdown GFM (Table Protection)**: Các công thức toán nằm trong ô của bảng GFM (dòng bắt đầu và kết thúc bằng `|`) KHÔNG được tự ý chèn dòng trống `\n\n` để tránh phá hủy cấu trúc bảng; công thức trong ô bảng tiếp tục hiển thị dưới dạng nội dòng hoặc theo quy tắc bảng.
- **Thụt lề trong danh sách (List Item Indentation)**: Khi công thức `$$...$$` nằm trong một mục danh sách (bullet list hoặc ordered list có thụt lề), các dòng trống chèn thêm phải bảo toàn khoảng cách thụt lề đầu dòng tương ứng, ngăn khối công thức bị văng ra ngoài danh sách.
- **Dấu câu liền sau công thức (`$$...$$,` hoặc `$$...$$.`)**: Khi phương trình kết thúc bằng dấu phẩy, dấu chấm hoặc dấu chấm phẩy liền sau `$$`, hệ thống nhận diện đúng điểm kết thúc công thức và xử lý dấu câu thuộc luồng văn bản tiếp theo.
- **Dãy ba dấu đô la liên tiếp (`$$$`)**: Khi người dùng đóng khối display `$$` và mở ngay công thức inline `$`, hệ thống phân tách chính xác thành điểm đóng `$$` và điểm mở `$`.
- **Khối công thức chưa đóng (Unclosed `$$`)**: Khi người dùng đang soạn thảo dở dang chưa gõ dấu đóng `$$`, hệ thống xử lý an toàn dạng văn bản thường mà không bị lặp vô tận hay treo trình duyệt (chống ReDoS).
- **Công thức dạng khối nhiều dòng (Multi-line Block Math)**: Người dùng mở `$$` ở một dòng, viết nhiều dòng toán học bên trong, rồi đóng `$$` ở một dòng riêng biệt. Hệ thống phải nhận diện trọn vẹn toàn bộ khối từ điểm mở đến điểm đóng là một khối công thức độc lập.
- **Ký hiệu tiền tệ hoặc dấu đô la đơn lẻ**: Các chuỗi có chứa ký tự đô la đơn lẻ hoặc dấu đô la kèm số (như `100$ và 200$`) không được nhận nhầm là dấu mở/đóng khối công thức display `$$`.
- **Dấu gạch chéo thoát (`\$\$`)**: Các cặp `$$` có tiền tố thoát không được kích hoạt chuyển đổi thành khối công thức.
- **Công thức trống (`$$ $$`)**: Cặp `$$` rỗng hoặc chỉ chứa khoảng trắng phải được bỏ qua an toàn mà không làm gián đoạn việc phân tích văn bản xung quanh.
- **Toán tử lớn không có cận hoặc chỉ có 1 cận**: Toán tử chỉ có cận trên (`\sum^N`) hoặc chỉ có cận dưới (`\sum_i`) vẫn phải bố cục đúng vị trí mà không gây lệch trục hay tính sai kích thước vùng chứa.
- **Toán tử tích phân có độ lệch ngang (`\int`)**: Dấu tích phân đã có độ lệch ngang tự nhiên `sup_dx` sẽ không bị kéo giãn khoảng cách dọc thừa thãi, chỉ áp dụng cưỡng chế khoảng hở an toàn cho các toán tử có cận thẳng hàng dọc (`sup_dx == 0` như `\sum, \prod`).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI tự động nhận diện bất kỳ cặp dấu phân cách công thức toán display (`$$...$$` hoặc `\[...\]`) bắt đầu trên một dòng mới là khối công thức độc lập (`MathBlock`), ngay cả khi dòng phía trước là dòng văn bản thông thường không có dòng trống phân cách.
- **FR-002**: Hệ thống PHẢI đảm bảo các khối công thức độc lập (`MathBlock`) luôn được kết xuất ở chế độ display math (toán tử lớn như $\sum, \prod$ hiển thị cận xếp chồng trên/dưới theo trục dọc, công thức có khả năng tự động ngắt xuống nhiều dòng khi vượt quá bề rộng trang giấy).
- **FR-003**: Hệ thống PHẢI bảo đảm khoảng cách thẳng đứng an toàn (vertical clearance) giữa chỉ số trên và chỉ số dưới khi toán tử lớn thẳng hàng (`sup_dx == 0`) hiển thị ở chế độ cận bên (side limits), tuyệt đối không để nét mực của chỉ số trên đè lấn lên chỉ số dưới.
- **FR-004**: Hệ thống PHẢI bảo vệ cấu trúc bảng GFM và danh sách có thụt lề, không chèn dòng trống phá vỡ bảng và bảo toàn thụt lề danh sách.
- **FR-005**: Hệ thống PHẢI bảo toàn tính tương thích với các công thức nội dòng chuẩn đặt trong cặp dấu đô la đơn (`$...$` hoặc `\(...\)`).
- **FR-006**: Quá trình chuẩn hóa phân tách khối công thức PHẢI diễn ra tự động, tuyến tính và an toàn (chống ReDoS), không làm biến đổi dữ liệu gốc trong ô soạn thảo của người dùng.
- **FR-007**: Hệ thống PHẢI xử lý an toàn các trường hợp biên như công thức toán nhiều dòng, dấu đô la bị thoát, dấu câu sau `$$`, dãy `$$$` và các biểu thức toán học rỗng hoặc chưa đóng.

### Key Entities

- **Document Block**: Khối phần tử cấp cao nhất trong tài liệu (Đoạn văn, Tiêu đề, Khối danh sách, Bảng biểu, hoặc Khối công thức toán độc lập).
- **Math Block (`MathBlock`)**: Khối công thức toán học độc lập, được bố cục theo phong cách display math, hỗ trợ cận trên/dưới xếp chồng theo trục đứng và tự động chia dòng khi dài.
- **Math Inline (`MathInline`)**: Biểu thức toán học nằm bên trong luồng chữ của một đoạn văn, bố cục theo chiều ngang của dòng kẻ hiện tại.
- **Operator Limits (Cận toán tử)**: Vị trí đặt cận của toán tử toán học, gồm chế độ xếp chồng (stacked limits - trên đỉnh và dưới đáy toán tử) và chế độ cận bên (side limits - góc trên bên phải và góc dưới bên phải).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các công thức dạng `$$...$$` bắt đầu ở dòng mới liền kề sau văn bản (ví dụ `a\n$$...$$`) được hiển thị đúng dạng khối công thức display độc lập với cận trên/dưới xếp chồng dọc, xóa bỏ hoàn toàn hiện tượng bị co ép thành công thức nội dòng một hàng.
- **SC-002**: 0% trường hợp nét mực của chỉ số trên đè lấn lên chỉ số dưới khi hiển thị toán tử lớn có cả hai cận ở chế độ cận bên, duy trì khoảng cách thẳng đứng tối thiểu giữa hai vùng nét mực.
- **SC-003**: 100% các bài toán mẫu và tài liệu Markdown hiện có không bị hồi quy (regression) về cấu trúc khối hoặc kết xuất bảng biểu và danh sách.
- **SC-004**: Tốc độ xử lý phân tích cú pháp và bố cục văn bản không tăng quá 5% so với phiên bản hiện tại.

---

## Assumptions

- Người dùng khi chủ động xuống dòng và gõ cặp dấu `$$...$$` luôn có ý định tạo một khối công thức toán học nổi bật (display math) thay vì chèn công thức nội dòng.
- Cú pháp `$$` nằm hoàn toàn ở giữa một dòng chữ (ví dụ `Một đoạn chữ $$x=1$$ tiếp tục`) vẫn được xử lý linh hoạt theo quy tắc công thức hai dấu đô la nội dòng hoặc tách khối hợp lý.
- Toàn bộ các quy tắc kiểu chữ viết tay (handwritten strokes) và hạt giống biến thể (stable variants) tiếp tục được áp dụng nhất quán cho các khối công thức được nhận diện mới.
