# Implementation Plan: Gia Cố Nền Tảng Kho Mã Nguồn Hậu Rà Soát (054-repo-audit-hardening)

**Branch**: `054-repo-audit-hardening` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/054-repo-audit-hardening/spec.md` derived from repo audit report (23/10/2026).

---

## Summary

Thực hiện gia cố toàn diện các thành phần cốt lõi của kho mã nguồn theo khuyến nghị ưu tiên của báo cáo rà soát ngày 23/10/2026:
1. Tuyến tính hóa bộ phân tách khối công thức Markdown bằng máy trạng thái một lượt và bảo vệ tuyệt đối khối mã (code fence & inline code).
2. Bảo đảm tính bất biến của Document IR trong `DocumentLayoutEngine._layout_inlines`, loại bỏ việc sửa đổi trực tiếp các nút `Text` nguồn.
3. Chuẩn hóa khóa bộ nhớ đệm Service Worker có tính định danh tài nguyên và tái lập bằng sắp xếp danh mục canonical trước khi băm.
4. Bảo vệ an toàn thư mục phân phối trong script build Web với cờ xác nhận `--force-clean` cho thư mục ngoài dự án.
5. Ngăn ngừa race condition trong Tab Viết bằng cơ chế số hiệu phiên bản kho mẫu đơn điệu (`bankRevision`).
6. Minh bạch hóa hợp đồng và cảnh báo cho chế độ nhập liệu DOCX Content-First.

---

## Technical Context

**Language/Version**: Python 3.10+ (hỗ trợ Python 3.10, 3.11, 3.12, 3.13, 3.14, Pyodide 0.26+) & JavaScript (ES2022+ trong trình duyệt và Node.js test runner)  
**Primary Dependencies**: `markdown-it-py`, `mdit_py_plugins`, `python-docx`, `pytest`, `ruff`  
**Storage**: IndexedDB (trên trình duyệt) / MEMFS (trong Web Worker Pyodide)  
**Testing**: `pytest` (cho core engine và importers Python), `node --test` (cho JS unit tests), `Playwright` (cho end-to-end PWA)  
**Target Platform**: Web Client (Pyodide Web Worker), Desktop CLI / Scripting  
**Project Type**: Thư viện xử lý chữ viết tay & Ứng dụng PWA Web-only  
**Performance Goals**: Quá trình phân tách công thức Markdown đạt $O(n)$ tuyến tính (<100ms cho tài liệu 5,000 dòng có lỗi cú pháp)  
**Constraints**: Không phá vỡ 1,294 bài kiểm thử hiện có của dự án; không làm thay đổi SHA-256 của các bài kiểm thử Golden Master  
**Scale/Scope**: 5 tệp mã nguồn chính (`markdown_importer.py`, `engine.py`, `build_web.py`, `write.js`, `docx_importer.py`) kèm các tệp kiểm thử tương ứng.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến pháp | Tiêu chí đánh giá | Trạng thái | Đánh giá kỹ thuật |
| :--- | :--- | :---: | :--- |
| **I. Maintainability & Code Cleanliness** | Mã nguồn rõ ràng, tự tài liệu hóa, giải quyết dứt điểm nợ kỹ thuật | **PASS** | Loại bỏ hoàn toàn vòng lặp quét nhìn trước lồng nhau $O(n^2)$; tách rõ ràng trách nhiệm máy trạng thái phân tích. |
| **II. Simple Architecture (KISS & YAGNI)** | Ưu tiên giải pháp trực tiếp, tránh trừu tượng hóa sớm | **PASS** | Dùng số hiệu phiên bản nguyên tăng đơn điệu thay vì cơ chế khóa bất đồng bộ phức tạp; tạo đối tượng `Text` mới thay vì deep copy cả cây. |
| **III. Comprehensive Automated Testing** | Kiểm thử tự động đầy đủ, tái hiện lỗi trước khi sửa | **PASS** | Bổ sung các bài kiểm thử biên: code fence ```` ``` ```` và `~~~`, tài liệu lớn nhiều `$$` dở dang, immutability, cache hash canonical, thư mục build ngoài. |
| **IV. Loose Coupling & High Cohesion** | Module tách biệt, dữ liệu luân chuyển rõ ràng (Explicit Data Flow) | **PASS** | Bảo vệ tính bất biến của Document IR do caller sở hữu; caller và layout engine không còn phụ thuộc đột biến ngầm. |

---

## Project Structure

### Documentation (this feature)

```text
specs/054-repo-audit-hardening/
├── plan.md              # Kế hoạch triển khai kiến trúc (file này)
├── research.md          # Kết quả nghiên cứu kỹ thuật Phase 0
├── data-model.md        # Mô hình trạng thái và dữ liệu Phase 1
├── quickstart.md        # Hướng dẫn xác minh nhanh các kịch bản thực tế Phase 1
├── contracts/           # Các hợp đồng giao diện kỹ thuật Phase 1
│   ├── markdown-scanner-contract.md
│   ├── document-ir-immutability-contract.md
│   ├── build-sw-cache-contract.md
│   └── preview-bank-sync-contract.md
└── checklists/
    └── requirements.md  # Danh mục kiểm định chất lượng đặc tả
```

### Source Code (affected paths)

```text
chuviettay/
├── importer/
│   ├── markdown_importer.py     # Thay thế _isolate_display_math_blocks bằng máy trạng thái O(n) & bảo vệ code fence
│   └── docx_importer.py         # Bổ sung cảnh báo minh bạch cho chế độ Content-First
└── layout/
    └── engine.py                # _layout_inlines tạo Text mới thay vì mutate đối tượng nguồn

scripts/
└── build_web.py                 # Chuẩn hóa SHA cache sw.js có path & bảo vệ xóa thư mục dist ngoài repo

webapp/js/
└── write.js                     # Quản lý bankRevision và requestRevision trong requestRender()

tests/
├── test_markdown_math_block_isolation.py  # Bổ sung kiểm thử code fence, O(n) unclosed performance, table rows
├── test_document_pipeline.py              # Bổ sung kiểm thử Document IR immutability qua nhiều lần layout
├── test_build_web.py                      # Bổ sung kiểm thử deterministic SW cache hash & dist dir protection
└── js/
    └── write_preview_sync.test.mjs        # Bổ sung kiểm thử race condition bankRevision
```

---

## Complexity Tracking

> Không có vi phạm Hiến pháp cần biện minh. Toàn bộ thiết kế tuân thủ nghiêm ngặt nguyên tắc đơn giản hóa kiến trúc và luồng dữ liệu minh bạch.

| Nội dung thay đổi | Lý do thực hiện | Giải pháp thay thế phức tạp đã loại bỏ |
| :--- | :--- | :--- |
| `Text` gộp tạo instance mới | Đảm bảo tính bất biến của Document IR | Loại bỏ `copy.deepcopy(document)` toàn phần tốn bộ nhớ |
| `bankRevision` tăng đơn điệu | Loại bỏ race condition preview/kho | Loại bỏ hàng đợi khóa semaphore bất đồng bộ phức tạp |
| Quét phân đoạn `_CODE_SEGMENT` | Bảo vệ code fence và code span | Loại bỏ regex lookahead phức tạp dễ gây lỗi ReDoS |
