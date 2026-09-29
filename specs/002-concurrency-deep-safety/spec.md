# Feature Specification: Concurrency Deep Safety and Scalability Hardening

**Feature Branch**: `002-concurrency-deep-safety`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Rà soát lại repo caoduongle/viet ở commit mới nhất fbae1a5... P0: Xóa hoàn toàn dữ liệu cá nhân khỏi Git history nếu mục tiêu là purge; P1: Sửa lost-update giữa GUI/CLI, lock phải bao phủ read-modify-write hoặc dùng versioning; P1: Sửa test concurrent để bắt buộc tu_0...tu_7 đều tồn tại; P1: Sửa Linux release archive; P1/P2: Làm schema validation sâu và đồng bộ với toàn bộ runtime schema; P2: Thiết kế incremental index/batch save cho teach_word(); P2: Sửa README/Quickstart lỗi thời; P2: Cải thiện reproducible dependencies; P2: Làm create_empty() dùng persistence pipeline an toàn; P2: Xử lý trường hợp logging thất bại hoàn toàn."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Concurrency Safety & Lost-Update Prevention Across Processes (Priority: P1)

As a user running GUI and CLI tools simultaneously or operating in multi-instance environments, I want updates from all processes to be reliably persisted without silent lost-update data overwrites, so that words taught in one tool are never accidentally erased by another tool saving an older snapshot.

**Why this priority**: File-level atomic replacement protects against partial file corruption, but does not prevent logical data loss when two processes read snapshot X and independently save X+a and X+b. Preventing data loss is the highest operational correctness requirement.

**Independent Test**: Launch multiple simulated processes or threads concurrently adding distinct words (`tu_0` through `tu_7`) to a shared bank; verify that all added words are present in the final bank file with zero lost updates.

**Acceptance Scenarios**:
1. **Given** two separate processes that opened the same handwriting bank at state X, **When** Process 1 adds word "aaa" and saves, and Process 2 adds word "bbb" and saves, **Then** both "aaa" and "bbb" exist in the final bank file.
2. **Given** multiple concurrent processes saving new words, **When** high write contention occurs, **Then** save operations complete without raising unhandled lock collisions, and no updates are dropped.

---

### User Story 2 - Deep Structural and Runtime Schema Validation (Priority: P1)

As a user or developer loading a handwriting bank, I want the schema validation engine to deeply inspect stroke geometry (valid coordinate pairs, finite floats, non-empty strokes) and verify all runtime-required metadata fields, so that invalid or malformed data is rejected at the boundary before causing cryptic runtime exceptions during document synthesis.

**Why this priority**: Current validation only verifies top-level types. If stroke lists contain odd numbers of coordinates, non-finite values (NaN/inf), or if runtime metadata keys (`wgaps`, `dgaps`, `line`, `v`, `x0`, `width`, `ratio`) are absent, the application crashes later with unhandled `KeyError` or `TypeError` during rendering.

**Independent Test**: Attempt to load bank files with malformed stroke lists (e.g. odd coordinate lengths, NaN coordinates, empty strokes) or missing runtime attributes (`line`, `width`, `wgaps`); verify that `BankValidationError` is raised immediately with actionable path-level error messages.

**Acceptance Scenarios**:
1. **Given** a bank file where stroke data contains non-finite numbers, odd coordinate counts, or invalid structures, **When** loaded, **Then** validation fails with a descriptive diagnostic message identifying the invalid glyph and stroke index.
2. **Given** a bank file missing runtime configuration fields (`wgaps`, `dgaps`, `line`, `v`, `x0`, `width`, `ratio`), **When** loaded, **Then** validation flags the missing fields and applies standard defaults or migration where backward compatibility permits.

---

### User Story 3 - Reliable Packaging and Release Workflow Delivery (Priority: P1)

As a project maintainer releasing new versions, I want the automated GitHub Actions release workflow to package executables alongside license and documentation files accurately from their repository locations, so that release archives package cleanly without runtime path errors.

**Why this priority**: The current Linux release packaging step changes working directory to `dist/` before referencing root-level files (`README.md`, `LICENSE`), causing release job failures during tag builds.

**Independent Test**: Run release archive generation commands; verify that archive creation succeeds and packages the executable, `README.md`, and `LICENSE` cleanly.

**Acceptance Scenarios**:
1. **Given** a tagged release workflow run on Linux and Windows, **When** the packaging step executes, **Then** the distributable archive is created with the application binary, `README.md`, and `LICENSE` without missing-file errors.

---

