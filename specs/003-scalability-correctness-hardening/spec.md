# Feature Specification: Scalability, Correctness, and CI Hardening

**Feature Branch**: `003-scalability-correctness-hardening`

**Created**: 2026-09-29

**Status**: Implemented

**Input**: User description: "Rà soát lại commit 31f289c và GitHub Actions: 1. CI Windows 3.10 fail do Tk/Tcl init.tcl; 2. Incremental indexing chưa thực sự O(1); 3. Incremental marks lệch rebuild() do mất mark bị lọc; 4. Benchmark và save() chưa tối ưu cho large bank (merge + rebuild + gzip toàn bộ); 5. Lost-update do delete vẫn còn (hồi sinh từ); 6. merge_bank_dicts() stroke_signature chỉ dựa trên 's'; 7. Deep schema validation chưa kiểm tra T/vi/ti invariant; 8. Schema chưa kiểm tra sâu pen (tool/color/width); 9. Git purge script backup branch trong repo không an toàn; 10. README lệch CI (Python 3.11/3.13)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resilient Cross-Platform CI and Graphical Test Isolation (Priority: P1)

As a contributor or maintainer verifying pull requests, I want the automated continuous integration workflow to execute deterministically across all supported platforms and Python versions without false-positive failures caused by incomplete or corrupted system graphical environments, so that code quality and regression gates remain strictly green.

**Why this priority**: CI is currently failing on Windows with Python 3.10 because the runner's Tcl/Tk runtime is incomplete (`init.tcl` / `listbox.tcl` missing). When an environment cannot instantiate graphical desktop components, tests that require a functioning Tk display must be cleanly detected and skipped, while 100% of core algorithms, persistence, CLI, and schema validation continue to execute and pass.

**Independent Test**: Execute the full test suite in an environment with missing or broken Tcl/Tk system libraries; verify that non-GUI unit, domain, and persistence tests pass completely and graphical tests report clean skips without unhandled environment crashes.

**Acceptance Scenarios**:
1. **Given** a CI runner or headless environment where the Tcl/Tk graphical runtime is missing, damaged, or uninitialized, **When** the test suite executes, **Then** Tk-dependent test fixtures detect the environment failure, report a clean skip with descriptive context, and allow the remaining test suite to pass with exit code 0.
2. **Given** an environment with a fully functional Tcl/Tk desktop runtime (e.g. Windows Python 3.12 or Linux with Xvfb), **When** the test suite executes, **Then** all GUI integration tests execute normally and pass.

---

### User Story 2 - Incremental Indexing Parity and Raw Mark Preservation (Priority: P1)

As an interactive user teaching new words or handwriting samples into the bank, I want incremental index updates to produce mathematically identical results to a complete database rebuild, while maintaining efficient index updates, so that newly taught words never degrade or diverge tone mark selection.

**Why this priority**: The current incremental index implementation filters tone marks by percentiles and discards excluded marks from memory. If subsequent samples shift the percentile boundaries, previously valid marks can never be recovered without a full rebuild from raw data. Furthermore, sorting tone marks on every sample addition violates the intended algorithmic complexity contract.

**Independent Test**: Teach a sequence of 50 samples with diverse tone marks incrementally; compare the resulting tone mark cache (`marks`) and stripped-tone substitution index (`tl`) against a bank loaded and rebuilt from scratch using `rebuild()`; verify identical candidate sets and percentile bounds.

**Acceptance Scenarios**:
1. **Given** an existing handwriting bank, **When** new samples are added via the incremental API, **Then** all raw harvested tone marks are retained in an underlying raw collection, ensuring no historical marks are permanently lost due to dynamic percentile filtering.
2. **Given** a sequence of sample additions that causes statistical percentiles to shift, **When** query tone marks are requested, **Then** marks that become valid under the updated percentiles are correctly included in the query index.
3. **Given** an incrementally populated bank and a bank rebuilt from the same underlying word dictionary, **When** comparing their query indexes, **Then** both indexes match exactly.
4. **Given** frequent word additions, **When** updating tone marks, **Then** index maintenance avoids redundant full-array re-sorting for every added mark.

---

