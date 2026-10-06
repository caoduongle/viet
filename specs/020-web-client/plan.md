# Implementation Plan: 020 — Web Client tĩnh 100% phía trình duyệt

**Branch**: `020-web-client` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

**Input**: Feature specification from `/specs/020-web-client/spec.md` and Phase 0 Survey Report from `/specs/020-web-client/report-g0.md`

---

## 1. Summary

Chuyển đổi ứng dụng "Chữ viết tay của bạn" (Python, MVC, hiện có CLI + Tkinter) thành ứng dụng web tĩnh 100% client-side chạy trên trình duyệt bằng WebAssembly (Pyodide 314.0.7 trong Web Worker), triển khai lên Render Static Site. Mọi dữ liệu (kho mẫu, văn bản) lưu trữ độc quyền trong trình duyệt người dùng qua IndexedDB; không có bất kỳ server-side backend, database hay analytics/telemetry nào. Lõi Python (`model/`, `controller/`, `layout/`, `document/`, `importer/`, `math/`) được giữ nguyên vẹn làm nguồn sự thật duy nhất cho thuật toán (Zero Algorithm Porting). Giao diện xây dựng bằng HTML/CSS/JS ES Modules thuần (Zero Framework/Zero Bundler cho runtime), tự host toàn bộ tài nguyên (Zero External CDN). Hỗ trợ đồng bộ an toàn đa tab qua Web Locks + BroadcastChannel, PWA offline, và đảm bảo 100% tính bất biến SHA-256 từng byte của file đầu ra `.xopp` so với CPython trên cả 8 ca Golden Master.

---

## 2. Technical Context

**Language/Version**: 
- Python: 3.10+ (Core, tested on 3.10–3.14; Pyodide runtime v314.0.7 chạy Python 3.14.2).
- JavaScript: Modern ECMAScript (ES2022+), ES Modules, không dùng framework (React/Vue/Angular), không dùng bundler runtime (Webpack/Vite).

**Primary Dependencies**:
- Runtime Web: Pyodide v314.0.7 (chạy trong Web Worker).
- Vendor Pure-Python Wheels: `markdown-it-py` (v4.2.0), `mdit-py-plugins` (v0.6.1), `mdurl` (v0.1.2) cho bộ phân tích Markdown; `lxml` (WASM wheel v6.1.3) + `python-docx` cho tính năng nạp tài liệu Word (tải lười).
- Core Package: Giữ nguyên Zero Core Dependencies (`dependencies = []`).

**Storage**:
- Trình duyệt: IndexedDB (database `chuviettay_db`, object stores `profiles` và `app_settings`).
- Pyodide Runtime: Emscripten in-memory virtual filesystem (MEMFS `/tmp`).
- Định dạng dữ liệu: Gzip-compressed JSON (`.json.gz`), tuân thủ nghiêm ngặt Schema Version 4.

**Testing**:
- CPython: `pytest`, `pytest-timeout`, `tests/test_architecture.py`.
- Pyodide in Node.js: `scripts/test_golden_pyodide.js` kiểm tra SHA-256 của 8 ca Golden Master.
- E2E Testing: Playwright (dev/CI).

**Target Platform**: 
- Render Static Site (`render.yaml`, runtime `static`, Linux build environment với Python).
- Trình duyệt web hiện đại trên máy tính và máy tính bảng (Chrome, Edge, Firefox, Safari).

**Project Type**: Client-side Static Web Application + Python Core Library.

**Performance Goals**:
- Khởi động Pyodide lần thứ hai (khi đã cache binary): khoảng vài giây (đo thực tế trên laptop phổ thông).
- Kết xuất xem trước 1 trang văn bản: ≤ 1.0s sau khi ngừng gõ (áp dụng debounce phù hợp).
- Thao tác trên Main Thread: 0 tác vụ (Long Task) chặn giao diện quá 50ms.
- Dung lượng tải mạng lần đầu (sau nén): đo và báo cáo thực tế qua các mốc nghiệm thu (không đặt giả định cứng).

