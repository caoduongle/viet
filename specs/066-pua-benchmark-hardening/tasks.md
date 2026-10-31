---
description: "Task list for feature 066-pua-benchmark-hardening"
---

# Tasks: Chuẩn hóa script benchmark PUA và tích hợp CI smoke test

**Input**: Design documents from `/specs/066-pua-benchmark-hardening/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/benchmark-hardening-contract.md`, `research.md`, `quickstart.md`)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Bao gồm bài kiểm thử tự động smoke test cho script benchmark chạy trong pytest và bước kiểm tra tự động trên GitHub Actions CI.

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

## Phase 2: User Story 1 - Chuẩn hóa tính nhất quán của tham số và tính chính xác của dữ liệu benchmark (Priority: P1) 🎯 MVP

**Goal**: Cải tiến `scripts/benchmark_pua_memory.py` để tham số `--rounds` áp dụng nhất quán cho cả kịch bản chính và đối kháng; sinh dữ liệu mẫu thực sự đa ngữ gồm 4 hệ chữ Unicode (CJK, Cyrillic, Greek, Math) và tính toán kích thước byte UTF-8 thực tế.

**Independent Test**: Chạy `python scripts/benchmark_pua_memory.py --rounds 2 --json`: xác nhận cả kịch bản chính và đối kháng đều đo đúng 2 vòng lặp; kích thước byte được tính bằng `len(text.encode("utf-8"))` (~1.48 MB) và mô tả hiển thị đầy đủ 4 hệ chữ.

### Implementation for User Story 1

- [x] T002 [US1] Upgrade `make_multilingual_text` to combine CJK, Cyrillic, Greek, Math operators and PUA in `scripts/benchmark_pua_memory.py`
- [x] T003 [US1] Calculate exact dynamic UTF-8 byte length and add `character_families` metadata to `dataset_main` in `scripts/benchmark_pua_memory.py`
- [x] T004 [US1] Apply `rounds` parameter consistently across both main benchmark and adversarial stress test in `scripts/benchmark_pua_memory.py`

**Checkpoint**: At this point, User Story 1 is complete and the benchmark script is statistically consistent and descriptive.

---

## Phase 3: User Story 2 - Kiểm thử tự động Smoke Test cho script benchmark (Priority: P2)

**Goal**: Tạo bài kiểm thử tự động trong pytest để kiểm chứng khả năng chạy thành công từ đầu đến cuối của script benchmark với `--rounds 1 --json`, xác thực tính hợp lệ của cấu trúc JSON đầu ra mà không phụ thuộc vào ngưỡng thời gian tuyệt đối.

**Independent Test**: Chạy `pytest tests/test_benchmark_pua_smoke.py`: xác nhận bài test vượt qua thành công trong < 3 giây với mã thoát 0 và cấu trúc JSON chuẩn.

### Tests for User Story 2

- [x] T005 [P] [US2] Implement `test_benchmark_pua_script_smoke_execution` running benchmark CLI with `--rounds 1 --json` via subprocess in `tests/test_benchmark_pua_smoke.py`
- [x] T006 [US2] Assert structural integrity of JSON schema (keys `environment`, `dataset_main`, `results_main`, `dataset_stress`, `results_stress`) in `tests/test_benchmark_pua_smoke.py`

**Checkpoint**: At this point, any breaking changes to the benchmark script CLI will immediately trigger a test failure in pytest.

---

## Phase 4: User Story 3 - Tích hợp Smoke Test vào Continuous Integration (CI) Workflow (Priority: P3)

**Goal**: Tích hợp bước kiểm tra nhanh `python scripts/benchmark_pua_memory.py --rounds 1 --json` vào các job kiểm thử Python trong GitHub Actions workflow.

**Independent Test**: Rà soát diff của `.github/workflows/ci.yml` và chạy mô phỏng lệnh smoke test trên máy cục bộ với cùng tham số của CI.

### Implementation for User Story 3

- [x] T007 [P] [US3] Add `Run PUA Benchmark Smoke Test` step to `test-core` and `test-python-314` jobs in `.github/workflows/ci.yml`

**Checkpoint**: All commits and pull requests will now automatically verify that the benchmark script executes cleanly from start to finish.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Full regression testing, code cleanup, linting, formatting, and Pyodide Web Client verification

- [x] T008 [P] Run full test regression verification via `pytest tests/test_benchmark_pua_smoke.py tests/test_markdown_math_block_isolation.py`
- [x] T009 [P] Code cleanup and style verification with `ruff check chuviettay tests scripts`
- [x] T010 Execute verification run `python scripts/benchmark_pua_memory.py --rounds 2` and Pyodide Golden Master test via `node scripts/test_golden_pyodide.mjs`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Core benchmark script refactor - blocks User Story 2 & 3
- **User Story 2 (Phase 3)**: Depends on User Story 1 completion
- **User Story 3 (Phase 4)**: Can proceed after User Story 2
- **Polish (Phase 5)**: Depends on all user stories being complete

### Parallel Opportunities

- Within Phase 3 (US2): `T005` can be developed in parallel with script validation
- Within Phase 4 (US3): `T007` (CI workflow update) can run independently
- Within Phase 5: `T008`, `T009`, `T010` can be dispatched independently

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`T001`)
2. Complete Phase 2: User Story 1 (`T002`, `T003`, `T004`)
3. **STOP and VALIDATE**: Verify consistent rounds and dynamic byte calculation on CLI
4. Deliver MVP data precision

### Incremental Delivery

1. Setup (`T001`)
2. US1: Benchmark script precision & rounds consistency (`T002` - `T004`) $\to$ Validate MVP
3. US2: Automated smoke test in pytest (`T005` - `T006`) $\to$ Validate Local Automation
4. US3: CI workflow integration (`T007`) $\to$ Validate CI Automation
5. Polish: Full regression, Lint, and Pyodide Check (`T008` - `T010`)
