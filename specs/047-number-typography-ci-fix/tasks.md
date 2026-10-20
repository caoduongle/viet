# Tasks: Number Typography and CI Fallback Hardening

**Branch**: `047-number-typography-ci-fix` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Xác nhận hiện trạng baseline môi trường kiểm thử và cô lập các điểm lỗi trên môi trường CI sạch

- [x] T001 Xác nhận baseline môi trường kiểm thử và tái hiện 3 lỗi kiểm thử khi ngắt kết nối `local data/kho_mau_v4.json.gz` trong `tests/test_number_fraction_typography.py` và `tests/test_system_hardening_feature_046.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Thiết lập các nét vector glyph fallback chuẩn và tái sinh fixture kho mẫu tổng hợp độc lập

- [x] T002 [P] Định nghĩa các nét vector fallback cho `%`, `,`, `.` và chuẩn hóa tọa độ trục toán học `y = -0.45 * xh` cho `-` trong `chuviettay/model/text_utils.py`
- [x] T003 Cập nhật script sinh kho mẫu tổng hợp `scripts/gen_synthetic_bank.py` để bổ sung các mẫu `-`, `%` và hiệu chỉnh tỷ lệ dấu phẩy `,`, dấu chấm `.`
- [x] T004 Thực thi `python scripts/gen_synthetic_bank.py` để tái sinh fixture chuẩn `tests/data/kho_mau_tong_hop.json.gz`

**Checkpoint**: Nét vector fallback và dữ liệu fixture tổng hợp đã sẵn sàng để tích hợp vào engine kết xuất.

---

## Phase 3: User Story 1 - Phục hồi dấu số âm và ký hiệu phần trăm khi thiếu mẫu (Priority: P1) 🎯 MVP

**Goal**: Khi kho mẫu thiếu nét `-` hoặc `%`, `Writer.number()` và `Writer.token("%")` tự động kích hoạt vector fallback, căn tâm trục toán học `y = -0.45 * xh`, chuẩn hóa chiều cao `1.20 * xh`, bám baseline `abs(max_y) <= 0.08 * xh`, và không báo thiếu mẫu trong danh sách `missing`.

**Independent Test**: Chạy `pytest tests/test_number_fraction_typography.py -k "test_minus_and_percent_digit_normalization"` xác nhận 0 lỗi missing và căn tâm đạt chuẩn.

### Implementation for User Story 1

- [x] T005 [US1] Tích hợp cơ chế vector fallback cho `ch == "-"` và `ch == "%"` khi thiếu mẫu kho trong `Writer.number()` tại `chuviettay/model/writer.py`
- [x] T006 [US1] Bổ sung xử lý loại bỏ `ch` khỏi danh sách `missing` khi fallback vector được áp dụng thành công trong `Writer.number()` tại `chuviettay/model/writer.py`
- [x] T007 [US1] Kiểm chứng độc lập kịch bản kết xuất số âm `"-25"` và token `"%"` bằng `pytest tests/test_number_fraction_typography.py -k "test_minus_and_percent_digit_normalization"`

**Checkpoint**: User Story 1 hoàn thành độc lập - số âm và phần trăm hiển thị chuẩn xác mà không bao giờ bị rớt ký tự.

---

## Phase 4: User Story 2 - Hài hòa khoảng cách dấu phẩy số thập phân (Priority: P1)

**Goal**: Tách bước tiến của dấu phẩy/chấm trong chuỗi số khỏi khoảng đệm ngắt câu văn bản; tính bước tiến dựa trên độ rộng quang học thực tế `glyph_w` kèm khoảng đệm chuẩn `0.10 * xh`, bảo đảm khoảng cách sau dấu phẩy nằm nghiêm ngặt trong dải `[0.08 * xh, 0.14 * xh]`.

**Independent Test**: Chạy `pytest tests/test_number_fraction_typography.py -k "test_decimal_number_spacing_harmony"` xác nhận `0.08 * xh <= gap_after_comma <= 0.14 * xh`.

### Implementation for User Story 2

- [x] T008 [US2] Tính toán độ rộng quang học `glyph_w = (max_x - min_x)` có kiểm tra phòng vệ nét rỗng và cập nhật bước tiến `x += p_gap + glyph_w + 0.10 * xh` cho `ch in ",."` trong `Writer.number()` tại `chuviettay/model/writer.py`
- [x] T009 [US2] Kiểm chứng độc lập khoảng cách sau dấu phẩy và độ đồng đều chữ số thập phân bằng `pytest tests/test_number_fraction_typography.py -k "test_decimal_number_spacing_harmony"`

**Checkpoint**: User Story 2 hoàn thành độc lập - số thập phân hiển thị tự nhiên, triệt tiêu khe hở 4.7 bất thường.

---

## Phase 5: User Story 3 - Đồng bộ đo lường trước và kết xuất thực tế (Priority: P1)

**Goal**: Đồng bộ hóa 100% công thức đo độ rộng chuỗi số trong `Writer.measure_text_width()` khớp với `Writer.number()`, đưa sai lệch về ngưỡng `<= 0.05 * xh`.

**Independent Test**: Chạy `pytest tests/test_system_hardening_feature_046.py -k "test_measure_text_width_number_sync"` xác nhận chênh lệch `diff <= 0.05 * xh` cho tất cả các chuỗi số thử nghiệm.

### Implementation for User Story 3

- [x] T010 [US3] Cập nhật bước tiến dấu phẩy/chấm trong nhánh `NUMRE` của `Writer.measure_text_width()` sử dụng độ rộng quang học `glyph_w + 0.10 * xh` trong `chuviettay/model/writer.py`
- [x] T011 [US3] Cập nhật `Writer.get_char_advance_width("-")` đồng bộ độ rộng bước tiến `0.5 * xh` khi dùng vector fallback trong `chuviettay/model/writer.py`
- [x] T012 [US3] Kiểm chứng độc lập tính đồng bộ giữa `measure_text_width()` và `number()` bằng `pytest tests/test_system_hardening_feature_046.py -k "test_measure_text_width_number_sync"`

**Checkpoint**: User Story 3 hoàn thành độc lập - đo lường trước và kết xuất thực tế khớp nhau hoàn toàn.

---

## Phase 6: User Story 4 - Đảm bảo tính toàn vẹn CI và cô lập Fixture (Priority: P2)

**Goal**: Bảo đảm bộ kiểm thử chạy độc lập hoàn toàn với dữ liệu cục bộ không được commit, mô phỏng chính xác môi trường clean CI.

**Independent Test**: Chạy toàn bộ test suite pytest khi không có `local data/kho_mau_v4.json.gz`.

### Implementation for User Story 4

- [x] T013 [US4] Kiểm thử mô phỏng môi trường sạch CI (clean environment emulation) không có `local data/kho_mau_v4.json.gz` trên `tests/test_number_fraction_typography.py` và `tests/test_system_hardening_feature_046.py`

**Checkpoint**: Toàn bộ các bài kiểm thử số học và hệ thống gia cố vượt qua trên môi trường sạch không cần file cục bộ.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm chứng hồi quy toàn diện trên toàn bộ kho mã nguồn và hoàn thiện tài liệu

- [x] T014 [P] Cập nhật tài liệu kiểm chứng nghiệm thu trong `specs/047-number-typography-ci-fix/quickstart.md`
- [x] T015 Chạy toàn bộ 1255+ kiểm thử `pytest` trên toàn bộ repository đảm bảo không phát sinh bất kỳ lỗi hồi quy nào

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Bắt đầu ngay lập tức
- **Foundational (Phase 2)**: Phụ thuộc vào Setup - cung cấp nét vector và fixture tổng hợp
- **User Stories (Phase 3+)**: Phụ thuộc vào Phase 2 (Foundational)
  - **US1 (P1)**: Thực hiện đầu tiên để mở khóa kết xuất số âm và `%`
  - **US2 (P1)**: Thực hiện kế tiếp để chuẩn hóa khoảng cách số thập phân
  - **US3 (P1)**: Phụ thuộc vào US1 và US2 (đồng bộ `measure_text_width` theo cả số âm và số thập phân)
  - **US4 (P2)**: Kiểm chứng tổng hợp trên môi trường sạch không có file cục bộ
- **Polish (Phase 7)**: Chạy sau khi toàn bộ User Stories hoàn tất

### Parallel Opportunities

- `T002` (Vector fallbacks trong `text_utils.py`) và `T003` (Script sinh fixture trong `gen_synthetic_bank.py`) có thể triển khai song song.
- `T014` (Cập nhật `quickstart.md`) có thể thực hiện song song với `T015` (Chạy toàn bộ test suite).

---

## Implementation Strategy

### MVP First (User Story 1 & User Story 2)
1. Hoàn thành Setup (Phase 1) và Foundational (Phase 2).
2. Triển khai User Story 1 (T005 - T007) -> Khắc phục triệt để lỗi thiếu mẫu `'-'`.
3. Triển khai User Story 2 (T008 - T009) -> Khắc phục lỗi giãn cách dấu phẩy 4.7.
4. Triển khai User Story 3 (T010 - T012) -> Đồng bộ hóa đo lường và kết xuất.
5. Kiểm chứng tổng thể với User Story 4 và Polish (Phase 7) -> Đảm bảo zero regression trên toàn bộ dự án.
