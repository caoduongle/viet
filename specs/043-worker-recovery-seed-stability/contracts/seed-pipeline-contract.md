# Contract: Render Seed Pipeline & Canonical Derivation (CTR-043-SEED-PIPELINE)

**Scope**: Cross-engine deterministic seed generation, unified context propagation, and editing invariance across [`chuviettay/model/rng.py`](file:///d:/viet/app/chuviettay/model/rng.py), [`chuviettay/model/writer.py`](file:///d:/viet/app/chuviettay/model/writer.py), [`chuviettay/layout/engine.py`](file:///d:/viet/app/chuviettay/layout/engine.py), [`chuviettay/layout/math_layout.py`](file:///d:/viet/app/chuviettay/layout/math_layout.py), and [`chuviettay/fidelity/engine.py`](file:///d:/viet/app/chuviettay/fidelity/engine.py).

---

## 1. Canonical Key Encoding (`derive_seed` v2)

### Interface
```python
def encode_canonical_key(val: Any) -> bytes:
    """Encodes a value into a typed, length-prefixed canonical byte representation."""

def derive_seed(master_seed: int, *keys: Any, version: str = "v2") -> int:
    """Derives a deterministic 64-bit unsigned integer from master_seed and keys.
    Version 'v2' enforces typed, length-prefixed canonical encoding:
    - Prepended with algorithm domain: b"rng-v2\\x00"
    - Tag b'n' (4B len 0) for None
    - Tag b'?' (4B len 1 + 0x01/0x00) for bool (checked BEFORE int)
    - Tag b'i' (4B len + ASCII decimal bytes) for int (safe for negative & >= 2**63)
    - Tag b's' (4B len + NFC-normalized UTF-8 bytes) for str
    - Tag b'b' (4B len + raw bytes) for bytes/bytearray
    - Tag b'c' (4B len 5 + recursive fields) for SeedContext
    - Tag b't' (4B len + recursive items) for tuple/list
    """
```

### Collision-Free & Overflow-Free Invariants
- For any distinct key sequences $K_1 \neq K_2$ (after Unicode NFC normalization on strings), $\text{Payload}(K_1) \neq \text{Payload}(K_2)$.
- `derive_seed(s, 1)`, `derive_seed(s, "1")`, and `derive_seed(s, True)` produce distinct non-colliding outputs.
- Null bytes (`\x00`) embedded in strings or bytes payloads never collide with key boundaries.
- Negative integers (`-1`) and unsigned 64-bit derived seeds (`>= 2**63`, e.g. `math_seed`) never raise `OverflowError`.

---

## 2. `SeedContext` Propagation & `Writer` Isolation

### Invariants
1. **Single Source of Truth**:
   - `DocumentLayoutEngine` and `FidelityLayoutEngine` construct `ctx = SeedContext(content_type=..., element_id=..., occurrence=...)` **before** invoking `Writer.token(tok, context=ctx)`, `Writer.symbol(sym, context=ctx)`, or `Writer.number(s, context=ctx)`.
   - Both `Writer` variant selection (`variant`, `jitter`, `dgap`) and layout engine geometry perturbations (`geom`, `wscale`) use the exact same `SeedContext` (`ctx.token_id == f"{ctx.content_type}:{ctx.element_id}#{ctx.occurrence}"`).
2. **Namespace & Call-Stack Isolation in `Writer`**:
   - `Writer._token_last` MUST be keyed by `(content_type, element_id, tag)` so `text`, `cell`, `sym`, `math_inline`, and `math_block` never share variant de-duplication state.
   - When `Writer.token()` delegates core digits to `Writer.number()`, `Writer.number(..., _preserve_context=True)` MUST NOT overwrite the enclosing token's `_current_ctx_type`, `_current_tok`, or `_current_k`.
   - In `Writer.assemble_word()`, character advance jitter (`self.J > 0`) MUST use the explicit character loop index `idx` rather than incrementing `self._char_idx`, so tone mark selection is invariant to `jitter`.
3. **Position-Aware Word Gaps (`wgap`)**:
   - In stable mode, word gaps between adjacent tokens $T_{\text{prev}}$ and $T_{\text{curr}}$ MUST be derived via:
     `ScopedRNG(master_seed, "wgap", prev_item.token_id, curr_item.token_id)`
     (using the string `token_id` such as `"text:hôm#0"` and `"text:nay#0"`, never Python's memory-address `id()`).
4. **Math & Table Determinism**:
   - `MathLayoutEngine._scratch()` MUST clone `_token_counts`, `_token_last`, and `_current_ctx_type`, and `layout_lines()` MUST use a fresh `_scratch()` clone per measurement probe so measurement and rendering derive identical seeds.
   - Table borders derive seeds via `ScopedRNG(master_seed, "tbl_border", table_id, curr_row_idx)` where `table_id` is derived from `block.stable_id` or structural table signature `(num_cols, first_row_sig, sig_occ)` rather than global `total_tables`.
5. **Editing Invariance (Including Duplicate Insertions)**:
   - Stateless renders track occurrences per `(content_type, element_id)`.
   - `align_document_seeds(base_doc, edited_doc)` (using `difflib.SequenceMatcher` LCS) and optional `stable_id` on IR nodes preserve the exact original `occurrence` of matched tokens, formulas, and tables when duplicate content is inserted earlier in the document.

---

## 3. Backward Compatibility & Baseline Protection
- When `stable_variants=False` (default):
  - No `ScopedRNG` or `derive_seed` calls occur in the active render path.
  - 100% of the 8 `GOLDEN_REAL` Golden Master SHA-256 test hashes (`.xopp` and `_thieu.xopp`) in CPython and Pyodide remain strictly unchanged.
