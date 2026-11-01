# Implementation Plan: Feature 070 - Render Generation, Import Generation, Export Stale Guard & Test Hardening

**Branch**: `070-render-generation-import-seed-hardening` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/070-render-generation-import-seed-hardening/spec.md` (cập nhật sau rà soát commit `53258d2`: P1 - Hoàn thiện `canExport()` đối chiếu `renderedGeneration` và `renderedSnapshot` gồm text, format, `writeOptions`; P2 - Kiểm thử trực tiếp Stage 2 Stale Guard với giải nén bị trì hoãn; P2 - Kiểm soát `currentImportGeneration` chống ghi đè khi mở nhiều tệp liên tiếp; P2 - Xác định hóa E2E race condition qua Render Barrier; P3 - Dọn dẹp `debounceTimer` và xử lý tranh chấp thời điểm làm ẩn `#bank-error-banner` trong `bank.spec.ts` trên CI).

---

## Summary

Feature 070 thiết lập hàng rào bảo vệ toàn diện cho chu trình **Soạn thảo / Nhập tệp $\to$ Kết xuất $\to$ Xem trước $\to$ Xuất tệp**:
1. **Two-Stage Stale Guard & Atomic State Commit**: Giải nén XOPP và phân tích XML vào biến cục bộ, kiểm tra thế hệ kết xuất cả trước và sau giải nén mới cam kết nguyên tử vào trạng thái toàn cục.
2. **Strict Export Stale Guard (`canExport`)**: Lưu trữ bản chụp đã cam kết (`renderedSnapshot` gồm `generation`, `text`, `format`, `options`). Khóa xuất tệp ngay khi `renderedGeneration !== currentRenderGeneration`, khi yêu cầu kết xuất mới gặp lỗi, hoặc khi người dùng thay đổi bất kỳ thông số nào trong `writeOptions` / `currentFormat` / `textarea`.
3. **Import Generation Guard (`currentImportGeneration`)**: Đánh số thế hệ cho mỗi lần mở hoặc kéo thả tệp (.txt, .md, .docx), hủy bỏ mọi tác vụ nhập tệp cũ hoàn tất muộn hơn để không bao giờ ghi đè tệp được chọn cuối cùng.
4. **Deterministic Testing & CI Stability**: Cung cấp hook trì hoãn giải nén (`setXoppDecompressorForTesting`) cho unit test Stage 2, cổng chặn (`installRenderBarrierForTesting`) cho E2E race condition xác định 100%, dọn dẹp `debounceTimer` trong test reset, và loại bỏ xung đột bất đồng bộ giữa `refreshBankView()` và `showBankErrorBanner()` giúp 100% các job trên CI xanh bền vững.

---

## Technical Context

**Language/Version**: Python 3.10+ (hỗ trợ CI 3.12, 3.13, 3.14) và JavaScript ES2022 (trình duyệt Web hiện đại + Node.js 20+ test runner).

**Primary Dependencies**:
- Frontend: Web Worker, Pyodide 314.0.7 (WebAssembly Python runtime), `DecompressionStream`.
- Backend: Standard Python Library, `markdown-it-py`, `python-docx`, `lxml`.

**Storage**: MEMFS (hệ thống tệp ảo Pyodide trong bộ nhớ), IndexedDB (lưu trữ hồ sơ người dùng offline).

**Testing**:
- Python: `pytest` (hơn 1.427 bài kiểm thử).
- Node.js: `node --test` (71+ bài kiểm thử đơn vị giải phóng 100% timer).
- Web Client: `npx playwright test` (24 bài kiểm thử E2E trên trình duyệt, chạy ổn định với `--workers=2`).

**Target Platform**: Linux, macOS, Windows (Python Backend/CLI) và Trình duyệt Web hiện đại (Chromium, Firefox, Safari qua WASM Pyodide).

**Project Type**: Ứng dụng Web tĩnh offline-first kết hợp lõi xử lý viết tay Python chạy client-side trong Web Worker.

