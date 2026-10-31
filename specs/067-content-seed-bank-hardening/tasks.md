---
description: "Task list for feature 067-content-seed-bank-hardening"
---

# Tasks: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu

**Input**: Design documents from `/specs/067-content-seed-bank-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/content-seed-bank-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Bao gồm bài kiểm thử tự động cho từng user story theo phương pháp TDD, bảo đảm kiểm thử được viết và xác nhận trước khi thực hiện logic, cùng với bộ kiểm thử hồi quy hiệu năng chuyên sâu.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent test functions, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`, `[US4]`, `[US5]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification of current repository state, existing test suites, and lint status

- [x] T001 Baseline verification of existing test suite and lint via `pytest tests/test_importer_markdown.py tests/test_bridge.py tests/test_composer.py tests/test_stable_variants.py` and `ruff check chuviettay tests`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core test harnesses and helper fixtures needed before user story tasks

- [x] T002 [P] Prepare shared test fixtures and assertion helpers for unsupported token validation and bank snapshot assertions in `tests/test_bridge.py`

---

## Phase 3: User Story 1 - Minh bạch hóa nội dung không hỗ trợ và bảo toàn thông báo khi nhập Markdown / DOCX (Priority: P1) 🎯 MVP

**Goal**: Ghi nhận đầy đủ các thành phần chưa hỗ trợ (`image`, `code_block`, `hr`, `table` trong danh sách) trong `unsupported`, ghi nhận làm phẳng `blockquote` vào `warnings` trong `MarkdownImporter`; chuyển tiếp `unsupported` qua `BrowserBridge.write_text`; hiển thị trên giao diện `webapp/js/write.js` và bảo toàn cảnh báo nạp DOCX sau khi render tự động.

**Independent Test**: Nhập tài liệu Markdown có code block, hr, image, blockquote, table trong list: xác nhận `ImportResult.unsupported` chứa mã chuẩn (`code_block`, `hr: horizontal rule`, `table: table inside list item`, `image`), `ImportResult.warnings` chứa cảnh báo blockquote; `BrowserBridge.write_text` trả về `unsupported`; và `write.js` hiển thị thông báo tiếng Việt kèm bảo toàn cảnh báo DOCX.

### Tests for User Story 1

- [x] T003 [P] [US1] Write unit tests for unsupported elements (`image`, `hr`, `code_block`, `table`) and blockquote warning in `tests/test_importer_markdown.py`
- [x] T004 [P] [US1] Write unit tests for `BrowserBridge.write_text` forwarding `unsupported` array in `tests/test_bridge.py`

### Implementation for User Story 1

- [x] T005 [US1] Update `_parse_inlines` to extract alt text into `Text(alt)` and record `"image: {alt}"` or `"image"` in `unsupported` in `chuviettay/importer/markdown_importer.py`
- [x] T006 [US1] Update `_parse_blocks` to record blockquote flattening notice into `warnings` in `chuviettay/importer/markdown_importer.py`
- [x] T007 [US1] Collect `unsupported` from all chunks and return `"unsupported": unsupported_list` in `write_text` in `chuviettay/browser/bridge.py`
- [x] T008 [US1] Update `updateInfoPanel` in `webapp/js/write.js` to render formatted unsupported notices and warnings
- [x] T009 [US1] Preserve `pendingImportNotices` across immediate preview renders in `handleFileImport` and `clearPreview` in `webapp/js/write.js`

**Checkpoint**: At this point, User Story 1 is complete: no unsupported content is dropped silently, and import warnings are preserved on UI.

---

## Phase 4: User Story 2 - Chống biến đổi nội dung người dùng do va chạm ký tự giữ chỗ PUA và dấu thoát công thức (Priority: P1)

**Goal**: Ngăn chặn va chạm ký tự PUA khi người dùng nhập thực thể HTML (`&#xE000;`, `&#57344;`...) và sửa nhận diện dấu thoát công thức (`\(`, `\)`, `\[`, `\]`) theo quy tắc đếm số lượng dấu `\` liên tiếp chẵn/lẻ.

**Independent Test**: Phân tích tài liệu chứa `&#xE000;` hoặc `&#57344;` với công thức trong blockquote: xác nhận ký tự không bị biến thành `$$`. Nhập chuỗi có $0, 1, 2, 3, 4$ dấu `\` trước `\(` và `\)`: xác nhận số chẵn mở công thức hợp lệ, số lẻ giữ nguyên văn bản thường.

### Tests for User Story 2

- [x] T010 [P] [US2] Write unit tests for PUA HTML entity decoding (`&#xE000;`, `&#57344;`, `&#x00E000;`, `&#057344;`) in `tests/test_markdown_math_block_isolation.py`
- [x] T011 [P] [US2] Write unit tests for even/odd backslash counting before formula delimiters (`\(`, `\)`, `\[`, `\]`) in `tests/test_importer_markdown.py`

