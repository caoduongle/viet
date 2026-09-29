# Contract: Deletion Tombstones and Cross-Process Merge Safety

**Component**: `chuviettay.model.bank.Bank` / `merge_bank_dicts`
**Status**: Active

## 1. Overview
This contract ensures that word deletions performed in one process persist permanently across subsequent multi-process saves, eliminating lost-update resurrection bugs.

## 2. Invariants & Rules

### 2.1 Persistent Tombstones
- Deleted words are recorded in the bank dictionary under an optional metadata key: `"tombstones": dict[str, float]`, mapping `word -> deletion_timestamp`.
- When `Bank.drop(word)` is executed:
  - The word is removed from `self.words`.
  - An entry `self.tombstones[word] = time.time()` is created.
  - The word is removed from `tl` and its marks are pruned from `_raw_marks` and `marks`.

### 2.2 Tombstone Revocation on Re-Teaching
- When a user explicitly re-teaches or adds a sample for a previously deleted word (`add_sample(word, ...)` or `add_sample_incremental(word, ...)`):
  - The tombstone for `word` is deleted: `self._tombstones.pop(word, None)`.
  - The word is added to session re-adds: `self._readded_words.add(word)`.
  - The word is restored to `self.words` with the new sample.

### 2.3 Cross-Process Merge Contract
When merging `base` (in-memory state) and `disk` (external file on disk):
```python
def merge_bank_dicts(base: dict[str, Any], disk: dict[str, Any], readded_words: set[str] | None = None) -> dict[str, Any]:
```
1. **Merge Tombstones**:
   - `disk_tombstones = disk.get("tombstones", {})`
   - `base_tombstones = base.get("tombstones", {})`
   - If `readded_words`:
     - For `w in readded_words`: disk and base tombstones for `w` are purged.
   - `merged_tombstones = {**disk_tombstones, **base_tombstones}`
   - If `readded_words`:
     - For `w in readded_words`: `merged_tombstones.pop(w, None)`
   - `base["tombstones"] = merged_tombstones`
2. **Apply Tombstones to Words**:
   - For every word in `merged_tombstones`:
     - If the word exists in `base.get("words", {})` or `disk.get("words", {})`:
       - If `readded_words and word in readded_words`:
         - Preserve the word in `base["words"]` (explicit user action overrides disk tombstone).
       - Else:
         - Remove the word from `base["words"]` (honoring the deletion).
3. **Merge Non-Deleted Words, Digits, Punct**:
   - For unaffected words/digits/punct, union sample lists using full sample signature:
     `_sample_signature(inst) = (strokes_rounded, w, T, vi, ti)`.
   - Identical duplicates (exact matching geometry and metadata) are skipped; distinct variations are preserved.
