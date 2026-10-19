# Implementation Plan: Worker and Seed Integrity Hardening

**Branch**: `044-worker-and-seed-integrity` | **Date**: 2026-10-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/044-worker-and-seed-integrity/spec.md`

## Summary

Triển khai củng cố toàn diện tính toàn vẹn của chu trình phục hồi Web Worker và luồng hạt giống ngẫu nhiên:
1. **Context-Bound RNG**: Dẫn xuất toàn bộ RNG (chọn biến thể `variant`, rung nét `jitter`, khoảng cách chữ số `dgap`) từ `SeedContext` chuẩn tắc, truyền `ctx_type` thay vì hằng số tĩnh `"tok"` để cô lập tuyệt đối giữa các phân loại nội dung (`text`, `cell`, `sym`, `heading`, `math`).
2. **Worker Lifecycle & Timeout Disaggregation**: Dừng `readyTimer` ngay lập tức khi Worker gửi tín hiệu `READY`; cho phép `onWorkerReady()` và `load_bank` chạy độc lập dưới timeout per-request; cô lập thế hệ Worker và rollback cờ `isDomListenersAttached` nếu khởi tạo giao diện gặp sự cố.
3. **Recursive Document Alignment**: Mở rộng `extract_doc_elements` duyệt đệ quy qua các khối danh sách `ListBlock` và các mục `ListItem`; đồng bộ hóa việc gán `inline.token_occurrences` theo từng từ gốc, loại bỏ hoàn toàn hiện tượng lệch số đếm khi từ dài bị chia thành nhiều chunk.
4. **Strict Canonical Key Typing**: Cập nhật `encode_canonical_key` để ném `TypeError` đối với mọi kiểu dữ liệu không xác định (`dict`, `set`, `object`), tuân thủ nghiêm ngặt hợp đồng CTR-044-SEED-PIPELINE.

## Technical Context

**Language/Version**: Python 3.12+ (Core Engine, Document IR, Layout) & JavaScript ES2022+ / Web Worker (Frontend, Pyodide 314.0.7)

**Primary Dependencies**: Pyodide (WASM Python runtime), standard library (`unicodedata`, `blake2b`, `struct`, `difflib`, `random`, `dataclasses`)

**Storage**: IndexedDB (Kho mẫu chữ & Cài đặt người dùng qua `webapp/js/storage.js`)

**Testing**: `pytest` (Unit & Regression), Node.js `node --test` (JS Unit), Playwright (E2E)

**Target Platform**: Web Client (WASM / Chromium / Firefox / Safari) & Python CLI / Library

**Project Type**: Hybrid Static Web Application & Offline-first Python handwriting synthesis engine

**Performance Goals**:
- Hoàn tất bắt tay Web Worker trong < 500ms (timeout tối đa 15s).
- Bố cục văn bản và đối chiếu hạt giống đệ quy < 50ms cho tài liệu 10 trang.
- 0% sai lệch hình học (độ lệch nét <= 0.02 pt) khi chèn thêm nội dung vào danh sách.

**Constraints**:
- Tuyệt đối không phụ thuộc Tkinter / GUI / View trong runtime Pyodide.
- Duy trì 100% SHA-256 trùng khớp trên cả 8 ca kiểm thử chuẩn Golden Master.
- Không thay đổi phiên bản `pyodide 314.0.7` trong `package.json`.

**Scale/Scope**: 5 thành phần bị tác động (`chuviettay/model/writer.py`, `chuviettay/model/rng.py`, `chuviettay/document/ir.py`, `chuviettay/layout/engine.py`, `webapp/js/app.js`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Maintainability & Code Cleanliness)**: PASS. Mã nguồn có định danh rõ ràng (`SeedContext`, `WorkerLifecycleSession`), phân tách rành mạch trách nhiệm, giữ trọn vẹn chú thích docstring.
- **Principle II (Simple Architecture - KISS & YAGNI)**: PASS. Sử dụng cấu trúc đệ quy tự nhiên cho cây IR thay vì thêm cơ chế caching phức tạp; loại bỏ chuyển đổi ép kiểu mờ ám.
- **Principle III (Comprehensive Automated Testing)**: PASS. Bổ sung các bài test chuyên biệt cho từng trường hợp biên: va chạm RNG giữa các không gian tên, chèn mục danh sách, token dài ngắt dòng, nạp kho chậm, và từ chối kiểu dữ liệu lạ.
- **Principle IV (Loose Coupling & High Cohesion)**: PASS. `document/ir.py` hoàn toàn độc lập với mô hình rendering; `webapp/js/app.js` phân định ranh giới giữa tầng điều phối Worker và tầng lưu trữ IndexedDB.

## Project Structure

### Documentation (this feature)

```text
specs/044-worker-and-seed-integrity/
├── plan.md              # File này (Kế hoạch thực thi)
├── research.md          # Kết quả nghiên cứu kiến trúc Phase 0
├── data-model.md        # Mô hình thực thể và biểu đồ trạng thái Phase 1
├── quickstart.md        # Hướng dẫn kiểm thử và kịch bản chạy Phase 1
├── contracts/           # Các hợp đồng giao diện
│   ├── seed-pipeline-contract.md
│   └── worker-lifecycle-contract.md
└── checklists/
    └── requirements.md  # Danh mục kiểm tra chất lượng đặc tả
```

### Source Code Layout (Affected Paths)

```text
chuviettay/
├── document/
│   └── ir.py                 # Duyệt đệ quy ListBlock & gán token_occurrences
├── layout/
│   └── engine.py             # Đồng bộ token chunking và SeedContext
└── model/
    ├── rng.py                # Strict TypeError trong encode_canonical_key
    └── writer.py             # Truyền ctx_type vào ScopedRNG (pick, jitter, dgap)

webapp/
└── js/
    └── app.js                # Tách biệt readyTimer, thế hệ Worker, resilient DOM init

tests/
├── js/
│   └── worker_resilience.test.mjs  # Unit test phục hồi Worker và timeout
├── test_rng.py                     # Unit test từ chối kiểu lạ trong encode_canonical_key
└── test_stable_variants.py         # Unit test cô lập namespace, ListBlock & chunking
```

**Structure Decision**: Duy trì kiến trúc mô-đun phân tầng chuẩn tắc của dự án, không phát sinh tệp rác hoặc thay đổi cấu trúc thư mục bên ngoài.

## Complexity Tracking

> **Không có vi phạm Constitution cần giải trình bổ sung.**
