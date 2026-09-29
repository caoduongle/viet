# Technical Research: Scalability, Correctness, and CI Hardening

**Feature**: `003-scalability-correctness-hardening`
**Date**: 2026-09-29
**Status**: Completed

## 1. CI Windows 3.10 & Tk/Tcl Runtime Isolation

### Context & Problem
In GitHub Actions on Windows with Python 3.10, the pre-installed Tcl/Tk runtime is incomplete: `init.tcl` or `listbox.tcl` is missing in `hostedtoolcache/windows/Python/3.10.11/x64/tcl/tcl8.6/`.
When `tests/test_gui.py` runs, `tk_root` fixture skips in one test, but another fixture `app` calls `MainWindow(AppController(...))` which invokes `tk.Tk.__init__()` directly without catching `_tkinter.TclError`, causing pytest to fail with `ERROR at setup of test_nap_tu_thong_dung`.

### Decision
1. **Fixture-Level Guarding**: In `tests/conftest.py` and `tests/test_gui.py`, all instantiations of `tk.Tk`, `MainWindow`, and `WordCanvas` must catch `_tkinter.TclError` (and missing Tcl scripts) and call `pytest.skip("Tkinter/Tcl runtime incomplete or unavailable")`.
2. **Pre-flight Tk Environment Probe**: Add a session-scoped fixture or utility `require_tk()` that checks if `tk.Tk()` can be initialized cleanly. If not, GUI tests are skipped uniformly across the module.
3. **Pytest Marker (`gui`)**: Add `@pytest.mark.gui` to GUI tests in `tests/test_gui.py` and `tests/test_word_canvas.py` so they can be filtered if needed (`pytest -m "not gui"`).
4. **CI Workflow Parity**: Expand `.github/workflows/ci.yml` matrix to test Python 3.10, 3.11, 3.12, 3.13. On Windows 3.10, the test suite executes all core domain, schema, and persistence tests cleanly, while GUI tests skip safely if Tcl runtime is broken.

### Alternatives Considered
- *Attempting to patch Tcl files on the runner*: Fragile, depends on runner paths and requires administrative downloads during CI runs.
- *Removing Python 3.10 from CI*: Violates the project constitution and `README.md` commitment to Python 3.10+.

---

## 2. Incremental Indexing Parity & Raw Marks Preservation

### Context & Problem
`Bank.rebuild()` calculates percentiles from all harvested marks across `self.words`.
`Bank.add_sample_incremental()` was filtering `self.marks[T]` directly in place and discarding outlier marks. When subsequent samples were added and shifted the percentile cutoff, previously discarded marks could never be restored, causing `marks` to diverge permanently from `rebuild()`. Additionally, sorting `self.marks[T]` on every added mark caused $O(M \log M)$ complexity per addition.

### Decision
1. **Separation of Raw vs Query Marks**:
   - `self._raw_marks: dict[str, list[dict]]`: Stores *all* harvested tone marks unconditionally without dropping outliers.
   - `self.marks: dict[str, list[dict]]`: The queryable index containing filtered marks (between 10th and 90th percentiles when $\ge 10$ marks exist).
2. **Deterministic Filter Synchronization**:
   - When a sample is added incrementally via `add_sample_incremental()`, the harvested mark is appended to `self._raw_marks[T]` in $O(1)$.
   - `self.marks[T]` is re-filtered from `self._raw_marks[T]`. Because `self._raw_marks[T]` contains every valid harvested mark, `self.marks` is always mathematically identical to `rebuild()`.
3. **Algorithmic Complexity**:
   - Appending to `words`, `tl`, and `_raw_marks` is strictly $O(1)$.
   - Percentile filtering is isolated strictly to the affected tone `T` (not all 5 tones), avoiding full-collection rebuilds.

### Alternatives Considered
- *Maintaining sorted lists with bisect*: Complicates percentile range slicing and does not prevent the data loss issue if outliers are discarded.
- *Running full rebuild on every word*: $O(N)$ on total database size, unusable for large banks.

---

## 3. Persistent Deletion Tombstones Across Concurrent Sessions

### Context & Problem
In multi-process usage (e.g. GUI and CLI running concurrently):
- Process A deletes word "xin" and saves.
- Process B holds an older in-memory snapshot with "xin", adds sample "bbb", and saves.
- Process B reads disk (which lacks "xin"), merges disk into its local snapshot `base` (which has "xin"), and writes "xin" back to disk.
- Result: "xin" is resurrected because Process A's `_deleted_words` set was ephemeral.

### Decision
1. **Persistent Tombstones in Bank Data**:
   - Add `"tombstones": dict[str, float]` to the bank JSON structure, storing `{word: timestamp_deleted}`.
   - When `drop(word)` is called, the word is removed from `words` and added to `tombstones` with current UTC timestamp.
2. **Merge Semantics with Tombstones**:
   - During `merge_bank_dicts(base, disk)`:
     - Combine tombstones: `merged_tombstones = {**disk_tombstones, **base_tombstones}`.
     - For any word present in `merged_tombstones`:
       - If the word exists in `base.words` or `disk.words`, check if any sample was added *after* the tombstone timestamp. If not, the word is removed from `words`.
     - Persist `tombstones` back to the bank file.
