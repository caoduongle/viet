# Quickstart & Validation Guide: Web Client (020)

Tài liệu này hướng dẫn cách build, kiểm thử tự động, và chạy nghiệm thu ứng dụng web tĩnh cục bộ trước khi triển khai lên Render.

---

## 1. Yêu cầu Môi trường (Prerequisites)
- **Python**: 3.10 trở lên (khuyến nghị 3.12+ hoặc 3.14).
- **Node.js**: 20 trở lên (khuyến nghị 22+ hoặc 24 LTS).
- **Trình duyệt**: Bất kỳ trình duyệt hiện đại nào (Chrome, Edge, Firefox, Safari) hỗ trợ WebAssembly, Web Worker và IndexedDB.

---

## 2. Các bước Thực hiện & Nghiệm thu

### Bước 1: Đóng gói Ứng dụng Web tĩnh
Chạy kịch bản build để suy ra đồ thị import, sao chép các module lõi cần thiết, tải wheels vendor và đóng gói thư mục `webapp/dist`:
```bash
python scripts/build_web.py
```
**Kết quả kỳ vọng**:
- Sinh thư mục `webapp/dist/`.
- Kiểm tra danh mục file: KHÔNG có `chu_cua_ban.json.gz`, `tests/`, `specs/`, `view/`, `gui.py`, `cli.py`.
- Tồn tại file `webapp/dist/version.json` và runtime Pyodide tại `webapp/dist/pyodide/`.

### Bước 2: Chạy thử Nghiệm thu Cục bộ (Local Run)
Vì Web Worker, IndexedDB và Service Worker yêu cầu ngữ cảnh bảo mật (`https://` hoặc `localhost`), hãy khởi chạy HTTP server từ thư mục dist:
```bash
python -m http.server 8000 --directory webapp/dist
```
Mở trình duyệt tại: `http://localhost:8000`

**Kịch bản kiểm thử luồng người dùng (User Acceptance Flow)**:
1. **Khởi động**: Thấy thanh tiến trình nạp Pyodide thật, trạng thái chuyển sang "Sẵn sàng". Màn hình chào hiển thị 3 lựa chọn.
2. **Nạp kho mẫu**: Chọn "Nhập kho có sẵn", tải lên file `tests/data/kho_mau_tong_hop.json.gz`. Thẻ trạng thái hiển thị đúng số lượng nhãn và từ.
3. **Soạn thảo & Xem trước**:
   - Gõ một đoạn văn bản tiếng Việt có kèm công thức toán `$\frac{1}{2}$`.
   - Ngừng gõ ~250ms, trang giấy bên phải tự động dựng nét chữ viết tay mà không bị chớp trắng giao diện.
   - Thử gõ Telex/VNI: khi đang gõ tổ hợp phím (IME), trang giấy không giật lag.
4. **Từ thiếu mẫu & Dạy mẫu**:
   - Gõ một từ chưa có mẫu (ví dụ: `blockchain`). Từ xuất hiện trong bảng "Từ thiếu mẫu".
   - Bấm vào từ `blockchain` -> Ứng dụng tự chuyển sang tab **Dạy mẫu** với nhãn `blockchain` đã nạp sẵn vào hàng đợi.
   - Dùng chuột hoặc bút vẽ nét chữ vào vùng canvas (kích thước chuẩn 760x230, có đường dóng chân chữ và mốc chiều cao).
   - Nhấn `Enter` -> Mẫu được lưu thành công, thông báo "Đã lưu vào trình duyệt".
   - Quay lại tab **Viết chữ** -> Từ `blockchain` nay đã được vẽ bằng chính nét chữ vừa dạy.
5. **Xuất file**: Bấm nút **Xuất .xopp** để tải file về máy. Mở file bằng Xournal++ hoặc so sánh byte với CLI.

### Bước 3: Kiểm thử Tự động Hồi quy (Automated Testing)

#### 1. Kiểm thử Toàn bộ Test Suite Python hiện có:
```bash
pytest
```
*Kỳ vọng*: Toàn bộ 1.074+ tests xanh (100% pass).

#### 2. Kiểm thử Golden Master trong Pyodide (8/8 ca):
```bash
node scripts/test_golden_pyodide.js
```
*Kỳ vọng*: 8/8 ca (`co_ban`, `tuy_chon`, `nhieu_trang`, `strict_case`, `assemble_letters`, `math`, `table`, `markdown_list`) đều báo `✅ MATCH` mã băm SHA-256 so với CPython gốc.

#### 3. Kiểm thử Ranh giới Kiến trúc MVC:
```bash
pytest tests/test_architecture.py
```
*Kỳ vọng*: Không vi phạm bất kỳ quy tắc phụ thuộc một chiều nào (đặc biệt `bridge.py` không được import `model/*`).

#### 4. Kiểm thử End-to-End với Playwright (Dev/CI):
```bash
npx playwright test
```
*Kỳ vọng*: Xác minh luồng e2e hoạt động trơn tru và assert `0` network requests ra ngoài origin `http://localhost:8000`.

---

## 3. Triển khai lên Render Static Site
1. Đẩy code lên GitHub.
2. Tại Render Dashboard, chọn **New +** -> **Blueprint**.
3. Kết nối với repository và chọn file `render.yaml`.
4. Render sẽ tự động phát hiện `buildCommand` và `staticPublishPath: ./webapp/dist`.
5. Sau khi deploy thành công, truy cập URL Render được cấp để kiểm tra ứng dụng chạy trực tuyến.
