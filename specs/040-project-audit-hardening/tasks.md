# Tasks: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng (Project Audit & Hardening)

**Feature**: `specs/040-project-audit-hardening`  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)  
**Status**: Ready for implementation

---

## Phase 1: Setup & Shared Infrastructure

**Purpose**: Thiết lập các tiện ích dùng chung và hạ tầng kiểm thử trước khi sửa đổi logic

- [X] T001 Tạo module tiện ích `webapp/js/html-utils.js` xuất hàm `escapeHtml(str)` dùng chung cho Web Client
- [X] T002 Cập nhật `webapp/js/write.js` để import `escapeHtml` từ `html-utils.js` thay vì hàm nội bộ
- [X] T003 [P] Tạo khung tệp kiểm thử hồi quy mới `tests/test_regression_audit.py` cho các ca test Python của spec 040
- [X] T004 [P] Tạo tệp kiểm thử đơn vị JS mới `tests/js/bank_safety.test.mjs` kiểm tra hàm `escapeHtml` với các chuỗi độc hại và ký tự toán học

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Đồng bộ các tệp test bị phân mảnh và dọn dẹp các tệp trùng lặp trước khi bước vào các User Story

- [X] T005 Di chuyển ca kiểm thử thứ 5 còn thiếu từ `tests/test_web_parse_seed.test.mjs` sang `tests/js/parse_seed.test.mjs`
- [X] T006 Xóa tệp kiểm thử trùng lặp `tests/test_web_parse_seed.test.mjs` khỏi git repository
- [X] T007 Chuyển các ca kiểm thử còn giá trị (F1, F2) từ `repro_viet_baseline.py` vào `tests/test_regression_audit.py`
- [X] T008 Xóa tệp chẩn đoán cũ `repro_viet_baseline.py` khỏi thư mục gốc theo chỉ thị

**Checkpoint**: Hạ tầng kiểm thử và cấu trúc thư mục đã sạch sẽ, sẵn sàng triển khai các User Story.

---

## Phase 3: User Story 1 - Bảo toàn toàn vẹn nội dung DOCX sang Markdown (Priority: P1) [MVP]

