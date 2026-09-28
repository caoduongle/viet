# Contract: WriteOptions Validation API

**Module**: `chuviettay/model/composer.py` (method on `WriteOptions` dataclass)

## Public Method

### `WriteOptions.validate() -> None`

Validates all fields of a `WriteOptions` instance against business rules.

**Raises**: `ValueError` with a descriptive message identifying the invalid field and constraint.

**Validation Rules**:

| Field | Constraint | Error message pattern |
|-------|------------|----------------------|
| `scale` | `> 0` and `math.isfinite(scale)` | `"scale phải là số dương hữu hạn, nhận được: {value}"` |
| `line` | `None` or (`> 0` and `math.isfinite`) | `"line phải là số dương hữu hạn hoặc để trống, nhận được: {value}"` |
| `width` | `None` or (`> 0` and `math.isfinite`) | `"width phải là số dương hữu hạn hoặc để trống, nhận được: {value}"` |
| `space` | `> 0` and `math.isfinite(space)` | `"space phải là số dương hữu hạn, nhận được: {value}"` |
| `jitter` | `>= 0` and `math.isfinite(jitter)` | `"jitter phải là số không âm hữu hạn, nhận được: {value}"` |
| `wscale` | `> 0` and `math.isfinite(wscale)` | `"wscale phải là số dương hữu hạn, nhận được: {value}"` |
| `color` | `None` or matches `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$` | `"color phải có dạng #RRGGBB hoặc #RRGGBBAA, nhận được: {value}"` |

**Call Sites**:
- `AppController.write_text()` — calls `opts.validate()` before passing to `compose_document()`.
- CLI `_cmd_write()` and GUI `WriteTab._do_write()` do NOT need separate validation — the controller handles it.

---

## Standalone Utility

### `parse_color(s: str) -> str`

**Module**: `chuviettay/model/composer.py` or a new `chuviettay/model/color.py`

Validates and normalizes a color string.

**Parameters**: `s` — Raw color string from user input.

**Returns**: Validated hex color string (lowercase).

**Raises**: `ValueError` if format does not match `#RRGGBB` or `#RRGGBBAA`.
