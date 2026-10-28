---
description: "Task list for feature 065-pua-verification-reproducibility"
---

# Tasks: Đo lường trực tiếp bộ nhớ PUA và kịch bản tái lập benchmark độc lập

**Input**: Design documents from `/specs/065-pua-verification-reproducibility/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/pua-verification-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Áp dụng phương pháp TDD cho việc kiểm chứng trực tiếp số lượng phần tử tập hợp PUA và kiểm thử đo lường bộ nhớ đỉnh `tracemalloc`.

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

**Purpose**: Tách phương thức nội bộ `_collect_used_pua_codepoints` trong `MarkdownImporter` làm nền tảng cho kiểm thử trực tiếp và đo lường bộ nhớ

**⚠️ CRITICAL**: Must be completed before User Story 1 tests and integration

- [x] T002 Implement `_collect_used_pua_codepoints` helper method with early exit in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundational helper method extracted - user story implementation and testing can begin

---

## Phase 3: User Story 1 - Đo lường trực tiếp và kiểm chứng số lượng phần tử tập hợp PUA (Priority: P1) 🎯 MVP

**Goal**: Cung cấp các bài kiểm thử khẳng định trực tiếp kích thước tập hợp `used_cps` (không chứa ký tự ngoài dải PUA) và đo lường bộ nhớ đỉnh bằng `tracemalloc` ($\le 50\text{KB}$) khi xử lý văn bản đa ngữ lớn chứa ký tự va chạm.

**Independent Test**: Gọi trực tiếp `MarkdownImporter._collect_used_pua_codepoints` với văn bản 10.000 ký tự chữ Hán/Nôm và `\ue000`, khẳng định tập hợp trả về có đúng 1 phần tử `{0xE000}`; chạy kiểm thử `tracemalloc` xác nhận mức tăng bộ nhớ đỉnh $\le 50\text{KB}$.

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Write unit test `test_pua_codepoint_collection_direct_and_bounded` verifying exact set elements and boundaries in `tests/test_markdown_math_block_isolation.py`
- [x] T004 [P] [US1] Write unit test `test_pua_memory_allocation_bounded_tracemalloc` with controlled `try...finally` block asserting peak memory <= 50KB in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T005 [US1] Update `MarkdownImporter._choose_fake_close_placeholder` to use `_collect_used_pua_codepoints` and handle exhaustion check in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and provably bounded in both set element count and peak traced memory.

---

## Phase 4: User Story 2 - Kịch bản thực nghiệm benchmark độc lập có thể tái lập (Priority: P2)

**Goal**: Xây dựng kịch bản dòng lệnh độc lập `scripts/benchmark_pua_memory.py` sử dụng thư viện chuẩn của Python để đo đạc, so sánh định lượng cả 3 phương án và tái lập các con số hiệu năng trong tài liệu.

**Independent Test**: Chạy `python scripts/benchmark_pua_memory.py` và xác nhận bảng số liệu hiển thị đầy đủ thông tin môi trường (Python, OS, CPU), kích thước bộ nhớ đỉnh và tỷ lệ tăng tốc của `finditer` so với `set(text)` và `findall`.

### Implementation for User Story 2

- [x] T006 [US2] Create standalone benchmark script with environment auto-detection and 3-way method comparison in `scripts/benchmark_pua_memory.py`
- [x] T007 [US2] Add adversarial stress test scenario (100,000 repeated PUA characters) demonstrating memory reduction of `finditer` vs `findall` in `scripts/benchmark_pua_memory.py`

**Checkpoint**: At this point, any external reviewer can independently reproduce all benchmark figures with a single command.

---

## Phase 5: User Story 3 - Chuẩn hóa tài liệu thực nghiệm và phân định đặc tính kỹ thuật (Priority: P3)

**Goal**: Hoàn thiện docstring, cập nhật tài liệu thiết kế phân định rõ ràng giữa `finditer` và `findall`, cung cấp hướng dẫn chạy benchmark tái lập.

**Independent Test**: Rà soát docstrings và các tài liệu trong `specs/065-pua-verification-reproducibility/`, xác nhận hướng dẫn tái lập rõ ràng và phân biệt chính xác đặc tính bộ nhớ.

### Implementation for User Story 3

- [x] T008 [P] [US3] Update docstrings for `_collect_used_pua_codepoints` and verify documentation consistency across `specs/065-pua-verification-reproducibility/`

**Checkpoint**: All documentation and code comments accurately reflect actual algorithmic behavior and reproducibility steps.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full regression testing, code cleanup, linting, formatting, and Pyodide Web Client verification

- [x] T009 [P] Run full test suite regression verification via `pytest tests/test_markdown_math_block_isolation.py tests/test_importer_markdown.py`
- [x] T010 [P] Code cleanup and style verification with `ruff check chuviettay tests scripts`
- [x] T011 Execute `python scripts/benchmark_pua_memory.py` verification run and Pyodide Golden Master test via `node scripts/test_golden_pyodide.mjs`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 - BLOCKS User Story 1
- **User Stories (Phase 3+)**:
  - **US1 (Phase 3)**: Depends on Phase 2 - Delivers direct element count and tracemalloc MVP
  - **US2 (Phase 4)**: Can proceed after US1 completion
  - **US3 (Phase 5)**: Can proceed in parallel with US2
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Core memory verification and unit testing
- **User Story 2 (P2)**: Standalone benchmark script for external reproducibility
- **User Story 3 (P3)**: Documentation synchronization across US1 & US2

### Parallel Opportunities

- Within Phase 3 (US1): `T003` (element count test) and `T004` (tracemalloc test) can run in parallel
- Within Phase 5 (US3): `T008` (docstrings) can run in parallel with `T006`/`T007` (script development)
- Within Phase 6: `T009`, `T010`, `T011` can be dispatched independently

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: Foundational (`T002`)
3. Complete Phase 3: User Story 1 (`T003`, `T004`, `T005`)
4. **STOP and VALIDATE**: Verify direct set size and peak traced memory on multilingual input
5. Deliver MVP direct memory testability

### Incremental Delivery

1. Setup + Foundational (`T001` - `T002`)
2. US1: Direct element collection & tracemalloc (`T003` - `T005`) $\to$ Validate MVP
3. US2: Standalone benchmark script (`T006` - `T007`) $\to$ Validate Reproducibility
4. US3: Docstring and specification synchronization (`T008`)
5. Polish: Regression, Linting, Benchmark Execution, and Pyodide Check (`T009` - `T011`)
