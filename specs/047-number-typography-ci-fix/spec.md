# Feature Specification: Number Typography and CI Fallback Hardening

**Feature Branch**: `047-number-typography-ci-fix`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "FAILURES in test_minus_and_percent_digit_normalization, test_decimal_number_spacing_harmony, test_measure_text_width_number_sync"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Negative Numbers and Missing Glyph Typography Resilience (Priority: P1)

Users writing educational sheets, worksheets, and scientific documents frequently include negative numbers (such as `-25`, `-5`, `-123,45`) and percentages (`25%`). When using handwriting libraries—especially minimalist, newly created, or synthetic test libraries that lack pre-recorded glyphs for `-` or `%`—the system must gracefully produce visually pleasing, mathematically centered glyphs instead of dropping characters and reporting missing-glyph errors.

**Why this priority**: Core document rendering and test suites fail when negative numbers or percentages cannot be written due to missing punctuation in user or test libraries. Preventing missing glyph errors and ensuring proper mathematical alignment is a foundational requirement.

**Independent Test**: Can be fully tested by requesting the rendering of negative numbers (e.g. `"-25"`) and percentages (`"25%"`) using a handwriting bank devoid of explicit `-` or `%` samples, confirming that zero missing glyphs are reported and the minus sign is vertically centered along the mathematical axis.

**Acceptance Scenarios**:

1. **Given** a handwriting bank without a `-` glyph sample, **When** a negative integer or decimal number (e.g., `"-25"`) is rendered, **Then** the minus sign is generated without reporting missing glyphs, and its vertical center aligns with the mathematical axis (approximately `-0.45 * xh`).
2. **Given** a handwriting bank without a `%` glyph sample, **When** a percentage token (e.g., `"25%"`) is rendered, **Then** the percent symbol is produced without reporting missing glyphs, rests firmly on the baseline (`abs(max_y) <= 0.08 * xh`), and matches standard digit height (`1.05 * xh` to `1.30 * xh`).

---

### User Story 2 - Natural Decimal Number and Comma Spacing Harmony (Priority: P1)

Users and educators frequently write decimal numbers (e.g., `0,39`, `0,0278`). In handwriting typography, commas in general text often carry wide trailing whitespace to separate sentences. However, within decimal numbers, wide whitespace looks unnatural and breaks numeric continuity. The layout engine must enforce natural, tight spacing between the comma's visible edge and the following decimal digit, bounded between `0.08 * xh` and `0.14 * xh`.

**Why this priority**: Excessive whitespace after a decimal comma degrades document legibility and causes automated typography harmony assertions to fail.

**Independent Test**: Can be tested by rendering decimal numbers like `"0,39"` and `"0,0278"` across various handwriting banks (including those with wide text commas) and measuring the physical horizontal gap between the comma stroke and the next digit stroke, verifying it falls within `[0.08 * xh, 0.14 * xh]`.

**Acceptance Scenarios**:

1. **Given** a handwriting bank where comma punctuation has large text-level whitespace, **When** a decimal number (e.g., `"0,39"`) is rendered, **Then** the geometric distance between the rightmost edge of the comma and the leftmost edge of the following digit is constrained to `0.08 * xh` to `0.14 * xh`.
2. **Given** a multi-digit decimal number (e.g., `"0,0278"`), **When** rendered, **Then** the gap before the comma is between `0.06 * xh` and `0.12 * xh`, the gap after the comma is between `0.08 * xh` and `0.14 * xh`, and subsequent inter-digit gaps remain harmoniously uniform.

---

### User Story 3 - Synchronization Between Advance Width Measurement and Number Rendering (Priority: P1)

Document layout and table engines rely on advance text measurement to allocate column widths, wrap paragraphs, and align math formulas before actual ink stroke generation. If the estimated width of a number differs from its actual rendered width, numbers will clip, overflow bounding cells, or produce visual gaps.

**Why this priority**: Discrepancies between measurement and rendering cause misaligned tables, improper text wrapping, and automated test regressions.

**Independent Test**: Can be tested by comparing width estimates from `measure_text_width(num_str)` with physical rendered widths from `number(num_str)` across positive integers, negative numbers, and decimal numbers, confirming the absolute difference is within `0.05 * xh`.

**Acceptance Scenarios**:

1. **Given** a negative number string (e.g., `"-5"` or `"-123,45"`), **When** measuring its width ahead of time and then rendering it, **Then** the difference between measured width and rendered width is less than or equal to `0.05 * xh`.
2. **Given** a decimal number string (e.g., `"0,39"` or `"0,0278"`), **When** measuring its width ahead of time and then rendering it, **Then** the measured width precisely accounts for the optical comma advance and matches rendered width within `0.05 * xh`.

---

### User Story 4 - Autonomous CI Environment and Synthetic Bank Test Integrity (Priority: P2)

