# Tasks: Data Integrity Safety Net & Core Persistence Hardening (P0)

**Input**: Design artifacts from `specs/018-data-integrity-safety/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`)
**Branch**: `fix/phase0-data-integrity`
**Target Commit Baseline**: `e517636`
**Verification Script**: `repro_viet_baseline.py`

---

## Phase 1: Setup & Safety Net — Golden Master Real Path (Step 0)

**Purpose**: Establish deterministic byte-level baseline verification on the real production layout engine (`AppController.write_text` / `DocumentLayoutEngine`) before modifying any application code.

- [ ] T001 Implement real-path golden master regression test suite in tests/test_golden_master_real_path.py covering 4 standard cases (co_ban, tuy_chon, nhieu_trang, strict_case) with decompressed XML SHA-256 assertions
- [ ] T002 Implement extended real-path golden master cases in tests/test_golden_master_real_path.py for single-letter assembly, inline/block math, markdown tables, and markdown lists
- [ ] T003 Execute real-path golden master tests against unmodified commit e517636 and pin reference SHA-256 digests in tests/test_golden_master_real_path.py
- [ ] T004 Run ruff check . and verify existing tests/test_golden_master.py and new tests/test_golden_master_real_path.py pass cleanly
- [ ] T005 Commit Step 0 safety net with message 'test: golden-master cho duong that [Step0]'

**Checkpoint**: Production real-path golden master established and green. Any regression in later steps will immediately fail this test.

---

## Phase 2: Foundational — Environment Decoupling (Q1)

**Purpose**: Eliminate false-positive test failures caused by LibreOffice without Word COM and long-running benchmark tests under code coverage.

- [ ] T006 Update Word COM availability guard from is_available() to is_word_available() in tests/test_docx_fidelity.py
- [ ] T007 Update Word COM availability guard from is_available() to is_word_available() in tests/test_cli_format.py
- [ ] T008 Register benchmark marker in pytest.ini
- [ ] T009 Decorate test_large_bank_persistence_benchmark_5000_samples with @pytest.mark.benchmark in tests/test_bank.py
- [ ] T010 Verify pytest tests/test_docx_fidelity.py tests/test_cli_format.py and full test suite pass cleanly
- [ ] T011 Commit Q1 decoupling with message 'test(ci): bảo vệ test khỏi môi trường thiếu word và coverage benchmark [Q1]'

**Checkpoint**: Test suite runs reliably across environments with LibreOffice and under test coverage.

---

## Phase 3: User Story 1 (Part 1) — Symbol Tombstone Restoration (D2)

**Goal**: Ensure deleting and subsequently re-teaching a mathematical symbol via `add_symbol_sample` clears tombstones and preserves the symbol across multi-process merges.

**Independent Test**: `python repro_viet_baseline.py --repo . --only D2` transitions from `BUG` to `ĐÃ SỬA`.

### Tests for D2
- [ ] T012 [US1] Write failing regression test in tests/test_bank.py asserting that re-adding a deleted symbol via add_symbol_sample clears tombstones and preserves samples after merge (verify RED)

### Implementation for D2
- [ ] T013 [US1] Update add_symbol_sample in chuviettay/model/bank.py to clear tombstones, discard keys from _deleted_words, and record additions into _readded_words
- [ ] T014 [US1] Add dedup support to add_symbol_sample in chuviettay/model/bank.py using sample_signature
- [ ] T015 [US1] Run regression test in tests/test_bank.py and verify GREEN
- [ ] T016 [US1] Run python repro_viet_baseline.py --repo . --only D2 and confirm ĐÃ SỬA
- [ ] T017 [US1] Run ruff check . and verify clean
- [ ] T018 [US1] Commit D2 fix with message 'fix(bank): xoá ký hiệu rồi dạy lại không bị mất sau khi hợp nhất [D2]'

**Checkpoint**: D2 bug resolved and verified with automated regression test and baseline script.

---

## Phase 4: User Story 2 — Resilient Concurrent Persistence (D5)

**Goal**: Prevent `RuntimeError: dictionary changed size during iteration` during background timer debounce saves by adopting single-pass JSON serialization, RLock synchronization, mutation sequence tracking, and dirty-flag error recovery.

**Independent Test**: `python repro_viet_baseline.py --repo . --only D5` transitions from `BUG` to `ĐÃ SỬA`, and heavy concurrent stress test passes without errors.

### Tests for D5
- [ ] T019 [US2] Write concurrent stress test in tests/test_bank.py simulating rapid sample additions while background timer saves execute concurrently on 20,000+ sample bank (verify RED)