3. **Explicit Re-Teaching / Revocation**:
   - When `add_sample(word, ...)` is called, any existing tombstone for `word` is deleted (`tombstones.pop(word, None)`), allowing the word to be re-taught cleanly.
4. **Backward Compatibility**:
   - If a bank file has no `tombstones` field (schema v1 or v2), it defaults to `{}`. No breaking migration required.

### Alternatives Considered
- *Full generation vector clocks*: Adds excessive complexity (violates KISS principle) for a local single-user multi-tool desktop setup.
- *Locking the bank file permanently across the entire session*: Causes lock starvation and crashes when two windows are open simultaneously.

---

## 4. Scalable Persistence Architecture

### Context & Problem
`AppController.teach_word()` currently calls `bank.add_sample_incremental()` followed immediately by `bank.save()`.
In `bank.save()`:
- The entire file is decompressed and re-read from disk.
- `merge_bank_dicts()` is called.
- `rebuild()` is called, completely wiping out the performance advantage of `add_sample_incremental()`.
- The entire dataset is JSON-serialized and gzip-compressed at `compresslevel=9`.
On banks with 10,000+ samples, this causes multi-second freezes on every taught word.

### Decision
1. **Mtime & Size Cache Check**:
   - Track `_last_synced_mtime` and `_last_synced_size` of the file on disk.
   - When `save()` acquires the lock:
     - Check `os.path.getmtime(self.path)` and `os.path.getsize(self.path)`.
     - If both match `_last_synced_mtime` and `_last_synced_size`, **NO external process has modified the file**.
     - We can safely SKIP disk re-read, SKIP `load_and_validate`, SKIP `merge_bank_dicts`, and SKIP `rebuild()`!
     - The in-memory bank with its already incremental index is directly saved.
2. **Optimized Compression Level**:
   - Use `compresslevel=1` (or `6`) instead of `9` during interactive saves. Benchmarks show `compresslevel=1` achieves 85-90% of max compression ratio at 5x to 8x the speed.
3. **Avoid Rebuild on Merge when Unmodified**:
   - If reload from disk occurs, only rebuild if external changes actually added or deleted words.

### Alternatives Considered
- *SQLite database backend*: Would require complete rewrite of persistence and breaks compatibility with existing `.json.gz` tools.
- *Append-only journal log*: More complex, requires compaction worker and alters file format.

---

## 5. Deep Schema Invariants: Tone Metadata & Pen Attributes

### Context & Problem
`validate_sample()` checked stroke coordinate parity and positive width, but did not check `ti`, `vi`, or `T`.
- If `ti >= len(s)` or `ti < -1`, calling `inst["s"][ti]` in `_harvest` crashes with `IndexError`.
- If `vi < -1`, invalid.
- If `T` is not in Vietnamese tones, invalid.
- `pen` attributes were only checked for key existence, allowing empty tool strings or invalid color codes to crash downstream SVG/XOPP generators.

### Decision
1. **Sample Invariants in `validate_sample()`**:
   - `ti`: `isinstance(ti, int)` and `-1 <= ti < len(item["s"])`.
   - `vi`: `isinstance(vi, int)` and `vi >= -1`. If `label` provided and `T` is present, `vi < len(label)`.
   - `T`: `isinstance(T, str)`. If non-empty, `T in TONES`.
2. **Pen Invariants in `validate_bank_dict()`**:
   - `pen["tool"]`: `isinstance(tool, str)` and `len(tool.strip()) > 0`.
   - `pen["color"]`: matches `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$`.
   - `pen["width"]`: numeric float $> 0$ and finite.

---

## 6. Sample Identity Contract for Merging

### Context & Problem
`_stroke_signature(inst)` used only rounded stroke coordinates `s`. If two samples had the same strokes but different `w` (width) or `T` (tone mark), they were treated as identical duplicates.

### Decision
- **Unified Sample Signature**:
  ```python
  def _sample_signature(inst: dict) -> tuple:
      strokes = tuple(tuple(round(float(c), 2) for c in s) for s in inst.get("s", []))
      w = round(float(inst.get("w", 0.0)), 2)
      T = inst.get("T", "")
      vi = int(inst.get("vi", -1))
      ti = int(inst.get("ti", -1))
      return (strokes, w, T, vi, ti)
  ```
- Samples are considered identical duplicates only when both geometry and metadata match.

---

## 7. Safe Git History Purge Procedures

### Context & Problem
`scripts/purge_git_history.ps1` and `.sh` created an in-tree backup branch `backup-pre-purge-*` right before invoking `git filter-repo`.
However, `git-filter-repo` rewrites refs across all local branches/tags and removes remotes, defeating the purpose of an in-tree backup.

### Decision
- Update purge scripts to:
  1. Mandate or automate creating an external backup bundle: `git bundle create ../viet-pre-purge.bundle --all`.
  2. Provide clear instructions for running in a fresh isolated clone (`git clone --no-local . ../viet-purge-clean`).
  3. Validate post-purge history with `git log --all -- "chu_cua_ban.json.gz"` before recommending force push.
