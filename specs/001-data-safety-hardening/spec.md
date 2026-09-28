# Feature Specification: Data Safety and Core Reliability Hardening

**Feature Branch**: `001-data-safety-hardening`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Tôi đã rà soát trực tiếp repo caoduongle/viet, branch main, commit hiện tại 621c01394ddb27f44e7dfebfac962cafc7a6cc7f... [P0: Tách kho chữ cá nhân khỏi source/test, P1: Sửa GUI --bank typo, P1: Schema version & migration, P1: Concurrency lock & fsync, P1: Validation WriteOptions & color XML, P1: CI/CD, P1/P2: Test corruption & edge cases, P2: Logging fallback, P2: Build reproducibility & pyproject.toml, P2: Loại bỏ tracked binary, P2: LICENSE & kiến trúc]"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Protection of Personal Handwriting Data & Isolated Test Fixtures (Priority: P1)

As a handwriting app contributor and user, I want my personal handwriting profile kept out of public version control, and I want the automated test suite to run against dedicated synthetic benchmark fixtures, so that my personal biometric handwriting data is never inadvertently leaked or coupled to unit tests.

**Why this priority**: Storing actual biometric handwriting data in the source tree is a critical privacy and open-source compliance risk. Furthermore, coupling regression tests to a personal data file prevents reproducible testing and violates test isolation principles.

**Independent Test**: Verify that the personal handwriting profile is ignored by default in version control, and that running the test suite completes successfully without requiring or reading personal handwriting profiles.

**Acceptance Scenarios**:
1. **Given** a clean clone of the project, **When** a user generates or updates their local personal handwriting file, **Then** version control flags it as ignored and does not stage it.
2. **Given** the automated test suite, **When** tests execute, **Then** all tests use a dedicated synthetic test fixture and produce deterministic results without referencing personal user profiles.

---

### User Story 2 - Safe Bank Loading without Unintended Creation on Typo (Priority: P1)

As a user launching the application with an explicit profile/bank path, I want the system to alert me with a clear error message if the path is invalid or misspelled, rather than silently creating a blank new bank, so that I do not mistake a typo for data loss.

**Why this priority**: Silently creating a blank file when an explicit path was supplied causes severe user panic (appearing as though all previously taught words have vanished).

**Independent Test**: Launch the application pointing to a non-existent path via explicit parameter; verify that the system halts or alerts the user with an explicit "file not found" notification and does not create an empty file on disk.

**Acceptance Scenarios**:
1. **Given** an explicit custom bank path that does not exist, **When** the application starts, **Then** it refuses to initialize a blank bank at that path and displays a clear error indicating the file was not found.
2. **Given** no custom bank path is specified and the default profile file is missing, **When** the application starts, **Then** it is permitted to create a default starter bank for first-time onboarding.

---

### User Story 3 - Data Schema Integrity and Backward-Compatible Migration (Priority: P1)

As a user with existing handwriting bank files from earlier versions, I want the application to validate data integrity upon loading and automatically handle version differences, so that corrupted or outdated files do not cause cryptic system crashes.

**Why this priority**: Corrupted, tampered, or legacy bank structures cause uncontrolled runtime crashes. Explicit schema validation and managed migration ensure long-term data safety as the application evolves.

**Independent Test**: Load valid current banks, valid legacy banks, and intentionally malformed/corrupted files; verify that valid banks load (and migrate if legacy), while corrupted files produce clear diagnostic validation errors.

**Acceptance Scenarios**:
1. **Given** a legacy handwriting bank lacking explicit version metadata, **When** loaded, **Then** the system detects the legacy format, validates required structural elements, and seamlessly migrates it to the current schema.
2. **Given** a corrupted, truncated, or structurally invalid bank file, **When** loaded, **Then** the system halts loading with a specific diagnostic message identifying the structural failure rather than an unhandled internal exception.

---

### User Story 4 - Reliable Concurrent Saving and Write Durability (Priority: P1)

As a user who may use both CLI and GUI interfaces or operate in multitasking environments, I want saving operations to be protected against concurrent write collisions and disk write caching failures, so that my handwriting profile is never corrupted during unexpected shutdown or concurrent tool execution.

**Why this priority**: Multiple processes accessing the same handwriting bank simultaneously can overwrite or corrupt the file if temporary files collide or file locking is absent.

**Independent Test**: Trigger simulated concurrent write operations and system interruptions; verify that bank saves utilize unique temporary workspaces, inter-process synchronization, and forced storage flushing, ensuring that the target file remains intact and uncorrupted.

**Acceptance Scenarios**:
1. **Given** two processes attempting to save changes to the same handwriting bank simultaneously, **When** both invoke the save operation, **Then** saving operations are serialized safely via file locking without overwriting each other's temporary files.
2. **Given** an in-flight save operation, **When** data is written to disk, **Then** all buffers are fully committed to physical storage before replacing the original file.

