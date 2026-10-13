# Feature Specification: Table Continuation, Rowspan Stability, and Geometry Safety Hardening

**Feature Branch**: `035-table-continuation-and-geometry-safety`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Rà soát repo viet lần mới nhất: Nhánh vẽ kẹp chưa thực sự kẹp tọa độ nét (P1); Định vị ô tiếp nối có thể không tìm được đúng ô nguồn khi có rowspan qua nhiều trang (P1); Ô rowspan được sao chép nhưng phạm vi gộp có thể bị chồng lấn (P2); Bẻ token dài cần bảo toàn mẫu nguyên từ và độ rộng thực tế (P2); Khoảng cách dòng cần đồng bộ với chế độ auto_xh (P2); Củng cố kiểm thử bằng nội dung định danh DONG_XXXX và tách benchmark thời gian cố định khỏi CI (P3)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Physical Stroke Boundary Clamping & Guaranteed Page Containment (Priority: P1)

A user exports a document containing oversized tables, tall formulas, or content positioned near the page bottom. The layout engine ensures that 100% of rendered handwriting strokes physically reside within the printable margins of each page. When an indivisible block appears at the top of a fresh page and exceeds the available vertical height, the system safely downscales the content to fit within printable bounds and records an explicit, verifiable warning, rather than rendering ink past the page edge while falsely claiming clamping.

**Why this priority**: Preventing ink from clipping past the page boundary or bleeding into unprintable margins is a foundational geometric guarantee. Falsely logging that a line was clamped when ink still exceeds margins violates user trust and produces malformed exports.

**Independent Test**: Render an oversized atomic element (e.g. an indivisible tall formula or single oversized row) at the top of a page. Verify that 100% of stroke point coordinates satisfy $y_{\text{stroke}} \le y_{\text{page\_bottom\_margin}}$ and that the system logs an accurate downscaling notification.

**Acceptance Scenarios**:

1. **Given** a table row containing text or math lines that exceed the bottom margin of an existing page, **When** layout occurs, **Then** the overflowing lines are cleanly deferred to the next page rather than truncated or drawn out of bounds.
2. **Given** an oversized indivisible block situated at the top of a fresh page that exceeds total page height, **When** rendering occurs, **Then** the block is proportionally scaled down to fit within printable margins, and all resulting stroke coordinates remain strictly within the printable page rectangle.
3. **Given** any rendered document, **When** geometry analysis checks stroke coordinates, **Then** zero strokes exist outside printable margins, and no system warnings claim clamping unless stroke coordinates were physically restricted.

---

### User Story 2 - Stable Cell Identity Tracking for Multi-Page Rowspan Continuation (Priority: P1)

A user formats a complex data table containing multi-row cells (`rowspan > 1`) that spans three or more pages. When a cell in this table overflows a page boundary, the layout engine tracks each continuation cell back to its unique originating source cell identity, regardless of slice row offsets or column position. This ensures that remaining lines roll over into the correct target cell on subsequent pages without dropping text or accidentally overwriting adjacent cells in the same column.

**Why this priority**: Without stable cell identity tracking across multi-page slices, multi-row cells easily desynchronize, causing text to vanish or overwrite neighbouring data in long statistical or scientific tables.

**Independent Test**: Render a 4-page table where Column 0 contains a cell with `rowspan=4` and 60 numbered text lines, alongside normal rows. Verify that 100% of the 60 lines appear across the pages in exact numerical sequence with zero lost or duplicated lines and zero corrupted adjacent cells.

**Acceptance Scenarios**:

1. **Given** a cell spanning multiple rows (`rowspan > 1`) that exceeds the page height, **When** the page slice boundary is reached, **Then** the remaining unrendered lines are stored into a continuation cell explicitly linked to the source cell by a persistent identity.
2. **Given** a multi-page table spanning 3 or more pages, **When** consecutive continuations occur, **Then** each page slice correctly resolves the active source cell and continues appending lines without relying on guessed row indices.
3. **Given** adjacent cells sharing the same column index across different rows, **When** one cell rolls over, **Then** the other cells retain their original content completely unaltered.

---

### User Story 3 - Non-Overlapping Rowspan Partitioning & Border Alignment (Priority: P2)

A user creates a table where tall multi-row cells sit alongside regular rows. When the layout engine dynamically splits a tall row across page boundaries, the spanning range (`rowspan`) is explicitly partitioned between the origin slice and the continuation slice. This prevents both copies from claiming overlapping grid positions, ensures that grid occupancy remains non-conflicting, and guarantees that border lines never slice through merged cells.

**Why this priority**: Overlapping `rowspan` ranges corrupt the table grid geometry, causing border rendering algorithms to draw spurious grid lines through merged cells and shifting content columns horizontally or vertically.

**Independent Test**: Render a table with merged multi-row cells split across multiple pages. Inspect the generated border geometry and cell occupancy grid to verify that merged cell areas have zero interior divider lines and that all borders strictly trace cell perimeters.

