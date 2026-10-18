# Research & Technical Decisions: Feature 043 — Worker Recovery & Render Seed Pipeline Hardening

**Branch**: `043-worker-recovery-seed-stability` | **Date**: 2026-10-18 | **Spec**: [spec.md](file:///d:/viet/app/specs/043-worker-recovery-seed-stability/spec.md)

---

## 1. Web Worker Recovery: Verification, Timeouts, and UI Lifecycle

### Context & Root Cause Analysis
In [`webapp/js/app.js`](file:///d:/viet/app/webapp/js/app.js#L119-L175) and [`attachWorkerHandlers`](file:///d:/viet/app/webapp/js/app.js#L240-L310), five concrete defects were identified:
1. `recoverWorker()` awaits `readyPromise` (which resolves to `true` or `false`), ignores the boolean return value, and unconditionally returns `true`.
2. The `finally` block in `recoverWorker()` unconditionally hides `#btn-worker-retry` (`btnRetry.style.display = "none"`), AND `onWorkerReady()` hides `#btn-worker-retry` at its very first line (line 327) *before* `storage.listProfiles()` and `sendWorkerMessage("load_bank", ...)` execute.
3. In `attachWorkerHandlers`, `targetWorker.onmessageerror` calls `handleWorkerFatalError(...)` without resolving `workerReadyResolve(false)`, and `data.type === "ERROR"` resolves `workerReadyResolve(false)` without calling `handleWorkerFatalError(...)`.
4. If the new Worker hangs during initialization without sending `READY` or firing an error event, `readyPromise` waits forever.
5. `isUiInitialized = true` is set in `onWorkerReady()` before `storage.listProfiles()` completes, which can prematurely suppress `showWelcomeModal()` if the first profile load fails.

### Decision
- **Strict End-to-End Readiness Validation**:
  - `recoverWorker(WorkerClass = null, timeoutMs = 10000)` awaits `readyPromise` bounded by a `timeoutMs` timer (default `10_000ms`).
  - `onWorkerReady()` only hides `#splash-screen` and `#btn-worker-retry`, marks `isUiInitialized = true`, and sets `setStatus("status_ready")` at the **very end** of `onWorkerReady()` after `load_bank` and UI refresh succeed.
  - If `onWorkerReady()` throws, `attachWorkerHandlers` catches the error, calls `handleWorkerFatalError(err.message)`, and resolves `workerReadyResolve(false)`.
- **Timeout & Error Paths**:
  - On timeout (`timeoutMs`), `recoverWorker()` terminates the hung worker (`worker.terminate()`), increments `workerGeneration`, calls `handleWorkerFatalError("Worker khởi tạo quá thời gian chờ")`, and resolves `readyPromise(false)`.
  - On `data.type === "ERROR"`, `targetWorker.onerror`, `targetWorker.onmessageerror`, or synchronous constructor error, `handleWorkerFatalError` is invoked and `workerReadyResolve(false)` is resolved immediately.
- **UI Retention on Failure**:
  - `finally` only resets `isRecovering = false`, `recoveryPromise = null`, `workerReadyResolve = null`, and sets `btnRetry.disabled = false`.
  - `#btn-worker-retry` is hidden **only** when `readySuccess === true`. On `false`, `#btn-worker-retry` remains visible (`display = "inline-block"`, `disabled = false`).

---

## 2. Storage Hardening: Atomic Teach Count & `localSyncedTimestamp` Coherence

### Context & Root Cause Analysis
In [`webapp/js/storage.js`](file:///d:/viet/app/webapp/js/storage.js#L340-L357), `incrementTeachCount(profileId)` and `resetTeachCount(profileId)` perform a non-atomic `getProfile()` followed by `saveProfile(profile)` without `expectedUpdatedAt`:
1. If another tab updated `profile.data` between `getProfile` and `saveProfile`, the unconditioned `saveProfile` overwrites the newer bank bytes with stale data.
2. If another tab deleted the profile, `saveProfile` resurrects the deleted profile.
3. Because `saveProfile` increments `profile.updated_at` without updating `localSyncedTimestamp`, when `notifySampleTaught()` schedules `triggerSyncSave()` 2 seconds later, `syncAndSaveActiveProfile()` sees `currentProfile.updated_at > localSyncedTimestamp` and falsely triggers a redundant multi-tab merge on single-tab usage.

### Decision
- Execute `incrementTeachCount(profileId)` and `resetTeachCount(profileId)` inside a single `executeTransaction(db, PROFILES_STORE, "readwrite", ...)` transaction:
  - Read `store.get(profileId)` inside the transaction.
  - If `!existing`, do not call `store.put` (prevent resurrection) and return `0`.
  - Record `wasInSync = (localSyncedTimestamp > 0 && localSyncedTimestamp === existing.updated_at)`.
  - Update `existing.teach_count_since_backup` (`(existing.teach_count_since_backup || 0) + 1` or `0`) and monotonic timestamp `existing.updated_at = Math.max(Date.now(), (existing.updated_at || 0) + 1)` without modifying `existing.data`.
  - On transaction completion: if `wasInSync`, update `localSyncedTimestamp = existing.updated_at` so subsequent `syncAndSaveActiveProfile()` in the same tab does not trigger a false-positive merge; if `localSyncedTimestamp < prevUpdatedAt` (another tab had unwritten changes), preserve `localSyncedTimestamp` so `syncAndSaveActiveProfile()` still merges the other tab's `diskGzBytes`.

---

## 3. Seed Pipeline: Unified `SeedContext` & `Writer` Internal Isolation

### Context & Root Cause Analysis
1. In [`chuviettay/layout/engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py#L338-L382), `_layout_inlines()` called `self.wr.token(chunk)` and `self.wr.symbol(sym)` *before* computing `occ` from `self._doc_token_counts[(context_prefix, chunk)]`, and without passing `occ` or `context_prefix` to `Writer`.
2. In [`chuviettay/fidelity/engine.py`](file:///d:/viet/app/chuviettay/fidelity/engine.py#L102-L151), `FidelityLayoutEngine` counted `occ` in `block_token_counts` for `wscale_rng`, but called `self.wr.token(w_tok)` without passing `occ`, causing `Writer` to use its own document-wide `_token_counts`.
3. In [`chuviettay/model/writer.py`](file:///d:/viet/app/chuviettay/model/writer.py):
   - `_token_last` was keyed by `(self._current_tok, tag)` without `content_type`, leaking variant de-duplication state between `text`, `cell`, and `sym`.
   - `Writer.token()` calling `self.number(core)` (line 625) overwrote `self._current_tok` and `self._current_k`, corrupting the seed context for trailing punctuation in tokens like `"(123)"`.
   - `Writer.assemble_word()` (line 366) incremented `self._char_idx` inside `if self.J > 0:`, causing tone mark selection (`line 400`) to shift variants depending on whether `jitter == 0` or `jitter > 0`.

### Decision
1. Define immutable `SeedContext` in `chuviettay/model/rng.py`:
   ```python
   @dataclass(frozen=True, slots=True)
   class SeedContext:
       content_type: str        # "text", "cell", "sym", "math_inline", "math_block", "wgap", "tbl_border"
       element_id: str          # Token string, symbol, latex formula, or structural table ID
       occurrence: int = 0      # Occurrence index
       purpose: str = "variant" # "variant", "geom", "jitter", "dgap"
       sub_index: int = 0       # Character / digit / stroke index
   ```
   With helper properties:
   - `token_id -> str`: `f"{self.content_type}:{self.element_id}#{self.occurrence}"`
   - `with_purpose(purpose: str, sub_index: int = 0) -> SeedContext`
2. Unify execution order in `DocumentLayoutEngine` and `FidelityLayoutEngine`:
   - Compute `occ` and construct `ctx = SeedContext(content_type=context_prefix, element_id=chunk, occurrence=occ)` **before** calling `self.wr.token(chunk, context=ctx)` or `self.wr.symbol(sym, context=ctx)`.
   - Attach `token_id = ctx.token_id` and `occurrence = ctx.occurrence` to `RenderItem`, and use `ScopedRNG(self.effective_seed, "geom", ctx.token_id)` in `_render_text_line` and `FidelityLayoutEngine`.
3. Fix `Writer` internal state:
   - Scope `_token_last` by `(self._current_ctx_type, self._current_tok, tag)`.
   - Add `_preserve_context: bool = False` (or internal helper) to `Writer.number()` when invoked from `Writer.token()` so `self._current_tok`, `self._current_k`, and `self._current_ctx_type` of the enclosing token are preserved for trailing punctuation.
   - In `Writer.assemble_word()`, use the character loop index `idx` for `"jitter"` (`ScopedRNG(..., "jitter", idx)`) instead of incrementing `self._char_idx`.

---

## 4. Editing Invariance & Duplicate Content Alignment

### Context & Problem
- With `(content_type, element_id, occurrence)`, inserting any non-duplicate word/symbol/formula/table leaves all existing tokens' `(content_type, element_id, occurrence)` untouched.
- However, if a user inserts a **duplicate** word (e.g. inserting `"nay"` at the start of a document that already contains `"nay"`), a purely sequential counter assigns `occurrence = 0` to the new `"nay"` and shifts the old `"nay"` from `0` to `1`.

### Decision
Establish a clear two-tier Editing Invariance Architecture:
1. **Tier 1 — Stateless Render (Default `stable_variants=True`)**:
   - Uses sequential occurrence per `(content_type, element_id)` (or explicit `occurrence_overrides` / `stable_id` on IR nodes when present).
   - Preserves 100% backward compatibility with existing `RenderItem.token_id` format (`"text:alpha#0"`, `"sym:beta#0"`, `"cell:alpha#0"`) and `_doc_token_counts`.
2. **Tier 2 — Diff-Aligned / Persistent ID Editing (`align_document_seeds` & IR `stable_id`)**:
   - Add optional `stable_id: str | None = None` / `token_occurrences: dict[int, int] | None = None` support on Document IR blocks/inlines (`Paragraph`, `Text`, `Symbol`, `MathInline`, `MathBlock`, `Table`).
   - Provide `align_document_seeds(base_doc: Document, edited_doc: Document) -> Document` using `difflib.SequenceMatcher` (LCS) over the document's token/math/table stream:
     - Tokens/elements matched by LCS retain their exact original `occurrence` numbers from `base_doc`.
     - Newly inserted duplicate tokens/elements are assigned fresh occurrence numbers starting after the max occurrence of that `(content_type, element_id)` in `base_doc`.
   - This guarantees that even when duplicate words, duplicate formulas, or new tables/rows/cells are inserted before existing ones, every matched existing element preserves its exact `SeedContext` and stroke geometry!

---

## 5. Word Gaps (`wgap`), Math (`_scratch`), and Table Borders (`tbl_border`)

### Context & Problem
1. `wgap` previously used `ScopedRNG(seed, "wgap", prev_tok, tok_str)`, giving identical spacing to every occurrence of the same word pair.
2. `MathLayoutEngine.layout_lines()` reused a single `scratch = self._scratch()` instance across multiple `scratch.measure()` calls, mutating `scratch.writer._token_counts` and omitting `_token_last`.
3. Table borders used `ScopedRNG(seed, "tbl_border", total_tables, curr_row_idx)`, shifting border seeds whenever a table was inserted earlier.

### Decision
1. **Position-Aware Word Gaps**:
   - Derive `wgap` from adjacent token IDs: `ScopedRNG(self.effective_seed, "wgap", prev_token_id, curr_token_id)` in both `DocumentLayoutEngine` and `FidelityLayoutEngine`.
   - Repeated phrases at different positions (`("text:hôm#0", "text:nay#0")` vs `("text:hôm#1", "text:nay#1")`) get distinct natural spacing, while remaining 100% invariant when unrelated tokens are inserted before them.
2. **Stateless Math `_scratch()` Clones**:
   - `MathLayoutEngine._scratch()` copies `_token_counts`, `_token_last`, and `_current_ctx_type`, and creates a deterministic `random.Random(w.seed or 0)` when `stable_variants=True`.
   - In `layout_lines()`, each measurement probe calls `self._scratch().measure(...)` on a fresh clone so measurement probes never pollute each other or diverge from `self.measure(...)`.
   - When `stable_variants=True`, `MathLayoutEngine._m_SymbolNode` uses `self.writer.symbol(sym)` so multi-variant math symbols vary deterministically by occurrence (while keeping `self.bank.symbols[sym][0]` when `stable_variants=False` to preserve the `math` Golden Master).
3. **Structural Table & Cell Identity**:
   - Derive a stable `table_id` for each `Table`: use `block.stable_id` if set, otherwise compute a structural signature `f"tbl:{num_cols}:{first_row_sig}#{tbl_sig_occ}"`.
   - Derive table border seed via `ScopedRNG(self.effective_seed, "tbl_border", table_id, curr_row_idx)`. Inserting a different table earlier in the document does not alter `table_id` or border strokes of existing tables.

---

## 6. Canonical Key Encoding (`derive_seed` v2)

### Context & Problem
1. Previous `derive_seed` joined `map(str, keys)` with `\x00`, causing `1` (int) and `"1"` (str) to collide, and strings containing `\x00` to collide with multi-key tuples.
2. Packing `master_seed` or `int` keys as fixed 8-byte signed integers raises `OverflowError` when a 64-bit unsigned derived seed (`>= 2**63`, such as `math_seed`) is passed as `master_seed` into a child `Writer`, whereas unsigned 8-byte packing fails on negative seeds (`seed=-1`).
3. In Python, `isinstance(True, int)` is `True`, so `bool` must be checked before `int`.

### Decision
Implement canonical, overflow-safe, length-prefixed serialization in `derive_seed(master_seed: int, *keys: Any, version: str = "v2") -> int`:
- Domain header: `b"rng-v2\x00"`
- Each value (including `master_seed` and each item in `keys`) is encoded via `_encode_canonical_key(val)`:
  - `None`: `b"n\x00\x00\x00\x00"`
  - `bool`: `b"?\x00\x00\x00\x01\x01"` (for `True`) or `b"?\x00\x00\x00\x01\x00"` (for `False`)
  - `int` (and not `bool`): ASCII decimal bytes `raw = str(int(val)).encode("ascii")` -> `b"i" + len(raw).to_bytes(4, "big") + raw` (supports negative, 64-bit unsigned, and arbitrary-precision ints with zero overflow)
  - `str`: NFC-normalized UTF-8 bytes `raw = unicodedata.normalize("NFC", val).encode("utf-8")` -> `b"s" + len(raw).to_bytes(4, "big") + raw`
  - `bytes` / `bytearray`: `b"b" + len(val).to_bytes(4, "big") + bytes(val)`
  - `SeedContext`: encoded as tuple of its canonical fields `b"c" + count.to_bytes(4, "big") + ...`
  - `tuple` / `list`: `b"t" + len(val).to_bytes(4, "big") + b"".join(_encode_canonical_key(x) for x in val)`
- Hash with `hashlib.blake2b(payload, digest_size=8)` and convert via `int.from_bytes(..., "big")`.
- Preserve `version="v1"` fallback for legacy comparison if explicitly requested, while defaulting to `version="v2"`.
- Note on `tests/test_golden_master_real_path.py`: All 8 `GOLDEN_REAL` cases use `stable_variants=False` and remain 100% bit-exact. The single `test_real_path_stable_variants` test (which tests `stable_variants=True`) will have its expected `.xopp` hash updated to reflect the v2 canonical seed pipeline in Phase 3/4.
