# Tasks: Gia Cố An Toàn Xóa Thư Mục Build Và Hoàn Thiện Cú Pháp CommonMark/GFM (056-build-safety-and-markdown-hardening)

**Input**: Design documents from `specs/056-build-safety-and-markdown-hardening/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Tests**: Bao gồm kiểm thử đơn vị, kiểm thử an toàn thư mục, kiểm thử tích hợp CommonMark/GFM và kiểm thử độ phức tạp tuyến tính theo yêu cầu đặc tả.  
**Organization**: Tasks được phân chia theo từng User Story để hỗ trợ thực thi độc lập và kiểm chứng tách biệt.

---

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Có thể chạy song song (khác tệp tin, không phụ thuộc vào task chưa hoàn thành)
- **[Story]**: Gắn với User Story tương ứng (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Mô tả công việc luôn đi kèm đường dẫn tệp cụ thể

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Khởi tạo môi trường và xác nhận trạng thái codebase trước khi triển khai

- [X] T001 Xác nhận môi trường làm việc và trạng thái test suite hiện tại trên `chuviettay/`, `scripts/build_web.py` và `tests/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Chuẩn bị các cấu trúc nền tảng và helper dùng chung cho các User Stories

- [X] T002 Cập nhật hằng số và chuẩn hóa quy tắc kiểm tra ranh giới thư mục đích trong `scripts/build_web.py`
- [X] T003 Xây dựng hàm helper kiểm tra ký tự thoát backtick chẵn/lẻ dùng chung trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nền tảng helper hoàn tất - các User Story có thể tiến hành độc lập

---

## Phase 3: User Story 1 - Bảo vệ dữ liệu người dùng khi Build Web vào thư mục ngoài (Priority: P1) 🎯 MVP

**Goal**: Đảm bảo `build_web.py` từ chối tuyệt đối việc xóa bất kỳ thư mục ngoài không rỗng nào nếu thiếu cờ `--force-clean`, không bao giờ xóa tệp người dùng chỉ vì có marker cũ.

**Independent Test**: Tạo một thư mục ngoài, đặt tệp `user_doc.txt`, chạy `prepare_dist_dir` không có `force_clean`: xác nhận ném `SystemExit` và `user_doc.txt` được bảo toàn nguyên vẹn.

### Tests for User Story 1
- [X] T004 [P] [US1] Cập nhật test case kiểm tra ngăn chặn xóa thư mục ngoài không rỗng khi thiếu `--force-clean` trong `tests/test_build_web.py`

### Implementation for User Story 1
- [X] T005 [US1] Sửa đổi hàm `prepare_dist_dir` trong `scripts/build_web.py` để bắt buộc `--force-clean` với thư mục ngoài không rỗng và ngừng tạo tệp `.chuviettay_build_dist` trong thư mục đích

**Checkpoint**: User Story 1 hoàn tất và có thể kiểm chứng độc lập mà không ảnh hưởng tới các module khác

---

## Phase 4: User Story 2 - Bảo toàn khối mã trong Blockquote, Indented Code và Escaped Backtick theo CommonMark (Priority: P1)

**Goal**: Bảo vệ 100% nội dung mã nguồn bên trong khối mã trích dẫn (`> ~~~`), khối mã thụt lề 4 khoảng trắng, và xử lý đúng ký tự backtick bị escape (`\``) qua toàn bộ pipeline `import_text()`.

**Independent Test**: Nạp tài liệu chứa trích dẫn blockquote bao bọc khối mã tilde (`> ~~~latex\n> \[x=1\]\n> ~~~`), indented code (`    \[x=1\]`) và escaped backtick (`dấu \` không đóng code`): xác nhận công thức toán bên trong không bị chuyển đổi thành `$$x=1$$`.

### Tests for User Story 2
- [X] T006 [P] [US2] Thêm các bài kiểm thử cho code fence trong blockquote, indented code block, và escaped backtick trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 2
- [X] T007 [US2] Nâng cấp `_split_code_segments` và `_find_code_spans` trong `chuviettay/importer/markdown_importer.py` để nhận diện blockquote fences, indented code blocks (có xét dòng trước đó) và bỏ qua backtick bị escape

**Checkpoint**: User Story 1 và User Story 2 đều hoạt động độc lập và bảo đảm tính toàn vẹn cú pháp

---

## Phase 5: User Story 3 - Nhận diện ngữ cảnh Bảng GFM chặt chẽ và bảo toàn giá trị ô (Priority: P2)

**Goal**: Chỉ coi một dòng là hàng bảng khi dòng đó thực sự nằm trong một khối bảng GFM có hàng phân cách cột (`---|---`), phân tách đúng dòng toán đơn độc `$$x=1$$ | 2`, và bảo toàn toàn bộ giá trị ô trong bảng compact.

**Independent Test**: Nạp dòng đơn `$$x=1$$ | 2` (tách thành MathBlock và Paragraph); nạp bảng compact có tiêu đề và hàng phân cách (tạo Table với hàng 2 ô 1 là MathInline và ô 2 là Text("2")).

### Tests for User Story 3
- [X] T008 [P] [US3] Thêm bài kiểm thử cho dòng đơn độc lập `$$x=1$$ | 2` và kiểm tra chi tiết giá trị từng ô trong bảng compact trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 3
- [X] T009 [US3] Triển khai cơ chế tiền quét (pre-scan) phát hiện khối bảng có hàng phân cách cột và cập nhật `_is_table_line` trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nhận diện bảng GFM chính xác theo ngữ cảnh khối, loại bỏ hoàn toàn việc nhận diện nhầm dòng toán đơn lẻ

---

