# Feature Specification: High-Fidelity Letter Assembly & Handwriting Synthesis Quality

**Feature Branch**: `017-letter-assembly-quality`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Sửa & cải tiến cơ chế ghép chữ viết tay (repo caoduongle/viet): chữ sinh ra không còn dính/nhoè vào nhau; chữ sinh ra trông giống chữ trong file note gốc (cùng cỡ, cùng độ đậm nét, cùng nhịp khoảng cách, cùng độ cao các chữ); làm lại tờ lưới ký tự và hướng dẫn viết rõ ràng; hỗ trợ đầy đủ chữ có dấu thanh; đảm bảo các ràng buộc kiến trúc MVC, zero core dependencies, tương thích ngược kho và golden-master."

---

## Background & Problem Statement

The application provides handwritten note synthesis for Xournal++ (`.xopp`), allowing typed documents to be converted into realistic personal handwriting. While whole-word synthesis preserves natural ligatures, fallback synthesis from individual handwritten characters is essential when words are not yet present in the whole-word bank.

Inspection and user testing of the existing single-letter assembly mechanism revealed critical fidelity and usability defects:
1. **Ink pooling and stroke collisions ("dính chữ / nhoè chữ")**: Synthesized words (such as "pipeline", "penguins", "body_mass_g") suffer from overlapping bounding boxes and touching strokes because advance width logic uses an artificial overlap subtraction (`advance = w - overlap`) without computing actual glyph boundary contours or left/right side bearings (LSB/RSB), and without enforcing a clearance floor based on pen stroke width.
2. **Disproportionate scale and stroke weight**: Characters written into the collection grid have small physical heights (~3.4–5.4pt) relative to the pen stroke width (1.41pt), resulting in ink pooling ("cục mực"). Furthermore, when scaling, the engine scales coordinates without normalizing character x-heights or scaling stroke thickness proportionally to match authentic note samples (`2026-09-20-Note-17-02.xopp`).
3. **Inconsistent x-heights**: Character heights across standard lowercase glyphs vary erratically (e.g. `a, u, o` ≈ 3.4–3.8pt vs `n, c, v` ≈ 5.4pt), causing uneven, disorderly word baselines.
4. **Tone mark omission on accented words**: In legacy bank schema v3, samples stored under single-letter keys lack explicit decomposed tone marks. Tone harvesting with hard-coded thresholds fails to recognize accents on many Vietnamese characters (e.g. 28/120 accented glyphs), causing accented words (e.g., "Lời", "Bài", "Chạy", "Phần", "giải") to be silently dropped or omitted as empty gaps.
5. **Ambiguous collection grid guidance**: The existing 206-cell grid lacks visual boundary guides (inner writing zone margins, ascender/descender reference lines) and clear Vietnamese instructions, leading users to write characters at inconsistent heights and arbitrary horizontal alignments.

This specification defines the functional requirements and acceptance criteria to resolve these defects, ensuring synthesized handwriting matches the rhythm, proportions, and legibility of authentic handwritten notes while maintaining strict architectural decoupling, zero core dependencies, bank backward compatibility, and golden-master test invariance.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Natural Spacing & Non-Overlapping Letter Assembly (Priority: P1)

When synthesizing text using single-letter assembly, adjacent characters within a word are placed with natural visual spacing. The placement logic respects individual character side margins (left and right side bearings) and character boundary contours (curved, straight, open), enforcing a minimum clearance floor proportional to the pen stroke thickness.

**Why this priority**: Solves the primary visual defect reported by users where words appear as blurred, overlapping blobs of ink ("pipeline", "penguins", "body_mass_g").

**Independent Test**: Can be tested by synthesizing words with varying boundary shapes (e.g., curved-to-straight, open-to-closed) and verifying that adjacent character bounding boxes do not overlap by more than 10% of the narrower character's width and that physical stroke distance never falls below the pen clearance floor.

**Acceptance Scenarios**:

