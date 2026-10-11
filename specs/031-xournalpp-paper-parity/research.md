# Implementation Research: Xournal++ Paper Background and Geometry Parity

**Feature Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11
**Spec**: [spec.md](spec.md)

This research artifact details the geometry, XML serialization standards, and algorithms extracted from the reference Xournal++ master branch codebase (`local data/xournalpp-xournalpp-8a5edab282632443.txt`). All implementations avoid importing GPL C++ code, reproducing purely geometric facts, mathematical formulas, and protocol contracts.

---

## 1. PDF Background Indexing and Domain Protocol

### Decision
1. In `chuviettay/model/xopp.py`: modify `pdf_background_xml(filename, pageno, domain="absolute")` to document `pageno` as 1-based (`page_index + 1`).
2. In `chuviettay/fidelity/engine.py`: pass `page.page_index + 1` and `domain="absolute"`. Ensure filename is a bare relative filename (without path prefix) so Xournal++ resolves it relative to the `.xopp` document directory.
3. Update tests: in `tests/test_docx_fidelity.py`, verify `pageno == str(idx + 1)` and `domain == "absolute"`.
4. Eliminate `domain="relative"` across the entire repository.

### Rationale
- Reference: `XmlAttrs.h` defines `Domain::NAMES = {"absolute", "attach", "clone"}`.
- Reference: `XmlParser.cpp` strictly parses `domain`: if `"absolute"` or `"attach"`, it constructs the PDF background; any other string (including `"relative"`) causes a parse failure.
- Reference: `SaveHandler.cpp` lines 40564–40570 writes:
  ```cpp
  background->setAttrib(xoj::xml_attrs::DOMAIN_STR, Domain::NAMES[Domain::ABSOLUTE]);
  background->setAttrib(xoj::xml_attrs::PAGE_NUMBER_STR, p->getPdfPageNr() + 1);
  ```
  `SaveHandler` writes `getPdfPageNr() + 1` (1-based), and `XmlParser.cpp` line 41228 parses `pageno - 1`. Therefore, transmitting a 0-based page index caused Xournal++ to read page index `-1` on the first page, resulting in failure to render.

### Alternatives Considered
- *Using `domain="attach"`*: Xournal++ uses `attach` only when the entire PDF binary is physically embedded inside the `.xopp` archive. For standard documents pointing to an external/sibling PDF, `absolute` with a relative filename is standard behavior.

---

## 2. Web SVG Paper Background Geometry (`webapp/js/paper.js`)

### Decision
Create a unified paper rendering function `renderBackgroundSvg(bg, width, height)` returning an array of SVG elements or XML strings, called by both `renderPageSvgString` and `renderPageSvgElement`.

### Mathematical Equations & Bounds
Extract geometry bounds following `getIndexBounds(min, max, step, margin, length)`:
- $\text{minBound} = \lceil \max(\text{min}, \text{margin}) / \text{step} \rceil$
- $\text{maxBound} = \lfloor \min(\text{max}, \text{length} - \text{margin}) / \text{step} \rfloor$

1. **Ruled / Lined**:
   - Spacing: $r_1$ (default $24.0\,\text{pt}$).
   - Top Header Offset: $80.0\,\text{pt}$.
   - Bottom Footer Margin: $60.0\,\text{pt}$.
   - Horizontal lines: $y = 80.0 + i \cdot r_1$ for $i \ge 0$ such that $y \le \text{height} - 60.0$.
   - Lined Margin Line:
     - For $m_1 > 0$: vertical line from $y=0$ to $\text{height}$ at $x = m_1$ (default $72.0\,\text{pt}$).
     - For $m_1 < 0$: vertical line at $x = \text{width} + m_1$ (negative denotes right margin).
     - Stroke width: $lw$ (default $0.5\,\text{pt}$).
2. **Graph**:
   - Grid pitch: $r_1$ (default $14.1732\,\text{pt} \approx 5\,\text{mm}$).
   - Margin: $m_1 \ge 0$. If $m_1 > 0$, leave margin on all four boundaries. If $rm = 1$, round margin to multiple of $r_1$.
   - Bold lines: If $bli > 0$, every $bli$-th line has width $blw$ (default $1.5\,\text{pt}$); all other lines have width $lw$ (default $0.5\,\text{pt}$).
3. **Dotted**:
   - Grid pitch: $r_1$ (default $14.1732\,\text{pt}$).
   - Dots placed at $(x, y) = (i \cdot r_1, j \cdot r_1)$.
   - Dot stroke width: $1.5\,\text{pt}$ with round line cap (or SVG circle with radius $0.75\,\text{pt}$).
4. **Isometric Graph & Isometric Dotted**:
   - Horizontal step: $x_{\text{step}} = \frac{\sqrt{3}}{2} \cdot r_1$.
   - Vertical step: $y_{\text{step}} = \frac{r_1}{2}$.
   - Margin: $r_1$.
   - Centering offset:
     $$\text{cols} = \lfloor (\text{width} - 2 r_1) / x_{\text{step}} \rfloor, \quad \text{rows} = \lfloor (\text{height} - 2 r_1) / y_{\text{step}} \rfloor$$
     $$\Delta x = \frac{\text{width} - \text{cols} \cdot x_{\text{step}}}{2}, \quad \Delta y = \frac{\text{height} - \text{rows} \cdot y_{\text{step}}}{2}$$
   - Isometric Graph draws 3 sets of parallel lines (vertical at $60^\circ$ intersections).
   - Isometric Dotted places dots at alternating triangle nodes.
