# Implementation Tasks: Worker and Seed Integrity Hardening

**Feature**: `specs/044-worker-and-seed-integrity`
**Specification**: [spec.md](./spec.md) | **Implementation Plan**: [plan.md](./plan.md)

---

## Phase 1: Setup (Baseline Environment & Verification Baseline)

**Purpose**: Xác lập trạng thái baseline sạch cho toàn bộ môi trường và các công cụ kiểm thử trước khi thực hiện thay đổi mã nguồn.

- [x] T001 Kiểm tra baseline hiện tại và bảo đảm môi trường kiểm thử sạch thông qua git status và ruff check trong repository root
- [x] T002 Chuẩn bị mock helpers và test assertions cho chuỗi kiểm thử phục hồi Worker và tính toàn vẹn hạt giống trong tests/js/worker_resilience.test.mjs và tests/test_stable_variants.py

---

## Phase 2: Foundational (Core Invariants & Strict Serialization)

**Purpose**: Thiết lập nền tảng kiểm soát kiểu dữ liệu chuẩn tắc bắt buộc cho mọi khâu sinh hạt giống ngẫu nhiên (CTR-044-SEED-PIPELINE).

**⚠️ CRITICAL**: Không được bắt đầu triển khai các User Story trước khi hoàn tất Phase 2.

- [x] T003 [P] Bổ sung kiểm thử encode_canonical_key từ chối kiểu dữ liệu không xác định bằng TypeError trong tests/test_rng.py
- [x] T004 Cập nhật encode_canonical_key trong chuviettay/model/rng.py ném TypeError cho các kiểu dữ liệu ngoài danh mục hợp đồng (CTR-044-SEED-PIPELINE), loại bỏ fallback str(val)

**Checkpoint**: Nền tảng mã hóa khóa hạt giống chuẩn tắc đã được siết chặt và kiểm chứng thành công.

---

## Phase 3: User Story 1 - Tách biệt chu trình khởi động Worker và chu trình nạp kho mẫu (Priority: P1) 🎯 MVP

**Goal**: Phân định độc lập thời hạn chờ tín hiệu READY của Web Worker (clear timer ngay khi nhận READY) khỏi thời gian nạp kho mẫu từ IndexedDB, cô lập thế hệ Worker và không bao giờ hủy ngang Worker chạy tốt.

**Independent Test**: Giả lập Worker gửi READY trong 50ms nhưng bước nạp kho kéo dài hơn 15 giây; Worker không bị terminate, readyTimer bị hủy ngay khi nhận READY, và nạp kho chạy dưới timeout riêng của request (CTR-044-WORKER-LIFECYCLE).

### Tests for User Story 1 🧪
- [x] T005 [P] [US1] Viết kiểm thử recoverWorker khi nạp kho mẫu kéo dài: readyTimer bị dừng ngay khi nhận READY, Worker không bị terminate nhầm trong tests/js/worker_resilience.test.mjs
- [x] T006 [P] [US1] Viết kiểm thử thế hệ Worker (workerGeneration pinning): thông điệp và lỗi muộn từ thế hệ cũ bị loại bỏ và không ảnh hưởng Worker mới trong tests/js/worker_resilience.test.mjs

### Implementation for User Story 1
- [x] T007 [US1] Cập nhật recoverWorker và attachWorkerHandlers trong webapp/js/app.js: dừng readyTimer ngay lập tức khi nhận READY hoặc ERROR, tách biệt chu trình bắt tay khỏi chu trình nạp kho
- [x] T008 [US1] Cập nhật attachWorkerHandlers và onWorkerReady trong webapp/js/app.js: kiểm tra generation === workerGeneration tại các điểm nối bất đồng bộ để ngăn ngừa rò rỉ thế hệ cũ
- [x] T009 [US1] Thực thi kiểm thử độc lập cho User Story 1 thông qua npm run test:unit -- --test-name-pattern="recoverWorker"

**Checkpoint**: User Story 1 đã hoàn chỉnh và có thể kiểm thử độc lập hoàn toàn.

---

## Phase 4: User Story 2 - Toàn vẹn không gian tên sinh số ngẫu nhiên theo ngữ cảnh nội dung (Priority: P1)

**Goal**: Dẫn xuất mọi luồng sinh số ngẫu nhiên (chọn biến thể, rung nét jitter, khoảng cách chữ số dgap) từ SeedContext chuẩn tắc với content_type tương ứng, bảo đảm 0% trùng luồng ngẫu nhiên giữa văn bản thường và ô bảng.

