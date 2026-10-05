# Research & Architectural Decisions: Data Integrity Safety Net & Core Persistence Hardening (P0)

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](./spec.md)  
**Status**: Completed  

---

## Executive Summary & Root Cause Findings

Prior to Phase 0 modifications, systematic analysis and reproduction using `repro_viet_baseline.py` on commit `e517636` identified seven primary data integrity vulnerabilities and safety gaps:

1. **Step 0 — Production Path Lacks Golden Master**:
   `tests/test_golden_master.py` tests only `composer.write_document(...)` (a deprecated prototype function operating on a fixed 598x200 canvas). The actual production path used by CLI and GUI (`AppController.write_text` -> `DocumentLayoutEngine`) generates standard A4 pages (595.28x841.89 pt) with distinct line breaking, font rendering, and missing grid logic. Because neither engine shares output XML bytes, any changes to `DocumentLayoutEngine` risk undetected visual or structural regressions.
2. **Q1 — Environment-Coupled Test Failures**:
   `tests/test_docx_fidelity.py` and `tests/test_cli_format.py` guard Word COM extraction using `if not FidelityConverter.is_available():`. Because `FidelityConverter.is_available()` returns `True` if *either* Word or LibreOffice is installed, environments with LibreOffice but without Microsoft Word attempt COM spatial extraction, raising `RuntimeError`. In addition, `test_large_bank_persistence_benchmark_5000_samples` failed when executed under code coverage due to rigid timing thresholds.
3. **D2 — Tombstone Ignored in `add_symbol_sample`**:
   `add_sample` and `add_letter_sample` clear deletion tombstones, discard keys from `_deleted_words`, and track additions in `_readded_words`. `add_symbol_sample` omitted this logic entirely. If a symbol was deleted and later re-learned, any multi-process merge reapplied the tombstone, silently wiping the new symbol.
4. **D5 — Concurrency Race in Deferred Debounce Saves**:
   Debounce saves run on background `threading.Timer` worker threads. The previous implementation called `json.dump(self.d, gz_f)` directly on a streaming file object. Python's pure-Python dictionary serializer traverses dict buckets iteratively; when a GUI user taught new words concurrently, the dictionary mutated during iteration, throwing `RuntimeError: dictionary changed size during iteration`. The background thread died silently, the save was dropped, and user data remained unpersisted.
5. **D4 — Missing Grid Overwrite & Flag Neglect**:
   `DocumentLayoutEngine` ignored `opts.missing_grid`. The CLI lacked a `--no-missing-grid` flag. When `<out>_thieu.xopp` was generated, re-running synthesis unconditionally wiped the file, destroying user handwriting already written into the practice sheet.
6. **D3 — Non-Idempotent Learning**:
   `learn_from_files` recorded learned files by SHA-256 of the raw `.xopp` file. Because `.xopp` is a gzip archive containing a creation timestamp header (`mtime`), re-compressing the exact same XML produced a different raw file hash, bypassing deduplication and re-adding duplicate samples.
7. **D1 — Unscoped Tombstone Collisions Across Categories**:
   `Bank._tombstones`, `_deleted_words`, and `_readded_words` indexed deletions solely by bare string labels (e.g. `"a"`). When `learn` ingested hw3 grids, it registered both `letters['a']` and `words['a']`. Deleting letter `a` created tombstone `"a"`, which upon merge deleted word `a`. Similarly, `AppController.drop_words(["a"])` resolved through `Bank.drop(label)`, which arbitrarily selected `letters` before `words`, deleting the letter instead of the word.

---

## Detailed Architectural Decisions

### Decision 1: Category-Qualified Namespacing for Tombstones (D1 & D2)

**Context**: Resolving cross-category sample deletion collisions between `words`, `letters`, `digits`, `symbols`, and `punct`.

**Decision**:
1. Store tombstones and pending deletion sets internally using qualified string keys: `"<category>:<label>"` (e.g. `"letters:a"`, `"words:a"`, `"symbols:π"`).
2. Update `Bank.drop(label, category=None)`:
   - If `category` is explicitly specified (one of `"words"`, `"letters"`, `"digits"`, `"symbols"`, `"punct"`), delete the sample only from that category dictionary and record `"<category>:<label>"` in tombstones and `_deleted_words`.
   - If `category is None`, retain legacy fallback order: `symbols -> digits -> punct -> letters -> words` for backward compatibility with external scripts.