### User Story 4 - Consistent Atomic Persistence for New Bank Creation (Priority: P2)

As a user creating a new handwriting bank, I want `create_empty()` to use the exact same atomic write, file locking, and storage synchronization pipeline as regular saves, so that newly created files are safeguarded against interrupted writes and file collisions.

**Why this priority**: Architectural consistency prevents fragile divergent write paths. `Bank.save()` has robust locking and fsync, but `create_empty()` currently writes directly, bypassing atomic replacement protections.

**Independent Test**: Invoke `create_empty()` under simulated concurrent creation or interrupted I/O; verify that creation utilizes a temporary file and atomic replacement under file lock protection.

**Acceptance Scenarios**:
1. **Given** a request to create a new starter bank, **When** `Bank.create_empty()` is called, **Then** the file is created via unique temporary workspace, flushed to disk via `fsync`, and atomically replaced under a file lock.

---

### User Story 5 - Scalable Incremental Processing for Word Teaching (Priority: P2)

As a user training handwriting profiles with thousands of samples, I want teaching operations in `teach_word()` to avoid redundant full-bank rebuilding and repetitive full-file compression on every single word addition, so that profile teaching remains responsive as the bank grows to tens of thousands of samples.

**Why this priority**: Calling `rebuild()` and full gzip persistence for every single sample in `teach_word()` scales quadratically with dataset size, creating a severe performance bottleneck during bulk learning sessions.

**Independent Test**: Teach 50 words consecutively into a bank containing 5,000 existing samples; measure total execution time and verify responsive interactive performance.

**Acceptance Scenarios**:
1. **Given** a teaching session with multiple word samples, **When** words are submitted, **Then** the application performs incremental index maintenance rather than full collection re-indexing for each sample.
2. **Given** consecutive word teaching actions, **When** saving to disk, **Then** persistence operations can be batched or deferred until the user completes the session.

---

### User Story 6 - Resilient Logging Fallback and Accurate Documentation (Priority: P2)

As an end user and developer, I want logging diagnostics to report `None` or an explicit inactive status when all file logging attempts fail, and I want user documentation to accurately state system prerequisites and dependencies, so that UI dialogues never report non-existent log paths and new users set up the project smoothly.

**Why this priority**: If both primary and fallback logging fail, `log_path()` currently returns a non-existent default path, confusing users. Furthermore, outdated documentation (`Python 3` vs `Python 3.10+`, obsolete `filelock` install, removed binary references) misleads contributors.

**Independent Test**: Simulate an environment where both app and user data directories are completely unwritable; verify `log_path()` accurately reports no active log file. Verify that README and Quickstart documentation match current codebase state.

**Acceptance Scenarios**:
1. **Given** both primary and user data log directories are unwritable, **When** logging initializes, **Then** error dialogs handle the inactive logger gracefully without asserting that logs were written to disk.
2. **Given** a new developer reading the documentation, **When** reviewing README and Quickstart, **Then** Python version (`3.10+`), zero runtime dependencies, and current test procedures are documented accurately.

---

### User Story 7 - Complete Git History Purge of Sensitive Biometric Blobs (Priority: P0 / Operational)

As a project owner preparing for public release or strict data privacy audits, I want historical commits in version control purged of previously committed personal handwriting data files (`chu_cua_ban.json.gz` and `tests/data/kho_mau_chup_lai.json.gz`), so that personal biometric data cannot be retrieved from git object history.

**Why this priority**: Untracking files in the working tree removes them from future commits, but existing git blobs remain permanently stored in `.git/objects` and historical commit trees until explicitly rewritten.

**Independent Test**: Run a history inspection tool (e.g. `git log --all --full-history -- "**/kho_mau_chup_lai.json.gz"`); verify zero commit history references to personal biometric files.

**Acceptance Scenarios**:
1. **Given** a repository with historical commits containing personal data, **When** the history purge procedure is executed, **Then** all historical tree objects referencing personal handwriting data are purged and replaced with clean history.

---

### Edge Cases

- What happens if two processes attempt to merge changes to the exact same word simultaneously with different strokes?
  The system must preserve both stroke variations under the word's sample list rather than overwriting.
- What happens if a stroke contains fewer than 2 coordinates (e.g. `[10.0]`) or an odd number of floating-point numbers?
  Deep schema validation must reject the bank with a clear validation error specifying the exact word and stroke index.
- What happens if disk storage becomes completely unwritable during both primary and user-data logging initialization?
  The logging system must fall back to standard error / console stream and report that persistent file logging is disabled.