**Independent Test**: So sánh khóa ngẫu nhiên và biến thể của cùng một từ ngữ có cùng số thứ tự xuất hiện giữa content_type="text" và content_type="cell"; hai ngữ cảnh sinh ra hai khóa hoàn toàn khác nhau (CTR-044-SEED-PIPELINE).

### Tests for User Story 2 🧪
- [x] T010 [P] [US2] Viết kiểm thử cô lập không gian tên RNG giữa văn bản thường (text) và ô bảng (cell) cho cùng một từ và occurrence trong tests/test_stable_variants.py
- [x] T011 [P] [US2] Viết kiểm thử cô lập không gian tên cho jitter và dgap theo ctx_type trong tests/test_stable_variants.py

### Implementation for User Story 2
- [x] T012 [US2] Cập nhật Writer.pick() trong chuviettay/model/writer.py truyền ctx_type từ ngữ cảnh vào ScopedRNG thay vì hằng số tĩnh "tok"
- [x] T013 [US2] Cập nhật Writer.assemble_word() và Writer._resolve_dgap() trong chuviettay/model/writer.py truyền ctx_type vào ScopedRNG
- [x] T014 [US2] Cập nhật giá trị SHA-256 kỳ vọng của bài test test_real_path_stable_variants trong tests/test_golden_master_real_path.py tương ứng với hạt giống dẫn xuất chuẩn ngữ cảnh
- [x] T015 [US2] Thực thi kiểm thử độc lập cho User Story 2 thông qua pytest tests/test_stable_variants.py -k "test_namespace_isolation"

**Checkpoint**: User Story 2 đã hoàn chỉnh, các không gian tên nội dung hoàn toàn trực giao và độc lập 100%.

---

## Phase 5: User Story 3 - Ổn định hình thái nét chữ khi chỉnh sửa danh sách và phân đoạn từ dài (Priority: P2)

**Goal**: Mở rộng đối chiếu đệ quy trên toàn bộ cấu trúc tài liệu (bao gồm ListBlock và các danh sách con lồng nhau); đồng bộ hóa việc đánh số token_occurrences cho các token dài bị ngắt dòng thành nhiều đoạn chunk.

**Independent Test**: Chèn một mục mới vào đầu danh sách lồng nhau hoặc chèn từ dài bị ngắt dòng; kiểm tra các mục danh sách và từ ngữ cũ phía sau bảo toàn 100% hình thái nét vẽ với dung sai sai lệch hình học <= 0.02 pt.

### Tests for User Story 3 🧪
- [x] T016 [P] [US3] Viết bài kiểm thử align_document_seeds cho danh sách (ListBlock và danh sách con lồng nhau): chèn mục mới ở đầu giữ nguyên hình thái nét chữ các mục cũ (tolerance <= 0.02 pt) trong tests/test_stable_variants.py
- [x] T017 [P] [US3] Viết bài kiểm thử đồng bộ token occurrence khi token dài bị chia thành nhiều chunk: các từ kế tiếp không bị trôi lệch occurrence trong tests/test_stable_variants.py

### Implementation for User Story 3
- [x] T018 [US3] Cập nhật extract_doc_elements trong chuviettay/document/ir.py với hàm đệ quy _extract_blocks duyệt qua ListBlock.items (items: list[list[Block]]) và gán token_occurrences đệ quy
- [x] T019 [US3] Cập nhật _layout_inlines trong chuviettay/layout/engine.py: tăng inline_tok_idx theo từng token gốc, gán tok_occ chung cho mọi chunk của cùng token và phân biệt bằng ctx.sub_index = chunk_idx
- [x] T020 [US3] Thực thi kiểm thử độc lập cho User Story 3 thông qua pytest tests/test_stable_variants.py -k "list or chunked"

**Checkpoint**: Cấu trúc danh sách và phân đoạn token dài đã được bảo toàn tính ổn định hạt giống 100%.

---

## Phase 6: User Story 4 - Nghiêm ngặt hóa kiểu dữ liệu khóa hạt giống và khôi phục giao diện bền bỉ (Priority: P2)

**Goal**: Bảo vệ quy trình khởi tạo giao diện người dùng, rollback an toàn cờ isDomListenersAttached khi gặp sự cố trung gian để cho phép khôi phục trọn vẹn toàn bộ các bảng điều khiển giao diện khi thử lại.

**Independent Test**: Mô phỏng lỗi trung gian trong onWorkerReady (ví dụ TeachController ném lỗi); cờ isDomListenersAttached được rollback về false, cho phép lần thử lại tiếp theo gắn kết lại đầy đủ các sự kiện giao diện (CTR-044-WORKER-LIFECYCLE).

