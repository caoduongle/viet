# Feature Specification: Table Content Continuation Across Pages, True Geometry Clamping & Layout Hardening

**Feature Branch**: `033-table-content-continuation-and-geometry`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User review of commit `ce78bec` on `main`, focusing on multi-page table text content continuation (preventing text loss in tall rows and rowspan cells), true stroke geometry containment at page and cell margins (accounting for descenders, tall formulas, and handwriting jitter), pure geometric width measurement for character-level token wrapping without mutating Writer state, tight per-cell stroke bounding box testing, and end-to-end propagation of table pagination warnings to `WriteResult`, CLI, and Web UI.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Page Table Text Content Continuation with Zero Dropped Text (Priority: P1)

As a user generating handwritten documents with extensive multi-row or tall-row tables (e.g., grade transcripts, multi-line notes, technical specifications, or merged rowspan sections), I want table cells that span across page breaks to continue their text seamlessly onto subsequent pages without dropping or silently clipping any lines of text, so that the entire text content of every cell is completely preserved and legible across all pages.

**Why this priority**: When a table cell contains many lines of text or when a row group cannot fit on the current page, the pagination algorithm currently creates continuation cells with empty rendered lines (`rendered_lines=[]`) or stops rendering at the page boundary without carrying remaining lines to subsequent pages. This causes silent data loss where subsequent lines of text vanish completely from the document. Ensuring zero text loss across page boundaries is a critical correctness requirement.

