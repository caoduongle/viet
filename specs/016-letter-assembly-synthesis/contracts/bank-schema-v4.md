# Contract: Bank Storage Schema v4 & Concurrency API

**Feature**: `016-letter-assembly-synthesis`  
**File**: `chuviettay/model/bank_schema.py` & `chuviettay/model/bank.py`  

---

## 1. Schema Validation (Schema v4)

`bank_schema.py` upgrades to `CURRENT_VERSION = 4`.

### Required Metadata Keys
```python
REQUIRED_METADATA_KEYS = {
    "words": dict,
    "digits": dict,
    "punct": dict,
    "symbols": dict,
    "letters": dict,  # Added in v4
    "xh": (int, float),
    "pen": dict,
    "line": (int, float),
    "width": (int, float),
    "x0": (int, float),
    "wgaps": list,
    "dgaps": list,
    "ratio": (int, float),
    "v": (int, float),
}
```

### Migrations
```python
def _migrate_v3_to_v4(d: dict[str, Any]) -> dict[str, Any]:
    """Nâng cấp từ v3 lên v4: thêm schema_version = 4 và chuẩn bị kho letters."""
    d["schema_version"] = 4
    if "letters" not in d:
        d["letters"] = {}
    return d

_MIGRATORS = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
}
```

---

## 2. Bank API Extensions

### `Bank.add_letter_sample`
```python
def add_letter_sample(self, letter: str, rel_strokes: list[Stroke], width: float, dedup: bool = True) -> dict:
    """Thêm một mẫu chữ cái đơn lẻ vào self.letters.
    
    Args:
        letter: Ký tự chữ cái đơn lẻ (NFC).
        rel_strokes: Danh sách nét vẽ tương đối (chân chữ tại y=0, min x=0).
        width: Bề rộng chữ cái.
        dedup: Khử trùng mẫu nét trùng lặp.
        
    Returns:
        Mẫu dict vừa thêm: {"w": width, "s": rel_strokes, "_sig": signature}
    """
```

### `Bank.drop_letter`
```python
def drop_letter(self, letter: str) -> int:
    """Xoá toàn bộ mẫu của một chữ cái khỏi self.letters.
    
    Ghi nhận tombstone, tăng generation, đánh dấu dirty, trả về số mẫu đã xoá.
    """
```

### `merge_bank_dicts` Integration
```python
# Concurrency merging rule:
for c_name in ("words", "digits", "punct", "symbols", "letters"):
    disk_c = disk.get(c_name, {})
    base_c = base.setdefault(c_name, {})
    for label, disk_samples in disk_c.items():
        if label in merged_tombstones:
            continue
        if label not in base_c:
            base_c[label] = list(disk_samples)
        else:
            existing_sigs = {_sample_signature(s) for s in base_c[label]}
            for s in disk_samples:
                sig = _sample_signature(s)
                if sig not in existing_sigs:
                    base_c[label].append(s)
                    existing_sigs.add(sig)
```