### Implementation for User Story 2

- [x] T012 [US2] Add `"&#" not in text` fast-path check in `_choose_fake_close_placeholder` and entity scanning in `_collect_used_pua_codepoints` in `chuviettay/importer/markdown_importer.py`
- [x] T013 [US2] Implement `_count_preceding_backslashes` and update even/odd escape logic for opener and closer in `_convert_delimited` in `chuviettay/importer/markdown_importer.py`
- [x] T014 [US2] Protect trailing escaped space `\ ` when `strip=True` in `_convert_delimited` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 2 is complete: user characters are 100% preserved and math delimiter escape rules are standard-compliant.

---

## Phase 5: User Story 3 - Ổn định biến thể nét chữ khi chỉnh sửa tài liệu dài có tần suất từ lặp cao và kiểm soát chặt tham số viết (Priority: P2)

**Goal**: Cải tiến `align_document_seeds` kết hợp cắt bỏ prefix/suffix $O(N)$ với `SequenceMatcher(..., autojunk=False)` trên đoạn giữa, đảm bảo giữ nguyên 100% biến thể nét chữ cho 300–1.000+ từ lặp lại; bổ sung kiểm tra hợp lệ nghiêm ngặt cho `letter_gap`, `target_xh`, `pen_clearance_factor` và từ chối kiểu `bool` ở các trường số học trong `WriteOptions.validate()`.

**Independent Test**: Chèn đoạn văn vào giữa tài liệu 1.000 từ lặp: xác nhận tất cả các từ không đổi ở nửa đầu và nửa sau giữ nguyên `occurrence` và nét chữ. Chạy `WriteOptions(letter_gap=-1).validate()` hay `WriteOptions(scale=True).validate()`: xác nhận ném `ValueError`.

### Tests for User Story 3

- [x] T015 [P] [US3] Write unit tests for seed alignment stability on 300–1,000 repeating tokens in `tests/test_stable_variants.py`
- [x] T016 [P] [US3] Write unit tests for `WriteOptions.validate()` verifying `letter_gap`, `target_xh`, `pen_clearance_factor`, booleans, and reject `bool` for numeric options in `tests/test_composer.py`

### Implementation for User Story 3

- [x] T017 [US3] Implement common prefix/suffix trimming $O(N)$ and `SequenceMatcher(..., autojunk=False)` in `align_document_seeds` in `chuviettay/document/ir.py`
- [x] T018 [US3] Implement numeric validation, range bounds, `bool` rejection, and strict boolean flag validation in `WriteOptions.validate()` in `chuviettay/model/composer.py`

**Checkpoint**: At this point, User Story 3 is complete: handwriting stability is preserved on large repetitive documents and all options are safely validated.

---

## Phase 6: User Story 4 - Tăng tốc tải tab Kho mẫu bằng cơ chế Snapshot một lượt và hiển thị lỗi minh bạch (Priority: P3)

**Goal**: Thêm phương thức `get_bank_snapshot` vào `BrowserBridge`, đăng ký trong `py-worker.js`, cập nhật `bank.js` để nạp kho mẫu trong 1 lượt gọi, lưu cache theo `(revision, profileId)` để bỏ qua render thừa và hiển thị lỗi trực quan.

**Independent Test**: Gọi `get_bank_snapshot` trên `BrowserBridge`: xác nhận trả về đầy đủ stats, letters, digits, punct, symbols, marks, revision trong 1 lệnh gọi; kiểm tra `bank.js` gọi `get_bank_snapshot` và xử lý lỗi / revision skip.

### Tests for User Story 4

- [x] T019 [P] [US4] Write unit tests for `get_bank_snapshot` and `bank_revision` increment tracking in `tests/test_bridge.py`

### Implementation for User Story 4

- [x] T020 [US4] Implement `self.bank_revision` tracking and `get_bank_snapshot()` in `chuviettay/browser/bridge.py`
- [x] T021 [US4] Register `get_bank_snapshot` dispatch handler in `webapp/js/worker/py-worker.js`
- [x] T022 [US4] Update `refreshBankView` in `webapp/js/bank.js` to use `get_bank_snapshot`, cache check on `(revision, activeProfileId)`, and show visible error banner on failure

**Checkpoint**: At this point, User Story 4 is complete: bank tab updates in a single worker call and handles revisions/errors cleanly.

---

## Phase 7: User Story 5 - Kiểm thử hồi quy hiệu năng tự động cho các luồng xử lý cốt lõi (Priority: P3)

**Goal**: Xây dựng bộ kiểm thử hồi quy hiệu năng tự động tách biệt giữa bài test bất biến thuật toán chạy trong CI (`not benchmark`) và bài đo kiểm chuyên sâu (`@pytest.mark.benchmark`).

