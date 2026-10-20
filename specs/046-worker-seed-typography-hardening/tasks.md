# Tasks: Worker Resilience, Seed Integrity & Typography Hardening

**Branch**: `046-worker-seed-typography-hardening` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Thiết lập môi trường và cấu trúc khung kiểm thử cho cả JavaScript và Python

- [x] T001 Xác nhận môi trường thực thi và kiểm tra baseline test suite hiện có trong `pytest.ini` và `package.json`
- [x] T002 [P] Khởi tạo khung file kiểm thử JavaScript Worker resilience trong `tests/test_worker_resilience.mjs`
- [x] T003 [P] Khởi tạo khung file kiểm thử Python hệ thống gia cố trong `tests/test_system_hardening_feature_046.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Hạ tầng lõi điều phối vòng đời và hủy bỏ listener dùng chung cho các User Stories phía Web Client

- [ ] T004 Xây dựng cấu trúc quản lý phiên phục hồi Worker theo thế hệ (`activeRecoverySession`) trong `webapp/js/app.js`
- [ ] T005 [P] Khởi tạo cơ chế điều khiển hủy bỏ `AbortController` (`uiAbortController`) cho các bộ lắng nghe sự kiện DOM trong `webapp/js/app.js`

**Checkpoint**: Hạ tầng điều phối phiên và controller dọn dẹp đã sẵn sàng cho triển khai User Stories.

---

## Phase 3: User Story 1 - Phục hồi Worker an toàn và triệt tiêu nguy cơ treo vô thời hạn (Priority: P1) 🎯 MVP

**Goal**: Quản lý phiên phục hồi theo thế hệ Worker, bảo đảm Promise luôn giải quyết dứt điểm đúng 1 lần khi thế hệ bị thay đổi giữa chừng; bộ đếm thời gian bao bọc cả giai đoạn `READY` và khởi tạo giao diện sau đó, cờ `isRecovering` luôn được giải phóng và nút "Thử lại" không bao giờ bị kẹt.

**Independent Test**: Chạy `node tests/test_worker_resilience.mjs`, mô phỏng tình huống Worker gửi `READY` khi thế hệ `workerGeneration` đã bị thay đổi; xác nhận `recoverWorker()` hoàn tất, `isRecovering === false` và nút "Thử lại" khả dụng.

### Tests for User Story 1

- [x] T006 [P] [US1] Viết unit tests kiểm chứng giải quyết Promise khi Worker generation thay đổi và timeout bảo vệ toàn diện trong `tests/test_worker_resilience.mjs`

### Implementation for User Story 1

- [x] T007 [US1] Tái cấu trúc hàm `recoverWorker()` quản lý `activeRecoverySession` và bảo đảm giải quyết Promise đúng một lần trong `webapp/js/app.js`
- [x] T008 [US1] Duy trì và mở rộng bộ đếm thời gian `recoveryTimeout` bao bọc cả tín hiệu `READY` lẫn hàm `onWorkerReady()` trong `webapp/js/app.js`
- [x] T009 [US1] Xử lý hủy bỏ phiên cũ khi thế hệ bị thay thế (`generation !== workerGeneration`) và bảo đảm giải phóng `isRecovering` trong khối `finally` của `webapp/js/app.js`

**Checkpoint**: User Story 1 hoàn thành độc lập - luồng phục hồi Worker không bao giờ bị treo vô hạn.

---

## Phase 4: User Story 2 - Idempotent UI Event Listeners và dọn dẹp bộ lắng nghe khi khởi tạo thất bại (Priority: P1)

**Goal**: Đảm bảo các hàm khởi tạo giao diện (`initBankTab`, `initWriteTab`, `initTeachTab`) có tính lũy suy (idempotent) hoặc được dọn dẹp bằng `AbortController`, loại bỏ hoàn toàn hiện tượng gắn trùng listener khi khởi tạo thất bại rồi thử lại.

**Independent Test**: Chạy `node tests/test_worker_resilience.mjs`, mô phỏng 3 chu kỳ khởi tạo giao diện thất bại liên tiếp rồi khởi tạo thành công; kích hoạt sự kiện click trên các nút Xuất file / Viết chữ và xác nhận mỗi hành động chỉ kích hoạt đúng 1 lần.

### Tests for User Story 2

- [x] T010 [P] [US2] Viết unit tests kiểm chứng tính idempotent và không nhân bản listener khi gọi `initBankTab` và `initWriteTab` nhiều lần trong `tests/test_worker_resilience.mjs`

### Implementation for User Story 2

- [x] T011 [P] [US2] Thêm hỗ trợ `AbortSignal` và cờ kiểm tra gắn kết (`__hasListener`) cho các phần tử DOM trong `webapp/js/bank.js`
- [x] T012 [P] [US2] Thêm hỗ trợ `AbortSignal` và cờ kiểm tra gắn kết (`__hasListener`) cho các phần tử DOM trong `webapp/js/write.js`
- [x] T013 [US2] Tích hợp chu trình `uiAbortController.abort()` và khởi tạo lại an toàn trong `onWorkerReady()` của `webapp/js/app.js`

**Checkpoint**: User Story 2 hoàn thành độc lập - các phần tử UI không bao giờ bị gắn trùng lặp listener.

---

## Phase 5: User Story 3 - Cô lập Seed Namespace cho Heading, Table MathBlock và Chunk Sub-index (Priority: P2)

**Goal**: Tách biệt không gian tên seed của `Heading` (`heading`) độc lập với `Paragraph` (`text`), chuyển tiếp đầy đủ `occurrence` và `stable_id` của `MathBlock` trong ô bảng, và phân biệt định danh hình học của từng chunk trong token dài.

**Independent Test**: Chạy `pytest tests/test_system_hardening_feature_046.py -k "test_seed"`, xác nhận việc chèn đoạn văn không làm đổi nét tiêu đề, công thức trong bảng giữ nguyên seed khi chèn nội dung trước bảng, và các chunk lặp có định danh hình học riêng biệt.

### Tests for User Story 3

- [x] T014 [P] [US3] Viết tests kiểm chứng cô lập seed Heading, chuyển tiếp MathBlock trong ô bảng và định danh hình học chunk trong `tests/test_system_hardening_feature_046.py`

### Implementation for User Story 3

- [x] T015 [P] [US3] Phân tách nhánh `isinstance(block, Heading)` với tiền tố ngữ cảnh `context_prefix="heading"` trong `chuviettay/document/ir.py`
- [x] T016 [US3] Truyền `context_prefix="heading"` khi kết xuất `Heading` và chuyển tiếp `occurrence`/`stable_id` khi tạo `MathInline` trong ô bảng trong `chuviettay/layout/engine.py`
- [x] T017 [US3] Gán `RenderItem.token_id = f"{ctx.token_id}:{chunk_idx}"` cho các token dài chia nhiều chunk trong `chuviettay/layout/engine.py`

**Checkpoint**: User Story 3 hoàn thành độc lập - tính toàn vẹn và bất biến cục bộ của seed được bảo đảm 100%.

---

## Phase 6: User Story 4 - Chuẩn hóa hình học số học bền vững, thu hẹp khoảng cách dấu âm và đồng bộ đo lường (Priority: P2)

**Goal**: Co giãn tỷ lệ thích ứng cho các mẫu chữ số cực đoan về chiều cao chuẩn `1.20 * xh`, thu hẹp khoảng cách dấu âm `-` đứng đầu số về dải tự nhiên `0.05 * xh .. 0.12 * xh`, và đồng bộ hóa 100% khoảng cách đo lường trong `measure_text_width()` với hàm `number()`.

**Independent Test**: Chạy `pytest tests/test_system_hardening_feature_046.py -k "test_typography"`, xác nhận mẫu chữ số dị biệt đạt dải `[1.05 * xh, 1.30 * xh]`, khoảng cách sau dấu `-` thu hẹp `<= 0.12 * xh`, và sai lệch giữa `measure_text_width` và `number()` cho số thập phân `<= 0.05 * xh`.

### Tests for User Story 4

- [x] T018 [P] [US4] Viết tests kiểm chứng co giãn mẫu số cực đoan, khoảng cách dấu âm số học và đồng bộ đo độ rộng số thập phân trong `tests/test_system_hardening_feature_046.py`

### Implementation for User Story 4

- [x] T019 [US4] Cải tiến `_normalize_digit_sample()` áp dụng tỷ lệ co giãn thích ứng trực tiếp `scale_y = clamp(target_h / sample_h, 0.10, 15.0)` và phòng vệ mẫu rỗng trong `chuviettay/model/writer.py`
- [x] T020 [US4] Bổ sung điều kiện `is_hyphen = (ch == "-" or (d_idx > 0 and s[d_idx - 1] == "-"))` trong `Writer.number()` để nén khoảng cách `0.5 * dgap` sau dấu âm trong `chuviettay/model/writer.py`
- [x] T021 [US4] Đồng bộ quy tắc khoảng cách dấu thập phân `,` / `.` và chữ số liền kề dấu âm trong `measure_text_width()` trong `chuviettay/model/writer.py`

**Checkpoint**: User Story 4 hoàn thành độc lập - hình học chữ số, số âm và số thập phân hiển thị tự nhiên, chuẩn xác.

---

## Phase 7: User Story 5 - Xác thực CI, kiểm thử Resilience, Seed Integrity và Typography (Priority: P2)

**Goal**: Chạy toàn bộ bộ kiểm thử tự động (JavaScript và Python), bảo đảm 100% vượt qua không lỗi hồi quy, đáp ứng đầy đủ các tiêu chuẩn kiểm thử của dự án.

**Independent Test**: Chạy toàn bộ `pytest`, chạy `node tests/test_worker_resilience.mjs` và chạy `node scripts/test_golden_pyodide.mjs` với 0 lỗi phát sinh.

- [x] T022 [P] [US5] Chạy và xác thực toàn bộ bài kiểm thử JavaScript Worker resilience và Idempotent UI trong `tests/test_worker_resilience.mjs`
- [x] T023 [P] [US5] Chạy và xác thực toàn bộ bài kiểm thử Python hệ thống gia cố trong `tests/test_system_hardening_feature_046.py`
- [x] T024 [US5] Chạy toàn bộ test suite pytest hiện có (1259+ tests) đảm bảo zero regression trên toàn bộ dự án
- [x] T025 [US5] Chạy bộ kiểm thử Pyodide Golden Master trong `scripts/test_golden_pyodide.mjs` đảm bảo kết xuất trên WebAssembly hoàn toàn trùng khớp

**Checkpoint**: Toàn bộ hệ thống kiểm thử tự động vượt qua thành công 100%.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Hoàn thiện tài liệu, dọn dẹp mã nguồn và kiểm chứng toàn diện

- [x] T026 [P] Cập nhật hướng dẫn kiểm thử và các kịch bản kiểm tra nghiệm thu trong `specs/046-worker-seed-typography-hardening/quickstart.md`
- [x] T027 Dọn dẹp log debug, rà soát code linting và kiểm tra tính nhất quán mã nguồn trên tất cả các file bị ảnh hưởng

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc - bắt đầu ngay lập tức
- **Foundational (Phase 2)**: Phụ thuộc vào Setup - ngăn chặn các User Stories về Web
- **User Stories (Phase 3+)**:
  - **US1 (Worker Recovery)**: Phụ thuộc vào Phase 2 (Foundational)
  - **US2 (Idempotent UI)**: Phụ thuộc vào Phase 2 (Foundational) và US1
  - **US3 (Seed Isolation)**: Có thể thực hiện song song với US1/US2 (khác hoàn toàn codebase Python vs JS)
  - **US4 (Typography Hardening)**: Có thể thực hiện song song với US1/US2/US3 (tập trung vào `writer.py`)
  - **US5 (CI Verification)**: Phụ thuộc vào việc hoàn tất US1, US2, US3, US4
- **Polish (Phase 8)**: Phụ thuộc vào việc hoàn tất toàn bộ các User Stories

### User Story Dependencies

- **US1 (P1)**: Phục hồi Worker - độc lập trên `webapp/js/app.js`
- **US2 (P1)**: Idempotent Listeners - kế thừa cấu trúc từ US1, tác động `bank.js`, `write.js`, `app.js`
- **US3 (P2)**: Seed Isolation - độc lập trên `ir.py`, `engine.py`
- **US4 (P2)**: Typography Hardening - độc lập trên `writer.py`
- **US5 (P2)**: CI Verification - chạy kiểm thử tổng hợp cho US1–US4

---

## Parallel Execution Examples

### Song song theo ngôn ngữ / module

```bash
# Nhóm Web Client (JavaScript):
Task: T007 "Tái cấu trúc hàm recoverWorker() trong webapp/js/app.js"
Task: T011 "Thêm hỗ trợ AbortSignal trong webapp/js/bank.js"
Task: T012 "Thêm hỗ trợ AbortSignal trong webapp/js/write.js"

