---
description: "Task list for feature 064-pua-memory-and-benchmark"
---

# Tasks: Khống chế bộ nhớ tập hợp PUA và chuẩn hóa thống kê kiểm thử hiệu năng

**Input**: Design documents from `/specs/064-pua-memory-and-benchmark/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/pua-memory-and-benchmark-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Áp dụng phương pháp TDD cho việc kiểm chứng khống chế bộ nhớ tập hợp PUA trên văn bản đa ngữ lớn và bài benchmark thống kê trung vị.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent test functions, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification of current repository state and test suite

- [x] T001 Baseline verification of existing test suite and code quality via `pytest tests/test_markdown_math_block_isolation.py` and `ruff check chuviettay tests`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pre-compile PUA regex pattern at module level in `chuviettay/importer/markdown_importer.py`

**⚠️ CRITICAL**: Must be completed before User Story 1 implementation

- [x] T002 Pre-compile `_PUA_RE` regex pattern in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundational regex pre-compiled - user story implementation can begin

---

## Phase 3: User Story 1 - Khống chế tuyệt đối mức sử dụng bộ nhớ tạm khi tài liệu chứa U+E000 (Priority: P1) 🎯 MVP

**Goal**: Thay thế `set(text)` bằng `_PUA_RE.finditer(text)` với cơ chế thoát sớm khi đạt đủ `_FAKE_CLOSE_PUA_COUNT`, khống chế tuyệt đối bộ nhớ phụ $\le 6.400$ phần tử mà không tạo danh sách trung gian.

**Independent Test**: Gọi `_choose_fake_close_placeholder` với văn bản chứa 10.000 ký tự phân biệt (chữ Hán/Nôm) và ký tự `\ue000`; xác nhận tập hợp `used_cps` nội bộ chỉ có đúng 1 phần tử `{0xE000}` và trả về `\ue001`.

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Write unit tests for bounded PUA memory collection on large multilingual documents with `\ue000` in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T004 [US1] Implement bounded PUA collection via `_PUA_RE.finditer` with early exit in `MarkdownImporter._choose_fake_close_placeholder` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and guarantees strict $O(\min(N, 6400))$ memory bounds across arbitrary Unicode alphabets.

---

## Phase 4: User Story 2 - Đánh giá hiệu năng khách quan và ổn định bằng thống kê trung vị (Priority: P2)

**Goal**: Nâng cấp `test_adversarial_complexity_multi_length_backticks_and_long_lines` sử dụng phương pháp thống kê trung vị trên 5 lượt đo độc lập, loại bỏ hoàn toàn cơ chế chọn lọc thiên vị `min(ratio, retry)`.

**Independent Test**: Chạy `test_adversarial_complexity_multi_length_backticks_and_long_lines` và xác nhận kết quả trung vị $R_{\text{med}} \le 6.0$ với đầy đủ nhật ký chẩn đoán 5 lượt đo.

### Implementation for User Story 2

- [x] T005 [US2] Update `test_adversarial_complexity_multi_length_backticks_and_long_lines` to use 5-round `statistics.median` without min retry bias in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: At this point, the adversarial performance benchmark is unbiased, statistically robust against OS scheduling jitter, and ready for CI.

---

## Phase 5: User Story 3 - Chuẩn hóa tài liệu kỹ thuật và làm rõ độ phức tạp tính toán (Priority: P3)

**Goal**: Chuẩn hóa docstring của `_choose_fake_close_placeholder` và các tài liệu thiết kế, phân định rõ thời gian $O(N)$ ở tầng C và bộ nhớ phụ $O(1)$ / $O(\min(N, 6400))$.

**Independent Test**: Rà soát docstring của `_choose_fake_close_placeholder` và các tài liệu đặc tả; xác nhận không còn tuyên bố thời gian $O(1)$ cho thao tác tìm kiếm chuỗi con.

### Implementation for User Story 3

- [x] T006 [P] [US3] Update docstrings and complexity descriptions in `chuviettay/importer/markdown_importer.py` and `specs/064-pua-memory-and-benchmark/`

**Checkpoint**: All documentation and code comments accurately reflect actual algorithmic behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full regression testing, code cleanup, linting, formatting, and Pyodide Web Client verification

- [x] T007 [P] Run full test suite regression verification via `pytest tests/test_markdown_math_block_isolation.py` and `pytest tests/test_importer_markdown.py`
- [x] T008 [P] Code cleanup and style verification with `ruff check chuviettay/importer/markdown_importer.py tests/test_markdown_math_block_isolation.py`
- [x] T009 Run quickstart.md validation script and Golden Master Pyodide verification via `node scripts/test_golden_pyodide.mjs`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS User Story 1
- **User Stories (Phase 3+)**:
  - **US1 (Phase 3)**: Depends on Phase 2 - Delivers bounded memory collection MVP
  - **US2 (Phase 4)**: Can proceed after US1 tests/implementation
  - **US3 (Phase 5)**: Depends on US1 and US2 completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundational optimization for memory safety
- **User Story 2 (P2)**: Independent benchmark enhancement
- **User Story 3 (P3)**: Documentation synchronization across US1 & US2

### Parallel Opportunities

- Within Phase 3 (US1): `T003` (tests) can run in parallel with foundational preparation
- Within Phase 5 (US3): `T006` (docstrings) can run in parallel with benchmark refinement
- Within Phase 6: `T007`, `T008`, `T009` can be dispatched independently

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`)
3. Complete Phase 3: User Story 1 (`T003`, `T004`)
4. **STOP and VALIDATE**: Verify bounded memory on large multilingual input
5. Deliver MVP memory safety

### Incremental Delivery

1. Setup + Foundational (`T001` - `T002`)
2. US1: Bounded PUA collection (`T003` - `T004`) $\to$ Validate MVP
3. US2: Median benchmark methodology (`T005`) $\to$ Validate Benchmark
4. US3: Documentation accuracy (`T006`)
5. Polish: Full regression, Lint, and Pyodide check (`T007` - `T009`)
