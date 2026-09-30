# Feature Specification: Letter-Level Handwriting Assembly & Fallback Synthesis

**Feature Branch**: `016-letter-assembly-synthesis`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "Hiện tại khi một từ chưa có trong kho, app báo 'từ còn thiếu' và phải vẽ nguyên từ đó. Cơ chế mới sẽ báo các chữ cái còn thiếu (a, ă, â, ơ, ư... và các dấu thanh) để chỉ vẽ một lần (~60 đơn vị), rồi Writer tự ghép chữ cái thành từ hoàn chỉnh làm phương án dự phòng. Mẫu nguyên từ vẫn được ưu tiên hàng đầu vì tự nhiên hơn. Bắt buộc giữ nguyên tương thích ngược và Golden Master khi tắt tính năng mới."

---

## Background & Problem Statement

Currently, the handwriting synthesis engine relies primarily on whole-word handwritten samples stored in the bank (`bank.words`). When a word in a document has never been taught:
1. The engine checks for a root word with matching unaccented letters and substitutes an isolated harvested tone mark (`substitute()`).
2. If no root word exists, the engine leaves a blank space of estimated width on the page and flags the entire word as missing.
3. The user must manually draw every missing whole word in a handwriting grid, which scales poorly: writing a standard Vietnamese text may require drawing hundreds of individual words even when the constituent letters are identical.

By introducing **letter-level assembly and fallback synthesis**, the application allows users to teach just ~29 base letters (plus uppercase variants and 5 tone marks) once. Any missing word whose constituent letters have been taught can then be synthesized automatically as a seamless fallback, while existing whole-word samples and root substitutions remain the primary choice for maximum visual naturalness.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Missing Letter Reporting & Greedy Teaching Queue (Priority: P1)

A user writes or imports a new document containing several words that do not yet exist in the handwriting bank. Instead of forcing the user to draw 50+ individual words, the application analyzes the unlearned words and reports the exact base letters and tone marks that are missing. The letters are ranked in greedy order (letters that unlock the largest number of missing words appear first). The user clicks a single button to load these missing letters into the interactive teaching canvas.

**Why this priority**: Solves the core user pain point of handwriting bootstrap friction. Reduces the initial handwriting teaching investment from hundreds of words to ~30-60 character units.

**Independent Test**: Can be tested by providing a document with unlearned words to the analysis engine; verifies that the resulting report identifies the minimal set of missing letters, correctly ranked by word unlocking potential, and loads them into the teaching queue.

**Acceptance Scenarios**:

1. **Given** a handwriting bank containing no whole words and no letters, **When** the user processes the sentence "mẹ và bé đi chợ", **Then** the system reports the missing letters (`m, e, v, a, b, d, đ, i, c, h, o, ơ`) and tone marks (`hỏi, nặng, huyền, sắc`), ranked by the count of words each unlocks.
2. **Given** a list of reported missing letters, **When** the user clicks "Dạy các chữ cái này", **Then** the teaching tab queue is populated with the missing letters in prioritized order.
3. **Given** a bank that already has the letters `b`, `a` and the acute tone mark (`sắc`), **When** processing the text "ba bá", **Then** neither `ba` nor `bá` is reported as missing letters because all constituent units exist.

---

### User Story 2 - Automated Fallback Word Synthesis from Learned Letters (Priority: P1)

When rendering a document with letter assembly fallback enabled, any word token lacking a whole-word sample or a tone-substituted root is synthesized dynamically from the learned letter samples. Letters are placed along the baseline with natural kerning, and tone marks are positioned above or below the designated vowel according to Vietnamese orthography and bounding-box geometry.

**Why this priority**: Delivers the primary functional capability: eliminating blank gaps in handwritten output documents by assembling words on demand.

**Independent Test**: Can be tested by rendering text containing words not present in `bank.words` but whose letters exist in `bank.letters`. The rendered output contains complete stroke representations for those words and zero missing-word blank gaps.

**Acceptance Scenarios**:

1. **Given** a bank with whole-word sample `xin` and letter samples for `c, h, a, o`, **When** rendering "xin chào", **Then** `xin` is rendered directly from its whole-word sample, and `chào` is assembled from letter samples `c`, `h`, `a`, `o` with the grave tone mark affixed to `a`.
2. **Given** a bank with whole-word sample `bà` and no sample for `bá`, **When** rendering "bá", **Then** the engine uses root substitution (swapping the grave tone mark for an acute tone mark on `bà`) in preference to letter-level assembly, preserving whole-word ligatures.
3. **Given** an unlearned word with an upper tone mark on the letter `i` (such as `gì`), **When** the letter assembly fallback synthesizes the word, **Then** the tittle (dot) of letter `i` is removed so the tone mark does not collide with the dot.
4. **Given** a word containing letters that have multiple learned samples, **When** the word is synthesized, **Then** the engine selects among available letter variants avoiding immediate repetition to ensure natural handwriting variability.

---

