# Feature Specification: Chuẩn hóa Hình học, Kích thước và Vị trí Quang học cho Hệ thống Dấu câu

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Created**: 2026-10-20  
**Status**: Ready for Planning  
**Input**: User description: "kiểm tra lại cách hoạt động của các dấu câu; điều chỉnh lại kích thước; vị trí sao cho phù hợp"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Chuẩn hóa chiều cao, vị trí dọc và khoảng cách cho nhóm dấu ngoặc bao quanh (Priority: P1)

Khi người dùng kết xuất các văn bản có dấu ngoặc như `(random_state=2026)` hoặc các biểu thức toán học như `P(X = k | X >= 1)`, `k!(e^\lambda - 1)`, `F_D(x)`, `\log_{10}(\lfloor x \rfloor + 1)`, các dấu ngoặc mở/đóng `(`, `)`, `[`, `]`, `{`, `}` phải có chiều cao cân xứng để bao trọn chữ hoa và chữ số bên trong, vươn đều qua đường cơ sở và tách biệt rõ ràng với các ký tự liền kề (đặc biệt là chữ số `1` có nét sổ thẳng đứng nằm sát mép phải).

**Why this priority**: Trong thực tế khi người dùng dạy mẫu dấu ngoặc trên bảng vẽ hoặc lưới tập viết, họ thường vẽ dấu ngoặc chỉ cao bằng chữ thường (`0.8 * xh` đến `1.0 * xh`) và dừng ở trên đường cơ sở. Khi ghép với chữ số (cao `1.20 * xh`), chỉ số dưới (`\log_{10}(...)`) hoặc chữ hoa, dấu ngoặc bị bé như dấu nháy lơ lửng; nghiêm trọng hơn, dấu đóng ngoặc `)` thấp hơn chữ số `1` và đặt sát mép phải của `1` làm hai đầu dấu `)` chập thẳng vào thân chữ số `1`, tạo thành nét chồng lấn gây hiểu nhầm nghiêm trọng.

**Independent Test**: Kết xuất các biểu thức `(random_state=2026)`, `P(X = k | X >= 1)`, `k!(e^\lambda - 1)` và `\log_{10}(\lfloor x \rfloor + 1)` với kho mẫu thực tế; đo khung bao hình học của dấu ngoặc và khoảng cách tới ký tự liền kề.

**Acceptance Scenarios**:

1. **Given** kho mẫu người dùng có mẫu dấu ngoặc `(`, `)` được vẽ thấp hoặc lệch đường cơ sở, **When** kết xuất trong văn bản thường `(random_state=2026)` hoặc công thức toán `P(X >= 1)`, **Then** dấu ngoặc được chuẩn hóa chiều cao đạt `1.45 * xh` (nằm trong dải `[1.35 * xh, 1.55 * xh]`), đỉnh vươn lên khoảng `-1.25 * xh` (cao hơn đỉnh chữ số `1.20 * xh`) và chân vươn xuống dưới đường cơ sở khoảng `+0.20 * xh`.
2. **Given** biểu thức toán học hoặc văn bản có chữ số `1` đứng ngay trước dấu đóng ngoặc `)` (như `X >= 1)`, `e^\lambda - 1)`, `\lfloor x \rfloor + 1)`), **When** kết xuất thành nét vẽ, **Then** khoảng hở ngang thực tế giữa nét mực cực phải của chữ số `1` và điểm bắt đầu của dấu `)` luôn đạt tối thiểu `max(0.18 * xh, 1.0 * độ_dày_nét_bút)`, tuyệt đối không chạm hoặc tạo vòng khép kín lên thân chữ số `1`.
3. **Given** biểu thức toán học có chỉ số dưới đứng trước dấu mở ngoặc như `\log_{10}(\lfloor x \rfloor + 1)`, **When** kết xuất thành nét vẽ, **Then** dấu mở ngoặc `(` có kích thước đầy đủ (`1.45 * xh`), cân đối với ký hiệu `\lfloor` bên trong và tách biệt rõ khỏi chỉ số dưới `10`.

---

### User Story 2 - Chuẩn hóa vị trí đường cơ sở và kích thước cho dấu phẩy, dấu chấm và dấu ba chấm (Priority: P1)