### Tests for User Story 4 🧪
- [x] T021 [P] [US4] Viết kiểm thử phục hồi khởi tạo giao diện khi TeachController.init hoặc listener ném lỗi: kiểm tra rollback isDomListenersAttached = false và thử lại thành công trong tests/js/worker_resilience.test.mjs

### Implementation for User Story 4
- [x] T022 [US4] Cập nhật onWorkerReady trong webapp/js/app.js: bọc khối đăng ký DOM trong try ... catch để chỉ đặt isDomListenersAttached = true khi toàn bộ listeners hoàn tất thành công, rollback về false khi có lỗi
- [x] T023 [US4] Thực thi kiểm thử độc lập cho User Story 4 thông qua npm run test:unit -- --test-name-pattern="DOM"

**Checkpoint**: Giao diện người dùng có khả năng tự phục hồi bền vững trước mọi lỗi trung gian.

---

## Phase 7: Polish & Toàn bộ Quality Gates

**Purpose**: Chạy toàn bộ các bộ kiểm chuẩn hệ thống, xác thực Golden Master, Pyodide WASM, kiểm tra lint và Playwright E2E.

- [x] T024 [P] Kiểm tra cú pháp và định dạng mã nguồn thông qua ruff check . và python -m compileall -q .
- [x] T025 Chạy toàn bộ bộ kiểm thử đơn vị và tích hợp Python thông qua pytest -q -m "not benchmark"
- [x] T026 Chạy kiểm thử xác thực 8 ca chuẩn Golden Master thông qua pytest tests/test_golden_master_real_path.py -q
- [x] T027 Build gói Web tĩnh và kiểm thử 8 ca Golden Master trong môi trường Pyodide 314.0.7 thông qua python scripts/build_web.py && node scripts/test_golden_pyodide.mjs
- [x] T028 Chạy toàn bộ bộ kiểm thử tự động trên trình duyệt thực Playwright thông qua npx playwright test
- [x] T029 Chạy và xác thực toàn bộ các kịch bản kiểm thử nghiệm thu theo specs/044-worker-and-seed-integrity/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 1 (Setup)**: Không phụ thuộc, chạy đầu tiên.
- **Phase 2 (Foundational)**: Phụ thuộc Phase 1 - CHẶN toàn bộ các User Stories.
- **Phase 3 (User Story 1)**: Phụ thuộc Phase 2 - Có thể chạy độc lập.
- **Phase 4 (User Story 2)**: Phụ thuộc Phase 2 - Có thể chạy độc lập hoặc song song với US1.
- **Phase 5 (User Story 3)**: Phụ thuộc Phase 2 - Có thể chạy sau US2.
- **Phase 6 (User Story 4)**: Phụ thuộc Phase 3 (US1) - Có thể chạy sau khi cơ chế phục hồi Worker hoàn thiện.
- **Phase 7 (Polish & Quality Gates)**: Phụ thuộc vào việc hoàn tất toàn bộ các User Stories (US1 - US4).

### Parallel Opportunities per User Story
- **Foundational**: T003 có thể chạy song song với việc chuẩn bị T004.
- **User Story 1**: T005 và T006 có thể được viết song song trước khi triển khai T007/T008.
- **User Story 2**: T010 và T011 có thể được viết song song trước khi triển khai T012/T013.
- **User Story 3**: T016 và T017 có thể được viết song song trước khi triển khai T018/T019.
- **User Story 4**: T021 có thể được viết trước khi triển khai T022.
- **Polish**: T024 có thể chạy song song với các bước kiểm tra tài liệu.

---

## Implementation Strategy

### MVP First (User Story 1 & User Story 2)
1. Hoàn tất Phase 1 (Setup) và Phase 2 (Foundational).
2. Hoàn tất Phase 3 (User Story 1: Tách biệt Timeout Worker Recovery).
3. Hoàn tất Phase 4 (User Story 2: Cô lập không gian tên RNG theo SeedContext).
4. **Dừng và nghiệm thu**: Xác nhận Worker phục hồi tin cậy và không còn va chạm hạt giống giữa text và cell.

### Incremental Delivery (User Story 3 & User Story 4)
1. Triển khai Phase 5 (User Story 3: Đối chiếu đệ quy danh sách ListBlock và đồng bộ hóa chunking token dài).
2. Triển khai Phase 6 (User Story 4: Resilient DOM initialization rollback).
3. Chạy Phase 7 (Polish & Full Quality Gates): 100% CI, Pyodide Golden Master, Playwright E2E.