**Constraints**:
- Ràng buộc cứng 1–10 trong spec: Không sửa `config.py`, không đụng dữ liệu cá nhân, giữ MVC một chiều, zero external runtime CDN, zero telemetry/analytics.
- Danh sách sửa đổi lõi đóng: Chỉ thực hiện 3.1 (bộ hẹn giờ tiêm được), 3.2 (tách hàm quy đổi canvas), 3.3 (accessor chỉ đọc), 3.4 (hợp nhất nếu cần).

**Scale/Scope**:
- 5 giai đoạn phát triển chính: G1 (Nền tảng & Cầu nối) -> G2 (Soạn thảo & Xem trước) -> G3 (Dạy mẫu Canvas) -> G4 (Kho mẫu & Đa tab) -> G5 (Hoàn thiện PWA, Hiệu năng, Render & Docs).

---

## 3. Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`*

- **Principle I: Maintainability & Code Cleanliness**: 
  - **PASS**. Mã nguồn Python phân định rõ ranh giới: lớp `chuviettay/browser/bridge.py` đóng vai trò Facade độc lập. Mã JS frontend được module hóa theo từng tính năng (`paper.js`, `write.js`, `teach.js`, `bank.js`, `canvas.js`, `storage.js`, `i18n.js`).
- **Principle II: Simple Architecture (KISS & YAGNI)**:
  - **PASS**. Không sử dụng framework frontend cồng kềnh hay compiler phức tạp; dùng HTML/CSS/JS thuần. Loại bỏ chế độ Fidelity khỏi web vì không cần thiết. Trì hoãn các tính năng mở rộng (xóa từng mẫu G5b, định dạng in đậm/nghiêng G8) để giữ kiến trúc tinh gọn.
- **Principle III: Comprehensive Automated Testing**:
  - **PASS**. Duy trì 100% số lượng test CPython hiện có (1.074 tests). Thêm test kiểm tra ranh giới kiến trúc cho `bridge.py`. Đưa kiểm thử Golden Master 8 ca trong Pyodide vào script tự động chạy trong CI.
- **Principle IV: Loose Coupling & High Cohesion**:
  - **PASS**. Tuân thủ luật MVC một chiều: `bridge.py` và JS không đụng trực tiếp `model/*`, chỉ gọi qua `AppController`. Các module lõi (`model/`, `controller/`, `layout/`) hoàn toàn không biết gì về Pyodide, JS hay DOM.
- **Rule of No Unjustified Dependencies**:
  - **PASS**. Lõi giữ nguyên zero dependencies. Frontend không dùng thư viện ngoài; runtime WASM được tự host.

---

## 4. Project Structure

### Documentation (this feature)

```text
specs/020-web-client/
├── spec.md                     # Feature specification (User stories, Requirements, SC)
├── report-g0.md                # Phase 0 Survey & Feasibility report (Golden master, Pyodide bench)
├── research.md                 # Phase 0 Technical decisions (D1-D8, architecture choices)
├── data-model.md               # Phase 1 Data models (IndexedDB schemas, runtime state, canvas spec)
├── quickstart.md               # Phase 1 Setup, run & validation guide
├── checklists/
│   └── requirements.md         # Specification quality checklist
├── contracts/                  # Phase 1 Interface contracts
│   ├── bridge-api.md           # Python Bridge <-> JS Worker API specifications
│   ├── storage-protocol.md     # Multi-tab concurrency & Web Locks protocol
│   └── render-blueprint.md     # Render Static Site blueprint & build specifications
├── plan.md                     # This implementation plan
└── tasks.md                    # Actionable task list (created via /speckit-tasks)
```

### Source Code Structure