**Acceptance Scenarios**:

1. **Given** a cell spanning $N$ rows that is split across a page boundary after row $K$, **When** the slice is formed, **Then** the origin cell covers rows $0 \dots K$ and the continuation cell covers the remaining rows, with zero overlapping span range.
2. **Given** a table with merged cells spanning multiple pages, **When** table border strokes are generated, **Then** no horizontal or vertical border lines cut through any merged cell area on any page.
3. **Given** cells in columns adjacent to a splitting merged cell, **When** the table is rendered, **Then** their contents remain in their respective logical columns without horizontal displacement.

---

### User Story 4 - Whole-Word Aware Hybrid Token Wrapping (Priority: P2)

A user formats text and tables containing words with specialized handwriting models (such as pre-composed words, ligatures, or mathematical terms). When wrapping text to fit column widths, the layout engine first checks if a whole-word model is available and fits the column. If the unbroken word genuinely exceeds the available width, the engine performs linear prefix partitioning while accounting for actual rendered dimensions.

**Why this priority**: Blindly splitting text based solely on isolated character advance widths destroys whole-word handwriting aesthetics and can mistakenly break words that would have fit comfortably as whole-word samples.

**Independent Test**: Render a table column containing words present in the handwriting bank as pre-composed samples. Verify that words fitting the column boundary are preserved as single units, while truly oversized unbroken tokens wrap linearly without overflowing column boundaries.

**Acceptance Scenarios**:

1. **Given** a word that exists as a pre-composed sample in the handwriting bank, **When** its rendered width fits the available column width, **Then** it is rendered as a whole unit without character splitting.
2. **Given** an unbroken token that genuinely exceeds the available width, **When** wrapping occurs, **Then** it is partitioned into sub-tokens using pure measurement in linear time without mutating synthesizer state.
3. **Given** a synthesized sub-token whose final rendered width slightly exceeds estimated width due to optical adjustments, **When** laid out, **Then** the layout engine accommodates or adjusts the line boundary in a single pass without repeated trial generation.

---

### User Story 5 - Synchronized Line Height and Character Sizing under Auto-Scale (Priority: P2)

A user enables automatic character height scaling (`auto_xh`) or specifies custom target glyph heights. The layout engine finalizes the effective scaling factor *before* determining physical line heights and safe anti-collision floors. This ensures that line spacing, cell padding, and baseline separation scale proportionally with the actual rendered letter size.

**Why this priority**: When character size is modified after line spacing is already fixed, small line spacing settings can cause scaled glyphs to collide, while large scalings can create disproportionate gaps. Calculating effective scaling first guarantees physical harmony.

**Independent Test**: Render documents with `auto_xh` enabled across target character heights of 6.0 pt, 7.94 pt, and 10.0 pt, combined with small line spacing (`line=1.0pt`). Assert that adjacent lines and table borders maintain physical anti-collision clearance proportional to the target character height.

**Acceptance Scenarios**:

1. **Given** a document rendered with `auto_xh` enabled, **When** the layout engine initializes, **Then** the effective character scale is computed first, and the safe line height floor is calculated based on the finalized scale.
2. **Given** any combination of `auto_xh` and small requested line spacing, **When** multi-line text and tables are rendered, **Then** consecutive text baselines remain separated by at least the physical glyph clearance floor.
3. **Given** characters with deep descenders (e.g. 'g', 'q', 'y') rendered under scaled mode, **When** positioned above table borders or subsequent lines, **Then** no strokes intersect lower boundaries.

---

### User Story 6 - Labeled Content Verification & Deterministic CI Testing (Priority: P3)

Developers and automated CI pipelines run the test suite to verify table continuation and token wrapping. Tests verify 100% content preservation using unique sequential line identifiers (e.g. `LINE_0001`, `LINE_0002`...) rather than simple line counts, ensuring no lines are dropped or duplicated. Furthermore, linear algorithmic complexity is verified through call-count invariants rather than wall-clock timing thresholds that could flake on slow or virtualized CI runners.

**Why this priority**: Simple line count assertions can pass even if lines are swapped, lost, or duplicated. Flaky wall-clock benchmarks cause false CI build failures. Deterministic labeled assertions provide undeniable verification of content preservation and algorithmic scaling.

**Independent Test**: Run the automated test suite on diverse hardware environments. Assert that all multi-page continuation tests verify complete ordered sets of labeled line IDs, and that algorithmic complexity checks pass deterministically without wall-clock flakiness.

**Acceptance Scenarios**:

1. **Given** a multi-page table continuation test, **When** output lines are verified, **Then** each unique line identifier is confirmed to appear exactly once and in strict sequential order across the generated pages.
2. **Given** an algorithmic efficiency test for long token wrapping, **When** executed in CI, **Then** validation relies on measurement invocation counts and input scaling invariants rather than fixed millisecond thresholds.

