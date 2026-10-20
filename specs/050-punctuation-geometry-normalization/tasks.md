# Tasks: Chuẩn hóa Hình học, Kích thước và Vị trí Quang học cho Dấu câu

**Input**: Design documents from `/specs/050-punctuation-geometry-normalization/`  
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)  
**Branch**: `050-punctuation-geometry-normalization`

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: Có thể chạy song song (khác tệp, không phụ thuộc vào tác vụ chưa hoàn tất)
- **[Story]**: Gắn nhãn User Story (`[US1]`, `[US2]`, `[US3]`, `[US4]`)
- Đường dẫn tệp rõ ràng, cụ thể

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Chuẩn bị tệp kiểm thử chuyên dụng và nạp dữ liệu kiểm tra

- [x] T001 Khởi tạo tệp kiểm thử hình học dấu câu mới trong tests/test_punctuation_geometry.py
- [x] T002 [P] Khởi tạo helper nạp mẫu dấu câu thực tế từ local data/kho_mau_v4.json.gz trong tests/test_punctuation_geometry.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Xây dựng hạ tầng phân loại hình học và chuẩn hóa mẫu cơ sở — BẮT BUỘC hoàn thành trước khi triển khai từng User Story

- [x] T003 Định nghĩa bảng tham số PUNCT_METRIC_PROFILES và hàm classify_punct_category trong chuviettay/model/text_utils.py
- [x] T004 [P] Xây dựng cơ chế Invariance Guard và xử lý mẫu suy biến (raw_h < 1e-3, raw_w < 1e-3) trong chuviettay/model/text_utils.py
- [x] T005 Mở rộng phương thức _normalize_punct_sample(self, inst: dict, char: str | None = None) trong chuviettay/model/writer.py
- [x] T006 Cập nhật get_char_advance_width trong chuviettay/model/writer.py để gọi _normalize_punct_sample cho toàn bộ ký tự trong b.punct

**Checkpoint**: Hạ tầng phân loại và chuẩn hóa hình học đã sẵn sàng — các User Stories có thể bắt đầu thực thi

---

## Phase 3: User Story 1 - Chuẩn hóa Dấu Ngoặc Bao Quanh & Chống Dính Nét 1) (Priority: P1) 🎯 MVP

**Goal**: Dấu ngoặc đơn `(`, `)`, vuông `[]`, nhọn `{}` đạt chiều cao $1.45 \times x_h$ (vươn từ $-1.25 \times x_h$ tới $+0.20 \times x_h$), co giãn bề rộng theo tỷ lệ an toàn, và duy trì khoảng hở quang học $\ge \max(0.18 \times x_h \times \text{eff},\, 1.2 \times \text{pen\_w})$ chống dính nét với chữ số `1`.

**Independent Test**: Kết xuất các biểu thức `(random_state=2026)`, `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)` với kho mẫu thực tế; đo chiều cao dấu ngoặc $\ge 1.35 \times x_h$ và khoảng cách tới chữ số `1` luôn $\ge 0.18 \times x_h$.

### Tests for User Story 1
- [x] T007 [P] [US1] Viết unit tests kiểm tra chiều cao và vị trí neo đỉnh/đáy của dấu ngoặc đơn `(`, `)` trong tests/test_punctuation_geometry.py
- [x] T008 [P] [US1] Viết unit tests kiểm tra khoảng hở nét mực giữa chữ số 1 và dấu đóng ngoặc `)` trong P(X >= 1), k!(e^\lambda - 1) trong tests/test_punctuation_geometry.py

### Implementation for User Story 1
- [x] T009 [US1] Triển khai logic chuẩn hóa nhóm PARENS với target_h = 1.45 * xh, target_min_y = -1.25 * xh, target_max_y = +0.20 * xh và scale_x an toàn trong chuviettay/model/writer.py
- [x] T010 [US1] Nâng sàn min_clearance lên max(0.18 * xh * eff, 1.2 * pen_w) trong _m_MathRow khi phần tử trước kết thúc bằng chữ số 1 hoặc phần tử sau là dấu đóng ngoặc trong chuviettay/layout/math_layout.py
- [x] T011 [US1] Tích hợp kiểm tra biên mực thực tế _get_item_ink_bounds_x(body) và đệm an toàn trước dấu đóng right trong _m_Delimited trong chuviettay/layout/math_layout.py
- [x] T012 [US1] Áp dụng sàn khoảng hở clearance_gap >= max(0.18 * xh, 1.0 * pen_w) khi trail là dấu đóng ngoặc sau core kết thúc bằng số 1 trong chuviettay/model/writer.py

