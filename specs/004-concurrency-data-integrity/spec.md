# Feature Specification: Concurrency Data Integrity, Tombstone Versioning, and Robust Persistence

**Feature Branch**: `004-concurrency-data-integrity`

**Created**: 2026-09-29

**Status**: Implemented

**Input**: User audit and enhancement request:
1. P1: `Bank.save()` MUST NOT overwrite corrupt disk file if merge/read validation fails (`raise BankError`, abort save, no `os.replace`).
2. P1: Tombstone generation/timestamp versioning for words and tombstones to prevent stale snapshots from resurrecting deleted words, while allowing deliberate post-deletion additions to restore words.
3. P1/P2: True large-bank persistence model evaluation and benchmark with 5,000–10,000 samples.
4. P2: Fix `_tombstones` dictionary aliasing in `merge_bank_dicts()` (`self._tombstones.clear(); self._tombstones.update(...)`).
5. P2: `Bank.drop()` must prune in-memory indexes (`tl`, `_raw_marks`, `marks`) directly.
6. P2: Incremental tone filtering optimization (avoid repeated `O(M log M)` sorting per addition).
7. P2: Concurrency testing via true multi-process execution (`multiprocessing` / subprocess).
8. P2: Git history purge execution and documentation update (`git push --force --mirror origin`).
9. P2: Synchronize metadata, CHANGELOG, quickstart (262 tests), CI ruff check, and release docs.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Safe Persistence Abort on Corrupted or Conflicting Disk State (Priority: P1)

As a user saving changes to a handwriting profile, I want `Bank.save()` to immediately abort and preserve the existing file on disk if reading or validating the disk file fails during a merge, so that a read error or corrupted file never silently causes data loss or unintended file destruction.

**Why this priority**: Currently in `Bank.save()`, if `load_and_validate()` fails on an existing disk file, the code logs a warning and proceeds to execute `os.replace(tmp, self.path)`. If the disk file was partially written, created by an incompatible future schema, or damaged by an external tool, the application blindly overwrites it with whatever state is in memory, turning a recoverable read error into permanent data loss.

**Independent Test**: Simulate a corrupted JSON/gzip file on disk; call `Bank.save()`; verify that `BankError` (or a subclass) is raised, the temporary file is removed, and the corrupted file on disk remains completely untouched.

**Acceptance Scenarios**:
1. **Given** a bank file on disk that contains invalid gzip data, invalid JSON, or an unsupported future schema, **When** `Bank.save()` attempts to merge changes, **Then** `Bank.save()` aborts immediately, deletes the temporary file, raises `BankError` without calling `os.replace`, and leaves the file on disk intact.
2. **Given** an administrative recovery operation where the user explicitly demands overwriting the disk state, **When** `Bank.save(force_overwrite=True)` is called, **Then** the system logs an audit warning and writes the in-memory state over the disk file.

---

### User Story 2 - Generation-Aware Deletion Tombstones and Stale Snapshot Resurrection Prevention (Priority: P1)

As a user running concurrent application sessions or managing words via GUI and CLI, I want deletion tombstones to record generation or timestamp metadata, so that sample additions originating from a stale snapshot taken *before* the deletion are suppressed, while deliberate additions taught *after* the deletion are honored.

**Why this priority**: Currently, `add_sample()` unconditionally clears the tombstone for a word and records the word in `_readded_words`. If Process A and Process B both load word "foo", Process A deletes "foo" and saves, and Process B later adds a sample to "foo" from its older snapshot and saves, Process B's merge logic resurrects "foo" along with all older samples from B's snapshot.

**Independent Test**: Load bank containing "foo" in Process A and Process B at $T_0$; delete "foo" in Process A at $T_1$ and save; add a sample to "foo" in Process B based on its $T_0$ snapshot and save; verify that "foo" remains deleted. Then in a fresh session at $T_2 > T_1$, explicitly teach "foo" and save; verify "foo" is restored with only the new sample.

**Acceptance Scenarios**:
1. **Given** Process A and Process B open the same bank at Generation $G_0$ / Timestamp $T_0$, **When** Process A deletes word "foo" at $T_1 > T_0$ and saves, and Process B subsequently adds a sample to "foo" originating from its $T_0$ snapshot, **Then** the merge algorithm detects that B's sample predates deletion $T_1$, drops the stale sample, and keeps "foo" deleted.
2. **Given** word "foo" was deleted at $T_1$, **When** a user deliberately teaches "foo" in an active session at $T_2 > T_1$, **Then** the new addition has operation timestamp $T_2 > T_1$, successfully revoking the tombstone and restoring "foo" with the new sample.
3. **Given** a bank file containing generation-aware tombstones, **When** loaded by existing or new bank instances, **Then** the schema preserves backward compatibility and accepts both legacy float timestamps and structured tombstone records.

