---
description: "Task list for feature 060-blockquote-math-state-hardening"
---

# Tasks: Theo dõi độ sâu trích dẫn cho trạng thái khối toán nhiều dòng và gia cố kiểm thử bảo toàn đầu ra Markdown

**Input**: Design documents from `/specs/060-blockquote-math-state-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/blockquote-math-and-test-invariants-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Feature specification yêu cầu kiểm thử TDD cho các trường hợp thoát blockquote của display math và kiểm thử bất biến bảo toàn nội dung mã.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent test functions, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification and initial state confirmation

- [x] T001 Baseline verification of existing test suite and code linting in `tests/test_markdown_math_block_isolation.py` and `chuviettay/importer/markdown_importer.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core state machine infrastructure in `_isolate_display_math_blocks()` required for blockquote math state tracking

**⚠️ CRITICAL**: Must be in place before implementing specific story behavior

- [x] T002 Initialize `math_bq_depth: int = 0` state variable and state reset invariants alongside `in_display_math` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Thoát trạng thái khối toán nhiều dòng khi kết thúc ngữ cảnh trích dẫn (Priority: P1) 🎯 MVP

**Goal**: Theo dõi độ sâu trích dẫn `math_bq_depth` cho khối toán hiển thị nhiều dòng `in_display_math`, tự động thoát trạng thái khi `bq_depth < math_bq_depth` (hoặc gặp dòng trống không có `>`), ngăn chặn *lazy continuation* của CommonMark và cho phép các dòng tiếp theo (như `Ngoài trích dẫn:$$y=2$$`) được tách thành `MathBlock` hợp lệ.

**Independent Test**: Nhập tài liệu có `> $$\n> x = 1\nNgoài trích dẫn:$$y=2$$\nĐoạn văn tiếp theo` và `>> $$\n>> x = 1\n> Trong trích dẫn cấp 1:$$y=2$$`; xác nhận cả ở `_isolate_display_math_blocks()` lẫn `import_text()` rằng `MathBlock("y=2")` được tách riêng biệt và đoạn văn tiếp theo được giữ nguyên.

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Add unit and integration tests for multiline display math blockquote exit on dedent (`test_display_math_in_blockquote_exits_on_dedent` verifying both `_isolate_display_math_blocks` and `import_text` with root exit and `>>` to `>` dedent) in `tests/test_markdown_math_block_isolation.py`
- [x] T004 [P] [US1] Add unit tests for blank line exit from blockquote display math and valid close only at matching `math_bq_depth` (`test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close`) in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T005 [US1] Record `math_bq_depth = bq_depth` when opening multiline display math block in `MarkdownImporter._isolate_display_math_blocks()` in `chuviettay/importer/markdown_importer.py`
- [x] T006 [US1] Implement blockquote exit check (`if in_display_math and bq_depth < math_bq_depth`) before blank/fence branches, resetting math state, inserting separator line to prevent lazy continuation, and allowing line reprocessing in `chuviettay/importer/markdown_importer.py`
- [x] T007 [US1] Implement matching depth closing rule (`bq_depth == math_bq_depth` and `stripped_rest` ends with `$$`) and blockquote blank line separator refinement in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Xác minh chặt chẽ bất biến bảo toàn nội dung và đầu ra công thức trong kiểm thử (Priority: P2)

**Goal**: Siết chặt các bài kiểm thử đối kháng và kiểm thử hồi quy để xác nhận trực tiếp bất biến bảo toàn từng ký tự của khối mã (code fence, indented code block) qua toàn bộ pipeline tiền xử lý, kiểm tra đầy đủ danh sách `MathBlock` ngoài vùng mã (bao gồm cả `x=2` và `y=3`), và bổ sung khẳng định bất biến nội dung cụ thể trong bài đo hiệu năng tuyến tính.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py` và xác nhận cả hai công thức `x=2` và `y=3` đều có mặt trong `math_blocks`, mọi ký tự trong code block được giữ nguyên 100%, và bài đo hiệu năng $N, 2N, 4N$ thỏa mãn tỷ lệ thời gian $\le 6.0$ kèm các khẳng định nội dung đầu ra.

### Tests & Invariants for User Story 2

- [x] T008 [P] [US2] Update `test_code_fence_in_blockquote_auto_closes_on_dedent` to assert both `x=2` and `y=3` in `[b.latex for b in math_blocks]` in `tests/test_markdown_math_block_isolation.py`
- [x] T009 [P] [US2] Add test `test_pipeline_code_preservation_and_outside_math_invariants` asserting character-for-character preservation of fenced and indented code blocks across preprocessing pipeline with outside math extraction in `tests/test_markdown_math_block_isolation.py`
- [x] T010 [US2] Add concrete output invariant assertions for `out_n`, `out_2n`, and `out_4n` (counting preserved code blocks and transformed math markers) to `test_adversarial_complexity_multi_length_backticks_and_long_lines` in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: At this point, User Stories 1 AND 2 are both verified with complete automated tests.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verification across all repository quality gates and regression baselines

- [x] T011 [P] Run static analysis and lint checks with `ruff check chuviettay tests scripts` in `chuviettay/importer/markdown_importer.py` and `tests/test_markdown_math_block_isolation.py`
- [x] T012 Run full Python test suite with `pytest`
- [x] T013 [P] Run Web Client unit and browser tests with `npm run test:unit` and `npm run test:browser`
- [x] T014 Run Golden Master Pyodide regression verification (8/8 SHA-256 match) with `node scripts/test_golden_pyodide.mjs`
- [x] T015 Run Playwright E2E test suite with `npm run test:e2e`
- [x] T016 Execute Quickstart validation scenario per `specs/060-blockquote-math-state-hardening/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
  - User Story 1 (P1): Core state machine fix for blockquote math exit
  - User Story 2 (P2): Strict test invariants building on US1 fixes
- **Polish (Phase 5)**: Depends on completion of User Stories 1 and 2

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on User Story 1 (T005-T007) so that math extraction across dedents operates correctly

### Within Each User Story

- TDD Tests (T003, T004) MUST be written first and verify failure before implementation
- Implementation tasks (T005, T006, T007) executed in sequence
- Checkpoint validation before moving to next priority

### Parallel Opportunities

- Within Phase 3: T003 and T004 can be drafted in parallel
- Within Phase 4: T008 and T009 can be written in parallel
- Within Phase 5: T011 and T013 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch test drafting for User Story 1 together:
Task: "T003 [P] [US1] Add unit and integration tests for multiline display math blockquote exit on dedent in tests/test_markdown_math_block_isolation.py"
Task: "T004 [P] [US1] Add unit tests for blank line exit from blockquote display math in tests/test_markdown_math_block_isolation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: User Story 1 (T003 -> T007)
4. **STOP and VALIDATE**: Run `pytest tests/test_markdown_math_block_isolation.py -k blockquote` independently
5. Verify MVP criteria met

### Incremental Delivery

1. Phase 1 + Phase 2 -> Foundation ready
2. Phase 3 (US1) -> Fix `in_display_math` blockquote depth tracking (MVP)
3. Phase 4 (US2) -> Harden test suite with strict character-for-character preservation and content invariants
4. Phase 5 (Polish) -> 100% CI compliance (Ruff, pytest, Web unit, Pyodide golden, E2E)
