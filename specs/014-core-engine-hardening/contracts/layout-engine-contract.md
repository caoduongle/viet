# Contract: Layout Engine Scaling & Geometry Invariants

**Document**: `contracts/layout-engine-contract.md`  
**Feature**: `014-core-engine-hardening`  
**Status**: Ratified

---

## 1. Line Height Scaling Formula

When rendering documents with `DocumentLayoutEngine`:

$$\text{effective\_line\_h} = \begin{cases} 
\text{opts.line}, & \text{if } \text{opts.line} > 0 \\
\text{base\_line\_h} \times \text{opts.scale}, & \text{otherwise}
\end{cases}$$

- $\text{base\_line\_h} \approx 29.0$ pt (or document default spacing).
- Doubling `opts.scale` from $1.0$ to $2.0$ MUST double $\text{effective\_line\_h}$, preventing overlapping text lines.

---

## 2. Math Formula Scale Invariant

For any mathematical node (inline span or display block):

$$\text{eff\_scale} = \text{opts.scale} \times \left(\frac{\text{target\_font\_size}}{\max(10.0, \text{bank\_xh})}\right)$$

- Both inline math and standalone math blocks MUST apply the same `eff_scale`.
- Subscript and superscript scaling are computed relative to `eff_scale`:
  - Superscript/Subscript scale: $\text{eff\_scale} \times 0.70$
  - Double superscript/subscript scale: $\text{eff\_scale} \times 0.50$

---

## 3. Table Column Bounding Measurement

Table column widths MUST NOT be calculated from character string lengths:

$$\text{col\_width}_j = \max_{i} \left( \sum_{w \in \text{cell}_{i,j}} \text{bounds}(w).\text{width} + \text{padding} \right)$$

- If total measured table width exceeds page printable width, each column width is scaled proportionally.
- Words exceeding the scaled column width MUST wrap to the next line within the cell.
