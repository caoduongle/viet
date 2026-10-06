# Contract: Giao tiếp Cấu hình Môi trường cho scripts/serve.mjs

## 1. Biến môi trường Đầu vào

Máy chủ tĩnh Node.js HTTP `scripts/serve.mjs` hỗ trợ cấu hình runtime thông qua các biến môi trường:

| Tên biến | Kiểu dữ liệu | Giá trị mặc định | Mô tả |
|---|---|---|---|
| `PORT` | Số nguyên | `8000` | Cổng TCP mà HTTP server sẽ lắng nghe (`server.listen(PORT)`). |
| `DIST_DIR` | Chuỗi đường dẫn | `webapp/dist` | Đường dẫn thư mục tĩnh gốc chứa các tài nguyên web (`index.html`, `js/`, `css/`, `sw.js`, ...). Luôn được chuẩn hoá qua `path.resolve()`. |

## 2. Quy tắc Định tuyến & Bảo mật (Routing & Security Contracts)

1. **Root Redirect**: Khi `req.url` là `"/"`, tự động chuyển thành `"/index.html"`.
2. **URL Decoding**: Đường dẫn được giải mã qua `decodeURIComponent()`. Nếu chuỗi URI không hợp lệ, trả về:
   - HTTP Status: `400 Bad Request`
   - Content-Type: `text/plain`
   - Body: `Bad Request`
3. **Path Traversal Protection**: Kiểm tra tuyệt đối:
   ```javascript
   if (filePath !== DIST_DIR && !filePath.startsWith(DIST_DIR + path.sep))
   ```
   Nếu vi phạm (yêu cầu chứa `../` hoặc trỏ ra ngoài `DIST_DIR`):
   - HTTP Status: `403 Forbidden`
   - Content-Type: `text/plain`
   - Body: `Forbidden`
4. **Not Found**: Nếu file không tồn tại hoặc là thư mục:
   - HTTP Status: `404 Not Found`
   - Content-Type: `text/plain`
   - Body: `Not Found`
5. **Success Response**: Trả về nội dung tệp tin cùng MIME Type thích hợp dựa trên phần mở rộng (`.html`, `.js`, `.css`, `.json`, `.wasm`, `.zip`, `.whl`, ...).