**Independent Test**: Chạy `pytest tests/test_performance_regression.py -m "not benchmark"` hoàn tất nhanh trong CI; chạy `pytest tests/test_performance_regression.py -m "benchmark"` xuất số liệu thời gian và bộ nhớ chi tiết.

### Implementation for User Story 5

- [x] T023 [P] [US5] Implement deterministic CI invariant tests for Markdown parsing scaling, seed alignment on 1,000 repeating words, and bank snapshot in `tests/test_performance_regression.py`
- [x] T024 [P] [US5] Implement detailed benchmark suite with `@pytest.mark.benchmark` for Markdown documents (10 KB, 100 KB, 1 MB), seed alignment, and bank snapshot in `tests/test_performance_regression.py`

**Checkpoint**: At this point, User Story 5 is complete: performance regressions are automatically detected in CI and via benchmarks.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Full regression suite verification, code cleanup, style check, and quickstart validation

- [x] T025 [P] Run full test suite regression via `pytest tests/` and verify all tests pass without regressions
- [x] T026 [P] Verify code quality and formatting with `ruff check chuviettay tests webapp`
- [x] T027 Run end-to-end quickstart validation scenarios from `specs/067-content-seed-bank-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3 - P1)**: Depends on Foundational (Phase 2)
- **User Story 2 (Phase 4 - P1)**: Depends on Foundational (Phase 2) - Can run in parallel with US1
- **User Story 3 (Phase 5 - P2)**: Depends on Foundational (Phase 2) - Can run after or in parallel with US1/US2
- **User Story 4 (Phase 6 - P3)**: Depends on Foundational (Phase 2) - Focuses on Bridge & Bank UI
- **User Story 5 (Phase 7 - P3)**: Depends on US1, US2, US3, US4 implementation completion to measure their actual performance
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent of other user stories
- **User Story 2 (P1)**: Independent of other user stories; both US1 and US2 modify `markdown_importer.py` but touch distinct methods
- **User Story 3 (P2)**: Modifies `ir.py` and `composer.py`, independent of Markdown importer
- **User Story 4 (P3)**: Modifies `bridge.py`, `py-worker.js`, and `bank.js`, independent of IR/composer
- **User Story 5 (P3)**: Tests the performance of components hardened in US1, US2, US3, and US4

### Within Each User Story

- Tests written FIRST and confirmed failing or covering edge cases before implementation
- Backend/Core changes implemented before UI integration
- Story independently testable before moving to the next phase

### Parallel Opportunities

- Within Phase 3 (US1): `T003` and `T004` tests can be written in parallel
- Within Phase 4 (US2): `T010` and `T011` tests can be written in parallel
- Within Phase 5 (US3): `T015` and `T016` tests can be written in parallel
- Within Phase 7 (US5): `T023` and `T024` can be implemented in parallel
- Within Phase 8: `T025` and `T026` can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests for User Story 1 in parallel:
Task: "T003 [P] [US1] Write unit tests for unsupported elements in tests/test_markdown_importer.py"
Task: "T004 [P] [US1] Write unit tests for BrowserBridge.write_text forwarding unsupported in tests/test_browser_bridge.py"

# Implement backend and frontend parts:
Task: "T005 [US1] Update _parse_inlines in chuviettay/importer/markdown_importer.py"
Task: "T007 [US1] Collect unsupported in chuviettay/browser/bridge.py"
Task: "T008 [US1] Update updateInfoPanel in webapp/js/write.js"
```

---

## Parallel Example: User Story 2

```bash
# Launch tests for User Story 2 in parallel:
Task: "T010 [P] [US2] Write unit tests for PUA HTML entity decoding in tests/test_markdown_math_block_isolation.py"
Task: "T011 [P] [US2] Write unit tests for even/odd backslash counting in tests/test_markdown_importer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`)
3. Complete Phase 3: User Story 1 (`T003` - `T009`)
4. **STOP and VALIDATE**: Verify Markdown unsupported notices & DOCX import notices are properly displayed on Web UI
5. Deliver MVP content preservation

### Incremental Delivery

1. Setup + Foundational (`T001` - `T002`) $\to$ Foundation ready
2. Add User Story 1 (`T003` - `T009`) $\to$ Test independently $\to$ Deliver MVP!
3. Add User Story 2 (`T010` - `T014`) $\to$ Test independently $\to$ PUA & Delimiter safety delivered
4. Add User Story 3 (`T015` - `T018`) $\to$ Test independently $\to$ Seed stability & Options validation delivered
5. Add User Story 4 (`T019` - `T022`) $\to$ Test independently $\to$ Bank snapshot & Worker sync delivered
6. Add User Story 5 (`T023` - `T024`) $\to$ Test independently $\to$ Performance regression suite delivered
7. Polish & Cross-Cutting (`T025` - `T027`) $\to$ Full regression & Quickstart verification complete
