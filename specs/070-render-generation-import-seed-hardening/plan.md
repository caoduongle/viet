# Implementation Plan: Feature 070 - Render Generation, Import Seed Reset & Test Hardening

**Branch**: `070-render-generation-import-seed-hardening` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/070-render-generation-import-seed-hardening/spec.md` (đã cập nhật Two-Stage Stale Guard sau giải nén XOPP, Export Stale Guard, Chặn nạp tệp khi reset seed thất bại, Deterministic Testing & Unit Test fixture hợp lệ).

---

## Summary

Feature 070 giải quyết triệt để vấn đề race condition khi kết xuất tài liệu cũ ghi đè lên tài liệu mới thông qua cơ chế Thế hệ kết xuất (Render Generation / Request ID) kết hợp Cam kết Nguyên tử 2 giai đoạn (Two-Stage Stale Guard: sau Worker và sau giải nén XOPP). Đồng thời, tính năng bổ sung cơ chế khóa xuất tệp an toàn (Export Stale Guard) ngăn chặn người dùng xuất tệp cũ khi nội dung đang thay đổi, xử lý dừng nạp tệp khi lệnh reset hạt giống thất bại, nâng cao tính xác định của bài kiểm thử Playwright E2E, củng cố unit test Node.js bằng fixture XOPP gzip chuẩn và giải phóng toàn bộ timer Worker.

---

## Technical Context

**Language/Version**: Python 3.10+ (hỗ trợ CI 3.12, 3.13, 3.14) và JavaScript ES2022 (trình duyệt Web hiện đại + Node.js 20+ test runner).

**Primary Dependencies**:
- Frontend: Web Worker, Pyodide 314.0.7 (WebAssembly Python runtime), `DecompressionStream` / `pako`.
- Backend: Standard Python Library, `markdown-it-py`, `python-docx`, `lxml`.

**Storage**: MEMFS (hệ thống tệp ảo Pyodide trong bộ nhớ), IndexedDB (lưu trữ hồ sơ người dùng offline).

**Testing**:
- Python: `pytest` (hơn 1.427 bài kiểm thử).
- Node.js: `node --test` (bộ test đơn vị Node.js giải phóng 100% timer).
- Web Client: `npx playwright test` (23+ bài kiểm thử E2E trên trình duyệt).

**Target Platform**: Linux, macOS, Windows (Python Backend/CLI) và Trình duyệt Web hiện đại (Chromium, Firefox, Safari qua WASM Pyodide).

**Project Type**: Ứng dụng Web tĩnh offline-first kết hợp lõi xử lý viết tay Python chạy client-side trong Web Worker.

**Performance Goals**:
- `requestRender`: Loại bỏ kết quả cũ trong 0ms ở cả 2 giai đoạn (sau Worker và sau giải nén XOPP).
- `canExport`: Phản hồi tức thì $0$ ms, ngăn chặn xuất nhầm tệp cũ khi `isRenderStale === true` hoặc `isRendering === true`.
- `get_bank_snapshot`: Trích xuất kho mẫu quy mô lớn (1.050+ nhãn, 3.520 mẫu nét) dưới 200ms (thực tế đo được $< 2$ ms).
- E2E Test Suite: Hoàn thành toàn bộ bộ test Playwright dưới 4 phút.

**Constraints**:
- Không làm thay đổi giao diện công khai hay phá vỡ tương thích ngược.
- Chạy 100% offline, tuyệt đối không gọi ra mạng ngoài (Zero Remote CDN).
- Giữ vững tính tất định của seed nét chữ viết tay.

**Scale/Scope**: Bộ gõ hỗ trợ xử lý tài liệu nhiều trang, chuyển đổi tệp .docx, .md, .txt và kết xuất đồ họa vector SVG / XOPP.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá Tuân thủ | Ghi chú & Biện pháp Đảm bảo |
|------------------------|-------------------|-----------------------------|
| **I. Maintainability & Code Cleanliness** | **PASS** | Sử dụng mã định danh thế hệ `currentRenderGeneration` số nguyên tăng đơn điệu, mô hình Atomic State Commit và kiểm tra tính mới `canExport()` tường minh; loại bỏ các chỉ số mảng cố định (hard-coded slice) trong kiểm thử nét vẽ. Không phát sinh nợ kỹ thuật. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Tận dụng trực tiếp các biến trạng thái trong `write.js` và `py-worker.js`, giải nén và phân tích vào biến cục bộ trước khi commit, không đưa thêm thư viện ngoài hay framework phức tạp vào dự án. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung kiểm thử E2E race condition xác định, kiểm thử khóa xuất file khi stale, kiểm thử nạp tệp đa định dạng, và unit test Node.js với fixture gzip hợp lệ không giữ timer treo. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Quản lý thế hệ kết xuất và điều phối xuất file thuộc trách nhiệm của tầng UI (`write.js`); Web Worker và Python Core giữ nguyên ranh giới I/O trong sáng và độc lập. |

*Gate Status: ALL GATES PASS. Không có vi phạm kiến trúc nào cần miễn trừ.*

---

## Project Structure

### Documentation (this feature)

```text
specs/070-render-generation-import-seed-hardening/
├── plan.md              # Kế hoạch kiến trúc (File này)
├── research.md          # Kết quả nghiên cứu và 6 quyết định kỹ thuật
├── data-model.md        # Mô hình trạng thái thế hệ kết xuất và vòng đời seed
├── quickstart.md        # Hướng dẫn kiểm chứng và bảng ghi nhận thực tế
├── contracts/
│   └── render-generation-contract.md # Hợp đồng giao tiếp Worker, UI và Stale Guard
└── tasks.md             # Sẽ được sinh bởi /speckit-tasks
```

### Source Code (repository root)

```text
chuviettay/
├── browser/
│   └── bridge.py                    # Cầu nối BrowserBridge (clear_document_history)
webapp/
├── js/
│   ├── write.js                     # Render generation, request ID, stale result guard, resetDocumentSeedHistory
│   └── worker/
│       └── py-worker.js             # Truyền và phản hồi requestId kèm write_text
tests/
├── e2e/
│   └── write.spec.ts                # E2E test chống ghi đè render cũ, reset seed khi mở file .txt/.md/.docx
├── test_bridge.py                   # Unit test BrowserBridge.clear_document_history
├── test_performance_regression.py   # Chuẩn hóa chú thích và cấu trúc dữ liệu 3.520 mẫu nét
└── test_stable_variants.py          # Bền vững hóa assertion so sánh nét vẽ theo từ ngữ
```

**Structure Decision**: Áp dụng trực tiếp vào cấu trúc phân tầng hiện tại của kho mã nguồn, duy trì sự tối giản và tính liên kết chặt chẽ.

---

## Complexity Tracking

*Không có vi phạm kiến trúc nào cần miễn trừ.*
