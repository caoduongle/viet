# Implementation Plan: Đồng Bộ Mô Hình Char-First, Khắc Phục Dấu Thanh & Sửa Lỗi CI Toàn Diện

**Branch**: `028-char-first-alignment-and-ci-repair` | **Date**: 2026-10-07 | **Spec**: [spec.md](file:///d:/viet/app/specs/028-char-first-alignment-and-ci-repair/spec.md)

**Input**: Feature specification from `specs/028-char-first-alignment-and-ci-repair/spec.md`

---

## Summary

Triển khai đồng bộ toàn diện mô hình học và ghép ký tự (char-first), khắc phục các lỗi nghiệp vụ về dấu thanh và khôi phục trạng thái CI xanh 100%:
1. **Hợp đồng Render Readiness duy nhất**: Xóa bỏ hoàn toàn việc kiểm tra `words` và `tl` cũ trong `Bank.can()`. Thống nhất một quy tắc kiểm tra tính khả thi kết xuất dựa trên các ký tự thành phần (`letters`, `digits`, `punct`, `symbols`, `marks`) cho `Bank`, `Writer`, `Controller` và `CLI`.
2. **Khắc phục hàng đợi Web Client**: Tách biệt rõ `addCharactersFromText` (cho ô gõ văn bản tự do, tách code points) và `addCatalogLabels` (cho nhãn danh mục, giữ nguyên vẹn nhãn nghiệp vụ `"dấu sắc"`, `"dấu huyền"`...).
3. **Bảo toàn đa nét dấu thanh**: Sửa `AppController.teach_char()` truyền toàn bộ `rel_strokes` vào `Bank.add_tone_sample()` thay vì chỉ truyền nét đầu tiên (`rel_strokes[0]`).
4. **Bao phủ đầy đủ file kiểm tra .xopp**: Bổ sung các mẫu dấu thanh từ `bank.marks` kèm nhãn hiển thị tiếng Việt trực quan vào `AppController.export_check()`.
5. **Nâng cấp kiểm chứng hình học chống dính nét**: Cải tiến `min_stroke_clearance` từ phép so sánh điểm rời rạc sang phép tính khoảng cách giữa các đoạn thẳng 2D (segment-to-segment distance) kết hợp bounding box prune trong Pure Python.
6. **Chuẩn hóa thống kê Desktop & Tài liệu**: Cập nhật `format_stats_gui()` hiển thị trọng tâm là tổng số ký tự có mẫu và số mẫu nét; đồng bộ hóa tài liệu `README.md`.
7. **Sửa chữa toàn diện bộ kiểm thử CI**: Hiện đại hóa các bài kiểm thử `test_gui.py` và Playwright E2E (`bank.spec.ts`, `teach.spec.ts`) đang đòi hỏi hành vi từ nguyên khối cũ, giải quyết dứt điểm 14 lỗi pytest và 4 lỗi Playwright.

---

## Technical Context

**Language/Version**: Python 3.12 & Python 3.14 (Future-Proofing), JavaScript ES2022 (Node 20+ / Web Browser / Pyodide 314.0.7).

**Primary Dependencies**:
- Desktop GUI: Tkinter (`tkinter`, `ttk`).
- Kiểm thử: `pytest`, `pytest-timeout`, `@playwright/test`.
- Web runtime: `pyodide` 314.0.7 (Web Worker).
- Stdlib thuần: `math`, `unicodedata`, `json`, `gzip`, `logging`. Không thêm thư viện C/binary phụ thuộc mới.

**Storage**:
- File nén Gzip JSON (`.json.gz`) lưu trữ kho mẫu viết tay.
- Tệp định dạng Xournal++ (`.xopp`) cho file lưới ô và kiểm tra kho.
- IndexedDB & Pyodide MemFS cho Web Client.

**Testing**:
- Unit & Integration: `pytest` (`test_bank.py`, `test_writer.py`, `test_controller.py`, `test_gui.py`, `test_text_utils.py`).
- Web JavaScript Unit: `node --test` (`tests/js/*.test.mjs`).
- Web Browser Bridge: `node tests/browser/*.mjs`.
- End-to-End: Playwright (`tests/e2e/*.spec.ts`).

**Target Platform**: Đa nền tảng (Windows, Ubuntu Linux, macOS, Trình duyệt Web hiện đại hỗ trợ WebAssembly & Web Worker).

**Project Type**: Desktop GUI (Tkinter) + Web Client (PWA/Pyodide SPA) + Python Library / CLI tool.

**Performance Goals**:
- Phép tính khoảng cách đoạn nét `min_stroke_clearance`: $< 0.1$ms cho mỗi cặp ký tự trong Pure Python.
- Kiểm tra tính khả thi kết xuất `Bank.can(w)`: $< 0.01$ms cho mỗi từ.
- Xuất file kiểm tra `.xopp` cho kho đầy đủ: $< 200$ms.

**Constraints**:
- Chạy 100% Offline, Zero Remote CDN.
- Không đưa thêm các thư viện bên ngoài nặng nề (như Shapely hoặc NumPy) theo Constitution Principle II.

**Scale/Scope**:
- Kho mẫu hỗ trợ hàng trăm ký tự đơn lẻ và hàng chục nghìn nét vẽ viết tay.
- Kết xuất tài liệu nhiều trang không dính nét, không rò rỉ bộ nhớ.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Trạng thái | Ghi chú |
| :--- | :--- | :--- | :--- |
| **I. Maintainability & Code Cleanliness** | Đạt | ✅ PASS | Tách rõ các phương thức xử lý hàng đợi, hợp đồng render readiness có tài liệu KDoc/Docstring giải thích rõ lý do thiết kế. |
| **II. Simple Architecture (KISS & YAGNI)** | Đạt | ✅ PASS | Thuật toán khoảng cách đoạn nét giải bằng công thức vector 2D cơ bản trong Pure Python, không cài thêm thư viện phức tạp. |
| **III. Comprehensive Automated Testing** | Đạt | ✅ PASS | Cập nhật đầy đủ các assertion trong `test_gui.py` và Playwright theo đặc tả mới; cam kết CI xanh 100% (0 lỗi). |
| **IV. Loose Coupling & High Cohesion** | Đạt | ✅ PASS | Phân định ranh giới rõ rệt giữa Controller, Model Bank, Writer, và Web Client UI. |

---

## Project Structure

### Documentation (this feature)

```text
specs/028-char-first-alignment-and-ci-repair/
├── spec.md              # Đặc tả yêu cầu người dùng, FR và SC
├── checklists/
│   └── requirements.md  # Checklist nghiệm thu yêu cầu
├── plan.md              # Kế hoạch triển khai kiến trúc (file này)
├── research.md          # Quyết định kỹ thuật Phase 0
├── data-model.md        # Mô hình thực thể Phase 1
├── quickstart.md        # Hướng dẫn kiểm thử và chạy thực tế Phase 1
└── contracts/           # Hợp đồng giao tiếp Phase 1
    ├── render-readiness-contract.md
    ├── web-teach-queue-contract.md
    └── stroke-clearance-geometry-contract.md
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   ├── bank.py          # Bank.can(), add_tone_sample() đa nét
│   ├── writer.py        # assemble_word() ghép nét và áp dụng sàn khe hở vật lý
│   └── text_utils.py    # min_stroke_clearance() đo khoảng cách đoạn thẳng 2D
├── controller/
│   └── app_controller.py # teach_char() đa nét, export_check() bao phủ marks
├── formatting.py        # format_stats_gui() thống kê theo ký tự và mẫu nét
└── view/
    ├── bank_tab.py      # Hiển thị và lọc danh sách ký tự
    └── teach_tab.py     # Hàng đợi dạy chữ Desktop

webapp/
├── js/
│   ├── teach.js         # Tách addCharactersFromText & addCatalogLabels
│   └── bank.js          # Quản lý kho mẫu trên Web
└── index.html           # Khung giao diện Web Client

tests/
├── test_bank.py         # Kiểm thử Bank.can() và phân tách dấu thanh
├── test_controller.py   # Kiểm thử teach_char đa nét và export_check
├── test_gui.py          # Cập nhật assertion Desktop GUI cho char-first
├── test_text_utils.py   # Kiểm thử tính toán khoảng cách đoạn nét 2D
└── e2e/
    ├── bank.spec.ts     # Cập nhật tìm kiếm ký tự thay vì từ nguyên khối
    ├── teach.spec.ts    # Cập nhật nạp ký tự và kiểm tra hàng đợi
    └── write.spec.ts    # Kiểm thử kết xuất văn bản
```

---

## Complexity Tracking

> **Không có vi phạm nguyên tắc Constitution nào cần theo dõi hoặc miễn trừ.** Mọi giải pháp đều sử dụng kiến trúc tối giản và công nghệ có sẵn của dự án.
