# Contract: Scalable Atomic Persistence

**Component**: `chuviettay.model.bank.Bank`
**Status**: Active

## 1. Overview
This contract governs how handwriting profiles are read from and written to physical storage. It guarantees atomic durability, cross-process safety, and scalable write performance on large banks.

## 2. Invariants & Guarantees

### 2.1 Atomic Replacement
- Files MUST be written to a unique temporary file (`.bank_*.tmp`) in the same directory as the target path.
- Temporary files MUST be flushed and synchronized to physical disk using `os.fsync()` before renaming.
- Renaming to the final destination MUST be executed using `os.replace()`.
- On POSIX platforms, the parent directory MUST be synchronized via `os.fsync()` after replacement.

### 2.2 External Modification Check (Fast Path)
- `Bank` tracks `_last_synced_mtime: float` and `_last_synced_size: int`.
- Inside the lock in `Bank.save()`:
  - If `os.path.exists(self.path)`:
    - If `mtime == _last_synced_mtime` and `size == _last_synced_size`:
      - **Fast path**: No external modifications. Skip `load_and_validate`, skip `merge_bank_dicts`, skip `rebuild`.
    - Else:
      - **Merge path**: External modifications detected. Read disk file, merge changes, update indexes.
  - Write temporary file, fsync, replace.
  - Update `_last_synced_mtime` and `_last_synced_size` from newly replaced file.

### 2.3 Interactive Save Compression
- Default compression level for interactive saves (`teach_word()`): `compresslevel=1` (or `6`) to ensure sub-second latency on large profiles while preserving gzip format compatibility.

## 3. Public Methods

```python
class Bank:
    _last_synced_mtime: float
    _last_synced_size: int

    def save(self, compresslevel: int = 1) -> None:
        """Persist bank dictionary atomically.
        Uses mtime/size cache check to skip unnecessary disk re-reads and full rebuilds."""
        ...
```