### Implementation for D5
- [ ] T020 [US2] Add threading.RLock and _mutation_seq counter to Bank in chuviettay/model/bank.py
- [ ] T021 [US2] Wrap bank mutating methods (add_sample, drop, clear, etc.) with self._lock and increment self._mutation_seq in chuviettay/model/bank.py
- [ ] T022 [US2] Replace streaming json.dump with single-pass json.dumps in memory under self._lock, followed by compresslevel=1 write to tempfile in chuviettay/model/bank.py
- [ ] T023 [US2] Protect dirty flag and pending deletion sets in Bank.save using _mutation_seq and snapshot sets so modifications during disk I/O are never lost in chuviettay/model/bank.py
- [ ] T024 [US2] Update _on_debounce_save in chuviettay/controller/app_controller.py with try/except logging and dirty state preservation
- [ ] T025 [US2] Update mock patch in test_save_bi_ngat_giua_chung_thi_kho_cu_con_nguyen_va_khong_de_lai_file_tam in tests/test_bank.py to target json.dumps while preserving atomic failure assertion
- [ ] T026 [US2] Run tests/test_bank.py concurrent stress test and verify GREEN
- [ ] T027 [US2] Run python repro_viet_baseline.py --repo . --only D5 and confirm ĐÃ SỬA
- [ ] T028 [US2] Run ruff check . and verify clean
- [ ] T029 [US2] Commit D5 fix with message 'fix(bank): chống đua luồng khi lưu hoãn và tăng tốc ghi kho [D5]'

**Checkpoint**: Bank persistence is fast (~5x faster), thread-safe, and free of dictionary iteration race conditions.

---

## Phase 5: User Story 4 — Missing Grid Protection & Option Control (D4)

**Goal**: Respect `missing_grid=False` during synthesis, add `--no-missing-grid` to CLI and GUI, and protect in-progress user handwriting in `_thieu.xopp` by generating sequential non-colliding filenames (`_thieu_2.xopp`).

**Independent Test**: `python repro_viet_baseline.py --repo . --only D4a D4b` transitions from `BUG` to `ĐÃ SỬA`.

### Tests for D4
- [ ] T030 [US4] Write failing regression test in tests/test_layout_semantic.py verifying missing_grid=False suppresses missing grid generation (verify RED)
- [ ] T031 [US4] Write failing regression test in tests/test_layout_semantic.py verifying existing _thieu.xopp containing user pen strokes is preserved and _thieu_2.xopp is generated (verify RED)
- [ ] T032 [US4] Write failing CLI test in tests/test_cli.py verifying --no-missing-grid flag is recognized and respected (verify RED)

### Implementation for D4
- [ ] T033 [US4] Implement has_user_handwriting helper in chuviettay/model/xopp.py checking for pen strokes with colors outside HW3_GUIDE_COLORS
- [ ] T034 [US4] Implement resolve_missing_grid_path in chuviettay/layout/engine.py to find first non-colliding filename when user handwriting exists
- [ ] T035 [US4] Update DocumentLayoutEngine in chuviettay/layout/engine.py to respect self.opts.missing_grid and use resolve_missing_grid_path
- [ ] T036 [US4] Add --no-missing-grid argument to write parser in chuviettay/cli.py and wire into WriteOptions
- [ ] T037 [US4] Add 'Tạo file chữ thiếu' checkbox bound to v_missing_grid in chuviettay/view/write_tab.py
- [ ] T038 [US4] Run regression tests in tests/test_layout_semantic.py and tests/test_cli.py and verify GREEN
- [ ] T039 [US4] Run python repro_viet_baseline.py --repo . --only D4a D4b and confirm ĐÃ SỬA
- [ ] T040 [US4] Run ruff check . and verify clean
- [ ] T041 [US4] Commit D4 fix with message 'fix(layout): tôn trọng cờ missing_grid và không ghi đè nét người dùng trong _thieu.xopp [D4]'

**Checkpoint**: User handwriting in missing grids is safely protected against accidental overwrite, and missing grid creation is fully configurable.

---

## Phase 6: User Story 3 — Idempotent Learning & Deduplication (D3)

**Goal**: Prevent duplicate sample ingestion when re-learning practice sheets by hashing uncompressed XML content and enforcing cell-level deduplication via `sample_signature`.

**Independent Test**: `python repro_viet_baseline.py --repo . --only D3` transitions from `BUG` to `ĐÃ SỬA`.

### Tests for D3
- [ ] T042 [US3] Write failing regression test in tests/test_learning.py verifying identical XML re-compressed with different gzip timestamp is skipped as duplicate (verify RED)
- [ ] T043 [US3] Write regression test in tests/test_learning.py verifying partial grid additions only add new cells while deduplicating existing cells (verify RED)

### Implementation for D3
- [ ] T044 [US3] Update learn_from_files in chuviettay/model/learning.py to hash decompressed XML content and check against learned_files
- [ ] T045 [US3] Update learn_from_files in chuviettay/model/learning.py to accept dedup: bool = True parameter (default True) and enforce cell deduplication
- [ ] T046 [US3] Audit tests in tests/test_learning.py and tests/test_controller.py that deliberately test batch aggregation of duplicate strokes and pass dedup=False with clear technical commentary
- [ ] T047 [US3] Run tests/test_learning.py and verify GREEN
- [ ] T048 [US3] Run python repro_viet_baseline.py --repo . --only D3 and confirm ĐÃ SỬA
- [ ] T049 [US3] Run ruff check . and verify clean
- [ ] T050 [US3] Commit D3 fix with message 'fix(learn): học mẫu tất định bằng hash XML và khử trùng từng ô [D3]'