### User Story 3 - Letter Glyph Storage, Multi-Session Concurrency & Safety (Priority: P1)

Users teach letters using the same interactive canvas used for words. Letter samples are saved into a dedicated `letters` section of the handwriting bank. The bank format safely migrates from previous schema versions (v1, v2, v3) without loss of existing data. Concurrent writing processes (GUI and CLI) safely merge letter additions and deletions without data loss using file locking and tombstone records.

**Why this priority**: Guarantees data durability and multi-process integrity for learned letters, preventing corruption of existing user handwriting banks.

**Independent Test**: Can be tested by teaching letters via GUI/controller, saving to disk, reloading across processes, validating schema migration from v3 bank files, and asserting tombstone deletions work across merged updates.

**Acceptance Scenarios**:

1. **Given** an existing v3 bank file, **When** opened by the application, **Then** it is migrated in-memory to support the `letters` section without error or data loss.
2. **Given** two active sessions sharing a bank file, **When** session A teaches letter `m` and session B deletes word `bàn`, **Then** saving in both sessions merges cleanly so both the letter addition and the word deletion are preserved.
3. **Given** an existing letter sample that is deleted by the user, **When** the bank is saved, **Then** a tombstone record is created ensuring the deletion persists across disk synchronizations.

---

### User Story 4 - Backward Compatibility & Golden Master Invariance (Priority: P2)

When the letter assembly fallback option is disabled (the default setting for legacy calls and standard CLI runs), the synthesis engine behaves identically to previous versions. Whole words and substituted roots render as before, and unlearned words leave blank gaps and populate `missing`. All existing golden master test cases pass with 100% hash parity.

**Why this priority**: Protects existing test suites, automated scripts, and guarantees zero unintended side effects for users who prefer strict whole-word rendering.

**Independent Test**: Can be tested by running `test_golden_master.py` with `assemble_letters=False`; verifies that all SHA-256 output hashes match the reference golden master values exactly.

**Acceptance Scenarios**:

1. **Given** `WriteOptions(assemble_letters=False)`, **When** rendering the standard golden master test cases, **Then** the resulting `.xopp` and `_thieu.xopp` files produce identical SHA-256 hashes to the reference repository standard.
2. **Given** an execution of the CLI without the `--assemble` flag, **When** processing text with missing words, **Then** the system outputs missing word notices and generates `_thieu.xopp` exactly as before.

---

### User Story 5 - User Interface Controls & Bank Statistics (Priority: P2)

The user can toggle "Ghép từ chữ cái" in the writing tab, view separate lists of missing words versus missing letters, and jump directly to teaching missing units. The bank management tab displays inventory counts for learned letters, and users can search, inspect, and delete individual letter samples.

**Why this priority**: Exposes the feature intuitively to end users within both graphical and terminal interfaces.

**Independent Test**: Can be tested through GUI integration tests verifying checkbox state, list population, and button interactions, as well as CLI `--assemble` and `stats` commands.

**Acceptance Scenarios**:

1. **Given** the writing tab in GUI, **When** "Ghép từ chữ cái" is checked and text is rendered, **Then** words synthesized from letters are listed under "Từ đã ghép tự động" and only unresolvable words/letters appear in the missing list.
2. **Given** the bank management tab, **When** refreshed, **Then** it displays the total count of distinct letters learned and total letter samples, alongside existing word and digit counts.
3. **Given** the CLI command `hw_note.py stats`, **When** executed, **Then** it outputs the letter inventory count in addition to word, digit, punctuation, and tone mark counts.

---

### Edge Cases

