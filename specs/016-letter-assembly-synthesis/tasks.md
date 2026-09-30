# Tasks: Letter-Level Handwriting Assembly & Fallback Synthesis

**Input**: Design artifacts from `specs/016-letter-assembly-synthesis/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test harness and environment initialization

- [X] T001 Initialize feature test harness file in tests/test_letter_assembly.py
- [X] T002 [P] Initialize storage test harness file in tests/test_letter_bank_storage.py
- [X] T003 [P] Initialize UI and CLI integration test harness file in tests/test_letter_gui_cli.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core storage schema v4 and bank containers that MUST be complete before user stories can execute

**CRITICAL**: Foundational tasks must complete before user story implementation begins

- [X] T004 Upgrade bank schema to version 4 with letters and marks containers in chuviettay/model/bank_schema.py
- [X] T005 Implement sequential migration _migrate_v3_to_v4 in chuviettay/model/bank_schema.py
- [X] T006 Add sample validation rules for letter samples in validate_sample and validate_bank_dict in chuviettay/model/bank_schema.py
- [X] T007 Initialize self.letters container and update empty_dict in chuviettay/model/bank.py
- [X] T008 Integrate letters and marks into merge_bank_dicts with deduplication and tombstone protection in chuviettay/model/bank.py

**Checkpoint**: Foundation ready - storage schema v4 and bank synchronization are operational

---

## Phase 3: User Story 1 - Missing Letter Reporting & Greedy Teaching Queue (Priority: P1)

**Goal**: Analyze text to decompose words into NFC letters and rank missing letters by greedy coverage to unlock maximum vocabulary with minimum teaching effort.

**Independent Test**: Provide unlearned words to `missing_letters_ranked`; verify output accurately identifies missing base letters and tone marks, sorted by the number of unlearned words each unlocks.

### Tests for User Story 1
- [X] T009 [P] [US1] Add unit tests for split_letters and missing_letters_ranked in tests/test_letter_assembly.py

### Implementation for User Story 1
- [X] T010 [US1] Implement split_letters with NFC normalization and accurate vowel tone index in chuviettay/model/text_utils.py
- [X] T011 [US1] Implement missing_letters_ranked greedy set-cover algorithm in chuviettay/model/text_utils.py
- [X] T012 [US1] Implement missing_letters_for_words helper method in chuviettay/controller/app_controller.py

**Checkpoint**: User Story 1 complete - text can be analyzed for missing letters with greedy ranking

---

## Phase 4: User Story 3 - Letter Glyph Storage & Multi-Session Concurrency (Priority: P1)

**Goal**: Allow adding, dropping, and querying letter samples in Bank with multi-process concurrency safety and standalone tone mark persistence.

**Independent Test**: Teach letters, save to disk, verify schema v4 migration from legacy files, and assert concurrent merge preserves letter additions and tombstones.

### Tests for User Story 3
- [X] T013 [P] [US3] Add unit tests for add_letter_sample, drop_letter, standalone tone marks, and v4 migration in tests/test_letter_bank_storage.py

### Implementation for User Story 3
- [X] T014 [US3] Implement add_letter_sample and drop_letter with tombstone tracking in chuviettay/model/bank.py
- [X] T015 [US3] Implement standalone tone mark persistence and update rebuild in chuviettay/model/bank.py
- [X] T016 [US3] Implement teach_letter and drop_letter coordinator methods in chuviettay/controller/app_controller.py

**Checkpoint**: User Story 3 complete - letter glyphs and tone marks safely stored and synchronized across processes

---

## Phase 5: User Story 2 - Automated Fallback Word Synthesis from Letters (Priority: P1)

**Goal**: Synthesize unlearned words dynamically from learned letter glyphs along the baseline, attaching tone marks, suppressing letter `i` dot, and executing the 4-tier resolution cascade.

**Independent Test**: Render text containing words missing from `bank.words` but whose letters exist in `bank.letters`. Verify synthesized words have 100% stroke visibility and 0 blank gaps.

### Tests for User Story 2
- [X] T017 [P] [US2] Add unit tests for assemble_word, dot suppression, kerning, and resolution cascade in tests/test_letter_assembly.py

### Implementation for User Story 2
- [X] T018 [US2] Implement Writer.assemble_word with kerning overlap and opportunistic 1-letter word fallback in chuviettay/model/writer.py
- [X] T019 [US2] Implement tone mark positioning and scoped dot suppression on letter i in chuviettay/model/writer.py
- [X] T020 [US2] Integrate assemble_word into Writer.word 4-tier resolution cascade in chuviettay/model/writer.py
- [X] T021 [US2] Add assembled_words and missing_letters tracking to Writer in chuviettay/model/writer.py

**Checkpoint**: User Story 2 complete - words synthesized automatically from letters as fallback

---

## Phase 6: User Story 4 - Backward Compatibility & Golden Master Invariance (Priority: P2)

**Goal**: Guarantee that when `assemble_letters=False` (default), the synthesis engine produces 100% byte-identical output to legacy versions.

**Independent Test**: Run `tests/test_golden_master.py` and verify all SHA-256 hashes match reference values with 0 discrepancies.

### Implementation for User Story 4
- [X] T022 [US4] Add assemble_letters boolean option with False default to WriteOptions in chuviettay/model/composer.py
- [X] T023 [US4] Add assembled_words and missing_letters fields with default factories to WriteResult in chuviettay/model/composer.py
- [X] T024 [US4] Wire assembled_words and missing_letters pass-through in chuviettay/layout/engine.py and chuviettay/fidelity/engine.py
- [X] T025 [US4] Verify golden master invariance by running tests/test_golden_master.py

**Checkpoint**: User Story 4 complete - 100% backward compatibility and golden master parity guaranteed

---

## Phase 7: User Story 5 - User Interface Controls & Bank Statistics (Priority: P2)

**Goal**: Provide GUI controls in WriteTab, TeachTab, and BankTab, as well as CLI `--assemble` and `stats` support.

**Independent Test**: Verify checkbox in WriteTab toggles assembly, missing letters button populates TeachTab queue, BankTab displays letter counts, and CLI `--assemble` flag functions as expected.

### Tests for User Story 5
- [X] T026 [P] [US5] Add unit tests for CLI assemble flag and stats output in tests/test_letter_gui_cli.py

### Implementation for User Story 5
- [X] T027 [US5] Add --assemble argument and letter stats reporting to write and stats commands in chuviettay/cli.py
- [X] T028 [US5] Extend BankStats with n_letters and letter_counts in chuviettay/controller/results.py and chuviettay/controller/app_controller.py
- [X] T029 [US5] Update WriteTab with assembly toggle checkbox, assembled words display, and teach missing letters action in chuviettay/view/write_tab.py
- [X] T030 [US5] Update TeachTab to route single letter teaching through teach_letter in chuviettay/view/teach_tab.py
- [X] T031 [US5] Update BankTab to display letter statistics and support dropping letter samples in chuviettay/view/bank_tab.py

**Checkpoint**: User Story 5 complete - full GUI and CLI integration operational

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation, regression checks, and code quality verification

- [X] T032 [P] Execute end-to-end quickstart scenarios in specs/016-letter-assembly-synthesis/quickstart.md
- [X] T033 Run full pytest test suite across all tests to verify zero regressions
- [X] T034 Verify strict MVC architecture compliance with zero tkinter or print imports in chuviettay/model/

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**:
  - **US1 (Missing Letter Reporting)**: Depends on Foundational phase.
  - **US3 (Letter Glyph Storage)**: Depends on Foundational phase.
  - **US2 (Fallback Word Synthesis)**: Depends on US1 (split_letters) and US3 (bank storage).
  - **US4 (Backward Compatibility & Golden Master)**: Depends on US2 (Writer resolution cascade).
  - **US5 (UI Controls & CLI)**: Depends on US1, US2, US3, US4.
- **Polish (Phase 8)**: Depends on all user stories being complete.

---

## Parallel Opportunities

- T001, T002, T003 can execute in parallel.
- Test tasks marked [P] (T009, T013, T017, T026) can be written concurrently with or before implementation.
- T010 and T014 can be developed in parallel as they touch separate modules (`text_utils.py` vs `bank.py`).

---

## Implementation Strategy

### MVP Scope (Phases 1 through 5)
1. Complete Setup and Foundational storage schema v4.
2. Complete US1 (letter splitting and greedy ranking).
3. Complete US3 (letter storage and persistence).
4. Complete US2 (Writer dynamic letter assembly).
5. Validate MVP independently: unlearned words synthesize from learned letters.

### Full Delivery (Phases 6 through 8)
1. Complete US4 (Golden master parity and dual-engine integration).
2. Complete US5 (GUI controls, TeachTab routing, BankTab inventory, CLI `--assemble`).
3. Complete Phase 8 (Quickstart validation and full test suite passing).
