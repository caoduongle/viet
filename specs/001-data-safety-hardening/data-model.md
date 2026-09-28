# Data Model: Data Safety and Core Reliability Hardening

**Feature**: `001-data-safety-hardening` | **Date**: 2026-09-29

## Entity: Handwriting Bank (`Bank`)

The central data structure of the application. Persisted as gzip-compressed JSON.

### Schema Definition (v2)

```
Bank Dictionary (top-level JSON object)
├── schema_version : int                          # NEW — 2 for current, absent = legacy v1
├── xh             : float                        # character x-height (> 0)
├── pen            : PenConfig                    # default pen style
│   ├── tool       : str                          # "pen"
│   ├── color      : str                          # "#RRGGBBAA" hex color
│   ├── width      : str                          # stroke width as string
│   └── capStyle   : str                          # "round"
├── words          : dict[str, list[Sample]]      # label → list of handwriting samples
├── digits         : dict[str, list[Sample]]      # digit label → samples
├── punct          : dict[str, list[Sample]]      # punctuation label → samples
├── wgaps          : list[float]                  # word gap reference widths (optional, defaults [11.0])
├── dgaps          : list[float]                  # digit gap reference widths (optional, defaults [3.5])
├── line           : float                        # line height (optional)
├── v              : int                          # legacy version indicator (optional, kept for compat)
├── x0             : float                        # left margin x-offset (optional)
├── width          : float                        # page width (optional)
└── ratio          : float                        # aspect ratio (optional)
```

### Entity: Sample

```
Sample (element of words/digits/punct lists)
├── w   : float                       # width of this sample (rounded to 2 decimal places)
├── s   : list[Stroke]                # list of stroke coordinate arrays
├── T   : str                         # tone mark identifier ("" if none)
├── vi  : int                         # vowel index carrying tone (-1 if none)
└── ti  : int                         # index of tone-mark stroke in `s` (-1 if none)
```

### Entity: Stroke

```
Stroke = list[float]    # flat array [x0, y0, x1, y1, ...] of relative coordinates
```

### Validation Rules

| Field | Rule |
|-------|------|
| `schema_version` | Integer; absent → 1; must be ≤ `CURRENT_VERSION` (2) |
| `xh` | Required; float/int; > 0 |
| `words` | Required; dict; each value must be `list[dict]` |
| `digits` | Required; dict; same structure as `words` |
| `punct` | Required; dict; same structure as `words` |
| `pen` | Required; dict; must contain `tool`, `color`, `width` |
| Each `Sample.s` | Required; list of Stroke arrays |
| Each `Sample.w` | Required; float/int |

### State Transitions

```
                    ┌──────────────────────┐
                    │   File on Disk       │
                    │   (gzip JSON)        │
                    └──────┬───────────────┘
                           │ load
                           ▼
            ┌──────────────────────────────┐
            │  Stage 1: Raw Bytes          │
            │  Check: exists? non-empty?   │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Stage 2: Gzip Decompress    │
            │  Check: valid gzip?          │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Stage 3: JSON Parse         │
            │  Check: valid JSON?          │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Stage 4: Schema Validation  │
            │  Check: required keys/types  │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Stage 5: Migration          │
            │  v1 → v2 (in-memory only)    │
            └──────────────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────┐
            │  Bank Instance (in memory)   │
            │  Ready for use               │
            └──────────────────────────────┘
                           │
                           │ save (on mutation)
                           ▼
            ┌──────────────────────────────┐
            │  Atomic Persistence          │
            │  lock → unique tmp → fsync   │
            │  → os.replace → unlock       │
            └──────────────────────────────┘
```

---

## Entity: WriteOptions (Validated Configuration)

```
WriteOptions (dataclass)
├── scale       : float         # > 0, finite          (default 1.0)
├── line        : float | None  # None or > 0, finite  (default None)
├── width       : float | None  # None or > 0, finite  (default None)
├── space       : float         # > 0, finite          (default 1.0)
├── jitter      : float         # >= 0, finite         (default 1.0)
├── wscale      : float         # > 0, finite          (default 1.0)
├── color       : str | None    # None or #RRGGBB[AA]  (default None)
├── seed        : int | None    # any integer or None   (default None)
└── strict_case : bool          # True/False            (default False)
```

### Validation Rules (applied identically in GUI and CLI)

| Field | Valid | Invalid Examples |
|-------|-------|-----------------|
| `scale` | `(0, ∞)`, `math.isfinite` | `0`, `-1`, `nan`, `inf` |
| `line` | `None` or `(0, ∞)`, `math.isfinite` | `0`, `-100` |
| `width` | `None` or `(0, ∞)`, `math.isfinite` | `0`, `-5` |
| `space` | `(0, ∞)`, `math.isfinite` | `0`, `-2` |
| `jitter` | `[0, ∞)`, `math.isfinite` | `-1`, `nan` |
| `wscale` | `(0, ∞)`, `math.isfinite` | `0`, `-1` |
| `color` | `None` or `^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$` | `"blue"`, `"rgb()"`, `"#000\" width=\"99"` |

---

## Entity: Error Hierarchy

```
BankError (base for all bank operations)
├── BankNotFoundError (FileNotFoundError)    # File does not exist
├── BankCorruptedError                        # 0 bytes / bad gzip / bad JSON
├── BankValidationError (ValueError)          # Missing keys / wrong types / bad values
└── BankSchemaError
    ├── UnsupportedSchemaVersionError         # schema_version > CURRENT
    └── BankMigrationError                    # Migration step failed
```

---

## Entity: Synthetic Test Bank

Generated by script, committed as `tests/data/kho_mau_tong_hop.json.gz`.

```
Synthetic Bank (subset)
├── schema_version : 2
├── xh             : 7.0
├── pen            : standard pen config
├── words          : ~20-30 labels with geometric pseudo-strokes
│   ├── basic words (no tone): "ba", "ma", "la"...
│   ├── toned words: "bà", "má", "là"...
│   └── multi-sample words: "xin" (5+ samples for calibration tests)
├── digits         : "0"-"9" with simple strokes
└── punct          : ",", ".", "(", ")" with simple strokes
```
