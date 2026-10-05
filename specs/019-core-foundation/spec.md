# Feature Specification: P1 — Core Foundation & Ecosystem Harmonization

**Feature Branch**: `refactor/phase1-foundation`  
**Created**: 2026-10-05  
**Status**: Draft  
**Input**: User description: "P1 — Giai đoạn 1: nền tảng (repo viet). Thứ tự: Q3 → Q2 → Q4 → F3 → F4 → F7 → CI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Source of Truth for Bank Schema & Documentation (Priority: P1 - Q3)

As a developer or automated script maintaining handwriting banks,
I want the bank schema version, data contracts, and user documentation to be completely synchronized to Schema Version 4,
So that tools, migration scripts, and users never encounter contradictory schema expectations or broken exports.

**Why this priority**: Inconsistent schema versions create silent data corruption risks during cross-tool data sharing, synthetic bank generation, and practice sheet migration.
**Independent Test**: Running schema validation across newly generated synthetic banks, migrated banks, and checking documentation ensures Schema v4 is universally referenced.

**Acceptance Scenarios**:
1. **Given** any utility script generating or migrating banks (`scripts/gen_synthetic_bank.py`, `scripts/migrate_letter_bank.py`), **When** an output bank is produced, **Then** its `schema_version` attribute is explicitly set to 4 and validates against the strict Schema v4 specification.
2. **Given** the project documentation (`README.md`, `CHANGELOG.md`, `chuviettay/model/bank_schema.py`), **When** a user inspects schema versions or practice grid contents, **Then** all references uniformly specify Schema Version 4, and the practice grid description accurately reflects 77+ character cells without claiming digits are part of the grid.
3. **Given** visual documentation artifacts (`docs/img/after_fix.png`), **When** reviewing documentation status, **Then** the repository acknowledges historical image provenance without regenerating synthetic approximations that distort authorial handwriting fidelity.

---

### User Story 2 - Real-Path Layout Engine Test Convergence & Legacy Cleanup (Priority: P1 - Q2)

As a maintainer of the handwriting layout engine,
I want all functional tests to exercise the true production pipeline (`DocumentLayoutEngine` / `AppController.write_text`) instead of obsolete deprecated composer routines,
So that deprecated layout paths can be safely removed without reducing test coverage or regressing rendering quality.

**Why this priority**: Dual layout paths create technical debt, confuse contributors, and leave dead code that could mask production regressions.
**Independent Test**: Execute the test suite where all 12 deprecated layout calls are routed through the production engine, followed by removal of deprecated legacy functions while preserving 100% test pass rate.

**Acceptance Scenarios**:
1. **Given** existing test suites in `tests/test_composer.py` and `tests/test_letter_assembly_quality.py`, **When** executed, **Then** all tests call the real production layout pipeline while verifying identical layout invariants (minimum stroke clearance >= 0.8x pen thickness, bounding box overlap limits, auto-xh scaling).
2. **Given** the verified Step 0 real-path golden master (`tests/test_golden_master_real_path.py`), **When** deprecated composer functions (`compose_document`, `composer.write_document`) and legacy golden master (`tests/test_golden_master.py`) are deleted, **Then** the production golden master passes with 100% byte invariance.
3. **Given** client modules importing public contracts (`WriteOptions`, `WriteResult`), **When** legacy composer functions are removed, **Then** public contracts remain importable from `chuviettay.model.composer` preserving API compatibility.

---

### User Story 3 - Automated Quantitative Acceptance Testing with Synthetic Letters (Priority: P1 - Q4)

As a release engineer and contributor,
I want CI to run objective ink measurement metrics against a deterministic synthetic letter bank covering all standard Vietnamese characters,
So that pull requests are automatically validated for text coverage, spacing, and stroke proportions without depending on private handwriting archives.

