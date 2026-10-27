---
description: "Task list for feature 062-fake-close-placeholder-restore"
---

# Tasks: Khôi phục dấu đóng giả bằng dấu giữ chỗ riêng, bảo toàn nguyên vẹn công thức LaTeX

**Input**: Design documents from `/specs/062-fake-close-placeholder-restore/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/fake-close-placeholder-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Feature specification yêu cầu phương pháp TDD cho việc kiểm chứng bảo toàn công thức LaTeX có `\$\$` hợp lệ và siết chặt các phép so sánh bằng tuyệt đối (`==`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent test functions, no incomplete dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification of current repository state and test suite

- [x] T001 Baseline verification of existing test suite and code quality via `pytest tests/test_markdown_math_block_isolation.py` and `ruff check chuviettay tests scripts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core PUA placeholder selection and token tree restoration infrastructure in `MarkdownImporter`

**⚠️ CRITICAL**: Must be established before User Story 1 and User Story 2 implementation

- [x] T002 Implement `_FAKE_CLOSE_PUA_START`, `_FAKE_CLOSE_PUA_END` and `@classmethod _choose_fake_close_placeholder(cls, text: str) -> str | None` in `chuviettay/importer/markdown_importer.py`
- [x] T003 Implement `@classmethod _restore_fake_close_placeholder(cls, tokens: list[Any], placeholder: str | None) -> None` with recursive traversal replacing placeholder in `token.content` and `token.info` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: Foundational helpers ready - user story implementation can begin

---

## Phase 3: User Story 1 - Công thức LaTeX chứa ký hiệu đô-la được escape được bảo toàn nguyên vẹn (Priority: P1) 🎯 MVP

**Goal**: Bảo toàn 100% nguyên vẹn từng ký tự công thức LaTeX hợp lệ có chứa cặp ký hiệu đô-la escape (ví dụ `$$\text{\$\$}$$`), loại bỏ hoàn toàn phép thay thế toàn cục `replace(r"\$\$", "$$")` làm thay đổi sai lệch nội dung công thức người dùng.

**Independent Test**: Nhập `$$\text{\$\$}$$`, `$$\n\text{\$\$}\n$$`, `> $$\n> \text{\$\$}\n> $$`, `$$\$ + \text{\$\$\$\$}$$` và `$$\n\$ + \$\$\$\$\n$$`; xác nhận nội dung `MathBlock.latex` trùng khớp từng ký tự với đầu vào gốc.

### Tests for User Story 1 (TDD - Write First) 🧪

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Write failing regression tests for valid escaped dollar formulas (T-ESC1 `$$\text{\$\$}$$`, T-ESC2 multiline, T-ESC3 blockquote multiline, T-MULTI single-line and multiline, and T-COMBO) in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 1

- [x] T005 [US1] Remove global `.replace(r"\$\$", "$$")` on `MathBlock` in `MarkdownImporter._parse_blocks()` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Story 1 is fully functional and all valid `\$\$` math formulas are preserved without data corruption.

---

## Phase 4: User Story 2 - Dấu đóng giả ở trích dẫn lồng nhau vẫn được bảo vệ và khôi phục đúng (Priority: P1)

**Goal**: Dấu đóng giả ở độ sâu trích dẫn lồng nhau (`>> $$` trong khối toán mở ở `> $$`) được bảo vệ bằng ký tự PUA giữ chỗ riêng không thể va chạm với dữ liệu người dùng, và được khôi phục về `$$` chính xác trên toàn cây token sau khi phân tích cú pháp.

**Independent Test**: Nhập `> $$\n> x = 1\n>> $$\n> x = 2\n> $$` và xác nhận sinh đúng 1 `MathBlock` chứa cả `x = 1`, `>> $$`, `x = 2`; kiểm chứng trường hợp văn bản chứa sẵn ký tự `\ue000` (tự động chọn `\ue001`) và ca khối toán không đóng không làm rò rỉ ký tự PUA ra ngoài.

### Tests for User Story 2 (TDD - Write First) 🧪

- [x] T006 [P] [US2] Write tests for PUA placeholder collision avoidance (T-COLL), unclosed math block token safety without PUA leak (T-LEAK), and explicit fallback when `fake_close_placeholder=None` in `tests/test_markdown_math_block_isolation.py`

### Implementation for User Story 2

