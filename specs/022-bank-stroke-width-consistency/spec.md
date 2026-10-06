# Feature Specification: Đồng bộ độ dày nét hiển thị giữa Dạy chữ và Kho mẫu (Bank Stroke Width Consistency)

**Feature Branch**: `022-bank-stroke-width-consistency`

**Created**: 2026-10-06

**Status**: Ready for Planning

**Input**: User description: "rõ ràng nó khi thêm mẫu thì nét chữ mảnh nhưng khi xem lại trong kho thì nét lại thành đậm; hãy kiểm tra và sửa"

---

## 1. Problem Statement & Root Cause Context

Khi người dùng thực hiện dạy chữ trong tab **Dạy chữ (Teach)**:
- Người dùng chọn tuỳ chọn vẽ nét bút với các kích thước trực quan (ví dụ: "Nét mảnh" `1.5px`, "Nét vừa" `2.5px`, "Nét đậm" `4.0px`).
- Vùng vẽ Canvas hiển thị nét chữ đúng theo độ dày này trên toạ độ logic chuẩn (760 x 230 px). Khi lưu, toạ độ nét được chuẩn hoá sang đơn vị kho mẫu (Bank Units, xh ~ 7.94pt) và lưu dưới dạng toạ độ `s` phẳng.
- Tuy nhiên, khi người dùng mở tab **Kho mẫu (Bank)** hoặc xem chi tiết biến thể nét:
  - Hàm tạo hình thu nhỏ SVG (`createSvgFromStrokes`) dựng thẻ `<svg>` với `viewBox` bao khít lấy bounding box của chính nét vẽ đó (chỉ thêm `pad = 4px` đơn vị kho).
  - Thuộc tính `stroke-width="1.6"` được cố định trong không gian toạ độ cục bộ của `viewBox`.
  - Đối với các ký tự hoặc chữ số có kích thước bounding box nhỏ (ví dụ chữ số `2` có bề ngang chỉ ~3 pt, bề cao ~8 pt), việc SVG bị co giãn (scale-up) phóng đại để lấp đầy thẻ card preview (rộng 140px, cao 56px) khiến độ dày nét thực tế trên màn hình bị phóng to gấp 6 đến 10 lần (trông như `stroke-width: 15px - 20px` siêu đậm, mập mạp và biến dạng tỷ lệ).
  - Ngược lại, nét chữ vẽ trong tab Dạy lại được vẽ trên không gian chuẩn rộng rãi với nét thanh mảnh tự nhiên.
  - Hơn nữa, độ dày nét mặc định được chọn khi dạy chữ không được lưu/phản ánh đồng bộ vào `pen.width` hoặc thông số mẫu, dẫn đến cảm giác thiếu nhất quán thị giác nghiêm trọng giữa lúc nhập liệu và lúc duyệt kho.

---

## 2. User Scenarios & Testing *(mandatory)*

### User Story 1 - Hiển thị nét mẫu trung thực và đúng tỷ lệ trong Kho mẫu (Priority: P1) 🎯 MVP

Là một người dùng dạy chữ viết tay tiếng Việt, tôi muốn các hình thu nhỏ (thumbnail) và thẻ chi tiết mẫu nét trong tab Kho mẫu phản ánh trung thực độ thanh mảnh / độ đậm tương quan với kích thước khi tôi viết trên Canvas, để chữ không bị phóng đại thành nét siêu đậm bất thường.

**Why this priority**: Đây là lỗi trực quan cốt lõi mà người dùng phản ánh qua ảnh chụp: chữ số "2" viết nét mảnh nhưng trong modal chi tiết mẫu lại biến thành một khối nét đậm đặc, mất thẩm mỹ và gây hoang mang về chất lượng lưu trữ nét.

**Independent Test**:
- Dạy chữ số "2" ở chế độ "Nét mảnh".
- Mở tab Kho mẫu và bấm vào chữ số "2" để mở modal chi tiết biến thể mẫu (`#modal-label-detail`).
- Khẳng định nét hiển thị trong thẻ mẫu `#1` giữ được độ thanh mảnh tự nhiên, không bị phình to cục bộ do co giãn tự do bounding box.

**Acceptance Scenarios**:
1. **Given** Người dùng vừa dạy một chữ/ký tự có kích thước bounding box hẹp (ví dụ: chữ số `2`, dấu câu, chữ `i`, `l`),
   **When** Người dùng xem thẻ mẫu trong tab Kho mẫu và modal chi tiết nhãn,
   **Then** SVG preview phải duy trì tỷ lệ nét vẽ (stroke width) cân xứng với chiều cao chuẩn (x-height / baseline chuẩn) thay vì phóng to nét vẽ theo bounding box hẹp.
2. **Given** Một mẫu chữ trong kho mẫu có toạ độ nét vẽ,
   **When** Hàm sinh SVG thumbnail dựng hình,
   **Then** `viewBox` của SVG phải được tính toán dựa trên không gian tỷ lệ cố định hoặc có cơ chế `vector-effect="non-scaling-stroke"` / chuẩn hoá tỷ lệ `stroke-width` theo hệ số phóng đại để độ dày nét rendered trên màn hình luôn đồng nhất và tương ứng với nét bút đã chọn (~1.5pt - 2.5pt).

---

### User Story 2 - Lưu và bảo toàn tuỳ chọn độ dày nét bút của phiên dạy chữ (Priority: P2)