**Why this priority**: Continuous Integration cannot run tests on private user archives; a deterministic synthetic letter bank provides reproducible, zero-dependency validation of letter assembly quality.
**Independent Test**: Running the acceptance suite on `accept_sample.txt` with `--assemble --auto-xh` against a generated synthetic bank asserts that 0 words are skipped, spacing is within bounds, and x-height conforms to notebook standards.

**Acceptance Scenarios**:
1. **Given** `scripts/gen_synthetic_bank.py`, **When** `build_synthetic_letter_bank(seed)` is called, **Then** it returns a Schema v4 bank dictionary containing all Vietnamese alphabet letters (upper and lowercase), 5 standalone tone marks, calibrated x-height (7.94 pt), and deterministic geometric strokes.
2. **Given** the synthetic letter bank and acceptance text (`tests/data/accept_sample.txt`), **When** synthesized with assembly and auto-scaling enabled, **Then** exactly 0 words are omitted or left blank in the output document.
3. **Given** output synthesized from the acceptance text, **When** measured with `tools/measure_ink.py`, **Then** the metrics satisfy:
   - Minimum stroke clearance: >= 0.8x pen thickness
   - Maximum bounding box overlap: <= 10.0%
   - Median x-height: within 7.94 pt ± 10% (7.15 pt to 8.73 pt)
   - Pen-to-x-height ratio: within 0.15 to 0.20

---

### User Story 4 - Complete Latin Alphabet in Practice Sheets (Priority: P2 - F3)

As a student or technical note-taker practicing handwriting,
I want the `hw3` practice sheet to include the Latin letters **f, j, w, z** (uppercase and lowercase),
So that loanwords, technical identifiers, and proper names (e.g. `wifi`, `win`, `jazz`, `json`) can be collected and assembled without missing character gaps.

**Why this priority**: Without f, j, w, z, modern technical notes and foreign loanwords cannot be synthesized via single-letter assembly.
**Independent Test**: Generating a practice grid exports the additional 8 character cells, and learning from both old (77 cells) and new (85 cells) practice sheets ingests letters accurately into `bank.letters`.

**Acceptance Scenarios**:
1. **Given** the practice grid generation command (`hw_note.py grid`), **When** exporting an `hw3` template, **Then** the grid contains uppercase and lowercase `F/f, J/j, W/w, Z/z` in addition to Vietnamese letters, vowel clusters, and tone marks.
2. **Given** an existing practice grid generated prior to adding new letters (77 cells), **When** ingested via `hw_note.py learn`, **Then** the parser reads all valid handwriting cells without crashing or misaligning cell boundaries.
3. **Given** practice sheet parsing in `learning.py`, **When** ingesting single-character cells, **Then** only alphabetic letters are stored in `bank.letters`, preventing non-letter symbols from polluting letter storage.

---

### User Story 5 - Robust Bank and Log Discovery for Standard Package Installations (Priority: P2 - F4)

As a user installing `chuviettay` via `pip`,
I want the application to look for the handwriting bank in portable and standard OS user directories rather than inside `site-packages`,
So that CLI and GUI commands like `hw-note stats` succeed immediately without permission errors or missing bank failures.

**Why this priority**: System Python directories are read-only for standard users; attempting to read/write banks inside `site-packages` breaks standard pip installations.
**Independent Test**: Running `hw-note stats` in a clean environment without `--bank` locates the user's bank in the standard OS data path and creates directory hierarchies automatically.

**Acceptance Scenarios**:
1. **Given** a command invoked with `--bank <path>`, **When** locating the bank, **Then** the explicit path takes absolute precedence.
2. **Given** a portable application deployment where `chu_cua_ban.json.gz` already exists alongside the executable or entry script, **When** running without `--bank`, **Then** the local file is loaded preserving portable behavior.
3. **Given** a standard `pip install` without a local bank file, **When** resolving the default bank path, **Then** the path resolves to the operating system's standard user data directory:
   - Windows: `%APPDATA%\chuviettay\chu_cua_ban.json.gz`
   - macOS: `~/Library/Application Support/chuviettay/chu_cua_ban.json.gz`
   - Linux: `$XDG_DATA_HOME/chuviettay/chu_cua_ban.json.gz` (or `~/.local/share/chuviettay/chu_cua_ban.json.gz`)