**Checkpoint**: Practice grid learning is idempotent across archive compression timestamp variations and prevents duplicate sample pollution.

---

## Phase 7: User Story 1 (Part 2) — Qualified Tombstones & Schema v4 (D1)

**Goal**: Eliminate cross-category deletion collisions (e.g. deleting letter `'a'` deleting word `'a'`), scope tombstones by category (`"<category>:<label>"`), route categories from Controller and GUI, and upgrade schema to Version 4 with migration.

**Independent Test**: `python repro_viet_baseline.py --repo . --only D1a D1b` transitions from `BUG` to `ĐÃ SỬA`.

### Tests for D1
- [ ] T051 [US1] Write failing regression test in tests/test_bank.py verifying deleting letter 'a' preserves word 'a' after external merge (verify RED)
- [ ] T052 [US1] Write failing regression test in tests/test_controller.py verifying ctl.drop_words(['a']) deletes word 'a' and preserves letter 'a' (verify RED)
- [ ] T053 [US1] Write failing schema migration test in tests/test_schema.py verifying v3 banks automatically upgrade to v4 with tombstone normalization (verify RED)

### Implementation for D1
- [ ] T054 [US1] Update Bank.drop(label, category=None) in chuviettay/model/bank.py to support explicit category targeting with legacy fallback
- [ ] T055 [US1] Unify drop_letter and drop_symbol in chuviettay/model/bank.py to delegate to Bank.drop with category='letters' and category='symbols'
- [ ] T056 [US1] Namespace tombstones, _deleted_words, and _readded_words with '<category>:<label>' keys in chuviettay/model/bank.py
- [ ] T057 [US1] Update merge_bank_dicts in chuviettay/model/bank.py to handle both legacy unqualified tombstones (applying across all categories) and qualified tombstones (applying strictly to specified category)
- [ ] T058 [US1] Update AppController.drop_words in chuviettay/controller/app_controller.py to pass category='words' to Bank.drop
- [ ] T059 [US1] Update BankTab in chuviettay/view/bank_tab.py to ensure category context is accurately passed during deletion
- [ ] T060 [US1] Bump CURRENT_VERSION to 4 in chuviettay/model/bank_schema.py, add _migrate_v3_to_v4 to _MIGRATORS, and update validate_bank_dict to accept qualified tombstones
- [ ] T061 [US1] Update tests/test_schema.py and tests/test_schema_v3.py to align assertions with CURRENT_VERSION = 4 and add v4 schema tests
- [ ] T062 [US1] Run regression tests in tests/test_bank.py, tests/test_controller.py, and tests/test_schema.py and verify GREEN
- [ ] T063 [US1] Run python repro_viet_baseline.py --repo . --only D1a D1b and confirm ĐÃ SỬA
- [ ] T064 [US1] Run ruff check . and verify clean
- [ ] T065 [US1] Commit D1 fix with message 'fix(bank): phân tách không gian tên tombstone giữa các loại mẫu và nâng schema lên v4 [D1]'

**Checkpoint**: Category-qualified tombstones prevent cross-category deletion collisions, and Schema v4 migration cleanly upgrades existing banks.

---

## Phase 8: Polish, Verification & Final Delivery Gate

**Purpose**: Execute complete verification suite across all Phase 0 items, confirm golden-master byte invariance, and verify code quality.

- [ ] T066 [P] Run python repro_viet_baseline.py --repo . --only D1a D1b D2 D3 D4a D4b D5 and verify 100% ĐÃ SỬA
- [ ] T067 [P] Run pytest tests/test_golden_master.py and verify original golden master remains 100% green without modifying GOLDEN constants
- [ ] T068 [P] Run pytest tests/test_golden_master_real_path.py and verify Step 0 real-path golden master remains 100% green
- [ ] T069 [P] Run pytest tests/test_architecture.py and verify zero MVC architectural boundary violations
- [ ] T070 Run full pytest test suite (python -m pytest -q --timeout=90 -p no:cacheprovider) and verify 100% pass rate
- [ ] T071 Run ruff check . and verify zero linter warnings
- [ ] T072 Generate final handover report documenting commit hashes, red-to-green test evidence, design decisions, and baseline performance comparison

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1: Setup (Step 0 Real-Path Golden Master)
    │
    ▼
Phase 2: Foundational (Q1 Test Decoupling)
    │
    ▼
Phase 3: D2 Symbol Tombstone Restoration
    │
    ▼
Phase 4: D5 Concurrency & Fast Debounce Persistence
    │
    ▼
Phase 5: D4 Missing Grid Protection & Options
    │
    ▼
Phase 6: D3 Idempotent Learning & Deduplication
    │
    ▼
Phase 7: D1 Qualified Tombstones & Schema v4
    │
    ▼
Phase 8: Polish & Final Quality Gates
```

### Commit Discipline

In accordance with Phase 0 rules:
1. Every item has a dedicated commit with the specified message format.
2. Every item must have regression tests that were verified RED before the fix, and GREEN after the fix.
3. Tests and code quality gates (`ruff check .`, `pytest`) must pass before each commit.
4. No commits to be pushed or PRs opened until explicitly directed.
