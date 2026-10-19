# Feature Specification: Cải thiện trình bày chữ số và phân số tự nhiên (Natural Number & Fraction Typography)

**Feature Branch**: `045-natural-number-fraction-layout`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "cải thiện cách trình bày số; các số nhìn rất không tự nhiên; kể cả phân số cũng vậy; kích thước; vị trí rất không tự nhiên"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kích thước đồng nhất và vị trí chân chữ (baseline) tự nhiên cho các chữ số (Priority: P1)

Khi người dùng chuyển đổi văn bản hoặc công thức toán học có chứa các chữ số (`0`–`9`) sang trang viết tay, tất cả các chữ số phải có chiều cao hài hòa, đồng nhất với nhau và cùng đứng vững trên đường cơ sở (baseline) của dòng chữ, không bị hiện tượng chữ số to chữ số nhỏ thất thường hoặc chữ số bị bay lơ lửng / tụt sâu khỏi dòng kẻ.

**Why this priority**: Trong tài liệu hiện tại (như các số `0,39`, `0,19`, `0,0278`, `0,6944`, `16`, `25`, `36`), kích thước và vị trí theo chiều dọc giữa các chữ số rất thiếu tự nhiên (ví dụ chữ số `4`, `6`, `7`, `8` quá nhỏ và bị treo cao khỏi đường kẻ, trong khi chữ số `5`, `9`, `1` lại cao vượt trội hoặc lệch chân). Điều này làm toàn bộ biểu thức toán và con số trông giống các mảnh ghép lệch lạc thay vì chữ viết tay tự nhiên của một người.

**Independent Test**: Kết xuất một dãy đầy đủ các chữ số `0123456789` và các số thập phân thực tế (`0,0278`, `0,6944`, `16`, `25`, `36`, `P(2 ≤ X ≤ 5)`) trên trang giấy có dòng kẻ; đo chiều cao thực tế và vị trí điểm thấp nhất (baseline) của từng chữ số để xác nhận toàn bộ chữ số có chiều cao đồng đều và bám sát đường cơ sở.

**Acceptance Scenarios**:

1. **Given** một số có nhiều chữ số khác nhau (ví dụ `0,0278`, `0,6944`, `16`, `25`, `36`), **When** hệ thống tạo nét viết tay cho chuỗi số, **Then** chiều cao hiển thị của mọi chữ số từ `0` đến `9` nằm trong dải tỷ lệ đồng nhất (tương ứng chiều cao chữ số chuẩn khoảng `1.15` đến `1.30` lần chiều cao chữ thường `x-height`), không có chữ số nào bị lùn bất thường hoặc cao vọt so với các chữ số bên cạnh.
2. **Given** bất kỳ mẫu chữ số nào trong kho chữ (kể cả mẫu gốc bị lệch cao độ khi thu thập), **When** chữ số được đặt lên dòng văn bản hoặc trong công thức toán, **Then** điểm chân của chữ số được chuẩn hóa về đúng đường cơ sở (`baseline`) với độ lệch tối đa không quá `8%` chiều cao chữ thường, chấm dứt hiện tượng chữ số bay lơ lửng hoặc chìm xuống dưới dòng.
3. **Given** biểu thức kết hợp chữ cái, dấu ngoặc, toán tử và chữ số (ví dụ `P(X = 2)`, `F_X(5) - F_X(1)`, `1 ≤ x < 2`), **When** hiển thị trên cùng một dòng, **Then** các chữ số cân xứng về tỷ lệ kích thước và nằm cùng trục nhìn trực quan với chữ cái hoa (`P`, `F`, `X`), chữ thường (`x`) và các dấu quan hệ (`=`, `≤`, `<`).

---

### User Story 2 - Khoảng cách liên kết chặt chẽ, đều đặn trong số nhiều chữ số và số thập phân (Priority: P1)

Khi người dùng viết các số có nhiều chữ số (ví dụ `16`, `25`, `36`) hoặc các số thập phân có dấu phẩy/chấm (ví dụ `0,39`, `0,19`, `0,20`, `0,0278`, `0,1111`, `0,4444`), các chữ số trong cùng một con số phải đứng gần nhau với khoảng cách đều đặn, tạo thành một khối số liền mạch thay vì bị tách rời thành từng chữ số đơn lẻ.