- **Missing both whole word and constituent letters**: If a word cannot be synthesized because one or more of its letters are missing, the word remains marked as missing, leaves an estimated blank gap on the page, and the specific missing letters are included in the missing letters report.
- **Strict-case vs. Loose-case**: In loose-case mode, if an uppercase letter (e.g., `B`) has no sample, the engine falls back to using the lowercase letter sample (`b`) scaled appropriately. In strict-case mode, uppercase letters require an explicit uppercase letter sample; if absent, synthesis for that word fails and falls back to a blank gap.
- **Tone mark collision avoidance on dotted letters**: When affixing an upper tone mark (huyền, sắc, hỏi, ngã) to the letter `i`, the original dot of the letter `i` must be suppressed to avoid visual artifacts.
- **Tone placement on complex diphthongs and triphthongs**: For vowel combinations such as `oa`, `oe`, `uy`, `ươ`, `iê`, the tone mark must be positioned on the correct orthographic vowel based on standard Vietnamese rules rather than naive centering.
- **Special characters and math inline tokens**: Mathematical expressions, LaTeX symbols, and standalone punctuation marks are excluded from letter decomposition and handled strictly through their respective dedicated layout handlers.
- **Punctuation attached to synthesized words**: Leading quotes/brackets and trailing punctuation (e.g., `"(bàn),"` or `"'chào!'"`) are detached, rendered with appropriate spacing, and reattached cleanly to the assembled word core.
- **Single-letter words**: Words consisting of a single letter (e.g., "ở", "ý", "ô", "anh ấy có *ý* kiến") utilize single letter samples directly and attach tone marks if necessary.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a text analysis function to decompose any Vietnamese word token into an ordered sequence of base alphabet letters and an optional tone mark.
- **FR-002**: System MUST analyze input text against the current handwriting bank to identify all missing base letters and tone marks needed to render unlearned words.
- **FR-003**: System MUST calculate greedy set-cover ranking for missing letters, ordering them by the number of unlearned words each letter unlocks.
- **FR-004**: System MUST allow users to draw, preview, and save individual letter samples (both lowercase and uppercase) via the interactive handwriting canvas.
- **FR-005**: System MUST store learned letter samples in a dedicated `letters` dictionary within the handwriting bank, supporting multiple distinct stroke samples per letter for natural handwriting variation.
- **FR-006**: System MUST maintain backward compatibility with previous bank schemas (v1, v2, v3), automatically migrating them in-memory to the new schema version supporting `letters` without data loss.
- **FR-007**: System MUST synchronize letter additions, deletions, and tombstone records across concurrent processes during file save operations.
- **FR-008**: System MUST implement a four-tier handwriting resolution cascade in the writer engine:
  1. Exact whole-word sample match (`bank.words`).
  2. Root substitution using existing words and harvested tone marks (`substitute()`).
  3. Letter-level assembly fallback from learned letter samples (`bank.letters`) and tone marks (`bank.marks`).
  4. Blank placeholder gap with missing token and missing letter reporting.
- **FR-009**: System MUST position assembled letters on the document baseline, applying proportional kerning and random jitter to maintain natural handwriting appearance.
- **FR-010**: System MUST affix tone marks to the appropriate vowel of an assembled word using vowel position calculation and extreme coordinate heuristics, suppressing existing tittles on letter `i` when placing upper tone marks.
- **FR-011**: System MUST provide a configuration option (`assemble_letters: bool`) in `WriteOptions`, accessible via a GUI toggle checkbox and a CLI flag (`--assemble`), defaulting to `False` to maintain golden master parity.
- **FR-012**: System MUST guarantee that when `assemble_letters` is `False`, rendering output is 100% byte-identical to legacy output and all golden master test hashes match exactly.
- **FR-013**: System MUST include `assembled_words` (list of synthesized words) and `missing_letters` (ranked list of missing letters) in the document writing result structure (`WriteResult`).
- **FR-014**: System MUST display missing letters and assembled words in GUI and CLI output reports, and allow one-click transfer of missing letters into the teaching queue.
- **FR-015**: System MUST display letter inventory metrics in bank statistics (CLI `stats` and GUI bank tab), and support searching and deleting letter samples in the bank management interface.

---

### Key Entities

- **Letter Glyph Sample**: A handwriting sample representing a single letter, containing relative stroke vectors (`s`), bounding advance width (`w`), and a deduplication hash signature (`_sig`).
- **Letter Bank (`bank.letters`)**: A dictionary mapping each character (e.g. `'a'`, `'b'`, `'c'`, `'A'`, `'B'`) to a list of one or more handwritten letter samples.
- **Missing Letter Summary**: An ordered collection of character units that are absent from the bank but required to assemble pending document words, weighted by word unlock utility.
- **Assembled Word**: A dynamically generated stroke composite representing a word token synthesized from individual letter samples and positioned tone marks.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can achieve 100% handwriting coverage for any new Vietnamese text passage by teaching at most 60 character units (29 lowercase alphabet letters, uppercase variants as required, and 5 tone marks), completely avoiding the requirement to draw hundreds of distinct words.
- **SC-002**: When letter assembly fallback is enabled, unlearned words whose letters exist in the bank render with 100% stroke visibility and 0 empty gaps on the generated page.
- **SC-003**: When letter assembly fallback is disabled, rendering output maintains 100% byte-for-byte fidelity with the golden master test suite (0 hash mismatches).
- **SC-004**: Dynamic word assembly introduces less than 10% elapsed execution time overhead compared to standard whole-word rendering for a 1,000-word document.
- **SC-005**: All existing bank files from schema versions 1, 2, and 3 open, migrate, and save without error, and concurrent multi-process operations retain 100% of letter additions and deletions without lost updates.

---

## Assumptions

- Whole-word handwritten samples remain visually superior to synthesized words because real human handwriting connects letters organically; therefore, whole-word samples must always take precedence over assembled letters.
- Standard Vietnamese tone marks (huyền, sắc, hỏi, ngã, nặng) can be positioned reliably above or below the primary vowel of an assembled word using vowel horizontal centroid calculation and vertical extrema heuristics.
- The default behavior of `WriteOptions.assemble_letters` remains `False` for legacy programmatic calls and standard CLI executions to prevent regression of established golden master references.
- Upper-case letters in loose-case mode can fall back to scaled lower-case letter samples if no explicit upper-case letter sample has been taught, matching the loose-case behavior of whole words.
