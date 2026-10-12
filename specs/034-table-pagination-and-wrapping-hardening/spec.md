# Feature Specification: Table Pagination, Token Wrapping, Line Spacing Anti-Collision, and Math Accent Hardening

**Feature Branch**: `034-table-pagination-and-wrapping-hardening`

**Created**: 2026-10-12

**Status**: Ready for Planning

**Input**: User description: "Rà soát repo viet — lần mới nhất trên commit 4af2dd3. Xử lý triệt để: (1) P1: Nhánh kẹp mép dưới không âm thầm nuốt dòng chưa vẽ mà phải chuyển tiếp sang trang sau kèm cảnh báo nếu không thể ngắt; (2) P2: Cập nhật chỉ số hàng và phạm vi ô gộp sau khi chèn hàng tiếp nối động để tránh sai lệch viền và nhóm hàng; (3) P2: Đường xử lý token dài dùng phép đo thuần một lần, không sinh nét thử làm bẩn trạng thái Writer, tối ưu độ phức tạp đo từ O(n^2) về O(n); (4) P2: Giữ nguyên dòng trống có chủ đích trong ô bảng; (5) Giới hạn hình học nét vẽ sau biến đổi (jitter, rotation) bảo đảm nằm trong ô và trang; (6) Bộ kiểm thử bảo toàn nội dung chính xác (exact line match, không lặp, không sót, test đa trang kết hợp rowspan + ô rỗng + công thức cao); (7) P1: Sàn chống dính dòng (anti-collision line spacing floor) — dù chỉnh khoảng cách dòng nhỏ (kể cả 1pt hay bất kỳ số dương nào), các dòng văn bản và các hàng trong bảng tuyệt đối không dính/đè lên nhau; (8) P2: Tinh chỉnh vị trí dấu mũ toán học (\bar, \hat, \tilde, \vec...) trên các ký tự như \bar{x}, \hat{x} đặt sát đỉnh chữ tự nhiên, không nhảy lên cao bất thường."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lossless Bottom-Margin Overflow Protection and Remainder Rollover (Priority: P1)

As a user generating multi-page handwritten documents with dense table cells, I need all text and mathematical formulas within table cells to be rendered fully across pages without any lines being silently dropped at page bottom margins, so that the generated document never loses information when content height exceeds estimated layout bounds.

**Why this priority**: Silently dropping content when a line extends beyond the printable bottom margin is a critical data loss defect (P1). Users rely on exact textual integrity; losing sentences or formulas destroys document validity.

**Independent Test**: Provide a table cell containing 40 numbered text lines and tall inline formulas rendered near the bottom margin of a page. Verify that 100% of the numbered lines appear across the page sequence, with no lines dropped when the bottom margin is reached and no duplicated lines on the succeeding page.

**Acceptance Scenarios**:

1. **Given** a table row placed near the bottom margin where rendered text or formula descenders exceed the printable area, **When** the page reaches capacity, **Then** all unrendered lines are cleanly transferred to a continuation row on the next page rather than being dropped, and a layout warning is issued if a single indivisible item exceeds total page height.
2. **Given** an indivisible atomic element (such as an oversized standalone math block) that cannot fit within remaining page space, **When** it cannot be split, **Then** the system defers the element to a fresh page or proportionally scales it with an explicit user-facing warning rather than silently discarding it.

---

### User Story 2 - Anti-Collision Line Spacing & Table Row Height Floor (Priority: P1)

As a user customizing document layout with custom line spacing values, I need the rendering engine to enforce a physical anti-collision floor so that setting very small line spacing values (such as 1pt or any arbitrary positive value) never causes consecutive lines of text or table rows to collide, overlap, or have border lines strike through text numbers.

**Why this priority**: When a user sets a small line spacing value (e.g. 1pt), they expect compact spacing or tight leading, not a complete structural breakdown where lines collide directly on top of each other and table borders cut through text. This renders the document completely illegible and destroys usability.

**Independent Test**: Configure the document line spacing setting to `1.0pt`. Render a multi-line paragraph and a table with numeric cells. Assert that:
1. In regular text, the vertical distance between consecutive baselines is at least the physical glyph height plus minimum clearance ($h_{\text{baseline-to-baseline}} \ge \text{glyph\_box\_height} + 1.0\text{pt}$).
2. In tables, each row's height is at least the cell text bounding height plus $2 \times \text{cell\_padding}$, and horizontal border lines do not intersect any glyph bounding boxes.

**Acceptance Scenarios**:

