# Feature Specification: Punctuation Spacing, Natural Alignment & Digit Spacing

**Feature Branch**: `specs/030-punctuation-spacing-alignment`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "tôi gặp lỗi; các ký tự dấu câu cứ bị dính vào từ thay vì cách 1 đoạn như trong ảnh; ngoài ra còn gặp lỗi; các chữ số thì nhiều khi lại cách nhau quá xa; hãy tìm cách sửa"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Khoảng cách tự nhiên cho dấu câu đi liền sau từ (Priority: P1)

Khi người dùng xuất tài liệu viết tay chứa các từ có dấu câu đi kèm ở đuôi (ví dụ: `đổi:`, `này,`, `sau.`, `gì?`), dấu câu (dấu hai chấm `:`, dấu phẩy `,`, dấu chấm `.`, chấm hỏi `?`, chấm than `!`, chấm phẩy `;`) phải được đặt cách nét chữ cuối cùng một khoảng đệm trực quan (visual clearance / typographic spacing) hợp lý, không được chạm nét, đè nét hoặc dính sát vào thân chữ cái trước đó.

**Why this priority**: Lỗi dính nét dấu câu (đặc biệt là dấu `:` chạm sát vào chữ cái như `đổi:`) khiến văn bản viết tay trở nên phi tự nhiên, khó đọc và làm giảm tính thẩm mỹ của trang viết tay. Đây là lỗi hiển thị trực tiếp ảnh hưởng đến người dùng cuối trong mọi tài liệu Markdown, Word hoặc văn bản thuần.

**Independent Test**: Có thể kiểm tra độc lập bằng cách render các từ kèm dấu câu đuôi (`đổi:`, `nhé,`, `xong.`, `sao?`) và xác minh khoảng cách vật lý/quang học giữa nét ngoài cùng của từ với nét bắt đầu của dấu câu đạt ngưỡng tối thiểu và không có hiện tượng giao cắt nét (zero stroke collision).

**Acceptance Scenarios**:

1. **Given** một từ tiếng Việt kết thúc bằng dấu hai chấm (ví dụ: `đổi:`), **When** hệ thống kết xuất token thành các nét viết tay, **Then** dấu hai chấm bắt đầu ở tọa độ ngang cách nét bên phải ngoài cùng của từ một khoảng trống tối thiểu tỷ lệ thuận với chiều cao chữ (`xh`), không chạm nét hay dính vào chữ cái cuối.
2. **Given** một từ kết thúc bằng dấu câu bất kỳ trong bộ dấu câu đuôi (`.`, `,`, `:`, `;`, `!`, `?`, `…`), **When** hệ thống bố cục token, **Then** dấu câu được căn lề tự nhiên với bearing trái (left side bearing / clearance) độc lập với tọa độ gốc tuyệt đối trong kho mẫu.
3. **Given** một token chỉ gồm duy nhất một dấu câu (ví dụ dấu ngoặc đơn đóng `)` hoặc dấu hai chấm `:` đứng riêng), **When** hệ thống tính toán độ rộng token, **Then** độ rộng được tính từ bounding box thực tế của nét cộng thêm lề phải, loại bỏ khoảng trắng trống bên trái không mong muốn.

---

### User Story 2 - Khoảng cách chữ số hài hòa, tự nhiên và chống rời rạc (Priority: P1)

Khi kết xuất các chuỗi số (ví dụ: số nguyên `181`, số thập phân `184{,}05`, `0,12`, các bảng số liệu `0 0 1 4 4`, `5 1 9 8 4`), các chữ số liền nhau phải có khoảng cách liên kết chặt chẽ (tight typographic spacing), không bị rời rạc hoặc dãn cách xa như các từ riêng biệt.

**Why this priority**: Trong bảng biểu, công thức toán và bài giải (như trong ảnh minh họa: `3 8,9 8`, `0,0 1 4 4`, `17 4 2 4`), các chữ số bị bung khoảng cách ngẫu nhiên quá rộng (do dữ liệu `dgaps` trong kho mẫu bị lệch lớn từ 0.8 đến 11.5 hoặc cơ chế clamp quá lỏng) khiến người đọc nhầm lẫn các chữ số trong cùng một số thành các số rời rạc hoặc từ tách biệt, làm mất tính chính xác và thẩm mỹ khoa học.

**Independent Test**: Render các chuỗi chữ số đa ký tự (`181`, `195`, `184,05`, `02704`) trong cả khối văn bản số thuần và công thức toán MathLayout/bảng biểu, đo đạc khoảng cách giữa các chữ số liền kề đảm bảo nằm trong dải quang học tự nhiên (`0.06 * xh` đến `0.25 * xh`), không có khoảng hở vượt quá `0.35 * xh`.

**Acceptance Scenarios**:

