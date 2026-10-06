# Nghiên cứu kỹ thuật: Hình học xem trước giấy và bộ điều khiển Zoom

**Feature**: `specs/023-write-preview-paper-geometry`
**Date**: 2026-10-06

## 1. Nghiên cứu hình học hiển thị trang giấy (Paper Geometry & DPI)

### Bối cảnh & Vấn đề phát hiện
- `.paper-frame` trong `webapp/css/style.css` hiện không thiết lập `width` rõ ràng.
- `renderPageSvgElement` trong `webapp/js/paper.js` gán `width="100%"`, `height="100%"`, và `viewBox="0 0 {ptWidth} {ptHeight}"`.
- Khi đặt trong flex container (`#preview-stage` / `.preview-pages`) với layout co giãn tự động theo nội dung con, trình duyệt coi SVG như một inline/block replaced element với tỉ lệ co mặc định ~300 px chiều rộng, khiến văn bản A4 (595,28 pt) chỉ rộng ~300 px (~0,5 px/pt), làm chữ bị thu nhỏ li ti, không thể quan sát bình thường.

### Quyết định kỹ thuật
- **Công thức quy đổi chuẩn**: 
  $$px = pt \times \frac{96}{72} \times zoom$$
  Hệ số quy đổi cơ sở: $1\text{ pt} = \frac{96}{72}\text{ px} = \frac{4}{3}\text{ px} \approx 1,33333\text{ px}$.
  - A4 (595,28 pt × 841,89 pt): 100% zoom tương đương $793,71\text{ px} \times 1122,52\text{ px}$.
  - A5 (419,53 pt × 595,28 pt): 100% zoom tương đương $559,37\text{ px} \times 793,71\text{ px}$.
  - Letter (612 pt × 792 pt): 100% zoom tương đương $816\text{ px} \times 1056\text{ px}$.
- Áp dụng `width` và `height` dạng pixel tường minh lên `.paper-frame` (hoặc SVG bên trong) dựa theo công thức trên.
- Duy trì thuộc tính `viewBox="0 0 {ptWidth} {ptHeight}"` của SVG để toàn bộ hệ tọa độ điểm nét vẽ nội bộ giữ nguyên không thay đổi, chất lượng vector hiển thị sắc nét ở mọi độ phân giải.

### Giải pháp thay thế đã xem xét
- *Dùng `transform: scale(...)`*: Đã bị từ chối vì `transform` chỉ thay đổi ma trận hiển thị mà không cập nhật bounding box layout thực tế của phần tử trong dòng chảy tài liệu, dẫn đến thanh cuộn `#preview-stage` không tính đúng kích thước cuộn khi zoom to (bị tràn ra ngoài màn hình không cuộn tới được) hoặc để lại khoảng trống trắng thừa khi zoom nhỏ.

---

## 2. Nghiên cứu cơ chế điều khiển Zoom & Tự động thích ứng (Fit Mode)

### Bối cảnh & Yêu cầu
- Cần cung cấp bộ điều khiển Zoom gọn gàng gồm nút giảm (`−`), nút tăng (`+`), nút `Fit`, và nhãn hiển thị phần trăm.
- Dải zoom cho phép: 50% đến 300%.
- Khi ở chế độ `Fit`: Chiều rộng trang giấy co giãn vừa bề rộng khung xem trước `#preview-stage` có trừ khoảng đệm (padding: 32px - 48px). Khi thay đổi kích thước cửa sổ trình duyệt (viewport resize), nếu đang ở chế độ Fit thì phải tự động tính toán lại tỷ lệ zoom.

### Quyết định kỹ thuật
- **Cấu trúc điều khiển UI**:
  - Nút giảm: `<button id="btn-zoom-out" class="btn btn-sm btn-icon" title="Thu nhỏ (zoom out)">−</button>`
  - Nhãn hiển thị: `<span id="zoom-percent-display" class="zoom-display">100%</span>`
  - Nút tăng: `<button id="btn-zoom-in" class="btn btn-sm btn-icon" title="Phóng to (zoom in)">+</button>`
  - Nút Fit: `<button id="btn-zoom-fit" class="btn btn-sm" title="Vừa chiều rộng khung">Vừa khung</button>`
  - Thay thế hoặc chuẩn hóa `<select id="select-zoom">` bằng bộ nút này để trải nghiệm nhanh chóng, tiện dụng hơn.
- **Tính toán chế độ Fit**:
  $$zoom_{\text{fit}} = \frac{\text{stageClientWidth} - \text{padding}}{\text{pagePtWidth} \times \frac{96}{72}}$$
  Giới hạn $zoom_{\text{fit}}$ trong khoảng $[0.3, 3.0]$ để bảo đảm an toàn.
- **Lắng nghe thay đổi kích thước**:
  Sử dụng `ResizeObserver` trên phần tử `#preview-stage` (hoặc `window.addEventListener('resize')`) để kích hoạt lại phép tính Fit khi người dùng thay đổi kích thước cửa sổ hoặc toggle thanh bên điều khiển.

---

## 3. Nghiên cứu chuẩn hóa kiểu giấy nền Xournal++

### Bối cảnh & Khảo sát mã nguồn Xournal++
- Kiểm tra mã nguồn Xournal++ v1.2.6 (`src/view/LinedBackgroundView.cpp` và `src/view/RuledBackgroundView.cpp`):
  - `LinedBackgroundView`: Vẽ các đường kẻ ngang có khoảng cách `spacing` đồng thời vẽ **đường lề dọc màu đỏ** (margin line) ở lề trái trang.
  - `RuledBackgroundView`: **Chỉ vẽ các đường kẻ ngang**, hoàn toàn không có đường lề dọc.
- Hiện trạng trong `webapp/js/paper.js`:
  - `renderPageSvgElement` (dòng 210-216) và `renderPageSvgString` (dòng 281-301) đang kiểm tra `if (style === "ruled")` để vẽ lề đỏ. Đây là lỗi hoán đổi ngược so với Xournal++.
  - Giao diện `webapp/index.html` đang đặt nhãn: `ruled` là "Dòng kẻ (có lề)", `lined` là "Dòng kẻ (không lề)".

### Quyết định kỹ thuật
- Sửa lại điều kiện trong `webapp/js/paper.js`:
  - `style === "lined"`: Vẽ dòng kẻ ngang và vẽ đường lề dọc màu đỏ (`#ff8a80` tại hoành độ `margin`).
  - `style === "ruled"`: Chỉ vẽ dòng kẻ ngang màu xám nhạt (`#cfd8dc`), không vẽ đường lề dọc.
- Cập nhật danh sách tùy chọn `#opt-background` trong `webapp/index.html`:
  - `<option value="lined" selected>Dòng kẻ & lề</option>`
  - `<option value="ruled">Chỉ dòng kẻ</option>`
  - `<option value="plain">Trắng trơn</option>`
  - `<option value="graph">Ô ly vuông</option>`
  - `<option value="dotted">Chấm bi</option>`
- Đặt giá trị mặc định của `writeOptions.background` trong `webapp/js/write.js` thành `"lined"`.

---

## 4. Cập nhật tài liệu cấu hình cổng máy chủ thử nghiệm

- `scripts/serve.mjs` khởi động HTTP server tại cổng `8000`.
- Cập nhật dòng lệnh và liên kết trong `README.md` từ `http://localhost:8080` về `http://localhost:8000`.
