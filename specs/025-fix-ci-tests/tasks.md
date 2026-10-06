# Tasks: 025 — Sửa lỗi CI Kiểm Thử Tự Động (Playwright E2E & GUI Tkinter)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Setup (Chuẩn bị môi trường & Phân tích Patch)

**Purpose**: Xác thực các tệp vá đầu vào và chuẩn bị môi trường kiểm thử

- [x] T001 Kiểm tra nội dung hai tệp vá `local data/fix-sw-update.patch` và `local data/fix_test_gui.patch`
- [x] T002 [P] Xác nhận trạng thái git làm việc sạch sẽ trước khi áp dụng các thay đổi

---

## Phase 2: Foundational (Hạ tầng Server Tĩnh Độc lập)

**Purpose**: Nâng cấp máy chủ HTTP tĩnh `scripts/serve.mjs` hỗ trợ cấu hình runtime và an toàn thư mục

**⚠️ CRITICAL**: Phải hoàn thành trước khi triển khai cách ly test E2E của User Story 1

- [x] T003 Cập nhật `scripts/serve.mjs` nhận `PORT` và `DIST_DIR` từ biến môi trường (`process.env.PORT || 8000`, `process.env.DIST_DIR || 'webapp/dist'`)
- [x] T004 Thêm cơ chế giải mã URL `decodeURIComponent()` với try/catch trả về HTTP 400 và chặn path traversal ra ngoài `DIST_DIR` trả về HTTP 403 trong `scripts/serve.mjs`

**Checkpoint**: `scripts/serve.mjs` có thể phục vụ bất kỳ thư mục dist nào trên bất kỳ cổng nào một cách an toàn.

---

## Phase 3: User Story 1 - Ổn định hóa kiểm thử E2E Service Worker Update (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo test `sw-update.spec.ts` chạy thành công trên mọi hệ điều hành (không bị lỗi `/bin/sh: 1: py: not found`) và an toàn tuyệt đối khi chạy đa luồng (`--workers=2`).

**Independent Test**: Chạy `npx playwright test tests/e2e/sw-update.spec.ts` và kiểm tra toàn bộ 14 tests với `npx playwright test --workers=2`.

### Implementation for User Story 1

- [x] T005 [US1] Xây dựng helper `runBuildWeb(distDir: string)` trong `tests/e2e/sw-update.spec.ts` tự động phát hiện Python interpreter (`process.env.PYTHON`, `py -3` trên win32, `python3`, `python`)
- [x] T006 [US1] Xây dựng helper `waitForServer(url: string, timeoutMs: number)` trong `tests/e2e/sw-update.spec.ts` để thăm dò server con sẵn sàng
- [x] T007 [US1] Cấu hình môi trường cách ly trong `tests/e2e/sw-update.spec.ts`: tạo `tmpDist` bằng `fs.mkdtempSync()`, khởi chạy tiến trình server con `serve.mjs` trên cổng `8101` (`SW_PORT = 8101`)
- [x] T008 [US1] Cập nhật kịch bản kiểm thử `tests/e2e/sw-update.spec.ts` trỏ tới `http://localhost:8101/`, build cập nhật vào `tmpDist` và kiểm tra băm cache mới
- [x] T009 [US1] Hoàn thiện khối dọn dẹp `finally` trong `tests/e2e/sw-update.spec.ts`: khôi phục file `webapp/js/app.js`, kill server con và xoá thư mục `tmpDist`

**Checkpoint**: User Story 1 hoàn thành độc lập, Playwright có thể chạy đa worker song song mà không xung đột tài nguyên.

---

## Phase 4: User Story 2 - Cập nhật kiểm thử GUI Tkinter theo Bộ Ký Tự Mới (Priority: P1)

**Goal**: Cập nhật `tests/test_gui.py` phản ánh đúng hộp thoại chọn bộ ký tự Toplevel mới từ Feature 024, loại bỏ kiểm tra mock cũ gây lỗi `AssertionError` trên CI có Xvfb.

**Independent Test**: Chạy `pytest -v -k "test_nap_bo_ky_tu_co_ban or test_huy_bo_ky_tu_khong_them_gi" tests/test_gui.py`.

### Implementation for User Story 2

- [x] T010 [US2] Xây dựng helper `_bam_nut_trong_hop_thoai_bo_ky_tu(t, nhan)` trong `tests/test_gui.py` để tìm và kích hoạt nút `TButton` trong cửa sổ `Toplevel`
- [x] T011 [US2] Thay thế bài test cũ `test_nap_tu_thong_dung` bằng `test_nap_bo_ky_tu_co_ban(app, dlg)` trong `tests/test_gui.py`
- [x] T012 [US2] Bổ sung bài test `test_huy_bo_ky_tu_khong_them_gi(app, dlg)` trong `tests/test_gui.py` để xác nhận huỷ dialog giữ nguyên hàng đợi
- [x] T013 [US2] Dọn dẹp import thừa `simpledialog` trong `tests/test_gui.py`

**Checkpoint**: User Story 2 hoàn thành, kiểm thử GUI xanh 100% khi chạy trên môi trường có Tk/Tcl hoặc Xvfb.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm tra chất lượng toàn diện, linter và đảm bảo không phá vỡ quy tắc kiến trúc

- [x] T014 [P] Kiểm tra linter bằng `ruff check .` bảo đảm 0 lỗi
- [x] T015 [P] Chạy kiểm tra kiến trúc MVC qua `pytest -q tests/test_architecture.py`
- [x] T016 Chạy toàn bộ test suite `pytest -q`
- [x] T017 Chạy toàn bộ test suite Playwright `npx playwright test --workers=2`
- [x] T018 Build lại static web assets bằng `python scripts/build_web.py` để đảm bảo dist sạch sẽ
- [x] T019 Xác nhận trạng thái git và thực hiện commit hoàn thiện

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Bắt đầu ngay lập tức.
- **Foundational (Phase 2)**: Cần thiết trước khi thực hiện `sw-update.spec.ts` của Phase 3.
- **User Story 1 (Phase 3)**: Phụ thuộc vào Phase 2 (`scripts/serve.mjs`).
- **User Story 2 (Phase 4)**: Độc lập với Phase 2 và Phase 3, có thể làm đồng thời hoặc tiếp nối.
- **Polish (Phase 5)**: Thực hiện sau khi cả hai User Story hoàn thành.

### Parallel Opportunities

- T003 và T004 được thực hiện trên `scripts/serve.mjs`.
- T010, T011, T012, T013 được thực hiện trên `tests/test_gui.py` độc lập với E2E.
- T014 (`ruff check`) và T015 (`test_architecture.py`) có thể chạy song song.

---

## Implementation Strategy

### MVP Scope (User Story 1 First)
1. Cập nhật `scripts/serve.mjs` (T003, T004).
2. Nâng cấp `tests/e2e/sw-update.spec.ts` (T005 → T009).
3. Chạy Playwright đa worker để xác nhận MVP giải quyết xong lỗi CI blocker lớn nhất.

### Incremental Delivery
1. Sau khi MVP xanh, cập nhật tiếp `tests/test_gui.py` (T010 → T013).
2. Chạy toàn bộ test suite Pytest và E2E với 2 workers.
3. Hoàn tất với Phase 5 Polish và Commit.
