# Contract: Giao diện và Điểm vào Web-Only (Web-Only API Contract)

**Contract ID**: `CTR-038-WEB-ONLY-API`  
**Feature**: `038-web-only-remove-desktop`  
**Date**: 2026-10-13  
**Status**: Active  

---

## 1. Phạm vi và Ranh giới công khai (Public Interface Boundary)

Kể từ Feature 038, sản phẩm Chữ Viết Tay chỉ có **MỘT** ranh giới giao tiếp công khai duy nhất:
- **Tầng ngoài**: Ứng dụng Web tĩnh client-side (`webapp/`).
- **Giao thức kết nối**: Web Worker RPC (truyền thông điệp qua `postMessage` giữa `worker.js` và `BrowserBridge` trong Pyodide).
- **Lớp Facade Python**: `chuviettay.browser.bridge.BrowserBridge`.

Toàn bộ các điểm vào dòng lệnh (`CLI`) và giao diện đồ hoạ máy tính để bàn (`Tkinter GUI`) bị xóa bỏ hoàn toàn.

---

## 2. Đặc tả giao diện Facade `BrowserBridge`

Mọi tương tác từ Web Client xuống lõi Python PHẢI đi qua lớp `BrowserBridge` (đặt tại `chuviettay/browser/bridge.py`). Không một module JavaScript nào được phép gọi trực tiếp vào `AppController` hay các module con bên trong `model/`, `layout/`, `math/`.

### 2.1. Quản lý kho mẫu (Bank Management)

| Phương thức | Tham số đầu vào | Kết quả trả về | Mô tả |
|---|---|---|---|
| `load_bank(bank_bytes: bytes)` | Mảng byte của tệp `.json.gz` | `{"ok": bool, "stats": dict, "error": str?}` | Nạp dữ liệu kho mẫu vào bộ nhớ ảo. |
| `export_bank()` | Không | `{"ok": bool, "bank_bytes": str (base64), "error": str?}` | Xuất toàn bộ kho mẫu hiện tại thành chuỗi base64 của file `.json.gz`. |
| `get_stats()` | Không | `{"ok": bool, "stats": dict, "error": str?}` | Trả về thống kê số lượng mẫu nét, ký tự, dấu thanh. |

### 2.2. Kết xuất văn bản và tài liệu (Writing & Rendering)

| Phương thức | Tham số đầu vào | Kết quả trả về | Mô tả |
|---|---|---|---|
| `write_text(text: str, options: dict)` | `text`: Chuỗi văn bản thuần hoặc Markdown; `options`: Dict tuỳ chọn viết | `{"ok": bool, "xopp_bytes": str (base64), "n_lines": int, "n_strokes": int, "n_tokens": int, "n_missing_tokens": int, "missing_tokens": list, "assembled_words": list, "warnings": list, "seed_used": int, "error": str?}` | Sinh tệp `.xopp` từ văn bản theo các tùy chọn nét viết và hạt giống. |
| `write_document(content: str, filename: str, options: dict)` | `content`: Nội dung tài liệu; `filename`: Tên tệp có đuôi (`.md`, `.txt`); `options`: Dict tuỳ chọn | Cấu trúc giống `write_text` | Nhận diện định dạng tài liệu, phân tích AST và tạo tệp `.xopp`. |

### 2.3. Dạy chữ và hiệu chỉnh (Teaching & Calibration)

| Phương thức | Tham số đầu vào | Kết quả trả về | Mô tả |
|---|---|---|---|
| `teach_letter(letter: str, strokes: list, w: float)` | `letter`: Ký tự; `strokes`: Tọa độ các nét; `w`: Độ rộng chữ | `{"ok": bool, "stats": dict, "error": str?}` | Thêm mẫu nét cho một chữ cái đơn. |
| `teach_word(word: str, strokes: list, w: float)` | `word`: Từ; `strokes`: Nét; `w`: Độ rộng | `{"ok": bool, "stats": dict, "error": str?}` | Thêm mẫu nét cho từ. |
| `delete_sample(key: str, index: int)` | `key`: Ký tự/từ cần xóa; `index`: Thứ tự mẫu | `{"ok": bool, "error": str?}` | Xóa một mẫu cụ thể với tombstone bảo vệ. |
| `batch_delete(targets: list)` | Danh sách `{key: str, index: int}` | `{"ok": bool, "deleted_count": int, "error": str?}` | Xóa hàng loạt mẫu nét. |

---

## 3. Bản ghi xóa bỏ giao diện (Interface Deprecation & Deletion Matrix)

| Giao diện bị gỡ bỏ | Tệp bị gỡ | Trạng thái | Hành vi thay thế |
|---|---|---|---|
| `CLI: hw-note / chuviettay.cli` | `chuviettay/cli.py`, `hw_note.py` | **ĐÃ XÓA** | Chuyển toàn bộ thao tác viết chữ, xem thống kê sang Web Client. |
| `CLI Console Script` | `pyproject.toml` (`[project.scripts]`) | **ĐÃ XÓA** | Không hỗ trợ chạy CLI qua pip install. |
| `Desktop GUI: hw-gui / chuviettay.gui` | `chuviettay/gui.py`, `hw_gui.py` | **ĐÃ XÓA** | Mở Web Client trong trình duyệt hoặc cài đặt PWA desktop. |
| `Desktop View Package` | `chuviettay/view/*` (8 tệp) | **ĐÃ XÓA** | Sử dụng Web UI components trong `webapp/`. |
| `PyInstaller Desktop Builds` | `hw_gui.spec`, `build_windows.bat`, `build_linux_mac.sh` | **ĐÃ XÓA** | Đóng gói Web tĩnh bằng `python scripts/build_web.py`. |

---

## 4. Cam kết bảo toàn (Preservation Guarantees)

1. **Lõi xử lý chung (Core Engine)**:
   - `chuviettay/model/` (Bank, Composer, Writer, ScopedRNG, XOPP, TextUtils) giữ nguyên vẹn 100%.
   - `chuviettay/layout/` (DocumentLayoutEngine, MathLayout, TableLayout) giữ nguyên vẹn 100%.
   - `chuviettay/document/` (IR nodes) và `chuviettay/importer/` giữ nguyên vẹn 100%.
   - Kết quả xuất ra định dạng `.xopp` với cùng hạt giống và tùy chọn giữ nguyên tính xác thực từng byte (byte-exact bit reproducibility).
2. **Lõi Fidelity (`chuviettay/fidelity/`)**:
   - Toàn bộ module trong `chuviettay/fidelity/` được bảo lưu nguyên vẹn trong kho mã.
   - Các bài kiểm thử `test_docx_fidelity.py`, `test_fidelity_pdf_first.py`, `test_fidelity_whiten_math.py`, `test_importer_fidelity.py` tiếp tục được bảo trì xanh trong CI.
