---
description: "Danh sách nhiệm vụ thực thi TDD cho tính năng 069-seed-reset-bank-cache-hardening"
---

# Tasks: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

**Input**: Design documents from `specs/069-seed-reset-bank-cache-hardening/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Organization**: Các nhiệm vụ được nhóm theo User Story để hỗ trợ thực thi và kiểm thử độc lập từng giai đoạn theo chuẩn TDD.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Có thể thực hiện song song (khác tệp tin, không phụ thuộc vào nhiệm vụ chưa hoàn tất).
- **[Story]**: Gắn với User Story tương ứng (`[US1]`, `[US2]`, `[US3]`, `[US4]`).
- Tất cả các nhiệm vụ đều chứa đường dẫn tệp tin cụ thể và hành động rõ ràng.

---

## Phase 1: Setup (Môi trường & Công cụ)

**Purpose**: Xác thực môi trường và công cụ thực thi trước khi bắt đầu triển khai code.

- [x] T001 Kiểm tra môi trường thực thi và kiểm thử hiện tại (`pytest`, `playwright`, `pyodide`) theo `specs/069-seed-reset-bank-cache-hardening/quickstart.md`

---

## Phase 2: Foundational (Cơ sở chung)

**Purpose**: Các thành phần hạ tầng và giao thức thông điệp chặn trước khi triển khai các User Story.

- [x] T002 Bổ sung phương thức `clear_document_history()` gọi tới `self._ctl.clear_document_history()` trong `chuviettay/browser/bridge.py`
- [x] T003 [P] Bổ sung nhánh xử lý thông điệp `"clear_document_history"` gọi tới `_bridge.clear_document_history()` trong `webapp/js/worker/py-worker.js`

**Checkpoint**: Nền tảng hạ tầng sẵn sàng — các User Story có thể bắt đầu triển khai.

---

## Phase 3: User Story 1 - Tự động xóa lịch sử hạt giống khi xóa trắng hoặc mở tài liệu mới (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo khi người dùng xóa trắng văn bản hoặc mở tệp tài liệu mới (TXT, MD, DOCX), lịch sử hạt giống của tài liệu cũ được xóa bỏ hoàn toàn, ngăn chặn việc kế thừa nhầm occurrence và triệt tiêu race condition khi xóa lúc đang render.

**Independent Test**: Soạn thảo văn bản A $\to$ xóa trắng ô soạn thảo $\to$ gõ lại văn bản A: xác nhận hình thái nét chữ của văn bản mới giống hệt lần đầu tiên viết độc lập; mở tài liệu B sau khi đã soạn tài liệu A: xác nhận các từ trong tài liệu B nhận occurrence độc lập tính từ 0.

### Tests cho User Story 1 (TDD - Viết test trước) 🧪

- [x] T004 [P] [US1] Viết unit test cho phương thức `BrowserBridge.clear_document_history()` xác nhận trả về `{"ok": True}` và đặt lại `_last_doc = None`, `_last_seed = None` trong `tests/test_bridge.py`
- [x] T005 [P] [US1] Viết kịch bản kiểm thử E2E Playwright cho tình huống xóa trắng ô soạn thảo rồi nhập lại và mở tệp tài liệu mới không kế thừa seed trong `tests/e2e/write.spec.ts`

### Implementation cho User Story 1

- [x] T006 [US1] Cập nhật `triggerPreviewImmediate()` và `clearPreview()` trong `webapp/js/write.js` gửi thông điệp `clear_document_history` khi `!text.trim()` và hủy bỏ mọi yêu cầu render chờ (`hasPendingRequest = false; pendingParams = null;`)
- [x] T007 [US1] Cập nhật hàm `requestRender()` trong `webapp/js/write.js` kiểm tra nếu nội dung ô soạn thảo hiện tại đã rỗng thì hủy bỏ việc áp dụng kết quả render muộn lên DOM
- [x] T008 [US1] Cập nhật hàm `handleFileImport()` trong `webapp/js/write.js` gửi `clear_document_history` có điều kiện sau khi tệp văn bản (TXT/MD) hoặc tệp Word (DOCX) đã được đọc/phân tích thành công
- [x] T009 [US1] Chạy kiểm thử xác nhận độc lập cho User Story 1 trong `tests/test_bridge.py` và `tests/e2e/write.spec.ts`

**Checkpoint**: User Story 1 (MVP) hoàn tất độc lập và vượt qua toàn bộ các ca kiểm thử bảo toàn trạng thái sạch khi xóa hoặc mở tài liệu.

---

## Phase 4: User Story 2 - Cập nhật bộ nhớ đệm Kho mẫu an toàn chỉ sau khi dựng giao diện thành công (Priority: P1)

**Goal**: Triển khai cơ chế Cam kết 2 giai đoạn (Two-Phase Cache Commit) cho `lastBankSnapshotCache` trong `bank.js`, chỉ ghi nhận cache khi quá trình dựng thẻ DOM hoàn tất 100%, vô hiệu hóa cache khi có lỗi để cho phép thử lại.

**Independent Test**: Giả lập `applyFiltersAndRender()` gặp lỗi hoặc container `#bank-cards-grid` chưa sẵn sàng ở lần gọi 1 $\to$ xác nhận cache bị vô hiệu hóa; gọi lại lần 2 $\to$ hệ thống không bỏ qua và dựng thành công danh sách thẻ mẫu.

