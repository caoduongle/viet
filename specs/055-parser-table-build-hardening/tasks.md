# Tasks: Gia Cố Độ Chuẩn Xác CommonMark, Bảng GFM Và An Toàn Đóng Gói (055-parser-table-build-hardening)

**Input**: Design documents from `specs/055-parser-table-build-hardening/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Thiết lập môi trường và cấu hình baseline cho feature 055

- [x] T001 Xác minh môi trường kiểm thử baseline qua `pytest tests/test_markdown_math_block_isolation.py` và `ruff check .`
- [x] T002 Cập nhật cấu hình tính năng trong `.specify/feature.json` trỏ tới `specs/055-parser-table-build-hardening`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Xây dựng các hàm tiện ích cốt lõi phân tích mã CommonMark dùng chung trước khi triển khai các user story

- [x] T003 Xây dựng hàm quét đoạn mã nội tuyến `_find_code_spans` theo chuẩn CommonMark trong `chuviettay/importer/markdown_importer.py`
- [x] T004 Xây dựng hàm tách khối mã và đoạn mã `_split_code_segments` bảo toàn `splitlines(keepends=True)` trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nền tảng phân tích mã CommonMark hoàn tất - sẵn sàng triển khai các User Story.

---

## Phase 3: User Story 1 - Bảo toàn khối mã và đoạn mã theo chuẩn CommonMark (Priority: P1) 🎯 MVP

**Goal**: Khối mã mở bằng $K \ge 3$ backticks/tildes không bị đóng sớm bởi dòng có $< K$ ký tự; đoạn mã nội tuyến $N$ backticks bảo vệ nội dung không bị phân tách hay đổi công thức; toàn bộ pipeline `import_text()` bảo toàn 100% nội dung mã.

**Independent Test**: Nạp tài liệu chứa khối mã 4 backticks có dòng 3 backticks và `\[x=1\]`, cùng đoạn mã 2 backticks chứa `$$x=1$$`. Cây Document IR và chuỗi xuất xưởng bảo toàn 100% nội dung mã gốc mà không sinh khối toán.

### Tests for User Story 1 🧪
- [x] T005 [P] [US1] Viết bài kiểm thử cho khối mã 4 backticks chứa dòng 3 backticks và `\[x=1\]` qua cả `_normalize_math_delimiters` và `import_text` trong `tests/test_markdown_math_block_isolation.py`
- [x] T006 [P] [US1] Viết bài kiểm thử cho đoạn mã nội tuyến 2 backticks chứa `$$x=1$$` qua cả `_isolate_display_math_blocks` và `import_text` trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1
- [x] T007 [US1] Tích hợp `_split_code_segments` vào `_normalize_math_delimiters` thay thế regex `_CODE_SEGMENT` trong `chuviettay/importer/markdown_importer.py`
- [x] T008 [US1] Tích hợp `_split_code_segments` vào `_sanitize_html` bảo đảm an toàn thẻ HTML ngoài khối mã trong `chuviettay/importer/markdown_importer.py`
- [x] T009 [US1] Cập nhật hàm kiểm tra `_is_inside_code_span` trong `_isolate_display_math_blocks` sử dụng `_find_code_spans` trong `chuviettay/importer/markdown_importer.py`
- [x] T010 [US1] Chuẩn hóa điều kiện mở và đóng fenced code block trong `_isolate_display_math_blocks` hỗ trợ thụt lề chuẩn CommonMark (0-3 spaces) trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: User Story 1 hoàn thành và được kiểm thử độc lập thành công.

---

## Phase 4: User Story 2 - Bảo toàn cấu trúc bảng GFM compact khi ô đầu tiên chứa công thức toán (Priority: P1)

**Goal**: Hàng bảng compact không có thanh đứng biên (ví dụ: `Col | Val\n---|---\n$$x=1$$ | 2`) được nhận diện chính xác, không bị xé dòng thành nhiều khối rời rạc; trong khi khối toán độc lập có chứa `|` nội bộ (ví dụ: `$$|x| = 1$$`) vẫn được phân tách đúng chuẩn.

**Independent Test**: Nạp bảng compact với ô đầu tiên chứa `$$x=1$$` và xác nhận kết quả tạo ra 1 khối `Table` duy nhất có 2 hàng và 2 cột trong Document IR.

### Tests for User Story 2 🧪
- [x] T011 [P] [US2] Viết bài kiểm thử bảng GFM compact có ô đầu tiên bắt đầu bằng `$$x=1$$` trong `tests/test_markdown_math_block_isolation.py`
- [x] T012 [P] [US2] Viết bài kiểm thử khối toán display chứa ký tự gạch đứng nội bộ `$$|x| = 1$$` không bị nhận nhầm thành bảng trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 2
- [x] T013 [US2] Cài đặt hàm `_is_table_line` ẩn code spans và công thức toán trước khi kiểm tra ký tự `(?<!\\)\|` trong `chuviettay/importer/markdown_importer.py`
- [x] T014 [US2] Cập nhật nhánh kiểm tra bảng trong `_isolate_display_math_blocks` sử dụng `_is_table_line` trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: User Story 1 và User Story 2 hoạt động độc lập và phối hợp hoàn hảo.

---

## Phase 5: User Story 3 - Làm sạch tệp marker nội bộ khỏi danh mục Service Worker và gói phát hành web (Priority: P2)

**Goal**: Loại trừ tệp marker `.chuviettay_build_dist` và các tệp ẩn bắt đầu bằng dấu chấm khỏi danh mục `PRECACHE_URLS` trong `sw.js` và gói phân phối web.

**Independent Test**: Sinh tệp `sw.js` bằng lệnh build và kiểm tra nội dung tệp `sw.js`: tuyệt đối không chứa chuỗi `.chuviettay_build_dist` hoặc các tệp ẩn bắt đầu bằng dấu chấm trong danh mục nạp trước.

### Tests for User Story 3 🧪
- [x] T015 [P] [US3] Viết bài kiểm thử xác nhận `BUILD_MARKER_NAME` và tệp ẩn không xuất hiện trong `sw.js` và `PRECACHE_URLS` trong `tests/test_build_web.py`

### Implementation for User Story 3
- [x] T016 [US3] Cập nhật vòng lặp quét tệp trong `generate_sw_js` để bỏ qua `BUILD_MARKER_NAME` và các tệp bắt đầu bằng dấu chấm trong `scripts/build_web.py`

**Checkpoint**: Gói phân phối web và Service Worker cache hoàn toàn sạch tệp marker nội bộ.

---

## Phase 6: User Story 4 - Kiểm thử hiệu năng co giãn tỷ lệ tuyến tính bền bỉ và không gây gián đoạn CI (Priority: P2)

**Goal**: Đo tỷ lệ tăng trưởng thời gian $T(2N) / T(N) \le 3.5$ với hai kích thước đầu vào $N$ và $2N$ (thay cho ngưỡng cứng 0.25s) và nới lỏng ngưỡng trần an toàn lên $< 2.0$s để chống flaky test trên CI.

**Independent Test**: Chạy bài kiểm thử hiệu năng với $N = 2,500$ cặp dòng và $2N = 5,000$ cặp dòng; xác nhận tỷ lệ $T(2N)/T(N) \le 3.5$ và thời gian $T(2N) < 2.0$s.

### Tests & Implementation for User Story 4 🧪
- [x] T017 [US4] Cải tiến hàm kiểm thử `test_linear_scalability_unclosed_display_math` theo phương pháp đo tỷ lệ tăng trưởng tương đối $T(2N)/T(N) \le 3.5$ và ngưỡng trần an toàn $< 2.0$s trong `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: Bài kiểm thử hiệu năng co giãn tuyến tính chạy ổn định 100% trên mọi môi trường CI.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Đóng gói lại Web Client, kiểm tra lint, xác minh toàn bộ test suite và quickstart

