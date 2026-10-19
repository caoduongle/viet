# Research & Architectural Decisions: Worker and Seed Integrity Hardening

**Feature**: `specs/044-worker-and-seed-integrity`
**Date**: 2026-10-18
**Status**: Completed

## 1. Context-Bound RNG Namespace Isolation (`Writer` & `ScopedRNG`)

### Problem
In commit `c6bc265`, `Writer.pick()`, `Writer.assemble_word()`, and `Writer._resolve_dgap()` received `_current_ctx_type` (e.g. `"text"`, `"cell"`, `"sym"`), but when instantiating `ScopedRNG`:
- `Writer.pick()`: `ScopedRNG(master_seed, "tok", self._current_tok, self._current_k, "variant", tag, char_idx)`
- `Writer.assemble_word()`: `ScopedRNG(master_seed, "tok", self._current_tok, self._current_k, "jitter", idx)`
- `Writer._resolve_dgap()`: `ScopedRNG(master_seed, "tok", self._current_tok, self._current_k, "dgap", digit_idx)`

All three calls hardcoded `"tok"` as the domain prefix instead of `self._current_ctx_type` or `self._current_context.content_type`. As a consequence, a word with `occurrence = 0` in running text (`content_type = "text"`) and the exact same word with `occurrence = 0` in a table cell (`content_type = "cell"`) derived identical sub-seeds for their variants and jitter.

### Decision
1. In `Writer.pick()`:
   Derive sub-seeds using the full canonical context:
   `ctx_type = getattr(self, "_current_ctx_type", "text")`
   `scoped_rng = ScopedRNG(master_seed, ctx_type, self._current_tok, self._current_k, "variant", tag, char_idx)`
2. In `Writer.assemble_word()`:
   `scoped_rng = ScopedRNG(master_seed, ctx_type, self._current_tok, self._current_k, "jitter", idx)`
3. In `Writer._resolve_dgap()`:
   `rnd = ScopedRNG(master_seed, ctx_type, self._current_tok, self._current_k, "dgap", digit_idx)`
4. Ensure `Writer.token()`, `Writer.word()`, `Writer.symbol()`, and `Writer.number()` consistently set `self._current_ctx_type = context.content_type if context else default_prefix`.
5. Rationale: Passing `ctx_type` ensures that distinct content types are 100% mathematically orthogonal in `blake2b` hashing, preventing cross-domain variant synchronization.

---

## 2. Worker Lifecycle & READY Timeout Disaggregation (`webapp/js/app.js`)

### Problem
In `recoverWorker()`:
```javascript
timer = setTimeout(() => { ... resFn(false); }, timeoutMs);
```
This single 10-second `timer` spanned:
1. Worker script loading and Pyodide initialization
2. Waiting for `data.type === "READY"`
3. IndexedDB profile loading via `storage.listProfiles()` and `storage.getProfile()`
4. Sending `load_bank` over postMessage and decompressing the gzip bank
5. Refreshing the DOM view and quota checking

If the bank gzip file is large or IndexedDB is contended, `onWorkerReady()` could take longer than 10 seconds. The timeout fired, terminated the newly created and functioning Worker, reported a fatal error, and resolved the promise with `false`.

### Decision
1. **Disaggregate Timeouts**:
   - `readyTimer`: Only guards the initial handshake from worker instantiation until `data.type === "READY"` (default 15,000ms).
   - Once `data.type === "READY"` is received, immediately clear `readyTimer`:
     ```javascript
     if (readyTimer) {
       clearTimeout(readyTimer);
       readyTimer = null;
     }
     ```
   - `onWorkerReady()` execution is then allowed to perform `load_bank` under its own per-request timeout (`sendWorkerMessage("load_bank", ..., 60000)` already defaults to 60,000ms).
2. **Generation Pinning**:
   - Each `recoverWorker()` invocation captures `const activeGen = ++workerGeneration;`.
   - `onWorkerReady()` captures `activeGen` and verifies `if (activeGen !== workerGeneration) return;` at every async step.
   - Late responses or errors from stale workers are completely ignored.
