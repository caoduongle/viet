# Contract: Bank Concurrency & Atomic Reload-and-Merge

**Module**: `chuviettay.model.bank` | **Component**: `Bank.save()` & `merge_banks()`

## Overview
Guarantees that concurrent save operations across separate processes do not discard updates made by other processes (eliminating lost updates).

## Signature & Interface

```python
def merge_bank_dicts(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge incoming bank dictionary into base bank dictionary.
    
    Words not in base are added. Words in both have new samples appended
    if they do not already exist (matching stroke coordinates).
    
    Args:
        base: The current bank dictionary.
        incoming: The on-disk bank dictionary read during lock.
        
    Returns:
        The merged bank dictionary.
    """

class Bank:
    def save(self, target_path: str | Path | None = None) -> None:
        """Persist bank atomically with cross-process file lock and disk reload-and-merge.
        
        Steps:
        1. Acquire FileLock(lock_path).
        2. If destination file exists on disk, read its contents and call merge_bank_dicts.
        3. Write merged dictionary to tempfile.mkstemp in parent directory.
        4. Flush buffer and os.fsync(fd).
        5. Close file descriptors.
        6. os.replace(tmp_path, destination_path).
        7. Flush parent directory if POSIX.
        8. Release FileLock.
        """
```

## Guarantees & Constraints
- **Zero Lost Updates**: If Process A adds word "tu_A" and Process B adds word "tu_B", both words exist in the destination bank after both saves finish.
- **Deadlock Freedom**: File lock has a default timeout (e.g. 10.0 seconds); raises `TimeoutError` if lock cannot be acquired.
- **Atomic File Integrity**: Target file is replaced only after data is fully committed via `fsync`.
