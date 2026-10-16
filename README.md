# Chữ viết tay của bạn (HandWrite Web)

Gõ chữ → ra **nét viết tay của chính bạn** cho Xournal++.

Ứng dụng hiện hoạt động dưới dạng **Web Client thuần túy (Static SPA / PWA)**: chạy 100% trong trình duyệt qua **WebAssembly (Pyodide 314.0.7)** mà không cần máy chủ backend, không yêu cầu cài đặt Python hay thư viện đồ họa cửa sổ (Tkinter) trên thiết bị của người dùng cuối.

Giao diện Web gồm ba tab chức năng chính:

| Tab | Mô tả | Có cần Xournal++ không |
|---|---|---|
| **Viết chữ** | Soạn thảo văn bản (Markdown, Math LaTeX, Bảng biểu) → xuất file `.xopp`, ảnh PNG/SVG, in PDF | Có (nếu muốn tiếp tục ghi chú trong Xournal++) hoặc tải trực tiếp ảnh/PDF |
| **Dạy chữ / Dạy từ mới** | Vẽ trực tiếp từng ký tự/chữ cái bằng chuột hoặc bút cảm ứng trên màn hình cảm ứng, bấm Lưu là xong | **Không** — không cần xuất/nạp file trung gian |
| **Kho mẫu** | Xem thống kê, tìm/xóa mẫu chữ an toàn, xem thumbnail nét vẽ, sao lưu và nhập tệp `.json.gz` | Xuất file lưới xem lại qua Xournal++ nếu cần kiểm tra tổng thể |

---

## Chuyển đổi từ bản Desktop cũ sang Web Client

Nếu bạn đã có tệp kho mẫu cá nhân từ phiên bản Desktop trước đây (`chu_cua_ban.json.gz` hoặc bất kỳ tệp kho mẫu nào):

1. Mở Web Client trong trình duyệt.
2. Chuyển sang tab **Kho mẫu**.
3. Bấm nút **"Nhập kho mẫu..."** (hoặc kéo thả tệp `.json.gz` vào vùng nhập).
4. Web Client tự động nạp và lưu trữ an toàn toàn bộ dữ liệu mẫu chữ (chữ cái, chữ số, dấu câu, ký hiệu, và hồ sơ cỡ tay) vào `IndexedDB` của trình duyệt. Mọi dữ liệu từ các phiên bản schema v1, v2, v3, v4 đều được bảo toàn nguyên vẹn 100%.
5. Muốn sao lưu kho mẫu từ Web Client về máy tính bất cứ lúc nào: bấm **"Sao lưu kho mẫu (.json.gz)"** trong tab Kho mẫu để tải tệp về.

---

## Hướng dẫn cài đặt & Khởi chạy (Dành cho Lập trình viên)

### Yêu cầu môi trường
- **Python 3.10+** (tương thích môi trường Python >= 3.10; hệ thống CI kiểm thử tự động chính thức trên Python 3.12, 3.13 và 3.14 future-proofing).
- **Node.js 18+** (cho các công cụ đóng gói Web, kiểm thử Playwright và Pyodide).
- **Zero GUI Dependencies**: Toàn bộ kho mã nguồn lõi chạy headless 100%, tuyệt đối không cần cài đặt `python3-tk` hay máy chủ hiển thị `xvfb`.

### Khởi chạy Web Client cục bộ

```bash
# 1. Cài đặt các gói phụ thuộc phát triển (tuỳ chọn)
pip install -r requirements-dev.txt

# 2. Đóng gói mã nguồn và dependencies vào webapp/dist/
python scripts/build_web.py

# 3. Khởi chạy HTTP Server hỗ trợ Web Worker & Cache headers
node scripts/serve.mjs
# Mở trình duyệt tại http://localhost:8000
```

### Triển khai lên máy chủ tĩnh (Render / GitHub Pages)