**Why this priority**: Trong ảnh chụp thực tế, các số thập phân như `0,39` bị hiển thị thành `0,3 9`, `0,20` thành `0,2 0`, `0,0278` thành `0,0 2 7 8` và mẫu số `36` thành `3 6`. Nguyên nhân là khoảng cách giữa chữ số đầu sau dấu phẩy và các chữ số tiếp theo không đồng nhất, cộng với khoảng cách giữa hai chữ số liên tiếp đang quá rộng (gần bằng bề ngang của một chữ số) và cách phân tích dấu phẩy thập phân trong công thức toán chưa thống nhất. Lỗi này làm người đọc hiểu nhầm một số thập phân thành nhiều số rời rạc.

**Independent Test**: Kết xuất các biểu thức `0,39 - 0,19 = 0,20` và `0,0278` (dưới cả hai cách gõ thông dụng là `0,39` và `0{,}39` trong công thức toán cũng như văn bản thường); đo khoảng cách ngang giữa các chữ số liên tiếp và quanh dấu phẩy để xác nhận khoảng cách đồng đều, chặt chẽ.

**Acceptance Scenarios**:

1. **Given** một số có nhiều chữ số liên tiếp (như `36`, `0278`, `1111`, `4444`, `6944`), **When** hệ thống ghép nét các chữ số, **Then** khoảng hở quang học giữa hai chữ số liền kề bất kỳ được giữ ổn định trong khoảng hẹp tự nhiên (`10%` đến `20%` chiều cao chữ thường), tuyệt đối không xuất hiện khoảng trống rộng bằng nửa thân chữ số.
2. **Given** một số thập phân sử dụng dấu phẩy hoặc dấu chấm (ví dụ `0,39`, `0,19`, `0,20`, `0,0278`), **When** người dùng nhập trực tiếp trong công thức toán (dù viết `0,39` hay `0{,}39`) hoặc trong văn bản, **Then** phần nguyên, dấu phẩy thập phân và tất cả các chữ số phần thập phân được trình bày thành một khối số thống nhất; khoảng cách từ dấu phẩy đến chữ số đầu tiên sau dấu phẩy và khoảng cách giữa các chữ số thập phân tiếp theo hoàn toàn hài hòa, không xảy ra hiện tượng chữ số đầu dính vào dấu phẩy còn các chữ số sau bị đẩy văng ra xa (`0,3 9`).
3. **Given** một số thập phân có dấu phẩy kết thúc câu hoặc ngăn cách mệnh đề đi kèm ở cuối (ví dụ `0,0278,   1 ≤ x < 2`), **When** hệ thống phân tích và bố cục công thức, **Then** dấu phẩy nằm giữa các chữ số được nhận diện là dấu thập phân (khoảng cách hẹp), còn dấu phẩy đứng cuối số được nhận diện là dấu câu ngăn cách (có khoảng nghỉ hợp lý phía sau).

---

### User Story 3 - Trình bày phân số cân đối về kích thước, khoảng cách tử/mẫu và căn chỉnh dòng (Priority: P1)

Khi người dùng tạo các biểu thức chứa phân số (ví dụ `\frac{1}{36}`, `\frac{4}{36}`, `\frac{9}{36}`, `\frac{16}{36}`, `\frac{25}{36}`), phân số phải có tỷ lệ kích thước vừa vặn, tử số và mẫu số nằm gần thanh gạch ngang một cách tự nhiên, thanh gạch phân số có độ dài vừa đủ ôm lấy tử/mẫu, và toàn bộ phân số căn chỉnh hài hòa với dấu `=`, `≈` cũng như dòng kẻ vở.

**Why this priority**: Trong ảnh chụp hiện tại, phân số nhìn rất mất tự nhiên: tử số (`1`, `4`, `9`, `16`, `25`) bị đẩy lên quá cao so với gạch phân số, mẫu số (`36`) bị đẩy xuống quá thấp tạo ra hai khoảng trống thừa lớn ở cả trên và dưới gạch ngang; thanh gạch phân số lại vươn dài quá mức sang hai bên; và khi đặt nhiều phân số trong hệ biểu thức từng khúc (`F_M(x)`), tổng chiều cao mỗi phân số bị đội lên quá lớn làm các dòng công thức bị giãn toạc và lệch khỏi dòng kẻ ngang của trang vở.

