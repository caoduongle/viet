# Research: Concurrency Data Integrity, Tombstone Versioning, and Robust Persistence

**Feature**: 004-concurrency-data-integrity | **Date**: 2026-09-29

---

## R1: Safe Save Abort on Corrupt Disk File (FR-001)

### Decision
When `load_and_validate()` raises any exception during the merge path of `Bank.save()`, abort immediately: delete the temporary file via `os.unlink(tmp)`, and re-raise the exception as-is (all are `BankError` subclasses or `OSError`). Add a `force_overwrite: bool = False` parameter to `Bank.save()` that, when `True`, skips the merge entirely and writes in-memory state directly.

### Rationale
The current code at `bank.py` L302–309 catches all merge exceptions, logs a warning, and falls through to `os.replace()`. This converts a recoverable read error into permanent data loss. The fix is minimal: replace the `except` block's fall-through with cleanup + re-raise.

### Alternatives Considered
1. **Auto-backup before overwrite**: Creates a `.bak` copy of the corrupt file before overwriting. Rejected — adds I/O complexity, doesn't solve the core problem (user still loses data silently), and violates KISS.
2. **Return error code instead of raising**: Rejected — Python convention is exceptions for exceptional situations; callers already expect `BankError`.
3. **Interactive prompt before overwrite**: Rejected — `save()` is called from both GUI and CLI contexts; adding interactive I/O to a model method violates MVC separation.

---

## R2: Generation-Aware Tombstone Schema (FR-002, FR-003)

### Decision
Extend tombstone values from scalar `float` timestamps to structured records: `{"deleted_at": float, "generation": int}`. The `generation` field is a monotonically increasing integer per bank instance, incremented on each mutation (add/delete). Sample additions in `add_sample()` record `_session_gen` (the generation at time of addition) so that `merge_bank_dicts()` can compare sample generation against tombstone generation to determine staleness.

**Backward compatibility**: `validate_bank_dict()` accepts both legacy scalar `float` timestamps and structured `dict` tombstone records. On load, legacy scalars are normalized to `{"deleted_at": float, "generation": 0}` during migration.

**Staleness rule**: During merge, a sample addition from Process B is considered stale if `B._session_start_gen <= tombstone.generation`. A deliberate re-teaching in an active session sets `_readded_words` with the current session generation, which is always greater than any tombstone generation from the same or earlier session.

### Rationale
Pure timestamps (`time.time()`) have resolution issues on fast machines and don't capture causal ordering. A generation counter provides a lightweight, monotonic ordering that is trivially comparable. The structured dict format is forward-compatible and self-documenting.

### Alternatives Considered
1. **UUID per sample**: Rejected — excessive storage overhead for a single-file JSON bank; doesn't solve ordering problem.
2. **Vector clocks**: Rejected — overkill for a 2-process desktop app; violates KISS/YAGNI.
3. **Timestamp-only (no generation)**: Rejected — `time.time()` resolution on Windows is ~15ms; two rapid operations in the same tick are indistinguishable. Generation counter is deterministic.
4. **Lamport timestamps**: Considered viable but generation counter is simpler and sufficient for this use case.

### Schema Migration Strategy
- **Schema version**: Remains at 2 (tombstone format is a sub-field evolution, not a top-level schema change).
- **On load**: `validate_bank_dict()` normalizes legacy `float` tombstones to `{"deleted_at": float, "generation": 0}` in-memory. No migration step needed — normalization happens transparently.
- **On save**: Always writes structured tombstone records.
- **Compatibility**: Older code that reads `tombstones[word]` as a float will fail on the structured dict. This is acceptable because feature 003 already introduced tombstones and the codebase is single-developer.

---

## R3: Multi-Process Concurrency Testing (FR-007)

### Decision
Use `multiprocessing.Process` with `multiprocessing.Barrier` for synchronization in concurrency tests. Each worker process imports `Bank`, performs operations, and writes results to a shared `multiprocessing.Queue`. The parent process collects results and asserts on the final bank state.

**Platform considerations**:
- Windows uses `spawn` start method (no `fork`), so all worker functions must be importable top-level functions or use `subprocess` with a helper script.
- `FileLock` uses `msvcrt.locking` on Windows which operates at the OS level across processes.

### Rationale
`ThreadPoolExecutor` shares GIL, memory, and file descriptors — it cannot faithfully test `FileLock` behavior. True OS processes with separate memory spaces are required to validate cross-process locking.

### Alternatives Considered
1. **`subprocess.run` with helper scripts**: Viable but harder to synchronize timing; `multiprocessing.Barrier` provides precise coordination.
2. **`ProcessPoolExecutor`**: Simpler API but less control over process lifecycle and synchronization points.
3. **Docker containers**: Rejected — extreme overkill for a desktop app test; violates KISS.

---

## R4: Large-Bank Benchmark Design (FR-008)

### Decision
Create a parametric benchmark test that generates synthetic banks at 1,000 / 5,000 / 10,000 sample counts, measures 20 consecutive `add_sample_incremental()` + `save()` operations, and records per-word latency. Use `time.perf_counter()` for high-resolution timing. Assert sub-second per-word latency for the 5,000-sample tier.

The benchmark uses deterministic synthetic data generation (seeded RNG) for reproducibility. Results are printed to stdout (captured by pytest) rather than written to external files.

