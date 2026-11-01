---
description: "Task list for Feature 070: Render Generation, Import Seed Reset & Test Hardening"
---

# Tasks: Feature 070 - Render Generation, Import Seed Reset & Test Hardening

**Input**: Design documents from `specs/070-render-generation-import-seed-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Prerequisites**: `spec.md` (required), `plan.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  

---

## Phase 1: Setup (Môi trường & Tiền điều kiện)

**Purpose**: Xác nhận môi trường thực thi và trạng thái sạch của kho mã nguồn trước khi triển khai.

- [x] T001 Kiểm tra môi trường Node.js, Python, Playwright và xác nhận nhánh git `070-render-generation-import-seed-hardening` sạch sẽ

---

## Phase 2: Foundational (Hạ tầng cốt lõi & Hợp đồng giao tiếp)

**Purpose**: Xây dựng hàm helper chuẩn hóa giao tiếp Worker và truyền tải thế hệ kết xuất (`requestId`).

**⚠️ CRITICAL**: Các User Stories phía sau phụ thuộc vào các hợp đồng cơ sở này.

- [x] T002 Cập nhật `webapp/js/worker/py-worker.js` tiếp nhận trường `requestId` trong tham số `write_text` và phản hồi lại `requestId` trong kết quả `result`
- [x] T003 Xây dựng hàm `resetDocumentSeedHistory()` chuẩn hóa trong `webapp/js/write.js`, kiểm tra phản hồi tường minh `{ ok: true }` từ Worker và ghi log cảnh báo khi gặp lỗi

**Checkpoint**: Hạ tầng thông điệp Worker và hàm reset seed đã sẵn sàng cho các User Stories.

---

## Phase 3: User Story 1 - Ngăn chặn kết quả kết xuất cũ ghi đè lên tài liệu mới (Priority: P1) 🎯 MVP

**Goal**: Triển khai cơ chế thế hệ kết xuất (`renderGeneration` / `requestId`) tăng đơn điệu và Two-Layer Stale Guard trong `write.js`, loại bỏ ngay tức thì các kết quả kết xuất cũ khi nội dung textarea đã thay đổi sang tài liệu khác hoặc bị xóa trắng.

**Independent Test**: Chạy bài kiểm thử đơn vị Node.js `tests/js/render_generation.test.mjs` xác nhận kết quả cũ của tài liệu A bị hủy bỏ khi tài liệu B được yêu cầu.

### Tests cho User Story 1 (TDD - Viết test trước) 🧪

- [x] T004 [P] [US1] Viết bài kiểm thử đơn vị Node.js trong `tests/js/render_generation.test.mjs` kiểm chứng cơ chế Two-Layer Stale Guard (hủy kết quả cũ `thisGeneration !== currentRenderGeneration`, hủy khi textarea khác nội dung snapshot)

### Implementation cho User Story 1

- [x] T005 [US1] Khởi tạo biến trạng thái `currentRenderGeneration = 0` và `currentRenderSnapshot = null` trong `webapp/js/write.js`
- [x] T006 [US1] Tái cấu trúc hàm `requestRender(params)` trong `webapp/js/write.js` tăng `currentRenderGeneration++` ngay khi phát sinh yêu cầu mới (kể cả khi bị đưa vào hàng chờ `pendingParams`) và lưu trữ `currentRenderSnapshot`
- [x] T007 [US1] Cập nhật hàm `clearPreview()` trong `webapp/js/write.js` tự động tăng `currentRenderGeneration++` để vô hiệu hóa lập tức bất kỳ kết quả render nào đang chạy dở dang
- [x] T008 [US1] Cập nhật khối `try...finally` của `requestRender()` trong `webapp/js/write.js` áp dụng Two-Layer Stale Guard: bỏ qua kết quả cũ nếu `thisGeneration !== currentRenderGeneration` hoặc `textarea.value !== currentRenderSnapshot.text`
- [x] T009 [US1] Chạy kiểm thử đơn vị Node.js `node --test tests/js/render_generation.test.mjs` xác nhận toàn bộ các kịch bản kiểm tra Stale Guard đạt 100% PASS

**Checkpoint**: User Story 1 hoàn tất độc lập. Hiện tượng ghi đè render cũ được triệt tiêu hoàn toàn.

---

## Phase 4: User Story 2 - Kiểm chứng E2E việc xóa sạch lịch sử seed khi mở tài liệu mới và Race Condition (Priority: P1)