4. **Given** a missing bank error in CLI, **When** reporting to the user, **Then** the error message provides accurate instructions pointing to the OS user data directory rather than assuming a local script directory.

---

### User Story 6 - Xournal++ Native Background Style Compliance (Priority: P3 - F7)

As an active Xournal++ user,
I want background page styles (`iso_graph`, `iso_dotted`, `music`) to be written using valid Xournal++ XML attributes (`isograph`, `isodotted`, `staves`),
So that my exported handwritten notes render their intended ruling patterns instead of reverting to plain white pages in Xournal++.

**Why this priority**: Xournal++ silently falls back to a plain white background when encountering non-standard background attribute values.
**Independent Test**: Exporting documents with each background style produces XML adhering to Xournal++ core source definitions, while bidirectional reading supports both naming variants.

**Acceptance Scenarios**:
1. **Given** user-selected background styles via CLI or GUI (`iso_graph`, `iso_dotted`, `music`), **When** serializing the document to `.xopp` XML, **Then** the attributes are written as native Xournal++ identifiers:
   - `iso_graph` -> `isograph`
   - `iso_dotted` -> `isodotted`
   - `music` -> `staves`
2. **Given** standard background styles (`plain`, `lined`, `ruled`, `graph`, `dotted`), **When** serializing, **Then** attribute names remain unaltered.
3. **Given** parsing of existing `.xopp` files, **When** reading background style attributes, **Then** both legacy (`iso_graph`) and canonical (`isograph`) identifiers are correctly parsed.

---

### User Story 7 - Continuous Integration Hardening (Priority: P3 - CI)

As a project maintainer,
I want CI to run a clean pip install smoke test, isolate performance benchmarks, and report test coverage,
So that environment-specific packaging flaws (like F4) and timing regressions are caught on every pull request.

**Why this priority**: Catches packaging regressions and ensures long-running benchmarks do not cause spurious timeouts during regular test runs.
**Independent Test**: The CI workflow executes a dedicated pip smoke test step in an isolated virtual environment and runs benchmarks separately from coverage.

**Acceptance Scenarios**:
1. **Given** a CI workflow run, **When** executing the pip smoke test, **Then** it installs the package from source in an isolated environment, runs `hw-note --help`, creates a temporary bank, and executes `hw-note stats` successfully.
2. **Given** the test suite in CI, **When** running coverage checks, **Then** tests marked `@pytest.mark.benchmark` run in a dedicated stage without coverage overhead.

---

### Edge Cases

