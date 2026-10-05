# Controller & Model API Contracts

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](../spec.md)  

---

## 1. Bank Interface Updates

### `Bank.drop(label: str, category: str | None = None) -> bool`

Deletes a sample entry from the bank.

**Parameters**:
- `label`: Text label of the entry to drop (e.g., `"a"`, `"π"`, `"1"`).
- `category`: Optional category string (`"words"`, `"letters"`, `"digits"`, `"symbols"`, `"punct"`).
  - If specified: Drops the entry strictly from `self.d[category]`, records `"<category>:<label>"` in `_tombstones` and `_deleted_words`, and removes it from `_readded_words`.
  - If `None`: Resolves category using legacy fallback order (`symbols` -> `digits` -> `punct` -> `letters` -> `words`), preserving backward compatibility.

**Returns**:
- `True` if an entry was found and deleted; `False` otherwise.

---

### `Bank.add_symbol_sample(symbol: str, strokes: list, width: float)`

Adds a symbol sample and maintains tombstone consistency.

**Behavior**:
- Discards `"symbols:" + symbol` (and legacy bare `symbol`) from `_deleted_words`.
- Records `"symbols:" + symbol` into `_readded_words`.
- Removes any tombstone record for the symbol.
- Appends the stroke sample to `self.d["symbols"][symbol]`.

---

### Thread Safety Contract (`Bank._lock`)

- `Bank` exposes thread synchronization via an internal `self._lock = threading.RLock()`.
- All methods modifying in-memory bank dictionaries acquire `self._lock`.
- `Bank.save()` acquires `self._lock` during cache checks, disk merges, and in-memory JSON serialization (`json.dumps`). It releases the lock before performing filesystem I/O.

---

## 2. Controller Interface Updates

### `AppController.drop_words(words: list[str]) -> int`

- Drops words strictly from `self.bank.words` by calling `self.bank.drop(w, category="words")`.
- Guarantees that dropping a word (e.g., word `"a"`) never affects a letter sample of the same name (`letters["a"]`).

### `AppController.drop_letter(letter: str) -> bool`

- Drops letter strictly from `self.bank.letters` by calling `self.bank.drop(letter, category="letters")`.

---

## 3. WriteOptions Contract

```python
@dataclass
class WriteOptions:
    ...
    missing_grid: bool = True  # Controls generation of missing character practice sheet
```

When `missing_grid == False`, `DocumentLayoutEngine.synthesize()` must not invoke `xopp.make_grid()`, and `WriteResult.missing_grid_path` must be `None`.