## Phase 6: User Story 4 - Làm sạch Artifact thành phẩm và loại trừ thư mục ẩn khỏi Service Worker (Priority: P2)

**Goal**: Đảm bảo thư mục xuất xưởng phân phối web (`dist_dir`) sạch hoàn toàn tệp marker nội bộ và Service Worker không thu thập bất kỳ tệp nào trong các thư mục ẩn (dot-directories).

**Independent Test**: Kiểm tra `sw.js` và thư mục `dist`: không có tệp `.chuviettay_build_dist`, và các tệp trong thư mục giả lập `.internal/` không xuất hiện trong `PRECACHE_URLS`.

### Tests for User Story 4
- [X] T010 [P] [US4] Thêm bài kiểm thử xác nhận tệp trong thư mục ẩn không lọt vào `sw.js` và không còn marker trong `dist` trong `tests/test_build_web.py`

### Implementation for User Story 4
- [X] T011 [US4] Cập nhật hàm `generate_sw_js` trong `scripts/build_web.py` để cắt tỉa thư mục ẩn in-place bằng `dirs[:] = [d for d in dirs if not d.startswith('.')]`

**Checkpoint**: Gói phân phối web thành phẩm hoàn toàn sạch sẽ, Service Worker precache an toàn tuyệt đối

---

## Phase 7: User Story 5 - Bộ kiểm thử hồi quy độ phức tạp tuyến tính và an toàn dữ liệu toàn diện (Priority: P2)

**Goal**: Đo tỷ lệ tăng trưởng thời gian $T(2N) / T(N) \le 3.5$ trên toàn bộ pipeline tiền xử lý (bao gồm `_split_code_segments`), và kiểm thử an toàn thư mục ngoài khi người dùng thêm tệp mới sau lần build trước.

**Independent Test**: Chạy bài đo hiệu năng với 2.500 và 5.000 cặp dòng kiểm tra tỷ lệ tăng thời gian $\le 3.5x$; chạy bài test thư mục ngoài có tệp mới xác nhận lệnh build từ chối xóa.

### Implementation and Verification for User Story 5
- [X] T012 [P] [US5] Mở rộng bài kiểm thử đo tỷ lệ co giãn $T(2N) / T(N) \le 3.5$ trên toàn bộ pipeline tiền xử lý trong `tests/test_markdown_math_block_isolation.py`
- [X] T013 [P] [US5] Bổ sung bài kiểm thử hồi quy kịch bản thư mục ngoài có tệp người dùng mới thêm sau lần build trước trong `tests/test_build_web.py`

**Checkpoint**: Toàn bộ các ca biên hiệu năng và an toàn dữ liệu được tự động kiểm tra trên CI

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm tra chất lượng tổng thể, format mã nguồn và xác nhận không có bất kỳ hồi quy nào

- [X] T014 [P] Chạy kiểm tra style và linting với `ruff check .`
- [X] T015 [P] Chạy toàn bộ test suite Python với `pytest tests/` (1.300+ tests)
- [X] T016 [P] Chạy toàn bộ test suite JavaScript với `npm run test:unit`
- [X] T017 [P] Chạy xác thực Pyodide Golden Master với `node scripts/test_golden_pyodide.mjs`
- [X] T018 Xác thực kịch bản mẫu từ `specs/056-build-safety-and-markdown-hardening/quickstart.md` và chạy build web hoàn chỉnh với `python scripts/build_web.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không phụ thuộc - có thể bắt đầu ngay.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup - cung cấp helper dùng chung cho US1 và US2.
- **User Stories (Phase 3 đến Phase 7)**:
  - **US1 (P1)**: Phụ thuộc vào T002 - triển khai an toàn thư mục build ngoài.
  - **US2 (P1)**: Phụ thuộc vào T003 - triển khai bảo vệ khối mã blockquote/indented/escaped.
  - **US3 (P2)**: Có thể tiến hành độc lập hoặc sau US2 trên `markdown_importer.py`.
  - **US4 (P2)**: Có thể tiến hành song song với US3 hoặc tiếp sau US1 trên `build_web.py`.
  - **US5 (P2)**: Chạy sau khi hoàn tất US1, US2, US3, US4 để đo đạc và bảo đảm độ bao phủ.
- **Polish (Phase 8)**: Chạy sau khi toàn bộ User Stories hoàn tất.

### Parallel Opportunities

- T004 [US1] và T006 [US2] có thể viết test song song (hai file test độc lập).
- T008 [US3] và T010 [US4] có thể viết test song song.
- T012 [US5] và T013 [US5] có thể viết test song song.
- T014, T015, T016, T017 có thể chạy song song ở bước thẩm định chất lượng.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1 & Phase 2 (T001, T002, T003).
2. Hoàn thành Phase 3 (T004, T005): Khắc phục dứt điểm rủi ro mất dữ liệu người dùng khi build lại vào thư mục ngoài.
3. Xác minh độc lập User Story 1 với `pytest tests/test_build_web.py`.

### Incremental Delivery

1. Setup + Foundational $\to$ Foundation sẵn sàng.
2. User Story 1 (P1) $\to$ An toàn thư mục ngoài đạt chuẩn (MVP).
3. User Story 2 (P1) $\to$ Bảo toàn khối mã CommonMark lồng nhau.
4. User Story 3 (P2) $\to$ Ngữ cảnh bảng GFM chuẩn tắc.
5. User Story 4 (P2) $\to$ Làm sạch Service Worker precache.
6. User Story 5 (P2) $\to$ Bộ test hồi quy và hiệu năng $O(n)$.
7. Polish $\to$ Linting, Golden Master, 100% CI pass.