### Tests cho User Story 2 (TDD - Viết test trước) 🧪

- [x] T010 [P] [US2] Viết kiểm thử đơn vị Node.js cho cơ chế Two-Phase Cache Commit của `refreshBankView` khi render DOM thất bại và phục hồi thành công trong `tests/js/bank_cache.test.mjs`

### Implementation cho User Story 2

- [x] T011 [US2] Cập nhật `applyFiltersAndRender()` trong `webapp/js/bank.js` kiểm tra chặt chẽ sự tồn tại của phần tử `#bank-cards-grid`, ném ngoại lệ rõ ràng nếu phần tử container bị thiếu
- [x] T012 [US2] Tái cấu trúc hàm `refreshBankView()` trong `webapp/js/bank.js` lưu `pendingCacheKey`, chỉ gán `lastBankSnapshotCache = pendingCacheKey` sau khi `applyFiltersAndRender()` thành công, và đặt lại cache về rỗng trong khối `catch`
- [x] T013 [US2] Chạy kiểm thử xác nhận độc lập cho User Story 2 qua `npm run test:unit`

**Checkpoint**: User Story 2 hoàn tất độc lập, tab Kho mẫu có khả năng tự phục hồi (resilience) hoàn hảo khi gặp sự cố giao diện.

---

## Phase 5: User Story 3 - Kiểm chứng nâng cao chất lượng hạt giống và bảo toàn hình thái nét vẽ toàn diện (Priority: P2)

**Goal**: Bổ sung assertion kiểm tra chỉ số xuất hiện `occs_d3[3] == 1` và so sánh toàn bộ các nét vẽ (all strokes) của toàn bộ các từ được bảo toàn qua chuỗi nhiều lượt chỉnh sửa liên tiếp.

**Independent Test**: Chạy `pytest tests/test_stable_variants.py -k "multi_step or stable_variants_workflow" -v` xác nhận toàn bộ assertion và so sánh nét vẽ đều xanh.

### Implementation & Test cho User Story 3

- [x] T014 [P] [US3] Bổ sung assertion `assert occs_d3[3] == 1` cho từ chèn mới `"học"` trong bài kiểm thử `test_align_document_seeds_multi_step_consecutive_edits` tại `tests/test_stable_variants.py`
- [x] T015 [P] [US3] Nâng cấp bài kiểm thử `test_app_controller_stable_variants_workflow` trong `tests/test_stable_variants.py` so sánh 100% danh sách nét vẽ (all strokes) của toàn bộ các từ giữ lại (`"xin"`, `"chào"`, `"ba"`) giữa các lần kết xuất
- [x] T016 [US3] Chạy kiểm thử xác nhận độc lập cho User Story 3 trong `tests/test_stable_variants.py`

**Checkpoint**: User Story 3 hoàn tất, chất lượng kiểm chứng hình học nét vẽ của thuật toán đạt độ tin cậy tuyệt đối.

---

## Phase 6: User Story 4 - Mở rộng kiểm thử hiệu năng Kho mẫu đa biến thể và đồng bộ hóa tài liệu kỹ thuật (Priority: P3)