1. **Given** a custom line parameter set to a value smaller than the physical font height (e.g. `line=1.0`), **When** calculating vertical line steps, **Then** the engine clamps the line height to a safe minimum floor based on the font/bank metrics ($\ge \text{ascent} + \text{descent} + \text{clearance}$) or interprets the user parameter as an extra inter-line gap, ensuring zero glyph collision between lines.
2. **Given** a table rendered with compact line spacing, **When** calculating row heights, **Then** each row height is guaranteed to exceed the visual height of contained text by at least $2 \times \text{cell\_padding}$, preventing horizontal borders from intersecting cell content.

---

### User Story 3 - Natural Math Accent Positioning and Compact Ascent Metrics (Priority: P2)

As a user writing mathematical expressions containing accented symbols (such as $\bar{x}$, $\bar{y}$, $\hat{x}$, $\tilde{x}$, $\vec{x}$, or $x_i - \bar{x}$), I need accents and overbars to be positioned tightly and naturally directly above the base character rather than floating abnormally high in the air, and I need the accent metrics not to artificially balloon line spacing.

**Why this priority**: Overbars and hats floating high above characters (touching the line above or hovering into empty space) look unnatural, violate handwriting conventions, and cause layout engines to inflate vertical line height (`extra_top`), causing entire lines to jump erratically.

**Independent Test**: Render formulas with accented symbols ($\bar{x}, \bar{y}, \hat{x}, \vec{x}$). Measure the vertical gap between the top point of the base glyph $x$ and the accent stroke. Verify that the optical gap is between $0.08 \times xh$ and $0.18 \times xh$, and that the overall symbol ascent remains balanced without triggering oversized line height expansion.

**Acceptance Scenarios**:

1. **Given** an accented math symbol such as $\bar{x}$ or $\hat{x}$, **When** calculating the accent stroke position, **Then** the accent is placed immediately above the base glyph's actual visual top with a tight optical clearance, rather than using an inflated vertical offset.
2. **Given** an inline math expression containing $\bar{x}$ inside normal text or a table cell, **When** computing line vertical metrics, **Then** the accent ascent is tightly bounded so that it does not cause adjacent text baselines to shift abnormally.

---

### User Story 4 - Row Index and Rowspan Synchronization for Dynamic Continuation Rows (Priority: P2)

As a user creating complex structured tables with multi-row merged cells (`rowspan`) and rows that exceed single-page height, I need the internal table structure and cell coordinates to remain consistent after splitting rows across pages, so that table borders, cell grouping, and background highlights are drawn accurately on every page.

**Why this priority**: When a long row is dynamically split across pages by inserting continuation rows into the layout data, subsequent rows shift. If cell row indices and multi-row spans are not synchronized, border grids and cell coordinates become desynchronized, causing misaligned borders, broken cell merges, or layout crashes on pages 2 and 3.

**Independent Test**: Render a 3-page document containing a table with both a 50-line cell in column 1 and a `rowspan=3` merged cell across subsequent columns. Verify that all horizontal and vertical borders align precisely with cell boundaries on all 3 pages and that no borders cut through merged cells.

**Acceptance Scenarios**:

1. **Given** a table where row $R$ is split into an initial slice and a continuation row $R+1$, **When** continuation rows are inserted into the layout structure, **Then** all subsequent cells ($R \ge R+2$) have their logical row indices updated, and any active multi-row spans intersecting the split boundary are properly adjusted.
2. **Given** an alternative slice-generation design that computes continuation slices without mutating the original table structure, **When** generating page slices, **Then** each slice independently maintains exact local row heights, border coordinates, and cell spans without modifying immutable source definitions.

---

### User Story 5 - Single-Pass Zero-Mutation Token Splitting with O(N) Prefix Measurement (Priority: P2)

As a user rendering tables containing long unbroken tokens (such as URLs, technical codes, or file paths) narrower than column widths, I need the text wrapping pipeline to split long tokens without altering the handwriting synthesis engine's internal selection state or repeating candidate synthesis, ensuring high rendering speed and reproducible visual output.

**Why this priority**: Measuring candidate character prefixes by calling full token synthesis repeatedly causes $O(N^2)$ quadratic slowdown on long strings and mutates random number generator / Markov word-assembly states before final rendering. This creates jitter artifacts, non-deterministic sample choices, and severe performance bottlenecks.

**Independent Test**: Render a table cell containing a 300-character unbroken URL. Assert that the text wrapping completes in linear time $O(N)$ with respect to character count, and verify that the handwriting synthesis model state (assembled words count, character frequency logs, RNG seed progression) remains identical before and after candidate width measurement.

**Acceptance Scenarios**:

1. **Given** an unbroken text token wider than the usable column width, **When** calculating wrap boundaries, **Then** candidate break points are determined exclusively via non-mutating pure width estimation using cumulative prefix widths in $O(1)$ per step and $O(N)$ total time.
2. **Given** final determined token segments, **When** emitting stroke data, **Then** stroke generation is invoked exactly once per final segment, with zero tentative trial generations polluting synthesis state.