1. **Given** a letter bank containing samples for `p`, `i`, `e`, `l`, `n`, **When** the word "pipeline" is synthesized, **Then** all adjacent letters have distinct visual separation, no strokes intersect or touch, and no character bounding boxes overlap by more than 10%.
2. **Given** two adjacent letters with curved outer contours (such as `o` followed by `o`), **When** assembled into a word, **Then** the inter-character gap naturally tightens compared to straight-edge pairs while remaining strictly above the pen clearance floor.
3. **Given** jitter/randomization enabled during synthesis, **When** jitter offsets are applied to letter positions, **Then** the post-jitter letter separation is bounded such that it never violates the minimum clearance floor.

---

### User Story 2 - Handwriting Proportions, x-Height Normalization & Dynamic Stroke Scaling (Priority: P1)

When assembling words, individual letters are normalized to a coherent target x-height derived from authentic handwriting notes, and pen stroke thickness scales dynamically with character scale to preserve the natural ratio of stroke width to letter height.

**Why this priority**: Prevents letters from appearing as thick "ink blobs" or having jarringly mismatched heights across vowels and consonants within the same word.

**Independent Test**: Can be tested by measuring the synthesized output of the acceptance sample (`accept_sample.txt`) and confirming median x-height matches reference note metrics within 10%, pen-to-x-height ratio matches within 15%, and height variance across x-height letters is reduced by at least 50%.

**Acceptance Scenarios**:

1. **Given** raw letter samples where `a` has height 3.5pt and `n` has height 5.4pt, **When** assembled into the word "nam", **Then** the visual x-heights of `a`, `m`, and `n` are normalized to a consistent baseline-aligned target height.
2. **Given** a user target scale or document font size, **When** the document is rendered, **Then** stroke width is adjusted so that the ratio of stroke thickness to x-height remains within 15% of the reference handwriting profile.
3. **Given** ascender letters (`b, d, h, k, l`), descender letters (`g, p, q, y`), and uppercase letters, **When** normalized, **Then** their ascender and descender proportions scale uniformly with their respective letter categories without geometric distortion.

---

### User Story 3 - Robust Tone Mark Placement & Vietnamese Diacritic Assembly (Priority: P1)

When synthesizing Vietnamese words containing diacritics and tone marks (sắc, huyền, hỏi, ngã, nặng, mũ, móc), tone marks are dynamically positioned relative to the center of the underlying vowel without colliding with ascenders or existing vowel diacritic hats/hooks, and uppercase letters or special characters in variable names are properly handled.

**Why this priority**: Eliminates blank omissions for accented Vietnamese words ("Lời", "giải", "Phần", "Bài", "Chạy", "Điều", "kiện", "chiều", "khối", "lượng") which currently fail to render when tone marks cannot be harvested.

**Independent Test**: Can be tested by rendering the standard acceptance text sample containing single and compound vowels with tone marks; verifies that all accented words render complete strokes, tone marks are clearly legible above or below their vowels, and letters `i`/`j` have their dots removed when upper tone marks are placed.

**Acceptance Scenarios**:

1. **Given** text containing words with complex diacritics ("Lời giải", "Điều kiện lọc"), **When** rendered with letter assembly, **Then** all words render complete strokes with tone marks positioned above/below their respective vowels without colliding with ascenders of neighboring letters (`l`, `d`, `k`).
2. **Given** a vowel `i` with an upper tone mark (such as "Bài"), **When** the tone mark is affixed, **Then** the default dot of the letter `i` is suppressed to avoid visual crowding and double-dot artifacts.
3. **Given** technical identifiers and formulas containing symbols (e.g., `bill_length_mm`, `body_mass_g`, `>=`, `<`, `(`, `)`, `.`), **When** synthesized, **Then** each constituent symbol and alphanumeric character is placed with appropriate horizontal metrics or gracefully fallen back to clean vector glyphs.

---

### User Story 4 - Redesigned Handwriting Collection Grid with Visual Guides & Explicit Instructions (Priority: P2)

A user preparing to teach their handwriting generates a printable/digital handwriting grid sheet (`hw3`) that provides intuitive four-line guides, horizontal margin boundaries, and explicit Vietnamese instructions.

