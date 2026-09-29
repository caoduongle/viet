# Contract: Incremental Indexing and Rebuild Equivalence

**Component**: `chuviettay.model.bank.Bank`
**Status**: Active

## 1. Overview
The `Bank` component provides two indexing mechanisms:
- `rebuild()`: Full collection re-indexing across all samples in `self.words`.
- `add_sample_incremental()`: In-memory incremental index update when a single new sample is added.

## 2. Invariant Contract

### 2.1 Rebuild Equivalence
For any arbitrary sequence of calls to `add_sample_incremental(label, rel_strokes, width)` starting from an initial bank state:
- The resulting stripped-tone index `self.tl` MUST be identical to the `self.tl` produced by calling `self.rebuild()`.
- The resulting query tone mark index `self.marks` MUST be identical in content and order to `self.marks` produced by calling `self.rebuild()`.

### 2.2 Raw Mark Preservation
- `Bank` MUST maintain `self._raw_marks: dict[str, list[dict]]` containing all harvested tone marks.
- Outlier filtering (10th-90th percentiles for tones with $\ge 10$ marks) MUST operate on `_raw_marks` to generate the query cache `self.marks`.
- Outlier filtering MUST NEVER discard or delete marks from `_raw_marks`.
- When an 11th, 12th, or Nth mark is added to tone $T$, previous marks that fall back within the new percentile thresholds MUST automatically be restored to `self.marks[T]`.

## 3. Algorithmic Complexity
- **Storage and Root Indexing**: $O(1)$ amortized for adding samples to `self.words` and stripped-tone index `self.tl`.
- **Tone Mark Maintenance**: $O(1)$ to append to `self._raw_marks[T]`, and $O(M \log M)$ to update percentile filter on tone $T$ with $M$ marks.
- **Scale Independence**: Maintenance is strictly independent of total bank size $N$ ($M \ll N$, with $M \le 100$ in typical user banks, yielding $< 10\mu\text{s}$ execution).
- **Full Rebuild**: $O(N + \sum M_i \log M_i)$ across all words and all tones (executed only on initial load or explicit drop operations).

## 4. Public Methods

```python
class Bank:
    _raw_marks: dict[str, list[dict]]
    marks: dict[str, list[dict]]
    tl: dict[str, list[tuple[str, dict]]]

    def rebuild(self) -> None:
        """Reconstruct tl and marks from all samples in self.words."""
        ...

    def add_sample_incremental(
        self, label: str, rel_strokes: list[Stroke], width: float
    ) -> dict:
        """Add one sample and incrementally update tl and marks without re-scanning self.words.
        Guarantees self.marks is identical to calling rebuild()."""
        ...
```
