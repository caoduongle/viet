# Contract: Stroke Geometry Boundary Containment

**Domain**: Document Rendering & Geometric Boundary Verification
**Module**: `chuviettay.layout.engine`

---

## 1. Specification

Handwritten strokes must not protrude beyond printable page margins ($y > \text{max\_page\_y}$) or individual table cell boundaries. The rendering engine evaluates line bottom boundaries prior to placing strokes onto a page.

## 2. Invariant Equations

For any rendered text line at `baseline_y`:
$$\text{effective\_descent} = \max(\text{line\_metrics.descent}, 0.3 \times \text{line\_height} \times S \times \text{scale\_mult})$$
$$\text{jitter\_tolerance} = 1.5 \times \text{jitter\_option}$$
$$\text{line\_bottom\_y} = \text{baseline\_y} + \text{effective\_descent} + \text{jitter\_tolerance}$$

### Page Boundary Clamping Rule
$$\text{If } \text{line\_bottom\_y} > \text{max\_page\_y} \implies \text{Stop / Break / Defer to Next Page}$$

### Cell Boundary Clamping Rule
For a cell with geometric vertical span $[y_{\text{top}}, y_{\text{bottom}}]$:
$$\text{If } \text{line\_bottom\_y} > y_{\text{bottom}} - \text{cell\_padding} \implies \text{Partition remaining lines into continuation cell}$$

## 3. Post-conditions for Rendered Documents

For every stroke $s$ and every point $(x, y) \in s$:
1. $y \le \text{page\_height} - \text{margin\_bottom}$ across all pages.
2. For strokes in table cell $c$:
   - $c.x \le x \le c.x + c.width$
   - $c.y \le y \le c.y + c.height$
