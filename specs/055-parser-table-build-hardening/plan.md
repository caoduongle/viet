# Implementation Plan: Gia Cố Độ Chuẩn Xác CommonMark, Bảng GFM Và An Toàn Đóng Gói (055-parser-table-build-hardening)

**Branch**: `055-parser-table-build-hardening` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/055-parser-table-build-hardening/spec.md`

---

## Summary

Kế hoạch này giải quyết triệt để 4 vấn đề đường biên còn lại được phát hiện trong quá trình rà soát kho mã nguồn:
1. **Bảo vệ mã chuẩn CommonMark**: Thay thế biểu thức chính quy thiếu bao quát bằng bộ phân tích tách đoạn mã CommonMark thống nhất (`split_code_segments`), ghi nhận đúng độ dài $K \ge 3$ của code fence và $N \ge 1$ của inline code span, ngăn ngừa việc đóng sớm fence 4 backticks khi gặp dòng 3 backticks, và bảo vệ code span nhiều backtick (như ```` ``prefix:$$x=1$$`` ````) qua toàn bộ pipeline `import_text()`.
2. **Bảo vệ bảng GFM compact**: Cải tiến logic nhận diện hàng bảng trong `_isolate_display_math_blocks`, kiểm tra sự tồn tại của ký tự phân cách `|` nằm bên ngoài công thức toán hoàn chỉnh và ngoài code span, bảo đảm hàng bảng compact có ô đầu tiên bắt đầu bằng `$$...$$` không bị xé dòng thành các khối rời rạc.
3. **Làm sạch danh mục Service Worker và gói phân phối**: Loại trừ tệp marker nội bộ `.chuviettay_build_dist` và các tệp ẩn khỏi danh sách `PRECACHE_URLS` trong `sw.js` và gói phát hành web, ngăn chặn lỗi 404 trên các máy chủ web chặn tệp ẩn.
4. **Kiểm thử hiệu năng co giãn tỷ lệ tương đối**: Chuyển bài kiểm tra thời gian xử lý với $N$ và $2N$ dòng `$$` không đóng sang phương pháp đo tỷ lệ tăng trưởng $T(2N) / T(N) \le 3.5$, kết hợp ngưỡng trần nới lỏng an toàn ($< 2.0$s), bảo đảm chứng minh độ phức tạp tuyến tính $O(n)$ mà không gây hiện tượng flaky test trên máy chủ CI tải cao.

---

## Technical Context

**Language/Version**: Python 3.12+ (hỗ trợ tương thích Python 3.13, 3.14 và Pyodide WASM), JavaScript (ES Modules, Node.js 20+)  
**Primary Dependencies**: `markdown-it-py`, `mdit_py_plugins`  
**Storage**: N/A (không thay đổi cấu trúc lưu trữ cơ sở dữ liệu hoặc IndexedDB)  
**Testing**: `pytest`, `pytest-timeout`, Node.js test runner (`npm run test:unit`)  
**Target Platform**: Nền tảng trình duyệt Web PWA (Pyodide WebAssembly) và môi trường Python Core  
**Project Type**: Thư viện xử lý tài liệu / Bộ đóng gói ứng dụng web tĩnh  
**Performance Goals**: Bộ phân tích tiền xử lý Markdown đạt độ phức tạp tuyến tính $O(n)$, xử lý 10.000 dòng mở không đóng trong $< 0.5$s, tỷ lệ $T(2N) / T(N) \le 3.5$  
**Constraints**: 0% hồi quy trên toàn bộ test suite hiện hữu (hơn 1.300 bài test), bảo toàn 100% SHA-256 Golden Master  
**Scale/Scope**: 3 tệp nguồn bị ảnh hưởng trực tiếp (`chuviettay/importer/markdown_importer.py`, `scripts/build_web.py`, `tests/test_markdown_math_block_isolation.py`, `tests/test_build_web.py`)  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Bộ phân tích tách đoạn mã CommonMark được thiết kế theo hàm thuần túy với tài liệu chú thích rõ ràng; không dùng các biểu thức chính quy khó hiểu hay mẹo xử lý phụ thuộc vào ngữ cảnh ẩn.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không thêm thư viện ngoài; sử dụng thuật toán quét xác định một lượt, bám sát đặc tả CommonMark v0.31.2.
- [x] **III. Comprehensive Automated Testing**: Bổ sung đầy đủ các test case tái hiện chính xác các ca lỗi được chỉ ra trong báo cáo rà soát (fence 4 backticks, span 2 backticks, compact table có `$$`, kiểm tra `sw.js` không chứa `.chuviettay_build_dist`, và đo tỷ lệ co giãn $T(2N)/T(N)$).
- [x] **IV. Loose Coupling & High Cohesion**: Các cải tiến nằm gọn trong ranh giới của bộ nhập liệu `MarkdownImporter` và script đóng gói `build_web.py`, không làm ảnh hưởng tới các tầng Layout Engine hay Bank Storage.

---

## Project Structure

### Documentation (this feature)

```text
specs/055-parser-table-build-hardening/
├── plan.md                                          # Kế hoạch thực hiện tổng thể
├── research.md                                      # Kết quả nghiên cứu kỹ thuật Phase 0
├── data-model.md                                    # Mô hình dữ liệu và máy trạng thái Phase 1
├── quickstart.md                                    # Hướng dẫn xác minh nhanh các kịch bản
├── contracts/                                       # Hợp đồng giao tiếp Phase 1
│   ├── markdown-code-protection-contract.md         # Hợp đồng bảo vệ khối mã và đoạn mã
│   ├── gfm-compact-table-contract.md                # Hợp đồng bảo toàn hàng bảng compact
│   └── build-distribution-safety-contract.md        # Hợp đồng loại trừ tệp ẩn khỏi precache
└── checklists/
    └── requirements.md                              # Bảng kiểm tra chất lượng đặc tả
```

### Source Code Layout (affected paths)

```text
chuviettay/
└── importer/
    └── markdown_importer.py     # Thống nhất split_code_segments, bảo vệ fence/span & compact table

scripts/
└── build_web.py                 # Loại trừ .chuviettay_build_dist khỏi precache và gói phân phối

tests/
├── test_markdown_math_block_isolation.py  # Test fence 4 backticks, span 2 backticks, compact table, scalability ratio
└── test_build_web.py                      # Test sw.js không chứa .chuviettay_build_dist trong PRECACHE_URLS
```

**Structure Decision**: Áp dụng trực tiếp vào cấu trúc mô-đun hiện hữu của repository, duy trì nguyên vẹn các đường dẫn chuẩn mà không tạo thêm các cấu trúc thừa.

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Không có vi phạm nguyên tắc kiến trúc.*
