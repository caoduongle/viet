# Feature Specification: Data Integrity Safety Net & Core Persistence Hardening (P0)

**Feature Branch**: `fix/phase0-data-integrity`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "# P0 — Bước 0 và Giai đoạn 0: lưới an toàn + vá lỗi toàn vẹn dữ liệu (repo viet)
Thứ tự trong chuỗi: P0 → P1 → P2A → P2B → P2C → P3A/P3B → P4. Đọc 00_README.md để biết bức tranh chung. Tệp đi kèm: repro_viet_baseline.py.
Nhiệm vụ, theo thứ tự: Bước 0 → Q1 → D2 → D5 → D4 → D3 → D1. Không làm những gì thuộc P1 trở đi."

---

## Background & Problem Statement

The `chuviettay` application synthesizes personalized Vietnamese handwriting documents into Xournal++ (`.xopp`) format via CLI (`hw_note.py`) and GUI (`hw_gui.py`). The core engine relies on a handwriting sample bank stored in compressed JSON format (`.json.gz`).

Comprehensive baseline reproduction using `repro_viet_baseline.py` on commit `e517636` identified critical data integrity vulnerabilities, race conditions, and testing gaps:
1. **Unprotected Real Production Path (Step 0)**: Existing golden-master regression tests (`tests/test_golden_master.py`) only exercise a deprecated legacy composer function (`composer.write_document`), whereas the actual CLI and GUI pipeline uses `AppController.write_text` / `DocumentLayoutEngine` targeting standard A4 pages. Changes to the production layout engine currently lack golden-master regression protection.
2. **Environment-Coupled Test Flakiness (Q1)**: Word COM integration tests fail when LibreOffice is present without Microsoft Word because the availability guard incorrectly treats LibreOffice as capable of COM spatial extraction. Furthermore, large-scale persistence benchmark tests fail under test coverage due to unflagged timing constraints.
3. **Symbol Tombstone Blind Spot (D2)**: Adding symbol samples (`add_symbol_sample`) fails to clear deletion tombstones or register re-added keys, causing newly learned symbols to be permanently deleted on subsequent multi-process merges.
4. **Debounce Save Concurrency Race (D5)**: Multi-threaded deferred saves execute streaming JSON serialization over mutable dictionaries while GUI operations insert new words, triggering unhandled `RuntimeError: dictionary changed size during iteration` and dropping save operations.
5. **Data Loss on In-Progress Missing Grids (D4)**: Generating documents with missing characters unconditionally overwrites `<output>_thieu.xopp`, destroying user handwriting in progress without warning. Furthermore, the `missing_grid=False` option is ignored by the modern layout engine, and the CLI lacks a `--no-missing-grid` flag.
6. **Non-Idempotent Grid Learning (D3)**: The learning subsystem dedupes files based on raw archive checksums whose gzip headers include timestamps; re-exporting the exact same grid with different archive timestamps causes all samples to be re-added as duplicates.
7. **Cross-Category Tombstone Collision (D1)**: Tombstones are keyed solely by text label without categorizing by sample type (words, letters, digits, symbols, punctuation). Deleting single-letter sample `a` inadvertently deletes whole-word sample `a` during bank merges, and GUI deletion of words erroneously removes letter samples of the same name.

This Phase 0 specification establishes strict data integrity guarantees, concurrent persistence safety, user data loss prevention, and an automated regression safety net across the actual production pipeline.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cross-Category Sample Isolation and Safe Deletion (Priority: P1)

As a user managing a handwriting collection, when I remove or re-learn a letter sample (e.g., character "a"), my corresponding whole-word sample (e.g., word "a") and other categories must remain intact and completely isolated during local operations and background merges.

**Why this priority**: Prevents catastrophic, silent user data loss where deleting or modifying one category destroys user handwriting in other categories sharing the same label.

**Independent Test**: Can be tested by adding both a letter sample "a" and a word sample "a", removing the letter sample, triggering a multi-process touch and merge save, and verifying that the word sample survives while the letter sample is cleanly removed.