**Independent Test**: Kết xuất biểu thức hàm phân phối từng khúc `F_M(x)` chứa 5 phân số `\frac{1}{36}` đến `\frac{25}{36}` kèm giá trị xấp xỉ `≈ 0,0278` trên trang giấy kẻ ngang; kiểm tra khoảng hở từ đáy tử số đến gạch phân số, từ gạch phân số đến đỉnh mẫu số, độ vươn ngang của gạch phân số và sự thẳng hàng với toán tử `≈` / `=`.

**Acceptance Scenarios**:

1. **Given** một phân số số học hoặc đại số (ví dụ `\frac{1}{36}`, `\frac{16}{36}`), **When** hệ thống bố cục phân số, **Then** khoảng cách từ điểm thấp nhất thực tế của tử số đến thanh gạch ngang và từ thanh gạch ngang đến điểm cao nhất thực tế của mẫu số phải cân đối, nhỏ gọn (tương đương `15%` đến `25%` chiều cao chữ thường), loại bỏ hoàn toàn khoảng đệm ảo làm tử số và mẫu số bị tách rời xa khỏi gạch phân số.
2. **Given** thanh gạch ngang của phân số, **When** tính toán chiều dài gạch phân số dựa trên tử số và mẫu số, **Then** phần nhô ra (overhang) ở mỗi đầu trái/phải của gạch phân số chỉ vượt nhẹ so với phần tử rộng hơn (`15%` đến `25%` chiều cao chữ thường mỗi bên), không vươn dài thừa thãi.
3. **Given** phân số đi kèm dấu `=`, `≈` và các số thập phân trên cùng một hàng hoặc trong hệ phương trình / hàm từng khúc (`cases`), **When** hiển thị trên trang, **Then** thanh gạch phân số nằm đúng trục toán học (math axis) đi qua tâm của dấu `=` và `≈`, tỷ lệ thu phóng chữ số trong phân số hài hòa với chữ số bên ngoài, và chiều cao tổng thể của mỗi hàng phân số được giữ gọn gàng để nhịp dòng trên trang vở tự nhiên.

---

### Edge Cases