5. **Music Staves**:
   - 5 lines per staff with inter-line spacing $5.0\,\text{pt}$.
   - Inter-staff spacing: $\text{STAVES\_SPACING} = 40.0\,\text{pt}$.
   - Staff height: $\text{staffHeight} = lw + 4 \times 5.0 = 20.5\,\text{pt}$ (at $lw = 0.5$).
   - Vertical step between successive staves:
     $$V_{\text{step}} = \text{STAVES\_SPACING} + \text{staffHeight} + 4 \cdot lw = 40.0 + 20.5 + 2.0 = 62.5\,\text{pt}$$
   - Margins: Left/Right $50.0\,\text{pt}$. Header $80.0\,\text{pt}$, Footer $60.0\,\text{pt}$.
6. **Colors & Dark Mode**:
   - Light mode (paper color brightness $\ge 0.5$):
     - Ruled horizontal: Dodgebllue `#40a0ff`
     - Lined margin: Deeppink `#ff0080`
     - Graph / Dotted / Iso: Silver `#bdbdbd`
     - Staves: Black `#000000`
   - Dark mode (paper color brightness $< 0.5$, e.g. `#1e1e1e`):
     - Ruled horizontal: Dark slate gray `#434343`
     - Lined margin: Midnight blue `#220080`
     - Graph / Dotted / Iso: Dark slate gray `#434343`
     - Staves: White `#ffffff`

### Rationale
Consolidating this logic inside `renderBackgroundSvg` guarantees 100% geometric equivalence between SVG preview strings and interactive DOM SVG elements, eliminating duplication and coordinate divergence.

---

## 3. Baseline Ruling Alignment (Snapping) Algorithm

### Decision
1. Add `snap_to_ruling: bool = True` to `WriteOptions`.
2. In `chuviettay/layout/engine.py`:
   - If `snap_to_ruling` is `True` and `background.style in ("ruled", "lined")`:
     - Determine ruling interval $r_1 = \text{background.spacing}$ (default $24.0\,\text{pt}$).
     - Compute line pitch:
       $$\text{pitch} = r_1 \times \max\left(1, \text{round}\left(\frac{\text{line\_h} \cdot \text{scale\_mult}}{r_1}\right)\right)$$
     - Align first line baseline: find the smallest $y = 80.0 + k \cdot r_1$ such that $y \ge \text{content\_top} + \text{eff\_line\_h}$.
     - Successive line baselines: advance by $\text{pitch}$.
     - Page break check: if next line baseline exceeds $\text{pageHeight} - 60.0$, call `new_page()`.
     - Lined margin clamping: if $m_1 > 0$, clamp $\text{line\_start\_x} \ge m_1 + 8.0$. If $m_1 < 0$, clamp $\text{line\_start\_x} + \text{width} \le \text{pageWidth} + m_1 - 8.0$.
   - If `background.style == "plain"` or `snap_to_ruling is False`:
     - Maintain original continuous layout logic unchanged.
     - Guarantees byte-exact output for `tests/test_golden_master.py`.

### Rationale
This delivers realistic handwritten text resting directly on ruled lines while preserving complete backward compatibility for plain backgrounds.

---

## 4. Background Presets and Page Format Single Source of Truth

### Decision
1. Create `BACKGROUND_PRESETS: dict[str, PageBackground]` in `chuviettay/document/page_format.py` matching `pagetemplates.ini.in`:
   - `plain`
   - `lined`, `lined_narrow` ($r_1=18$), `lined_college` ($r_1=20$), `lined_wide` ($r_1=24$)
   - `ruled` ($r_1=24$)
   - `graph`, `graph_5mm` ($r_1=14.1732$), `graph_grid` ($bli=5, blw=1.5$)
   - `dotted` ($r_1=14.1732$)
   - `iso_graph`, `iso_dotted` ($r_1=14.1732$)
   - `staves`
2. Create `get_page_catalog() -> dict[str, Any]` returning all supported paper dimensions, presets, and standard paper tones (`#ffffff`, `#ffffc8`, `#e8f4f8`, `#1e1e1e`).
3. Allow negative lengths in `parse_length(val, allow_negative=True)` to accept negative margin values like `-72pt`.
4. Add CLI arguments `--bg-preset`, `--bg-r1`, `--bg-m1`, `--bg-color` in `chuviettay/cli.py`.

---

## 5. Verification Strategy

- **Unit tests**:
  - Test PDF background XML output format (`domain="absolute"`, `pageno="1"`, bare filename).
  - Test negative margin parsing in `parse_length`, `WriteOptions.validate()`, and `PageBackground.to_xml()`.
  - Test `BACKGROUND_PRESETS` and `get_page_catalog()`.
  - Test baseline snapping formulas across various font sizes ($12\,\text{pt}, 24\,\text{pt}, 36\,\text{pt}$).
  - Test Golden Master plain hash invariant.
- **Web tests**:
  - Jest / unit tests for `renderBackgroundSvg` verifying exact line counts, line coordinates, and colors for ruled, lined, graph, dotted, iso, and staves.