```text
# Python Core & Bridge
chuviettay/
├── browser/                    # [MỚI] Module cầu nối Web
│   ├── __init__.py
│   └── bridge.py               # Facade JSON API cho Web Worker (chỉ gọi AppController)
├── controller/
│   ├── app_controller.py       # Injectable timer (3.1), read-only accessors (3.3)
│   └── teach_geometry.py       # [MỚI] Chuyển strokes_to_bank_units & canvas constants (3.2)
├── view/
│   └── word_canvas.py          # Re-export từ teach_geometry để Tkinter không đổi
scripts/
├── build_web.py                # [MỚI] Script đóng gói webapp/dist (suy đồ thị import, vendor wheels)
└── test_golden_pyodide.js      # [MỚI] Chạy 8 ca Golden Master trong Pyodide bằng Node

# Frontend Web Application (Vanilla ES Modules)
webapp/
├── index.html                  # Giao diện chính (Header, Tabs, Editor, Canvas, Library)
├── manifest.webmanifest        # PWA Manifest
├── sw.js                       # Service Worker (Cache-first offline runtime & assets)
├── css/
│   ├── main.css                # Base layout, typography, responsive rules (~768px)
│   ├── editor.css              # 2-column layout (textarea + live preview paper)
│   ├── canvas.css              # Drawing canvas styling & touch gestures
│   ├── bank.css                # Bank statistics & sample library grid
│   └── themes.css              # System / Dark / Light theme variables
└── js/
    ├── app.js                  # Entrypoint, tab router, status indicators, toast notifications
    ├── i18n.js                 # Chuỗi tiếng Việt tập trung (có chuỗi tiếng Anh dự phòng)
    ├── storage.js              # IndexedDB operations, Web Locks wrapper, BroadcastChannel sync
    ├── paper.js                # Render SVG preview from .xopp XML, guidelines, paper backgrounds
    ├── write.js                # Live editor controller, debounce (250ms), IME composition handling
    ├── teach.js                # Teach tab manager, queue handler, calibration logic
    ├── canvas.js               # Pointer Events, palm rejection, logical coord scaling (760x230)
    ├── bank.js                 # Bank browser, search filter, sample thumbnails, backup/import UI
    └── worker/
        └── py-worker.js        # Web Worker script hosting Pyodide runtime & dispatching bridge calls

# Deployment & CI
render.yaml                     # Render Blueprint cho Static Site (type: web, runtime: static)
.github/workflows/
└── ci.yml                      # Thêm job test web build + pyodide golden master + python 3.14
```

---

## 5. Implementation Roadmap (Phases G1 – G5)

### G1: Nền tảng Kỹ thuật (Foundation & Infrastructure)
- **Mục tiêu**: Thiết lập cây cầu nối Python <-> Web Worker, đóng gói tự động qua `scripts/build_web.py`, cấu hình IndexedDB và `render.yaml`.
- **Hạng mục**:
  1. Tách `strokes_to_bank_units` sang `chuviettay/controller/teach_geometry.py`; `view/word_canvas.py` re-export (Thay đổi lõi 3.2).
  2. Bổ sung bộ hẹn giờ tiêm được vào `AppController` (Thay đổi lõi 3.1).
  3. Bổ sung Accessor chỉ đọc cho `AppController` (Thay đổi lõi 3.3).
  4. Cài đặt `chuviettay/browser/bridge.py` (Facade JSON API).
  5. Mở rộng `tests/test_architecture.py` để quét `browser/` và xác nhận không kéo `tkinter`.
  6. Viết `scripts/build_web.py` (suy đồ thị import, gom file, vendor wheels, băm file, `version.json`).
  7. Viết `webapp/js/worker/py-worker.js` nạp Pyodide cục bộ và nhận/trả thông điệp.
  8. Khởi tạo cấu trúc khung HTML/CSS và module `storage.js` (IndexedDB).
  9. Tạo `render.yaml` và ghim phiên bản Python/Node.
  10. Sửa test phụ thuộc môi trường `test_paths_logging.py` (D6).
- **Tiêu chí nghiệm thu**: Bản build chạy trên `http://localhost:8000`, nạp được `kho_mau_tong_hop.json.gz`, hiển thị thông tin thống kê. Kiểm thử kiến trúc xanh.