**Checkpoint**: User Story 1 hoàn tất — dấu ngoặc bao quanh vươn cao hơn chữ số và hoàn toàn không dính nét vào chữ số 1

---

## Phase 4: User Story 2 - Neo Đường Cơ Sở cho Dấu Phẩy, Dấu Chấm & Dấu Ba Chấm (Priority: P1)

**Goal**: Dấu phẩy `,` có đỉnh ở $-0.14 \times x_h$ và đuôi ở $+0.24 \times x_h$ (không bay lơ lửng), dấu chấm `.` bám sát đường cơ sở $y = 0.0$ với chiều cao $\le 0.22 \times x_h$, và chuỗi ba chấm `...` không bị báo thiếu mẫu khi kho đã có dấu chấm `.`.

**Independent Test**: Kết xuất các cụm `0,`, `1,`, `k = 1, 2, 3, ...` và câu kết thúc bằng `...`; xác nhận dấu phẩy có đỉnh âm, đuôi dương, dấu chấm bám đường cơ sở và `miss` rỗng.

### Tests for User Story 2
- [x] T013 [P] [US2] Viết unit tests kiểm tra dấu phẩy `,` và dấu chấm `.` bám sát đường cơ sở (không bay lơ lửng, đỉnh âm, đuôi dương) trong tests/test_punctuation_geometry.py
- [x] T014 [P] [US2] Viết unit tests kiểm tra chuỗi dấu ba chấm `...` kết xuất 3 dấu chấm đều nhau và không bị báo thiếu mẫu trong tests/test_punctuation_geometry.py

### Implementation for User Story 2
- [x] T015 [US2] Triển khai chuẩn hóa nhóm COMMA trong _normalize_punct_sample đưa đỉnh về -0.14 * xh và đuôi về +0.24 * xh khi mẫu bay lơ lửng trong chuviettay/model/writer.py
- [x] T016 [US2] Triển khai chuẩn hóa nhóm DOT trong _normalize_punct_sample đặt đáy bám sát y = 0.0 và thu gọn kích thước nếu h > 0.22 * xh trong chuviettay/model/writer.py
- [x] T017 [US2] Sửa điều kiện ghi đè miss = [tok] ở cuối hàm token() để không báo thiếu chuỗi nhiều dấu câu liên tiếp như `...` khi đã vẽ thành công trong chuviettay/model/writer.py

**Checkpoint**: User Story 2 hoàn tất — dấu phẩy và dấu chấm bám chắc trên đường cơ sở, dấu ba chấm hoạt động chuẩn xác

---

## Phase 5: User Story 3 - Chuẩn hóa Hai Chấm, Chấm Phẩy, Chấm Than, Hỏi & Nháy (Priority: P2)

**Goal**: Căn chỉnh dấu hai chấm `:`, chấm phẩy `;`, chấm than `!`, hỏi `?`, dấu nháy `'`, `"` theo đúng phân tầng đường kẻ x-height, baseline và ascender.

**Independent Test**: Kết xuất `thuyết:`, `ví dụ;`, `chú ý!`, `tại sao?`, `' mẫu '`; kiểm tra biên dọc và độ thẳng hàng của hai chấm.

### Tests for User Story 3
- [x] T018 [P] [US3] Viết unit tests kiểm tra dấu hai chấm `:`, chấm phẩy `;` nằm gọn trong dải dọc và thẳng trục trong tests/test_punctuation_geometry.py
- [x] T019 [P] [US3] Viết unit tests kiểm tra dấu chấm than `!` và chấm hỏi `?` đạt chiều cao 1.18 * xh và chạm baseline trong tests/test_punctuation_geometry.py

### Implementation for User Story 3
- [x] T020 [US3] Triển khai chuẩn hóa nhóm COLON và SEMICOLON trong _normalize_punct_sample căn thẳng trục dọc và khống chế bề rộng trong chuviettay/model/writer.py
- [x] T021 [US3] Triển khai chuẩn hóa nhóm EXCL_QUEST (!, ?) trong _normalize_punct_sample đạt chiều cao 1.18 * xh và neo đáy tại y = 0.0 trong chuviettay/model/writer.py
- [x] T022 [US3] Triển khai chuẩn hóa nhóm QUOTES và HYPHEN_DASH trong _normalize_punct_sample theo đúng tầng trong chuviettay/model/writer.py

**Checkpoint**: User Story 3 hoàn tất — toàn bộ hệ thống dấu câu phụ trợ đạt tỷ lệ kích thước hài hòa

---

## Phase 6: User Story 4 - Đồng Bộ Bản Đóng Gói Web & Bảo Toàn Golden Master (Priority: P1)