**Acceptance Scenarios**:
1. **Given** a bank with letter `a` and word `a`, **When** the user or controller deletes the letter sample `a` and merges with external changes, **Then** `letters['a']` is deleted, `words['a']` is fully preserved, and tombstones track category-qualified identifiers (`letters:a`).
2. **Given** a user selecting word `a` in the GUI sample management tab, **When** the user clicks delete, **Then** only `words['a']` is deleted and `letters['a']` is untouched.
3. **Given** a symbol `π` deleted with a tombstone, **When** the user subsequently teaches a new sample for `π` via `add_symbol_sample` and a merge occurs, **Then** the tombstone is cleared, the re-added symbol is tracked, and the new sample is preserved on disk.
4. **Given** a legacy bank file created under Schema Version 3 containing unqualified tombstones, **When** opened and migrated to Schema Version 4, **Then** legacy tombstones apply safely across categories without crashing or reviving previously deleted samples.

---

### User Story 2 - Resilient Thread-Safe Background Persistence (Priority: P1)

As a user rapidly teaching new words in the GUI, the application must reliably persist changes in the background without throwing dictionary iteration exceptions, dropping saves, or freezing the interface.

**Why this priority**: Under rapid input in the GUI, background timer saves currently crash with `RuntimeError`, causing lost handwriting data without notifying the user.

**Independent Test**: Can be tested by simulating high-speed word teaching (50+ words added during active debounce intervals on a 40,000+ sample bank) and verifying zero `RuntimeError` exceptions, zero temporary file leaks, atomic file replacement, and 100% data retention upon flush.

**Acceptance Scenarios**:
1. **Given** a large handwriting bank (≥ 20,000 samples) and an active debounce timer, **When** new samples are added concurrently while a save is serializing, **Then** serialization completes atomically without `RuntimeError` dictionary iteration exceptions.
2. **Given** a background debounce save operation, **When** an unexpected I/O exception occurs, **Then** the exception is captured in logs, the dirty state flag is preserved, and the next save attempt or application exit safely retries writing the unsaved data.
3. **Given** the persistence pipeline, **When** writing the bank to disk, **Then** the serialized payload is formatted in a fast single-pass buffer, written to a temporary file, synced to disk, and atomically renamed over the target file.

---

### User Story 3 - Idempotent Learning and Sample Deduplication (Priority: P1)

As a user re-scanning or re-importing practice sheets, the learning engine must detect duplicate submissions based on canonical document content regardless of file compression timestamps, and deduplicate individual cell strokes.

**Why this priority**: Prevents bank bloat and distorted handwriting statistics caused by duplicate sample accumulation when the same practice grid is imported multiple times.

**Independent Test**: Can be tested by generating a practice grid, creating two distinct `.xopp` files with identical XML content but different gzip archive modification times, running learning on both, and verifying that total sample counts do not increase on the second run.

**Acceptance Scenarios**:
1. **Given** a generated practice grid file `g1.xopp` and an identical XML copy `g2.xopp` compressed with a different timestamp, **When** `learn_from_files` is executed on both files sequentially, **Then** the second file is recognized as already learned and zero duplicate samples are inserted.
2. **Given** a partially completed practice sheet where new strokes are added to previously empty cells, **When** the updated sheet is learned, **Then** existing cells are deduplicated via stroke signature comparison and only genuinely new character samples are added.

---

### User Story 4 - In-Progress Missing Grid Protection and Option Control (Priority: P2)

As a user synthesizing documents, I must be able to disable missing grid generation when unneeded. When missing grids are enabled, any existing missing grid file containing my handwritten strokes must never be overwritten or destroyed.

**Why this priority**: When users spend time filling out generated `<out>_thieu.xopp` sheets, re-running synthesis currently overwrites the file and erases their handwritten progress.

**Independent Test**: Can be tested by generating `<out>_thieu.xopp`, appending an authentic user pen stroke to it, re-running synthesis with missing characters, and verifying that the existing file is preserved and a non-colliding file `<out>_thieu_2.xopp` is created.

**Acceptance Scenarios**:
1. **Given** synthesis requested with `missing_grid=False` (or CLI flag `--no-missing-grid`), **When** synthesis finishes with missing characters, **Then** no `_thieu.xopp` file is generated on disk.
2. **Given** an existing `<out>_thieu.xopp` containing non-guide user pen strokes, **When** synthesis is re-run and missing characters occur, **Then** the original file is kept unmodified, output is written to the next sequential filename (`<out>_thieu_2.xopp`), and the returned `WriteResult.missing_grid_path` accurately reflects the new path.
3. **Given** an existing `<out>_thieu.xopp` that contains only guide lines and background marks (no user writing), **When** synthesis is re-run, **Then** the file is overwritten cleanly as before without creating superfluous numbered copies.

---

### User Story 5 - Real-Path Golden Master & Portable Test Suite (Priority: P2)