Khi người dùng kết xuất các biểu thức có dấu phẩy `,` (như `0,`, `1,`, `k = 1, 2, 3, ...`), dấu chấm câu `.` hoặc dấu ba chấm `...` / `\dots`, các dấu này phải bám đúng vị trí sinh học trên đường cơ sở thay vì bay lơ lửng giữa dòng chữ, đồng thời có kích thước gọn gàng, tự nhiên.

**Why this priority**: Trong kho mẫu thực tế của người dùng, dấu phẩy và dấu chấm thường bị viết cao hơn đường cơ sở (nằm lơ lửng ở độ cao `-0.5 * xh` đến `-0.15 * xh`) hoặc có kích thước quá lớn (`> 0.8 * xh`). Điều này làm cho dấu phẩy trong `0,`, `1,`, `k = 1, 2, 3, ...` trông như dấu nháy hoặc nét gạch giữa dòng. Ngoài ra, chuỗi dấu chấm liên tiếp `...` đang bị báo nhầm là thiếu mẫu dù kho đã có mẫu dấu chấm `.`.

**Independent Test**: Kết xuất các cụm `0,`, `1,`, `k = 1, 2, 3, ...` và câu kết thúc bằng dấu `.` hoặc `...` trên kho mẫu thực tế; kiểm tra tọa độ dọc (`min_y`, `max_y`), kích thước khung bao và danh sách báo thiếu mẫu.

**Acceptance Scenarios**:

1. **Given** mẫu dấu phẩy `,` trong kho bị vẽ lơ lửng phía trên đường cơ sở (`max_y < 0`) hoặc có chiều cao bất thường (`< 0.20 * xh` hoặc `> 0.50 * xh`), **When** kết xuất trong văn bản, số thập phân hoặc công thức toán (`0,`, `1,`, `1, 2, 3,`), **Then** dấu phẩy được chuẩn hóa chiều cao về dải `[0.22 * xh, 0.45 * xh]` (mục tiêu `0.38 * xh`) và neo vị trí dọc sao cho đỉnh dấu phẩy nằm ngay trên đường cơ sở (`min_y ≈ -0.14 * xh`) và đuôi móc xuống dưới đường cơ sở (`max_y ≈ +0.24 * xh`).
2. **Given** mẫu dấu chấm `.` trong kho bị vẽ lơ lửng trên cao (`max_y < 0`) hoặc quá to (`h > 0.22 * xh`), **When** kết xuất dấu chấm câu hoặc dấu ba chấm `...`, **Then** mỗi dấu chấm được thu gọn kích thước (`<= 0.18 * xh`) và đặt bám sát ngay trên đường cơ sở (`max_y ≈ 0.0`, `min_y ≈ -0.15 * xh`).
3. **Given** kho mẫu đã có mẫu dấu chấm `.`, **When** người dùng kết xuất chuỗi `...` (ba chấm), **Then** hệ thống ghép 3 dấu chấm liên tiếp trên đường cơ sở với khoảng cách đều nhau và không báo `...` vào danh sách thiếu mẫu.

---

### User Story 3 - Chuẩn hóa kích thước và vị trí cho dấu hai chấm, chấm phẩy, chấm than, chấm hỏi và dấu nháy (Priority: P2)

Khi người dùng kết xuất các câu có dấu hai chấm `:` (như `và xác suất lý thuyết:`), dấu chấm phẩy `;`, dấu chấm than `!`, dấu chấm hỏi `?`, hoặc dấu nháy đơn/kép `'`, `"`, các dấu câu này phải có tỷ lệ kích thước hài hòa với chữ viết liền kề và đặt đúng tầng đường kẻ (x-height, ascender hoặc baseline).

**Why this priority**: Trong ảnh chụp thực tế `và xác suất lý thuyết:`, dấu hai chấm `:` có chấm dưới bị tràn xuống dưới đường cơ sở và hai chấm lệch cỡ nhau; dấu `!` và `?` trong kho thực tế chỉ cao `~0.77 * xh` (thấp hơn cả chữ thường có nét cao và chữ số); dấu nháy `'`, `"` lại nằm tụt xuống vùng chữ thường thay vì ở vùng đỉnh chữ.