---

### User Story 3 - Multi-Process Concurrency Verification via True OS Subprocesses (Priority: P1)

As a quality engineer, I want concurrency tests to execute across actual operating system processes rather than within thread pools, so that cross-process file locking (`FileLock`), inter-process race conditions, and tombstone reconciliation are proven under true multi-process conditions.

**Why this priority**: Python's `ThreadPoolExecutor` shares the Global Interpreter Lock (GIL), process memory, open file handles, and module namespaces. Testing concurrency exclusively via threads does not faithfully represent the operational environment where GUI (`hw_gui.py`) and CLI (`hw_note.py`) run as independent OS processes with distinct memory spaces and OS-level file descriptor locks.

**Independent Test**: Launch multiple worker processes using Python's `multiprocessing` or `subprocess` targeting the same `.json.gz` bank file; perform concurrent deletions and additions; verify that no file corruption occurs, locks prevent interleaving, and final bank contents match expected conflict resolution.

**Acceptance Scenarios**:
1. **Given** multiple distinct OS processes writing to the same handwriting bank simultaneously, **When** executing concurrent reads, writes, and deletions, **Then** all processes complete without unhandled lock contention or file corruption.
2. **Given** Process 1 deleting word "foo" while Process 2 concurrently adds samples to "bar" in a separate OS process, **When** both processes complete, **Then** "foo" is deleted and "bar" contains all newly added samples.

---

### User Story 4 - Large-Bank Persistence Benchmarks and Asymptotic Evaluation (Priority: P2)

As a system architect and performance tester, I want empirical benchmark tests that evaluate profile persistence against realistic large handwriting banks ($\ge 5,000$ samples), so that asymptotic $O(N)$ gzip and JSON limits are measured, documented, and verified to meet interactive latency requirements.

**Why this priority**: The existing benchmark tests only 100 words with 20 additions. While the fast-path mtime check bypasses full disk re-reads and index rebuilds, saving still requires serializing and compressing the entire in-memory dictionary. We must verify that interactive teaching remains responsive even on large profiles and establish empirical baseline metrics.

**Independent Test**: Generate a synthetic bank with 5,000+ samples; measure 20 consecutive `add_sample_incremental()` + `save()` operations; record per-word latency, total elapsed time, and memory profile.

**Acceptance Scenarios**:
1. **Given** a handwriting bank populated with $\ge 5,000$ samples, **When** teaching 20 consecutive words interactively, **Then** fast-path cache validation bypasses disk re-reading and full re-indexing, completing with sub-second per-word latency.
2. **Given** persistence profiling on large banks, **When** measured across varying sample counts (1,000, 5,000, 10,000), **Then** compression and I/O scaling behavior is documented in benchmark reports.

---

### User Story 5 - In-Memory Invariant Consistency on Drop and Tombstone Dict Aliasing (Priority: P2)

As a developer calling the `Bank` model API, I want `Bank.drop()` to immediately prune in-memory lookup indexes (`tl`, `_raw_marks`, `marks`) and maintain identical dictionary identity for `_tombstones`, so that querying `bank.can()` or saving the bank never encounters stale or decoupled state.

**Why this priority**: Currently, `Bank.drop()` only pops `self.words` and sets a tombstone flag, but leaves entries in substitution index `tl` and tone marks in `_raw_marks` and `marks`. If code calls `bank.drop("foo")` followed by `bank.can("foo")`, `can()` may return True because `tl` was not pruned. Additionally, `merge_bank_dicts()` reassigns `base["tombstones"] = merged_tombstones`, which breaks the reference identity between `self._tombstones` and `self.d["tombstones"]`.

**Independent Test**: Call `bank.drop("foo")` on a bank containing "foo" with tone marks; verify `bank.can("foo")` immediately returns False, `tl` has no references to "foo", and `_raw_marks` no longer contains the harvested tone marks of "foo". Verify `bank._tombstones is bank.d["tombstones"]` remains True after merge.

**Acceptance Scenarios**:
1. **Given** a bank with word "bà", **When** `bank.drop("bà")` is executed, **Then** "bà" is removed from `self.words`, purged from substitution index `self.tl`, its harvested mark is removed from `self._raw_marks`, `self.marks` is refreshed, and `bank.can("bà")` returns False.
2. **Given** `merge_bank_dicts(base, disk)` executes, **When** tombstones are merged, **Then** `base["tombstones"]` updates in-place or re-binds cleanly so `self._tombstones` and `self.d["tombstones"]` remain the exact same dictionary object.

