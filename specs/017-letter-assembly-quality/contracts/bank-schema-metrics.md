# Contract: Bank Schema & Typographical Metrics

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](../spec.md)  
**Status**: Active  

---

## 1. Schema Version & Compatibility

- Current active schema: `schema_version = 4`.
- Migrations from `schema_version = 1, 2, 3` are performed in-memory automatically on load via `chuviettay/model/bank_schema.py`.
- On-disk migration script `scripts/migrate_letter_bank.py` produces an upgraded bank without modifying the source file.

---

## 2. Letter Entry Schema Contract

A letter entry in `bank.letters[char]` is a list of sample objects conforming to:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LetterSample",
  "type": "object",
  "required": ["s", "w"],
  "properties": {
    "s": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 2,
          "maxItems": 2
        }
      }
    },
    "w": { "type": "number", "minimum": 0 },
    "h": { "type": "number", "minimum": 0 },
    "lsb": { "type": "number" },
    "rsb": { "type": "number" },
    "adv": { "type": "number", "minimum": 0 },
    "cat": {
      "type": "string",
      "enum": ["x_height", "ascender", "descender", "uppercase", "digit", "punct", "symbol"]
    },
    "lc": {
      "type": "string",
      "enum": ["CURVED", "STRAIGHT", "OPEN"]
    },
    "rc": {
      "type": "string",
      "enum": ["CURVED", "STRAIGHT", "OPEN"]
    },
    "dx": { "type": "number" },
    "dy": { "type": "number" }
  },
  "additionalProperties": true
}
```

---

## 3. Concurrency & Merge Contracts

When two sessions concurrently write or delete letters:
1. `merge_bank_dicts(base, incoming)` merges keys in `letters` using tombstone reconciliation.
2. Deleted characters recorded in `tombstones` are suppressed across merged banks.
3. Every write operation is wrapped in a file-level exclusive lock (`FileLock`).