3. Update `AppController.drop_words(words)` to explicitly pass `category="words"`.
4. Update `BankTab` in `hw_gui.py` to inspect the currently active category tab and pass the exact category string to `AppController`.
5. Extract a shared helper `_clear_tombstone_and_mark_readded(category, label)` in `Bank` used by `add_sample`, `add_letter_sample`, and `add_symbol_sample`.
6. Backward Compatibility for Merge:
   - When merging with a bank that has unqualified tombstones (e.g. `"a"` without a colon), the merge logic applies the tombstone across all categories as in legacy behavior.
   - When merging with a bank that has qualified tombstones (e.g. `"letters:a"`), the tombstone applies strictly to the specified category.

**Rationale**:
Using qualified string keys requires zero changes to the underlying JSON format types (strings in a list/dict) and guarantees unambiguous identity. Backward compatibility guarantees that older files do not resurrect previously deleted data.

---

### Decision 2: Schema Version Upgrade to Version 4

**Context**: Ensuring older software versions do not silently misinterpret qualified tombstones and validating bank structure.

**Decision**:
1. Increment `CURRENT_VERSION = 4` in `chuviettay/model/bank_schema.py`.
2. Add a schema migrator `migrate_v3_to_v4(data)`:
   - Upgrades `schema_version` to 4.
   - Preserves existing sample categories and marks.
   - Normalizes tombstones: keeps legacy unqualified tombstones intact while marking the bank as v4.
3. Update `validate_bank_dict`:
   - Accept schema version 4 as valid.
   - Allow tombstones to contain both legacy strings and `"<category>:<label>"` formatted strings.
4. Update schema test suites (`test_schema.py`, `test_schema_v3.py`) to validate v4 persistence and migration.

**Rationale**:
Clear versioning informs users and tooling of format changes, preventing older buggy engines from corrupting namespaced tombstones.

---

### Decision 3: Atomic Serialization & Concurrency Protection in Bank Persistence (D5)

**Context**: Eliminating `RuntimeError: dictionary changed size during iteration` during background timer debounce saves and ensuring thread-safe persistence.

**Decision**:
1. Fast Single-Pass Serialization:
   In `Bank.save()`, replace iterative file dumping with an atomic in-memory serialization pass:
   ```python
   payload = json.dumps(self.d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
   ```
   Followed by fast gzip writing:
   ```python
   with gzip.open(temp_file, "wb", compresslevel=1) as gz:
       gz.write(payload)
   ```
2. Thread Synchronization (`threading.RLock`):
   Instantiate `self._lock = threading.RLock()` in `Bank`.
   - Acquire `self._lock` in mutative methods: `add_sample*`, `add_letter_sample*`, `add_symbol_sample*`, `drop*`, `clear`, etc.
   - In `Bank.save()`, acquire `self._lock` during:
     a) Checking disk modification timestamps and merging disk state if modified.
     b) Serializing `self.d` to the in-memory `payload` bytes.
   - Release `self._lock` *before* initiating filesystem operations (writing temporary file, `fsync`, and atomic rename `os.replace`).
3. Resilient Error Handling in Controller:
   In `AppController._on_debounce_save`:
   - Wrap the save call in `try / except Exception`.
   - Log failures using `_log.exception("Debounce save failed")`.
   - Maintain the bank's dirty state flag (`self.bank._dirty = True`) so subsequent operations or application exit will retry saving.
4. Test Update:
   Update `test_save_bi_ngat_giua_chung_thi_kho_cu_con_nguyen_va_khong_de_lai_file_tam` in `tests/test_bank.py` to patch `json.dumps` (or `os.replace`), preserving the test's intent of asserting zero file corruption and zero temporary file leakage upon unexpected failure.

**Rationale**:
Single-pass C-accelerated `json.dumps` is ~5.1x faster than streaming Python `json.dump`. Releasing the lock before disk I/O ensures the GUI remains responsive while the in-memory snapshot is written to disk. The `RLock` guarantees thread safety on all Python implementations, including free-threaded Python (3.13t).

---

### Decision 4: Idempotent Practice Grid Learning (D3)

**Context**: Preventing duplicate sample accumulation when the same practice grid is learned multiple times or re-saved.

**Decision**:
1. Uncompressed Content Hashing:
   In `chuviettay/model/learning.py`, compute the SHA-256 hash over the decompressed XML stream of `.xopp` files:
   ```python
   xml_content = gzip.decompress(raw_bytes)
   file_hash = hashlib.sha256(xml_content).hexdigest()
   ```
2. Legacy Tolerance:
   Retain existing recorded hashes in `learned_files`. If a file's raw or uncompressed hash is present, skip re-learning.
3. Cell-Level Deduplication via `sample_signature`:
   When extracting strokes from practice cells, pass `dedup=True` to `add_sample` / `add_letter_sample`. Compare sample strokes and width using `sample_signature(strokes, width)`. Skip inserting duplicate cells even if a new practice file is processed.
