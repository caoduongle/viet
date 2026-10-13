# Quickstart & Hướng dẫn kiểm chứng (Validation Guide)

**Feature**: `038-web-only-remove-desktop`  
**Date**: 2026-10-13  
**Status**: Hoàn thành  

---

Tài liệu này hướng dẫn cách chạy và kiểm chứng độc lập rằng ứng dụng đã chuyển đổi hoàn toàn sang Web Client duy nhất, các thành phần Desktop và CLI đã được dọn sạch, và 100% tính năng cốt lõi hoạt động ổn định.

---

## 1. Yêu cầu môi trường (Prerequisites)

- **Python**: 3.10 trở lên (khuyên dùng Python 3.11 hoặc 3.12).
- **Node.js**: 18.x trở lên (đã ghi nhận trong `.node-version`).
- **Không cần**: `tkinter`, `xvfb`, hay `pyinstaller`.

---

## 2. Thiết lập môi trường (Setup)

```bash
# 1. Cài đặt các gói phụ thuộc Python cho phát triển và kiểm thử
pip install -r requirements-dev.txt

# 2. Cài đặt các phụ thuộc Node.js (bao gồm runtime Pyodide và Playwright)
npm ci
npx playwright install --with-deps chromium
```

---

## 3. Các kịch bản kiểm chứng tự động (Automated Verification Scenarios)

### Kịch bản 1: Kiểm chứng không còn mã Desktop / CLI và không có import Tkinter
Chạy kiểm tra kiến trúc để chứng minh không còn bất kỳ tệp hay module nào import `tkinter`, `chuviettay.view`, `chuviettay.cli`, `chuviettay.gui`:

```bash
python -m pytest tests/test_architecture.py -vv
```
*Kết quả kỳ vọng*: Tất cả các bài kiểm tra kiến trúc đều PASS; khẳng định 0 import `tkinter` trên toàn bộ repository.

---

### Kịch bản 2: Kiểm chứng toàn bộ Lõi xử lý chung (Core Tests)
Chạy bộ kiểm thử lõi mà không cần bất kỳ môi trường đồ họa ảo hay biến `DISPLAY` nào:

```bash
python -m pytest tests/ -k "not web and not browser and not benchmark" -vv --timeout=30
```
*Kết quả kỳ vọng*:
- Không có bài test nào bị lỗi do thiếu `tkinter` hay thiếu display.
- Toàn bộ các bài test về bố cục (bảng, toán LaTeX, ngắt trang, RNG hạt giống, ghép nét chữ cái, Fidelity) đều PASS.

---

### Kịch bản 3: Kiểm chứng tính tương đương từng byte (Golden Master Parity)
Xác nhận rằng kết quả sinh nét của Web Client (`BrowserBridge`) trùng khớp từng byte với bộ điều phối lõi (`AppController`):

```bash
python -m pytest tests/test_web_controller_parity.py tests/test_golden_master_real_path.py -vv
```
*Kết quả kỳ vọng*: 100% các bài test golden master và parity đều PASS.

---

### Kịch bản 4: Đóng gói và kiểm thử bản Web tĩnh (Build & Web Sanity)
Đóng gói mã nguồn sạch thành bản Web tĩnh và kiểm tra tính toàn vẹn của gói phân phối:

```bash
# Đóng gói web client
python scripts/build_web.py

# Kiểm thử tính sạch sẽ của bản phân phối dist (không chứa mã cấm, không chứa tệp nhị phân desktop)
python -m pytest tests/test_build_web.py -vv
```
*Kết quả kỳ vọng*:
- `webapp/dist/pyodide/chuviettay.zip` được tạo thành công, chỉ chứa các module lõi (`browser`, `controller`, `model`, `document`, `importer`, `layout`, `math`).
- Không có bất kỳ file `view/`, `gui.py`, `cli.py` nào lọt vào bản phân phối.

---

### Kịch bản 5: Kiểm chứng giao diện người dùng Web đầu-cuối (E2E Tests)
Chạy kiểm thử giao diện trình duyệt thực tế qua Playwright:

```bash
# Khởi chạy kiểm thử Playwright cho 3 luồng: Viết chữ, Dạy chữ, Kho mẫu
npm test
```
*Kết quả kỳ vọng*:
- Kiểm thử `tests/e2e/write.spec.ts`, `tests/e2e/teach.spec.ts`, `tests/e2e/bank.spec.ts` đều PASS.
- Người dùng thực hiện đầy đủ các tác vụ tạo tài liệu, gõ công thức toán, dạy chữ mới và xuất file `.xopp` trực tiếp trên trình duyệt.

---

## 4. Kiểm chứng thủ công luồng nhập kho mẫu Desktop cũ (Manual User Flow)

1. **Khởi chạy máy chủ Web cục bộ**:
   ```bash
   node scripts/serve.mjs
   ```
   Mở trình duyệt truy cập `http://localhost:8000`.

2. **Chuyển đổi kho mẫu cũ**:
   - Chuyển sang tab **"Kho mẫu"**.
   - Bấm nút **"Nhập kho mẫu (.json.gz)"**.
   - Chọn tệp kho mẫu được tạo từ phiên bản Desktop trước đây (ví dụ `tests/data/kho_mau_tong_hop.json.gz`).
   - Quan sát bảng thống kê: Số lượng mẫu nét, chữ cái, chữ số, dấu câu hiển thị chính xác và đầy đủ.

3. **Viết thử văn bản**:
   - Chuyển sang tab **"Viết chữ"**.
   - Nhập một đoạn văn bản tiếng Việt có dấu và công thức toán (ví dụ: `Xin chào Việt Nam $E = mc^2$`).
   - Bấm **"Xem trước"** hoặc **"Tải về .xopp"**.
   - Tệp kết quả mở được trong Xournal++ hoặc hiển thị nét viết tay chuẩn xác trên màn hình.
