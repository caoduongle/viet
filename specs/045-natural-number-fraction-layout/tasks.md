# Tasks: Cải thiện trình bày chữ số và phân số tự nhiên (Natural Number & Fraction Typography)

**Input**: Design documents from `specs/045-natural-number-fraction-layout/`  
**Prerequisites**: [plan.md](file:///d:/viet/app/specs/045-natural-number-fraction-layout/plan.md), [spec.md](file:///d:/viet/app/specs/045-natural-number-fraction-layout/spec.md), [research.md](file:///d:/viet/app/specs/045-natural-number-fraction-layout/research.md), [data-model.md](file:///d:/viet/app/specs/045-natural-number-fraction-layout/data-model.md), [contracts/number-fraction-layout-contract.md](file:///d:/viet/app/specs/045-natural-number-fraction-layout/contracts/number-fraction-layout-contract.md)

---

## Phase 1: Setup

**Purpose**: Thiết lập môi trường kiểm thử và bộ đo đạc benchmark hình học cho chữ số và phân số

- [X] T001 Khởi tạo file kiểm thử chuyên biệt [test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) với các fixture nạp kho mẫu tổng hợp và hàm đo đạc bounding box

---

## Phase 2: Foundational

**Purpose**: Xây dựng hàm phụ trợ chuẩn hóa hình học 2 chiều cho mẫu chữ số dùng chung trong `Writer`

- [X] T002 Cài đặt hàm helper `_normalize_digit_sample(inst: dict, ch: str, xh: float | None = None) -> tuple[list[Stroke], float]` trong [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) hỗ trợ chuẩn hóa chân chữ `dy = -max_y`, tính tỷ lệ co giãn `scale_y`/`scale_x` theo `target_h = 1.20 * xh`, định vị tâm trục toán học `y = -0.45 * xh` cho `ch == "-"`, và trả về nét cùng độ rộng tiến quang học

---

## Phase 3: User Story 1 - Kích thước đồng nhất và vị trí chân chữ (baseline) tự nhiên cho các chữ số (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo 100% chữ số `0`–`9` có chân chữ chạm đúng đường cơ sở (`y = 0.0`), chiều cao hiển thị đồng đều trong `[1.05 * xh, 1.30 * xh]` (chênh lệch `≤ 12%`), không bị bay lơ lửng hay nhấp nhô thất thường.

**Independent Test**: Chạy `pytest tests/test_number_fraction_typography.py -k "test_digit_baseline_and_height or test_minus_and_percent"` để xác minh tọa độ `max_y` và chiều cao của tất cả các chữ số `0`–`9` khi kết xuất từ cả `kho_mau_v4.json.gz` và `chu_cua_ban.json.gz`.

### Tests for User Story 1

- [X] T003 [P] [US1] Viết unit test `test_digit_baseline_and_height_normalization` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra `abs(max_y) <= 0.08 * xh` và độ phân tán chiều cao `≤ 12%` cho các chữ số `0`–`9`
- [X] T004 [P] [US1] Viết unit test `test_minus_and_percent_digit_normalization` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra dấu `"-"` căn tâm tại `y = -0.45 * xh` và `"%"` chuẩn hóa như ký hiệu đồng cao

### Implementation for User Story 1

- [X] T005 [US1] Cập nhật hàm `Writer.number()` trong [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) áp dụng `_normalize_digit_sample()` khi lấy mẫu từ `bank.digits`
- [X] T006 [US1] Cập nhật hàm `Writer.token()` trong [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) để các token chữ số đơn lẻ (`len(tok) == 1` và `tok.isdigit()`) đi qua luồng chuẩn hóa chữ số thay vì trả về nét thô chưa chuẩn hóa
- [X] T007 [US1] Cập nhật `Writer.get_letter_sample()`, `Writer.get_char_advance_width()` và `Writer.measure_text_width()` trong [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) để thống nhất độ rộng tiến quang học và tránh lệch số đo khi ngắt dòng

---

## Phase 4: User Story 2 - Khoảng cách liên kết chặt chẽ trong số nhiều chữ số và số thập phân (Priority: P1)

**Goal**: Giữ khoảng hở quang học giữa các chữ số liên tiếp trong khoảng `0.10 * xh` đến `0.18 * xh`, đồng bộ khoảng cách trước và sau dấu thập phân `,`, và tự động nhận diện số thập phân tiếng Việt tự nhiên (`$0,39$`, `$0,0278$`) trong công thức LaTeX toán.

**Independent Test**: Chạy `pytest tests/test_number_fraction_typography.py -k "test_inter_digit_spacing or test_decimal_number or test_latex_parser"` để xác minh khoảng hở giữa các chữ số trong `16`, `25`, `36`, `0,39`, `0,0278` và kiểm tra parser nhận diện đúng số thập phân có dấu phẩy.

### Tests for User Story 2

- [X] T008 [P] [US2] Viết test `test_inter_digit_spacing_bounds` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) đo đạc khoảng hở giữa các nét chữ số liền kề trong dải `[0.10 * xh, 0.20 * xh]`
- [X] T009 [P] [US2] Viết test `test_decimal_number_spacing_harmony` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra chênh lệch khoảng cách sau dấu phẩy và giữa các chữ số thập phân `≤ 0.08 * xh` (chống lỗi `0,3 9`)
- [X] T010 [P] [US2] Viết test `test_latex_parser_vietnamese_decimal_comma` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra parse `$0,39$`, `$0,0278,$`, và `$(0, 1)$`

