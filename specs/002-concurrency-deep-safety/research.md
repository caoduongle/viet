# Research & Technical Decisions: Concurrency Deep Safety and Scalability Hardening

**Feature**: `002-concurrency-deep-safety` | **Date**: 2026-09-29

## 1. Concurrency Conflict Resolution (Lost-Update Prevention)

### Problem Statement
In `001-data-safety-hardening`, `Bank.save()` was hardened with cross-process `FileLock`, unique temporary files, `fsync`, and atomic `os.replace`. However, file locking only protected the write phase.
If Process A and Process B open the bank at snapshot $S_0$:
- Process A adds word "từ_A" and saves: on-disk file becomes $S_0 \cup \{\text{"từ\_A"}\}$.
- Process B adds word "từ_B" and saves: because Process B's in-memory bank still holds snapshot $S_0$, it writes $S_0 \cup \{\text{"từ\_B"}\}$, completely erasing "từ_A".

### Evaluated Alternatives
1. **Global Process Mutex (Read-Modify-Write lock across application lifespan)**:
   - *Pros*: Simple conceptually.
   - *Cons*: Holding a file lock while GUI is open prevents CLI or secondary instances from opening or using the bank. Deadlocks or lock starvation in interactive desktop apps. Rejected.
2. **Optimistic Versioning with Conflict Rejection**:
   - *Pros*: Standard in web apps; detects dirty writes.
   - *Cons*: Desktop users training words would see sudden "Save failed: file modified externally. Discard your changes?" popups. Poor desktop UX. Rejected.
3. **Transactional Reload-and-Merge under Save Lock (Selected)**:
   - *Pros*: Completely non-blocking during user thinking/writing time. Lock is held exclusively during the milliseconds-long `save()` operation.
   - *Mechanism*:
     1. Inside `Bank.save()`, acquire `FileLock(self.path + ".lock")`.
     2. Check if target file exists on disk. If so, read on-disk dictionary $D_{\text{disk}}$.
     3. Merge: For each word in $D_{\text{disk}}[\text{"words"}]$, compare samples against local $D_{\text{mem}}[\text{"words"}]$.
        - If word is missing in $D_{\text{mem}}$, copy it.
        - If word exists in both, append samples from $D_{\text{disk}}$ that do not match existing samples in $D_{\text{mem}}$ (using coordinate signature or tuple equality).
     4. Write the merged result to temporary file, `fsync`, atomically replace, and release lock.
   - *Outcome*: Both "từ_A" and "từ_B" are preserved without human intervention.

---

## 2. Deep Structural and Runtime Schema Validation

### Problem Statement
The initial schema validation in `bank_schema.py` checked high-level container types (`isinstance(d, dict)`, `isinstance(words, dict)`), but left stroke coordinates unvalidated. A corrupt file with odd-length coordinate lists (`[10.0, 20.0, 30.0]`), empty strokes (`[]`), or non-finite values (`NaN`, `Infinity`) passes `validate_bank_dict()` but crashes later in `composer.py` or `xopp.py`.
Additionally, `composer.py` directly indexes runtime metadata:
`bank.d["line"]`, `bank.d["width"]`, `bank.d["wgaps"]`, `bank.d["dgaps"]`, `bank.d["v"]`, `bank.d["x0"]`, `bank.d["ratio"]`.
If any key is missing, runtime crashes with `KeyError`.

### Technical Decision
1. **Deep Stroke Invariants**:
   - Every stroke `s` in a sample must be `list[float | int]`.
   - Length must be $\ge 2$ and even (`len(s) % 2 == 0`).
   - Every coordinate must be finite (`math.isfinite(coord)`).
   - Sample width `w` must be a positive number ($w > 0$) and finite.
2. **Metadata Key Completeness & Defaults**:
   - Define `REQUIRED_METADATA_KEYS = {"schema_version", "words", "line", "width", "wgaps", "dgaps", "v", "x0", "ratio"}`.
   - In `validate_bank_dict()`: Validate presence and numeric/list types of all metadata keys.
   - In `migrate_bank_dict()`: For legacy banks (v1 or unversioned) missing typographic keys, populate defaults from `chuviettay.config` (`DEFAULT_LINE_HEIGHT`, `DEFAULT_LINE_WIDTH`, etc.) rather than failing.