Continuous integration (CI) runners in clean containers do not have access to developer-local uncommitted files (such as `local data/kho_mau_v4.json.gz`). The repository must provide fully functional, self-contained synthetic fixture data containing standard punctuation (including `-`, `,`, `.`, `%`) and digits so that all typography and system hardening tests pass reliably without environmental discrepancies.

**Why this priority**: Adheres to the Constitution Principle III (Comprehensive Automated Testing) and prevents false CI breakages while maintaining clean separation from local developer files.

**Independent Test**: Can be tested by running the entire pytest suite in a clean environment where local data is absent, verifying all 1250+ tests pass with zero failures.

**Acceptance Scenarios**:

1. **Given** a clean clone where `local data/kho_mau_v4.json.gz` is absent, **When** test fixtures load the synthetic fallback bank, **Then** the synthetic bank supplies valid samples for all required numeric punctuation (`-`, `,`, `.`, `!`, `?`, `(`, `)`, `%`).
2. **Given** the synthetic bank generation script, **When** executed, **Then** it generates clean geometric samples with appropriate bounding widths, avoiding bloated advance metrics that distort numeric layouts.

---

### Edge Cases

- **Negative Decimals**: What happens when rendering negative decimals such as `"-0,39"` or `"-123,45"`? The minus sign must have its standard vertical centering and reduced gap before the first digit, while the decimal comma maintains its tight inter-digit spacing.
- **Extreme Punctuation Widths**: What happens when an imported bank has a comma whose recorded bounding width `w` is 5 to 10 times larger than the drawn stroke? The numeric rendering engine must base inter-character spacing on visible glyph bounds rather than unconstrained text whitespace.
- **Empty or Incomplete Banks**: What happens when rendering numbers with a newly initialized, empty handwriting bank? The engine must gracefully synthesize standard vector fallbacks for minus, punctuation, and digits without throwing uncaught exceptions or reporting missing essential numeric operators.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render negative numbers with a properly centered minus glyph positioned at the mathematical axis (approximately `-0.45 * xh`), utilizing a vector fallback if the active bank does not supply a dedicated minus glyph.
- **FR-002**: System MUST report zero missing glyphs when writing standard negative numbers (`-`) and percentage tokens (`%`) on valid handwriting libraries with vector fallback capability.
- **FR-003**: System MUST calculate post-comma advance spacing within numeric sequences based on optical stroke width, constraining the gap between the comma and subsequent decimal digits to `0.08 * xh` through `0.14 * xh`.
- **FR-004**: System MUST keep ahead-of-time text width measurements in exact parity with physical rendered widths for all numeric sequences (integers, negative numbers, decimals, and percent values), ensuring the absolute discrepancy does not exceed `0.05 * xh`.
- **FR-005**: System MUST provide complete synthetic test fixture data in `tests/data/kho_mau_tong_hop.json.gz` encompassing all basic digits and numeric punctuation (`-`, `%`, `,`, `.`), ensuring standalone test reproducibility in CI environments.
- **FR-006**: System MUST ensure percentage glyphs within numbers or isolated tokens align to the baseline (`abs(max_y) <= 0.08 * xh`) with height bounded within standard digit specifications (`1.05 * xh` to `1.30 * xh`).

### Key Entities

- **Number Sequence**: A string conforming to numeric syntax containing digits, leading minus sign, optional decimal separators (comma or period), and optional trailing percentage sign.
- **Optical Glyph Metrics**: Geometric bounding box coordinates (`min_x`, `max_x`, `min_y`, `max_y`) derived from actual ink stroke points, used to compute precise visual inter-character clearances.
- **Synthetic Test Bank**: A self-contained, anonymized handwriting library fixture used during automated testing and CI runs to validate layout behavior without requiring external user assets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero missing glyph errors reported when rendering negative numbers and percentages across all supported handwriting libraries.
- **SC-002**: Optical gap after decimal commas in rendered numbers consistently falls within `[0.08 * xh, 0.14 * xh]`, eliminating unnatural gaps greater than `0.14 * xh`.
- **SC-003**: Advance width measurement divergence between `measure_text_width()` and `number()` remains strictly `<= 0.05 * xh` across all test numeric strings.
- **SC-004**: 100% test pass rate in CI environments where local developer banks are absent, resolving all 3 failing tests (`test_minus_and_percent_digit_normalization`, `test_decimal_number_spacing_harmony`, `test_measure_text_width_number_sync`).

## Assumptions

- Minus signs in numeric contexts require vertical centering near the mathematical axis (`-0.45 * xh`) to match arithmetic expectations, unlike text hyphens which may sit lower.
- In Vietnamese typography, commas are commonly used as decimal points (e.g. `0,39`), requiring the same tight, cohesive kerning as periods in English typography.
- Handwriting banks may originate from diverse drawing sources with variable whitespace margins; relying on optical stroke bounds inside numeric sequences is required to ensure consistent inter-digit rhythm.
- Test suites running in continuous integration should never depend on uncommitted developer-local file paths.