### Implementation for User Story 2

- [X] T011 [US2] Cải tiến hàm `Writer._resolve_dgap()` trong [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) siết chặt giới hạn dgap trong `[0.10 * xh, 0.18 * xh]` và loại bỏ việc cho phép các giá trị ngoại lai lớn tới `0.55 * xh`
- [X] T012 [US2] Điều chỉnh logic đặt dấu thập phân (`,` và `.`) trong `Writer.number()` của [chuviettay/model/writer.py](file:///d:/viet/app/chuviettay/model/writer.py) để khoảng cách sau dấu phẩy và giữa các chữ số thập phân tiếp theo cân đối, hài hòa
- [X] T013 [US2] Nâng cấp biểu thức chính quy `_NUM_RE` với lookahead `,(?=[0-9])` trong [chuviettay/math/parser.py](file:///d:/viet/app/chuviettay/math/parser.py) để nhận diện số thập phân tiếng Việt dạng `0,39` và `0,0278` thành `TextNode(..., kind="num")`

---

## Phase 5: User Story 3 - Trình bày phân số cân đối về kích thước, khoảng cách tử/mẫu và căn chỉnh dòng (Priority: P1)

**Goal**: Đưa khoảng hở từ nét tử số/mẫu số đến gạch phân số về `0.15 * xh` đến `0.25 * xh`, thu gọn độ nhô gạch phân số mỗi bên về `0.15 * xh` đến `0.25 * xh`, và điều chỉnh nhịp dòng phân số trong ma trận/cases gọn gàng trên nền giấy kẻ ngang.

**Independent Test**: Chạy `pytest tests/test_number_fraction_typography.py -k "test_textnode_numeric or test_fraction_optical or test_piecewise_cases"` để đo đạc khoảng cách quang học từ nét tử số/mẫu số đến gạch phân số và độ nhô của thanh gạch trong `\frac{1}{36}` đến `\frac{25}{36}`.

### Tests for User Story 3

- [X] T014 [P] [US3] Viết test `test_textnode_numeric_descent_zero` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra `TextNode` số học không bị gán `descent` ảo
- [X] T015 [P] [US3] Viết test `test_fraction_optical_clearance_and_overhang` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra khoảng hở nét tử/mẫu trong `[0.15 * xh, 0.25 * xh]` và độ nhô gạch ngang trong `[0.15 * xh, 0.25 * xh]`
- [X] T016 [P] [US3] Viết test `test_piecewise_cases_fraction_compactness` trong [tests/test_number_fraction_typography.py](file:///d:/viet/app/tests/test_number_fraction_typography.py) kiểm tra chiều cao phân số trong hệ `cases` giảm tối thiểu 25%

### Implementation for User Story 3

- [X] T017 [US3] Cập nhật `MathLayoutEngine._m_TextNode()` trong [chuviettay/layout/math_layout.py](file:///d:/viet/app/chuviettay/layout/math_layout.py) để tính `descent = max(0.0, max(ys) * eff)` cho `kind == "num"`, triệt tiêu phần chân ảo
- [X] T018 [US3] Cải tiến `MathLayoutEngine._m_Fraction()` trong [chuviettay/layout/math_layout.py](file:///d:/viet/app/chuviettay/layout/math_layout.py) sử dụng biên dọc thực tế của nét (`ink bounds`), đặt khoảng hở quang học `gap = (0.20 if node.bar else 0.12) * self.xh * eff`, và độ nhô `overhang = (0.18 if node.bar else 0.08) * self.xh * eff`
- [X] T019 [US3] Bổ sung quản lý ngữ cảnh `self._matrix_level` trong `MathLayoutEngine._m_Matrix()` của [chuviettay/layout/math_layout.py](file:///d:/viet/app/chuviettay/layout/math_layout.py), áp dụng `child_scale = scale * 0.78` khi phân số nằm trong ma trận/cases, và điều chỉnh `row_gap = 0.35 * xh` cho khối `cases`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Xác minh không hồi quy trên toàn bộ test suite và kiểm chứng trực quan bằng file mẫu thực tế

- [X] T020 Chạy toàn bộ test suite hiện có của dự án (`pytest`) bảo đảm 100% bài kiểm tra tiếp tục vượt qua thành công
- [X] T021 Tạo script kiểm chứng trực quan [scripts/verify_number_fraction_output.py](file:///d:/viet/app/scripts/verify_number_fraction_output.py) render mẫu biểu thức đề bài và xác nhận các con số `0,39`, `0,0278` và phân số `\frac{1}{36}` hiển thị tự nhiên

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không có phụ thuộc, thực hiện ngay để chuẩn bị file test.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1; cung cấp hàm helper `_normalize_digit_sample`.
- **User Story 1 (Phase 3)**: Phụ thuộc vào Phase 2; hoàn thiện chuẩn hóa baseline và chiều cao chữ số.
- **User Story 2 (Phase 4)**: Phụ thuộc vào Phase 3 (kế thừa các mẫu chữ số đã chuẩn hóa để siết chặt `dgap` và gộp số thập phân).
- **User Story 3 (Phase 5)**: Phụ thuộc vào Phase 4 (kế thừa chữ số và số thập phân chuẩn hóa trong tử số, mẫu số).
- **Polish (Phase 6)**: Phụ thuộc vào toàn bộ các User Stories 1, 2, 3 hoàn thành.

### Parallel Opportunities

- Trong Phase 3: T003 và T004 có thể viết song song.
- Trong Phase 4: T008, T009 và T010 có thể viết song song; T011/T012 (trong `writer.py`) và T013 (trong `parser.py`) có thể triển khai song song.
- Trong Phase 5: T014, T015 và T016 có thể viết song song.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1 & Phase 2 (Setup & Foundational helper).
2. Viết test T003, T004 cho User Story 1.
3. Triển khai T005, T006, T007 trong `writer.py`.
4. **Dừng và kiểm chứng**: Chạy test US1 xác nhận tất cả chữ số `0`–`9` đã bám đúng baseline và đồng đều chiều cao.

### Incremental Delivery

- Bước tiếp theo: Triển khai US2 để giải quyết triệt để lỗi rời rạc số thập phân (`0,3 9`, `0,0 2 7 8`).
- Bước tiếp theo: Triển khai US3 để hoàn thiện bố cục phân số gọn gàng, cân đối với dấu `=`, `≈` và dòng kẻ vở.
- Bước cuối cùng: Chạy toàn bộ regression test suite và xác minh trực quan.