### User Story 3 - Persistent Deletion Tombstones and Cross-Process Deletion Safety (Priority: P1)

As a user running concurrent application sessions or managing words via CLI and GUI, I want deletions made in one session to persist reliably across concurrent saves, so that deleted words are not accidentally resurrected when another process saves an older snapshot.

**Why this priority**: The current merge strategy protects concurrent additions, but in-memory deletion sets (`_deleted_words`) are ephemeral and cleared upon saving. If Process A deletes a word and saves, and Process B later saves an addition to another word from an earlier snapshot, Process B's merge logic resurrects the word deleted by Process A.

**Independent Test**: Open a shared bank in two separate processes; delete a word in Process A and save; add a different word in Process B and save; verify that the deleted word remains deleted in the final bank file and the newly added word is preserved.

**Acceptance Scenarios**:
1. **Given** Process A and Process B opened on the same handwriting bank, **When** Process A deletes word "xin" and saves, and Process B subsequently saves local additions to other words, **Then** "xin" remains deleted in the persisted bank and is not resurrected.
2. **Given** a bank with recorded deletion tombstones, **When** a user deliberately teaches or re-adds a sample for the deleted word, **Then** the deletion tombstone for that word is revoked and the word becomes active again.
3. **Given** persisted deletion tombstones in the bank file, **When** validated and loaded, **Then** tombstones are safely recognized and maintained without corrupting backward compatibility.

---

### User Story 4 - Scalable Persistence Architecture for Large Handwriting Profiles (Priority: P1)

As a user training large handwriting banks with thousands of samples, I want interactive word teaching to save quickly without freezing the application, avoiding redundant full-database re-reading, full re-indexing, and full-file gzip re-compression on every single taught word.

**Why this priority**: Currently, calling `teach_word()` forces an immediate `Bank.save()` which re-reads the entire file from disk, merges, runs full `rebuild()`, and re-compresses the entire database with gzip. On banks with 10,000+ samples, this creates substantial UI latency and eliminates the benefit of fast in-memory indexing.

**Independent Test**: Measure the end-to-end latency of teaching 50 consecutive words into a bank with over 5,000 samples; verify that interactive teaching remains responsive and sub-second per word or supports non-blocking deferred/batched persistence.

**Acceptance Scenarios**:
1. **Given** a bank containing thousands of samples, **When** a user teaches words interactively in the GUI or via batch scripts, **Then** each word addition persists or stages durable changes without re-indexing the entire database from scratch.
2. **Given** an interactive teaching session with multiple words, **When** saving to disk, **Then** the application ensures data durability while minimizing redundant disk I/O and compression overhead.

---

### User Story 5 - Deep Schema Invariants for Tone Metadata and Pen Configuration (Priority: P2)

As a developer or user loading third-party or migrated handwriting banks, I want schema validation to rigorously verify internal invariants for tone markers (`T`, `vi`, `ti`) and pen rendering attributes (`tool`, `color`, `width`), so that malformed data is rejected immediately at load time rather than triggering `IndexError` or rendering exceptions during document synthesis.

**Why this priority**: A sample with `ti >= len(s)` or `vi` referencing an invalid vowel index passes existing schema checks but triggers an unhandled `IndexError` during `rebuild()` or document generation. Additionally, unvalidated pen attributes can cause XML/XOPP rendering failures.

**Independent Test**: Load bank dictionaries containing invalid tone stroke indices (`ti >= len(s)`), mismatched vowel indices (`vi`), or malformed pen color strings; verify that `BankValidationError` is raised with precise path diagnostics.

**Acceptance Scenarios**:
1. **Given** a sample with tone attributes, **When** validated, **Then** the system verifies that `ti` is a valid stroke index (`-1 <= ti < len(s)`), `T` is an allowed tone or empty, and `vi` is consistent with the vowel position of the word.
2. **Given** a bank with pen settings, **When** validated, **Then** the system validates that `pen.color` is a valid hexadecimal color string (`#RRGGBB` or `#RRGGBBAA`), `pen.tool` is a non-empty string, and `pen.width` represents a positive finite dimension.

---

### User Story 6 - Explicit Sample Identity Contract for Multi-Process Merging (Priority: P2)