### G2: Soạn thảo Văn bản & Xem trước Trực tiếp (Write & Live Preview)
- **Mục tiêu**: Xây dựng trình soạn thảo 2 cột, kết xuất chữ viết tay trực tiếp lên trang giấy, xuất `.xopp`, PNG, SVG, In/PDF.
- **Hạng mục**:
  1. Trình soạn thảo 2 cột: textarea + trang giấy xem trước tự cập nhật sau ~250ms ngừng gõ.
  2. Xử lý bộ gõ IME (`compositionstart` / `compositionend`) để tránh giật lag khi gõ Telex/VNI.
  3. Thanh công cụ Markdown (tiêu đề 1-3, danh sách, bảng, công thức `$...$` và `$$...$$`, ngắt trang).
  4. Bảng chèn ký hiệu LaTeX động lấy từ `bridge.py` (`math/symbols.py`).
  5. Tải/kéo thả file `.txt`, `.md`, `.docx` (tải lười `lxml`).
  6. Thanh trượt tùy chọn viết (cỡ chữ, giãn dòng, bề rộng dòng, giãn từ, độ run, hạt giống seed kèm nút xúc xắc, màu mực, khổ giấy, hướng giấy, nền giấy).
  7. Bật cờ `stable_variants` trên web để giữ ổn định kiểu chữ khi sửa giữa đoạn (D3).
  8. Parser trích xuất SVG từ `.xopp` trong `paper.js` (dựng nét và vẽ nền giấy).
  9. Hiển thị bảng "Từ thiếu mẫu" (`missing_sorted`) kèm callback gạch đỏ trên trang (D2).
  10. Chức năng xuất file: tải file `.xopp` gốc, xuất ảnh PNG/SVG (1x/2x/3x, nền trong suốt/nền giấy, tải riêng hoặc ZIP), in/PDF qua print stylesheet.
- **Tiêu chí nghiệm thu**: File `.xopp` tải từ web giống từng byte CLI cùng seed/tùy chọn (với `--stable`). SVG/PNG khớp nét 100%.

### G3: Vùng vẽ & Dạy mẫu chữ (Teach Canvas & Samples)
- **Mục tiêu**: Cung cấp công cụ dạy mẫu chữ trực tiếp trên web bằng chuột, bút hoặc cảm ứng với tỉ lệ hình học chuẩn xác so với Tkinter.
- **Hạng mục**:
  1. Canvas tương tác bằng Pointer Events (`pointerdown`, `pointermove`, `pointerup`), `touch-action: none`.
  2. Cơ chế lọc điểm thô theo `min_point_dist` (2.5px logic) và làm mượt nét chỉ để hiển thị.
  3. Tọa độ logic cố định 760x230 co giãn bằng CSS theo spec từ `bridge.py`.
  4. Đường dóng có nhãn (chân chữ, mốc xh, lưới 4 dòng `hw3` cho chữ cái). Chữ mẫu mờ bật/tắt.
  5. Hàng đợi dạy chữ: nạp từ thông dụng (`missing_seed_words`), nạp bộ tối thiểu (`missing_minimal_essentials`), thêm từ tự do, hiệu chỉnh cỡ tay (`start_calibration`).
  6. Phím tắt thao tác nhanh: `Enter` (lưu và sang từ kế), `Ctrl+Z` (hoàn tác nét), `Esc` (bỏ qua).
  7. Route chuẩn xác sang `ctl.teach_letter` (chữ cái/dấu thanh) hoặc `ctl.teach_word` (từ, số, dấu câu, ký hiệu).
- **Tiêu chí nghiệm thu**: Replay cùng một chuỗi điểm qua đường Tkinter và đường web cho ra kho JSON giống hệt từng byte.

