# Contract: Bank UI Safety & SVG Preview

**Scope**: Ràng buộc an toàn DOM và hiển thị nét chữ trong `webapp/js/bank.js`.

---

## 1. Ràng buộc Module Mã hóa Chuỗi HTML Dùng chung

Hàm `escapeHtml` được cung cấp qua module độc lập `webapp/js/html-utils.js`:

```javascript
export function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
```

Tất cả các điểm gắn DOM trong `webapp/js/bank.js` và `webapp/js/write.js` phải import và sử dụng hàm này cho các nhãn `label`, `category` và `err.message`.

---

## 2. Ràng buộc Hiển thị Xem thử Ngẫu nhiên (Random Preview)

Khi người dùng nhấn nút xem thử ngẫu nhiên (`handleRandomPreview`):
1. Hệ thống gửi yêu cầu `write_text` với 3 hạt giống: `[7, 42, 99]`, kèm tùy chọn:
   ```javascript
   {
     seed,
     missing_grid: false,  // Bắt buộc: Chống tạo file rác trong MEMFS
     background: "plain",  // Nền trắng không kẻ dòng để xem rõ nét chữ
   }
   ```
2. Đối với mỗi kết quả nhận được chứa `xopp_base64`:
   - Phải giải nén nhị phân qua `decompressXoppBase64(res.xopp_base64)`.
   - Phải phân tích XML qua `parseXoppXml(xml)`.
   - Phải tính toán bounding box của các nét vẽ thực tế và gán `viewBox` cắt gọn (thêm padding 10pt) để chữ hiển thị to rõ thay vì thu nhỏ cả trang A4.
   - Nhúng phần tử SVG vào khung xem trước.
   - Phải hủy bỏ việc hiển thị nếu người dùng đã chuyển sang xem chi tiết nhãn khác (Race Condition guard).