---

### User Story 6 - Efficient Incremental Tone Mark Percentile Maintenance (Priority: P2)

As a developer maintaining handwriting indexes, I want incremental tone mark additions to update percentile boundaries efficiently without repeatedly sorting the entire mark array four times per added mark, so that incremental indexing remains efficient as tone collections scale.

**Why this priority**: In `_refresh_tone_marks()`, every time a single tone mark is harvested and added, `sorted()` is called four times (on `dx` and `dy` arrays) to determine 10th and 90th percentile bounds. When a bank accumulates hundreds or thousands of tone marks, sorting $O(M \log M)$ four times per mark is computationally redundant.

**Independent Test**: Add 100 consecutive tone marks incrementally; verify that percentile bounds are computed efficiently and produce candidate sets identical to `rebuild()`.

**Acceptance Scenarios**:
1. **Given** an existing collection of tone marks, **When** a new mark is added incrementally, **Then** percentile bounds are maintained without full four-pass sorting of the entire array.
2. **Given** identical underlying marks, **When** comparing `marks[T]` against `rebuild()`, **Then** the filtered tone marks match 100%.

---

### User Story 7 - Complete Git History Purge Execution and Remote Mirror Guidance (Priority: P2 / Operational)

As a repository maintainer, I want the git history purge scripts to be safely executed to remove all sensitive personal handwriting blobs from historical commits, and I want the documentation to recommend `git push --force --mirror origin` to prevent dangling remote refs.

**Why this priority**: While the working tree is clean and the purge scripts have been updated to create external bundle backups, the actual git history of the repository still contains blobs `chu_cua_ban.json.gz` and `kho_mau_chup_lai.json.gz` in commits `5a25e92` and `621c013`. Furthermore, standard git practice for sensitive data purge requires `--force --mirror` when updating remote repositories to ensure all historical tags and refs are sanitized.

**Independent Test**: Run `scripts/purge_git_history.ps1 -CheckOnly`; execute the purge in an isolated clone; verify `git log --all` contains zero references to sensitive blobs; verify script prints `git push --force --mirror origin`.

**Acceptance Scenarios**:
1. **Given** purge scripts `scripts/purge_git_history.ps1` and `.sh`, **When** inspected, **Then** the post-purge remote push instructions recommend `git push --force --mirror origin` and advise inspecting history before pushing.
2. **Given** execution of the purge workflow, **When** git log is queried across all commits, **Then** zero occurrences of personal data files remain in the commit history.

---

### User Story 8 - Documentation, Metadata, and CI Linter Alignment (Priority: P3)

As a contributor reviewing project metadata and documentation, I want `CHANGELOG.md`, `quickstart.md`, `spec.md`, and CI workflows to accurately reflect recent concurrency features, updated test counts (262+ passed), and automated Ruff linting, so that project health and documentation remain perfectly synchronized.

**Why this priority**: Minor documentation discrepancies remain: `CHANGELOG.md` describes an obsolete single-process overwrite warning, `quickstart.md` mentions "215+ passed" while CI runs 262 passed tests, `spec.md` for feature 003 was left with "Status: Draft", and `ruff check .` is not yet an automated step in `.github/workflows/ci.yml`.

**Independent Test**: Verify that `.github/workflows/ci.yml` includes a linting step (`ruff check .`), `CHANGELOG.md` accurately describes cross-process concurrency, and `quickstart.md` documents 262+ passed tests.

**Acceptance Scenarios**:
1. **Given** `.github/workflows/ci.yml`, **When** CI executes, **Then** a dedicated lint job runs `ruff check .` across the codebase.
2. **Given** `CHANGELOG.md` and `README.md`, **When** reviewed, **Then** concurrency safety is accurately documented and obsolete single-process overwrite warnings are removed.
3. **Given** `quickstart.md` and feature specs, **When** checked, **Then** test counts match 262+ passed and spec statuses are properly updated.

---

## Edge Cases

- **What happens if a disk file is modified by another process during `Bank.save()` while the lock is held?**
  `FileLock` prevents concurrent writes. If another process modified the file between our load and lock acquisition, `mtime_ns` and `size` will differ from `_last_synced_*`, forcing the slow-path read, validation, and merge.
- **What happens if the disk file is completely unreadable or zero-byte during save?**
  `load_and_validate()` raises `BankCorruptedError`. Under FR-001, `save()` aborts immediately, cleans up the temporary file, raises `BankCorruptedError`, and refuses to overwrite the corrupted file.