**Independent Test**: Kết xuất `thuyết:`, `ví dụ;`, `chú ý!`, `tại sao?`, `' mẫu '` và `" mẫu "` trên kho mẫu người dùng; xác minh biên dọc (`min_y`, `max_y`) và bề rộng của từng dấu.

**Acceptance Scenarios**:

1. **Given** mẫu dấu hai chấm `:` trong kho có vị trí lệch hoặc kích thước hai chấm không đều, **When** kết xuất `thuyết:`, **Then** dấu hai chấm nằm gọn trong tầng chữ thường (`min_y ≈ -0.75 * xh`, `max_y ≈ -0.05 * xh`), hai chấm cân đối, căn thẳng theo trục dọc và cách nét chữ trước tối thiểu `max(0.18 * xh, 0.85 * độ_dày_nét_bút)`.
2. **Given** mẫu dấu chấm phẩy `;` trong kho có phần phẩy bè quá rộng hoặc lệch tầng, **When** kết xuất, **Then** chấm trên nằm ở khoảng `-0.75 * xh`, phần phẩy dưới móc qua đường cơ sở tới khoảng `+0.24 * xh`, và tổng bề rộng không vượt quá `0.32 * xh`.
3. **Given** mẫu dấu chấm than `!` hoặc chấm hỏi `?` trong kho có chiều cao thấp hơn chữ số, **When** kết xuất trong văn bản hoặc toán học (`k!`), **Then** dấu `!` và `?` được chuẩn hóa chiều cao đạt `1.15 * xh` đến `1.20 * xh` và điểm chấm dưới cùng chạm đúng đường cơ sở (`max_y = 0.0`).
4. **Given** mẫu dấu nháy đơn `'` hoặc nháy kép `"` bị vẽ thấp ở giữa dòng, **When** kết xuất, **Then** dấu nháy được neo ở vùng đỉnh chữ (`min_y ≈ -1.20 * xh`, `max_y ≈ -0.85 * xh`).

---

### User Story 4 - Đồng bộ bản đóng gói ứng dụng Web và bảo toàn tương thích ngược (Priority: P1)

Khi cập nhật quy tắc chuẩn hóa hình học dấu câu trong bộ xử lý trung tâm, bản đóng gói ứng dụng Web chạy trên trình duyệt phải được xây dựng lại đồng bộ để người dùng nhận ngay kết quả mới, đồng thời toàn bộ các bài kiểm thử chuẩn Golden Master phải được bảo toàn 100%.

**Why this priority**: Nếu chỉ sửa mã nguồn mà không cập nhật gói phân phối chạy trong trình duyệt, người dùng cuối khi mở ứng dụng Web vẫn tải bản đóng gói cũ và tiếp tục gặp lỗi dính nét `1)` hay lệch dấu câu.

**Independent Test**: Xây dựng lại gói phân phối Web, kiểm tra gói mã nguồn bên trong và chạy toàn bộ bộ kiểm thử tự động cùng bộ kiểm thử Golden Master.

**Acceptance Scenarios**:

1. **Given** các cải tiến chuẩn hóa dấu câu đã hoàn tất, **When** đóng gói lại ứng dụng Web và chạy trên trình duyệt, **Then** bộ xử lý nền nạp đúng phiên bản mới nhất và hiển thị chính xác toàn bộ dấu câu trong cả chế độ xem trước lẫn tệp xuất ra.
2. **Given** bộ kiểm thử chuẩn Golden Master hiện hữu, **When** chạy kiểm thử đối chiếu mã băm SHA-256 trên cả môi trường gốc và môi trường trình duyệt, **Then** 100% các ca kiểm thử chuẩn khớp tuyệt đối mà không phát sinh sai lệch.

---

### Edge Cases

