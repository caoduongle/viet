# Contract: Deep Schema Validation & Invariants

**Component**: `chuviettay.model.bank_schema`
**Status**: Active

## 1. Overview
This contract defines the deep structural invariants and validation rules enforced on all handwriting profile files (`.json.gz`) at the application boundary.

## 2. Invariants & Rules

### 2.1 Sample Tone Invariants (`validate_sample`)
For every sample item in `words[label]`, `digits[label]`, and `punct[label]`:
- **Stroke Count**: `len(item["s"]) >= 1`.
- **Sample Width (`w`)**:
  - For `words` and `digits`: MUST be present and be a positive finite float (`w > 0`).
  - For `punct`: OPTIONAL (legacy banks omit `w` and compute width dynamically from stroke bounding box). If present, MUST be a positive finite float (`w > 0`).
- **Tone Stroke Index (`ti`)**:
  - Must be an `int`.
  - Must satisfy `-1 <= ti < len(item["s"])`.
  - If `ti >= 0`:
    - `ti` represents an existing stroke in `item["s"]`.
    - Sample MUST have non-empty `T` (`T in TONES`).
    - `vi` MUST be $\ge 0$.
- **Tone Character (`T`)**:
  - Must be a `str`.
  - If non-empty, MUST belong to valid Vietnamese tones (`TONES = ("\u0300", "\u0301", "\u0303", "\u0309", "\u0323")`).
- **Vowel Index (`vi`)**:
  - Must be an `int`.
  - Must satisfy `vi >= -1`.
  - If label is known and $vi \ge 0$, $vi$ MUST satisfy $vi < \text{len}(\text{label})$.

### 2.2 Pen Configuration Invariants (`validate_bank_dict`)
For the `pen` configuration dictionary:
- `pen["tool"]`: Must be `str`, non-empty (`len(tool.strip()) > 0`).
- `pen["color"]`: Must be `str`, formatted as a valid 6-character or 8-character hexadecimal color matching regex:
  `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$`
- `pen["width"]`: Must represent a positive, finite numeric value (`float > 0`).

### 2.3 Exception Hierarchy
- Invariant violations MUST raise `BankValidationError` (subclass of `BankError` and `ValueError`).
- Diagnostics MUST include the JSON path (e.g. `words['chào'][0]['ti']`).
