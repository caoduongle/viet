# Hợp đồng giao diện & DOM: Khung xem trước giấy và bộ điều khiển Zoom

**Feature**: `specs/023-write-preview-paper-geometry`
**Date**: 2026-10-06

## 1. Cấu trúc DOM điều khiển Zoom trên thanh công cụ xem trước

Phần tử điều khiển zoom được bố trí tại thanh công cụ xem trước của tab "Viết chữ" (`.preview-controls` hoặc tương đương):

```html
<div class="zoom-controls">
  <button id="btn-zoom-out" class="btn btn-sm btn-icon" title="Thu nhỏ (zoom out)" aria-label="Thu nhỏ">
    <span aria-hidden="true">−</span>
  </button>
  <span id="zoom-percent-display" class="zoom-display" aria-live="polite">100%</span>
  <button id="btn-zoom-in" class="btn btn-sm btn-icon" title="Phóng to (zoom in)" aria-label="Phóng to">
    <span aria-hidden="true">+</span>
  </button>
  <button id="btn-zoom-fit" class="btn btn-sm" title="Vừa chiều rộng khung">Vừa khung</button>
</div>
```

---

## 2. Cấu trúc DOM và thuộc tính hiển thị trang giấy

Vùng chứa trang giấy `#preview-stage` và phần tử giấy `.paper-frame`:

```html
<div id="preview-stage" class="preview-stage">
  <div id="paper-svg-wrapper" class="preview-pages">
    <div class="paper-frame" style="width: 794px; height: 1123px;">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 595.28 841.89"
        width="100%"
        height="100%"
        style="display: block;"
      >
        <!-- Background lines & handwritten path strokes -->
      </svg>
    </div>
  </div>
</div>
```

### Các ràng buộc kiểu dáng (CSS):
1. `#preview-stage`:
   - `overflow: auto;` (cho phép xuất hiện thanh cuộn tự nhiên theo cả chiều ngang và dọc khi nội dung vượt quá khung nhìn).
   - `display: flex; justify-content: center; align-items: flex-start;` (hoặc cấu trúc cho phép căn giữa trang và cuộn trơn tru).
2. `.paper-frame`:
   - Phải có `width` và `height` rõ ràng được cập nhật theo pixel layout tương ứng với zoom.
   - `flex-shrink: 0;` (ngăn flexbox tự ý co ép kích thước của trang giấy).
   - `box-shadow` và viền trang giấy sắc nét.

---

## 3. Hàm JavaScript hỗ trợ hiển thị kích thước trang giấy (`paper.js` & `write.js`)

### `getPaperPixelDimensions(paperSize, orientation, zoom)`
- **Đầu vào**:
  - `paperSize`: `"a4" | "a5" | "letter"`
  - `orientation`: `"portrait" | "landscape"`
  - `zoom`: Số thập phân dương (ví dụ `1.0`, `1.25`, `0.75`)
- **Đầu ra**:
  ```javascript
  {
    widthPx: number,
    heightPx: number,
    widthPt: number,
    heightPt: number
  }
  ```

### `applyPaperZoom(zoom, isFit = false)`
- Cập nhật kích thước `.paper-frame` của tất cả các trang trong preview.
- Cập nhật nội dung hiển thị của `#zoom-percent-display` (ví dụ `"100%"`).
- Kích hoạt tính toán lại khi có sự kiện thay đổi kích thước container nếu `isFit === true`.