Là một người dùng tuỳ biến nét viết, tôi muốn khi tôi chọn "Nét mảnh", "Nét vừa" hoặc "Nét đậm" trong tab Dạy chữ, thông số độ dày nét này được ghi nhận hoặc đồng bộ với cấu hình bút (`pen.width`) trong kho mẫu, để các trang viết và các bản xem trước tái hiện đúng phong cách nét tôi mong muốn.

**Why this priority**: Giúp trải nghiệm viết và dạy chữ liền mạch, đảm bảo nhất quán giữa nét vẽ lúc nhập liệu, lưu trữ và kết xuất ra trang giấy `.xopp` / `.svg`.

**Independent Test**:
- Chọn "Nét mảnh" (1.5), dạy mẫu chữ.
- Kiểm tra cấu hình nét và độ dày nét kết xuất khi xem lại hoặc kết xuất trang viết.

**Acceptance Scenarios**:
1. **Given** Người dùng chuyển đổi bộ chọn độ dày nét trên thanh công cụ Dạy chữ (`#select-teach-pen-width`),
   **When** Lưu mẫu chữ mới vào kho,
   **Then** Giá trị độ dày nét tương ứng được áp dụng nhất quán trong phiên làm việc.

---

### Edge Cases

- **Ký tự siêu hẹp (Dấu câu, dấu phẩy, dấu chấm, dấu thanh rời)**: Bounding box có chiều ngang cực nhỏ (ví dụ `< 1 pt`). Nếu scale-to-fit không có khung chuẩn, dấu chấm/dấu phẩy sẽ biến thành một hình vuông/tròn khổng lồ chiếm trọn khung preview. Cần áp dụng chiều cao tối thiểu hoặc khung dóng chuẩn (dựa trên baseline và x-height) khi dựng SVG.
- **Từ rất dài (Cụm từ viết liền)**: Bounding box có chiều rộng lớn (`> 50 pt`). Tỷ lệ co nhỏ không được làm nét bị mờ tịt (hairline) biến mất.
- **Mẫu nét không có toạ độ (rỗng)**: Hệ thống phải xử lý fallback an toàn không gây lỗi script.

---

## 3. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST chuẩn hoá cách dựng hình SVG thumbnail của các mẫu nét (`createSvgFromStrokes`) trong tab Kho mẫu sao cho độ dày nét trên màn hình phản ánh đúng độ dày vật lý tự nhiên, không bị phóng đại quá mức đối với các ký tự hẹp.
- **FR-002**: Hệ thống MUST sử dụng chiều cao khung tham chiếu chuẩn (dựa trên tỷ lệ chiều cao chữ thường `xh` hoặc khung lưới chuẩn ~24-30 pt) khi xác định `viewBox` cho các ký tự đơn và chữ số ngắn, tránh việc chỉ bao bọc đơn thuần `[minX, minY, maxX, maxY]` của các nét nhỏ.
- **FR-003**: Hệ thống MUST hỗ trợ thuộc tính `vector-effect="non-scaling-stroke"` hoặc tính toán động `stroke-width` tỷ lệ nghịch với tỷ lệ scale của `viewBox`, đảm bảo độ dày nét thực tế trên giao diện luôn giữ ở mức thanh mảnh dễ đọc (~1.5px đến 2.5px màn hình).
- **FR-004**: Đảm bảo sự đồng nhất hiển thị giữa:
  1. Nét vẽ trực tiếp trên Canvas (`TeachCanvas`).
  2. Nét thu nhỏ trên thẻ danh sách kho (`bank-card-thumb`).
  3. Nét trên thẻ danh sách biến thể trong modal chi tiết (`sample-item-thumb`).
  4. Nét kết xuất trên trang giấy xem trước (`#paper-svg-wrapper`).
- **FR-005**: Mọi thay đổi MUST không làm thay đổi cấu trúc dữ liệu lưu trữ cốt lõi trong `Bank` và không làm vỡ các bài kiểm thử hồi quy Golden Master (8/8 ca giữ nguyên 100%).

---

## 4. Key Entities & Data Model

- **Bank Sample**:
  - `s`: Danh sách nét vẽ phẳng theo đơn vị kho mẫu `[x0, y0, x1, y1, ...]`.
  - `w`: Độ rộng chữ số/ký tự (pt).
- **SVG Thumbnail Renderer (`createSvgFromStrokes`)**:
  - Đầu vào: `strokes` (danh sách nét), `width`, `height`.
  - Thuộc tính dựng: `viewBox`, `stroke-width`, `vector-effect="non-scaling-stroke"`.
  - Đầu ra: Chuỗi HTML `<svg>...</svg>` hiển thị cân đối trong khung card.

---

## 5. Success Criteria *(mandatory)*

- **SC-001**: Hình ảnh chữ số `2` và các ký tự hẹp trong modal chi tiết mẫu nét hiển thị với độ dày nét thanh mảnh, sắc nét, tương đương độ dày nét vẽ ban đầu trên Canvas, không còn bị biến dạng thành nét đậm đen mập mạp.
- **SC-002**: Tỷ lệ giữa chiều cao thân chữ và độ dày nét bút được bảo toàn trực quan trên tất cả các kích thước thumbnail (thẻ kho 110x50px và thẻ biến thể 140x56px).
- **SC-003**: 100% các bộ kiểm thử tự động hiện có (1.119 tests CPython, 8 Golden Master Pyodide, 8 kịch bản Playwright E2E) tiếp tục pass không có lỗi hồi quy.
- **SC-004**: Thêm kịch bản kiểm thử E2E / Unit test xác minh thuộc tính hiển thị nét của SVG thumbnail không bị phình to bất thường.
