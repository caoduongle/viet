# Phase 0 Research: Chuyển sang sản phẩm chỉ có Web — Loại bỏ ứng dụng Desktop & CLI

**Feature**: `038-web-only-remove-desktop`  
**Date**: 2026-10-13  
**Status**: Hoàn thành  

---

## 1. Danh sách tệp Desktop và CLI cần loại bỏ hoàn toàn

### Quyết định (Decision)
Loại bỏ 100% các thành phần mã nguồn, tệp khởi chạy, kịch bản đóng gói và tệp cấu hình chỉ phục vụ Desktop Tkinter và CLI:
- **Thư mục giao diện Tkinter**: `chuviettay/view/` (toàn bộ 8 tệp: `__init__.py`, `app_window.py`, `bank_tab.py`, `dialogs.py`, `teach_tab.py`, `theme.py`, `word_canvas.py`, `write_tab.py`).
- **Điểm vào Desktop & CLI**:
  - `chuviettay/gui.py`
  - `chuviettay/cli.py`
  - `chuviettay/__main__.py`
  - `hw_gui.py`
  - `hw_note.py`
- **Cấu hình và kịch bản đóng gói PyInstaller**:
  - `hw_gui.spec`
  - `build_windows.bat`
  - `build_linux_mac.sh`
  - `requirements-build.txt`
- **Cấu hình package**:
  - Gỡ bỏ mục `[project.scripts]` (`hw-note`, `hw-gui`) trong `pyproject.toml`.
  - Gỡ bỏ `pyinstaller>=6` khỏi `[project.optional-dependencies] dev` trong `pyproject.toml`.

### Cơ sở lựa chọn (Rationale)
- Người dùng đã chỉ định rõ ràng qua quyết định làm rõ Q1: B (loại bỏ hoàn toàn công cụ dòng lệnh) và yêu cầu ban đầu (loại bỏ phần desktop, chỉ làm cho web).
- Web Client đã hỗ trợ đầy đủ 3 luồng chức năng chính (Viết chữ, Dạy chữ, Quản lý kho mẫu) thông qua WebAssembly / Pyodide, IndexedDB và PWA.
- Việc gỡ bỏ triệt để các file trên loại bỏ hơn 3.000 dòng mã thừa, xóa bỏ tình trạng trùng lặp công sức phát triển giữa Desktop và Web.

### Các phương án khác đã xem xét (Alternatives considered)
- *Giữ CLI cho lập trình viên (Option A ở câu hỏi Q1)*: Bị từ chối vì làm phân mảnh mục tiêu tập trung vào Web, duy trì chi phí kiểm thử CLI và tạo ra các lối vào thứ cấp không đồng bộ với trải nghiệm Web Client.
- *Giữ lớp mỏng `chuviettay/__main__.py`*: Bị từ chối vì sản phẩm không còn phân phối như một CLI package; việc chạy cục bộ cho Web được thực hiện thống nhất qua `python scripts/build_web.py` và `node scripts/serve.mjs`.

---

## 2. Chiến lược xử lý bộ kiểm thử (Tests Suite Refactor)

### Quyết định (Decision)
1. **Loại bỏ các tệp kiểm thử thuần Desktop và CLI**:
   - `tests/test_gui.py`
   - `tests/test_gui_document.py`
   - `tests/test_gui_resilience.py`
   - `tests/test_theme.py`
   - `tests/test_word_canvas.py`
   - `tests/test_cli.py`
   - `tests/test_cli_format.py`
2. **Dọn dẹp các bài test chứa import Desktop/CLI ẩn trong bộ kiểm thử lõi**:
   - `tests/test_logging.py`: Xoá bỏ hàm `test_report_error_with_no_log_path` (do import `chuviettay.view.dialogs` và `tkinter.messagebox`). Giữ nguyên toàn bộ các bài test `logging_setup` còn lại.
   - `tests/test_teach_geometry.py`: Xoá bỏ hàm `test_view_reexport_matches` (do import `chuviettay.view.word_canvas`). Giữ nguyên toàn bộ các bài test hình học và lọc nét.
   - `tests/test_txt_unified_pipeline.py`: Xoá bỏ hoặc viết lại hàm `test_cli_write_txt_file_uses_document_ir` (do gọi `from chuviettay.cli import main`) sang gọi trực tiếp `AppController.write_document()`.
   - `tests/test_paths_logging.py`: Xoá bỏ hàm `test_duong_dan_mac_dinh_khi_da_dong_goi_dung_thu_muc_cua_file_exe` (do kiểm tra nhánh `sys.frozen` của PyInstaller đã gỡ).