**Independent Test**:
1. Create a table with a cell containing 30 lines of text (exceeding a single page's printable height).
2. Render the document to `.xopp` and extract all rendered text content across all generated pages.
3. Assert that:
   - The table spans across multiple pages (e.g., 2 or 3 pages).
   - Page 1 contains the initial subset of lines $[0..k]$ that fit vertically within printable limits.
   - Page 2 contains continuation lines $[k..m]$ with valid continuation borders.
   - 100% of the input cell's text lines are present in the output document in the correct reading order.
   - For `rowspan` cells that span page boundaries, the cell continues on the next page with remaining text and closed border caps.

**Acceptance Scenarios**:

1. **Given** a table containing an oversized single row with 25 lines of text that exceeds a single page's vertical printable space, **When** pagination slices the table, **Then** the row's lines are partitioned across consecutive pages such that lines fitting within page 1 appear on page 1, and the remaining lines continue on page 2 in a continuation row structure.
2. **Given** a table with a `rowspan=3` cell containing 15 lines of text spanning across a page break, **When** the table is paginated, **Then** the continuation cell on page 2 receives the unrendered text lines and appropriate vertical dimensions rather than being rendered as an empty placeholder box.
3. **Given** any multi-page table slicing operation, **Then** the total count and sequence of rendered lines across all page slices equals 100% of the formatted lines of the original table, with zero dropped lines and zero duplicated lines.

---

### User Story 2 - True Stroke Geometry Boundary Containment (Priority: P1)

As a user reading or printing generated handwritten notes, I want all handwritten strokes—including letter descenders (e.g., "g", "y", "p", "q", "j"), multi-level math formulas (fractions, square roots, integrals), and handwriting jitter variations—to remain strictly within the printable page area and cell bounding boxes, so that no stroke spills into page margins, footer zones, or across table borders.

**Why this priority**: Clamping based solely on baseline vertical position (`baseline_y <= max_page_y`) allows strokes that extend below the baseline (descenders up to $0.5 \times \text{line\_height}$, formulas extending tens of points downward, and pen jitter $dy \approx \pm 1.5\text{ pt}$) to protrude beyond the bottom margin or collide with cell border lines. True geometry checking must evaluate the full vertical stroke extents.

**Independent Test**:
1. Render a document containing text with heavy descenders ("quốc gia", "ngày càng phát triển") and tall math formulas at the bottom-most boundary of a page and within table cells.
2. Extract all $(x, y)$ coordinates of all rendered strokes in the generated `.xopp` file.
3. Assert that:
   - Every stroke point satisfies $y \le \text{max\_page\_y}$ (where $\text{max\_page\_y} = \text{page\_height} - \text{margin\_bottom}$).
   - Every cell stroke point satisfies $y \le \text{cell.y} + \text{cell.height} - \text{cell\_padding}$.
   - No stroke intersects or overflows the bottom border of any table cell.

**Acceptance Scenarios**:

1. **Given** a line of text whose baseline is located near the page bottom, **When** the line includes characters with descenders or handwriting jitter, **Then** the engine checks the line's maximum descent ($\text{baseline\_y} + \text{descent} + \text{jitter\_tolerance}$) against $\text{max\_page\_y}$ before placing it on the page.
2. **Given** a line that would cause its descender or formula stroke to exceed $\text{max\_page\_y}$, **When** layout evaluates the line, **Then** the engine breaks the page or defers the line/row to the next page rather than rendering a partially clipped stroke.
3. **Given** a table cell containing a formula, **Then** the cell's allocated height guarantees that the formula's maximum ascent and descent plus padding never collide with the cell's top or bottom border lines.

---

### User Story 3 - Pure Geometric Width Measurement Without Writer Mutation (Priority: P2)

As a system user formatting tables with long unbreakable tokens (such as URLs, hashes, or technical IDs), I want the layout engine to calculate candidate wrapping widths using pure geometric measurement without mutating the handwritten synthesis state or generating discarded strokes, so that formatting executes quickly and random handwriting variation remains natural and untainted.

**Why this priority**: Character-level token wrapping currently calls `Writer.token(candidate)` repeatedly in an $O(n^2)$ loop to test widths. This invokes full letter assembly, randomly selects stroke samples, updates frequency counts, and pollutes `Writer.last` and `Writer.assembled`. Separating pure geometric measurement from stroke generation eliminates state side-effects and prevents artificial bias in letter sample selection.

**Independent Test**:
1. Track the internal state of `Writer` (`counts`, `last`, `assembled`) before and after measuring token widths.
2. Verify that pure candidate width queries perform no mutations on `Writer` state.
3. Verify that `Writer.token()` is invoked only once for each final chunk that will actually be rendered.

**Acceptance Scenarios**:

1. **Given** a long token of 60 characters being wrapped into a 150 pt column, **When** candidate substrings are evaluated for fitting width, **Then** width queries do not update `Writer.counts` or `Writer.last`, nor do they record candidate fragments in `Writer.assembled`.
2. **Given** a formatted cell with wrapped tokens, **When** the final chunks are synthesized, **Then** `Writer.token()` is called exactly once per emitted line chunk, preserving the natural distribution of handwriting sample variants.
3. **Given** wrapping performance across large tables with dozens of long URLs, **Then** wrapping executes with linear time complexity relative to token length rather than $O(n^2)$ full stroke synthesis calls.

---

### User Story 4 - Cell-Level Stroke Bounding Box Containment & Visual Border Integrity (Priority: P2)

As a developer and quality maintainer, I want automated test suites to rigorously verify stroke containment at the granular level of individual table cells (not merely page-wide bounds), so that content is proven never to overlap adjacent column boundaries or horizontal divider rules.

**Why this priority**: Existing tests checked broad page bounds ($y \le 841.89 - 60$) or total table width ($x \le x_0 + \text{width}$), which would pass even if column 1 text bled horizontally into column 2 or if formulas intersected cell borders. Tight per-cell assertions guarantee visual perfection and regression prevention.

**Independent Test**:
1. Render test documents containing multi-column tables with varying alignments (left, center, right), wrapped tokens, and inline math.
2. For every cell in the table, extract the subset of strokes rendered for that specific cell.
3. Assert that for every point $(x, y)$ in those strokes:
   - $\text{cell.x} \le x \le \text{cell.x} + \text{cell.width}$
   - $\text{cell.y} \le y \le \text{cell.y} + \text{cell.height}$
4. Assert that cell border lines remain visually distinct with adequate separation from inner content strokes.

**Acceptance Scenarios**:

1. **Given** a 2-column table where column 1 contains wrapped long URLs and column 2 contains text, **When** rendered, **Then** all strokes in column 1 have $x < \text{cell\_1.x} + \text{cell\_1.width} - \text{padding}$, with zero overlap into column 2.
2. **Given** a table cell containing inline math formulas, **When** rendered, **Then** no stroke of the formula touches or crosses the cell's top, bottom, left, or right borders.
3. **Given** integration tests `test_table_wrapping_pipeline.py` and `test_table_rich_inlines.py`, **Then** the tests assert exact per-cell coordinate bounds $[x_{\min}, x_{\max}]$ and $[y_{\min}, y_{\max}]$ for every cell.

---

### User Story 5 - Layout Diagnostic Warning Propagation to WriteResult, CLI, and Web UI (Priority: P2)

As a user composing documents through either the web interface or the CLI, I want any layout adjustments, cell clamping events, or page overflow compromises to be clearly reported in the execution summary and warning display, so that I am immediately aware if table content required special handling or was adapted to fit printable dimensions.

**Why this priority**: `TableLayoutData.slice_page()` generates diagnostic warnings when rows exceed printable page height, but `DocumentLayoutEngine.render()` currently discards these warnings without attaching them to `WriteResult`. Consequently, CLI users and web UI users receive no feedback regarding table formatting compromises.

**Independent Test**:
1. Render a document containing an oversized table row that triggers vertical clamping or multi-page continuation warnings.
2. Check `WriteResult.warnings`: verify that all warnings generated during table slicing are included.
3. In the Web client bridge (`chuviettay/browser/bridge.py`), verify that `result.warnings` are forwarded into the response JSON payload and displayed in the `editor-warnings` container.
4. In the CLI (`chuviettay/cli.py`), verify that warnings are printed to the user report if present.

**Acceptance Scenarios**:

1. **Given** a table row whose required height exceeds the available page space, **When** layout slices the table, **Then** the diagnostic warning generated by `slice_page()` is captured and included in `WriteResult.warnings`.
2. **Given** `WriteResult` returned to the Web worker bridge, **When** warnings are present, **Then** the bridge includes them in the returned JSON object under the `warnings` array, causing the `#editor-warnings` banner in the Web UI to display them.
3. **Given** `WriteResult` processed by the CLI or GUI, **When** warnings exist, **Then** the formatting report presents the warnings clearly to the user without interrupting normal document output.

---

## Edge Cases

- **Single row taller than two full pages**: If a single cell contains text exceeding multiple pages, the continuation engine must partition lines across multiple consecutive pages ($k_1$ lines on page 1, $k_2$ lines on page 2, $k_3$ lines on page 3) until all lines are exhausted, maintaining top and bottom continuation borders on each intermediate slice.
- **Table cell containing a single unbreakable token that is taller than a page**: When an enormous token or atomic block exceeds page height, the system must clamp safely, emit an explicit warning, and avoid infinite pagination loops.
- **Rowspan cell spanning across multiple pages while adjacent rows end**: When a multi-row span continues past the rows it originally accompanied, adjacent cells on subsequent pages must render appropriate empty continuation cells or allow subsequent rows to align correctly beside the continuing cell.
- **Lines containing both tall formulas and characters with deep descenders**: The effective descent of the line must be computed as $\max(\text{text\_descent}, \text{math\_descent}) + \text{jitter\_tolerance}$, ensuring that compound vertical height is never underestimated.
- **Empty table cells or cells with only whitespace**: Continuation logic must handle empty cells without index errors or division by zero, preserving empty column spaces across page breaks.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The table pagination engine MUST partition cell lines (`rendered_lines` and `line_metrics`) across page slices so that lines that cannot fit on the current page are carried forward into continuation cells on subsequent pages.
- **FR-002**: Continuation cells created during table slicing MUST retain their remaining `rendered_lines`, `line_metrics`, and adjusted height, ensuring zero dropped lines across page boundaries.
- **FR-003**: When an individual table row exceeds the available page height, the engine MUST allow the row's content to continue across page boundaries, updating slice progress monotonically without discarding unrendered lines.
- **FR-004**: The rendering engine MUST calculate line bottom boundaries using $\text{baseline\_y} + \text{effective\_descent} + \text{jitter\_margin}$ rather than baseline position alone.
- **FR-005**: The rendering engine MUST NOT place any line or stroke whose bottom boundary exceeds the printable bottom margin ($\text{page\_height} - \text{margin\_bottom}$).
- **FR-006**: When evaluating long unbreakable tokens for character-level wrapping, the engine MUST use non-mutating geometric width measurement that does not modify `Writer.counts`, `Writer.last`, or `Writer.assembled`.
- **FR-007**: The engine MUST invoke `Writer.token()` only once per final wrapped chunk for actual stroke synthesis, preserving letter selection randomness and cache integrity.
- **FR-008**: All generated strokes for any table cell MUST remain strictly within that cell's horizontal bounding box ($x \in [\text{cell.x}, \text{cell.x} + \text{cell.width}]$) and vertical bounding box ($y \in [\text{cell.y}, \text{cell.y} + \text{cell.height}]$).
- **FR-009**: Mathematical formulas in table cells MUST have adequate padding from cell borders, ensuring formula strokes never intersect or overlap border lines.
- **FR-010**: `WriteResult` MUST include a `warnings: list[str]` field to store layout and formatting diagnostic messages.
- **FR-011**: `DocumentLayoutEngine.render()` MUST collect all warnings generated during table pagination and attach them to the returned `WriteResult.warnings`.
- **FR-012**: The Web browser bridge (`chuviettay/browser/bridge.py`) MUST merge `WriteResult.warnings` into the response payload so they are surfaced in the Web UI `#editor-warnings` container.
- **FR-013**: The CLI reporting module MUST include any layout warnings in `WriteResult` in the user summary report.
- **FR-014**: Existing Plain paper golden master test hashes MUST remain 100% invariant, ensuring table layout enhancements introduce zero regression to continuous text layout.
- **FR-015**: All architecture rules enforced by `tests/test_architecture.py` MUST remain fully compliant (zero MVC violations across Model, View, CLI, and Controller).

---

### Key Entities

- **LaidOutCell**: Represents a positioned table cell with geometric bounds $(x, y, \text{width}, \text{height})$, associated source cell, logical row/column indices, span information, `rendered_lines`, `line_metrics`, and `is_continuation` flag.
- **TableLayoutData**: Container for resolved table geometry including column widths, row heights, matrix of `LaidOutCell` objects, and diagnostic `warnings`.
- **LineVerticalMetrics**: Measurement structure recording baseline ascent, descent, total height, and line width for text and formula lines.
- **WriteResult**: Structured output record returned by the layout engine, capturing line counts, stroke counts, token statistics, missing glyphs, generated pages, and diagnostic `warnings`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of text lines in multi-page tables are preserved and rendered across pages with 0 dropped lines and 0 duplicate lines.
- **SC-002**: 100% of generated strokes in all test cases satisfy $y \le \text{page\_height} - \text{margin\_bottom}$, with zero strokes protruding past printable page boundaries.
- **SC-003**: 100% of table cell strokes remain strictly inside their respective cell bounding boxes ($x \in [\text{cell.x}, \text{cell.x} + \text{cell.width}]$ and $y \in [\text{cell.y}, \text{cell.y} + \text{cell.height}]$) with zero border overlap.
- **SC-004**: Character-level token wrapping executes with zero mutations to `Writer.counts` and `Writer.last` during candidate width measurement.
- **SC-005**: 100% of table layout diagnostics generated during slicing are propagated to `WriteResult.warnings` and surfaced to Web UI and CLI.
- **SC-006**: The full test suite passes with zero failures, zero regressions on Golden Master SHA-256 hashes, and zero MVC violations.

---

## Assumptions

- Table cells continuation across pages assumes standard reading order (top-to-bottom) for multi-line content.
- Jitter margin tolerance of $1.5\text{ pt}$ is sufficient to account for random handwriting perturbation along the vertical axis.
- When a single row is partitioned across multiple pages, maintaining horizontal border caps on each page slice provides clear visual cues to readers that the table is continuing.
- Pure geometric measurement can query font glyph advances or bank sample widths directly without altering pseudo-random sequence state.
- Existing Plain paper layout remains decoupled from table layout, ensuring golden master hashes are unaffected.