**Goal**: Xây dựng các kịch bản kiểm thử tự động đầu-cuối (E2E) trên trình duyệt bằng Playwright, chứng minh toán học việc mở tệp mới (.txt, .md, .docx) luôn xóa sạch lịch sử seed (occurrence = 0) và xử lý an toàn race condition nạp tệp khi đang render dở dang.

**Independent Test**: Chạy `npx playwright test tests/e2e/write.spec.ts` xác nhận 100% kịch bản kiểm thử E2E về reset seed và race condition đều xanh.

### Implementation & Test cho User Story 2

- [x] T010 [US2] Nâng cấp bài test E2E trong `tests/e2e/write.spec.ts`: viết tài liệu A có từ lặp `"xin xin chào ba"` (từ `"xin"` thứ hai có occurrence 1), sau đó mở tệp văn bản mới chứa từ `"xin"` và đối sánh hình thái nét vẽ khẳng định trùng khớp 100% với occurrence 0 (không kế thừa occurrence 1)
- [x] T011 [US2] Bổ sung kịch bản kiểm thử E2E trong `tests/e2e/write.spec.ts` cho việc mở tệp Markdown (`.md`) và tệp Word (`.docx`), xác nhận lệnh `resetDocumentSeedHistory` được kích hoạt và tài liệu mới hiển thị chính xác
- [x] T012 [US2] Bổ sung kịch bản kiểm thử E2E race condition trong `tests/e2e/write.spec.ts`: gửi render văn bản dài, ngay lập tức nạp tệp mới trong vòng 50ms, xác nhận giao diện chỉ hiển thị nội dung tệp mới, không bị chớp tắt hoặc ghi đè nét vẽ của văn bản cũ
- [x] T013 [US2] Thực thi bộ kiểm thử E2E bằng lệnh `npx playwright test tests/e2e/write.spec.ts` xác nhận toàn bộ các kịch bản đều đạt PASS

**Checkpoint**: User Story 2 hoàn tất độc lập. Tính độc lập hạt giống và xử lý race condition khi mở file được kiểm chứng E2E chặt chẽ.

---

## Phase 5: User Story 3 - Tăng cường độ bền vững cho kiểm thử hình thái nét vẽ (Priority: P2)

**Goal**: Thay thế các chỉ số mảng cố định (`strokes1[0:3]`, `strokes1[6:11]`) bằng hàm gom nhóm nét theo khoảng cách trục X (`group_strokes_by_word_proximity`), giúp test bền vững khi bộ mẫu chữ thay đổi.

**Independent Test**: Chạy `pytest tests/test_stable_variants.py -k "test_app_controller_stable_variants_workflow" -v` xác nhận việc gom nhóm nét và so sánh từ ngữ độc lập đạt PASS.

### Implementation & Test cho User Story 3

- [x] T014 [P] [US3] Xây dựng hàm trợ giúp `group_strokes_by_word_proximity(strokes, min_gap=4.0)` trong `tests/test_stable_variants.py` tự động phân tách danh sách stroke XML thành các nhóm từ ngữ dựa trên khoảng cách tọa độ trục X
- [x] T015 [US3] Nâng cấp bài kiểm thử `test_app_controller_stable_variants_workflow` trong `tests/test_stable_variants.py` sử dụng hàm nhóm nét động để so sánh từ ngữ `"xin"`, `"chào"`, và kiểm tra hình thái nét tương đối của `"ba"`
- [x] T016 [US3] Chạy kiểm thử Python `pytest tests/test_stable_variants.py -k "test_app_controller_stable_variants_workflow" -v` xác nhận PASS

**Checkpoint**: User Story 3 hoàn tất. Bộ kiểm thử hình thái nét chữ đạt độ tin cậy và khả năng bảo trì bền vững.

---

## Phase 6: User Story 4 - Chuẩn hóa chú thích và số liệu đo kiểm hiệu năng Kho mẫu đa biến thể (Priority: P3)

**Goal**: Đồng bộ hóa chú thích docstring và log console trong `test_bank_snapshot_large_scale_performance` với đúng cấu trúc dữ liệu: 1.050+ nhãn và 3.520 mẫu nét (thay vì ghi 3.420).

**Independent Test**: Chạy `pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s` xác nhận log in 3.520 mẫu nét và $t < 200$ ms.

