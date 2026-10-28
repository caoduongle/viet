---
description: "Task list for feature 063-pua-placeholder-optimization"
---

# Tasks: Tối ưu hóa tìm ký tự giữ chỗ PUA và kiểm thử cạn kiệt toàn bộ vùng giữ chỗ

**Input**: Design documents from `/specs/063-pua-placeholder-optimization/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/pua-placeholder-optimization-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Áp dụng phương pháp TDD cho việc kiểm chứng fast-path, chuỗi va chạm PUA, và trường hợp biên cạn kiệt toàn bộ 6.400 ký tự.

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

**Purpose**: Core constant definition and range standardization in `MarkdownImporter`

**⚠️ CRITICAL**: Must be completed before User Story 1 and User Story 2 implementation

- [x] T002 Add `_FAKE_CLOSE_PUA_COUNT` constant to `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundational constant ready - user story implementation can begin

---

## Phase 3: User Story 1 - Tối ưu hóa hiệu năng tìm ký tự PUA khi xảy ra va chạm ký tự đầu dãy (Priority: P1) 🎯 MVP

**Goal**: Tối ưu hóa thuật toán chọn ký tự PUA: áp dụng Fast-path tức thời $O(1)$ cho `U+E000` và Slow-path dùng `used_cps: set[int]` qua `set(text)` chạy bằng C để giảm độ phức tạp từ $O(k \times N)$ về $O(N)$ khi gặp chuỗi nhiều ký tự PUA liên tiếp.

**Independent Test**: Gọi `_choose_fake_close_placeholder` với chuỗi không có `\ue000` (trả về `\ue000`), chuỗi rỗng (trả về `\ue000`), chuỗi chứa 10 ký tự `\ue000`..`\ue009` (trả về `\ue00a`), và chuỗi ngắt quãng `\ue000\ue002\ue003` (trả về `\ue001`).

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Write unit tests for fast-path, empty string, multiple collision chain, and sparse collision in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T004 [US1] Implement fast-path and single-pass `used_cps` set optimization in `MarkdownImporter._choose_fake_close_placeholder` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and delivers optimal $O(1)$ and $O(N)$ performance across all collision scenarios.

---

## Phase 4: User Story 2 - Xử lý an toàn và bảo toàn dữ liệu khi cạn kiệt toàn bộ vùng ký tự PUA (Priority: P2)

**Goal**: Đảm bảo hàm chọn ký tự trả về `None` khi toàn bộ 6.400 ký tự PUA xuất hiện trong văn bản, và quy trình `import_text()` thực hiện cơ chế dự phòng an toàn (graceful fallback) không ném ngoại lệ và không làm biến đổi ký tự của người dùng.

**Independent Test**: Cung cấp chuỗi chứa đủ 6.400 ký tự PUA (`0xE000`..`0xF8FF`); xác nhận `_choose_fake_close_placeholder` trả về `None`, và `import_text()` hoàn thành thành công mà vẫn bảo toàn 100% các ký tự PUA gốc trong tài liệu đầu ra.

### Tests for User Story 2 (TDD - Write First) 🧪

- [x] T005 [P] [US2] Write unit test for 6,400 PUA exhaustion returning None and end-to-end fallback test for `import_text` preserving user characters in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 2

- [x] T006 [US2] Implement $O(1)$ early exit on full exhaustion (`len(used_cps) == _FAKE_CLOSE_PUA_COUNT`) in `MarkdownImporter._choose_fake_close_placeholder` and verify graceful fallback behavior in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Stories 1 AND 2 work together reliably: the system handles normal, collision, and full exhaustion cases gracefully.

---

## Phase 5: User Story 3 - Kiểm thử hồi quy tự động siết chặt cho vùng PUA và tương thích toàn diện (Priority: P3)

**Goal**: Đảm bảo 100% các ca kiểm thử hiện có (bảo toàn LaTeX `\$\$`, blockquote lồng nhau) tiếp tục vượt qua, và bài benchmark độ phức tạp duy trì tỷ lệ tăng trưởng tuyến tính $T(4N)/T(N) \le 6.0$.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py` và `pytest tests/test_markdown_importer.py`; xác nhận tất cả các bài kiểm thử đều đạt.

### Implementation for User Story 3

- [x] T007 [P] [US3] Run full test suite regression verification via `pytest tests/test_markdown_math_block_isolation.py` and `pytest tests/test_markdown_importer.py`
- [x] T008 [US3] Verify adversarial complexity benchmark ratio $T(4N)/T(N) \le 6.0$ in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: All user stories functional and verified without performance or functional regression.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Code cleanup, linting, formatting, and Pyodide Web Client verification

- [x] T009 [P] Code cleanup and style verification with `ruff check chuviettay/importer/markdown_importer.py tests/test_markdown_math_block_isolation.py`
- [x] T010 Run quickstart.md validation script and Golden Master Pyodide verification via `node scripts/test_golden_pyodide.mjs`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS User Story 1 and User Story 2
- **User Stories (Phase 3+)**:
  - **US1 (Phase 3)**: Depends on Phase 2 - Delivers MVP performance optimization
  - **US2 (Phase 4)**: Depends on Phase 3 implementation
  - **US3 (Phase 5)**: Depends on Phase 3 and Phase 4 completion
- **Polish (Phase 6)**: Depends on all user stories passing verification

### User Story Dependencies

- **User Story 1 (P1)**: Foundation for optimized character lookup (Fast-path + set lookup)
- **User Story 2 (P2)**: Builds upon US1 by adding exhaustion early-exit and E2E fallback verification
- **User Story 3 (P3)**: Validates overall regression and benchmark stability across US1 & US2

### Parallel Opportunities

- Within Phase 3 (US1): `T003` (tests) can be authored before or in parallel with foundational tasks
- Within Phase 4 (US2): `T005` (tests) can be authored in parallel with US1 implementation
- Within Phase 5 (US3): `T007` (regression tests) can run in parallel with polish tasks
- Within Phase 6: `T009` (ruff check) can run in parallel with Pyodide checks

---

## Parallel Example: User Story 1 & 2 Tests

```bash
# Authoring unit and integration tests in tests/test_markdown_math_block_isolation.py:
Task: "T003 [P] [US1] Write unit tests for fast-path, empty string, multiple collision chain, and sparse collision"
Task: "T005 [P] [US2] Write unit test for 6,400 PUA exhaustion returning None and end-to-end fallback test"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`)
3. Complete Phase 3: User Story 1 (`T003`, `T004`)
4. **STOP and VALIDATE**: Verify fast-path and collision handling independently
5. Deliver MVP optimization

### Incremental Delivery

1. Setup + Foundational (`T001` - `T002`)
2. US1: Fast-path and $O(N)$ set-based PUA selection (`T003` - `T004`) $\to$ Validate MVP
3. US2: Exhaustion handling ($O(1)$ early exit and E2E fallback) (`T005` - `T006`) $\to$ Validate Safety
4. US3: Full regression and benchmark verification (`T007` - `T008`)
5. Polish: Lint and Pyodide Golden Master check (`T009` - `T010`)