- [x] T007 [US2] Update `MarkdownImporter._isolate_display_math_blocks()` to accept `fake_close_placeholder: str | None = ""` and replace trailing `$$` on nested fake-close lines (`bq_depth > math_bq_depth`) with placeholder instead of `r"\$\$"` in `chuviettay/importer/markdown_importer.py`
- [x] T008 [US2] Wire placeholder selection, passing to `_isolate_display_math_blocks()`, and token tree restoration via `_restore_fake_close_placeholder()` into `MarkdownImporter.import_text()` in `chuviettay/importer/markdown_importer.py`

**Checkpoint**: At this point, User Stories 1 AND 2 work together in harmony: nested fake close delimiters do not prematurely close math blocks and do not alter valid `\$\$` LaTeX code.

---

## Phase 5: User Story 3 - Kiểm thử so sánh chính xác toàn bộ chuỗi sau cô lập và nội dung khối công thức (Priority: P3)

**Goal**: Siết chặt các khẳng định kiểm thử của ca trích dẫn lồng nhau từ phép kiểm tra hậu tố sang so sánh bằng tuyệt đối (`==`) trên toàn bộ chuỗi đầu ra của `_isolate_display_math_blocks()` và nội dung `MathBlock.latex` sau khi qua `import_text()`.

**Independent Test**: Chạy `pytest tests/test_markdown_math_block_isolation.py -k test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close` và xác nhận tất cả các phép so sánh `==` cho T-ISO, T-NEST, T-PUNCT đều vượt qua.

### Implementation for User Story 3

- [x] T009 [P] [US3] Update `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close()` with strict exact equality assertions (`==`) on `_isolate_display_math_blocks()` output (T-ISO) and `import_text()` `MathBlock.latex` (T-NEST, T-PUNCT) in `tests/test_markdown_math_block_isolation.py`

**Checkpoint**: All three user stories are implemented, verified with strict assertions, and have 0 regressions.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification across all repository quality gates and regression baselines

- [x] T010 [P] Run static analysis and lint checks with `ruff check chuviettay tests scripts` in `chuviettay/importer/markdown_importer.py` and `tests/test_markdown_math_block_isolation.py`
- [x] T011 Run full Python test suite with `pytest`
- [x] T012 [P] Run Web Client unit and browser tests with `npm run test:unit` and `npm run test:browser`
- [x] T013 Rebuild static web client with `python scripts/build_web.py` and verify Golden Master Pyodide regression (8/8 SHA-256 match) with `node scripts/test_golden_pyodide.mjs`
- [x] T014 Run Playwright E2E test suite with `npm run test:e2e`
- [x] T015 Execute Quickstart validation scenarios per `specs/062-fake-close-placeholder-restore/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Stories 1 and 2
- **User Stories (Phase 3+)**:
  - User Story 1 (P1): Removes `.replace(r"\$\$", "$$")` and adds escaped dollar formula preservation tests
  - User Story 2 (P1): Replaces `\$\$` escaping with PUA placeholder mechanism in isolation and token restore
  - User Story 3 (P3): Strict exact equality assertions on isolation string and AST
- **Polish (Phase 6)**: Depends on completion of all user stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P1)**: Depends on Foundational (Phase 2) and pairs with US1 to replace the `r"\$\$"` mechanism
- **User Story 3 (P3)**: Depends on US2 completion (exact expected isolation string uses `\ue000`)

### Parallel Opportunities

- T004 [US1], T006 [US2], and T009 [US3] define independent test cases in `tests/test_markdown_math_block_isolation.py`
- T010 (Ruff) and T012 (Web tests) can run in parallel during Polish Phase 6

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002, T003)
3. Complete Phase 3: User Story 1 (T004 -> T005)
4. **STOP and VALIDATE**: Confirm `$$\text{\$\$}$$` is no longer mutated to `\text{$$}`

### Incremental Delivery

1. Phase 1 + Phase 2 -> Foundation ready (PUA helper and restore methods)
2. Phase 3 (US1) -> Fix LaTeX `\$\$` preservation (MVP)
3. Phase 4 (US2) -> Switch fake close escaping from `r"\$\$"` to dynamic PUA placeholder
4. Phase 5 (US3) -> Upgrade test assertions to strict exact equality (`==`)
5. Phase 6 (Polish) -> 100% Quality Gates (Ruff, Pytest, Web unit/browser, Golden Master 8/8, E2E)