**Why this priority**: Guarantees that newly collected handwriting samples have clean baselines, uniform x-heights, and measurable side bearings from the moment they are written, eliminating the root cause of poor sample quality.

**Independent Test**: Can be tested by generating a new grid sheet and verifying that the output contains four guide rules (baseline, x-height, ascender, descender), left/right side margins, legible Vietnamese labels without missing font glyphs, and embedded instructional text.

**Acceptance Scenarios**:

1. **Given** a request to generate a character collection grid, **When** the new grid template is exported, **Then** each cell displays four reference lines (baseline, x-height matching authentic note target, ascender, descender) and two vertical margin lines designating the writing boundaries.
2. **Given** Vietnamese character labels (such as `ă, â, đ, ê, ô, ơ, ư`), **When** displayed on the grid sheet, **Then** labels are rendered clearly with full Vietnamese unicode typography without placeholder square boxes (□).
3. **Given** the generated grid sheet, **When** inspected by a user, **Then** clear Vietnamese instructions are prominently visible explaining target height, unlinked print style, tone mark placement, and normal writing cadence.
4. **Given** a completed grid sheet in either the new format (`hw3`) or legacy format (`hw2`), **When** ingested by the learning command, **Then** the system successfully extracts character samples and computes side bearings while providing warnings for empty or malformed cells.

---

### User Story 5 - Non-Destructive Bank Migration & Explicit Missing Character Diagnostics (Priority: P2)

A user with an existing legacy handwriting bank (schema v1–v3 with single-character samples stored under `words`) runs a migration tool to produce an upgraded bank with normalized character metrics, side bearings, and extracted tone marks, without modifying or corrupting the original file.

**Why this priority**: Protects existing user handwriting data while upgrading older banks to support the high-fidelity assembly engine.

**Independent Test**: Can be tested by migrating a legacy v3 bank containing 178 single-character entries; verifies that the original file is untouched, the output file adheres to the upgraded bank schema, and any characters that cannot be cleanly decomposed are explicitly flagged.

**Acceptance Scenarios**:

1. **Given** a legacy v3 bank file (`schema_version=3`), **When** the migration script is executed, **Then** a new upgraded bank file is produced, single-character entries are converted into structured letter records, and the original source bank file remains byte-identical.
2. **Given** a document containing characters or symbols not present in the bank, **When** synthesis runs, **Then** the system outputs a clear diagnostic report specifying exactly which characters or tone marks are missing rather than silently producing blank spaces.
3. **Given** two concurrent processes updating the handwriting bank, **When** migrations or letter additions occur, **Then** file locking and tombstone records guarantee zero data corruption or lost updates.

---

### User Story 6 - Objective Ink Measurement & Visual Regression Baseline (Priority: P2)

Developers and automated test suites measure objective handwriting metrics (x-height, stroke-width-to-x-height ratio, inter-letter clearance, bounding-box overlap ratio) and render visual verification snapshots from `.xopp` documents to validate synthesis quality quantitatively.

**Why this priority**: Replaces subjective visual guesswork with repeatable, automated quality verification.

**Independent Test**: Can be tested by running the measurement tool on reference note files and generated files; verifies that computed metrics are emitted as structured reports and that golden-master SHA-256 hashes remain 100% invariant when letter assembly is disabled.

**Acceptance Scenarios**:

1. **Given** an authentic handwritten `.xopp` file and a synthesized `.xopp` file, **When** the ink measurement tool is executed, **Then** it calculates and outputs median x-height, pen-thickness-to-x-height ratio, median inter-letter gap, median inter-word gap, bounding-box overlap ratio, and x-height standard deviation.
2. **Given** the visual renderer tool, **When** invoked with a `.xopp` file and target page/crop region, **Then** it outputs an accurate PNG image representing the strokes for automated or human inspection.
3. **Given** legacy whole-word synthesis mode (`assemble_letters=False`), **When** running the golden-master test suite, **Then** all golden-master file outputs produce identical SHA-256 hashes to existing reference baselines.

---

