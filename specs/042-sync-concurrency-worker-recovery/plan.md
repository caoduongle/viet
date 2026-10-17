# Implementation Plan: Hoàn thiện Kiểm soát Cạnh tranh Đa tab, Khôi phục Sự cố Worker & Nguyên tử hóa Cache Ngoại tuyến

**Branch**: `042-sync-concurrency-worker-recovery` | **Date**: 2026-10-17 | **Spec**: [spec.md](file:///d:/viet/app/specs/042-sync-concurrency-worker-recovery/spec.md)

**Input**: Feature specification from `/specs/042-sync-concurrency-worker-recovery/spec.md`

## Summary

Feature 042 hoàn thiện tính toàn vẹn và độ tin cậy của ứng dụng sau đợt rà soát commit `4250256`:
1. Triển khai cơ chế kiểm soát cạnh tranh 3 trạng thái (Explicit 3-State OCC) trong IndexedDB (`webapp/js/storage.js`), ngăn chặn tuyệt đối lỗi làm sống lại hồ sơ đã xóa và xung đột khi khởi tạo mới đồng thời.
2. Đảm bảo an toàn ngoại lệ đồng bộ trong `executeTransaction()` bằng cách chủ động gọi `tx.abort()` khi `operationFn` phát sinh lỗi.
3. Bổ sung kịch bản kiểm thử cuộc đua ghi đồng thời thực sự giữa nhiều tab (E2E trong Playwright và unit test) để xác minh đường dẫn phát hiện xung đột $\rightarrow$ tự động thử lại $\rightarrow$ hợp nhất mẫu chữ $\rightarrow$ bảo toàn trạng thái đã xóa.
4. Triển khai cơ chế khôi phục Worker tương tác (`recoverWorker`) kèm nút "Thử lại" trên giao diện (`#btn-worker-retry`), dọn dẹp hàng đợi và nạp lại kho mẫu sạch sẽ mà không làm mất nội dung văn bản; bảo vệ chống duplicate execution khi yêu cầu bị timeout.
5. Nguyên tử hóa quá trình nạp cache Service Worker (`webapp/sw.js` và `scripts/build_web.py`), xóa sạch cache dở dang nếu có lỗi mạng lúc install, và tách các wheel DOCX tùy chọn khỏi precache bắt buộc.

---

## Technical Context

**Language/Version**: JavaScript (ES2022+ / Node.js 18+ / Browser), Python 3.10+ (CI trên 3.12, 3.13, 3.14).  
**Primary Dependencies**: Pyodide 314.0.7, Playwright 1.58+, Ruff.  
**Storage**: IndexedDB (v2, object stores `profiles`, `app_settings`), MEMFS (Pyodide), CacheStorage (Service Worker).  
**Testing**: Node.js test runner (`node:test`, `node:assert/strict`), Playwright Chromium E2E, pytest.  
**Target Platform**: Web Modern Browsers (Chrome/Edge, Firefox, Safari) hỗ trợ IndexedDB và Web Workers; Offline-first qua Service Worker.  
**Project Type**: Static Web Application (Client-only / Headless Core / No Backend Server).  
**Performance Goals**: Khởi tạo lại Worker và nạp lại kho mẫu dưới 15 giây; độ trễ retry xung đột đồng bộ < 300ms.  
**Constraints**: Zero CDN / Zero Remote Runtime; hoàn toàn độc lập với Tkinter / GUI; không phá vỡ cấu trúc cache ngoại tuyến của phiên bản đang chạy.  
**Scale/Scope**: 4 User Stories, 5 files mã nguồn chính (`storage.js`, `app.js`, `sw.js`, `build_web.py`, `index.html`), 3 test suites (`storage.test.mjs`, `worker_resilience.test.mjs`, `multitab.spec.ts`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I: Maintainability & Code Cleanliness**: Kiến trúc phân tách rõ ràng 3 trạng thái OCC và các hàm khôi phục Worker có tài liệu KDoc/JSDoc rõ ràng.
- [x] **Principle II: Simple Architecture (KISS & YAGNI)**: Không thêm thư viện ngoài; tận dụng triệt để IndexedDB transactions, CacheStorage native và Worker native APIs.
- [x] **Principle III: Comprehensive Automated Testing**: Bổ sung đầy đủ unit tests cho 3-state OCC, timeout idempotency, worker recovery, và E2E race condition Playwright.
- [x] **Principle IV: Loose Coupling & High Cohesion**: `storage.js` chỉ quản lý lưu trữ và đồng bộ dữ liệu; `app.js` quản lý giao diện và vòng đời Worker; `sw.js` quản lý tài nguyên ngoại tuyến.
- [x] **Quality Gates**: Ruff, compileall, pytest, unit tests, bridge tests, Pyodide golden master, và Playwright tests đạt 100%.

---

## Project Structure

### Documentation (this feature)

```text
specs/042-sync-concurrency-worker-recovery/
├── spec.md              # Feature specification
├── plan.md              # Implementation Plan (this file)
├── research.md          # Technical research and design decisions
├── data-model.md        # Entities, OCC states, Worker session, and Cache model
├── quickstart.md        # Runnable validation scenarios
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── contracts/
│   ├── storage-concurrency-contract.md
│   ├── worker-recovery-contract.md
│   └── offline-cache-contract.md
└── tasks.md             # Tasks definition (generated in /speckit-tasks)
```

### Source Code Layout

```text
webapp/
├── index.html           # Thêm nút Thử lại #btn-worker-retry trên thanh trạng thái / banner
├── sw.js                # Nguyên tử hóa install cache, tách core vs optional lazy wheels
└── js/
    ├── app.js           # Bổ sung recoverWorker(), xử lý onmessageerror, an toàn timeout
    ├── storage.js       # 3-State OCC, tx.abort() khi sync error, xử lý ProfileDeletedConflictError
    └── worker/
        └── py-worker.js # Xử lý nạp lazy wheels và phản hồi trạng thái
scripts/
└── build_web.py         # Cập nhật sinh sw.js động tách PRECACHE_URLS và OPTIONAL_LAZY_URLS
tests/
├── test_build_web.py    # Kiểm thử phân tách PRECACHE_URLS vs OPTIONAL_LAZY_URLS và cấu trúc sw.js
├── js/
│   ├── storage.test.mjs           # Unit tests cho 3-state OCC, delete resurrection, sync error abort
│   └── worker_resilience.test.mjs # Unit tests cho recoverWorker, onmessageerror, timeout recovery
└── e2e/
    └── multitab.spec.ts           # E2E Playwright cho cuộc đua đồng thời thực sự giữa 2 tab
```

**Structure Decision**: Giữ nguyên kiến trúc module ES tĩnh của Web Client, không thêm layer trừu tượng mới. Mọi sửa đổi bám sát các module đã có.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| Không có vi phạm | N/A | Thiết kế hoàn toàn tuân thủ KISS, YAGNI và quy chuẩn Constitution |
