# Research & Technical Decisions: Bank Stroke Width Consistency

## Decision 1: Phương pháp chuẩn hoá tỷ lệ hiển thị nét trong SVG Thumbnail (`createSvgFromStrokes`)

- **Context**: 
  - Trong `webapp/js/bank.js`, hàm `createSvgFromStrokes(strokes, width = 100, height = 50)` đang tính `minX, maxX, minY, maxY` dựa thuần tuý trên nét vẽ. Với chữ số `2` hoặc ký tự ngắn, `strokeW ~ 3pt` và `strokeH ~ 8pt`.
  - Thẻ SVG có kích thước cố định hoặc `max-width: 100%; max-height: 100%` trong thẻ `.sample-item-thumb` (cao 60px) và `.bank-card-thumb` (cao 56px).
  - Thuộc tính `stroke-width="1.6"` được vẽ trong không gian `viewBox`, khi `viewBox` bị zoom lên 4-6 lần để lấp đầy thẻ, `stroke-width` thực tế trên màn hình trở thành `8px - 10px` (quá đậm).

- **Alternatives Considered**:
  1. *Giải pháp A: Dùng `vector-effect="non-scaling-stroke"` và `stroke-width="2px"`*:
     - Ưu điểm: Bất kể `viewBox` zoom bao nhiêu, độ dày nét trên màn hình luôn cố định ở giá trị pixel chỉ định (ví dụ `1.8px`).
     - Nhược điểm: Với các từ dài (ví dụ "nghiên cứu" rộng 60pt), từ đó bị co nhỏ lại nhưng nét vẽ vẫn giữ 2px thì các nét có thể dính vào nhau; tuy nhiên với thumbnail xem trước, nét sắc nét không biến dạng là tối ưu nhất.
  2. *Giải pháp B: Cố định chiều cao tối thiểu của `viewBox` theo đơn vị dòng kẻ chuẩn (`minH ~ 24pt - 28pt` hoặc dựa trên `xh * 3`)*:
     - Ưu điểm: Đảm bảo ký tự chữ số `2` cao 8pt sẽ nằm lọt trong một khung dòng kẻ có chiều cao thực tế tương đương ô lưới/dòng kẻ, không bị phóng to vượt cỡ. Tỷ lệ nét so với chiều cao chữ luôn đồng nhất.
  3. *Giải pháp Kết hợp (Recommended)*:
     - **Chuẩn hoá ViewBox với khung tham chiếu chiều cao tối thiểu (`minVbH = 26pt`)**:
       - Với hệ thống chữ viết tay: `xh ~ 7.94pt`, chiều cao dòng chuẩn `line ~ 24pt`.
       - Nếu bounding box của ký tự có chiều cao `strokeH < 22pt`, đặt chiều cao khung `vbH = Math.max(strokeH + pad*2, 26)`. Chiều rộng khung `vbW = Math.max(strokeW + pad*2, vbH * (width / height))`.
       - Căn chỉnh tâm toạ độ ký tự vào chính giữa `viewBox`.
     - **Thêm `vector-effect="non-scaling-stroke"` và điều chỉnh `stroke-width="1.8"`**:
       - Đảm bảo nét bút hiển thị trên màn hình luôn giữ đúng độ mảnh tự nhiên (~1.8px), giống hệt như khi người dùng quan sát trên Canvas hoặc trang giấy viết.

- **Decision**: Áp dụng Giải pháp Kết hợp:
  1. Tính toán `viewBox` với khung tham chiếu tối thiểu (`minVbH = 24pt`), căn giữa ký tự theo trục ngang và trục dọc.
  2. Thêm `vector-effect="non-scaling-stroke"` vào thẻ `<polyline>`.
  3. Đặt `stroke-width="1.8"` và hỗ trợ truyền `penWidth` linh hoạt nếu cần.

---

## Decision 2: Khả năng hiển thị đường dóng mờ tham chiếu (Baseline guide) trong xem chi tiết mẫu

- **Context**: 
  - Trong tab Dạy chữ (`TeachCanvas`), người dùng có đường kẻ chân chữ (baseline) và đường mốc `x-height` để biết vị trí tương đối của chữ.
  - Khi xem lại trong modal chi tiết mẫu của Kho mẫu, người dùng nhìn vào chữ số `2` không có đường dóng, chỉ thấy một hình ảnh trơ trọi.
- **Decision**: 
  - Giữ thumbnail dạng lưới danh sách sạch sẽ (không nền), nhưng trong khung SVG của modal chi tiết, hiển thị đường kẻ mốc chân chữ mờ mảnh (`stroke="#e2e8f0" stroke-dasharray="2,2"`) nếu có toạ độ baseline (y = 0 trong Bank units). 
  - Điều này giúp người dùng nhận ra vị trí đặt chân chữ chính xác của mẫu mình vừa dạy.

---

## Decision 3: Tương thích ngược và tính độc lập của Lõi Python

- **Decision**:
  - Toàn bộ cơ chế điều chỉnh này nằm trọn vẹn trong lớp hiển thị Frontend tĩnh (`webapp/js/bank.js` và CSS).
  - Không thay đổi bất kỳ trường dữ liệu nào của cấu trúc JSON kho mẫu (`BankSchema` v4) hay toạ độ `s`, `w` trong Python lõi.
  - Bảo toàn 100% hash của 8 ca kiểm thử Golden Master.