### G4: Quản lý Kho mẫu, Nhập/Xuất & Đa Tab (Library & Concurrency)
- **Mục tiêu**: Quản lý thư viện mẫu theo từng nhãn, chuyển đổi hồ sơ, xuất/nhập kho và bảo đảm an toàn đa tab.
- **Hạng mục**:
  1. Thẻ thống kê tổng quan theo danh mục (từ, chữ cái, số, dấu câu, ký hiệu, dấu thanh).
  2. Lưới nhãn có ô tìm kiếm tức thì, lọc theo danh mục, hiển thị hình thu nhỏ SVG và số mẫu.
  3. Màn hình chi tiết nhãn (Thư viện mẫu): xem các kiểu cạnh nhau, nút "Thêm kiểu mới" (chuyển sang tab Dạy), nút "Xem thử ngẫu nhiên", chỉ báo độ phủ (< 2 mẫu).
  4. Xóa cả nhãn có xác nhận + thông báo Toast có nút Hoàn tác (Undo).
  5. Quản lý đa hồ sơ (Profiles): tạo mới (không ghi đè kho cũ), đổi tên, chuyển đổi qua chip trạng thái.
  6. Giao thức đồng bộ đa tab bằng Web Locks (`navigator.locks`) + IndexedDB + `BroadcastChannel`.
  7. Xuất file sao lưu `.json.gz` tương thích 100% CLI, nạp kho cũ từ desktop vào web.
- **Tiêu chí nghiệm thu**: Hai tab cùng mở, cùng dạy và xóa đồng thời mà không bị mất nét vẽ và không làm hồi sinh nhãn đã xóa. File xuất mở được bằng `hw-note stats`.

### G5: Hoàn thiện PWA, Tối ưu Hiệu năng, Render & Tài liệu
- **Mục tiêu**: Đảm bảo PWA offline, đáp ứng tiêu chuẩn hiệu năng mục 8, kiểm thử CI tự động và cập nhật tài liệu.
- **Hạng mục**:
  1. Service Worker (`sw.js`) cache toàn bộ static assets và runtime WASM, hoạt động offline sau lần tải đầu.
  2. Bắt sự kiện cập nhật của Service Worker, hiển thị thông báo "Có bản mới — bấm để tải lại".
  3. Đo đạc các chỉ số hiệu năng thực tế bằng Playwright (first load size, second load time, preview latency, long tasks) và lập báo cáo.
  4. Script CI cho GitHub Actions: build web, chạy kiểm thử Golden Master trong Pyodide (`scripts/test_golden_pyodide.js`), kiểm tra rò rỉ file trong dist.
  5. Bổ sung job Python 3.14 vào CI matrix (D8).
  6. Cập nhật `README.md` (hướng dẫn triển khai Render, chạy thử cục bộ, sửa tên file golden master `test_golden_master_real_path.py`).
  7. Cập nhật `CHANGELOG.md` ghi nhận toàn bộ cải tiến của phiên bản Web Client.
- **Tiêu chí nghiệm thu**: Ứng dụng chạy offline sau lần tải đầu; đạt 100% tiêu chí đo đạc mục 8; CI xanh 100%.

---

## 6. Complexity Tracking

*Không phát hiện vi phạm ranh giới kiến trúc hay cấu trúc phức tạp bất thường. Mọi thay đổi đều tuân thủ danh sách đóng được phê duyệt.*

| Thành phần | Mức độ phức tạp | Biện pháp kiểm soát & Lý do chấp thuận |
|---|---|---|
| Web Worker + Pyodide | Vừa phải | Đóng gói toàn bộ trong `py-worker.js`; Main Thread chỉ giao tiếp bất đồng bộ qua thông điệp có ID, tránh khóa cứng UI. |
| Đồng bộ đa tab | Vừa phải | Tận dụng nguyên bản thuật toán `Bank.save` và `merge_bank_dicts` của Python; Web Locks bảo đảm tính tuần tự độc quyền; không viết lại logic hợp nhất bằng JS. |
| Vendor Wheels | Thấp | Chỉ vendor 3 wheel pure-Python nhỏ gọn (`markdown-it-py`, `mdit-py-plugins`, `mdurl`); `lxml` wasm và `python-docx` được tách riêng để nạp lười. |