- **Mẫu dấu câu chỉ có 1 điểm hoặc suy biến (`chiều cao = 0` hoặc `chiều rộng = 0`)**: Hệ thống tự động mở rộng điểm suy biến thành nét chấm tròn nhỏ hợp lệ hoặc dùng hình học dự phòng chuẩn mà không gây lỗi chia cho 0.
- **Chuỗi nhiều dấu câu liên tiếp ở cuối từ (`...`, `?!`, `):`, `),`)**: Mỗi dấu câu trong chuỗi được chuẩn hóa độc lập theo đúng phân loại của nó, cách nhau một khoảng hở quang học dương (`>= 0.12 * xh`) và không bị báo thiếu mẫu nếu từng ký tự thành phần đã có mặt.
- **Dấu câu nằm trong ký hiệu toán học (`k!`, `f'(x)`, `P(A | B)`, `(a, b)`)**: Các dấu `!`, `'`, `(`, `)`, `,` khi đi qua bộ bố cục toán học đều được áp dụng cùng một quy chuẩn chuẩn hóa kích thước, vị trí dọc và khoảng hở quang học nhất quán với văn bản thường.
- **Mẫu dấu câu trong kho chuẩn đã nằm đúng vùng hợp lệ**: Nếu mẫu dấu chấm `.` hoặc dấu phẩy `,` đã nằm đúng trên đường cơ sở và trong ngưỡng kích thước chuẩn (như trong kho kiểm thử chuẩn), hệ thống giữ nguyên tọa độ gốc để đảm bảo tính tất định tuyệt đối.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống PHẢI phân loại và chuẩn hóa từng mẫu dấu câu theo nhóm hình học ngữ nghĩa (dấu chấm nền, dấu phẩy có đuôi, dấu hai tầng `:` / `;`, dấu ngoặc bao quanh, dấu cao toàn phần `!` / `?`, dấu nháy đỉnh `'`, `"`, và dấu gạch ngang `-`) dựa trên chiều cao chuẩn `x-height` (`xh`) và đường cơ sở (`baseline = 0.0`).
- **FR-002**: Hệ thống PHẢI chuẩn hóa các dấu ngoặc đơn/vuông/nhọn `(`, `)`, `[`, `]`, `{`, `}` sao cho chiều cao đạt `1.45 * xh` (nếu mẫu ngoài dải `[1.35 * xh, 1.55 * xh]`), đỉnh nằm tại `-1.25 * xh` và đáy nằm tại `+0.20 * xh` dưới đường cơ sở.
- **FR-003**: Hệ thống PHẢI chuẩn hóa dấu phẩy `,` khi mẫu nằm lệch khỏi đường cơ sở (`min_y < -0.25 * xh` hoặc `max_y < 0.0` hoặc `max_y > 0.45 * xh`) hoặc có chiều cao ngoài dải `[0.20 * xh, 0.50 * xh]`, đưa về chiều cao chuẩn `0.38 * xh` với đỉnh tại `-0.14 * xh` và đuôi tại `+0.24 * xh`.
- **FR-004**: Hệ thống PHẢI chuẩn hóa dấu chấm `.` khi mẫu nằm lệch khỏi đường cơ sở (`max_y < -0.05 * xh` hoặc `min_y > 0.05 * xh`) hoặc có kích thước quá lớn (`> 0.22 * xh`), đưa về kích thước nhỏ gọn (`~0.14 * xh`) và đặt ngay trên đường cơ sở (`max_y = 0.0`).
- **FR-005**: Hệ thống PHẢI chuẩn hóa dấu hai chấm `:` nằm gọn trong vùng `x-height` (`min_y ≈ -0.75 * xh`, `max_y ≈ -0.05 * xh`), căn chỉnh hai chấm thẳng trục dọc và có kích thước chấm cân đối (`<= 0.18 * xh` mỗi chấm).
- **FR-006**: Hệ thống PHẢI chuẩn hóa dấu chấm phẩy `;` với chấm trên tại `-0.75 * xh`, phần phẩy dưới kéo tới `+0.24 * xh` và giới hạn bề rộng tối đa `0.32 * xh`.
- **FR-007**: Hệ thống PHẢI chuẩn hóa dấu chấm than `!` và dấu chấm hỏi `?` đạt chiều cao `1.18 * xh` (nếu ngoài dải `[1.10 * xh, 1.25 * xh]`) và neo điểm đáy tại đường cơ sở (`max_y = 0.0`).
- **FR-008**: Hệ thống PHẢI chuẩn hóa dấu nháy đơn `'` và nháy kép `"` về vùng đỉnh chữ (`min_y ≈ -1.20 * xh`, `max_y ≈ -0.85 * xh`).
- **FR-009**: Trong bố cục toán học và văn bản, khoảng hở quang học giữa ký tự đứng trước (đặc biệt là chữ số `1`) và dấu đóng ngoặc `)` hoặc dấu phẩy `,` PHẢI đạt tối thiểu `max(0.18 * xh, 1.0 * độ_dày_nét_bút)`, đảm bảo không bao giờ chồng lấn nét mực.
- **FR-010**: Khi một chuỗi gồm nhiều dấu câu liên tiếp (như `...`) đã được kết xuất đầy đủ từ các dấu câu thành phần có trong kho, hệ thống KHÔNG ĐƯỢC đánh dấu chuỗi đó là thiếu mẫu.
- **FR-011**: Bản phân phối ứng dụng Web tĩnh PHẢI được đóng gói lại đồng bộ với mã nguồn mới nhất, đảm bảo phiên bản chạy trên trình duyệt phản ánh đầy đủ mọi quy tắc chuẩn hóa dấu câu.

