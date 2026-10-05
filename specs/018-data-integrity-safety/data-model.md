# Data Model & Schema Specifications: Data Integrity Safety Net (P0)

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](./spec.md)  
**Status**: Completed  

---

## 1. Domain Entities & Schema Definitions

### 1.1 Qualified Tombstone Key (`TombstoneKey`)

In Schema Version 4, tombstones and in-memory deletion tracking sets (`_tombstones`, `_deleted_words`, `_readded_words`) transition from bare string labels to category-qualified composite keys.

```python
from typing import Literal

Category = Literal["words", "letters", "digits", "symbols", "punct"]

def make_tombstone_key(category: Category, label: str) -> str:
    """Create a namespaced tombstone identifier."""
    return f"{category}:{label}"

def parse_tombstone_key(key: str) -> tuple[Category | None, str]:
    """Parse a tombstone key into (category, label).
    
    If key has no colon prefix, returns (None, key) representing a legacy
    unqualified tombstone that applies to all categories.
    """
    if ":" in key:
        prefix, _, label = key.partition(":")
        if prefix in ("words", "letters", "digits", "symbols", "punct"):
            return prefix, label  # type: ignore
    return None, key
```

**State Transitions for Samples and Tombstones**:

```text
[Active Sample Exists]
         |
         | Bank.drop(label, category)
         v
[Tombstone Created: "category:label"]
[Key added to _deleted_words]
         |
         | Bank.add_*_sample(label)
         v
[Tombstone Removed]
[Key discarded from _deleted_words]
[Key added to _readded_words]
         |
         | Bank.save() (after disk merge)
         v
[_readded_words and _deleted_words flushed]
```

---

### 1.2 Bank Dictionary Model (Schema Version 4)

Stored in compressed JSON (`.json.gz`) format:

```json
{
  "schema_version": 4,
  "words": {
    "a": [
      { "s": [[[0.0, -5.0], [3.0, 0.0]]], "w": 4.0, "T": "", "vi": -1, "ti": -1 }
    ]
  },
  "letters": {
    "a": [
      { "s": [[[0.0, -5.0], [3.0, 0.0]]], "w": 4.0 }
    ]
  },
  "digits": {},
  "symbols": {
    "π": [
      { "s": [[[0.0, 0.0], [5.0, 5.0]]], "w": 6.0 }
    ]
  },
  "punct": {},
  "marks": {},
  "learned_files": [
    "a1b2c3d4... (SHA-256 of uncompressed XML or legacy raw archive)"
  ],
  "tombstones": {
    "letters:b": 1728140000.0,
    "words:chao": 1728140100.0,
    "legacy_deleted_key": 1728130000.0
  }
}
```

**Validation Rules**:
1. `schema_version` must be an integer $\ge 1$ and $\le 4$.
2. Categories `words`, `letters`, `digits`, `symbols`, `punct` must be dictionaries mapping string labels to lists of sample dictionaries.
3. `tombstones` can be either a dictionary of `{key: timestamp}` or a list of `[key]`.
4. Keys in `tombstones` may be qualified (`"<category>:<label>"`) or legacy unqualified (`"<label>"`).

---

### 1.3 Missing Grid Document (`MissingGridDocument`)

Represents a practice grid output (`<output>_thieu.xopp` or numbered variant).

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class MissingGridTarget:
    base_output_path: Path
    missing_characters: list[str]
    allow_creation: bool  # Corresponds to opts.missing_grid

    def resolve_target_file(self) -> Path | None:
        """Determines destination file path.
        
        - If allow_creation is False, returns None.
        - If base_thieu.xopp does not exist or contains ONLY guide strokes, returns base_thieu.xopp.
        - If base_thieu.xopp contains user handwriting, searches base_thieu_2.xopp,
          base_thieu_3.xopp, etc., returning the first unwritten or non-existent path.
        """
```

**Stroke Classification**:
- A stroke `<stroke tool="pen" color="C" ...>` in `.xopp` XML represents **guide geometry** if `C` is in `HW3_GUIDE_COLORS` (`#c8c8c8`, `#a0a0a0`, `#d8d8d8`, `#e0e0e0`, `#e8e8e8`, `#ffc0c0`, `#ffd0d0`, `#e8f4f8`).
- A stroke represents **user handwriting** if `tool == "pen"` and `color` is NOT in `HW3_GUIDE_COLORS`.

---

### 1.4 WriteResult Entity

Returned by `DocumentLayoutEngine` and `AppController`:

```python
@dataclass
class WriteResult:
    out_path: str
    missing_grid_path: str | None = None
    n_strokes: int = 0
    missing_count: int = 0
    pages: int = 1
```

- When `opts.missing_grid == False` or `missing_count == 0`, `missing_grid_path` is `None`.
- When an existing `_thieu.xopp` has user strokes and a numbered file is generated (`_thieu_2.xopp`), `missing_grid_path` contains the exact path to `_thieu_2.xopp`.
