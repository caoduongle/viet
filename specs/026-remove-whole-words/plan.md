# Implementation Plan: Loại Bỏ Từ Nguyên Khối, Chuyển Sang Thuần Ghép Ký Tự

**Branch**: `026-remove-whole-words` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/026-remove-whole-words/spec.md`

## Summary

Loại bỏ hoàn toàn các thành phần, cấu trúc và luồng xử lý liên quan đến mẫu từ nguyên khối (`bank.words`, `substitute`, `seed_words`, `teach_word`, `pick_calib_word`) trong toàn bộ dự án ChuVietTay. Chuyển đổi bộ máy kết xuất văn bản (`Writer`, `FidelityEngine`) sang cơ chế thuần ghép ký tự (`assemble_word`), chuẩn hóa quy trình dạy chữ chỉ tiếp nhận ký tự đơn, chuyển đổi hiệu chỉnh cỡ tay sang ký tự mốc ổn định (`pick_calibration_char`), và tinh gọn giao diện Desktop GUI cùng Web Client để tập trung hoàn toàn vào kho ký tự.

## Technical Context

**Language/Version**: Python 3.10+, JavaScript (ES2022)

**Primary Dependencies**: Tkinter (Desktop GUI), Pyodide (WebAssembly Web Worker), Playwright (Web E2E tests), pytest (Unit & Integration tests)

**Storage**: File nén gzip chứa JSON (`.json.gz`), hỗ trợ IndexedDB lưu trữ ngoại tuyến trên trình duyệt qua Web Locks

**Testing**: `pytest`, `pytest-timeout`, `pytest-cov`, Playwright test runner

**Target Platform**: Windows, Linux, macOS (CLI & Tkinter GUI); Trình duyệt web hiện đại hỗ trợ WASM/Worker (Chrome, Firefox, Safari, Edge)

**Project Type**: Desktop Application + Web Client + Python Package CLI

**Performance Goals**:
- Thời gian ghép một từ bằng `assemble_word`: $< 2\text{ ms}$
- Độ trễ lưu mẫu hoãn (debounced save): $< 50\text{ ms}$ trên UI
- Thời gian khởi tạo/mở kho mẫu: $< 200\text{ ms}$

**Constraints**:
- Bảo toàn nguyên vẹn trường dữ liệu lịch sử `words` trong file `.json.gz` cũ (Zero Data Loss), nhưng cô lập hoàn toàn khỏi luồng xử lý mới.
- Không gây hồi quy (regression) cho hệ thống test hiện hữu (1126+ tests).

**Scale/Scope**:
- ~300 ký tự đơn lẻ (chữ cái Latin/tiếng Việt, 5 dấu thanh rời, 10 chữ số, dấu câu, ký hiệu toán học & Hy Lạp).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Loại bỏ mã nguồn thừa kế (dead/legacy code) như `substitute()`, `self.tl`, `seed_words.py`, giúp mã nguồn tinh gọn và dễ bảo trì.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Loại bỏ mô hình kết xuất 2 tầng phức tạp (vừa tra từ vừa ghép ký tự); hợp nhất thành 1 luồng ghép ký tự duy nhất, minh bạch và tất định.
- [x] **III. Comprehensive Automated Testing**: Tất cả các hàm chuyển đổi đều có hợp đồng rõ ràng và có kịch bản kiểm thử trong `quickstart.md` cùng bộ test tự động.
- [x] **IV. Loose Coupling & High Cohesion**: Tách biệt rõ ràng giữa danh mục ký tự (`char_catalog`), mô hình lưu trữ (`bank`), bộ máy kết xuất (`writer`), và giao diện điều khiển (`controller`/`view`).

*Gate Status*: **PASSED**

## Project Structure

### Documentation (this feature)

```text
specs/026-remove-whole-words/
├── spec.md              # Đặc tả tính năng
├── checklists/
│   └── requirements.md  # Bảng kiểm tra chất lượng đặc tả
├── plan.md              # Kế hoạch thực hiện (file này)
├── research.md          # Nghiên cứu kiến trúc & các quyết định kỹ thuật
├── data-model.md        # Mô hình dữ liệu thực thể
├── quickstart.md        # Hướng dẫn kiểm thử và xác thực nhanh
└── contracts/           # Các bản giao kèo giao diện & API
    ├── writer-assembly-contract.md
    ├── controller-calibration-contract.md
    └── teach-queue-contract.md
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py             # Loại bỏ duyệt words trong rebuild(), cập nhật has_word()
│   ├── writer.py           # Thuần ghép ký tự assemble_word, bỏ b.words & substitute
│   ├── text_utils.py       # Cập nhật missing_letters_ranked, bỏ lọc theo bank_words
│   ├── char_catalog.py     # Danh mục ký tự tập trung chuẩn hóa
│   ├── xopp.py             # Thay pick_calib_word bằng pick_calibration_char
│   └── seed_words.py       # Đánh dấu deprecated, chuyển hướng sang char_catalog
├── controller/
│   └── app_controller.py   # Thay pick_calibration_word, tinh gọn bank_size, bỏ teach_word
├── fidelity/
│   └── engine.py           # Tạo missing_grid theo ký tự đơn thay vì theo từ
├── browser/
│   └── bridge.py           # Đồng bộ API sang pick_calibration_char và teach_char
├── cli.py                  # Cập nhật các lệnh check, stats, drop sang thuần ký tự
└── view/
    ├── teach_tab.py        # Tự động bóc tách chuỗi, dùng pick_calibration_char
    ├── bank_tab.py         # Hiển thị danh sách ký tự thay vì _all_words
    └── word_canvas.py      # Đổi tên logic sang char canvas

webapp/
├── index.html              # Bỏ nút lọc "Từ vựng (words)"
├── js/
│   ├── bank.js             # Mặc định danh mục 'letters', bỏ nạp 'list_words'
│   ├── teach.js            # Bóc tách ký tự, gọi pick_calibration_char, saveChar()
│   └── worker/
│       └── py-worker.js    # Cập nhật ánh xạ gọi Worker sang API ký tự mới
```

**Structure Decision**: Giữ nguyên kiến trúc mô-đun phân tầng chuẩn mực của dự án, chỉ can thiệp tinh chỉnh luồng dữ liệu bên trong các mô-đun để loại bỏ triệt để từ nguyên khối.

## Complexity Tracking

> Không có vi phạm kiến trúc nào. Thiết kế này giúp giảm độ phức tạp của toàn hệ thống (KISS).