- [x] T018 Đóng gói lại Web Client và cập nhật `webapp/dist/` qua lệnh `python scripts/build_web.py`
- [x] T019 [P] Chạy rà soát tĩnh cú pháp và chất lượng mã bằng `ruff check .`
- [x] T020 [P] Chạy toàn bộ bộ kiểm thử đơn vị Python qua `python -m pytest tests/`
- [x] T021 [P] Chạy toàn bộ bộ kiểm thử đơn vị JavaScript qua `npm run test:unit`
- [x] T022 Thực hiện xác minh 5 kịch bản nghiệm thu theo `specs/055-parser-table-build-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Có thể bắt đầu ngay lập tức.
- **Foundational (Phase 2)**: Phụ thuộc vào Phase 1; cung cấp hàm tiện ích cho US1 và US2.
- **User Story 1 (Phase 3 - P1)**: Phụ thuộc vào Phase 2.
- **User Story 2 (Phase 4 - P1)**: Phụ thuộc vào Phase 2 và Phase 3 (tận dụng `_find_code_spans`).
- **User Story 3 (Phase 5 - P2)**: Độc lập với Markdown parser, có thể chạy song song với US1/US2.
- **User Story 4 (Phase 6 - P2)**: Chạy sau khi hoàn tất US1 và US2 để đo lường trên engine đã nâng cấp.
- **Polish (Phase 7)**: Chạy sau khi hoàn tất toàn bộ các user story.

### Parallel Opportunities
- Các bài test T005, T006 [US1] có thể viết song song.
- Các bài test T011, T012 [US2] có thể viết song song.
- T015, T016 [US3] nằm trên `scripts/build_web.py` và `tests/test_build_web.py`, có thể triển khai song song với parser tasks.
- Các bài kiểm thử rà soát cuối kỳ T019, T020, T021 có thể chạy song song.
