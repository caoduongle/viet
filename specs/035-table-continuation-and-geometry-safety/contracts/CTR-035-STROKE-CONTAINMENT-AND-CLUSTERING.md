# Contract CTR-035-STROKE-CONTAINMENT-AND-CLUSTERING: Physical Stroke Containment and Clamping

**Identifier**: `CTR-035-STROKE-CONTAINMENT-AND-CLUSTERING`  
**Applies to**: `DocumentLayoutEngine` (`chuviettay/layout/engine.py`)  
**Status**: Normative  

---

## 1. Specification

### C1. Physical Boundary Invariant
For every generated page with printable boundary $y \in [y_{\text{content\_top}}, y_{\text{max\_page\_y}}]$, 100% of rendered handwriting stroke coordinates $(x, y)$ MUST satisfy:
$$y \le y_{\text{max\_page\_y}}$$
No stroke point may bleed past $y_{\text{max\_page\_y}}$ under any circumstance, including random jitter, line slope, and sine baseline perturbation.

### C2. Downscaling for Indivisible Oversized Elements
When an indivisible element (such as an unsplittable math formula or single text line) is situated at the top of a fresh page (`cur_y <= pf.content_top + 1e-6`) and its expected bottom coordinate exceeds $y_{\text{max\_page\_y}}$:
1. The engine MUST compute a proportional scale factor:
   $$\text{scale\_mult} = \max\left(0.2, \min\left(1.0, \frac{y_{\text{max\_page\_y}} - \text{baseline\_y}}{\text{cur\_desc} + \text{jitter\_tol}}\right)\right)$$
2. The engine MUST pass `scale_mult` to `_render_text_line()`.
3. If generated points still exceed $y_{\text{max\_page\_y}}$ due to stochastic noise, coordinates MUST be physically clamped:
   $$y_{\text{clamped}} = \min(y, y_{\text{max\_page\_y}})$$
4. The system MUST record a diagnostic warning explicitly declaring downscaling and coordinate clamping:
   `"Dòng {l_idx} trong ô ({row}, {col}) quá khổ trên trang mới; đã co tỷ lệ {scale_mult:.2f}x và kẹp tọa độ trong giới hạn trang."`

### C3. Clamping Warning Truthfulness
The engine MUST NEVER emit a log or warning claiming that a line was "vẽ kẹp trong giới hạn" unless physical coordinate bounding has been executed and verified. For content with `cur_y > pf.content_top`, overflowing lines MUST be deferred to the next page rather than rendered out-of-bounds.