- What happens during a git history rewrite if contributors have active divergent branches or unmerged work?
  History rewriting must be provided with clear operational safety guidelines, requiring explicit local backup and remote force-push coordination.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement a transactional reload-and-merge concurrency strategy with cross-process file locking during save/mutation operations, ensuring that external additions on disk are merged (sample list union) with local updates before atomic write to eliminate lost updates.
- **FR-002**: System MUST strengthen concurrent bank test assertions (`tests/test_bank.py::test_concurrent_save...`) to verify that all concurrently added sample tokens (`tu_0` through `tu_7`) exist in the final saved bank file.
- **FR-003**: System MUST provide deep schema validation in `bank_schema.py` ensuring every stroke `s` is a list of coordinate pairs with an even count of finite floating-point numbers, at least one point, and valid non-negative pen widths.
- **FR-004**: System MUST validate all runtime metadata fields used across document rendering (`wgaps`, `dgaps`, `line`, `v`, `x0`, `width`, `ratio`) during bank schema validation, supplying standard defaults for legacy banks missing non-critical metrics.
- **FR-005**: System MUST correct the Linux release packaging step in `.github/workflows/ci.yml` so that repository root documents (`README.md`, `LICENSE`) are correctly bundled into release archives.
- **FR-006**: System MUST update `Bank.create_empty()` to utilize the atomic persistence pipeline (`FileLock`, unique temporary file, `fsync`, `os.replace`) identically to `Bank.save()`.
- **FR-007**: System MUST optimize `teach_word()` in `AppController` and `Bank` by performing in-memory incremental index updates for modified words rather than full dictionary re-indexing, followed by durable atomic persistence.
- **FR-008**: System MUST update `logging_setup.py` so that `log_path()` returns `None` (or an explicit inactive indicator) when all file logging attempts fail, and GUI error dialogues handle this case without displaying a ghost log path.
- **FR-009**: System MUST synchronize user documentation across `README.md` and `quickstart.md` to reflect `Python 3.10+`, stdlib-only locking (removing external `filelock` references), and current standalone build instructions.
- **FR-010**: System MUST align development and build dependency specifications between `requirements-dev.txt` and `requirements-build.txt` to maintain reproducible environments.
- **FR-011**: System MUST provide a standalone, safe automation script (`scripts/purge_git_history.sh` / `.ps1`) using `git filter-repo` with pre-flight worktree and branch backup checks to purge historical personal handwriting data blobs from version control.
- **FR-012**: System MUST maintain 100% test passing rate across the automated test suite and preserve byte-exact golden-master regression outputs.

### Key Entities *(include if feature involves data)*

- **Handwriting Bank (`Bank`)**: The persistent profile container holding words, stroke geometry, and metadata. Now includes transactional merge support and deep structural invariants.
- **Stroke Geometry**: Sequence of 2D coordinates `(x, y)` representing continuous pen movements, strictly validated for pair parity, finiteness, and positive dimensions.
- **Bank Metadata (`BankMetadata`)**: Global rendering and typographic parameters (`wgaps`, `dgaps`, `line`, `v`, `x0`, `width`, `ratio`), validated against runtime requirements.
- **Concurrency Transaction**: An atomic unit of mutation encompassing latest disk state inspection, sample delta application, and durable persistence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of concurrent word additions across 8 concurrent simulated processes are preserved in the final bank file with zero dropped updates (`tu_0`..`tu_7` all verified present).
- **SC-002**: 100% of malformed stroke data (odd coordinate lengths, non-finite coordinates, empty strokes) and missing required runtime fields are rejected during schema validation before reaching document generation.
- **SC-003**: Release workflow archive step executes successfully on Linux and Windows CI runners without file-not-found failures.
- **SC-004**: Sequential teaching of 50 new words demonstrates at least a 3x speedup compared to full re-indexing and full file gzip persistence per word.
- **SC-005**: 100% of golden-master regression test assertions continue to pass without algorithm modification.
- **SC-006**: When file logging is completely unavailable, error dialogs and diagnostic queries accurately report that logging is disabled with 0 ghost file references.

## Assumptions

- Python 3.10+ remains the minimum supported environment.
- The core handwriting stroke layout and rendering mathematics in `writer.py` and `text_utils.py` remain untouched to preserve golden-master visual output.
- Concurrency protection is scoped to multiple processes operating on local or shared network file systems supporting standard file locking (`msvcrt` on Windows, `fcntl` on POSIX).
- Git history rewriting is an administrative operation that alters commit hashes; automation should be provided safely with safeguards against accidental data loss.