### Rationale
The existing benchmark (`test_sequential_teach_benchmark_with_tones`) only tests 100 words / 20 saves. Scaling to 5,000+ samples validates the O(N) gzip compression claim and establishes empirical baselines.

### Alternatives Considered
1. **`pytest-benchmark`**: Provides statistical analysis but adds an external dependency; rejected per YAGNI.
2. **External profiling (cProfile)**: Useful for debugging but not suitable as an automated regression test.

---

## R5: Efficient Percentile Maintenance (FR-006)

### Decision
Replace four independent `sorted()` calls in `_refresh_tone_marks()` with a single-sort approach: sort `lst` once by `dy`, extract 10th/90th percentile bounds, then filter. For `dx`, use the same approach. Total: 2 sorts instead of 4, and the sorts operate on the same list object rather than creating generator expressions.

Additionally, maintain sorted auxiliary lists `_sorted_dy[T]` and `_sorted_dx[T]` that use `bisect.insort()` for O(log M) insertion on incremental additions, avoiding full re-sorts entirely during `add_sample_incremental()`.

### Rationale
`bisect.insort()` is O(log M) for insertion into a sorted list, compared to O(M log M) for full re-sort. This is the stdlib solution — no external dependencies. The percentile bounds are then O(1) index lookups.

### Alternatives Considered
1. **SortedList from `sortedcontainers`**: O(log M) insertion with cleaner API, but adds external dependency; rejected per constitution.
2. **Approximate percentiles (reservoir sampling)**: Rejected — exact percentile matching against `rebuild()` is a spec requirement.
3. **Skip re-sorting if count unchanged**: Doesn't help — count always increases during incremental addition.

---

## R6: `drop()` Index Pruning (FR-004)

### Decision
In `Bank.drop(word)`, after popping from `self.words`:
1. Compute `key = strip_tone(word)` and remove `(word, ...)` entries from `self.tl[key]`. If `self.tl[key]` becomes empty, delete the key.
2. Determine tone `T` from the word. If `T` exists, remove harvested marks originating from `word` from `self._raw_marks[T]`.
3. Call `self._refresh_tone_marks(T)` to rebuild filtered `self.marks[T]`.

**Challenge**: `_raw_marks` items are anonymous dicts (`{"s": ..., "dx": ..., "dy": ...}`) with no originating word identifier. To enable selective removal, extend the mark dict to include `"_src": word` (private field, stripped on serialization). Alternatively, rebuild `_raw_marks[T]` from remaining words after drop.

**Chosen approach**: Add `"_src": label` to mark dicts in `_harvest()`. In `drop()`, filter `_raw_marks[T]` to remove marks where `_src == word`. The `_src` field is transient (in-memory only, never serialized).

### Rationale
Full `rebuild()` after every `drop()` is O(N) and defeats the purpose of incremental indexing. Selective pruning with `_src` tracking is O(M) where M is marks for the tone, which is typically small.

### Alternatives Considered
1. **Call `rebuild()` after `drop()`**: Correct but O(N); rejected for performance.
2. **Lazy invalidation flag**: Mark indexes as dirty and defer cleanup to next `save()`. Rejected — `can()` would return stale results.

---

## R7: Dictionary Aliasing Fix in `merge_bank_dicts()` (FR-005)

### Decision
After `merge_bank_dicts()` returns in `Bank.save()`, re-bind `self._tombstones = self.d["tombstones"]` to restore reference identity. Additionally, change `merge_bank_dicts()` to update `base["tombstones"]` in-place when possible:
```python
base["tombstones"].clear()
base["tombstones"].update(merged_tombstones)
```

### Rationale
In-place update preserves reference identity between `self._tombstones` and `self.d["tombstones"]`. The re-bind after merge is a safety net. Both approaches are O(T) where T is tombstone count.

### Alternatives Considered
1. **Property-based access (`@property tombstones`)**: Rejected — adds indirection for a simple fix; KISS.
2. **Remove `_tombstones` cache entirely**: Rejected — direct dict access `self.d["tombstones"]` is verbose and error-prone.

---

## R8: Git History Purge Script Update (FR-009)

### Decision
Update `scripts/purge_git_history.ps1` and `.sh` to print `git push --force --mirror origin` instead of `git push --force --all origin`. Add a pre-push verification step that checks `git log --all -- <sensitive-files>` returns empty before recommending the push.

### Rationale
`--force --all` only pushes branches, not tags or other refs. `--force --mirror` ensures all refs (branches, tags, notes) are synchronized, preventing dangling historical refs from retaining sensitive blobs on the remote.

### Alternatives Considered
1. **`git push --force --all --tags`**: Covers branches and tags but misses notes and other refs.
2. **Automated push in script**: Rejected — destructive remote operation should always require manual confirmation.

---

## R9: CI Ruff Integration (FR-010)

### Decision
Add a dedicated `lint` job to `.github/workflows/ci.yml` that runs `ruff check .` on a single Python version (3.12) and single OS (Ubuntu). Place it before the test matrix so lint failures fail fast.

### Rationale
Running ruff on every matrix combination is wasteful — lint results are platform-independent. A single lint job provides fast feedback without multiplying CI minutes.

### Alternatives Considered
1. **Pre-commit hook only**: Rejected — doesn't enforce in CI; contributors can skip hooks.
2. **Ruff in every test job**: Rejected — wasteful duplication.
