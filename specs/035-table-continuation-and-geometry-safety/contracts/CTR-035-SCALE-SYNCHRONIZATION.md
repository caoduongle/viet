# Contract CTR-035-SCALE-SYNCHRONIZATION: Scale Synchronization and Anti-Collision Under `auto_xh`

**Identifier**: `CTR-035-SCALE-SYNCHRONIZATION`  
**Applies to**: `DocumentLayoutEngine`, `resolve_effective_line_height` (`chuviettay/layout/engine.py`)  
**Status**: Normative  

---

## 1. Specification

### C1. Scale Resolution Sequence
In `DocumentLayoutEngine.__init__`:
1. The engine MUST calculate the finalized effective character scaling factor `self.S` and pen width scale `self.effective_wscale` BEFORE calling `resolve_effective_line_height`.
2. If `auto_xh` is enabled (`getattr(opts, "auto_xh", False)`):
   $$\text{self.S} = \text{opts.scale} \times \frac{\text{target\_xh}}{\text{current\_xh}}$$
3. `resolve_effective_line_height` MUST be invoked with the finalized `self.S`:
   $$\text{self.line\_h} = \text{resolve\_effective\_line\_height}(\text{opts.line}, \text{bank}, \text{self.S})$$

### C2. Anti-Collision Floor Scaling
1. The anti-collision clearance floor:
   $$\text{safe\_line\_floor} = \max\left(1.4 \times \text{font\_xh} \times \text{scale}, 0.65 \times \text{default\_bank\_line}\right)$$
   MUST scale linearly with the finalized `scale = self.S`.
2. When the user requests a small line spacing $0 < \text{requested\_line} < \text{safe\_line\_floor}$, the effective line height MUST be:
   $$\text{effective\_line\_h} = \text{safe\_line\_floor} + \text{requested\_line}$$
3. Adjacent text lines and table cell contents rendered under `auto_xh` MUST maintain zero physical character stroke collisions.
