# Tasks: Củng cố Phục hồi Worker, Quản lý Vòng đời Giao diện và Đo đạc Chữ số Đa biến thể

**Input**: Design documents from `specs/048-worker-recovery-ui-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Hợp nhất tệp kiểm thử mồ côi và chuẩn hóa cấu trúc thư mục kiểm thử.

- [X] T001 Hợp nhất toàn bộ các ca kiểm thử từ `tests/test_worker_resilience.mjs` vào `tests/js/worker_resilience.test.mjs` và xóa tệp mồ côi `tests/test_worker_resilience.mjs`
- [X] T002 [P] Xác minh cấu hình script `test:unit` trong `package.json` bao phủ toàn bộ các tệp kiểm thử `tests/js/*.test.mjs`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cơ sở hạ tầng mock test cho Worker lifecycle, UI AbortSignal và Typography fixtures.

- [X] T003 Cập nhật `setupMockDocument` trong `tests/js/worker_resilience.test.mjs` hỗ trợ đầy đủ `ResizeObserver`, `document.addEventListener/removeEventListener` và `AbortSignal`
- [X] T004 [P] Thiết lập fixture kiểm thử kho mẫu đa biến thể chữ số và mẫu suy biến (`sample_h <= 1e-3`) trong `tests/test_system_hardening_feature_046.py`

**Checkpoint**: Nền tảng kiểm thử và cấu trúc tệp đã sẵn sàng - có thể triển khai độc lập các User Stories.

---

## Phase 3: User Story 1 - Worker Recovery Session Isolation (Priority: P1) 🎯 MVP

**Goal**: Loại bỏ hoàn toàn race condition trong `recoverWorker()` khi phiên cũ kết thúc trong lúc phiên mới đang chạy.

**Independent Test**: Kích hoạt phiên phục hồi A, ngay sau đó kích hoạt phiên B (`force: true`). Khi A kết thúc, xác nhận `isRecovering === true`, `recoveryPromise` vẫn gắn với B, nút "Thử lại" vẫn bị vô hiệu hóa.

### Tests for User Story 1
- [X] T005 [P] [US1] Bổ sung ca kiểm thử trong `tests/js/worker_resilience.test.mjs` kiểm tra trạng thái trung gian (`isRecovering === true`, `btnRetry.disabled === true`) ngay khi phiên cũ kết thúc nhưng phiên mới đang chờ

### Implementation for User Story 1
- [X] T006 [US1] Cập nhật khối `finally` trong `recoverWorker()` tại `webapp/js/app.js` bảo vệ bằng điều kiện `if (activeRecoverySession === session)`
- [X] T007 [US1] Kích hoạt `uiAbortController.abort()` và đặt `isDomListenersAttached = false` ngay khi bắt đầu `recoverWorker()` tại `webapp/js/app.js`
- [X] T008 [US1] Chạy `node --test tests/js/worker_resilience.test.mjs` xác nhận các ca kiểm thử US1 vượt qua 100%

**Checkpoint**: User Story 1 hoàn thành độc lập, bảo vệ tuyệt đối trạng thái phục hồi đa phiên.

---

## Phase 4: User Story 2 - CI Integration for Worker Resilience (Priority: P1)

**Goal**: Đảm bảo 100% các bài test Worker resilience được tự động thực thi trong CI qua `npm run test:unit`.

**Independent Test**: Chạy `npm run test:unit` từ terminal; toàn bộ các ca kiểm thử kiên cường Worker trong `tests/js/worker_resilience.test.mjs` được phát hiện và vượt qua.

### Implementation for User Story 2
- [X] T009 [US2] Kiểm tra đường dẫn và cú pháp import trong `tests/js/worker_resilience.test.mjs` tương thích với môi trường chạy `node --test` của CI
- [X] T010 [US2] Chạy `npm run test:unit` và kiểm tra báo cáo kết quả CI, xác nhận không còn bài kiểm thử nào bị bỏ sót

**Checkpoint**: Bộ kiểm thử Web Worker được tích hợp hoàn toàn vào quy trình CI.

---

## Phase 5: User Story 3 - Full UI Event Listener & Observer Teardown (Priority: P2)

**Goal**: Thu hồi triệt để toàn bộ trình lắng nghe sự kiện DOM, phím tắt toàn cục và quan sát viên bố cục khi UI làm mới hoặc hủy.

**Independent Test**: Khởi tạo UI, kích hoạt `uiAbortController.abort()`, khởi tạo lại; kiểm tra số lượng listener trên các nút, sự kiện trên `document` và trạng thái `disconnect()` của `ResizeObserver`.

### Tests for User Story 3
- [X] T011 [P] [US3] Viết các ca kiểm thử trong `tests/js/worker_resilience.test.mjs` kiểm chứng `TeachController.destroy()` gỡ bỏ listener trên `document`, `setupPreviewNavigation` ngắt kết nối `ResizeObserver` khi abort, và tính lũy đẳng của `initQuotaAndBackupReminders`

### Implementation for User Story 3
- [X] T012 [P] [US3] Bổ sung phương thức `destroy()` và quản lý listener theo `options.signal` trong `TeachCanvas` tại `webapp/js/canvas.js`
- [X] T013 [US3] Bổ sung `destroy()`, theo dõi mảng dọn dẹp và gắn `{ signal }` cho `document.addEventListener("keydown", ...)` trong `TeachController` tại `webapp/js/teach.js`
- [X] T014 [US3] Truyền `{ signal }` cho `new TeachController()` trong `onWorkerReady()` tại `webapp/js/app.js` và gọi `window.__teachController?.destroy()` trước khi thay thế
- [X] T015 [US3] Cập nhật `setupPreviewNavigation()` trong `webapp/js/write.js` quản lý biến module `previewResizeObserver`, ngắt kết nối observer cũ và lắng nghe sự kiện `abort` từ `options.signal`
- [X] T016 [US3] Đảm bảo tính lũy đẳng cho `initQuotaAndBackupReminders()` trong `webapp/js/app.js` thông qua cờ đánh dấu trên nút hoặc nhận `options.signal`
- [X] T017 [US3] Chạy `node --test tests/js/worker_resilience.test.mjs` xác nhận các ca kiểm thử US3 vượt qua 100%

**Checkpoint**: Toàn bộ rò rỉ listener và quan sát viên giao diện đã được triệt tiêu hoàn toàn.

---

## Phase 6: User Story 4 - Post-READY Initialization Timeout Worker Termination (Priority: P2)

**Goal**: Chấm dứt vật lý tiến trình Worker, tăng `workerGeneration` và hủy tham chiếu khi khởi tạo giao diện sau tín hiệu `READY` bị quá hạn.

**Independent Test**: Giả lập Worker gửi `READY` nhưng bước nạp kho bị treo quá thời hạn `initTimeout`; kiểm tra `worker.terminate()` được gọi và `workerGeneration` tăng lên.

### Tests for User Story 4
- [X] T018 [P] [US4] Bổ sung ca kiểm thử trong `tests/js/worker_resilience.test.mjs` kiểm tra `targetWorker.terminated === true` và `workerGeneration` tăng sau khi post-READY timeout kích hoạt

### Implementation for User Story 4
- [X] T019 [US4] Cập nhật bộ đếm thời gian `initTimeout` trong `attachWorkerHandlers()` tại `webapp/js/app.js` thực hiện `targetWorker.terminate()`, `workerGeneration++` và xóa tham chiếu `worker = null`
- [X] T020 [US4] Chạy `node --test tests/js/worker_resilience.test.mjs` xác nhận ca kiểm thử US4 vượt qua

**Checkpoint**: Ngăn chặn hoàn toàn sự tồn tại của các tiến trình Worker ma sau timeout.

---

## Phase 7: User Story 5 - Extreme Digit Geometry Sanitization & Multi-Variant Width Parity (Priority: P2)

**Goal**: Chuẩn hóa an toàn mẫu chữ số suy biến và đồng bộ độ rộng tính bởi `measure_text_width()` với `number()` trên mọi cấu hình kho mẫu.

**Independent Test**: Đo độ rộng `measure_text_width` vs `number` trên kho mẫu đa biến thể (sai lệch $\le 0.05 \times x_h$); kết xuất mẫu chữ số có `sample_h <= 1e-3` không ném ngoại lệ.

### Tests for User Story 5
- [X] T021 [P] [US5] Viết các ca kiểm thử trong `tests/test_system_hardening_feature_046.py` cho chữ số có chiều cao cực đoan `sample_h <= 1e-3` và kho mẫu có biến thể chữ số với độ rộng khác nhau

### Implementation for User Story 5
- [X] T022 [US5] Cập nhật `_normalize_digit_sample()` trong `chuviettay/model/writer.py` xử lý an toàn `sample_h <= 1e-3` hoặc `bbox_w <= 1e-3`, áp dụng `adv_w = max(raw_w, 0.60 * eff_xh)` và vector fallback
- [X] T023 [US5] Cập nhật `measure_text_width()` trong `chuviettay/model/writer.py` đối với chuỗi số (`NUMRE.match`) khi `stable_variants=True` mô phỏng độ rộng từ `number(..., _preserve_context=True)` có khôi phục `_token_counts` và `last`
- [X] T024 [US5] Thắt chặt các câu lệnh khẳng định (assertions) trong `tests/test_system_hardening_feature_046.py` và `tests/test_number_fraction_typography.py` dựa trên bounding box thực tế
- [X] T025 [US5] Chạy `pytest tests/test_system_hardening_feature_046.py tests/test_number_fraction_typography.py -v` xác nhận toàn bộ tests US5 vượt qua

**Checkpoint**: Khử triệt để suy biến hình học chữ số và bảo đảm đồng bộ đo đạc tuyệt đối.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Xác minh toàn diện không hồi quy trên toàn bộ hệ thống.

- [X] T026 [P] Chạy toàn bộ bộ kiểm thử Python: `pytest` (xác nhận 1265+ tests pass, 0 fail)
- [X] T027 [P] Chạy toàn bộ bộ kiểm thử Web & Browser Bridge: `npm test` (xác nhận unit, browser bridge, Pyodide golden master pass)
- [X] T028 Thực thi kịch bản kiểm tra nghiệm thu theo `quickstart.md` và rà soát mã nguồn sạch sẽ

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Không phụ thuộc, chạy đầu tiên.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1; cung cấp mock và fixtures cho các User Story.
- **User Story 1 (Phase 3 - P1 MVP)**: Khắc phục race condition cốt lõi trong `app.js`.
- **User Story 2 (Phase 4 - P1)**: Tích hợp CI và xác minh bộ test tổng hợp.
- **User Story 3 (Phase 5 - P2)**: Vòng đời listener giao diện và AbortSignal.
- **User Story 4 (Phase 6 - P2)**: Dọn dẹp Worker khi post-READY timeout.
- **User Story 5 (Phase 7 - P2)**: Lõi Python `writer.py` và typography tests.
- **Polish (Phase 8)**: Xác minh toàn bộ hệ thống sau khi hoàn thành cả 5 User Stories.

### Parallel Execution Opportunities
- **T002 [P]** có thể chạy song song với **T001**.
- **T004 [P]** có thể chuẩn bị song song với **T003**.
- **T005 [P] [US1]** viết test song song với chuẩn bị code.
- **T011 [P] [US3]** và **T012 [P] [US3]** có thể triển khai song song.
- **T018 [P] [US4]** có thể viết test độc lập với US3.
- **T021 [P] [US5]** hoàn toàn độc lập với các tác vụ JavaScript của US1, US3, US4.
- **T026 [P]** và **T027 [P]** chạy kiểm thử hồi quy song song trên hai nền tảng.

---

## Implementation Strategy: MVP First

1. **Bước 1 (MVP)**: Hoàn tất Phase 1, Phase 2 và Phase 3 (User Story 1) $\to$ Triệt tiêu hoàn toàn race condition trong phục hồi Worker.
2. **Bước 2 (CI Hardening)**: Hoàn tất Phase 4 (User Story 2) $\to$ Đảm bảo CI chạy 100% bộ test Worker.
3. **Bước 3 (UI Lifecycle Hardening)**: Hoàn tất Phase 5 và Phase 6 (User Story 3 & 4) $\to$ Sạch sẽ listener DOM, ResizeObserver và tiêu diệt Worker ma.
4. **Bước 4 (Typography Core Robustness)**: Hoàn tất Phase 7 (User Story 5) $\to$ Khử suy biến mẫu chữ số và đồng bộ sai lệch đo độ rộng $\le 0.05 \times x_h$.
5. **Bước 5 (System Verification)**: Hoàn tất Phase 8 $\to$ Chạy toàn bộ 1265+ Python tests và toàn bộ test suite Web Client.