As a user combining or synchronizing handwriting banks, I want an unambiguous sample identity definition during data merge, so that distinct handwriting variations are preserved and identical duplicate samples are deduplicated predictably.

**Why this priority**: The current sample signature relies exclusively on rounded stroke coordinates, ignoring sample metadata (`w, T, vi, ti`). If two samples share the same stroke geometry but have different metadata, one is silently dropped.

**Independent Test**: Merge two bank structures containing samples with identical strokes but different width or tone annotations; verify that merge decisions conform strictly to the specified identity contract.

**Acceptance Scenarios**:
1. **Given** two bank snapshots being merged, **When** samples are compared for deduplication, **Then** the comparison evaluates both stroke coordinates and sample metadata according to the established identity contract.

---

### User Story 7 - Safe and Isolated Git History Purge Automation (Priority: P2 / Operational)

As a repository administrator purging historical personal data blobs from version control, I want the purge automation scripts to mandate an isolated clone and external backups rather than creating in-repo branches that are rewritten by git-filter-repo, preventing accidental corruption of local worktrees.

**Why this priority**: `git-filter-repo` rewrites refs across the repository and strips origin remotes. An in-repo backup branch does not provide an independent safety net. Recommended practice requires a fresh, dedicated clone with an external backup before rewriting history.

**Independent Test**: Review and dry-run the purge automation scripts; verify that the script verifies isolated clone prerequisites, creates an external backup, and provides safe verification and push instructions.

**Acceptance Scenarios**:
1. **Given** a user executing the git history purge script, **When** run in a primary working clone, **Then** the script advises or enforces running in a dedicated mirror/fresh clone and creates an external backup archive prior to execution.
2. **Given** completion of the purge command, **When** inspected with `git log --all`, **Then** all historical references to personal data files are gone and clear guidance is provided for force-pushing.

---

### User Story 8 - CI Matrix Parity and Documentation Accuracy (Priority: P3)

As a user or contributor reviewing the repository, I want the stated Python version support in the documentation (`README.md`) to be fully backed by continuous integration workflows, so that claimed compatibility is proven by automated tests.

**Why this priority**: `README.md` states that Python 3.10, 3.11, 3.12, and 3.13 are continuously tested on CI, but the CI matrix currently only includes 3.10 and 3.12. Aligning documentation and CI matrices restores complete accuracy.

**Independent Test**: Verify that all Python versions advertised in `README.md` are actively represented in `.github/workflows/ci.yml` or the documentation accurately reflects the active test matrix.

**Acceptance Scenarios**:
1. **Given** the CI matrix configuration and `README.md`, **When** inspected, **Then** the list of tested Python versions in the documentation matches the actual test matrix in the CI configuration file.

---

### Edge Cases

- What happens if Tcl/Tk is completely absent, or `init.tcl` is corrupted on a headless Windows/Linux runner?
  The test fixture must intercept `_tkinter.TclError` during Tk root initialization or window construction, log a diagnostic skip notice, and cleanly bypass GUI-dependent tests without failing the test run.
- What happens if a word is deleted in one process while a new sample for the same word is concurrently taught in another process?
  The merge resolution must evaluate generation/timestamp metadata: an explicit new addition created after a deletion must restore the word with the new sample, whereas additions originating from older snapshots must be suppressed by the tombstone.
- What happens if an older bank file lacks tombstone records?
  Validation and loading must treat absent tombstones as an empty set, ensuring 100% backward compatibility with existing v1/v2 bank files.
- What happens if a legacy sample has `ti == -1` or empty `T`?
  Validation must accept negative `ti` and empty `T` as indicating an untoned or body-only sample without raising errors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide robust graphical environment detection in test fixtures (`conftest.py` / `test_gui.py`), catching `_tkinter.TclError` during both fixture creation and widget initialization to skip GUI tests cleanly when Tk/Tcl runtimes are unavailable or defective.