---

### User Story 6 - High-Fidelity Retention of Intentional Empty Lines in Cells (Priority: P2)

As a user formatting tables with multi-paragraph text or intentional blank lines between paragraphs, I need empty lines and paragraph breaks to be visually preserved as vertical spacing within table cells, matching the spacing expected from document editors.

**Why this priority**: Empty lines inside table cells represent deliberate visual separation (e.g., bulleted points separated by spaces, multi-line addresses). Silently collapsing them reduces layout fidelity and compromises parity with imported DOCX/Markdown documents.

**Independent Test**: Render a table cell with text content consisting of "Header Line", an intentional empty blank line, and "Body Line". Verify that the vertical distance between the two text lines accounts for the empty line height, and that the cell height reflects all 3 logical lines.

**Acceptance Scenarios**:

1. **Given** a table cell containing paragraph breaks or explicit newlines with an empty line in between, **When** formatting cell lines, **Then** the empty line is preserved as a blank layout line with standard vertical line height rather than being pruned.
2. **Given** an entirely empty cell, **When** computing cell layout, **Then** the cell maintains minimum readable height without generating phantom strokes or crashing pagination.

---

### User Story 7 - Stroke Geometry Boundary Containment and Invariant Verification (Priority: P3)

As a user expecting professional handwriting visual quality, I need all generated strokes to stay strictly within their cell horizontal bounds and printable page margins even after random jitter, baseline variation, and slant transformations are applied.

**Why this priority**: While baseline estimation protects most content, extreme character descenders, tall mathematical accents, or handwriting jitter can bleed across column separators or page bottom margins. Verifying actual post-transformation stroke coordinates guarantees visual containment.

**Independent Test**: Render tables with varying degrees of jitter (from 0.0 to 2.0) containing mixed text, descenders (e.g., 'g', 'y', 'p', 'q'), and tall math expressions. Execute geometric invariant checks asserting that $100\%$ of generated stroke coordinates lie within the allocated cell bounding box (with configurable tolerance) and strictly above the bottom printable page limit.

**Acceptance Scenarios**:

1. **Given** table text rendered with natural handwriting jitter enabled, **When** inspecting final point coordinates, **Then** all points in column $C$ remain within column $C$'s horizontal boundaries without bleeding into adjacent columns.
2. **Given** lines rendered near the page bottom, **When** post-transformation stroke points are verified, **Then** no stroke points exceed the defined page bottom margin.

---

### Edge Cases

- **Extreme Tiny Line Spacing ($0 < \text{line} < 5\text{pt}$)**: System must enforce the anti-collision safety floor, preventing zero or overlapping vertical steps.
- **Combined Tiny Line Spacing with Table Borders**: Rows must maintain sufficient height so border strokes never intersect text numbers or math expressions.
- **Stacked Multiple Accents ($\hat{\bar{x}}$ or $\vec{\bar{x}}$)**: Accents stacked on top of each other must maintain consistent relative gaps without exponential ballooning.
- **Accents on Tall Glyphs ($\bar{d}, \bar{h}, \hat{k}, \bar{B}$)**: Accents on glyphs with tall ascenders must clear the ascender without clipping or flying away into preceding lines.
- **Indivisible Oversized Math Block**: Single formulas taller than a blank page must scale down or emit a structured warning to prevent infinite page loops.
- **Cascading Splits with Multi-Page Spans**: Tables where multi-row merged cells span across 3 or more page breaks simultaneously.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect when a table line's bottom extent (including baseline, glyph descent, and maximum transformation tolerance) exceeds the printable page bottom margin.
- **FR-002**: When a line cannot fit within the remaining vertical space of the active page, the system MUST NOT discard the line; it MUST retain all unrendered lines and transfer them to a continuation cell on the subsequent page.
- **FR-003**: The system MUST enforce a physical anti-collision minimum line height floor ($\text{line\_height} \ge \text{safe\_glyph\_height}$) ensuring that setting arbitrary small positive line parameters never causes consecutive lines to collide.
- **FR-004**: In table layout, the system MUST enforce a minimum row height floor based on visual text height plus cell padding, guaranteeing that table border lines never intersect cell text.
- **FR-005**: Mathematical accents (`\bar`, `\hat`, `\tilde`, `\vec`, `\dot`, etc.) MUST be anchored tightly to the base glyph's visual bounding top with natural optical clearance ($0.08\text{xh}$ to $0.18\text{xh}$), eliminating excessive vertical separation.
- **FR-006**: The vertical metric calculation for accented symbols MUST keep ascent tightly bounded to avoid artificially triggering oversized `extra_top` line displacements.
- **FR-007**: When table rows are dynamically partitioned across page boundaries, the system MUST maintain consistent row indices and multi-row spans (`rowspan`) across all subsequent cells.
- **FR-008**: The table pagination slicing mechanism SHOULD prefer immutable slice generation where continuation slices are derived without destructive in-place mutation of the parent table structure.
- **FR-009**: Long text tokens exceeding usable column width MUST be segmented using non-mutating width measurement algorithms that have zero side-effects on the synthesis engine's internal state.
- **FR-010**: The token segmentation algorithm MUST compute candidate break positions in $O(N)$ linear time complexity over token length $N$ using cumulative width calculations rather than repeated full-string measurements.
- **FR-011**: Final stroke generation for segmented token chunks MUST occur exactly once per chunk, prohibiting speculative trial stroke generations that pollute word assembly statistics.
- **FR-012**: Intentional empty lines and blank paragraphs within table cells MUST be preserved as distinct blank lines with defined vertical height rather than being dropped during line formatting.
- **FR-013**: The layout engine MUST verify that all post-transformation stroke points for table content reside within designated page printable boundaries and within allocated cell column boundaries.
- **FR-014**: If an indivisible cell item exceeds the total usable height of an entire blank page, the system MUST scale the item to fit or log a structured warning and prevent infinite page allocation.
- **FR-015**: The automated test suite MUST enforce exact-count line assertions ($N_{\text{rendered}} = N_{\text{expected}}$) and verify that 0% of lines are lost or duplicated.
- **FR-016**: Automated tests MUST validate collision-free rendering and border clearance when line spacing is configured to extreme low values (e.g. `1.0pt`).
- **FR-017**: Automated tests MUST validate accent stroke proximity relative to the base glyph ($y_{\text{accent}} - y_{\text{base\_top}} \le 0.25 \times xh$).