---

### User Story 5 - Comprehensive Input Validation for Writing and Rendering Options (Priority: P1)

As a user generating handwritten documents via graphical interface or command-line parameters, I want all formatting options (dimensions, scale, jitter, spacing, colors) strictly validated before processing, so that invalid inputs (negative values, NaN, infinity, ill-formed color strings) are rejected before corrupting the document output or breaking XML markup.

**Why this priority**: Unvalidated numeric and string inputs can cause division errors, non-finite XML coordinates, or broken document markup that crashes downstream viewer applications like Xournal++.

**Independent Test**: Provide boundary and invalid values (negative scale, infinite width, malformed color hex strings); verify that the validator rejects them with actionable messages before any rendering or document synthesis occurs.

**Acceptance Scenarios**:
1. **Given** invalid numeric inputs (e.g. non-positive scale, negative jitter, NaN, infinity), **When** a write action is requested, **Then** the system rejects the operation and displays specific validation errors.
2. **Given** a color value, **When** checked, **Then** only valid standard color codes (such as `#RRGGBB` or `#RRGGBBAA`) are accepted, preventing XML attribute injection.

---

### User Story 6 - Continuous Quality Assurance via Automated CI Workflows (Priority: P2)

As a developer and maintainer, I want every pull request and push automatically verified by an automated build and test pipeline, so that regressions, compilation failures, and architecture violations are caught immediately.

**Why this priority**: The repository currently lacks automated CI runs, allowing regressions to go unnoticed until manual developer testing.

**Independent Test**: Trigger a push or pull request; verify that the automated workflow runs the complete test suite and code compilation checks across supported operating platforms.

**Acceptance Scenarios**:
1. **Given** newly pushed code changes, **When** processed by continuous integration, **Then** unit tests, architecture tests, and compilation checks are automatically executed and reported.

---

### User Story 7 - Reproducible Build Pipeline and Standardized Packaging (Priority: P2)

As a distributor or advanced user, I want the project to adhere to modern packaging standards with clearly declared dependencies and pinned build tooling, so that application packaging produces consistent, reproducible binaries across clean environments.

**Why this priority**: Unpinned packaging tools and lack of standard project metadata lead to environment drift, broken standalone executable builds, and ambiguous Python version requirements.

**Independent Test**: Build the project from a clean isolated virtual environment using pinned build specifications; verify that dependencies install cleanly and packaging succeeds.

**Acceptance Scenarios**:
1. **Given** a modern Python 3.10+ environment, **When** inspecting package metadata, **Then** Python version constraints, dependencies, and entry points are explicitly defined in standard project configuration.
2. **Given** standalone binary build scripts, **When** executed, **Then** builds use reproducible, pinned packaging dependencies rather than arbitrary unconstrained packages.

---

### User Story 8 - Resilient Logging with User-Writable Storage Fallbacks (Priority: P3)

As an end user running the application from read-only media or restricted directories, I want operational logs to fall back gracefully to standard user data directories, so that error logs are reliably recorded and diagnostic messages accurately indicate where logs were written.

**Why this priority**: If the application cannot write to its installation folder, it currently fails to log silently while still claiming to the user that details were saved to that uncreatable file.

**Independent Test**: Run the application in a directory where the process lacks write permissions; verify that the application detects the constraint, falls back to the user's standard application data directory, and accurately reports the active log location.

**Acceptance Scenarios**:
1. **Given** the application directory is read-only, **When** logging is initialized, **Then** logs are routed to the OS-appropriate user application data folder and UI error dialogues report the true log file path.

---

### Edge Cases

- What happens when a handwriting bank file is completely empty (0 bytes) or contains invalid gzip data?
  The system must raise a descriptive bank corruption error without crashing ungracefully.
- What happens when multiple combining diacritical marks in Vietnamese Unicode (e.g. decomposed vs precomposed Unicode) are supplied as text input?
  Text normalization must ensure consistent canonical representation before matching glyph samples.
- What happens if the file lock cannot be acquired during a save because another process held it and crashed?
  The locking mechanism must implement reasonable timeouts and stale lock handling to avoid permanent deadlock.
- What happens when a user enters non-standard color strings like `"blue"`, `"rgb(0,0,0)"`, or XML injection strings `"#000000\" width=\"99"`?
  The color validator must reject any format not matching strict `#RRGGBB` or `#RRGGBBAA` hexadecimal syntax.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST exclude the personal handwriting profile (`chu_cua_ban.json.gz`) from git tracking and ensure standard ignore rules prevent its re-addition.
