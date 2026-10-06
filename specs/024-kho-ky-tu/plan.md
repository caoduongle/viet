# Implementation Plan: Thuần Ký Tự và Nạp Lưới Tạo Kho Mẫu

**Branch**: `024-kho-ky-tu` | **Date**: 2026-10-06 | **Spec**: [specs/024-kho-ky-tu/spec.md](file:///d:/viet/app/specs/024-kho-ky-tu/spec.md)

**Input**: Feature specification from `specs/024-kho-ky-tu/spec.md`

## Summary

Chuyển đổi toàn diện hệ thống từ dạy/lưu/dùng mẫu theo TỪ sang **thuần KÝ TỰ** và nạp file lưới tập viết `.xopp` để tạo kho mẫu:
1. **R1**: Bỏ hoàn toàn dạy/lưu/dùng mẫu theo TỪ; kho chỉ gồm `letters`, `digits`, `punct`, `symbols`, `marks`. Khi viết văn bản luôn tự động ghép từ ký tự (luôn bật assemble, không còn cờ `--assemble`). Bảo toàn trường `words` của kho cũ để không làm mất dữ liệu người dùng.
2. **R2**: Thêm tính năng đọc file lưới `.xopp` tạo kho ký tự trên Web, Desktop GUI và CLI; sửa triệt để lỗi tính `lsb/rsb` từ lề ô khiến chữ bị giãn 10 lần (F2); đảm bảo idempotent và sinh báo cáo `GridImportResult`.
3. **R3**: Nút "Bộ ký tự…" thay cho nút "Bộ tối thiểu" và "Từ thông dụng" (xóa 700 từ SEED).
4. **R4**: Rà soát và sửa triệt để các lỗi nền F1–F13.

## Technical Context

**Language/Version**: Python 3.10+ & JavaScript ES2022 (Pyodide Worker)  
**Primary Dependencies**: Không thêm thư viện ngoài mới. Dùng `gzip`, `xml.etree.ElementTree`, `unicodedata`, `dataclasses`.  
**Storage**: File nén gzip JSON (`kho_mau.json.gz`), file `.xopp` (gzipped XML).  
**Testing**: `pytest`, `pytest-timeout`, Playwright E2E (`@playwright/test`).  
**Target Platform**: Web Client (WASM/Pyodide), Desktop GUI (Tkinter), Cross-platform CLI.  
**Project Type**: Python core library + Web Client + Desktop App.  
**Performance Goals**: Nạp file lưới 140–500 ô trong < 500ms; không gây treo Pyodide worker.  
**Constraints**:
- Tuân thủ nghiêm ngặt mô hình kiến trúc MVC (`tests/test_architecture.py`).
- Không đổi hằng số `config.py` (`CW, CH, BASE, COLS, ROWS, MXT, MYT, TONES`).
- Không xoá dữ liệu người dùng (kho cũ có `words` vẫn mở và lưu được).
- Mỗi pha kết thúc bằng test xanh và 1 commit với thông điệp chuẩn tiếng Việt có tag `[PX]`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Cấu trúc module rõ ràng (`char_catalog.py`, `xopp.py`), mã nguồn có docstring đầy đủ.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Bỏ cơ chế dạy từ phức tạp, dùng chung 1 đường nạp ký tự và ghép từ thống nhất.
- [x] **III. Comprehensive Automated Testing**: Làm "đỏ trước, xanh sau" cho F2, F3, F4, F7; bổ sung test đơn vị và Playwright E2E.
- [x] **IV. Loose Coupling & High Cohesion**: Phân tách rõ ràng giữa Model (`import_char_grid`), Controller (`AppController`), và View/Bridge.

## Project Structure

### Documentation (this feature)

```text
specs/024-kho-ky-tu/
├── spec.md              # Đặc tả yêu cầu chi tiết
├── plan.md              # Kế hoạch triển khai kiến trúc (file này)
├── research.md          # Kết quả nghiên cứu & giải pháp thiết kế
├── data-model.md        # Mô hình thực thể & luật phân loại
├── quickstart.md        # Hướng dẫn kiểm thử & xác minh
├── contracts/           # Hợp đồng API Controller & CLI
└── tasks.md             # Danh sách task triển khai chi tiết
```

### Source Code Layout

```text
chuviettay/
├── model/
│   ├── char_catalog.py   # [MỚI] Danh mục bộ ký tự chuẩn (co_ban, toan_hy_lap, ...)
│   ├── xopp.py           # Nạp lưới import_char_grid, GridImportResult, sửa F2
│   ├── bank.py           # Quản lý kho mẫu ký tự, bảo toàn words cũ
│   ├── calibration.py    # pick_calib_char thay cho tra words
│   ├── text_utils.py     # classify_char phân loại ký tự chuẩn
│   └── writer.py         # Luôn tự động assemble_word, bỏ cờ assemble
├── controller/
│   └── app_controller.py # teach_char, import_grid, get_char_catalog
├── browser/
│   └── bridge.py         # Endpoints import_grid, teach_char, get_char_catalog
├── view/                 # Tkinter Desktop GUI
│   ├── teach_tab.py      # Nút "Bộ ký tự…", "Nạp lưới", bỏ dạy từ
│   ├── bank_tab.py       # Bỏ tab từ, chỉ quản lý ký tự
│   └── write_tab.py      # Bỏ checkbox ghép chữ
├── cli.py                # Lệnh grid (--set), learn (--grid), write
└── tao_luoi_day_du.py    # Dùng char_catalog.py làm nguồn chung
webapp/
├── index.html            # Cập nhật menu/nút nạp lưới và bộ ký tự
├── js/
│   ├── teach.js          # Giao diện hàng đợi ký tự, import lưới
│   ├── bank.js           # Bỏ bảng từ, chỉ hiển thị ký tự
│   └── write.js          # Viết luôn ghép chữ
└── js/worker/
    └── py-worker.js      # Chuyển tiếp bridge payload nạp lưới
tests/
├── helpers.py            # fill_grid_with_ink giả lập nét viết
├── test_char_catalog.py  # Test các bộ ký tự chuẩn
├── test_grid_import.py   # Test nạp lưới, idempotent, F2 bearing
└── e2e/
    └── grid-import.spec.ts # Test E2E Playwright trên trình duyệt
```

---

## Phases & Execution Strategy

### Pha P0: Chuẩn bị & Test Tái Hiện Lỗi (Đỏ Trước)
- Viết test helper `tests/helpers.py` (`fill_grid_with_ink`).
- Viết test tái hiện: F2 (lỗi giãn chữ do bearing mép ô), F3 (thiếu danh mục chuẩn), F4 (phân loại ký tự), F7 (thiếu ký tự mốc calib).
- Cam kết: `test(grid): add test helpers and repro failing tests [P0]`.

### Pha P1: Lõi Domain Model
- Tạo `chuviettay/model/char_catalog.py`.
- Bổ sung `chuviettay/model/text_utils.py: classify_char`.
- Cập nhật `chuviettay/model/xopp.py`: cài đặt `import_char_grid` trả về `GridImportResult`, sửa triệt để F2.
- Cập nhật `calibration.py: pick_calib_char`.
- Cập nhật `bank.py`: hỗ trợ phân loại mới, bảo toàn `words` cũ.
- Cam kết: `feat(grid): implement char catalog, classify_char, and grid importer [P1]`.

### Pha P2: Writer & Bỏ Cờ Ghép Chữ
- Sửa `writer.py`: mặc định luôn ghép từ ký tự (`assemble_word`), loại bỏ cờ `--assemble`, bổ sung guard bearing $0 \le bearing \le 0.3 \times xh$.
- Cập nhật tính toán missing tokens chỉ dựa trên ký tự.
- Cam kết: `feat(writer): enforce letter assembly and remove word model [P2]`.

### Pha P3: Controller, Bridge & CLI
- Thêm `import_grid`, `teach_char`, `get_char_catalog` vào `AppController`.
- Cập nhật `browser/bridge.py` serialize `GridImportResult`.
- Cập nhật `cli.py`: lệnh `grid --set`, `learn --grid`.
- Cam kết: `feat(controller): add char grid controller and bridge endpoints [P3]`.

### Pha P4: Desktop GUI (Tkinter)
- Cập nhật `teach_tab.py`: nút "Bộ ký tự…", nút "Nạp file lưới…", bỏ tab/nút dạy từ.
- Cập nhật `bank_tab.py` và `write_tab.py`.
- Cam kết: `feat(gui): update desktop gui to char-only model [P4]`.

### Pha P5: Web Client (Pyodide)
- Cập nhật `index.html` và `webapp/js/teach.js`, `webapp/js/bank.js`, `webapp/js/write.js`, `py-worker.js`.
- Thêm modal nạp file lưới và dialog chọn bộ ký tự.
- Cam kết: `feat(web): update web client for char bank and grid upload [P5]`.

### Pha P6: Test Suite Toàn Diện & E2E
- Cập nhật toàn bộ unit test suite hiện có thích ứng với mô hình mới.
- Bổ sung `tests/e2e/grid-import.spec.ts`.
- Chạy toàn bộ pytest và playwright test.
- Cam kết: `test: add comprehensive test suite for char bank [P6]`.

### Pha P7: Nghiệm Thu & Tài Liệu
- Tạo script nghiệm thu đầu cuối `tools/accept_char_bank.py`.
- Cập nhật `README.md` và `CHANGELOG.md`.
- Cam kết: `docs: update documentation and acceptance report [P7]`.