- **What happens if a word is deleted in Process A at timestamp $T_1$, and Process B attempts to add a sample to the same word with timestamp $T_0 < T_1$?**
  The sample is rejected as stale because its generation/timestamp is older than the tombstone deletion timestamp.
- **What happens if Process B attempts to add a sample with timestamp $T_2 > T_1$?**
  The addition is accepted as an intentional new re-teaching; the tombstone is revoked and the word is restored with the new sample.
- **What happens if `Bank.drop()` is called on a non-existent word?**
  `Bank.drop()` returns 0 and does not pollute `_raw_marks` or indexes.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: In `Bank.save()`, if reading, parsing, or validating the existing on-disk file fails during a merge attempt, the system MUST immediately abort saving, delete the temporary file, and raise `BankError` (or a subclass), refusing to call `os.replace` or overwrite the disk file, unless explicitly authorized via `force_overwrite=True`.
- **FR-002**: In `Bank.save()` and `merge_bank_dicts()`, the system MUST associate word mutations and deletion tombstones with timestamp or generation metadata, ensuring that sample additions originating from a snapshot older than the deletion timestamp are rejected during cross-process merging.
- **FR-003**: In `Bank.add_sample()` and `Bank.add_sample_incremental()`, the system MUST only revoke a word's deletion tombstone when the sample addition is explicitly created in the current session with an operational timestamp newer than the tombstone deletion timestamp.
- **FR-004**: In `Bank.drop()`, the system MUST immediately prune in-memory lookup indexes (`tl`, `_raw_marks`, `marks`) in addition to updating `self.words` and tombstones, ensuring that subsequent calls to `bank.can()` or Writer queries reflect the deletion without requiring `rebuild()`.
- **FR-005**: In `merge_bank_dicts()`, the system MUST update `base["tombstones"]` in-place (`clear()` + `update()`) or re-bind `self._tombstones = self.d["tombstones"]` so that dictionary reference identity is preserved across merges.
- **FR-006**: In `_refresh_tone_marks()`, the system MUST optimize percentile calculation to avoid four full-array sorts on every incremental sample addition.
- **FR-007**: The test suite MUST provide multi-process concurrency integration tests using `multiprocessing` or `subprocess` to validate file locking, concurrent additions, and tombstone resolution between independent OS processes.
- **FR-008**: The test suite MUST provide a large-bank benchmark test simulating $\ge 5,000$ samples to measure write latency and document the $O(N)$ full-file compression scaling characteristics.
- **FR-009**: The git history purge automation scripts (`scripts/purge_git_history.ps1` and `.sh`) MUST recommend `git push --force --mirror origin` and provide clear operational instructions for post-purge remote synchronization.
- **FR-010**: Continuous integration (`.github/workflows/ci.yml`) MUST execute `ruff check .` as an automated quality gate.
- **FR-011**: Project documentation (`CHANGELOG.md`, `README.md`, `specs/003.../quickstart.md`, `specs/003.../spec.md`) MUST be updated to remove obsolete concurrency warnings, reflect current test counts (262+ passed), and accurately state feature statuses.

---

### Key Entities

- **Deletion Tombstone Record**: A persistent structure recording `{"deleted_at": float, "generation": int}` associated with a deleted word identifier.
- **Sample Mutation Metadata**: Timestamp or generation information tracking when a sample or word was created or updated.
- **Handwriting Bank (`Bank`)**: The container encapsulating handwriting samples, metrics, lookup caches, and persistent sync state.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% rate of corrupted or incompatible disk file overwrites when merge validation fails during `Bank.save()`.
- **SC-002**: 0% rate of deleted word resurrection when merging stale snapshots from concurrent processes.
- **SC-003**: 100% test pass rate across multi-process concurrency tests executing in separate OS processes.
- **SC-004**: Sub-second interactive save times during incremental word teaching on profiles with $\ge 5,000$ samples.
- **SC-005**: 0 residual entries in `tl` or `marks` immediately following a call to `Bank.drop(word)`.
- **SC-006**: 100% pass rate on automated CI workflow jobs, including automated `ruff check .` linting and 8 test matrix jobs.
- **SC-007**: 0 occurrences of sensitive personal data blobs in repository git history following purge execution.

---

## Assumptions

- Python 3.10 remains the minimum supported version across all platforms.
- `FileLock` timeouts (10.0s) remain sufficient for local multi-process coordination.
- Timestamps recorded via `time.time()` provide sufficient resolution for distinguishing session deletion from subsequent deliberate re-teaching.
- Large bank compression costs scale linearly with database size ($O(N)$), which is acceptable for interactive desktop sessions when fast-path validation avoids redundant disk re-reads.