- **FR-002**: System MUST replace the committed personal handwriting test fixture (`tests/data/kho_mau_chup_lai.json.gz`) with a dedicated synthetic benchmark fixture generated by an internal build/test script that produces geometric pseudo-stroke data, entirely free of personal biometric content, and reproducibly regenerable at any time.
- **FR-003**: System MUST provide an explicit schema versioning contract (e.g., `schema_version`) and validate bank dictionary structures upon loading.
- **FR-004**: System MUST support legacy unversioned bank formats by validating their baseline structure and migrating them in-memory upon loading; the updated `schema_version` is persisted to disk only when the next genuine save operation occurs (e.g. learning a new word or deleting a sample), ensuring read-only usage never modifies the user's file.
- **FR-005**: System MUST reject invalid, corrupted, or unsupported future schema version files with human-readable diagnostic messages.
- **FR-006**: System MUST prevent accidental creation of new bank files when the user explicitly provides a `--bank` path that does not exist, displaying an error instead.
- **FR-007**: System MUST permit automatic creation of a default empty bank only when no custom `--bank` path was specified and the default profile does not exist.
- **FR-008**: System MUST perform safe atomic file persistence using unique process-specific temporary files, ensuring concurrent writes do not collide.
- **FR-009**: System MUST enforce cross-platform inter-process file locking during save operations on handwriting banks.
- **FR-010**: System MUST flush and synchronize in-flight file buffers to physical storage (`fsync`) before executing atomic replacement.
- **FR-011**: System MUST strictly validate all document writing options (`scale`, `line`, `width`, `space`, `jitter`, `wscale`) across both CLI and GUI interfaces, rejecting non-positive dimensions, negative jitters, NaN, and infinite values.
- **FR-012**: System MUST validate color options strictly against `#RRGGBB` or `#RRGGBBAA` formats before allowing them into document markup.
- **FR-013**: System MUST preserve 100% behavioral fidelity of the core handwriting synthesis algorithms in `writer.py` and `text_utils.py`, maintaining existing golden-master test compatibility.
- **FR-014**: System MUST establish automated CI workflows on GitHub Actions running test suites and compilation checks on push and pull requests.
- **FR-015**: System MUST remove pre-built binaries (`hw_gui-linux`) from source tree tracking immediately in this refactor via `git rm`, and transition binary distribution to automated GitHub Actions Release Artifacts.
- **FR-016**: System MUST define standard project metadata and minimum Python requirements (`>=3.10`) via a standard `pyproject.toml` file.
- **FR-017**: System MUST provide reproducible build specifications (`requirements-build.txt`) with pinned packaging tools.
- **FR-018**: System MUST include a project `LICENSE` file clarifying software and data licensing terms.
- **FR-019**: System MUST provide fallback log file paths in standard user data directories when the application directory is non-writable.
- **FR-020**: System MUST enforce architectural separation in automated tests to prevent user interface components from directly bypassing the Controller to access internal Model instances.
- **FR-021**: System MUST strengthen existing tests whose assertions do not fully verify their stated contracts (specifically `test_jitter_0_thi_khong_con_ngau_nhien_ve_hinh_dang`).

### Key Entities *(include if feature involves data)*

- **Handwriting Bank (`Bank`)**: A compressed JSON structure storing taught word stroke samples, diacritic marks, pen parameters, character height (`xh`), and an explicit `schema_version`.
- **Write Options (`WriteOptions`)**: A validated configuration object defining scaling, line spacing, margins, word spacing, jitter randomness, pen weight scaling, stroke color, and random seed.
- **Write Result (`WriteResult`)**: The structured outcome of a document synthesis operation containing line counts, stroke counts, token statistics, and missing glyph inventories.
- **Synthetic Test Bank**: A non-personal, deterministically generated or synthetic fixture containing minimal necessary phonemes and marks for automated testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of personal handwriting data is eliminated from source tracking, with zero matching SHA blobs between personal profile files and test fixtures.
- **SC-002**: Automated test coverage successfully executes in continuous integration with 0 failures across supported platforms (Ubuntu and Windows).
- **SC-003**: 100% of invalid writing options (such as negative scale, infinite width, NaN values, and malformed color strings) are rejected before document generation begins.
- **SC-004**: Bank save operations subjected to simulated concurrent process writes result in 0 file corruptions or data loss incidents.
- **SC-005**: 100% of golden-master regression test assertions continue to pass without algorithm modification.
- **SC-006**: When launched with an invalid explicit `--bank` path, the application fails safely 100% of the time without generating empty files on disk.

## Assumptions

- Python 3.10 is the minimum supported Python version due to modern type hint union syntax (`|`) and modern typing features used across the codebase.
- Cross-platform file locking will support both Windows and POSIX operating systems using native system primitives.
- Existing user banks from prior releases will be automatically readable and non-destructively handled without requiring manual user conversion steps.
- Core handwriting layout mathematics (`writer.py`, `text_utils.py`, `composer.py`) remain functionally unchanged to protect handwriting visual style.