As a developer and CI system, the test suite must verify the byte-level deterministic output of the actual production layout engine (`AppController.write_text` / `DocumentLayoutEngine`) and execute reliably across diverse environments (with or without Word COM, with or without code coverage).

**Why this priority**: Guarantees that future optimizations and refactorings never introduce visual or structural regressions into real production outputs, and ensures CI builds pass consistently.

**Independent Test**: Can be tested by running `pytest` with and without Word COM installed, running benchmarks under standard invocation, and verifying `tests/test_golden_master_real_path.py` reproduces fixed SHA-256 hashes for uncompressed XML outputs across all seeds.

**Acceptance Scenarios**:
1. **Given** `tests/test_golden_master_real_path.py` covering standard cases (`co_ban`, `tuy_chon`, `nhieu_trang`, `strict_case`) and extended cases (letter assembly, math, tables, markdown lists), **When** executed, **Then** decompressed XML outputs match deterministic golden SHA-256 digests.
2. **Given** a testing environment with LibreOffice installed but without Microsoft Word COM, **When** executing fidelity converter tests, **Then** tests safely use controlled mock fixtures rather than raising unhandled `RuntimeError`.
3. **Given** execution under code coverage or resource-constrained CI environments, **When** persistence benchmark tests run, **Then** dedicated benchmark test markers allow selective execution without false-positive timing failures.

---

### Edge Cases

- **Mixed-Version Tombstones**: What happens when a bank contains legacy unqualified tombstones (e.g. `"a"`) alongside new category-qualified tombstones (e.g. `"letters:a"`)? The merge engine must honour both, applying unqualified tombstones broadly to avoid resurrecting deleted data while scoping qualified tombstones strictly to their respective category.
- **Concurrent Write Collisions During Save**: What happens if an external process modifies the bank on disk while an in-memory timer save is executing? File locking (`FileLock`) and disk modification timestamp checks must detect the change, merge the disk state cleanly with the in-memory state, and persist the combined result atomically.
- **Multiple Sequential Missing Grids**: What happens if both `_thieu.xopp` and `_thieu_2.xopp` already exist and contain user handwriting? The system must increment the suffix to the first non-colliding name (`_thieu_3.xopp`).
- **Malformed Practice Sheets**: What happens if a practice grid file is corrupted or cannot be decompressed during idempotent learning? The learning pipeline must log the failure and skip the file gracefully without corrupting existing learned file records.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support category-qualified tombstone keys in internal bank tracking (`_tombstones`, `_deleted_words`, `_readded_words`) using the format `"<category>:<label>"` (e.g., `"letters:a"`, `"words:a"`, `"symbols:π"`).
- **FR-002**: System MUST allow `Bank.drop(label, category=None)` to accept an optional category parameter, defaulting to legacy category resolution order when `category=None` for backward compatibility.
- **FR-003**: System MUST pass explicit category targets from `AppController` and GUI `BankTab` when deleting samples so that deleting a word never deletes a letter of the same name and vice versa.
- **FR-004**: System MUST upgrade `CURRENT_VERSION` in `chuviettay/model/bank_schema.py` to Version 4 and provide an automated schema migrator from Version 3 to Version 4.
- **FR-005**: System MUST validate and parse both legacy unqualified tombstones and Version 4 category-qualified tombstones during bank loading and dictionary merging.
- **FR-006**: System MUST remove existing tombstones, discard from `_deleted_words`, and record into `_readded_words` when `add_symbol_sample` is called, matching the behavior of `add_sample` and `add_letter_sample`.
- **FR-007**: System MUST perform bank serialization in `Bank.save()` by serializing the entire dictionary in a single call via `json.dumps(..., ensure_ascii=False, separators=(',', ':'))` before writing to gzip storage, eliminating streaming dictionary iteration races.
- **FR-008**: System MUST protect mutable bank operations and merge-serialization critical sections with thread synchronization (`threading.RLock`) to guarantee thread safety beyond CPython GIL assumptions.
- **FR-009**: System MUST catch unhandled exceptions inside `_on_debounce_save`, log the full traceback, and keep the bank's dirty flag set so subsequent operations will retry persistence.
- **FR-010**: System MUST calculate file hashes for the learned file registry (`learned_files`) based on the SHA-256 digest of uncompressed XML content rather than raw archive bytes.
- **FR-011**: System MUST perform per-cell stroke deduplication during practice grid learning using `sample_signature`, skipping duplicate cells even if a practice grid has not been previously seen in `learned_files`.
- **FR-012**: System MUST respect `WriteOptions.missing_grid` in `DocumentLayoutEngine`, preventing the generation of `<output>_thieu.xopp` when `missing_grid=False`.
- **FR-013**: System MUST expose the `--no-missing-grid` flag in the CLI (`hw_note.py`) and a corresponding user checkbox in the GUI Write Tab (`hw_gui.py`).
- **FR-014**: System MUST detect authentic user handwriting strokes in `<output>_thieu.xopp` (pen strokes whose color is not in `HW3_GUIDE_COLORS`) and generate sequential non-colliding filenames (`_thieu_2.xopp`, etc.) when user strokes exist.
- **FR-015**: System MUST record the actual generated missing grid file path in `WriteResult.missing_grid_path` and format it accurately in console and UI reports.
- **FR-016**: System MUST update fidelity test guards in `tests/test_docx_fidelity.py` and `tests/test_cli_format.py` from `FidelityConverter.is_available()` to `FidelityConverter.is_word_available()`.
- **FR-017**: System MUST mark timing-sensitive persistence benchmarks with `@pytest.mark.benchmark` and register the `benchmark` marker in `pytest.ini`.
- **FR-018**: System MUST establish a comprehensive golden-master test suite (`tests/test_golden_master_real_path.py`) validating uncompressed XML SHA-256 digests produced by `AppController.write_text` across standard and extended layout scenarios.