- **Mẫu chữ số trong kho dữ liệu người dùng có biên tọa độ dị biệt**: Khi người dùng tự dạy chữ số mới hoặc dùng kho chữ cũ có mẫu chữ số vẽ quá nhỏ, quá to, hoặc vẽ lệch hẳn lên trên/xuống dưới đường kẻ ô mẫu, hệ thống phải tự động chuẩn hóa vị trí chân chữ (baseline) và quy chuẩn chiều cao chữ số về khung tỷ lệ chuẩn trước khi ghép thành số hoặc đưa vào công thức toán.
- **Phân biệt dấu phẩy thập phân và dấu phẩy liệt kê trong toán học**: Trong chuỗi như `0,39` (không có khoảng trắng sau dấu phẩy và hai bên đều là chữ số), dấu phẩy đóng vai trò ngăn cách thập phân nên gắn kết chặt; nhưng trong danh sách hoặc khoảng như `(0, 1)`, `x_{i,j}`, hoặc dấu phẩy kết thúc dòng điều kiện `0,0278,`, dấu phẩy đóng vai trò dấu ngăn cách nên vẫn giữ khoảng hở chuẩn sau dấu câu.
- **Phân số lồng nhau hoặc phân số có chỉ số trên/dưới**: Khi tử số hoặc mẫu số có mũ/chỉ số dưới (ví dụ `\frac{x^2}{2}`, `\frac{1}{n_1}`) hoặc phân số lồng nhau, khoảng cách từ tử/mẫu đến gạch phân số phải tính theo biên hình học thực tế của các nét vẽ để không bao giờ xảy ra hiện tượng nét chữ chạm hoặc cắt vào thanh gạch phân số.
- **Số âm, số phần trăm và số trong ngoặc / chỉ số dưới**: Các biểu thức như `-0,39`, `25%`, `F_X(1)`, `P(2 ≤ X ≤ 5)` phải áp dụng cùng một quy chuẩn kích thước, baseline và khoảng cách chữ số để không có sự lệch pha giữa số đứng riêng, số trong ngoặc và số ở chỉ số.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI chuẩn hóa vị trí theo chiều dọc (baseline alignment) của tất cả các mẫu chữ số (`0`–`9`) sao cho chân chữ số luôn bám sát đường cơ sở (`y = 0`), loại bỏ độ trôi cao độ (vertical drift) giữa các chữ số trong cùng một con số và giữa chữ số với chữ cái trên dòng.
- **FR-002**: Hệ thống PHẢI chuẩn hóa tỷ lệ chiều cao của các chữ số (`0`–`9`) về một dải chiều cao mục tiêu đồng nhất tỷ lệ với chiều cao chữ thường (`x-height`), đảm bảo các chữ số khi đặt cạnh nhau (như `16`, `25`, `36`, `0278`, `6944`) có độ lớn đồng đều và cân đối với chữ cái in hoa / chữ thường.
- **FR-003**: Hệ thống PHẢI chuẩn hóa biên ngang (left/right optical bounds) của từng mẫu chữ số và áp dụng khoảng cách giữa hai chữ số liên tiếp (`inter-digit gap`) chặt chẽ, ổn định trong khoảng `0.10 * xh` đến `0.18 * xh`, loại bỏ việc lấy các giá trị khoảng cách quá rộng làm các chữ số bị tách rời.
- **FR-004**: Khi kết xuất số thập phân có dấu phẩy hoặc dấu chấm (ví dụ `0,39`, `0,0278`), hệ thống PHẢI đảm bảo khoảng cách từ chữ số phần nguyên đến dấu thập phân, từ dấu thập phân đến chữ số thập phân đầu tiên, và giữa các chữ số thập phân tiếp theo hoàn toàn cân đối, liền mạch, không làm chữ số đầu tiên dính vào dấu phẩy còn các chữ số sau bị đẩy xa.
- **FR-005**: Trong công thức toán học, hệ thống PHẢI nhận diện tự nhiên các số thập phân viết bằng dấu phẩy theo thói quen tiếng Việt (ví dụ `0,39`, `0,0278` bên cạnh cách viết `0{,}39`) để kết xuất thành một số thập phân liền mạch duy nhất, đồng thời vẫn bảo toàn đúng khoảng cách cho dấu phẩy ngăn cách ở cuối số (ví dụ `0,0278,`) hoặc dấu phẩy liệt kê có khoảng trắng (ví dụ `(0, 1)`).
- **FR-006**: Khi đo đạc chiều cao (ascent và descent) của chữ số và chuỗi số trong công thức toán, hệ thống PHẢI tính toán dựa trên biên hình học thực tế của các nét chữ số đã chuẩn hóa (không gán phần chân `descent` ảo cho các chữ số không có nét kéo xuống dưới đường cơ sở), giúp việc đặt số vào tử số, mẫu số, căn thức và chỉ số chính xác tuyệt đối.
- **FR-007**: Khi bố cục phân số, hệ thống PHẢI đặt tử số và mẫu số cách thanh gạch ngang một khoảng hở quang học thực tế nhỏ gọn và đối xứng (tương đương `0.15 * xh` đến `0.25 * xh` tính từ biên nét thực của tử số và mẫu số đến gạch ngang), đồng thời đảm bảo không bao giờ chạm nét.
- **FR-008**: Độ dài thanh gạch ngang của phân số PHẢI vừa vặn với chiều rộng của phần tử lớn hơn giữa tử số và mẫu số, với phần vươn ra hai đầu (bar overhang) gọn gàng trong khoảng `0.15 * xh` đến `0.25 * xh` mỗi bên (thay vì vươn rộng quá mức).
- **FR-009**: Trong các cấu trúc nhiều hàng như hệ phương trình hoặc hàm cho bởi nhiều công thức (`cases`), khoảng cách giữa các hàng chứa phân số và tỷ lệ kích thước phân số PHẢI được điều chỉnh gọn gàng để công thức cân đối, dễ đọc và hài hòa với khoảng cách dòng kẻ của trang giấy.

