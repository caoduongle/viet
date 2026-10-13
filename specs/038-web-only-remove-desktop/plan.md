# Implementation Plan: Chuyển sang sản phẩm chỉ có Web — Loại bỏ ứng dụng Desktop & CLI

**Branch**: `038-web-only-remove-desktop` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/038-web-only-remove-desktop/spec.md`

---

## Summary

Chuyển đổi sản phẩm Chữ Viết Tay thành một ứng dụng Web tĩnh (Static Web App / PWA) duy nhất chạy hoàn toàn trên trình duyệt thông qua WebAssembly / Pyodide. Loại bỏ hoàn toàn ứng dụng Desktop Tkinter (`chuviettay/view/`, `gui.py`, `hw_gui.py`), công cụ dòng lệnh (`chuviettay/cli.py`, `hw_note.py`, console scripts `hw-note`), kịch bản đóng gói PyInstaller (`hw_gui.spec`, `build_windows.bat`, `build_linux_mac.sh`), các bài kiểm thử chỉ phục vụ Desktop/CLI và các phụ thuộc liên quan trong CI (`python3-tk`, `xvfb`). Bảo lưu nguyên vẹn 100% lõi xử lý chung (`model/`, `layout/`, `document/`, `importer/`, `math/`), mã nguồn lõi của chế độ Fidelity (`fidelity/`), và tính xác thực từng byte (byte-exact) của kết quả kết xuất.

---

## Technical Context

**Language/Version**: Python 3.10+ (Lõi xử lý & Pyodide 314.0.7), JavaScript (ES Modules), HTML5 / CSS3  
**Primary Dependencies**:
- Lõi (Core Engine): Không phụ thuộc thư viện ngoài (Zero external dependencies).
- Tài liệu mở rộng: `python-docx>=1.1.0`, `markdown-it-py>=3.0.0`, `mdit-py-plugins>=0.4.0`.
- Web Frontend: Pyodide 314.0.7 (WASM), Service Worker PWA, HTML5 Canvas.
- Đã gỡ bỏ: `tkinter`, `pyinstaller`, `xvfb`.  
**Storage**: Trình duyệt `IndexedDB` (lưu kho mẫu đang kích hoạt `active_bank`), xuất/nhập tệp `.json.gz` (Schema v3).  
**Testing**: `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `playwright>=1.40.0` (Node.js E2E).  
**Target Platform**: Các trình duyệt hiện đại (Chrome, Edge, Firefox, Safari) trên máy tính và thiết bị di động, PWA cài đặt độc lập.  
**Project Type**: Static Web Application / PWA (Client-Side WASM).  
**Performance Goals**: Thời gian khởi tạo Web Worker & Pyodide trong ngưỡng tối ưu, xem trước nét viết trong vòng < 500ms, không phụ thuộc máy chủ backend.  
**Constraints**: 100% byte-exact parity giữa Web và Engine cho cùng hạt giống và cấu hình viết; không được làm hỏng khả năng nhập kho mẫu từ phiên bản Desktop cũ.  
**Scale/Scope**: Loại bỏ ~3.000 dòng mã giao diện Tkinter & CLI thừa; xóa bỏ 7 tệp test Desktop/CLI; quy trình CI giảm 1 phụ thuộc hệ thống và chạy nhanh hơn.  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá | Ghi chú cụ thể |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | **PASS** | Xóa bỏ hoàn toàn mã cũ Desktop Tkinter và CLI giúp xóa bỏ gánh nặng kỹ thuật lớn, loại bỏ việc phải bảo trì 2 bộ giao diện song song. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Chỉ duy trì một giao diện duy nhất (Web Client), một cơ chế đóng gói duy nhất (`scripts/build_web.py`), gỡ bỏ hoàn toàn PyInstaller và các tệp build nền tảng. |
| **III. Comprehensive Automated Testing** | **PASS** | Mọi bài kiểm thử lõi (toán, bảng, bố cục, golden master, parity XML) được bảo toàn 100%; CI chạy xanh sạch mà không cần cài thư viện đồ hoạ ảo hay `python3-tk`. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Tầng giao diện Web chỉ tương tác với Python Core qua `BrowserBridge` -> `AppController`. Các module lõi độc lập hoàn toàn với UI. Fidelity Core được cô lập và bảo toàn nguyên vẹn trong `chuviettay/fidelity/`. |
| **Quality Gates & CI Verification** | **PASS** | CI chạy đầy đủ lint (Ruff), test core Python, build web tĩnh, và kiểm thử trình duyệt (Playwright) trước khi tích hợp. |

*Kết luận*: **100% GATES PASS.** Không có bất kỳ vi phạm nào cần miễn trừ.

---

## Project Structure

### Documentation (this feature)

```text
specs/038-web-only-remove-desktop/
├── spec.md                  # Đặc tả tính năng và yêu cầu người dùng
├── plan.md                  # Kế hoạch triển khai chi tiết này
├── research.md              # Phase 0: Phân tích và quyết định kỹ thuật
├── data-model.md            # Phase 1: Mô hình thực thể dữ liệu Web-Only
├── quickstart.md            # Phase 1: Hướng dẫn kiểm chứng và chạy thử
├── contracts/               # Phase 1: Hợp đồng giao diện
│   └── web-only-api-contract.md
├── checklists/
│   └── requirements.md      # Đánh giá chất lượng đặc tả (16/16 Passed)
└── tasks.md                 # Phase 2: Danh sách nhiệm vụ thực thi (sẽ sinh ở /speckit-tasks)
```

### Source Code (repository root)