1. **Given** một chuỗi số gồm nhiều chữ số liên tiếp (ví dụ `181`, `195`, `945`), **When** hệ thống kết xuất số trong văn bản hoặc công thức toán, **Then** khoảng cách ngang giữa 2 chữ số liên tiếp duy trì tỷ lệ tự nhiên, đều đặn, không bị giãn cách quá xa.
2. **Given** số thập phân có dấu phẩy hoặc chấm (ví dụ `0,12`, `184,05`), **When** kết xuất chuỗi số, **Then** dấu phẩy/chấm nằm cân đối ngay sau chữ số trước và chữ số sau bắt đầu với khoảng hở vừa vặn, không tạo khoảng trống bất thường trước hoặc sau dấu ngăn cách.
3. **Given** kho mẫu có trường `dgaps` chứa các giá trị ngoại lai (outliers > `5.0` hoặc không tương thích với `xh`), **When** hệ thống chọn khoảng cách ghép số, **Then** hệ thống tự động lọc (filter) hoặc chuẩn hóa theo tỷ lệ `xh` để khoảng cách luôn trong giới hạn thẩm mỹ an toàn.

---

### User Story 3 - Khoảng cách và căn lề cho dấu câu mở đầu và bao quanh (Priority: P2)

Khi văn bản chứa các dấu câu mở đầu như dấu mở ngoặc đơn `(`, mở ngoặc vuông `[`, mở ngoặc nhọn `{`, dấu mở ngoặc kép `"`/`“` hoặc các cấu trúc bao bọc (ví dụ `(bằng ...)`), dấu mở đầu phải giữ khoảng cách tự nhiên với ký tự đứng sau, không bị dính nét vào phần thân từ và không tạo khoảng hở bất thường.

**Why this priority**: Tài liệu học tập, công thức và đề thi thường xuyên chứa các cấu trúc mở ngoặc chú thích hoặc đơn vị như `(bằng $184{,}05\text{ g}$)`. Dấu mở ngoặc cần có khoảng cách hài hòa với chữ cái tiếp theo để đảm bảo tính mỹ thuật đồng đều.

**Independent Test**: Render các token có tiền tố dấu mở như `(bằng`, `[1]`, `“Hà` và xác nhận khoảng cách từ nét của dấu mở đến nét đầu tiên của từ tuân thủ khoảng cách typographic tự nhiên.

**Acceptance Scenarios**:

1. **Given** token có dấu mở ngoặc đứng trước từ (ví dụ `(bằng`), **When** hệ thống ghép nét, **Then** nét của từ bắt đầu sau nét của dấu mở ngoặc với khoảng đệm phù hợp.
2. **Given** dấu đóng ngoặc đứng riêng liền kề một biểu thức toán inline (ví dụ `(bằng $184{,}05\text{ g}$)`), **When** bố cục inline dòng, **Then** dấu đóng ngoặc không bị thụt lề hay tạo khoảng trống thừa bất thường so với biểu thức trước đó.

---

### Edge Cases

- **Mẫu dấu câu trong kho có tọa độ x gốc lệch lớn**: Một số mẫu dấu câu trong kho người dùng lưu tọa độ x bắt đầu từ giá trị lớn (ví dụ `min_x = 4.0` hoặc `14.75` trong khung ô cũ). Hệ thống phải chuẩn hóa bounding box của dấu câu về gốc 0 (zero-baseline normalize) trước khi cộng offset vào đuôi từ, tránh làm dấu câu bị xê dịch bất thường hoặc thụt lùi đè lên từ.
- **Nhiều dấu câu dồn dập (punctuation cluster)**: Các cụm như `...`, `?!`, `"):`, `):` phải được tính toán khoảng cách tiến (advance) nối tiếp giữa từng dấu câu, không để dấu câu sau đè lên dấu câu trước.
- **Ký tự cuối của từ có nét vẩy dài về bên phải**: Khi chữ cái cuối có nét lượn sang phải (như chữ `a`, `u`, `n`), khoảng đệm dấu câu phải tính từ tọa độ x lớn nhất thực tế của nét chữ (`max_x`) thay vì dựa thuần túy vào metric lý thuyết `w`.
- **Chữ số có hình dáng mở hoặc nét móc rộng (ví dụ số 1, 4, 7)**: Khi ghép các chữ số có bounding box hẹp hoặc rộng bất đối xứng, khoảng hở phải căn cứ theo đường bao và chiều rộng thực tế của mẫu số để tránh bị giãn cách cục bộ.
- **Khoảng cách số trong MathLayoutEngine**: Khi kết xuất công thức toán LaTeX chứa số thập phân như `$184{,}05$`, `TextNode(kind='num')` gọi qua `Writer.number()` phải áp dụng chung quy chuẩn khoảng cách số đã cải tiến.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI đảm bảo khoảng cách giữa nét kết thúc của từ (hoặc số) và nét bắt đầu của dấu câu đi liền sau (trail punctuation: `:`, `,`, `.`, `;`, `!`, `?`) có khoảng hở quang học tối thiểu không nhỏ hơn độ rộng nét bút (`pen_w`) và tỷ lệ với chiều cao chữ `xh`.
- **FR-002**: Hệ thống PHẢI chuẩn hóa vị trí x của mẫu dấu câu (`bank.punct`) sao cho nét ngoài cùng bên trái của dấu câu bắt đầu từ mốc offset mong muốn, triệt tiêu độ trôi tọa độ cục bộ (local origin offset) do dữ liệu kho mẫu cũ để lại.
- **FR-003**: Hệ thống PHẢI căn cứ vào tọa độ x cực đại thực tế (`max_x`) của các nét đã vẽ trong từ/số khi gắn dấu câu đuôi, tránh trường hợp thuộc tính `w` của từ nhỏ hơn biên nét thực tế gây va chạm nét.
- **FR-004**: Đối với dấu câu mở đầu (`lead punctuation`), hệ thống PHẢI chuẩn hóa gốc tọa độ và duy trì khoảng cách đệm dương (positive clearance) trước khi vẽ phần thân từ.
- **FR-005**: Hệ thống PHẢI chuẩn hóa và siết chặt khoảng cách giữa các chữ số liên tiếp (`dgaps` / digit kerning), đảm bảo khoảng hở giữa 2 chữ số liền kề trong cùng một số nằm trong giới hạn quang học chặt chẽ tỷ lệ theo `xh` (mặc định tương đương `0.08 * xh` đến `0.22 * xh`), loại bỏ triệt để các khoảng cách ngoại lai gây rời rạc chữ số.
- **FR-006**: Hệ thống PHẢI đảm bảo khoảng cách chữ số được áp dụng đồng bộ trên cả luồng văn bản thông thường (`Writer.number`), luồng công thức toán (`MathLayoutEngine` với `TextNode`) và bảng biểu (`TableLayoutEngine`).
- **FR-007**: Hệ thống PHẢI duy trì khả năng tương thích 100% với toàn bộ định dạng đầu vào (Markdown, Word DOCX, TXT thuần) và không làm suy giảm hiệu năng xử lý văn bản hay phá vỡ các luồng ghép ký tự hiện có.