- **FR-002**: System MUST retain all raw harvested tone marks in memory (`_raw_marks` or equivalent internal structure) during incremental indexing, so that dynamic percentile filtering never permanently discards historical marks.
- **FR-003**: System MUST ensure that `add_sample_incremental()` produces query lookup indexes (`marks`, `tl`) identical to those produced by `rebuild()` for the same underlying dataset.
- **FR-004**: System MUST optimize incremental sample addition to avoid redundant full-list percentile re-sorting on every single stroke or mark addition.
- **FR-005**: System MUST implement durable deletion tombstones in the bank data structure, persisting deleted word identifiers across saves to prevent resurrection by concurrent processes merging older snapshots.
- **FR-006**: System MUST clear the deletion tombstone for a word when a user explicitly re-teaches or adds a new sample for that word.
- **FR-007**: System MUST optimize the persistence pipeline for interactive teaching in `AppController` and `Bank` to prevent redundant full-database decompressions, full rebuilds, and compression cycles per taught word.
- **FR-008**: System MUST define an explicit sample identity contract for cross-process merging that evaluates both stroke geometry and sample metadata (`s`, `w`, `T`, `vi`, `ti`) to avoid unintended duplicate conflation.
- **FR-009**: System MUST enforce deep invariant validation in `validate_sample()`:
  - `ti` must satisfy `-1 <= ti < len(s)`.
  - If `T` is non-empty, `T` must be a recognized Vietnamese tone diacritic.
  - If `vi >= 0`, `vi` must reference a valid character position in the word label.
- **FR-010**: System MUST validate pen attributes in `validate_bank_dict()`:
  - `pen["tool"]` must be a non-empty string.
  - `pen["color"]` must be a valid hexadecimal color format matching `#RRGGBB` or `#RRGGBBAA`.
  - `pen["width"]` must represent a positive finite numeric value.
- **FR-011**: System MUST update git history purge documentation and scripts (`scripts/purge_git_history.sh` / `.ps1`) to require an external backup or dedicated fresh clone before invoking history rewriting.
- **FR-012**: System MUST synchronize `.github/workflows/ci.yml` and `README.md` so that advertised Python version support is accurately reflected in automated test coverage.
- **FR-013**: System MUST maintain 100% test pass rate across the full test suite and preserve byte-exact golden master rendering outputs.

### Key Entities *(include if feature involves data)*

- **Handwriting Bank (`Bank`)**: The persistent profile container managing words, stroke geometry, tone indexes, and deletion tombstones.
- **Raw Tone Mark Index (`_raw_marks`)**: The complete, unfiltered collection of harvested tone marks from all taught words, preserved across incremental updates.
- **Filtered Tone Mark Index (`marks`)**: The query-optimized cache of tone marks after outlier filtering, used by the document composer.
- **Deletion Tombstones (`tombstones` / `_tombstones`)**: Persistent records of explicitly deleted words, preventing resurrection during multi-process merges until deliberately re-taught.
- **Sample Identity (`SampleIdentity`)**: The unique tuple signature combining normalized stroke geometry and sample metadata (`w, T, vi, ti`) used for deduplication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of CI workflow jobs pass across all configured platforms (Windows, Linux) and Python versions, with zero unhandled `TclError` fixture failures.
- **SC-002**: 100% parity between incremental index state and full `rebuild()` index state across all tone marks and substitution lookups.
- **SC-003**: 0% resurrection rate for deleted words when concurrent processes save additions to unaffected words.
- **SC-004**: Sequential interactive teaching of 50 words achieves sub-second per-word response times on banks with over 5,000 samples.
- **SC-005**: 100% of malformed tone index invariants (`ti >= len(s)`, invalid `vi`) and invalid pen attributes are rejected during schema validation.
- **SC-006**: Documented Python version compatibility in `README.md` matches 100% with the active CI matrix in `.github/workflows/ci.yml`.
- **SC-007**: 100% of existing regression and golden-master tests continue to pass without output drift.

## Assumptions

- Python 3.10 remains the minimum supported runtime version.
- On CI runners or headless systems lacking a complete Tk/Tcl desktop runtime, GUI integration tests may be skipped safely without compromising core algorithmic or persistence verification.
- Handwriting stroke geometry and rendering layout mathematics in `writer.py` and `text_utils.py` remain untouched to preserve golden-master visual output.
- Deletion tombstones may be stored as an optional metadata field in the bank dictionary to maintain backward compatibility with legacy bank loaders.