---

## 3. GitHub Actions Linux Release Packaging Bug

### Problem Statement
In `.github/workflows/ci.yml`:
```yaml
- name: Package Linux release
  run: |
    tar -czf ${{ matrix.archive_name }} -C dist hw_gui README.md LICENSE
```
Because `-C dist` changes the directory to `dist/`, `tar` looks for `README.md` and `LICENSE` inside `dist/`, where they do not exist.

### Technical Decision
Before invoking `tar`, copy root-level assets into `dist/`:
```yaml
cp README.md LICENSE dist/
tar -czf ${{ matrix.archive_name }} -C dist hw_gui README.md LICENSE
```
This ensures paths are resolved cleanly and consistently across both Linux and Windows jobs.

---

## 4. Uniform Persistence for Bank Creation

### Problem Statement
`Bank.create_empty(path)` previously performed a raw `gzip.open(path, "wt")` followed by `json.dump()`. It lacked `FileLock`, unique temporary file creation, `fsync`, and atomic `os.replace`.

### Technical Decision
Refactor `Bank.create_empty(path)` to delegate directly to `Bank.empty_dict()` and `Bank.save()`:
```python
@classmethod
def create_empty(cls, path: str | Path) -> Bank:
    bank = cls(path=path, empty=True)
    bank.save()
    return bank
```
This ensures new bank creation inherits the full durability, locking, and atomic replacement protections.

---

## 5. Scalable Incremental Indexing for Word Teaching

### Problem Statement
`AppController.teach_word()` called `Bank.add_sample()` followed by `Bank.rebuild()` and `Bank.save()`.
`Bank.rebuild()` recalculates token sets, spacing metrics, and bounding boxes across all words in the dictionary.
When the bank grows to 10,000+ words, teaching 50 words consecutively triggers 50 full-dictionary re-indexes, degrading responsiveness.

### Technical Decision
1. Add `Bank.add_sample_incremental(word: str, sample: dict)`:
   - Appends the sample to `self.d["words"][word]`.
   - Incrementally registers the word in `self.vocab` and token structures without scanning untouched words.
   - Executes `Bank.save()` which utilizes the reload-and-merge transactional lock.
2. Benchmarking test: Verify 50 sequential additions run in < 1.0 second on standard fixtures.

---

## 6. Resilient Logging State Contract

### Problem Statement
If both the primary application folder and the user application data directory are non-writable, `configure_logging()` falls through. Calling `log_path()` returns `DEFAULT_LOG_PATH`, leading UI error dialogs to claim logs were written to a file that does not exist.

### Technical Decision
1. Update `logging_setup.py`:
   - Initialize `_ACTIVE_LOG_PATH: str | None = None`.
   - If both file handlers raise `OSError`, configure a `logging.StreamHandler(sys.stderr)` and leave `_ACTIVE_LOG_PATH = None`.
   - Type hint `log_path() -> str | None`.
2. Update `app_window.py`:
   - Check `path = log_path()`. If `path` is not `None`, display "Chi tiết lỗi được ghi tại {path}".
   - If `None`, display "Không thể ghi file nhật ký (chế độ chỉ đọc)".

---

## 7. Historical Git Biometric Data Purge

### Problem Statement
Git commit history retains historical blobs for `chu_cua_ban.json.gz` and `tests/data/kho_mau_chup_lai.json.gz` from commits prior to `001-data-safety-hardening`.
Rewriting git history rewrites all past commit SHAs and requires `git push --force`. This must be handled safely as an administrative operation.

### Technical Decision
Create `scripts/purge_git_history.ps1` and `scripts/purge_git_history.sh`:
- Verifies that `git status --porcelain` is clean (no uncommitted changes).
- Verifies that `git-filter-repo` is installed (`pip install git-filter-repo`).
- Creates a local backup tag or branch `backup-pre-purge-<timestamp>`.
- Executes:
  ```bash
  git filter-repo --invert-paths \
    --path chu_cua_ban.json.gz \
    --path tests/data/kho_mau_chup_lai.json.gz \
    --force
  ```
- Outputs clear guidance on verifying the purge and force-pushing to remote.