3. **Di chuyển và bảo lưu kiểm thử logic nghiệp vụ không phụ thuộc GUI/CLI**:
   - `tests/test_letter_gui_cli.py`: Các bài test kiểm tra CLI (`test_cli_parser_assemble_flag`, `test_cli_stats_command_with_letters`) được gỡ bỏ; các bài test kiểm tra logic ghép chữ và định dạng (`test_bank_stats_contains_letters`, `test_write_report_lines_with_assembled_and_missing`) được chuyển vào `tests/test_formatting.py` hoặc `tests/test_letter_assembly.py`. Tệp `test_letter_gui_cli.py` sau đó được xoá.
   - `tests/test_web_cli_parity.py`: Đổi tên thành `tests/test_web_controller_parity.py`. Tệp này thực chất kiểm tra tính tương đương từng byte (byte-exact parity) giữa `BrowserBridge` và `AppController`, hoàn toàn không phụ thuộc CLI. Giữ nguyên 100% logic so sánh XML XOPP.
   - `tests/test_formatting.py`: Đồng bộ hoá các chuỗi kỳ vọng với các cập nhật thông điệp mới trong `chuviettay/formatting.py` (loại bỏ `python hw_note.py learn ...` và `--seed`).
4. **Cập nhật quy tắc kiến trúc (`tests/test_architecture.py`)**:
   - Cấm hoàn toàn `tkinter` trên toàn bộ repository (không ngoại lệ).
   - Xóa bỏ danh sách `UI_AND_ENTRY = ["chuviettay.view", "chuviettay.cli", "chuviettay.gui"]`.
   - Bổ sung assertion đảm bảo các module `chuviettay.view`, `chuviettay.cli`, `chuviettay.gui` không còn tồn tại trong kho mã.
   - Xóa bỏ các test kiểm tra `hw_note.py` và `hw_gui.py`.
5. **Dọn dẹp fixtures Tkinter trong `tests/conftest.py`**:
   - Xóa bỏ các hàm/fixtures: `is_tk_usable()`, `tk_root`, `_safe_gui_dialogs`, `pytest_collection_modifyitems` (đoạn lọc marker gui).

### Cơ sở lựa chọn (Rationale)
- Kiểm thử phải phản ánh kiến trúc thực tế. Các bài test cho tính năng đã gỡ bỏ phải được gỡ bỏ để tránh test xanh giả tạo hoặc lỗi test do thiếu môi trường.
- Các bài kiểm thử logic cốt lõi (ghép từ, parity XML) được bảo toàn nguyên vẹn để không làm suy giảm độ bao phủ của engine.

### Các phương án khác đã xem xét (Alternatives considered)
- *Giữ lại các file test GUI và đánh dấu `@pytest.mark.skip`*: Bị từ chối vì tạo mã chết, gây hiểu nhầm về độ bao phủ thực tế và vi phạm Nguyên tắc I & II của Hiến chương dự án.

---

## 3. Tối ưu hoá quy trình CI (`.github/workflows/ci.yml`)

### Quyết định (Decision)
- Trong job `test-core`:
  - Gỡ bỏ hoàn toàn bước cài đặt gói hệ thống `python3-tk xvfb`.
  - Thay đổi lệnh chạy pytest từ `xvfb-run -a python -m pytest ...` thành `python -m pytest -vv -s --timeout=30 -m "not benchmark"`.
- Job `web-client` giữ nguyên và bổ sung bước kiểm tra toàn diện: build web tĩnh, chạy kiểm thử Playwright E2E cho 100% các luồng người dùng trên Web.

### Cơ sở lựa chọn (Rationale)
- Không còn bất kỳ mã Python nào sử dụng Tkinter, việc cài đặt `python3-tk` và khởi chạy `xvfb-run` là hoàn toàn dư thừa.
- Giảm thời gian chạy CI trên Ubuntu runner khoảng 30-45 giây mỗi lượt chạy, tránh lỗi treo màn hình ảo (Xvfb hang).

### Các phương án khác đã xem xét (Alternatives considered)
- *Giữ nguyên `xvfb-run` phòng hờ*: Bị từ chối vì vi phạm nguyên tắc YAGNI và làm tăng thời gian/nguy cơ lỗi không cần thiết của CI pipeline.

---

## 4. Dọn dẹp mã chết và thông điệp người dùng trong Lõi (Core Engine)

### Quyết định (Decision)
1. **`chuviettay/paths.py`**:
   - Loại bỏ logic xử lý tệp đóng gói `sys.frozen` và `sys.executable`.
   - Loại bỏ các hàm `load_user_config` và `save_user_config` (vốn chỉ phục vụ lưu theme cho Desktop Tkinter).
   - Giữ nguyên `app_base_dir()`, `user_data_dir()`, `default_bank_path()` và `user_log_dir()` phục vụ chạy cục bộ và ghi log.
