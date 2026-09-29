# Contract: Math Root Node Layout & Glyph Deduplication

**Feature Branch**: `009-table-and-math-layout-fixes`
**Date**: 2026-09-30
**Spec**: [spec.md](../spec.md)

## 1. Purpose

This contract defines the geometric and stroke generation guarantees of `MathLayoutEngine.measure` when handling `Root` expressions (e.g. square roots $\sqrt{\dots}$ and nth-roots $\sqrt[n]{\dots}$).

---

## 2. API Signature & Invariants

### 2.1 Invocation

```python
item: MathLayoutItem = math_layout_engine.measure(node: Root, scale: float = 1.0, depth: int = 0)
```

### 2.2 Guarantees

1. **Deduplication Invariant**:
   - `len(item.glyphs)` MUST equal `len(radicand_item.glyphs)` + `len(degree_item.glyphs if degree else [])`.
   - The unshifted copies of radicand glyphs/strokes at origin $(0, 0)$ MUST NOT be present in `item.glyphs` or `item.strokes`.
2. **Horizontal Alignment**:
   - Every radicand glyph $g \in \text{item.glyphs}$ MUST have horizontal coordinate $g.x \ge \text{sign\_w}$.
   - The overbar of the radical symbol in `item.strokes` MUST extend from $\text{sign\_w} \times 0.8$ to at least $\text{sign\_w} + \text{radicand\_width}$.
3. **Stroke Density**:
   - For any non-empty radicand containing supported alphanumeric tokens (e.g. `x`, `2`, `+`, `1`), `sum(len(g.strokes) for g in item.glyphs)` MUST be $> 0$.
   - Total strokes in `item.strokes` MUST equal:
     $$\text{strokes}_{\text{radical\_hook}} + \sum \text{strokes}_{\text{radicand\_internal}} + \sum \text{strokes}_{\text{degree\_internal}}$$