3. **Resilient DOM Listener Flagging**:
   - `isDomListenersAttached` must only be set to `true` AFTER all synchronous/asynchronous setup in the one-time DOM listener block has successfully executed.
   - If an error occurs during listener initialization (e.g. `teachController.init()` fails), `isDomListenersAttached` is reset to `false` in a `catch` block so that subsequent recovery attempts will properly re-attach all listeners.

---

## 3. Recursive Document IR Alignment (`align_document_seeds`)

### Problem
In `chuviettay/document/ir.py`, `extract_doc_elements(doc)` iterated over top-level blocks and matched `Paragraph`, `Heading`, `MathBlock`, `Table`. It did NOT inspect:
- `ListBlock`: contains `items: list[ListItem]`. Each `ListItem` contains `inlines: list[Inline]` or `blocks: list[Block]`.
- As a result, list items were completely skipped during LCS alignment. When an item was prepended to a list, all subsequent items in the edited document fell back to naive sequential counts (`_doc_token_counts`), shifting their seeds and changing existing stroke shapes.

### Decision
1. Update `extract_doc_elements(doc)` to handle `ListBlock` recursively:
   ```python
   def _extract_blocks(blocks, counts, elements, context_prefix="text"):
       for block in blocks:
           if isinstance(block, (Paragraph, Heading)):
               _extract_inlines(block.inlines, counts, elements, context_prefix=context_prefix)
           elif isinstance(block, ListBlock):
               for item_blocks in block.items:
                   _extract_blocks(item_blocks, counts, elements, context_prefix="text")
           elif isinstance(block, Table):
               ...
   ```
2. When reconstructing `assigned_occs`, map `assigned_occs` back to `Text` nodes inside nested `Paragraph` inlines within list items.
3. Rationale: Ensures list content enjoys the exact same LCS alignment guarantees as standard paragraphs and tables.

---

## 4. Chunked Token Indexing Synchronization

### Problem
In `chuviettay/layout/engine.py` (`_layout_inlines`):
```python
chunks = _split_token(...) if ... else [tok]
for chunk in chunks:
    if inline_tok_idx < len(inline.token_occurrences):
        occ = inline.token_occurrences[inline_tok_idx]
    ...
    inline_tok_idx += 1
```
`inline.token_occurrences` is generated per *word/token* in `extract_doc_elements`. When a long token is split into multiple chunks (e.g. 2 chunks) due to page or cell width, `inline_tok_idx` increments for each chunk. For the second chunk, it consumes `token_occurrences[1]`, causing every subsequent token in the paragraph to have its occurrence shifted by +1!

### Decision
1. `inline_tok_idx` represents the original token index in the paragraph (`tok_idx`).
2. Loop over original tokens first. For a token with index `tok_idx`:
   - Retrieve `occ = inline.token_occurrences[tok_idx]` if available, else from `_doc_token_counts`.
   - If `tok` splits into `chunks`:
     - Each chunk `c_i` (index `0 .. len(chunks)-1`) uses the parent token's `occ`.
     - `ctx = SeedContext(content_type=context_prefix, element_id=chunk, occurrence=occ, sub_index=c_i)`.
   - `tok_idx` increments once per *original token*, not per chunk.
3. Rationale: Eliminates all occurrence counter drift for subsequent tokens when long words are hyphenated or wrapped.

---

## 5. Strict Canonical Key Encoding (`encode_canonical_key`)

### Problem
In `chuviettay/model/rng.py`:
```python
payload = unicodedata.normalize("NFC", str(val)).encode("utf-8")
return b"s" + struct.pack(">I", len(payload)) + payload
```
Unrecognized types (e.g. `set`, `dict`, arbitrary classes) were silently converted via `str(val)` into `b's'` (string) tags. This violated CTR-043-SEED-PIPELINE and created collision hazards between custom objects and strings.

### Decision
1. Remove the fallback `str(val)`.
2. Raise `TypeError(f"Unsupported key type for canonical encoding: {type(val).__name__}")` if `val` is not an instance of `(NoneType, bool, int, float, str, bytes, bytearray, SeedContext, tuple, list)`.
3. Add unit test vectors verifying that invalid types (`{"a": 1}`, `{"set_item"}`, `object()`) explicitly raise `TypeError`.