**Goal**: Mở rộng bài đo hiệu năng bản chụp kho mẫu với 1.050 nhãn và 3.400+ mẫu nét đa biến thể ($t < 200$ ms) và chuẩn hóa toàn bộ các tài liệu kỹ thuật liên quan.

**Independent Test**: Chạy `pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s` xác nhận $t < 200$ ms trên dữ liệu kho đa biến thể.

### Implementation & Test cho User Story 4

- [x] T017 [P] [US4] Nâng cấp bài đo hiệu năng `test_bank_snapshot_large_scale_performance` trong `tests/test_performance_regression.py` tạo 1.050 nhãn với 3–5 biến thể nét/chữ (tổng cộng trên 3.400 mẫu nét)
- [x] T018 [US4] Thực thi bài đo hiệu năng snapshot đa biến thể trong `tests/test_performance_regression.py` xác nhận hoàn tất dưới 200 mili-giây
- [x] T019 [P] [US4] Chuẩn hóa đường dẫn tệp kiểm thử `tests/test_bridge.py`, đồng bộ số lượng bài test E2E (20 tests) và ghi chú phân định số liệu kiểm thử CI vs Local trong `specs/068-seed-bank-e2e-hardening/tasks.md` và `specs/068-seed-bank-e2e-hardening/quickstart.md`

**Checkpoint**: User Story 4 hoàn tất, hiệu năng kho mẫu đa biến thể được kiểm chứng và tài liệu kỹ thuật đồng bộ nhất quán.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Đóng gói phân phối web sạch và kiểm thử hồi quy toàn diện trên toàn bộ kho mã nguồn.

- [x] T020 Đóng gói phân phối tĩnh Web Client sạch bằng `python scripts/build_web.py`
- [x] T021 Chạy kiểm thử đơn vị & Golden Master Node.js (`npm run test:unit`, `npm run test:browser`, `npm run test:golden`)
- [x] T022 Chạy kiểm thử hồi quy toàn diện Playwright E2E (`npx playwright test`) đảm bảo 21/21 bài test đạt 100% PASS
- [x] T023 Chạy kiểm thử hồi quy toàn diện bộ test Python (`pytest`) đảm bảo toàn bộ bài test đạt 100% PASS
- [x] T024 [P] Cập nhật bảng ghi nhận kết quả kiểm chứng thực tế trong `specs/069-seed-reset-bank-cache-hardening/quickstart.md`

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
- **User Story 2 (P1)**: Phụ thuộc Phase 2. Độc lập với US1, US3, US4.
- **User Story 3 (P2)**: Phụ thuộc Phase 2. Độc lập với US1, US2, US4.
- **User Story 4 (P3)**: Phụ thuộc Phase 2. Độc lập với US1, US2, US3.

### Within Each User Story

- Viết test trước, chạy test xác nhận thất bại (TDD).
- Sửa logic cốt lõi trong Python/JS.
- Chạy kiểm thử xác nhận thành công trước khi chuyển sang story tiếp theo.

---

## Parallel Opportunities

- **Setup & Foundational**: T002 và T003 có thể chạy song song (2 tệp khác nhau: `bridge.py` và `py-worker.js`).
- **User Story 1**: T004 và T005 có thể viết song song; T006, T007, T008 có thể triển khai liên tục trên `write.js`.
- **User Story 2**: T010 có thể viết song song với việc chuẩn bị `bank.js`.
- **User Story 3 & 4**: T014, T015, T017 và T019 có thể viết song song.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 (Setup) & Phase 2 (Foundational).
2. Viết test TDD cho User Story 1 (T004, T005).
3. Triển khai T006, T007, T008 trong `webapp/js/write.js`.
4. **DỪNG LẠI & XÁC THỰC**: Chạy T009 để kiểm chứng độc lập User Story 1.

### Incremental Delivery
1. Sau khi MVP (US1) xanh $\to$ Chuyển sang User Story 2 (Two-Phase Cache Commit).
2. Sau khi US2 xanh $\to$ Chuyển sang User Story 3 (All strokes parity & occs_d3[3]).
3. Sau khi US3 xanh $\to$ Chuyển sang User Story 4 (Benchmark đa biến thể & chuẩn hóa tài liệu).
4. Thực thi Phase 7 (Polish, Build web, Full regression verification).
