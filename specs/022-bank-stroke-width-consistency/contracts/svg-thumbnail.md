# Contract: SVG Thumbnail Generation in Web Client Bank Tab

## Function Signature

Trong `webapp/js/bank.js`:

```javascript
/**
 * Dựng chuỗi HTML thẻ <svg> hiển thị hình thu nhỏ (thumbnail) nét chữ từ toạ độ ngân hàng.
 *
 * @param {Array<Array<number>>} strokes Danh sách các nét phẳng [[x0, y0, x1, y1, ...], ...]
 * @param {number} [width=100] Chiều rộng thẻ SVG (px)
 * @param {number} [height=50] Chiều cao thẻ SVG (px)
 * @param {Object} [options={}] Tuỳ chọn hiển thị
 * @param {number} [options.minVbHeight=24.0] Chiều cao khung tham chiếu tối thiểu (pt)
 * @param {number} [options.strokeWidth=1.8] Độ dày nét hiển thị trên màn hình (px)
 * @param {boolean} [options.showBaseline=false] Hiển thị đường kẻ chân chữ mờ (y=0)
 * @returns {string} Chuỗi HTML <svg>...</svg>
 */
export function createSvgFromStrokes(strokes, width = 100, height = 50, options = {})
```

## SVG Markup Contract

```html
<svg viewBox="{vbX} {vbY} {targetW} {targetH}" width="{width}" height="{height}" style="max-width: 100%; max-height: 100%; display: block; margin: auto;">
  <!-- Nếu options.showBaseline === true -->
  <line x1="{vbX}" y1="0" x2="{vbX + targetW}" y2="0" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="2,2" vector-effect="non-scaling-stroke" />
  
  <!-- Các nét chữ -->
  <polyline points="{pts}" fill="none" stroke="#0f172a" stroke-width="{strokeWidth}" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

## Invariants

1. **Non-empty strokes**: Nếu `strokes` rỗng hoặc không có toạ độ hợp lệ, trả về chuỗi rỗng `""`.
2. **AspectRatio Preservation**: SVG luôn bảo toàn tỷ lệ khung hình tự nhiên mà không làm méo mó toạ độ nét.
3. **No Overflow**: Không có điểm nét nào bị cắt cụt (clipping) ngoài biên `viewBox`.
4. **Resolution-independent stroke width**: Nhờ `vector-effect="non-scaling-stroke"`, độ dày nét rendered trên màn hình luôn đúng kích thước chỉ định mà không phụ thuộc vào kích thước bounding box của ký tự.
