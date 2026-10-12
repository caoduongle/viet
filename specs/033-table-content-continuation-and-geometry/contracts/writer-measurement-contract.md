# Contract: Pure Geometric Width Measurement Without Writer Mutation

**Domain**: Letter Assembly & Text Wrapping
**Module**: `chuviettay.model.writer` & `chuviettay.layout.engine`

---

## 1. Specification

Evaluating candidate token widths during character-level wrapping must be a pure, side-effect-free operation that does not mutate internal `Writer` state and safely handles Unicode combining characters.

## 2. Invariants & Mutability Guarantees

When measuring candidate text width:
- `writer.counts`: Invariant (no keys added, no counts incremented).
- `writer.last`: Invariant (no sample indices recorded).
- `writer.assembled`: Invariant (no candidate strings appended).
- `writer.missing`: Invariant (no candidate fragments flagged as missing).
- `random.Random` state: Invariant (no pseudo-random draws consumed).
- Text strings are evaluated under Unicode NFC normalization to prevent separating base characters from diacritical marks.

## 3. Interface Contract

```python
class Writer:
    def measure_text_width(self, text: str, scale: float = 1.0) -> float:
        """Calculate pure geometric advance width of `text` without synthesizing strokes
        or mutating Writer state, using cached character sample widths."""
        ...
```

- Returns a non-negative float representing the advance width in points.
- Time complexity: $O(L)$ where $L = \text{len}(text)$, using cached character advance widths in `_char_width_cache: dict[str, float]`.
- Actual stroke synthesis via `writer.token()` is invoked exactly once per finalized line chunk.