**Goal**: Bảo toàn 100% kết quả 9/9 Golden Master SHA-256, đồng thời tự động xây dựng lại gói phân phối WebAssembly `webapp/dist/pyodide/chuviettay.zip` và cập nhật service worker.

**Independent Test**: Chạy `pytest tests/test_golden_master_real_path.py` (9/9 pass), chạy `pytest tests/test_build_web.py` và `npm run test:unit` (56/56 pass).

### Tests for User Story 4
- [x] T023 [P] [US4] Viết test kiểm tra tính toàn vẹn và độ tươi mới của gói phân phối chuviettay.zip trong tests/test_build_web.py
- [x] T024 [P] [US4] Chạy kiểm thử hồi quy tuyệt đối 9/9 Golden Master trong tests/test_golden_master_real_path.py

### Implementation for User Story 4
- [x] T025 [US4] Chạy scripts/build_web.py đóng gói lại webapp/dist/pyodide/chuviettay.zip và cập nhật webapp/dist/sw.js
- [x] T026 [US4] Chạy xác nhận bộ kiểm thử Web Worker node --test tests/js/*.test.mjs bảo đảm tương thích môi trường web

**Checkpoint**: Toàn bộ hệ sinh thái từ lõi Python tới trình duyệt Web đều đồng bộ và bảo toàn 100% kết quả chuẩn

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm chứng toàn diện, dọn dẹp và bảo đảm chất lượng tổng thể

- [x] T027 [P] Chạy toàn bộ bộ kiểm thử tự động pytest tests/ bảo đảm 1272+ tests pass
- [x] T028 [P] Kiểm tra tính nhất quán tài liệu trong specs/050-punctuation-geometry-normalization/
- [x] T029 Thực hiện toàn bộ 6 kịch bản kiểm chứng độc lập trong specs/050-punctuation-geometry-normalization/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Không có phụ thuộc — bắt đầu ngay.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup — KHÓA tất cả các User Stories.
- **User Stories (Phase 3+)**: Phụ thuộc vào Foundational hoàn thành:
  - US1 (P1): Bắt đầu ngay sau Phase 2 (MVP).
  - US2 (P1): Bắt đầu sau Phase 2; tích hợp cùng `Writer._normalize_punct_sample`.
  - US3 (P2): Bắt đầu sau Phase 2; bổ sung các nhóm dấu câu phụ.
  - US4 (P1): Phụ thuộc vào mã nguồn lõi của US1, US2, US3 đã hoàn tất để đóng gói dist và kiểm tra Golden Master.
- **Polish (Phase 7)**: Chạy sau khi toàn bộ User Stories hoàn tất.

### Parallel Opportunities
- Các tác vụ kiểm thử `[P]` trong từng User Story có thể viết trước song song (TDD).
- Các tác vụ `T003`, `T004` trong Phase 2 có thể thực hiện song song.
- Trong Phase 6, `T023` và `T024` có thể chạy song song.
- Trong Phase 7, `T027` và `T028` có thể chạy song song.

---

## Parallel Example: User Story 1

```bash
# Khởi chạy song song các bài test cho US1:
pytest tests/test_punctuation_geometry.py -k "test_parentheses_height_and_anchors"
pytest tests/test_punctuation_geometry.py -k "test_digit_one_closing_paren_clearance"

# Triển khai các tác vụ core model và layout math:
Task: "Triển khai logic chuẩn hóa nhóm PARENS trong chuviettay/model/writer.py"
Task: "Nâng sàn min_clearance trong chuviettay/layout/math_layout.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Hoàn thành Phase 1 (Setup) & Phase 2 (Foundational).
2. Hoàn thành Phase 3 (User Story 1: Chuẩn hóa dấu ngoặc và chống dính nét `1)`).
3. **STOP and VALIDATE**: Kiểm tra độc lập các biểu thức `(random_state=2026)` và `P(X >= 1)`.

### Incremental Delivery
1. Bước 1: Setup + Foundational (hạ tầng phân loại hình học).
2. Bước 2: US1 (Dấu ngoặc đơn & chống dính nét `1)` - giải quyết lỗi nghiêm trọng nhất ở Image 1, 2, 3).
3. Bước 3: US2 (Dấu phẩy, chấm bám baseline & sửa lỗi ba chấm `...`).
4. Bước 4: US3 (Dấu hai chấm, chấm phẩy, chấm than, hỏi, nháy).
5. Bước 5: US4 (Đóng gói webapp/dist & bảo toàn 9/9 Golden Master SHA-256).
6. Bước 6: Polish & toàn bộ 1272+ tests.