2. **`chuviettay/formatting.py`**:
   - Cập nhật hàm `write_report_lines()`:
     - Dòng 50-51: Xóa câu nhắc `python hw_note.py learn ...`, thay bằng thông báo nạp tệp lưới vào ứng dụng Web.
     - Dòng 61: Xóa gợi ý tham số dòng lệnh `--seed`, thay bằng hướng dẫn nhập hạt giống (seed) vào ô tùy chọn trên giao diện Web.
   - Giữ lại hoặc đổi tên `format_stats_gui` thành `format_stats_text` dùng cho báo cáo thống kê chuỗi thuần.
3. **BẢO TOÀN BẤT KHẢ XÂM PHẠM Golden Master XML (`chuviettay/layout/engine.py:1063`)**:
   - Chuỗi chú thích `"Từ/ký hiệu CHƯA có mẫu: viết mỗi từ/ký hiệu vào ô theo 4 vạch kẻ mốc (chuẩn hw3), rồi Ctrl+S và chạy: python hw_note.py learn %s"` trong `chuviettay/layout/engine.py:1063` được ghi trực tiếp vào nội dung tệp `_thieu.xopp`.
   - Vì mã băm SHA-256 của `_thieu.xopp` được kiểm tra byte-exact trong `test_golden_master_real_path.py` (`GOLDEN_REAL["markdown_list"]["thieu"]` và `test_real_path_stable_variants`), chuỗi này **BẮT BUỘC GIỮ NGUYÊN** để không phá vỡ tính tương thích Golden Master.
   - Tương tự, thuộc tính XML `<xournal creator="hw_note" fileversion="4">` trong `xopp.py` và `webapp/js/paper.js` là hằng số định dạng Xournal++, **BẮT BUỘC GIỮ NGUYÊN**.
4. **`chuviettay/__init__.py`**:
   - Cập nhật tài liệu docstring của package: mô tả kiến trúc web-first (Web Client kết nối qua BrowserBridge và AppController), loại bỏ mô tả về view Tkinter và CLI.

### Cơ sở lựa chọn (Rationale)
- Đảm bảo người dùng và lập trình viên không gặp các thông điệp dẫn dắt đến các lệnh hoặc giao diện đã bị xoá (FR-011).
- Mã không còn người dùng (dead code) cần được gỡ bỏ để đảm bảo tính tinh gọn (FR-010).

---

## 5. Bảo lưu chế độ Fidelity (`chuviettay/fidelity/`)

### Quyết định (Decision)
- Giữ nguyên 100% mã nguồn trong `chuviettay/fidelity/` (`engine.py`, `importer.py`, `models.py`, `renderer.py`).
- Giữ nguyên các bài kiểm thử liên quan (`test_docx_fidelity.py`, `test_fidelity_pdf_first.py`, `test_fidelity_whiten_math.py`, `test_importer_fidelity.py`).
- Feature 038 chỉ gỡ bỏ phần UI kết nối tới Fidelity trên Desktop (`chuviettay/view/write_tab.py` - đã được bao gồm trong việc xoá `chuviettay/view/`).
- Chuẩn bị sẵn hợp đồng và cấu trúc cho feature tiếp theo đưa tính năng Fidelity lên Web Client.

### Cơ sở lựa chọn (Rationale)
- Thực hiện chính xác quyết định làm rõ Q2: C của người dùng.
- Engine Fidelity độc lập hoàn toàn với Tkinter và CLI (đã kiểm chứng qua AST / grep), việc giữ lại không gây bất kỳ tác dụng phụ nào cho bản build Web hay CI hiện tại.

---

## 6. Hướng dẫn di chuyển dữ liệu (Migration Guide in README)

### Quyết định (Decision)
Cập nhật `README.md`:
- Đặt Web Client là sản phẩm duy nhất.
- Hướng dẫn chạy cục bộ (`npm ci` -> `python scripts/build_web.py` -> `node scripts/serve.mjs`).
- Thêm mục rõ ràng: **"Chuyển đổi từ bản Desktop cũ sang Web Client"**:
  - Hướng dẫn người dùng Desktop tìm tệp kho cá nhân mặc định (`chu_cua_ban.json.gz`).
  - Mở Web Client, vào tab **"Kho mẫu"** → bấm **"Nhập kho mẫu (.json.gz)"** và chọn tệp trên máy.
  - Giải thích rằng toàn bộ mẫu chữ, chữ số, dấu câu, ký hiệu và hồ sơ cỡ tay được giữ nguyên vẹn 100%.
- Cập nhật `CHANGELOG.md` ghi nhận việc loại bỏ Desktop & CLI như một breaking change (phiên bản v2.1.0 hoặc tương đương).
