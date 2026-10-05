# Data Model: P1 — Core Foundation & Ecosystem Harmonization

**Feature**: `019-core-foundation`  
**Date**: 2026-10-05  

## Core Data Entities

### 1. Bank Schema Version 4 (`BankDict`)

The primary persistent data structure serialized to gzip JSON (`chu_cua_ban.json.gz`).

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
    "width": 1.41,
    "capStyle": "round"
  },
  "words": {
    "<word>": [
      {
        "w": 12.5,
        "s": [[0.0, 0.0, 5.0, -10.0, 10.0, 0.0]],
        "T": "sắc",
        "vi": 1,
        "ti": 0,
        "_sig": "hash..."
      }
    ]
  },
  "digits": {},
  "punct": {},
  "symbols": {
    "<symbol>": [
      {
        "w": 8.0,
        "s": [[0.0, 0.0, 4.0, 4.0]],
        "_sig": "hash..."
      }
    ]
  },
  "letters": {
    "<letter>": [
      {
        "w": 6.5,
        "s": [[0.0, 0.0, 3.0, -7.0, 6.0, 0.0]],
        "lsb": 0.5,
        "rsb": 0.5,
        "adv": 7.5,
        "_sig": "hash..."
      }
    ]
  },
  "marks": {
    "sắc": [],
    "huyền": [],
    "hỏi": [],
    "ngã": [],
    "nặng": []
  },
  "tombstones": {
    "words:xin": { "deleted_at": 1791217000.0, "generation": 2 },
    "letters:a": { "deleted_at": 1791217005.0, "generation": 3 }
  },
  "generation": 3,
  "learned_files": {
    "<sha256_uncompressed_xml>": "filename.xopp"
  }
}
```

#### Validation & Invariants:
- `schema_version`: Must equal `4`.
- `tombstones`: Must be a dictionary where keys are `<category>:<label>` (or legacy `<label>`), and values are `{ "deleted_at": float, "generation": int }` or legacy float timestamp.
- `letters`: Keys must be alphabetic Vietnamese or Latin characters (including digraphs).
- `marks`: Keys must strictly match the 5 Vietnamese tone marks: `sắc`, `huyền`, `hỏi`, `ngã`, `nặng`.

---

### 2. HW3 Practice Grid Model (`HW3GridDefinition`)

Defines the structure and coordinates of cells in the 4-line practice sheet.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `letters` | `list[str]` | 33 standard letters in upper and lower case (66 total: 29 Vietnamese + f, j, w, z). |
| `digraphs` | `list[str]` | 14 consonant/vowel clusters: `ng, nh, ch, tr, ph, th, kh, gi, qu, ươ, ưa, uy, ay, oa`. |
| `tones` | `list[str]` | 5 standalone tone labels: `dấu sắc, dấu huyền, dấu hỏi, dấu ngã, dấu nặng`. |
| `total_cells` | `int` | 85 cells (expanded from 77). |
| `target_xh` | `float` | Target x-height for grid ruling (default: 7.94 pt). |
| `guide_colors` | `set[str]` | Hex color set identifying non-user ruling strokes (`HW3_GUIDE_COLORS`). |

---

### 3. Path Resolution Hierarchy (`BankPathResolver`)

Models the precedence logic for locating the active handwriting bank.

```text
Input Request
    │
    ▼
Has `--bank <path>`? ──────► YES ──► Use explicitly provided path
    │
    NO
    ▼
File exists in `app_base_dir()`? ──► YES ──► Use local portable path
    │
    NO
    ▼
Resolve OS standard user directory:
  - Windows: %APPDATA%/chuviettay/chu_cua_ban.json.gz
  - macOS:   ~/Library/Application Support/chuviettay/chu_cua_ban.json.gz
  - Linux:   $XDG_DATA_HOME/chuviettay/chu_cua_ban.json.gz
```

---

### 4. Xournal++ Page Background Mapping (`BackgroundStyleMapping`)

Models bidirectional mapping between user-facing CLI/GUI style names and native Xournal++ XML attributes.

| User-Facing Style | Native Xournal++ XML Style | Description |
| :--- | :--- | :--- |
| `plain` | `plain` | Blank white page |
| `lined` | `lined` | Horizontal lines with vertical margin rule |
| `ruled` | `ruled` | Horizontal lines without vertical margin |
| `graph` | `graph` | Grid square ruling |
| `dotted` | `dotted` | Regular dot grid |
| `iso_graph` | `isograph` | Isometric triangular grid |
| `iso_dotted` | `isodotted` | Isometric dot pattern |
| `music` | `staves` | Musical staff ruling |