- **Mixed Schema Ingestion**: What happens when a user imports an older Schema v2 or v3 bank into an environment expecting Schema v4? The automated migrators in `bank_schema.py` must transparently upgrade the in-memory data to v4 without data loss.
- **Corrupted User Data Directory**: What happens when the OS user data directory cannot be created due to permissions? The system must raise a clear `BankNotFoundError` or descriptive OS error explaining the exact directory path.
- **Practice Sheet Layout Drift**: What happens if an older 77-cell practice grid is passed to `learn` after adding `f, j, w, z`? The parser must inspect cell coordinate bounding boxes or row/column indexes rather than hardcoding static array offsets, successfully extracting all 77 characters.
- **Background Name Aliasing**: What happens when an external tool writes `isograph` and another writes `iso_graph`? The parser normalizes both into a unified internal representation.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST standardize on Schema Version 4 as the single source of truth across all code, docstrings, migrators, and synthetic bank generators.
- **FR-002**: Project documentation (`README.md`) MUST accurately reflect that `hw3` practice grids generate character and vowel cluster cells, while digits and punctuation are trained via the minimal essentials workflow.
- **FR-003**: System MUST execute all functional layout tests via `DocumentLayoutEngine` and `AppController.write_text`, deprecating and removing legacy `compose_document` and `composer.write_document` without altering test semantics.
- **FR-004**: System MUST provide a public generator function `build_synthetic_letter_bank(seed)` producing a complete, deterministic, Schema v4 synthetic bank containing all Vietnamese alphabetic characters, tone marks, and geometric strokes.
- **FR-005**: Automated acceptance testing MUST verify that synthesis of `accept_sample.txt` with `--assemble --auto-xh` achieves 0 missing words, stroke clearance >= 0.8x pen thickness, bounding box overlap <= 10.0%, and median x-height within 7.94 pt ± 10%.
- **FR-006**: Practice grid generator MUST include uppercase and lowercase `f, F, j, J, w, W, z, Z` (+8 cells), expanding grid capacity from 77 to 85 cells while preserving backward compatibility for 77-cell grids.
- **FR-007**: Practice sheet ingestion in `learning.py` MUST validate that single-character cells are alphabetic letters before storing them in `bank.letters`.
- **FR-008**: Default bank discovery MUST follow a deterministic priority: (1) explicit `--bank`, (2) existing file in local/portable directory, (3) OS standard user data directory (`%APPDATA%`, `~/Library/Application Support`, `$XDG_DATA_HOME`).
- **FR-009**: Document serialization to `.xopp` XML MUST map background styles `iso_graph -> isograph`, `iso_dotted -> isodotted`, and `music -> staves` to match native Xournal++ format definitions.
- **FR-010**: Document deserialization MUST accept both canonical Xournal++ identifiers and legacy hyphenated/underscored style identifiers.
- **FR-011**: CI workflow MUST include an isolated `pip install` smoke test step validating CLI commands (`hw-note --help`, `hw-note stats`).
- **FR-012**: CI workflow MUST run benchmark tests in an uninstrumented step separate from code coverage.

---

### Key Entities

- **Bank Schema (Version 4)**: The persistent JSON data contract defining storage for `words`, `digits`, `punct`, `symbols`, `letters`, `marks`, `tombstones`, and generation metadata.
- **Synthetic Letter Bank**: A reproducible, algorithmically generated bank dictionary containing geometric strokes for all 29 Vietnamese letters (x2 case), 4 loan letters (x2 case), and 5 tone marks.
- **Practice Grid (HW3)**: A 4-line rule Xournal++ template containing labeled bounding boxes for collecting individual handwriting samples, expanded to 85 cells.
- **Page Background Format**: The page styling metadata mapping user-friendly ruling names to Xournal++ internal string tokens.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of functional tests in `tests/` pass using the production layout engine, with deprecated composer routines (~150 lines) safely pruned.
- **SC-002**: Automated acceptance test suite verifies 0 missing words on `tests/data/accept_sample.txt` with clearance >= 0.8x pen thickness and overlap <= 10.0%.
- **SC-003**: 100% of CLI and GUI tests pass across platforms without requiring local directory write permissions when installed via `pip`.
- **SC-004**: XML output for all 8 background styles matches official Xournal++ parser specifications (`PageTypeHandler.cpp`).
- **SC-005**: Full test suite executes in continuous integration with zero failures, zero regressions on the Step 0 real-path golden master, and zero architectural violations.

---

## Assumptions

- **A-001**: The Step 0 real-path golden master (`tests/test_golden_master_real_path.py`) established in Phase 0 serves as the definitive byte-level regression baseline when pruning the legacy golden master.
- **A-002**: The historical visual artifact `docs/img/after_fix.png` should not be regenerated with synthetic approximations, as it represents authentic authorial handwriting from a private collection.
- **A-003**: Native Xournal++ source code at master branch (`PageTypeHandler.cpp`) defines the canonical XML background format strings.
- **A-004**: Standard operating system user directories (`%APPDATA%` on Windows, `~/Library/Application Support` on macOS, `$XDG_DATA_HOME` on Linux) are accessible for read and write operations during user sessions.