```text
chuviettay/
├── __init__.py              # Khai báo package và tài liệu kiến trúc web-first
├── config.py                # Cấu hình hằng số hệ thống
├── logging_setup.py         # Ghi log dự phòng
├── paths.py                 # Đường dẫn dữ liệu ứng dụng (đã dọn dẹp sys.frozen)
├── formatting.py            # Định dạng báo cáo (đã dọn nhắc lệnh CLI)
├── browser/                 # Facade cầu nối Web Worker & Pyodide
│   └── bridge.py
├── controller/              # Điều phối nghiệp vụ lõi
│   ├── app_controller.py
│   ├── results.py
│   └── teach_geometry.py
├── document/                # Intermediate Representation (IR)
│   └── ir.py
├── importer/                # Bộ nạp định dạng tài liệu (TXT, Markdown, DOCX)
├── layout/                  # Bố cục văn bản, bảng biểu, công thức toán
├── math/                    # Phân tích cú pháp và xử lý AST toán học
├── model/                   # Kho mẫu, ghép nét, RNG, xử lý tệp .xopp
└── fidelity/                # Lõi chế độ khoá bố cục Word (bảo lưu cho feature Web sau)

webapp/                      # Ứng dụng Web Client (Giao diện duy nhất)
├── index.html               # Trang chính PWA
├── manifest.json            # Web App Manifest
├── css/                     # Giao diện CSS3 hiện đại, hỗ trợ Dark/Light theme
├── js/                      # Logic giao diện, IndexedDB, Canvas, Audio, Web Worker RPC
└── worker.js                # Web Worker nạp Pyodide và giao tiếp với bridge.py

scripts/                     # Kịch bản công cụ hỗ trợ Web
├── build_web.py             # Đóng gói bản web tĩnh sạch vào webapp/dist/
├── serve.mjs                # HTTP Server phát triển cục bộ hỗ trợ header CSP
└── test_golden_pyodide.mjs  # Kiểm thử golden master trong môi trường Node.js / Pyodide

tests/                       # Bộ kiểm thử tự động
├── browser/                 # Kiểm thử môi trường browser bridge
├── e2e/                     # Kiểm thử Playwright E2E cho 3 luồng Web
├── js/                      # Kiểm thử đơn vị frontend JavaScript
└── test_*.py                # Kiểm thử đơn vị và tích hợp Python lõi (không dùng Tkinter)
```

**Structure Decision**:
- Toàn bộ thư mục `chuviettay/view/` và các tệp `chuviettay/gui.py`, `chuviettay/cli.py`, `chuviettay/__main__.py`, `hw_gui.py`, `hw_note.py` bị xoá hoàn toàn khỏi cây thư mục.
- Các tệp cấu hình đóng gói PyInstaller (`hw_gui.spec`, `build_windows.bat`, `build_linux_mac.sh`, `requirements-build.txt`) bị xoá hoàn toàn.
- `webapp/` là giao diện người dùng duy nhất của sản phẩm.

---

## Phase 0: Outline & Research Summary

Đã hoàn thành và ghi nhận trong [research.md](./research.md):
- **Quyết định 1**: Lập danh mục chính xác 16 tệp/thư mục Desktop & CLI cần xoá bỏ.
- **Quyết định 2**: Lập kế hoạch xoá 7 tệp kiểm thử thuần Desktop/CLI, dọn 4 điểm import ẩn trong bộ test lõi (`test_logging.py`, `test_teach_geometry.py`, `test_txt_unified_pipeline.py`, `test_paths_logging.py`), chuyển giao 2 bài test logic sang `test_formatting.py`/`test_letter_assembly.py`, và đổi tên `test_web_cli_parity.py` thành `test_web_controller_parity.py`.
- **Quyết định 3**: Gỡ bỏ `python3-tk` và `xvfb` khỏi CI, loại bỏ `pyinstaller` và console scripts khỏi `pyproject.toml`.
- **Quyết định 4**: Dọn dẹp mã chết trong `paths.py` và thông điệp nhắc lệnh CLI trong `formatting.py`; đồng thời xác lập quy tắc bất khả xâm phạm đối với chuỗi chú thích XML `layout/engine.py:1063` để bảo vệ tuyệt đối mã băm Golden Master.
- **Quyết định 5**: Bảo lưu nguyên vẹn 100% mã nguồn và test của `chuviettay/fidelity/`.
- **Quyết định 6**: Cập nhật tài liệu `README.md` và `CHANGELOG.md` cho kiến trúc Web-only và hướng dẫn người dùng chuyển đổi kho mẫu.

---

## Phase 1: Design & Contracts Summary

Đã hoàn thành và ghi nhận trong:
- [data-model.md](./data-model.md): Định nghĩa chi tiết thực thể Kho mẫu cá nhân (`.json.gz`), cấu trúc trao đổi dữ liệu Web Bridge (`WriteOptionsPayload`, `WriteResultPayload`, `BankStatsPayload`), và danh mục các thực thể đã gỡ bỏ.
- [contracts/web-only-api-contract.md](./contracts/web-only-api-contract.md): Hợp đồng giao diện công khai qua `BrowserBridge`, bản ghi gỡ bỏ CLI/Desktop và cam kết bảo toàn tính toàn vẹn của lõi engine.
- [quickstart.md](./quickstart.md): Hướng dẫn 5 kịch bản kiểm chứng tự động (kiến trúc, kiểm thử lõi, golden master, build web, Playwright E2E) và luồng kiểm chứng thủ công cho người dùng chuyển đổi kho mẫu.

---

## Complexity Tracking

*Không có vi phạm hay ngoại lệ kiến trúc nào.*