### Key Entities

- **Nhóm Hình học Dấu câu (Punctuation Metric Profile)**: Tập hợp các thông số chuẩn hóa cho từng loại dấu câu, bao gồm: dải chiều cao hợp lệ (`min_h`, `max_h`, `target_h`), vị trí neo dọc so với đường cơ sở (`target_min_y`, `target_max_y`), giới hạn tỷ lệ bề rộng (`max_w`), và khoảng đệm ngang trái/phải (`lsb`, `rsb`).
- **Mẫu Dấu câu Đã Chuẩn hóa (Normalized Punctuation Glyph)**: Danh sách nét vẽ đã được dịch chuyển gốc ngang về `x = 0.0`, co giãn kích thước và căn chỉnh vị trí dọc theo đúng nhóm hình học ngữ nghĩa của ký tự dấu câu đó.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% các dấu ngoặc `(`, `)` trong văn bản `(random_state=2026)` và công thức toán `P(X = k | X >= 1)`, `\log_{10}(\lfloor x \rfloor + 1)`, `F_D(x)` có chiều cao lớn hơn chiều cao chữ số (`>= 1.35 * xh`), vươn lên trên `-1.20 * xh` và xuống dưới đường cơ sở `>= +0.15 * xh`.
- **SC-002**: Khoảng hở ngang thực tế giữa nét mực của chữ số `1` và dấu đóng ngoặc `)` trong `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)` luôn dương và đạt `>= 0.18 * xh` (tối thiểu `1.4pt`), loại bỏ hoàn toàn hiện tượng `1)` bị chập nét.
- **SC-003**: 100% các dấu phẩy `,` trong `0,`, `1,`, `k = 1, 2, 3, ...` có đỉnh nằm phía trên đường cơ sở (`min_y < 0`) và đuôi nằm phía dưới đường cơ sở (`max_y > 0`), không còn bất kỳ dấu phẩy nào bay lơ lửng giữa dòng chữ.
- **SC-004**: Dấu hai chấm `:` trong `thuyết:` có cả hai chấm nằm gọn trong dải `[-0.85 * xh, 0.0]`, thẳng trục dọc và cách chữ `t` liền trước tối thiểu `0.18 * xh`.
- **SC-005**: 100% (9/9) ca kiểm thử Golden Master đường thật và 100% (8/8) ca kiểm thử Golden Master trên môi trường WebAssembly giữ nguyên mã băm SHA-256 tuyệt đối.
- **SC-006**: Gói phân phối Web (`webapp/dist`) được cập nhật đồng bộ và vượt qua toàn bộ bài kiểm tra tính toàn vẹn đóng gói (`test_build_web`).

---

## Assumptions

- Kích thước chữ thường chuẩn (`x-height`, ký hiệu `xh`) của kho mẫu luôn dương (mặc định `7.94pt` nếu kho chưa xác định) và là đơn vị tham chiếu chuẩn cho mọi tỷ lệ hình học của dấu câu.
- Hệ trục tọa độ nét vẽ quy ước đường cơ sở (`baseline`) tại `y = 0.0`, chiều âm (`y < 0`) hướng lên đỉnh chữ và chiều dương (`y > 0`) hướng xuống chân chữ.
- Các mẫu dấu câu trong bộ kiểm thử chuẩn (`tiny_bank`) vốn đã có tọa độ gốc bắt đầu tại `y = 0.0` và nằm trong dải kích thước hợp lệ sẽ được bảo toàn nguyên trạng để giữ tính tương thích ngược tuyệt đối.
