# Contract: Bank Storage & Categorization (Schema v3)

**Document**: `contracts/bank-storage-contract.md`  
**Feature**: `014-core-engine-hardening`  
**Status**: Ratified

---

## 1. Schema v3 File Structure

A `.json.gz` handwriting sample bank file conforms to the following JSON structure:

```json
{
  "version": 3,
  "words": {
    "chào": [[[10.0, 20.0], [12.0, 22.0]]]
  },
  "digits": {
    "0": [[[5.0, 5.0], [5.0, 15.0]]],
    "1": [[[10.0, 5.0], [10.0, 15.0]]]
  },
  "punct": {
    ",": [[[2.0, 18.0], [1.0, 22.0]]],
    ".": [[[5.0, 20.0], [5.5, 20.5]]]
  },
  "symbols": {
    "+": [[[5.0, 10.0], [15.0, 10.0]], [[10.0, 5.0], [10.0, 15.0]]]
  },
  "tombstones": {
    "words": [],
    "digits": [],
    "punct": [],
    "symbols": []
  },
  "xh": 16.0,
  "wgaps": [8.0, 11.0, 14.0],
  "pen": {
    "tool": "pen",
    "color": "#000000ff",
    "width": "1.41"
  }
}
```

---

## 2. Invariants & Lookup Rules

1. **Classification Contract (`classify_token`)**:
   - Single ASCII digit `0`–`9` $\rightarrow$ must be routed to `digits`.
   - ASCII/Unicode punctuation marks (`.,!?:;-"'()[]{}/`) $\rightarrow$ must be routed to `punct`.
   - Standard math operators and LaTeX symbols $\rightarrow$ must be routed to `symbols`.
   - All other word tokens $\rightarrow$ routed to `words`.
2. **Lookup Hierarchy (`Writer.number`)**:
   - Check `bank.digits.get(ch)` first.
   - If not found in `digits`, check `bank.words.get(ch)` (backward compatibility).
   - If found in neither, report `ch` as missing digit.
3. **Tombstone Merge Invariant**:
   - When merging Bank A and Bank B:
     $$\text{Keys}_{\text{result}} = (\text{Keys}_A \cup \text{Keys}_B) \setminus (\text{Tombstones}_A \cup \text{Tombstones}_B)$$
   - Tombstones are never cleared unless explicitly requested by a user reset.
4. **Sample Deduplication Contract**:
   - Two samples with identical coordinates rounded to 1 decimal place (`_sample_signature`) MUST NOT be duplicated in the same bank entry.