### Key Entities

- **NormalizedDigitGlyph**: Mẫu chữ số đã được chuẩn hóa đồng thời về biên ngang (bắt đầu từ gốc `x = 0`), vị trí chân chữ trên đường cơ sở (`baseline y = 0`) và tỷ lệ chiều cao đồng nhất theo chiều cao chữ chuẩn của kho mẫu.
- **DecimalNumberToken**: Chuỗi số nguyên hoặc số thập phân (bao gồm dấu chấm/phẩy thập phân nội bộ) được xử lý như một đơn vị số học thống nhất với khoảng cách giữa các chữ số và dấu ngăn cách thập phân đồng đều.
- **CompactFractionLayout**: Cấu trúc bố cục phân số xác định vị trí tử số, mẫu số và thanh gạch ngang dựa trên biên hình học thực tế của tử/mẫu quanh trục toán học (`math axis`), đảm bảo khoảng hở đối xứng và độ vươn gạch phân số tối ưu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các chữ số `0`–`9` khi kết xuất trong cùng một cấp cỡ chữ có chiều cao hiển thị đồng nhất (độ lệch chiều cao giữa chữ số cao nhất và thấp nhất không vượt quá `12%`) và điểm chân chữ nằm sát đường cơ sở với sai số không quá `0.08 * xh`.
- **SC-002**: 100% các chuỗi chữ số liên tiếp và số thập phân (như `0,39`, `0,19`, `0,20`, `0,0278`, `16`, `25`, `36`) có khoảng cách giữa hai chữ số liền kề nằm trong dải `0.10 * xh` đến `0.20 * xh`, và chênh lệch giữa khoảng cách sau dấu phẩy thập phân với khoảng cách giữa các chữ số liền kề không vượt quá `0.08 * xh`.
- **SC-003**: Trong mọi phân số số học (như `\frac{1}{36}` đến `\frac{25}{36}`), khoảng hở thực tế từ đáy tử số đến gạch phân số và từ gạch phân số đến đỉnh mẫu số nằm trong khoảng `0.15 * xh` đến `0.25 * xh` (giảm tối thiểu `40%` khoảng trống thừa so với bố cục cũ), và tổng chiều cao của phân số đơn giản giảm tối thiểu `25%` để vừa vặn tự nhiên trên dòng giấy kẻ ngang.
- **SC-004**: Độ vươn ngang mỗi bên của thanh gạch phân số nằm trong khoảng `0.15 * xh` đến `0.25 * xh`, giúp phân số gọn gàng và cân đối trực quan với các toán tử `=`, `≈` đứng liền kề.
- **SC-005**: 100% các bài kiểm thử tự động hiện có và các bài kiểm thử mới cho bố cục số, số thập phân và phân số đều vượt qua thành công mà không gây lỗi hồi quy cho văn bản tiếng Việt hay bảng biểu.

## Assumptions

- Chữ số viết tay chuẩn trong toán học và văn bản học thuật thuộc kiểu chữ số đồng cao (lining figures): cả 10 chữ số `0`–`9` đều đứng trên đường cơ sở (`baseline`) và có cùng chiều cao mục tiêu (khoảng `1.20 * xh`, thấp hơn nhẹ hoặc ngang với chữ cái in hoa và cao hơn chữ cái thường không có nét sổ lên).
- Trong tài liệu tiếng Việt, dấu phẩy viết liền giữa hai chữ số (như `0,39`, `0,0278` không có khoảng trắng theo sau) mặc định mang ý nghĩa là dấu phẩy thập phân. Nếu người dùng viết dấu phẩy có khoảng trắng theo sau (như `0, 1` hoặc `1, 2, 3`) hoặc dấu phẩy đứng sau chữ số nhưng tiếp theo không phải chữ số (như `0,0278,`), dấu phẩy đó là dấu câu ngăn cách thông thường.
- Việc chuẩn hóa chiều cao và chân chữ của các mẫu chữ số được thực hiện tự động khi kết xuất (hoặc khi nạp mẫu chữ số) mà không đòi hỏi người dùng phải vẽ lại kho mẫu chữ tay hiện có.
