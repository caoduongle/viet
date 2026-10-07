# Tasks: Punctuation Spacing, Natural Alignment & Digit Spacing

**Feature**: `030-punctuation-spacing-alignment`  
**Input**: Design artifacts from `specs/030-punctuation-spacing-alignment/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/writer-contract.md`, `quickstart.md`)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Chuẩn bị môi trường và fixture kiểm thử cho typography spacing

- [x] T001 Tạo bộ kiểm thử cơ sở cho khoảng cách dấu câu và chữ số trong `tests/test_punctuation_spacing.py`
- [x] T002 [P] Bổ sung helper đo khoảng cách biên nét và bounding box trong `tests/test_punctuation_spacing.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Các hàm helper hình học nền tảng cần thiết trước khi tích hợp vào Writer

**⚠️ CRITICAL**: Phải hoàn thành các hàm chuẩn hóa tọa độ và dải khoảng cách trước khi chỉnh sửa logic ghép nét token

- [x] T003 Triển khai hàm chuẩn hóa mẫu dấu câu `_normalize_punct_sample` về gốc `0.0` trong `chuviettay/model/writer.py`
- [x] T004 [P] Xây dựng bộ lọc và tính toán dải khoảng cách chữ số an toàn `_resolve_dgap` theo `xh` trong `chuviettay/model/writer.py`

**Checkpoint**: Foundation ready - có thể bắt đầu triển khai các User Story

---

## Phase 3: User Story 1 - Khoảng cách tự nhiên cho dấu câu đi liền sau từ (Priority: P1) 🎯 MVP

**Goal**: Dấu câu đuôi (`:`, `,`, `.`, `;`, `!`, `?`) không bị dính nét, đè nét vào từ đứng trước và có khoảng hở quang học tự nhiên (`0.18 * xh`).

**Independent Test**: Render các từ kèm dấu câu (`đổi:`, `này,`, `sau.`, `gì?`) và xác minh không có va chạm nét giữa chữ và dấu câu; khoảng cách hở `>= 0.15 * xh`.

### Tests for User Story 1
- [x] T005 [P] [US1] Viết unit test kiểm chứng zero collision và clearance gap cho `đổi:`, `y:`, `a,` trong `tests/test_punctuation_spacing.py`
- [x] T006 [P] [US1] Viết test kiểm tra token dấu câu đơn lẻ (`:`, `)`) có độ rộng và vị trí chuẩn trong `tests/test_punctuation_spacing.py`

### Implementation for User Story 1
- [x] T007 [US1] Cải tiến xử lý `trail` trong `Writer.token()` để tính mốc xuất phát từ `max(core_w, max_x_placed) + clearance` trong `chuviettay/model/writer.py`
- [x] T008 [US1] Áp dụng chuẩn hóa gốc `0.0` cho các mẫu dấu câu đuôi trong `chuviettay/model/writer.py`
- [x] T009 [US1] Xử lý token dấu câu đơn lẻ (`len(tok) == 1`) không để lại khoảng trắng ảo bên trái trong `chuviettay/model/writer.py`

**Checkpoint**: User Story 1 hoàn thành - kiểm tra độc lập `pytest tests/test_punctuation_spacing.py -k "test_trail"` đạt pass 100%.

---

## Phase 4: User Story 2 - Khoảng cách chữ số hài hòa, tự nhiên và chống rời rạc (Priority: P1)

**Goal**: Các chữ số liên tiếp trong cùng một số (số nguyên, số thập phân, phân số, bảng) không bị giãn cách xa nhau quá mức, loại bỏ hiện tượng số bị đứt rời.

**Independent Test**: Render các chuỗi số (`181`, `195`, `0,12`, `184,05`, `00144`) trong cả văn bản thường và công thức toán; xác minh khoảng cách giữa các chữ số liên tiếp nằm trong dải `[0.08 * xh, 0.22 * xh]`.

### Tests for User Story 2
- [x] T010 [P] [US2] Viết unit test kiểm tra khoảng cách chữ số liên tiếp không vượt quá `0.25 * xh` trong `tests/test_punctuation_spacing.py`
- [x] T011 [P] [US2] Viết test kiểm chứng khoảng cách số thập phân có dấu phẩy/chấm (`184,05`, `0,12`) trong `tests/test_punctuation_spacing.py`

### Implementation for User Story 2
- [x] T012 [US2] Cập nhật `Writer.number()` áp dụng `_resolve_dgap` thay thế cho `clamp(rnd.choice(gaps), 0.5, 7.0)` trong `chuviettay/model/writer.py`
- [x] T013 [US2] Chuẩn hóa mốc x cho dấu phẩy và chấm ngăn cách trong `Writer.number()` trong `chuviettay/model/writer.py`
- [x] T014 [US2] Xác nhận tính đồng bộ hiển thị số giữa `Writer.number()` và `MathLayoutEngine._m_TextNode()` trong `chuviettay/layout/math_layout.py`

**Checkpoint**: User Story 2 hoàn thành - kiểm tra độc lập `pytest tests/test_punctuation_spacing.py -k "test_digit"` đạt pass 100%.

---

## Phase 5: User Story 3 - Khoảng cách và căn lề cho dấu câu mở đầu và bao quanh (Priority: P2)

**Goal**: Dấu mở ngoặc `(`, `[`, `{`, `“` có khoảng cách tự nhiên với từ tiếp theo, dấu đóng ngoặc đứng riêng không bị thụt lề bất thường.

**Independent Test**: Render `(bằng`, `[1]`, `“Hà` và kiểm tra khoảng cách đệm dương giữa dấu mở và nét chữ đầu tiên.

### Tests for User Story 3
- [x] T015 [P] [US3] Viết test kiểm tra khoảng cách an toàn cho dấu mở đầu `(bằng` trong `tests/test_punctuation_spacing.py`

### Implementation for User Story 3
- [x] T016 [US3] Chuẩn hóa gốc `0.0` và khoảng cách tiến cho `lead` trong `Writer.token()` trong `chuviettay/model/writer.py`

**Checkpoint**: Cả 3 User Story đều hoạt động độc lập và phối hợp hoàn hảo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm thử toàn diện hệ thống, kiểm tra hồi quy và tài liệu hướng dẫn

- [x] T017 [P] Chạy toàn bộ bộ kiểm thử hiện có `pytest` đảm bảo không có bất kỳ regression nào
- [x] T018 Thực thi kịch bản kiểm chứng CLI trong `quickstart.md` với tài liệu mẫu Markdown toán & bảng biểu
- [x] T019 Dọn dẹp mã nguồn, kiểm tra lint/type hints và đóng gói tài liệu nghiệm thu

---

## Dependencies & Execution Order

### Phase Dependencies
1. **Phase 1 (Setup)**: Không phụ thuộc, bắt đầu ngay.
2. **Phase 2 (Foundational)**: Phụ thuộc Phase 1 - BLOCKS toàn bộ User Stories.
3. **Phase 3 (US1 - Dấu câu đuôi)**: Phụ thuộc Phase 2 - MVP cốt lõi.
4. **Phase 4 (US2 - Khoảng cách chữ số)**: Phụ thuộc Phase 2 - Có thể chạy song song hoặc nối tiếp US1.
5. **Phase 5 (US3 - Dấu mở ngoặc)**: Phụ thuộc Phase 2 & Phase 3.
6. **Phase 6 (Polish)**: Phụ thuộc hoàn thành toàn bộ các User Story.

---

## Parallel Opportunities
- T001 và T002 có thể viết cùng lúc trong Phase 1.
- T005 và T006 (tests cho US1) có thể viết song song.
- T010 và T011 (tests cho US2) có thể viết song song.
- Sau Phase 2, US1 và US2 có thể được triển khai độc lập vì US1 tác động vào logic `trail`/`punct` trong khi US2 tác động vào `number()`/`dgaps`.

---

## Implementation Strategy: MVP First
1. Hoàn thành Phase 1 & Phase 2 (Nền tảng chuẩn hóa).
2. Hoàn thành Phase 3 (US1 - Dấu câu không còn dính chữ - Đạt MVP).
3. Hoàn thành Phase 4 (US2 - Chữ số không còn cách xa nhau).
4. Hoàn thành Phase 5 (US3 - Hoàn thiện dấu mở ngoặc).
5. Chạy toàn bộ regression test (Phase 6).
