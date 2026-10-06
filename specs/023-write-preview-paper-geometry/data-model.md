# Mô hình dữ liệu & Thực thể: Hình học xem trước giấy

**Feature**: `specs/023-write-preview-paper-geometry`
**Date**: 2026-10-06

## 1. Thực thể hình học trang giấy (`PaperGeometry`)

Mô tả các thông số hình học để render trang giấy từ kích thước điểm in ấn (PostScript pt) sang pixel giao diện màn hình CSS (px).

### Các trường dữ liệu:

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `paperSize` | `string` | Tên khổ giấy: `"a4"`, `"a5"`, `"letter"` |
| `orientation` | `string` | Chiều giấy: `"portrait"` (dọc), `"landscape"` (ngang) |
| `widthPt` | `number` | Chiều rộng chuẩn tính theo đơn vị pt (A4 dọc: 595.28 pt) |
| `heightPt` | `number` | Chiều cao chuẩn tính theo đơn vị pt (A4 dọc: 841.89 pt) |
| `zoom` | `number` | Hệ số thu phóng hiện tại (ví dụ: 1.0 cho 100%, 0.75 cho 75%) |
| `layoutWidthPx` | `number` | Chiều rộng layout CSS: `Math.round(widthPt * (96 / 72) * zoom)` |
| `layoutHeightPx` | `number` | Chiều cao layout CSS: `Math.round(heightPt * (96 / 72) * zoom)` |

### Quy tắc bất biến:
- Tỷ lệ khung hình: $\frac{\text{layoutWidthPx}}{\text{layoutHeightPx}} \approx \frac{\text{widthPt}}{\text{heightPt}}$ với sai số làm tròn số nguyên không quá 1 pixel.
- Phạm vi zoom: $0.5 \le zoom \le 3.0$ (tương ứng 50% đến 300%).

---

## 2. Trạng thái điều khiển thu phóng (`ZoomControlState`)

Quản lý trạng thái tương tác thu phóng của khung xem trước trang giấy trên web client.

### Các trường dữ liệu:

| Thuộc tính | Kiểu dữ liệu | Giá trị mặc định | Mô tả |
| :--- | :--- | :--- | :--- |
| `currentZoom` | `number` | `1.0` (hoặc fit) | Tỷ lệ phóng to/thu nhỏ hiện tại |
| `isFit` | `boolean` | `false` | Cờ đánh dấu chế độ tự động tính theo bề rộng khung |
| `minZoom` | `number` | `0.5` | Giới hạn zoom nhỏ nhất (50%) |
| `maxZoom` | `number` | `3.0` | Giới hạn zoom lớn nhất (300%) |
| `zoomStep` | `number` | `0.1` | Bước nhảy khi nhấn nút `+` hoặc `−` (10%) |

### Chuyển đổi trạng thái:
- **Nhấn nút `+`**: `currentZoom = Math.min(maxZoom, Math.round((currentZoom + zoomStep) * 10) / 10)`, `isFit = false`.
- **Nhấn nút `−`**: `currentZoom = Math.max(minZoom, Math.round((currentZoom - zoomStep) * 10) / 10)`, `isFit = false`.
- **Nhấn nút `Fit`**: `isFit = true`, tính toán `currentZoom = computeFitZoom()`.
- **Sự kiện viewport resize**: Nếu `isFit === true`, tự động tính toán lại `currentZoom = computeFitZoom()`.

---

## 3. Kiểu mẫu nền trang giấy (`PaperBackgroundStyle`)

Định nghĩa kiểu nền giấy cho việc vẽ SVG và xuất tệp tin `.xopp`.

### Các giá trị hợp lệ:
- `"lined"`: Dòng kẻ ngang cách đều + vạch kẻ lề dọc màu đỏ bên trái (chuẩn Xournal++ LinedBackground).
- `"ruled"`: Chỉ các dòng kẻ ngang song song, không có vạch lề dọc (chuẩn Xournal++ RuledBackground).
- `"plain"`: Nền trắng trơn không có dòng kẻ.
- `"graph"`: Lưới ô ly vuông.
- `"dotted"`: Lưới chấm bi.