### Key Entities

- **PunctuationGlyph**: Biểu diễn nét vẽ của dấu câu, bao gồm bounding box cục bộ chuẩn hóa (`min_x`, `max_x`, `min_y`, `max_y`), độ rộng thực tế (`effective_w`) và khoảng lề an toàn (`side_bearings`).
- **DigitSpacingModel**: Mô hình tính toán bước tiến (advance) giữa các chữ số liền kề, chuẩn hóa theo `xh` và loại bỏ độ biến thiên khoảng trống quá đà.
- **TokenAssembly**: Cấu trúc kết quả ghép nối giữa tiền tố (`lead`), thân (`core`) và hậu tố (`trail`), trong đó mỗi thành phần được định vị bằng offset cộng dồn có kiểm tra khoảng hở nét.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các trường hợp từ kết hợp dấu câu đuôi (tiêu biểu như `đổi:`, `gì?`, `này,`) không có bất kỳ điểm chạm hoặc chồng chéo nét nào (zero stroke intersection / collision).
- **SC-002**: Khoảng cách hở giữa nét cuối của chữ và nét đầu của dấu câu đuôi đạt khoảng thẩm mỹ tối thiểu từ `0.15 * xh` đến `0.35 * xh`, tạo cảm giác viết tay tự nhiên như hình mẫu tham chiếu.
- **SC-003**: 100% các chuỗi chữ số liên tiếp (trong cả văn bản thường, công thức toán và bảng) có khoảng cách giữa các chữ số liền kề không vượt quá `0.25 * xh`, ngăn chặn hoàn toàn hiện tượng số bị đứt rời thành từng ký tự riêng biệt.
- **SC-004**: Toàn bộ bộ kiểm thử tự động của hệ thống (unit tests, integration tests) tiếp tục vượt qua thành công với tỷ lệ 100% pass, không gây hồi quy (no regression).

## Assumptions

- Kho mẫu chữ viết tay có thể chứa các mẫu dấu câu và chữ số được vẽ tự do ở các vị trí khác nhau trong ô lưới gốc, do đó thuật toán bố cục cần tự động bù trừ tọa độ x để đảm bảo kết quả đồng nhất.
- Danh sách `dgaps` trong các kho mẫu người dùng có thể chứa các giá trị đo đạc cũ từ các phiên bản trước quá lớn (ví dụ > `5.0`); thuật toán cần có cơ chế lọc an toàn (sanitization / scaling factor) tự động dựa trên `xh` hiện tại của kho mẫu.
- Quy tắc khoảng cách typographic tiếng Việt tuân thủ tiêu chuẩn: dấu câu đuôi (`:`, `,`, `.`, `;`, `!`, `?`) gắn liền sau từ với khoảng hở nhỏ tự nhiên; dấu mở ngoặc cách từ phía sau một khoảng hở nhỏ; các chữ số trong cùng một số đi liền nhau với độ nén tự nhiên.
