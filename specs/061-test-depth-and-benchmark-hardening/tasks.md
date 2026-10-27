---
description: "Task list for feature 061-test-depth-and-benchmark-hardening"
---

# Tasks: Gia cố kiểm thử đóng khối toán theo độ sâu và bổ sung bất biến công thức trong benchmark

**Input**: Design documents from `/specs/061-test-depth-and-benchmark-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/test-depth-and-benchmark-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Feature specification yêu cầu bổ sung các phép kiểm thử nghiêm ngặt đối chiếu AST và bất biến công thức đầu ra.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent test functions, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification of current repository state

- [x] T001 Baseline verification of existing test suite and code linting in `tests/test_markdown_math_block_isolation.py` and `chuviettay/importer/markdown_importer.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pipeline escaping & unescaping infrastructure for fake close markers at deeper blockquote depths

**⚠️ CRITICAL**: Must be established before User Story 1 implementation

- [x] T002 Add fake close marker protection handling structure in `MarkdownImporter._isolate_display_math_blocks()` and token unescaping in `MarkdownImporter._parse_blocks()` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Xác minh chặt chẽ quy tắc đóng khối toán đúng độ sâu trích dẫn (Priority: P1) 🎯 MVP

**Goal**: Bảo vệ khối toán trích dẫn trước dấu đóng giả ở độ sâu lồng nhau (`>> $$`), đảm bảo `import_text()` không đóng sớm khối toán và siết chặt bài kiểm thử `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close()` với các assertion đầy đủ về cả chuỗi cô lập lẫn AST `MathBlock`.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` và xác nhận cả `_isolate_display_math_blocks()` và `import_text()` chỉ sinh đúng 1 khối `MathBlock` duy nhất chứa đầy đủ cả `x = 1` lẫn `x = 2`.

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Write strict assertions for nested fake close marker `>> $$` on both `_isolate_display_math_blocks` and `import_text` (`len(math_blocks) == 1`, `"x = 1"` and `"x = 2"` in `latex`) in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T004 [US1] Implement escaping of fake close `$$` to `\$\$` when `bq_depth > math_bq_depth` in `MarkdownImporter._isolate_display_math_blocks()` in `chuviettay/importer/markdown_importer.py`
- [x] T005 [US1] Implement unescaping of `\$\$` to `$$` in `MarkdownImporter._parse_blocks()` for `MathBlock` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Xác nhận trực tiếp việc chuyển đổi công thức và tính toàn vẹn của mã trong benchmark (Priority: P2)

**Goal**: Bổ sung các bất biến kiểm tra trực tiếp số lượng xuất hiện của công thức toán học hiển thị hợp lệ sau tiền xử lý (`$$display_formula$$` và `$$x=1$$`) trên cả 3 kích thước $N, 2N, 4N$ trong bài đo hiệu năng đối kháng.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k test_adversarial_complexity_multi_length_backticks_and_long_lines` và xác nhận 100% các khẳng định bất biến công thức và mã nguồn vượt qua đồng thời tỷ lệ $T(4N)/T(N) \le 6.0$.

### Implementation for User Story 2

- [x] T006 [US2] Add output formula invariants for `$$display_formula$$` and `$$x=1$$` on sizes $N, 2N, 4N$ to `test_adversarial_complexity_multi_length_backticks_and_long_lines()` in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: At this point, User Stories 1 AND 2 are verified.

---

## Phase 5: User Story 3 - Bảo toàn trạng thái Garbage Collector ban đầu trong các bài benchmark (Priority: P3)

**Goal**: Lưu và khôi phục đúng trạng thái ban đầu của Garbage Collector trong các bài benchmark để bảo vệ tính độc lập của môi trường kiểm thử.

**Independent Test**: Chạy bài benchmark khi GC tắt, xác nhận sau khi chạy GC vẫn tắt; chạy khi GC bật, xác nhận sau khi chạy GC vẫn bật.

### Implementation for User Story 3

- [x] T007 [P] [US3] Capture initial GC state with `gc.isenabled()` and conditionally restore in `finally` in `test_adversarial_complexity_unclosed_backticks_and_blockquotes()` in `tests/test_markdown_math_block_isolation.py`
- [x] T008 [P] [US3] Capture initial GC state with `gc.isenabled()` and conditionally restore in `finally` in `test_adversarial_complexity_multi_length_backticks_and_long_lines()` in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: All three user stories are implemented and verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification across all repository quality gates and regression baselines

- [x] T009 [P] Run static analysis and lint checks with `ruff check chuviettay tests scripts` in `chuviettay/importer/markdown_importer.py` and `tests/test_markdown_math_block_isolation.py`
- [x] T010 Run full Python test suite with `pytest`
- [x] T011 [P] Run Web Client unit and browser tests with `npm run test:unit` and `npm run test:browser`
- [x] T012 Run Golden Master Pyodide regression verification (8/8 SHA-256 match) with `node scripts/test_golden_pyodide.mjs`
- [x] T013 Run Playwright E2E test suite with `npm run test:e2e`
- [x] T014 Execute Quickstart validation scenarios per `specs/061-test-depth-and-benchmark-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Story 1
- **User Stories (Phase 3+)**:
  - User Story 1 (P1): Core escaping/unescaping and strict nested close test assertions
  - User Story 2 (P2): Formula invariants in multi-length benchmark
  - User Story 3 (P3): GC state hygiene in both benchmark tests
- **Polish (Phase 6)**: Depends on completion of all user stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Independent from US1, can proceed in sequence
- **User Story 3 (P3)**: Touches benchmark tests alongside US2

### Parallel Opportunities

- T007 and T008 can be applied in parallel across the two benchmark functions
- T009 (Ruff) and T011 (NPM tests) can run in parallel in Phase 6

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: User Story 1 (T003 -> T005)
4. **STOP and VALIDATE**: Test User Story 1 independently with `pytest tests/test_markdown_math_block_isolation.py -k test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close`

### Incremental Delivery

1. Phase 1 + Phase 2 -> Foundation ready
2. Phase 3 (US1) -> Fix nested close escaping and harden test assertions (MVP)
3. Phase 4 (US2) -> Add benchmark formula output invariants
4. Phase 5 (US3) -> GC state hygiene
5. Phase 6 (Polish) -> 100% Quality Gates (Ruff, Pytest, Web unit/browser, Golden Master, E2E)