### Edge Cases

- **Special symbols and math operators in code/text**: Words or identifiers containing punctuation (e.g. `bill_length_mm`, `body_mass_g`, `>=`, `<`, `(`, `)`, `.`, `---`) must correctly assemble or fall back to vector glyphs without crashing or distorting letter spacing.
- **Extreme scaling factors**: When the user specifies very small (e.g. `--scale 0.5`) or very large (e.g. `--scale 3.0`) scaling, stroke widths and letter clearance must scale proportionally to prevent strokes from merging into solid ink blobs or spreading unnaturally wide.
- **Accented capital letters and complex tone clusters**: Characters like `Ẩ`, `Ẹ`, `Ợ`, `Ự` where tone marks combine with vowel horns or hats must maintain vertical clearance without exceeding line boundary limits or colliding with adjacent ascenders.
- **High-jitter settings**: When `--jitter` is set to high values, randomized displacement must be clamped to preserve the minimum inter-character stroke clearance floor.
- **Single-stroke letters vs multi-stroke letters**: Characters with disconnected parts (e.g. `i, j, đ, x`) must maintain internal stroke unity during horizontal advance calculations so that internal components do not drift apart.
- **Malformed or empty grid cells**: When ingesting grid sheets, cells with stray ink marks, empty cells, or multiple unrelated strokes must trigger informative warnings and be safely skipped without corrupting the bank.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST compute letter placement advance using left side bearing (LSB), glyph width, right side bearing (RSB), and boundary contour classifications rather than subtracting a fixed overlap amount.
- **FR-002**: The system MUST enforce a minimum stroke clearance floor between adjacent letters within a word, ensuring no adjacent strokes approach closer than $k \times \text{pen\_thickness}$ (where default $k \approx 0.8$, configurable via synthesis options).
- **FR-003**: The system MUST bound adjacent character bounding-box overlap so that overlap does not exceed 10% of the narrower character's width.
- **FR-004**: The system MUST normalize individual letter sample heights to match the target x-height determined from authentic user handwriting profiles, scaling ascenders, descenders, and uppercase glyphs proportionally without distorting aspect ratios.
- **FR-005**: The system MUST adjust effective stroke thickness when scaling character geometry, maintaining a stroke-thickness-to-x-height ratio that matches the authentic handwriting baseline within 15%.
- **FR-006**: The system MUST dynamically position Vietnamese tone marks relative to the geometric center and bounding box of the base vowel, preventing collisions with neighboring ascenders (`l, h, b, k, d`) and vowel diacritics (mũ, móc).
- **FR-007**: The system MUST automatically suppress the tittle (dot) of letters `i` and `j` when an upper tone mark (sắc, huyền, hỏi, ngã) is affixed.
- **FR-008**: The system MUST provide an explicit diagnostic report of any missing characters, tone marks, or symbols required by the input document, preventing silent omissions or unexplained blank spaces.
- **FR-009**: The system MUST provide a non-destructive migration utility that converts legacy single-letter entries in bank schema v1–v3 into structured letter and tone mark records in an upgraded bank file, without modifying the source file.
- **FR-010**: The system MUST support generating an enhanced collection grid template (`hw3`) featuring four horizontal reference guides (baseline, x-height, ascender, descender), left/right side margin boundaries, legible Vietnamese unicode labels, and clear instructional text.
- **FR-011**: The system MUST support reading and ingesting both new `hw3` grid sheets and legacy `hw2`/`hw2c` grid sheets, ensuring full backward compatibility.
- **FR-012**: The system MUST strictly preserve legacy whole-word synthesis behavior with 100% SHA-256 byte-for-byte invariance on golden-master benchmarks when letter assembly is disabled.
- **FR-013**: The system MUST adhere to the strict MVC architectural separation: models MUST NOT depend on UI frameworks, CLI parsers, or contain standard output / exit side effects; core model and controller modules MUST NOT require third-party dependencies outside the Python standard library.

---

### Key Entities