# Nhóm Python Layout & Typography (chạy song song độc lập):
Task: T015 "Phân tách nhánh Heading trong chuviettay/document/ir.py"
Task: T019 "Cải tiến _normalize_digit_sample() trong chuviettay/model/writer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 & User Story 2)
1. Hoàn thành Phase 1 (Setup) và Phase 2 (Foundational).
2. Hoàn thành Phase 3 (US1 - Worker Recovery Resilience) -> Giải quyết dứt điểm lỗi treo ứng dụng P1.
3. Hoàn thành Phase 4 (US2 - Idempotent Listeners) -> Giải quyết lỗi nhân bản thao tác P1.
4. Kiểm chứng độc lập MVP Web Client qua `node tests/test_worker_resilience.mjs`.

### Gia cố Seed & Bố cục số học (User Story 3 & User Story 4)
5. Hoàn thành Phase 5 (US3 - Seed Isolation) -> Bảo đảm tính toàn vẹn seed của Heading và MathBlock.
6. Hoàn thành Phase 6 (US4 - Typography Hardening) -> Chuẩn hóa mẫu số dị biệt và dấu âm.
7. Chạy bộ test chuyên biệt `pytest tests/test_system_hardening_feature_046.py`.

### Kiểm chứng tổng thể & Bàn giao (User Story 5 & Phase 8)
8. Chạy toàn diện 1259 tests pytest + Pyodide Golden Master.
9. Dọn dẹp mã và cập nhật tài liệu kiểm chứng `quickstart.md`.
