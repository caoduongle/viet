# Tasks: Cải tiến Seed Stability, Phân trang Bảng và Kế hoạch Dạy chữ

**Input**: Design documents from `specs/036-seed-stability-and-teaching-plan/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)  
**Status**: Ready for Implementation  
**Total Tasks**: 35 tasks across 8 phases

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Chuẩn bị môi trường kiểm thử và dữ liệu mẫu cần thiết cho toàn bộ feature.

- [x] T001 Kiểm tra môi trường thực thi và kiểm thử hiện tại qua `python -m pytest tests/test_golden_master_real_path.py`
- [x] T002 [P] Tạo fixture kho mẫu đa biến thể ($\ge 4$ biến thể/chữ) trong `tests/test_stable_variants.py` để phục vụ kiểm chứng ngẫu nhiên cục bộ

---

## Phase 2: Foundational (Core Localized RNG Module)

**Purpose**: Xây dựng module sinh số ngẫu nhiên cục bộ nền tảng - điều kiện tiên quyết cho các user story.

**⚠️ CRITICAL**: Các user story liên quan đến hạt giống và ổn định hình thái chữ viết phụ thuộc trực tiếp vào module này.

- [x] T003 [P] Tạo module thuần túy `chuviettay/model/rng.py` với `derive_seed` (blake2b phân tách byte null) và lớp `ScopedRNG` (Box-Muller `gauss`, `uniform`, `randrange`, `choice` bọc `Random.random()`)
- [x] T004 [P] Viết bộ unit test kiểm chứng tính tất định bit-exact và thuật toán Box-Muller của `chuviettay/model/rng.py` trong `tests/test_rng.py`

**Checkpoint**: Nền tảng `ScopedRNG` sẵn sàng - có thể bắt đầu triển khai các user story.

---

## Phase 3: User Story 1 - Phân trang ô gộp toàn bảng, Định danh ô cô lập và Bảo toàn hình thái nét vẽ (Priority: P1) 🎯 MVP Candidate

**Goal**: Quét ô nguồn `source_cell_id` từ hàng 0 trên toàn bộ bảng; guard `if search_r >= curr_row_idx: next_row = min(...)`; định danh ô tăng đơn điệu trong `LaidOutCell` (không ghi đè `TableCell` trong Document IR); chống bẹt nét vẽ ở mép trang bằng cách co tỷ lệ hoặc dịch chuyển nét thay vì kẹp collinear.

**Independent Test**: Render bảng có ô `rowspan=4` chứa 80 dòng qua 4 trang; xác minh toàn bộ 80 dòng hiển thị đầy đủ, không ghi đè ô cùng cột, không bẹt nét, và IR `TableCell` giữ nguyên tính bất biến.

### Tests for User Story 1
> **NOTE: Viết test trước để tái hiện lỗi, bảo đảm test ĐỎ trước khi sửa mã nguồn**

- [x] T005 [P] [US1] Viết unit & integration test kiểm chứng phân trang ô gộp 4 trang từ hàng 0, an toàn bounding box và bảo toàn IR trong `tests/test_table_continuation.py`

### Implementation for User Story 1

- [x] T006 [US1] Cập nhật `TableLayoutEngine` trong `chuviettay/layout/table_layout.py`: cấp phát định danh ô tăng đơn điệu trong `LaidOutCell.source_cell_id`, loại bỏ gán `r * 1000 + c` vào `TableCell` IR
- [x] T007 [US1] Cập nhật `chuviettay/document/ir.py`: bảo toàn tính bất biến của `TableCell` và loại bỏ các trường layout nội bộ nếu có
- [x] T008 [US1] Sửa đổi nhánh chuyển tiếp ô bảng trong `chuviettay/layout/engine.py`: quét toàn bảng từ hàng 0, áp dụng điều kiện `if search_r >= curr_row_idx: next_row = min(next_row, search_r)`
- [x] T009 [US1] Loại bỏ nhánh fallback tìm theo cột trong `chuviettay/layout/engine.py`, thêm cảnh báo bố cục an toàn nếu không tìm thấy ô nguồn
- [x] T010 [US1] Cải tiến `_render_text_line` và tính toán dòng bảng trong `chuviettay/layout/engine.py`: áp dụng co tỷ lệ trừ dung sai rung nét và dịch chuyển nét chống bẹt (anti-squash shift) thay vì kẹp cơ học từng điểm
- [x] T011 [US1] Chạy `pytest tests/test_table_continuation.py` và xác minh test chuyển sang XANH

**Checkpoint**: User Story 1 hoàn thành độc lập, giải quyết dứt điểm các lỗi hình học bảng biểu và nét chữ.

---

## Phase 4: User Story 2 - Minh bạch hóa và kiểm chuẩn vòng đời Seed ngẫu nhiên (Priority: P1 - WP1)

**Goal**: Kiểm chuẩn miền giá trị $[0, 2^{32}-1]$ trong `WriteOptions.validate()`, xác định hạt giống hiệu dụng một lần duy nhất tại đầu phiên, bổ sung `WriteResult.seed_used`, hiển thị hướng dẫn tái tạo trên CLI, chuẩn hóa hàm thuần `parseSeed()` trên Web (chấp nhận 0), và phản hồi `ignored_options` trong `bridge.py`.

**Independent Test**: Chạy `test_seed_lifecycle.py` kiểm tra seed validation, kiểm chứng `Random(-5) == Random(5)`, và tái tạo tệp XML bit-exact qua `seed_used`. Chạy `node --test tests/test_web_parse_seed.test.mjs` kiểm tra `parseSeed`.

### Tests for User Story 2

- [x] T012 [P] [US2] Viết test kiểm chuẩn seed, kiểm chứng `Random(-5) == Random(5)`, và tái tạo bit-exact qua `seed_used` trong `tests/test_seed_lifecycle.py`
- [x] T013 [P] [US2] Viết unit test cho hàm web `parseSeed()` trong `tests/test_web_parse_seed.test.mjs`

### Implementation for User Story 2

- [x] T014 [US2] Cập nhật `WriteOptions.validate()` trong `chuviettay/controller/results.py`: chỉ chấp nhận `seed is None` hoặc `int` (không phải `bool`) trong $[0, 2^{32}-1]$, ném `ValueError` tiếng Việt
- [x] T015 [US2] Bổ sung trường `seed_used: int | None = None` vào `WriteResult` trong `chuviettay/controller/results.py`
- [x] T016 [US2] Xác định hạt giống hiệu dụng một lần duy nhất và ghi nhận `result.seed_used` trong `chuviettay/layout/engine.py`
- [x] T017 [US2] Cập nhật `chuviettay/fidelity/engine.py`: truyền đủ `seed`, `stable_variants`, `letter_gap`, `pen_clearance_factor` vào `Writer` và ghi nhận `result.seed_used`
- [x] T018 [US2] Cập nhật `chuviettay/cli.py`: bổ sung mô tả cho `--seed` trong help và in thông báo `"Seed đã dùng: N (chạy lại với --seed N để có đúng kết quả này)"` khi seed tự sinh
- [x] T019 [US2] Cập nhật `chuviettay/browser/bridge.py`: thu thập và trả về danh sách `ignored_options` cùng trường `seed_used`
- [x] T020 [US2] Tách hàm thuần `parseSeed(inputVal, currentSeed)` trong `webapp/js/write.js`, chấp nhận giá trị `0`, giữ nguyên seed hiện tại khi lỗi, loại bỏ `parseInt(...) || 42`
- [x] T021 [US2] Chạy `pytest tests/test_seed_lifecycle.py` và `node --test tests/test_web_parse_seed.test.mjs`, xác minh XANH

**Checkpoint**: User Story 2 hoàn thành độc lập, vòng đời hạt giống hoàn toàn minh bạch trên mọi tầng giao diện.

---

## Phase 5: User Story 3 - Ngẫu nhiên cục bộ bảo đảm kiểu chữ thực sự ổn định khi chèn sửa văn bản (Priority: P1 - WP2)

**Goal**: Tích hợp `ScopedRNG` vào `Writer` khi `stable_variants=True` neo theo token `(seed, "tok", text, k, purpose, idx)` và layout engines; token-local de-duplication; viết lại `tests/test_stable_variants.py` chứng minh đỏ sang xanh; giữ nguyên 100% hash cũ của default path `stable_variants=False`; bổ sung golden test riêng cho stable mode.

**Independent Test**: `tests/test_stable_variants.py` kiểm tra biến thể thật bằng kho đa mẫu, chèn từ "a" phía trước không đổi "nay", lặp 50 lần không trùng 2 lần liên tiếp, bất biến tịnh tiến trục Y.

### Tests for User Story 3

- [ ] T022 [P] [US3] Viết lại toàn diện bộ kiểm thử `tests/test_stable_variants.py` so sánh tag thật và nét thật, chứng minh ĐỎ trên mã nguồn cũ

### Implementation for User Story 3

- [ ] T023 [US3] Tích hợp `ScopedRNG` vào `Writer` trong `chuviettay/model/writer.py`: hỗ trợ tham số `k` trong `token(tok, k=None)`, tự động đếm tần suất token qua `self._token_counts`
- [ ] T024 [US3] Áp dụng `ScopedRNG` cho các vị trí tiêu thụ ngẫu nhiên trong `Writer` (`pick`, `jitter`, `_resolve_dgap`) và cô lập chống lặp biến thể trong phạm vi token khi `stable_variants=True`
- [ ] T025 [US3] Cập nhật `chuviettay/layout/engine.py`: neo luồng ngẫu nhiên cho word gap `(wgap)`, sóng dòng `(line)`, viền bảng `(tbl_border)` và công thức toán khi `stable_variants=True`
- [ ] T026 [US3] Cập nhật `chuviettay/fidelity/engine.py`: neo luồng ngẫu nhiên cho word gap và wscale khi `stable_variants=True`
- [ ] T027 [US3] Chạy `pytest tests/test_stable_variants.py` và xác minh test chuyển từ ĐỎ sang XANH
- [ ] T028 [US3] Chạy `pytest tests/test_golden_master_real_path.py` xác minh 100% SHA-256 cũ không đổi từng byte; bổ sung ca golden master riêng cho `stable_variants=True`

**Checkpoint**: User Story 3 hoàn thành, giải quyết triệt để hiện tượng nhấp nháy chữ viết tay khi soạn thảo.

---

## Phase 6: User Story 4 - Chuẩn hóa Kế hoạch Dạy chữ và Gỡ nghẽn Hàng đợi SEED (Priority: P2 - Teaching Plan)

**Goal**: Đồng bộ `Bank.can()` công nhận các từ nguyên khối đã lưu trong `bank.words`; bổ sung `CORE_ESSENTIALS_38` (33 chữ cái thường + 5 dấu thanh) mở khóa 100% (700/700) từ trong `SEED`; cập nhật hàng đợi gợi ý dạy chữ.

**Independent Test**: `tests/test_teaching_plan.py` chứng minh 38 mục cốt lõi viết được 700/700 từ SEED, và `teach_char("tôi")` lưu vào `bank.words` gỡ bỏ "tôi" khỏi hàng đợi `missing_minimal_essentials()`.

### Tests for User Story 4

- [ ] T029 [P] [US4] Viết unit test kiểm chứng độ phủ 700 từ SEED của 38 mục cốt lõi và gỡ tắc nghẽn hàng đợi dạy chữ trong `tests/test_teaching_plan.py`

### Implementation for User Story 4

- [ ] T030 [US4] Cập nhật `Bank.can(w)` trong `chuviettay/model/bank.py`: công nhận từ nguyên khối có mẫu trong `bank.words`
- [ ] T031 [US4] Bổ sung hằng số `CORE_ESSENTIALS_38` và hàm `get_core_essentials_38()` trong `chuviettay/model/seed_words.py`
- [ ] T032 [US4] Cập nhật `AppController.missing_minimal_essentials()` trong `chuviettay/controller/app_controller.py`: ưu tiên gợi ý các ký tự cốt lõi còn thiếu trước từ ghép đa ký tự
- [ ] T033 [US4] Chạy `pytest tests/test_teaching_plan.py` và xác minh XANH

**Checkpoint**: User Story 4 hoàn thành, tối ưu hóa lộ trình dạy chữ và giải phóng hoàn toàn hàng đợi.

---

## Phase 7: User Story 5 - Hoàn thiện tài liệu, Parity và Xác minh Nghi vấn Kỹ thuật (Priority: P3 - WP4)

**Goal**: Cập nhật README, CHANGELOG tiếng Việt; kiểm chứng nghi vấn `MathLayoutEngine._scratch()` và `Writer.measure_text_width`; lập báo cáo kỹ thuật về cờ `assemble_letters`.

**Independent Test**: Toàn bộ tài liệu chuẩn hóa tiếng Việt, CLI `--help` đầy đủ, các nghi vấn kỹ thuật được xác minh bằng test độc lập.

- [ ] T034 [P] [US5] Cập nhật `MathLayoutEngine._scratch()` trong `chuviettay/layout/math_layout.py`: truyền đủ `letter_gap`, `pen_clearance_factor`, `stable_variants`, `seed` sang scratch Writer
- [ ] T035 [P] [US5] Kiểm chứng và đồng bộ `Writer.measure_text_width` trong `chuviettay/model/writer.py`: ưu tiên đo từ chữ cái ghép khớp với `Writer.word()`
- [ ] T036 [US5] Cập nhật `README.md` mục "Tái tạo đúng một kết quả" và `CHANGELOG.md` bằng tiếng Việt chuẩn mực; báo cáo hiện trạng cờ `assemble_letters`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Đảm bảo chất lượng toàn diện, hiệu năng và tương thích trước khi bàn giao.

- [ ] T037 [P] Đo đạc và lập báo cáo hiệu năng kết xuất tài liệu ~5.000 tokens ở chế độ `stable_variants=True` vs tuần tự (đạt mục tiêu < 1.5x)
- [ ] T038 [P] Chạy `ruff check .` và đảm bảo 100% mã nguồn sạch linter, không phát sinh cảnh báo
- [ ] T039 Chạy toàn bộ test suite dự án (`pytest`, `npm run test:unit`) đảm bảo $\ge 1269$ tests passed, zero regression
- [ ] T040 Thực hiện kiểm chứng toàn diện theo kịch bản `quickstart.md`

---

## Dependencies & Execution Order

```text
Phase 1: Setup (T001 - T002)
   │
   ▼