**Performance Goals**:
- `requestRender`: Loại bỏ kết quả cũ trong $0$ ms ở cả Stage 1 và Stage 2.
- `canExport`: Kiểm tra đối chiếu thế hệ và bản chụp tùy chọn trong $< 0.1$ ms.
- `get_bank_snapshot`: Trích xuất kho mẫu quy mô lớn (1.050+ nhãn, 3.520 mẫu nét) dưới 200ms (thực tế $< 2$ ms).
- Unit Test Suite (`render_generation.test.mjs`): Hoàn thành dưới 500ms, không giữ tiến trình Node.js.

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
| **I. Maintainability & Code Cleanliness** | **PASS** | Sử dụng các bộ đếm thế hệ tăng đơn điệu (`currentRenderGeneration`, `renderedGeneration`, `currentImportGeneration`) và bản chụp bất biến `renderedSnapshot`; hàm so sánh `areWriteOptionsEqual` rõ ràng, tự giải thích. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Giải quyết trực tiếp trong `write.js` và `bank.js` bằng các cấu trúc dữ liệu thuần JavaScript, không thêm thư viện ngoài hay sự phức tạp không cần thiết. |
| **III. Comprehensive Automated Testing** | **PASS** | Kiểm thử trực tiếp Stage 2 giải nén XOPP, kiểm thử mở nhiều tệp liên tiếp lệch thứ tự (.docx vs .txt), kiểm thử E2E race condition bằng barrier xác định, và khắc phục triệt để flaky test XSS trên CI. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Các hook kiểm thử (`setXoppDecompressorForTesting`, `installRenderBarrierForTesting`) được cô lập gọn nhẹ, không ảnh hưởng tới luồng thực thi sản phẩm (production). |

*Gate Status: ALL GATES PASS. Không có vi phạm kiến trúc nào cần miễn trừ.*

---

## Project Structure

### Documentation (this feature)

```text
specs/070-render-generation-import-seed-hardening/
├── plan.md              # Kế hoạch kiến trúc (File này)
├── research.md          # Kết quả nghiên cứu và 12 quyết định kỹ thuật
├── data-model.md        # Mô hình trạng thái thế hệ kết xuất, thế hệ nhập tệp và bản chụp đã cam kết
├── quickstart.md        # Hướng dẫn kiểm chứng và bảng ghi nhận thực tế
├── contracts/
│   └── render-generation-contract.md # Hợp đồng giao tiếp Worker, canExport, handleFileImport & Testing Hooks
└── tasks.md             # Sẽ được cập nhật bởi /speckit-tasks
```

### Source Code (repository root)

```text
chuviettay/
├── browser/
│   └── bridge.py                    # Cầu nối BrowserBridge (clear_document_history)
webapp/
├── js/
│   ├── app.js                       # Quản lý Worker và clearPendingWorkerRequestsForTesting
│   ├── bank.js                      # Đồng bộ hóa showBankErrorBanner(null) đầu refreshBankView tránh race condition
│   ├── write.js                     # Render generation, Import generation, renderedSnapshot, canExport, Testing hooks
│   └── worker/
│       └── py-worker.js             # Truyền và phản hồi requestId kèm write_text
tests/
├── js/
│   └── render_generation.test.mjs   # Unit test Stage 1, Stage 2 (trì hoãn giải nén), canExport (options/failed render), importGeneration (.docx vs .txt)
├── e2e/
│   ├── bank.spec.ts                 # E2E test kho mẫu & ổn định hóa kiểm thử XSS với --workers=2
│   └── write.spec.ts                # E2E test race condition xác định (Render Barrier), Export Stale Guard, reset seed
├── test_bridge.py                   # Unit test BrowserBridge.clear_document_history
├── test_performance_regression.py   # Chuẩn hóa chú thích và cấu trúc dữ liệu 3.520 mẫu nét
└── test_stable_variants.py          # Bền vững hóa assertion so sánh nét vẽ theo từ ngữ
```

**Structure Decision**: Áp dụng trực tiếp vào cấu trúc phân tầng hiện tại của kho mã nguồn, duy trì sự tối giản và tính liên kết chặt chẽ.

---

## Complexity Tracking

*Không có vi phạm kiến trúc nào cần miễn trừ.*