### Implementation & Test cho User Story 4

- [x] T017 [P] [US4] Cập nhật docstring và log in console trong `tests/test_performance_regression.py` thành `1.050+ nhãn và 3.520 mẫu nét đa biến thể`
- [x] T018 [US4] Chạy `pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s` xác nhận PASS và thời gian $< 200$ ms

**Checkpoint**: User Story 4 hoàn tất. Tài liệu đo kiểm kỹ thuật và mã nguồn đạt tính nhất quán 100%.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Đóng gói phân phối web sạch và kiểm thử hồi quy toàn diện trên toàn bộ kho mã nguồn.

- [x] T019 Đóng gói phân phối tĩnh Web Client sạch bằng `python scripts/build_web.py`
- [x] T020 Chạy kiểm tra ruff lint `python -m ruff check chuviettay tests`
- [x] T021 Chạy kiểm thử đơn vị & Golden Master Node.js (`npm run test:unit`, `npm run test:browser`, `npm run test:golden`)
- [x] T022 Chạy kiểm thử hồi quy toàn diện Playwright E2E (`npx playwright test`) đảm bảo toàn bộ bài test đạt 100% PASS
- [x] T023 Chạy kiểm thử hồi quy toàn diện bộ test Python (`pytest`) đảm bảo toàn bộ bài test đạt 100% PASS
- [x] T024 [P] Cập nhật bảng ghi nhận kết quả kiểm chứng thực tế trong `specs/070-render-generation-import-seed-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc — chạy đầu tiên.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup — **CHẶN** tất cả các User Stories.
- **User Stories (Phase 3+)**: Phụ thuộc vào hoàn tất Phase 2.
  - Thực thi tuần tự theo mức độ ưu tiên: US1 (P1 - MVP) $\to$ US2 (P1) $\to$ US3 (P2) $\to$ US4 (P3).
- **Polish (Phase 7)**: Phụ thuộc vào toàn bộ 4 User Stories đã hoàn thành.

### User Story Dependencies

- **User Story 1 (P1)**: Phụ thuộc Phase 2 (T002, T003). Độc lập với US2, US3, US4.
- **User Story 2 (P1)**: Phụ thuộc Phase 2 và tích hợp với cơ chế generation của US1.
- **User Story 3 (P2)**: Phụ thuộc Phase 2. Độc lập với US1, US2, US4.
- **User Story 4 (P3)**: Phụ thuộc Phase 2. Độc lập với US1, US2, US3.

### Parallel Opportunities

- **Setup & Foundational**: T002 và T003 có thể viết song song.
- **User Story 1**: T004 (Unit test Node.js) viết trước song song với việc chuẩn bị logic.
- **User Story 3 & 4**: T014 (Python helper) và T017 (Benchmark docstring) có thể viết song song.
- **Polish**: T024 có thể cập nhật song song khi các bài test hoàn thành.

---

## Parallel Example: User Story 1

```bash
# Viết bài test đơn vị Node.js kiểm chứng Two-Layer Stale Guard:
Task: "T004 [P] [US1] Viết bài kiểm thử đơn vị Node.js trong tests/js/render_generation.test.mjs"

# Triển khai song song logic quản lý thế hệ trong write.js:
Task: "T005 [US1] Khởi tạo biến trạng thái currentRenderGeneration trong webapp/js/write.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1: Setup (T001)
2. Hoàn thành Phase 2: Foundational (T002, T003)
3. Hoàn thành Phase 3: User Story 1 (T004 $\to$ T009)
4. **DỪNG LẠI & XÁC THỰC**: Chạy `node --test tests/js/render_generation.test.mjs` xác nhận giải quyết triệt để race condition ghi đè render cũ.

### Incremental Delivery

1. Setup + Foundational $\to$ Sẵn sàng nền tảng.
2. User Story 1 $\to$ Kiểm chứng Stale Guard $\to$ Đóng gói MVP!
3. User Story 2 $\to$ Kiểm chứng E2E Playwright cho tệp .txt, .md, .docx và race condition.
4. User Story 3 $\to$ Bền vững hóa assertion kiểm thử nét vẽ theo từ.
5. User Story 4 $\to$ Chuẩn hóa chú thích benchmark 3.520 mẫu nét.
6. Phase 7 $\to$ Build dist sạch và chạy toàn diện 100% test suite trước khi nghiệm thu.