Phase 2: Foundational (T003 - T004: ScopedRNG)
   │
   ├───► Phase 3: User Story 1 (T005 - T011: Table Geometry Safety) [MVP]
   │
   ├───► Phase 4: User Story 2 (T012 - T021: Seed Lifecycle & WP1)
   │        │
   │        ▼
   ├───► Phase 5: User Story 3 (T022 - T028: Localized RNG & WP2)
   │
   ├───► Phase 6: User Story 4 (T029 - T033: Teaching Plan & Bank.can)
   │
   └───► Phase 7: User Story 5 (T034 - T036: Docs & Questions WP4)
            │
            ▼
Phase 8: Polish & Verification (T037 - T040)
```

### Parallel Opportunities

- **Trong Phase 2**: `T003` (`rng.py`) và `T004` (`test_rng.py`) có thể phát triển song song (TDD).
- **Sau Phase 2**: Các User Story 1, 2, 4 có thể triển khai song song vì không phụ thuộc chéo:
  - Developer A: User Story 1 (Hình học bảng biểu & Bounding box)
  - Developer B: User Story 2 (Vòng đời Seed & Web UI)
  - Developer C: User Story 4 (Kế hoạch Dạy chữ & Bank.can)
- **User Story 3**: Triển khai tiếp sau khi hoàn thành Phase 2 và User Story 2 (thừa hưởng `seed_used`).
- **Trong Phase 8**: `T037` (benchmark), `T038` (ruff) có thể chạy độc lập.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 & Phase 2.
2. Hoàn thành Phase 3 (User Story 1 - Phân trang bảng & Bounding box).
3. **VALIDATE**: Kiểm tra độc lập với `tests/test_table_continuation.py` (Bảng 80 dòng qua 4 trang không mất dữ liệu).

### Incremental Delivery (Theo thứ tự gói việc)
1. **MVP**: User Story 1 (Table Geometry Safety).
2. **Increment 1**: User Story 2 (Seed Lifecycle & Web/CLI parity).
3. **Increment 2**: User Story 3 (Localized ScopedRNG & Stable Variants Red-to-Green).
4. **Increment 3**: User Story 4 (Teaching Plan 38 Essentials & Bank.can fix).
5. **Increment 4**: User Story 5 & Polish (Documentation, Tech Questions, CI Clean).