Dự án đã cấu hình sẵn Blueprint [`render.yaml`](render.yaml):
1. Đẩy mã nguồn lên kho lưu trữ GitHub/GitLab.
2. Trên [Render Dashboard](https://dashboard.render.com/), chọn **New +** → **Blueprint** và kết nối tới repository này.
3. Render tự động chạy `python scripts/build_web.py` và triển khai thư mục `webapp/dist/` dưới dạng Static Site.
4. Tệp Blueprint tích hợp sẵn:
   - Header bảo mật CSP (`Content-Security-Policy`), chống sniff MIME (`X-Content-Type-Options: nosniff`), Web Locks & Service Worker.
   - Header bộ đệm dài hạn `Cache-Control: public, max-age=31536000, immutable` cho các file tĩnh và tài nguyên WASM / wheels.

---

## Đặc tả tính năng & Mô hình thuật toán

### 1. Mô hình thuần ký tự & Tự động ghép chữ (Char-First Assembly)
- Mọi văn bản soạn thảo đều được tự động ghép từ các ký tự đơn (`letters`), chữ số (`digits`), dấu câu (`punct`), ký hiệu (`symbols`) và dấu thanh rời (`marks`).
- **Khoảng cách tự nhiên & chống dính chữ**: Sử dụng đường bao biên hình học (contour pair gap), khoảng đệm biên `lsb`/`rsb` và thuật toán kiểm chứng khoảng cách đoạn nét 2D kèm sàn khe hở vật lý (`pen_clearance = 0.8` lần nét bút), ngăn chặn triệt để hiện tượng bết dính mực giữa các chữ cái.
- **Ghép dấu thanh (Dual-Path Assembly)**: Ưu tiên dùng mẫu nguyên âm có sẵn dấu tiếng Việt trong kho; tự động fallback ghép nguyên âm cơ sở với dấu thanh rời theo trọng tâm và né tránh nét vươn cao (ascender).
- **Chuẩn hóa cỡ chữ (`auto_xh`)**: Tự động chuẩn hóa các ký tự về cùng cỡ x-height chuẩn (7,94 pt), bảo đảm tỉ lệ nét chữ đồng đều và thanh thoát.

### 2. Hạt giống ngẫu nhiên minh bạch & Kiểu chữ ổn định
- **Minh bạch hóa hạt giống (`seed`)**: Chấp nhận giá trị nguyên không âm trong khoảng $[0, 2^{32} - 1]$. Kết quả kết xuất trả về chính xác `seed_used` để người dùng có thể nhập lại và tái hiện kết quả bất kỳ lúc nào.
- **Kiểu chữ ổn định (`stable_variants`)**: Sử dụng bộ sinh ngẫu nhiên cục bộ `ScopedRNG` neo theo từng token và dòng. Việc chỉnh sửa hoặc thêm bớt câu chữ ở phần đầu tài liệu không làm thay đổi biến thể chữ và khoảng cách của các đoạn văn phía sau.

### 3. Khổ giấy, Mẫu nền & Căn dòng kẻ Xournal++ (Baseline Snapping)
- **Tương thích mẫu giấy Xournal++**: `plain` (trắng), `ruled`/`lined` (kẻ ngang), `graph` (ô vuông), `dotted` (chấm bi), `iso_graph`/`iso_dotted` (tam giác đều Isometric), `staves` (khuông nhạc).
- **Căn dòng tự động (`snap_to_ruling`)**: Tự động đặt chân chữ chính xác lên các đường kẻ ngang $y = 80.0 + k \cdot r_1$, tự động nhảy dòng chống đè chữ khi đổi cỡ bút và kẹp chặt trong biên độ lề in được.

### 4. Hỗ trợ Toán học & Bảng biểu
- **Toán học LaTeX & OMML**: Hỗ trợ phân số, căn thức, tích phân, tổng sigma, ma trận, hệ phương trình, ngoặc co giãn `\left...\right` và hơn 200 ký hiệu toán học. Ký hiệu chưa có mẫu được vẽ dự phòng bằng nét vector.
- **Bố cục bảng dữ liệu**: Tự động phân trang an toàn khi có ô gộp hàng/cột (`rowspan`/`colspan`), bẻ dòng theo ký tự cho các chuỗi URL hoặc mã băm dài, đồng bộ kích thước công thức toán học trong từng ô.

---

## Kiến trúc hệ thống (Web-Only Architecture)

Mã nguồn được phân tầng nghiêm ngặt với luồng phụ thuộc một chiều:

```
    Web Client (webapp/ - HTML / JS / CSS / Web Worker)
                          │  (Pyodide RPC qua Web Worker Bridge)
                          ▼
             chuviettay/browser/bridge.py
                          │
                          ▼
             chuviettay/controller/app_controller.py   ← Điểm điều phối nghiệp vụ duy nhất
                          │
                          ▼
             chuviettay/model/ & layout/ & document/   ← Thuật toán thuần Python
```

- **webapp/**: Giao diện người dùng tĩnh (Vanilla JS, Canvas API, IndexedDB).
- **chuviettay/browser/**: Cầu nối JSON-RPC trung gian giữa JavaScript và Python trong môi trường Pyodide.
- **chuviettay/controller/**: Bộ điều phối nghiệp vụ tập trung (`AppController`).
- **chuviettay/model/**: Quản lý kho mẫu (`Bank`), sinh nét viết (`Writer`), bộ dàn trang (`DocumentLayoutEngine`), đọc/ghi XOPP (`xopp.py`).
- **chuviettay/fidelity/**: Mã nguồn lưu trữ (legacy/archive) cho mô hình xử lý Word cố định toạ độ không gian (chỉ chạy ngoại tuyến với Word COM/LibreOffice; Web Client sử dụng cơ chế nạp nội dung Content-First sang Markdown).

### Tường lửa kiến trúc
Kiến trúc này được bảo vệ tự động bằng `tests/test_architecture.py`:
- Cấm 100% `tkinter` trên toàn bộ repository.
- Cấm tồn tại bất kỳ tệp Desktop GUI hoặc CLI nào trong kho mã nguồn.
- Mô hình lõi `model/` và `controller/` hoàn toàn độc lập, không phụ thuộc vào `js` hay `pyodide`.

---

## Kiểm thử & Đảm bảo chất lượng

Dự án duy trì bộ kiểm thử tự động toàn diện:

```bash
# 1. Chạy toàn bộ test suite lõi headless (hơn 1.200 bài kiểm thử)
pytest tests/ -k "not web and not browser and not benchmark" -q

# 2. Chạy kiểm thử kiến trúc cấm Tkinter
pytest tests/test_architecture.py -v

# 3. Kiểm thử Golden Master đối chiếu từng byte (Python & Pyodide)
pytest tests/test_golden_master_real_path.py -v
node scripts/test_golden_pyodide.mjs

# 4. Kiểm thử End-to-End giao diện Web (Playwright)
npx playwright test tests/e2e/write.spec.ts tests/e2e/teach.spec.ts tests/e2e/bank.spec.ts

# 5. Kiểm tra chất lượng mã nguồn (Lint)
ruff check .
```
