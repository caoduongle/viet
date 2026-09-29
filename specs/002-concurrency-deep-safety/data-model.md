# Data Model: Concurrency Deep Safety and Scalability Hardening

**Feature**: `002-concurrency-deep-safety` | **Date**: 2026-09-29

## Entities & Schemas

### 1. Handwriting Bank (`Bank`)

The primary data structure holding all learned word samples and rendering configuration.

```python
{
    "schema_version": 2,                  # int: Currently 2
    "words": {                           # dict[str, list[SampleDict]]
        "xin": [
            {
                "s": [                   # list[list[float | int]]: List of strokes
                    [0.0, 10.0, 5.0, 15.0, 10.0, 12.0],  # stroke 0: (x0, y0, x1, y1, ...)
                    [12.0, 8.0, 15.0, 20.0]               # stroke 1
                ],
                "w": 1.5                 # float: Base stroke width > 0
            }
        ]
    },
    # Required Runtime Metadata Fields:
    "line": 32.0,                        # float: Default line spacing in points
    "width": 1.2,                        # float: Default stroke width
    "wgaps": 8.0,                        # float: Inter-word spacing
    "dgaps": 2.0,                        # float: Inter-character spacing
    "v": 0.8,                            # float: Speed/velocity scale
    "x0": 10.0,                          # float: Initial x margin offset
    "ratio": 1.0                         # float: Aspect ratio factor
}
```

#### Invariants & Constraints:
- `schema_version`: Must equal `CURRENT_SCHEMA_VERSION` (2).
- `words`: Non-empty dictionary of Vietnamese words and glyph tokens.
- `words[w]`: List of at least 1 sample dictionary.
- Each `sample`:
  - Contains `"s"` (strokes) and `"w"` (pen width).
  - `"w"` must be finite, $> 0$.
  - `"s"` must be a non-empty list of strokes.
  - Each stroke must be a list with even length $\ge 2$.
  - All coordinates in strokes must be finite floats/ints (not `NaN`, not `±inf`).
- Metadata fields: `line`, `width`, `wgaps`, `dgaps`, `v`, `x0`, `ratio` must all be finite positive numbers.

---

### 2. Stroke Geometry

A single continuous pen stroke represented as flattened alternating 2D Cartesian coordinates:

$$\text{stroke} = [x_0, y_0, x_1, y_1, \dots, x_{n-1}, y_{n-1}]$$

- **Coordinate count**: $2n$, where $n \ge 1$ is the number of captured points.
- **Constraints**:
  - Length is strictly even: `len(stroke) % 2 == 0`.
  - Coordinates are finite: `math.isfinite(coord)`.
  - Stroke must contain at least one point: `len(stroke) >= 2`.

---

### 3. Concurrency Mutation Transaction

Represents an in-flight mutation operation executing under `FileLock`.

```
State Transitions:
[In-Memory Mutation]
        │
        ▼
[Acquire FileLock(path + ".lock")]
        │
        ▼
[Read On-Disk State D_disk] ── (File missing) ──► [Write Local D_mem]
        │
  (File exists)
        │
        ▼
[Merge D_disk + D_mem]
        │
        ▼
[Write Merged D to tempfile.mkstemp]
        │
        ▼
[flush() + os.fsync()]
        │
        ▼
[os.replace(tmp_path, final_path)]
        │
        ▼
[Release FileLock]
```

#### Merge Rules:
- Let $W_{\text{disk}}$ be words in on-disk file, and $W_{\text{local}}$ be words in memory.
- For each word $w \in W_{\text{disk}}$:
  - If $w \notin W_{\text{local}}$, add $w$ with all its samples to $W_{\text{local}}$.
  - If $w \in W_{\text{local}}$, identify samples in $W_{\text{disk}}[w]$ not present in $W_{\text{local}}[w]$ (compared by tuple serialization of stroke geometry) and append them.
- Preserve local updates for any $w \in W_{\text{local}}$.

---

### 4. Logging State

```python
class LoggingState:
    active_path: str | None    # Path to active log file, or None if completely disabled
    handler_type: str          # "file" | "stream_fallback" | "null"
```