---

### Edge Cases

- What happens when a single mathematical formula or atomic glyph is taller than an entire blank page?
  The system proportionally downscales the element to fit precisely within the printable height, logs a structured downscaling notice, and guarantees all strokes stay within page margins.
- What happens when a cell with `rowspan=5` splits across 3 distinct pages while adjacent columns contain varying row heights?
  Each page slice maintains the persistent origin cell identity, correctly distributing the remaining lines without index desynchronization.
- What happens when a pre-composed word sample has a width very close to the column boundary?
  The layout engine uses pure whole-word measurement to determine whether it fits before deciding whether character-level partitioning is necessary.
- What happens when `auto_xh` increases character size by 150% while the user requests minimal line spacing (`line=0.5pt`)?
  The safe line height floor scales up by 150%, preventing physical glyph overlap while adding the 0.5 pt user request as an inter-line gap.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The layout engine MUST physically clamp or downscale any element situated at the top of a page that exceeds printable page height, ensuring 100% of rendered stroke coordinates satisfy $y_{\text{stroke}} \le y_{\text{page\_bottom\_margin}}$.
- **FR-002**: The system MUST NEVER report or log that content was clamped unless stroke coordinates were physically restricted to within printable margins.
- **FR-003**: The layout engine MUST assign and preserve a stable, persistent cell identity (`source_cell_id`) on all table cell representations throughout page slicing and dynamic row splitting.
- **FR-004**: When table content overflows a page, continuation lines MUST be routed to the exact origin cell using its persistent identity, without relying on reconstructed slice row/column indices.
- **FR-005**: When dynamically splitting a row with `rowspan > 1`, the system MUST partition the row span explicitly between the origin cell and continuation cell so that their span ranges never overlap.
- **FR-006**: The table layout engine MUST prevent overlapping cell occupancy in the grid structure and ensure horizontal and vertical border lines never intersect merged cell interiors.
- **FR-007**: When evaluating words for wrapping, the system MUST inspect whether whole-word models exist and fit within the column width before applying character-level partitioning.
- **FR-008**: Long unbroken tokens exceeding available width MUST be partitioned using pure measurement in $O(N)$ linear time without mutating handwriting synthesizer state during trial evaluation.
- **FR-009**: The layout engine MUST compute the finalized effective character scaling factor *before* calculating physical line heights, safe clearance floors, or background ruling alignments.
- **FR-010**: Safe anti-collision line spacing floors and table row height floors MUST scale proportionally with the effective character scale under automatic height scaling mode (`auto_xh`).
- **FR-011**: Multi-page table continuation tests MUST verify the complete presence and sequential ordering of unique line identifiers (e.g. `LINE_0001` through `LINE_NNNN`) to guarantee zero content loss and zero duplicates.
- **FR-012**: Algorithmic complexity tests for token wrapping MUST verify linear execution through operation and invocation counts rather than environmental wall-clock timing assertions.

### Key Entities

- **Persistent Cell Identity**: A unique identifier attached to each table cell that remains invariant across page slicing, dynamic row splitting, and continuation remainder passes.
- **Physical Printable Bounds**: The geometric rectangle defined by page margins within which 100% of rendered vector strokes must reside.
- **Effective Character Scale**: The finalized scale factor combining base scale and automatic x-height adjustments, serving as the foundation for all vertical spacing calculations.
- **Partitioned Row Span**: A non-overlapping allocation of row span ranges between an origin cell on one page and its continuation cell on subsequent pages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of handwriting strokes across all rendered pages strictly satisfy printable margin boundaries, with zero points exceeding the bottom margin.
- **SC-002**: Multi-page tables spanning 3 or more pages with `rowspan > 1` cells preserve 100% of input text lines in exact sequential order, with zero dropped lines and zero duplicated lines verified by labeled identifiers.
- **SC-003**: 100% of merged cell interiors remain completely free of intersecting border lines across all page slices.
- **SC-004**: Text configured with small line spacing (`line=1.0pt`) combined with automatic character scaling (`auto_xh`) maintains zero physical overlap between consecutive lines and between text and table borders.
- **SC-005**: Long unbroken tokens wrap into columns without causing trial state mutations, completing in linear complexity verified deterministically in CI.
- **SC-006**: Zero system warnings claim clamping when strokes have not been physically verified to be within page boundaries.

## Assumptions

- Page margins for standard paper formats (A4, Letter, etc.) provide adequate printable height for standard text lines.
- When an indivisible element exceeds total page height, proportional downscaling to fit printable height is the user-preferred alternative to truncating or dropping content.
- Pre-composed word models in the handwriting bank take visual precedence over synthesized letter sequences when they fit within the allocated width.
- Unit and integration tests run in diverse environments (local developer machines, CI containers), requiring deterministic metric assertions rather than hardware-sensitive timing thresholds.