4. Explicit Test Support:
   Preserve `dedup=False` parameter capability for tests that deliberately evaluate duplicate handling.

**Rationale**:
Gzip file headers include an `mtime` timestamp field that varies on re-compression. Hashing the canonical uncompressed XML makes duplicate detection deterministic and idempotent. Cell-level deduplication protects against sheets where users fill in additional cells over time.

---

### Decision 5: Non-Destructive Missing Grid Generation & Stroke Preservation (D4)

**Context**: Preventing synthesis from erasing user handwriting in `<out>_thieu.xopp`, and honoring `missing_grid=False`.

**Decision**:
1. Honor `opts.missing_grid`:
   In `chuviettay/layout/engine.py` (around line 570), check `if self.opts.missing_grid:`. If `False`, skip calling `xopp.make_grid` entirely and return `missing_grid_path = None`.
2. CLI and GUI Options:
   - Add `--no-missing-grid` argument to `chuviettay write` subparser in `chuviettay/cli.py` and `hw_note.py`.
   - Add "Tạo file chữ thiếu" checkbox in `hw_gui.py` Write Tab, bound to `opts.missing_grid`.
3. Authentic User Stroke Detection:
   When `<out>_thieu.xopp` already exists:
   - Parse XML and inspect `<stroke>` tags.
   - A stroke represents user handwriting if `tool == "pen"` and its `color` attribute is NOT in `HW3_GUIDE_COLORS` (`#c8c8c8`, `#a0a0a0`, `#d8d8d8`, `#e0e0e0`, `#e8e8e8`, `#ffc0c0`, etc. defined in `chuviettay/model/xopp.py`).
4. Sequential File Suffixing:
   - If user handwriting strokes are detected, search for the next available filename: `<out>_thieu_2.xopp`, `<out>_thieu_3.xopp`, etc.
   - Write the newly generated grid to the non-colliding path.
   - Record the final path in `WriteResult.missing_grid_path` so CLI reports and GUI dialogs present the correct path.
   - If the file exists but contains ONLY guide strokes (no user handwriting), overwrite it in-place as before.

**Rationale**:
Protects hours of user effort writing into practice sheets while avoiding filename clutter when no actual user writing is present.

---

### Decision 6: Decoupled Environment Test Guards & Benchmark Markers (Q1)

**Context**: Eliminating false test failures on machines with LibreOffice or when running tests with coverage.

**Decision**:
1. In `tests/test_docx_fidelity.py` and `tests/test_cli_format.py`, replace:
   ```python
   if not FidelityConverter.is_available():
   ```
   with:
   ```python
   if not FidelityConverter.is_word_available():
   ```
   This ensures environments with LibreOffice but without Word COM mock the extraction layer cleanly.
2. Decorate `test_large_bank_persistence_benchmark_5000_samples` in `tests/test_bank.py` with `@pytest.mark.benchmark`.
3. Register `benchmark` in `pytest.ini`:
   ```ini
   markers =
       gui: ...
       benchmark: các bài đo hiệu năng thời gian thực
   ```

**Rationale**:
Decouples unit test execution from environment-specific Office software installations, enabling seamless CI runs on Linux and Windows.

---

### Decision 7: Real-Path Golden Master Architecture (Step 0)

**Context**: Creating a deterministic regression safety net for the real production engine (`AppController.write_text` / `DocumentLayoutEngine`).

**Decision**:
1. Implement `tests/test_golden_master_real_path.py`:
   - Run `AppController.write_text` with standard `tiny_bank_dict()`.
   - Test standard cases:
     * `co_ban`: Baseline mixed Vietnamese text with accents and symbols.
     * `tuy_chon`: Custom width, scale, spacing, jitter, and color options.
     * `nhieu_trang`: Multi-page document generation.
     * `strict_case`: Case-sensitive character preservation.
   - Test extended cases:
     * `assemble_letters`: Letter assembly (`assemble_letters=True`, `auto_xh`) with `_create_quality_test_bank`.
     * `inline_and_block_math`: Inline math `$x^2$` and block math `$$\sum_{i=1}^n x_i$$`.
     * `markdown_table`: Multi-column Markdown table.
     * `markdown_list_and_headings`: Nested lists and hierarchical headings.
2. Verification Algorithm:
   - Decompress `.xopp` and `_thieu.xopp` archives to XML.
   - Compute `hashlib.sha256(xml_bytes).hexdigest()`.
   - Compare against fixed reference digests recorded from the unmodified codebase (`e517636`).
   - Assertion error messages print observed hash values for instant validation.

**Rationale**:
Guarantees byte-level layout invariance across all future refactorings and features.
