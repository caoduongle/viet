# Implementation Plan: Gia Cố An Toàn Xóa Thư Mục Build Và Hoàn Thiện Cú Pháp CommonMark/GFM (056-build-safety-and-markdown-hardening)

**Branch**: `056-build-safety-and-markdown-hardening` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/056-build-safety-and-markdown-hardening/spec.md`

---

## Summary

Kế hoạch này giải quyết dứt điểm các rủi ro kỹ thuật đường biên còn lại theo báo cáo rà soát:
1. **An toàn tuyệt đối thư mục ngoài**: Sửa `prepare_dist_dir` để không bao giờ tự động xóa thư mục ngoài không rỗng chỉ dựa trên marker cũ; bắt buộc cờ `--force-clean` tại chính lần chạy đó. Loại bỏ hoàn toàn tệp marker `.chuviettay_build_dist` khỏi thư mục `dist`.
2. **Bảo vệ mã CommonMark nâng cao**: Mở rộng `_split_code_segments` và `_find_code_spans` để nhận diện chính xác code fence trong blockquote (`> ~~~`), indented code block (4 spaces), và bỏ qua backtick bị escape (`\``) qua toàn bộ pipeline `import_text()`.
3. **Nhận diện ngữ cảnh bảng GFM chặt chẽ**: Dùng kỹ thuật pre-scan xác định khối bảng có hàng phân cách `---|---`, tránh nhận nhầm dòng đơn độc lập `$$x=1$$ | 2` là bảng; đồng thời kiểm tra chi tiết giá trị ô trong Document IR của bảng compact.
4. **Làm sạch thư mục Service Worker**: Lọc `dirs[:] = [d for d in dirs if not d.startswith('.')]` trong `generate_sw_js` để ngăn việc duyệt vào các thư mục ẩn.
5. **Kiểm thử hồi quy toàn diện**: Đo tỷ lệ mở rộng $T(2N) / T(N) \le 3.5$ trên toàn bộ luồng tiền xử lý (bao gồm `_split_code_segments`), và kiểm thử an toàn thư mục ngoài có tệp người dùng mới thêm vào.

---

## Technical Context

**Language/Version**: Python 3.12+ (hỗ trợ tương thích Python 3.13, 3.14 và Pyodide WASM), JavaScript (Node.js 20+)  
**Primary Dependencies**: `markdown-it-py`, `mdit_py_plugins`  
**Storage**: N/A  
**Testing**: `pytest`, `pytest-timeout`, Node.js test runner (`npm run test:unit`)  
**Target Platform**: Nền tảng trình duyệt Web PWA (Pyodide WebAssembly) và Python Core  
**Project Type**: Thư viện xử lý tài liệu / Script đóng gói ứng dụng web tĩnh  
**Performance Goals**: Bộ tiền xử lý đạt độ phức tạp tuyến tính $O(n)$, tỷ lệ $T(2N) / T(N) \le 3.5$  
**Constraints**: 0% hồi quy trên toàn bộ test suite hiện hữu (hơn 1.300 bài test), bảo toàn 100% SHA-256 Golden Master  
**Scale/Scope**: `chuviettay/importer/markdown_importer.py`, `scripts/build_web.py`, `tests/test_markdown_math_block_isolation.py`, `tests/test_build_web.py`  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Maintainability & Code Cleanliness**: Logic an toàn thư mục ngoài rõ ràng, không phụ thuộc vào marker ẩn; bộ phân tách mã bám sát CommonMark v0.31.2.
- [x] **II. Simple Architecture (KISS & YAGNI)**: Không thêm cấu trúc phức tạp hay dependencies ngoài; giải quyết trực tiếp tại gốc rễ vấn đề.
- [x] **III. Comprehensive Automated Testing**: Bổ sung đầy đủ các bài kiểm tra tái hiện chính xác các ca lỗi (blockquote fence, indented block, escaped backticks, isolated pipe line, tệp người dùng trong thư mục ngoài, lọc thư mục ẩn).
- [x] **IV. Loose Coupling & High Cohesion**: Phân định ranh giới rõ ràng giữa an toàn hệ thống tệp của build script và bộ phân tích cú pháp Markdown.

---

## Project Structure

### Documentation (this feature)

```text
specs/056-build-safety-and-markdown-hardening/
├── plan.md                                          # Kế hoạch thực hiện tổng thể
├── research.md                                      # Kết quả nghiên cứu kỹ thuật Phase 0
├── data-model.md                                    # Mô hình dữ liệu và luồng quyết định Phase 1
├── quickstart.md                                    # Hướng dẫn xác minh nhanh các kịch bản
├── contracts/                                       # Hợp đồng giao tiếp Phase 1
│   ├── build-external-safety-contract.md            # Hợp đồng an toàn thư mục ngoài
│   ├── commonmark-nested-code-contract.md           # Hợp đồng bảo vệ khối mã lồng nhau
│   └── gfm-table-context-contract.md                # Hợp đồng ngữ cảnh bảng GFM
└── checklists/
    └── requirements.md                              # Bảng kiểm tra chất lượng đặc tả
```

### Source Code Layout (affected paths)

```text
chuviettay/
└── importer/
    └── markdown_importer.py     # Blockquote fences, indented blocks, escaped backticks, table context

scripts/
└── build_web.py                 # An toàn thư mục ngoài không rỗng, bỏ marker khỏi dist, lọc dirs ẩn

tests/
├── test_markdown_math_block_isolation.py  # Tests blockquote fence, indented block, table context, scaling
└── test_build_web.py                      # Tests an toàn thư mục ngoài có tệp người dùng, dirs ẩn
```

**Structure Decision**: Áp dụng trực tiếp vào cấu trúc mô-đun hiện hữu của repository.

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*Không có vi phạm nguyên tắc kiến trúc.*