- **Letter Sample (`BankLetter`)**: Represents an individual handwritten character glyph, encapsulating normalized vector strokes, baseline offset ($y=0$), visual bounding box, left side bearing (`lsb`), right side bearing (`rsb`), default advance width, and character classification category (x-height, ascender, descender, capital, punctuation, symbol).
- **Tone Mark Sample (`BankMark`)**: Represents a harvested or designed Vietnamese tone mark (sắc, huyền, hỏi, ngã, nặng), encapsulating vector strokes, relative placement offsets ($\Delta x, \Delta y$), vertical placement zone (above/below), and target vowel compatibility.
- **Letter Assembly Engine (`LetterAssembler`)**: Pure domain model component responsible for laying out letter sequences, computing boundary kerning, enforcing stroke clearance floors, resolving ascender/diacritic collisions, and applying tone mark attachments.
- **Collection Grid Sheet (`GridTemplate`)**: Domain specification for printable/digital handwriting capture sheets, defining page geometry, cell matrices, reference guide lines (baseline, x-height, ascender, descender), margin boundaries, and instructional typography.
- **Ink Measurement Profile (`InkProfile`)**: Quantitative representation of handwriting geometry, containing statistical metrics for median x-height, stroke-width-to-x-height ratio, inter-letter clearance distribution, inter-word spacing, bounding-box overlap percentages, and group variance.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In synthesized output using letter assembly, 0% of adjacent letter pairs exhibit bounding-box overlap greater than 10% of the narrower character's width.
- **SC-002**: In synthesized output using letter assembly, the minimum physical clearance between adjacent letter strokes within any word is at least 0.8 times the pen stroke thickness.
- **SC-003**: The median x-height of synthesized output deviates by no more than 10% from the authentic handwriting baseline established from `2026-09-20-Note-17-02.xopp`.
- **SC-004**: The ratio of pen stroke thickness to x-height in synthesized output deviates by no more than 15% from the authentic handwriting baseline.
- **SC-005**: Standard deviation of lowercase x-height across standard glyphs (`a, c, e, m, n, o, r, s, u, v, x, ă, â, ê, ô, ơ, ư`) is reduced by at least 50% compared to raw unnormalized bank samples.
- **SC-006**: 100% of characters in the standard acceptance test sample (`tests/data/accept_sample.txt`) are either rendered with valid handwritten strokes or explicitly reported in the missing character diagnostics, with zero silent omissions.
- **SC-007**: Synthesized output of the standard acceptance sample renders with complete human legibility and visual rhythm matching authentic handwriting notes upon inspection.
- **SC-008**: 100% byte-for-byte SHA-256 hash parity is preserved on all existing golden-master test cases when letter assembly fallback is disabled.
- **SC-009**: 100% of existing automated regression tests pass cleanly, with zero new test regressions or architectural boundary violations.

---

## Assumptions

- The reference note document `2026-09-20-Note-17-02.xopp` serves as the authoritative ground-truth target for user handwriting proportions, stroke weights, and spacing cadence.
- Single-letter handwriting synthesis serves primarily as an automated fallback for words not present in whole-word form (`bank.words`), while whole-word samples remain the highest-priority rendering choice for maximum visual naturalness.
- Personal handwriting data files (`kho_mau_ky_tu_json.gz`, `luoi_ky_tu_de_viet.xopp`, `2026-09-20-Note-17-02.xopp`, `anh_loi.png`) are private user assets stored exclusively in `local_data/` / `local data/` and will never be committed to source control.
- Test suites will use deterministic synthetic fixture banks (`tests/data/kho_mau_tong_hop.json.gz` or programmatically generated fixtures) to ensure automated test independence from private user data.
- Phase 4 (automated harvesting of whole words directly from the 13-page reference note) is an optional future enhancement that requires explicit user confirmation and will not be executed prior to complete verification of Phases 0–3.
- All core business logic in `chuviettay/model` and `chuviettay/controller` adheres to zero external dependencies outside the Python standard library; analysis scripts and visual renderers in `tools/` may utilize standard scientific/imaging libraries (Pillow, numpy) with appropriate runtime checks.