**Goal**: Đảm bảo `MathBlock`, `Heading`, các ký tự điều khiển Markdown (`*`, `_`, `~`, `#`, `$`, `\`, `|`) và ngắt dòng trong bảng được bảo toàn 100% qua round-trip Markdown.

**Independent Test**: `py -3.12 -m pytest tests/test_regression_audit.py -k "test_docx_markdown_roundtrip"`

### Tests for User Story 1
- [X] T009 [P] [US1] Viết unit test kiểm tra round-trip Markdown (`DocumentIR` -> Markdown text -> `MarkdownImporter` -> `DocumentIR`) cho các trường hợp: `2*3*4`, `\#`, `5\$`, `MathBlock`, `Heading`, và công thức có `|` trong bảng trong `tests/test_regression_audit.py` (đảm bảo test FAIL)

### Implementation for User Story 1
- [X] T010 [US1] Bổ sung hàm escape ký tự điều khiển Markdown cho text và inline runs trong `chuviettay/browser/bridge.py`
- [X] T011 [US1] Cập nhật `BrowserBridge._document_to_markdown_dict` để xử lý tường minh `MathBlock` (`$$...$$`), tiêu đề phân cấp `Heading` (`#`..`######`) và nối chuỗi run bằng chuỗi rỗng
- [X] T012 [US1] Cập nhật `_extract_cell_markdown` trong `chuviettay/browser/bridge.py` để escape `\|` trong công thức toán, xử lý `MathBlock` trong ô bảng và đổi `LineBreak` thành khoảng trắng
- [X] T013 [US1] Chạy lại kiểm thử T009 và đảm bảo test PASS 100%

**Checkpoint**: User Story 1 hoàn tất - nạp DOCX vào Web Client không còn bị rơi mất công thức toán hoặc vỡ định dạng.

---

## Phase 4: User Story 2 - Hỗ trợ Căn lề Đoạn văn trong Core Engine & IR (Priority: P1)

**Goal**: `DocumentLayoutEngine` tính toán đúng tọa độ ngang `line_start_x` cho `center`, `right`, và phân bổ khoảng cách từ cho `justify`.

**Independent Test**: `py -3.12 -m pytest tests/test_regression_audit.py -k "test_paragraph_alignment"` và `test_golden_master_real_path.py`

### Tests for User Story 2
- [X] T014 [P] [US2] Viết unit test kiểm tra tọa độ hình học dòng chữ và `TokenBox` cho cả 4 chế độ căn lề `left`, `center`, `right`, `justify` trong `tests/test_regression_audit.py` (đảm bảo test FAIL)

### Implementation for User Story 2
- [X] T015 [US2] Cập nhật `DocumentLayoutEngine.render_paragraph_inlines` trong `chuviettay/layout/engine.py` nhận tham số `align: str = "left"`
- [X] T016 [US2] Triển khai công thức hình học căn lề trong `flush_line`: dịch `line_start_x` cho `center`/`right`, và phân bổ khoảng cách từ cho dòng tràn trong `justify` (giữ căn trái cho dòng có `LineBreak` hoặc dòng cuối đoạn)
- [X] T017 [US2] Cập nhật việc tạo lại `RenderItem` với tọa độ `start` đã dời để `token_layout_callback` ghi nhận đúng vị trí từ
- [X] T018 [US2] Truyền `block.align` từ khối `Paragraph` khi duyệt blocks trong `render_document` tại `chuviettay/layout/engine.py`
- [X] T019 [US2] Chạy kiểm thử T014 và kiểm thử Golden Master `tests/test_golden_master_real_path.py` (đảm bảo căn trái không làm thay đổi kết xuất hiện tại)

**Checkpoint**: User Story 2 hoàn tất - Core Engine hỗ trợ căn lề chính xác 100% theo chuẩn typography.

---

## Phase 5: User Story 3 - Bảo mật DOM chống XSS và Hiển thị SVG Xem thử thật (Priority: P1)

**Goal**: Thoát ký tự HTML an toàn trong `bank.js` và dựng hình ảnh SVG nét vẽ trực quan cho từng seed trong modal xem thử ngẫu nhiên.

**Independent Test**: `npm run test:unit` và `npm run test:browser`

### Tests for User Story 3
- [X] T020 [P] [US3] Viết unit test kiểm tra `escapeHtml` ngăn chặn các chuỗi XSS `<`, `>`, `&`, `"`, `'` trong `tests/js/bank_safety.test.mjs`

### Implementation for User Story 3
- [X] T021 [US3] Cập nhật `webapp/js/bank.js`: import `escapeHtml` từ `html-utils.js` và bọc toàn bộ các vị trí nội suy DOM (`item.label`, `err.message`) trong `applyFiltersAndRender`, `openLabelDetail`, `handleDeleteLabel`
- [X] T022 [US3] Import `decompressXoppBase64`, `parseXoppXml`, và `renderPageSvgElement` từ `paper.js` vào `webapp/js/bank.js`
- [X] T023 [US3] Nâng cấp hàm `handleRandomPreview` trong `webapp/js/bank.js`: gửi tùy chọn `missing_grid: false` và `background: "plain"`, giải nén và dựng SVG nét vẽ với viewBox cắt gọn theo bbox nét vẽ, đồng thời thêm kiểm tra race condition khi đổi nhãn
**Checkpoint**: User Story 3 hoàn tất - Quản lý Kho mẫu an toàn 100% và xem thử nét vẽ trực quan.

---

## Phase 6: User Story 4 - Gạch ngang Markdown & Cảnh báo Định dạng Giàu (Priority: P2)

**Goal**: Loại bỏ dấu `~~` thừa trong nét viết tay và phát cảnh báo minh bạch khi tài liệu chứa định dạng chữ giàu.

**Independent Test**: `py -3.12 -m pytest tests/test_regression_audit.py -k "test_markdown_strikethrough"`

### Tests for User Story 4
- [X] T024 [P] [US4] Viết unit test kiểm tra cú pháp `~~text~~` được trích xuất thành chữ thuần và `warnings` ghi nhận cảnh báo khi có in đậm/nghiêng/mã trong `tests/test_regression_audit.py`

### Implementation for User Story 4
- [X] T025 [US4] Bổ sung `.enable("strikethrough")` cho `MarkdownIt` trong `chuviettay/importer/markdown_importer.py`
- [X] T026 [US4] Cập nhật `_parse_inlines` trong `chuviettay/importer/markdown_importer.py` để ghi nhận cảnh báo kiểu chữ giàu hợp nhất vào `ImportResult.warnings`
- [X] T027 [US4] Chạy lại kiểm thử T024 và đảm bảo test PASS 100%

**Checkpoint**: User Story 4 hoàn tất - nét chữ viết tay không còn rác `~~` và cảnh báo rõ ràng.

---

## Phase 7: User Story 5 - Loại bỏ Cơ chế Desktop Cũ & Rò rỉ MEMFS (Priority: P3)

**Goal**: Đổi mặc định `missing_grid=False`, loại bỏ nhánh sinh lưới cũ `hw2`, cập nhật thông điệp hướng dẫn lưới ô theo nhãn Web.

**Independent Test**: `py -3.12 -m pytest tests/test_regression_audit.py -k "test_desktop_legacy"`

### Tests for User Story 5
- [X] T028 [P] [US5] Viết unit test kiểm tra `WriteOptions().missing_grid == False`, chạy `write_text` khi thiếu mẫu không sinh file `*_thieu.xopp`, và `make_grid` chỉ sinh chuẩn `hw3` trong `tests/test_regression_audit.py`

### Implementation for User Story 5
- [X] T029 [US5] Đổi giá trị mặc định của `missing_grid` thành `False` trong `chuviettay/model/composer.py`
- [X] T030 [US5] Cập nhật các bài test cũ kỳ vọng `missing_grid=True` mặc định (như `test_composer.py`, `test_formatting.py`) truyền tường minh `missing_grid=True` nếu cần kiểm tra luồng sinh file phụ
- [X] T031 [US5] Loại bỏ nhánh sinh lưới `if grid_version == "hw2"` trong `chuviettay/model/xopp.py`, chỉ hỗ trợ sinh chuẩn `hw3`
- [X] T032 [US5] Cập nhật thông điệp tiêu đề trang lưới ô trong `chuviettay/layout/engine.py:1085`: thay câu lệnh `hw_note.py learn` cũ bằng chỉ dẫn nạp lại file tại tab "Dạy chữ" -> "Nạp file lưới"

**Checkpoint**: User Story 5 hoàn tất - hệ thống sạch bóng tàn dư desktop, triệt tiêu rò rỉ bộ nhớ MEMFS.

---

## Phase 8: Polish, Packaging & CI Quality Gates

**Purpose**: Đóng gói lại Web tĩnh, xác minh toàn bộ test suite và cổng CI

- [X] T033 Chạy `ruff check .` và sửa toàn bộ các lỗi lint (nếu có)
- [X] T034 Chạy `py -3.12 -m compileall -q .` xác minh không có lỗi cú pháp Python
- [X] T035 Chạy toàn bộ test suite Python: `py -3.12 -m pytest -vv -s --timeout=60 -m "not benchmark"`
- [X] T036 Chạy build web tĩnh: `py -3.12 scripts/build_web.py`
- [X] T037 Chạy toàn bộ test suite JS: `npm run test:unit && npm run test:browser`
- [X] T038 Kiểm tra `git status` đảm bảo working tree sạch sẽ, không còn file rác

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: Không phụ thuộc, thực hiện đầu tiên.
- **Phase 2 (Foundational)**: Phụ thuộc Phase 1. Khóa toàn bộ các User Story cho tới khi hoàn tất dọn dẹp file.
- **Phase 3 (US1 - DOCX Roundtrip)**: Có thể thực hiện độc lập sau Phase 2 [MVP].
- **Phase 4 (US2 - Alignment)**: Có thể thực hiện độc lập sau Phase 2.
- **Phase 5 (US3 - Bank Safety)**: Có thể thực hiện độc lập sau Phase 1 & 2.
- **Phase 6 (US4 - Markdown Strikethrough)**: Có thể thực hiện độc lập sau Phase 2.
- **Phase 7 (US5 - Desktop Cleanup)**: Thực hiện sau US1..US4 để đảm bảo không ảnh hưởng các test đang chạy.
- **Phase 8 (Polish & CI)**: Thực hiện cuối cùng sau khi hoàn tất tất cả các Phase trước.
