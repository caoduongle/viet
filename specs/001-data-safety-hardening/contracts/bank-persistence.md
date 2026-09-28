# Contract: Atomic Bank Persistence API

**Module**: `chuviettay/model/bank.py` (method `Bank.save()`)

## Public Method

### `Bank.save() -> None`

Persists the current bank state to disk with full durability guarantees.

**Raises**:
- `RuntimeError` — If the file lock cannot be acquired within timeout (another process holds it).
- `OSError` — If disk write fails.

**Behavior (sequential steps)**:

1. **Acquire file lock** on `{bank_path}.lock` with 10-second timeout.
2. **Set `schema_version`** to `CURRENT_VERSION` in `self.d`.
3. **Create unique temp file** in the same directory as the bank file (using `tempfile.mkstemp`).
4. **Write** gzip-compressed JSON to the temp file.
5. **Close gzip stream**, then **flush** and **fsync** the raw file descriptor.
6. **Atomic replace**: `os.replace(tmp_path, self.path)`.
7. **fsync parent directory** (POSIX only, skip on Windows).
8. **Release file lock**.
9. **Cleanup**: On any error, remove the temp file and re-raise.

**Invariants**:
- The target bank file is never in a partially-written state.
- Two processes calling `save()` simultaneously are serialized via the lock.
- After `save()` returns, data is committed to physical storage.

---

## Lock File Convention

- Lock file path: `{bank_path}.lock` (e.g., `chu_cua_ban.json.gz.lock`)
- Lock file is a zero-byte sentinel; its content is irrelevant.
- Lock file may persist on disk after the process exits — this is normal and harmless.
- The `.lock` file should be added to `.gitignore`.
