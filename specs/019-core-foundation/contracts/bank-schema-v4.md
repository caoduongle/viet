# Contract: Bank Schema Version 4

**Version**: 4.0.0  
**Status**: Ratified  
**Scope**: `chuviettay/model/bank_schema.py`, `chuviettay/model/bank.py`  

## 1. Top-Level Structure

Every valid Schema v4 bank dictionary MUST contain:

```json
{
  "schema_version": 4,
  "xh": 7.0,
  "line": 24.0,
  "width": 500.0,
  "ratio": 6.6,
  "x0": 78.0,
  "v": 1.0,
  "wgaps": [11.0],
  "dgaps": [3.5],
  "pen": {
    "tool": "pen",
    "color": "#000000ff",
    "width": 1.41
  },
  "words": {},
  "digits": {},
  "punct": {},
  "symbols": {},
  "letters": {},
  "marks": {
    "sắc": [],
    "huyền": [],
    "hỏi": [],
    "ngã": [],
    "nặng": []
  },
  "tombstones": {},
  "generation": 0
}
```

## 2. Tombstone Scoping Rules

- **Qualified Format**: Keys matching `"<category>:<label>"` (where category is one of `words`, `digits`, `punct`, `symbols`, `letters`) apply strictly to that specific dictionary during synchronization merges.
- **Legacy Unqualified Format**: Keys without a colon (`"<label>"`) are interpreted as applying across all categories for backward compatibility with schema versions 1 through 3.
- **Identity & Membership**: In-memory `bank._tombstones` is backed by `TombstoneDict`, allowing `"xin" in bank._tombstones` to evaluate to `True` if either `"words:xin"` or `"xin"` is present.

## 3. Synthetic Generator Contract

Functions generating synthetic banks (`scripts/gen_synthetic_bank.py`) MUST expose:

```python
def build_synthetic_letter_bank(seed: int = 42) -> dict[str, Any]:
    """Tạo kho mẫu chữ rời tổng hợp chuẩn Schema v4 với đầy đủ 33 chữ cái (hoa/thường)
    và 5 dấu thanh rời tiếng Việt, x-height = 7.94 pt, nét bút = 1.41."""
    ...
```
