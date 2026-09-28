# Contract: Bank Schema Validation API

**Module**: `chuviettay/model/bank_schema.py`

## Public Functions

### `validate_bank_dict(d: dict) -> int`

Validates the structural integrity of a bank dictionary.

**Parameters**:
- `d` — A parsed JSON dictionary (the bank data).

**Returns**: The detected schema version (integer). Returns `1` if `schema_version` key is absent (legacy format).

**Raises**:
- `BankValidationError` — Missing required keys, wrong types, invalid values.
- `UnsupportedSchemaVersionError` — `schema_version` exceeds `CURRENT_VERSION`.

**Behavior**:
1. Checks `d` is a `dict`.
2. Verifies all required keys exist with correct types: `words` (dict), `digits` (dict), `punct` (dict), `xh` (float/int, > 0), `pen` (dict with `tool`, `color`, `width`).
3. For each entry in `words`/`digits`/`punct`: verifies value is `list[dict]`, each sample has `"s"` and `"w"` keys.
4. Checks `schema_version` if present: must be `int`, must be ≤ `CURRENT_VERSION`.

---

### `migrate_bank_dict(d: dict, from_version: int) -> None`

Applies sequential in-memory migrations from `from_version` to `CURRENT_VERSION`.

**Parameters**:
- `d` — Bank dictionary to migrate (modified in-place).
- `from_version` — Starting version (as returned by `validate_bank_dict`).

**Raises**:
- `BankMigrationError` — No migration path available for a version step.

**Behavior**:
- Applies `MIGRATIONS[v]` for each `v` from `from_version` to `CURRENT_VERSION - 1`.
- Each migration function modifies `d` in-place and sets `schema_version` to `v + 1`.

---

## Constants

- `CURRENT_VERSION = 2` — The current schema version supported by the application.

---

## Exception Classes

All defined in `chuviettay/model/bank_schema.py` (or `chuviettay/model/bank.py`):

| Exception | Base | Purpose |
|-----------|------|---------|
| `BankCorruptedError` | `BankError` | File-level corruption (0 bytes, bad gzip, bad JSON) |
| `BankValidationError` | `BankError, ValueError` | Structural validation failures |
| `UnsupportedSchemaVersionError` | `BankSchemaError` | Future version not supported |
| `BankMigrationError` | `BankSchemaError` | Migration step failure |