### Key Entities

- **LineHeightPolicy**: Rules and clamping thresholds defining effective baseline-to-baseline stepping and anti-collision floors.
- **AccentGeometry**: Placement parameters and bounding offsets for overbars, hats, vectors, and tildes relative to base glyph heights.
- **TableSlice**: A discrete vertical segment of a table allocated to a single document page, containing the subset of rows (or partial continuation rows) that fit within the page's vertical capacity.
- **LaidOutCell**: A positioned cell instance with calculated $(x, y, w, h)$, rendered stroke line bundles, vertical metrics, and a continuation flag (`is_continuation`).
- **ContinuationRemainder**: The state representing unrendered lines, line metrics, and span adjustments deferred from an overflowing cell to the next page.
- **BorderLookupGrid**: A two-dimensional occupancy and span lookup structure used to determine horizontal and vertical border visibility without rendering borders through merged cells.
- **TokenChunk**: An individual character segment derived from wrapping an unbroken long token to fit within a cell's usable width.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: **Zero Text Overlap at Extreme Line Spacing**: When line spacing is configured to `1.0pt`, vertical clearance between consecutive text lines is strictly greater than 0, and 0% of characters or table border strokes intersect.
- **SC-002**: **Tight Math Accent Proximity**: For accented symbols ($\bar{x}, \bar{y}, \hat{x}, \vec{x}$), the vertical gap between the top of the base glyph and the accent stroke does not exceed $0.2 \times xh$, matching natural handwriting appearance.
- **SC-003**: **Zero Text Loss Across Page Breaks**: 100% of lines across multi-page tables (tested up to 100 lines and across 4+ pages) are present in the final rendered output with zero omitted or duplicated lines.
- **SC-004**: **Exact Border Alignment**: In tables combining tall rows and multi-row merged cells (`rowspan`), 100% of border segments match logical cell outer boundaries with zero stray borders cutting across merged areas.
- **SC-005**: **Linear Token Wrapping Performance**: Token splitting on arbitrary strings up to 1,000 characters executes in under 5 milliseconds with $O(N)$ time complexity.
- **SC-006**: **Zero Synthesis Mutation**: Synthesizer state metrics show identical pre- and post-values during width measurement.
- **SC-007**: **Blank Line Fidelity**: 100% of intentional blank lines in cell content produce equivalent vertical whitespace in the rendered document.
- **SC-008**: **100% Geometric Containment**: 0% of stroke points fall below the page bottom printable margin or outside cell column boundaries beyond allowed styling tolerances.

## Assumptions

- When a user enters a line spacing value smaller than font height (e.g. 1pt), they intend either an inter-line gap or minimum compact spacing, which must be safely bounded to maintain legibility.
- Handwriting fonts and vector glyphs have an established base $x$-height ($xh \approx 7.0 - 8.0\text{pt}$), and ascenders typically reach $1.5 - 2.0\text{xh}$.
- Accents should scale harmoniously with the base glyph scale and maintain consistent visual proximity across font variations.
- Table columns have a minimum width threshold, and cells maintain minimum inner padding.