---

### Key Entities

- **Handwriting Bank (`Bank`)**: Core data container managing categorized sample collections (`words`, `letters`, `digits`, `symbols`, `punct`), stroke metadata, tombstones, and atomic gzip persistence.
- **Tombstone**: Deletion marker recording deleted keys to ensure deletions propagate correctly when merging concurrently modified banks on disk. In Schema v4, namespaced by sample category.
- **Learned File Registry (`learned_files`)**: Set of content digests representing previously processed practice sheets to avoid duplicate learning.
- **Layout Engine (`DocumentLayoutEngine`)**: Modern page-based typesetting engine translating structured text or Document IR into multi-page `.xopp` documents and tracking missing character inventories.
- **Missing Grid Document (`_thieu.xopp`)**: A generated practice grid containing cells for words or characters that were missing during synthesis, allowing users to write them by hand and learn them into the bank.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of reproduction test checks in `repro_viet_baseline.py` for Phase 0 (`D1a`, `D1b`, `D2`, `D3`, `D4a`, `D4b`, `D5`) transition from `BUG` to `ĐÃ SỬA`.
- **SC-002**: Automated test suite achieves 100% pass rate (`pytest -q`) on environments with LibreOffice but without Microsoft Word, with zero regressions against existing baseline tests.
- **SC-003**: Persistence benchmark tests for large banks (60,000 samples) demonstrate faster serialization latency (~5x reduction from ~0.77s to ~0.15s) with zero dictionary mutation errors during active concurrency.
- **SC-004**: Zero user stroke data loss: re-running synthesis over an existing missing grid file containing user handwriting preserves 100% of user strokes in the existing file while routing new missing characters to a new file.
- **SC-005**: 100% test determinism on real production path: `tests/test_golden_master_real_path.py` outputs identical SHA-256 XML digests across varying seeds and execution environments.
- **SC-006**: Code quality and architecture gates remain 100% clean: zero linter warnings under `ruff check .` and zero architecture violations under `tests/test_architecture.py`.

---

## Assumptions

- **Python Runtime Environment**: Primary target environments are CPython 3.10 through 3.14 on Linux, macOS, and Windows. Thread synchronization incorporates `threading.RLock` to safeguard against free-threaded Python builds (3.13t) and long-running background tasks.
- **Zero Core Dependency Mandate**: All enhancements to `chuviettay` core, models, layout engine, and CLI remain free of mandatory third-party dependencies (`dependencies = []` in `pyproject.toml`).
- **Backward Compatibility**: Existing Version 3 `.json.gz` banks in user storage automatically migrate to Version 4 on save, while Version 4 banks preserve all sample data and format structures required by the application.
- **Out of Scope for P0**: Advanced text layout formatting (F1: center/right alignment), Markdown inline style handling (F2: bold/italic/strike preservation), packaging paths (F4: site-packages default bank path), intermediate stroke IR, and GUI freeze prevention during synthesis are deferred to subsequent phases (P1 and P2).
