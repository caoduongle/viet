# Tasks: Khôi phục CI xanh, sửa cấu hình Render và siết các trường hợp biên của Markdown importer (058-ci-e2e-render-markdown-hardening)

**Input**: Design documents from `specs/058-ci-e2e-render-markdown-hardening/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/build-and-markdown-contract.md`, `quickstart.md`  
**Tests**: Đầy đủ các bài kiểm thử tự động cho Playwright E2E, cấu hình Render, khối mã thụt lề, bảng GFM và benchmark độ phức tạp tuyến tính $O(n)$ không điều kiện.  
**Organization**: Tasks được phân chia theo từng User Story để hỗ trợ thực thi độc lập và kiểm chứng tách biệt.

---

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Có thể chạy song song (khác tệp tin, không phụ thuộc vào task chưa hoàn thành)
- **[Story]**: Gắn với User Story tương ứng (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Mô tả công việc luôn đi kèm đường dẫn tệp cụ thể

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Xác nhận hiện trạng codebase và các tệp kiểm thử trước khi thực hiện thay đổi

- [X] T001 Xác nhận hiện trạng lỗi Playwright trong `tests/e2e/sw-update.spec.ts` và cấu hình `render.yaml`
- [X] T002 Xác nhận trạng thái bộ kiểm thử importer hiện có trong `tests/test_markdown_math_block_isolation.py` và `tests/test_version_metadata.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Chuẩn bị các cấu trúc regex biên dịch sẵn ở cấp lớp và helper dùng chung cho các User Stories

- [X] T003 Chuẩn hóa regex biên dịch sẵn cấp lớp `_BQ_PREFIX_RE` và helper kiểm tra cấu trúc bảng GFM trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nền tảng helper hoàn tất — các User Story có thể tiến hành độc lập

---

## Phase 3: User Story 1 - CI Web Client Xanh & Bảo Toàn An Toàn Build (Priority: P1) 🎯 MVP

**Goal**: Cho phép bài kiểm thử `tests/e2e/sw-update.spec.ts` truyền cờ `--force-clean` ở lần build thứ hai vào thư mục tạm `tmpDist`, giữ nguyên 100% rào chắn bảo vệ của `prepare_dist_dir()` trong `scripts/build_web.py`.

**Independent Test**: Chạy `npx playwright test tests/e2e/sw-update.spec.ts` vượt qua và `pytest tests/test_build_web.py` tiếp tục pass 9/9 tests.

### Implementation for User Story 1
- [X] T004 [US1] Bổ sung tham số `forceClean = false` vào hàm `runBuildWeb()` và truyền `true` ở lần build thứ hai trong `tests/e2e/sw-update.spec.ts`
- [X] T005 [US1] Xác minh bài kiểm thử an toàn build trong `tests/test_build_web.py` tiếp tục bảo vệ thư mục ngoài không rỗng khi thiếu `--force-clean`

**Checkpoint**: User Story 1 hoàn tất — lỗi CI Playwright được giải quyết mà không làm suy yếu an toàn build

---

## Phase 4: User Story 2 - Cấu Hình Render Phiên Bản Python Hợp Lệ (Priority: P1)

**Goal**: Loại bỏ biến môi trường `PYTHON_VERSION` khỏi `render.yaml` để Render sử dụng tệp `.python-version` (`3.13`) làm nguồn phiên bản duy nhất, tránh lỗi định dạng `Major.Minor.Patch`.

**Independent Test**: `pytest tests/test_version_metadata.py` vượt qua và xác nhận `render.yaml` không chứa cấu hình `PYTHON_VERSION` rút gọn.

### Tests for User Story 2
- [X] T006 [P] [US2] Cập nhật test guard trong `tests/test_version_metadata.py` để khẳng định `.python-version` là `"3.13"` và `render.yaml` không khai báo biến `PYTHON_VERSION` dạng rút gọn

### Implementation for User Story 2
- [X] T007 [US2] Xóa khai báo biến môi trường `PYTHON_VERSION` khỏi dịch vụ `chuviettay-web` trong `render.yaml`

**Checkpoint**: Cấu hình triển khai Render đồng bộ với tệp phiên bản gốc của repo

---

## Phase 5: User Story 3 - Bảo Toàn Khối Mã Thụt Lề trong Markdown Importer (Priority: P1)

**Goal**: Bổ sung trạng thái `in_indented_code` vào `_isolate_display_math_blocks()` và chuẩn hóa indent khi tách công thức trên dòng tiếp nối đoạn văn, bảo toàn 100% ký tự trong khối mã thụt lề qua toàn bộ pipeline `import_text()`.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k "indented"` vượt qua 100% các ca thử nghiệm chứa `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, và thẻ HTML trong khối mã thụt lề.

### Tests for User Story 3
- [X] T008 [P] [US3] Viết bài test cho khối mã thụt lề chứa `prefix:$$x=1$$`, `$$y=2$$`, `\[z=3\]`, thẻ `<b>tag</b>`, dòng trống xen giữa và dòng tiếp nối lười trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 3
- [X] T009 [US3] Bổ sung trạng thái `in_indented_code` và cơ chế theo dõi `can_start_indented` trong `_isolate_display_math_blocks()` của `chuviettay/importer/markdown_importer.py`
- [X] T010 [US3] Chuẩn hóa khoảng trắng đầu dòng về $\le 3$ spaces khi tách công thức `$$...$$` trên dòng tiếp nối đoạn văn cấp gốc trong `_isolate_display_math_blocks()` của `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nội dung khối mã thụt lề được bảo toàn nguyên vẹn 100% qua mọi bước tiền xử lý

---

## Phase 6: User Story 4 - Siết Nhận Diện Ngữ Cảnh Bảng GFM (Priority: P2)

**Goal**: Đảm bảo tiền quét bảng GFM chỉ đánh dấu các dòng thuộc bảng khi khớp số cột giữa dòng tiêu đề và dòng phân cách ($C_{\text{header}} == C_{\text{delim}} \ge 1$), không bỏ sót việc tách công thức ở đoạn văn chứa `|` đứng trước bảng hoặc trước chuỗi giả phân cách.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k "table"` vượt qua cả các ca bảng compact, bảng chuẩn và đoạn văn chứa `|` kèm công thức liền kề bảng.

### Tests for User Story 4
- [X] T011 [P] [US4] Viết bài test kiểm tra đoạn văn chứa `|` và `$$...$$` đứng ngay trước bảng GFM trong cùng nhóm dòng và đoạn văn đứng trước chuỗi giả phân cách trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 4
- [X] T012 [US4] Cải tiến thuật toán tiền quét `table_line_indices` trong `_isolate_display_math_blocks()` để kiểm tra chính xác số cột $C_{\text{header}} == C_{\text{delim}} \ge 1$ và chỉ đánh dấu từ dòng tiêu đề `h = d - 1` trở đi trong `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Nhận diện bảng GFM tuân thủ nghiêm ngặt chuẩn CommonMark / GFM, không nuốt công thức của đoạn văn

---

## Phase 7: User Story 5 - Đảm Bảo Độ Phức Tạp Tuyến Tính $O(n)$ cho Bộ Tiền Xử Lý (Priority: P2)

**Goal**: Loại bỏ thao tác cắt lát chuỗi `text[i:]`, tối ưu bước nhảy dòng trống trong indented code, và bổ sung bộ nhớ đệm backtick (`backticks_scanned` + `backticks_max_pos`) để đảm bảo thời gian xử lý tăng tuyến tính $O(n)$ ngay cả trên đầu vào bất lợi có nhiều dấu backtick mở không đóng.

**Independent Test**: Chạy bài test kiểm tra tỷ lệ tăng thời gian $T(4N)/T(N) \le 6.0$ trên các kích thước $N, 2N, 4N$ với đầu vào bất lợi trong `tests/test_markdown_math_block_isolation.py`.

### Tests for User Story 5
- [X] T013 [P] [US5] Viết bài test kiểm tra độ phức tạp tuyến tính vô điều kiện ($T(4N)/T(N) \le 6.0$) với đầu vào bất lợi nhiều dòng blockquote và nhiều backtick mở không đóng trong `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 5
- [X] T014 [US5] Thay thế `re.match(..., text[i:])` bằng `_BQ_PREFIX_RE.match(text, i, eol)` và tối ưu bước nhảy dòng trống khối mã thụt lề trong `_split_code_segments()` của `chuviettay/importer/markdown_importer.py`
- [X] T015 [US5] Áp dụng cơ chế bộ nhớ đệm `backticks_scanned` và `backticks_max_pos` trong `_split_code_segments()` và `_find_code_spans()` của `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Bộ tiền xử lý Markdown đạt độ phức tạp tuyến tính $O(n)$ nghiêm ngặt cả về thời gian và bộ nhớ

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Kiểm tra chất lượng toàn diện, format mã nguồn, kiểm chứng Golden Master và bảo đảm 0 hồi quy

- [X] T016 [P] Chạy kiểm tra style và linting với `ruff check .`
- [X] T017 [P] Chạy toàn bộ test suite JavaScript với `npm run test:unit`
- [X] T018 [P] Chạy kiểm chứng Pyodide Golden Master với `node scripts/test_golden_pyodide.mjs`
- [X] T019 Chạy build web client dist sạch với `python scripts/build_web.py`
- [X] T020 Chạy toàn bộ test suite Python với `pytest -m "not benchmark"`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Không phụ thuộc — bắt đầu ngay.
- **Foundational (Phase 2)**: Phụ thuộc vào Setup — chuẩn hóa regex cấp lớp.
- **User Stories (Phase 3..7)**:
  - **US1 (P1)**: Độc lập với Markdown importer — có thể làm ngay để CI xanh.
  - **US2 (P1)**: Độc lập với US1 và Markdown importer — sửa cấu hình deploy.
  - **US3 (P1)**: T008 (test) $\to$ T009, T010 (code).
  - **US4 (P2)**: T011 (test) $\to$ T012 (code), kế thừa cấu trúc từ US3.
  - **US5 (P2)**: T013 (test) $\to$ T014, T015 (code), hoàn thiện tối ưu $O(n)$.
- **Polish (Phase 8)**: Chạy sau khi hoàn tất tất cả User Stories.

### Parallel Opportunities

- T004/T005 (US1), T006/T007 (US2), và T008 (US3) có thể tiến hành song song vì tác động trên các tệp hoàn toàn khác nhau (`sw-update.spec.ts`, `render.yaml`, `test_markdown_math_block_isolation.py`).
- T016, T017, T018 trong Phase 8 có thể chạy song song ở bước thẩm định chất lượng cuối cùng.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Hoàn thành Phase 1 & Phase 3 (T004, T005): Khắc phục trực tiếp bài kiểm thử Playwright đang làm đỏ CI.
2. Xác minh độc lập User Story 1 với `npx playwright test tests/e2e/sw-update.spec.ts`.

### Incremental Delivery

1. US1 (P1) $\to$ CI Web Client xanh trở lại (MVP).
2. US2 (P1) $\to$ Cấu hình Render chuẩn hóa về `.python-version`.
3. US3 (P1) $\to$ Khối mã thụt lề bảo toàn nguyên vẹn 100%.
4. US4 (P2) $\to$ Nhận diện bảng GFM chuẩn xác, bảo toàn công thức đoạn văn liền kề.
5. US5 (P2) $\to$ Đạt độ phức tạp tuyến tính $O(n)$ không điều kiện.
6. Polish $\to$ 100% test suites pass, Golden Master match 100%.
