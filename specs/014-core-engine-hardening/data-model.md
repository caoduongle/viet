# Data Model: Comprehensive Quality, Correctness, and Performance Hardening

**Feature**: `014-core-engine-hardening`  
**Date**: 2026-09-30  
**Status**: Completed

---

## 1. Core Domain Entities

### `Bank` (Font Collection & Storage Model)

Represents a handwriting sample bank stored on disk as gzip-compressed JSON (`.json.gz`).

```text
┌───────────────────────────────────────────────────────────────┐
│ Bank                                                          │
├───────────────────────────────────────────────────────────────┤
│ + version: int = 3                                            │
│ + words: dict[str, list[Sample]]                              │
│ + digits: dict[str, list[Sample]]                             │
│ + punct: dict[str, list[Sample]]                              │
│ + symbols: dict[str, list[Sample]]                            │
│ + tombstones: dict[str, list[str]]                            │
│ + xh: float = 16.0                                            │
│ + wgaps: list[float]                                          │
│ + pen: dict[str, str]                                         │
│ - _dirty: bool = False                                        │
│ - _lock: threading.Lock                                       │
└───────────────────────────────────────────────────────────────┘
```

#### Fields & Types
- **`version`** (`int`): Schema format version (v3 active).
- **`words`** (`dict[str, list[Sample]]`): Multi-character lexical words (e.g., `"chào"`, `"học"`).
- **`digits`** (`dict[str, list[Sample]]`): Single ASCII digits (`"0"` through `"9"`).
- **`punct`** (`dict[str, list[Sample]]`): Punctuation glyphs (`","`, `"."`, `"!"`, `"?"`, `":"`, `";"`, `"-"`, `"("`, `")"`, `"["`, `"]"`, `"'"`, `"""`, `"/"`).
- **`symbols`** (`dict[str, list[Sample]]`): Mathematical and special symbol strokes (`"+"`, `"-"`, `"="`, `"*"`, `"\alpha"`, etc.).
- **`tombstones`** (`dict[str, list[str]]`): Explicit deleted key registries for each category (`"words"`, `"digits"`, `"punct"`, `"symbols"`) preventing resurrection during peer-bank merges.
- **`xh`** (`float`): Measured lower-case x-height baseline in points.
- **`wgaps`** (`list[float]`): Word spacing distribution samples.
- **`pen`** (`dict[str, str]`): Default tool properties (`tool`, `color`, `width`).

---

### `Sample` & Deduplication Signature

Represents a single handwritten variant of a character, digit, punctuation mark, or word.

```text
┌───────────────────────────────────────────────────────────────┐
│ Sample                                                        │
├───────────────────────────────────────────────────────────────┤
│ + strokes: list[list[tuple[float, float]]]                   │
│ + signature: str (derived hash of normalized points)          │
└───────────────────────────────────────────────────────────────┘
```

#### Deduplication Rules
- **`_sample_signature(strokes)`**: Generates a stable SHA-256 hash derived from the rounded coordinate array `[(round(x, 1), round(y, 1)) for x, y in stroke]`.
- **Deduplication Check**: When `add_sample(category, label, strokes)` is invoked, the sample is only appended if its signature does not already exist within `bank[category][label]`.

---

### `Document IR` (Universal Document Intermediate Representation)

Universal document AST bridging importers (Markdown, DOCX, TXT) with layout engines.

```text
┌───────────────────────────────────────────────────────────────┐
│ Document                                                      │
├───────────────────────────────────────────────────────────────┤
│ + blocks: list[BlockNode]                                     │
│ + unsupported: list[UnsupportedItem]                          │
└───────────────────────────────────────────────────────────────┘
                                ▲
                                │
        ┌───────────────────────┴───────────────────────┐
        │                       │                       │
┌───────┴───────┐       ┌───────┴───────┐       ┌───────┴───────┐
│ ParagraphNode │       │ ListItemNode  │       │ MathBlockNode │
├───────────────┤       ├───────────────┤       ├───────────────┤
│ + inlines     │       │ + level: int  │       │ + latex: str  │
│ + align       │       │ + bullet_char │       │ + ast: MathRow│
└───────────────┘       │ + inlines     │       └───────────────┘
                        └───────────────┘
```

#### Node Definitions
- **`ParagraphNode`**: Contains sequential `InlineNode` spans (`TextSpan`, `BoldSpan`, `ItalicSpan`, `MathInlineSpan`), with alignment property (`"left"`, `"center"`, `"right"`).
- **`ListItemNode`**: Structured list item preserving hierarchy depth (`level: int`), bullet/order style, and inline contents.
- **`MathBlockNode`**: Display-mode mathematical formula, containing raw LaTeX string and parsed AST (`MathRow`).
- **`TableNode`**: Structured table containing rows, cells, and alignment specifications.
- **`UnsupportedItem`**: Structured record of bypassed content:
  - `block_type: str` (e.g., `"code_block"`, `"raw_html"`, `"horizontal_rule"`, `"field_code"`)
  - `source_location: int | str`
  - `raw_text: str`

---

### `WriteOptions` & `WriteResult`

Execution configuration and diagnostic output structures.

```text
┌───────────────────────────────────────────────────────────────┐
│ WriteOptions                                                  │
├───────────────────────────────────────────────────────────────┤
│ + scale: float = 1.0                                          │
│ + line: float | None = None (None = auto-scale with scale)    │
│ + space: float = 1.0                                          │
│ + jitter: float = 0.5                                         │
│ + wscale: float = 1.0                                         │
│ + color: str = "#000000ff"                                    │
│ + seed: int = 42                                              │
│ + strict_case: bool = False                                   │
│ + mode: str = "semantic" ("semantic" | "fidelity")            │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│ WriteResult                                                   │
├───────────────────────────────────────────────────────────────┤
│ + out_path: str                                               │
│ + n_pages: int                                                │
│ + n_lines: int                                                │
│ + n_strokes: int                                              │
│ + n_tokens: int                                               │
│ + n_missing_tokens: int                                       │
│ + missing: dict[str, int]                                     │
│ + missing_symbols: dict[str, int]                             │
│ + n_images: int = 0                                           │
│ + n_tables: int = 0                                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. State Transitions: Debounced Deferred Persistence

```text
[Idle State]
     │
     │ add_sample(...)
     ▼
[Dirty State] ──(2s idle timer)──► [Background Worker]
     │                                     │
     │ tab switch / app close              │ gzip.compress + atomic swap
     ▼                                     ▼
[Immediate Sync Flush] ──────────► [Disk File Updated]
                                           │
                                           ▼
                                     [Idle State]
```
