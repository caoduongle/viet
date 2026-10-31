# Implementation Plan: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

**Branch**: `068-seed-bank-e2e-hardening` | **Date**: 2026-10-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/068-seed-bank-e2e-hardening/spec.md`

## Summary

Nâng cấp độ ổn định và tính toàn vẹn của hệ sinh thái `viet` bằng cách:
1. Sửa lỗi thuật toán cắt tiền tố/hậu tố trong đối chiếu hạt giống (`align_document_seeds`) khi tiền tố thực tế ngắn ($p < 3$) bằng cách khống chế chặn trên `max_suffix = min_len - p`, ngăn tuyệt đối hậu tố quét đè lên tiền tố.
2. Trích xuất và bảo toàn các chỉ số `token_occurrences` đã gắn sẵn trên cây Document IR qua nhiều lượt chỉnh sửa liên tiếp ($D_0 \to D_1 \to D_2 \to \dots$), ngăn ngừa đánh số lại từ 0 và tránh va chạm chỉ số khi chèn từ mới.
3. Tích hợp trực tiếp đối chiếu hạt giống vào luồng kết xuất thực tế tại `AppController.write_document` (tự động áp dụng cho cả CLI và Web Worker qua `BrowserBridge.write_text` khi `stable_variants=True`).
4. Khắc phục lỗi `ReferenceError: currentProfileId` trong `webapp/js/bank.js:194`, bổ sung định danh thế hệ `worker_epoch` và cơ chế đồng bộ `bank_revision` hai thành phần qua `sync_save`, đưa 100% bộ kiểm thử Playwright E2E về trạng thái PASS.
5. Bảo đảm tính nguyên tử của bản chụp kho mẫu `get_bank_snapshot` (chỉ thành công khi mọi danh mục con đều thành công) và tái cấu trúc hàm `showBankErrorBanner` sang DOM API chuẩn để loại bỏ lỗ hổng chèn mã đánh dấu HTML.
6. Bổ sung bài đo kiểm hiệu năng hồi quy bản chụp kho mẫu quy mô lớn (1.000+ nhãn) dưới 200ms.

---

## Technical Context

**Language/Version**: Python 3.10+ (Core, Layout, IR, Bridge, Pyodide 0.26+) & JavaScript ES2022 (Web Client, Web Worker, Playwright E2E).

**Primary Dependencies**:
- Python: `difflib`, `dataclasses`, `uuid`, `gzip`, `pytest`.
- Web: Pyodide (WASM Python runner), IndexedDB, Web Locks API, BroadcastChannel.
- E2E Testing: `@playwright/test` (Chromium headless).

**Storage**:
- File System: `.xopp` (Xournal++ gzip XML layout), `.json.gz` (kho mẫu nhị phân).
- Browser: IndexedDB (lưu trữ hồ sơ kho mẫu cá nhân dạng gzip bytes), MEMFS Pyodide (`/tmp/active_bank.json.gz`).

**Testing**:
- Python: `pytest` (hơn 1.410 bài test đơn vị, tích hợp, hồi quy hiệu năng).
- Web Client: `npx playwright test` (19 bài kiểm thử tự động đầu-cuối E2E trên trình duyệt).

**Target Platform**: Đa nền tảng: Linux, macOS, Windows (Python CLI/Backend) và Trình duyệt Web hiện đại (Chromium, Firefox, Safari qua WebAssembly Pyodide).

**Project Type**: Thư viện lõi Python, CLI công cụ tạo nét chữ viết tay, và Ứng dụng Web tĩnh chạy Python client-side trong Web Worker (WASM).

**Performance Goals**:
- `align_document_seeds`: Thực thi dưới 200ms cho tài liệu 1.000 từ lặp.
- `get_bank_snapshot`: Tổng hợp dữ liệu kho mẫu lớn (1.000+ nhãn) dưới 200ms.
- E2E Test Suite: Toàn bộ 19 bài kiểm thử hoàn thành dưới 60 giây.

**Constraints**:
- Chạy offline hoàn toàn trên trình duyệt, không phụ thuộc server bên ngoài.
- 100% tính tương thích ngược với dữ liệu kho mẫu và Document IR hiện có.
- Tuyệt đối an toàn trước mã độc (Zero HTML/Script injection).

**Scale/Scope**: Kho mẫu hỗ trợ hàng nghìn ký tự/mẫu nét; tài liệu hỗ trợ đa trang, văn bản thuần, Markdown, bảng biểu và công thức toán học LaTeX.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc Hiến chương | Đánh giá Tuân thủ | Ghi chú & Biện pháp Đảm bảo |
|------------------------|-------------------|-----------------------------|
| **I. Maintainability & Code Cleanliness** | **PASS** | Logic đối chiếu hạt giống, quản lý phiên bản và an toàn DOM được viết rõ ràng, có chú thích giải thích lý do toán học ($p + s \le \min(len)$). Không phát sinh nợ kỹ thuật. |
| **II. Simple Architecture (KISS & YAGNI)** | **PASS** | Tận dụng trực tiếp các thuộc tính sẵn có trên `Document IR` (`token_occurrences`, `occurrence`) và `AppController` (`_last_doc`, `_last_seed`). Không tạo thêm lớp trung gian hay dịch vụ phức tạp thừa thãi. |
| **III. Comprehensive Automated Testing** | **PASS** | Bổ sung các bài kiểm thử đơn vị cho tiền tố ngắn 1, 2, 3 token kèm từ lặp; kiểm thử chuỗi nhiều lượt sửa liên tiếp; kiểm thử an toàn DOM; kiểm thử hiệu năng 1.000 nhãn; và xác thực toàn bộ 19 bài kiểm thử E2E Playwright. |
| **IV. Loose Coupling & High Cohesion** | **PASS** | Logic xử lý nghiệp vụ tài liệu nằm hoàn toàn tại Python Core (`ir.py`, `app_controller.py`); cầu nối `bridge.py` đóng vai trò giao tiếp I/O; `py-worker.js` chuyển tiếp thông điệp và quản lý tệp ảo MEMFS; `bank.js` dựng giao diện. Ranh giới giữa các tầng được giữ vững tuyệt đối. |

*Gate Status: ALL GATES PASS. Không có vi phạm kiến trúc nào cần miễn trừ.*

---

## Project Structure

### Documentation (this feature)

```text
specs/068-seed-bank-e2e-hardening/
├── spec.md                          # Đặc tả yêu cầu chi tiết (Feature Specification)
├── plan.md                          # Kế hoạch triển khai kiến trúc (Implementation Plan)
├── research.md                      # Phase 0: Nghiên cứu kỹ thuật và quyết định thiết kế
├── data-model.md                    # Phase 1: Thực thể dữ liệu, quy tắc ràng buộc và chuyển trạng thái
├── quickstart.md                    # Phase 1: Hướng dẫn thiết lập và các kịch bản kiểm chứng độc lập
├── contracts/                       # Phase 1: Hợp đồng giao tiếp giữa các tầng
│   └── seed-bank-e2e-contract.md    # Schema API, Worker messages và DOM UI contracts
├── checklists/
│   └── requirements.md              # Bảng kiểm tra chất lượng đặc tả (16/16 PASS)
└── tasks.md                         # Phase 2: Danh sách nhiệm vụ thực thi TDD (speckit-tasks)
```

### Source Code (repository layout)

```text
chuviettay/
├── document/
│   └── ir.py                        # Sửa max_suffix = min_len - p & đọc token_occurrences đã gán
├── controller/
│   └── app_controller.py            # Tích hợp align_document_seeds vào write_document (_last_doc, _last_seed)
├── browser/
│   └── bridge.py                    # Bổ sung worker_epoch, kiểm tra atomic ok trong get_bank_snapshot
webapp/
├── js/
│   ├── bank.js                      # Sửa activeProfileId an toàn, kiểm tra cache 3 yếu tố, DOM textContent
│   └── worker/
│       └── py-worker.js             # Tăng _bridge.bank_revision và nạp lại kho trong sync_save
tests/
├── test_stable_variants.py          # Bổ sung test tiền tố ngắn 1-3 token, từ lặp, multi-step consecutive edits
├── test_browser_bridge.py           # Bổ sung test atomic get_bank_snapshot, worker_epoch
├── test_performance_regression.py   # Bổ sung benchmark get_bank_snapshot 1.000+ nhãn (< 200ms)
└── e2e/
    ├── bank.spec.ts                 # Kiểm chứng E2E tab kho mẫu và error banner an toàn
    ├── grid-import.spec.ts          # Kiểm chứng nhập lưới tập viết
    ├── multitab.spec.ts             # Kiểm chứng đồng bộ đa tab có và không có lock
    └── offline.spec.ts              # Kiểm chứng hoạt động ngoại tuyến
```

**Structure Decision**: Áp dụng trực tiếp vào cấu trúc phân tầng hiện tại của kho mã nguồn mà không cần tạo thêm thư mục mới, đảm bảo tính liên kết chặt chẽ và tuân thủ tuyệt đối cấu trúc dự án.

---

## Complexity Tracking

> Không có vi phạm kiến trúc hay sự phức tạp quá mức nào cần biện minh. Toàn bộ giải pháp tuân thủ chặt chẽ KISS và YAGNI.
