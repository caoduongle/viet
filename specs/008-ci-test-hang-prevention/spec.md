# Feature Specification: CI Workflow Deadlock Prevention, Test Timeout Diagnostics, and Runner Concurrency Hardening

**Feature Branch**: `008-ci-test-hang-prevention`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User reports & CI logs:
1. Workflow hung/deadlocked during `Run pytest with virtual display (Linux)`:
   > Pytest reached ~42% (with 2 tests failing `F`) and then hung for 2 hours 16 minutes on Linux xvfb.
   > The next commit (`feat: add document IR...`) stalled in `Pending` state due to GitHub Actions runner concurrency limits.
2. Pytest collection crash when optional dependencies are missing:
   > `ERROR collecting tests/test_docx_omml_diagnostics.py`
   > `ModuleNotFoundError: No module named 'docx'`
   > `Interrupted: 1 error during collection (Process completed with exit code 2)`

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuous Integration Job-Level Timeout & Branch Concurrency Cancellation (Priority: P1)

As a software engineer and repository maintainer, I want CI workflow test jobs to enforce an explicit execution time limit (10 minutes) and automatically cancel superseded in-progress runs when new commits are pushed to the same branch, so that hung jobs do not consume runner capacity for hours and subsequent commits are never blocked indefinitely in a pending queue.

**Why this priority**: Without explicit job timeouts, GitHub Actions defaults to a 6-hour execution window (360 minutes). When a single matrix job hangs, it holds all 8 runner slots across operating systems and Python versions, causing subsequent commits to stall in "Pending" status and depleting the project's monthly CI minute budget.

**Independent Test**: Push consecutive commits to a branch and simulate a delayed job; verify that the previous in-progress run is automatically canceled (`cancelled`), and verify that any job running beyond 10 minutes is automatically terminated (`timed out`).

**Acceptance Scenarios**:
1. **Given** a running CI workflow job on any platform (Linux or Windows), **When** total execution exceeds 10 minutes, **Then** the runner terminates the job immediately with a timeout status.
2. **Given** an in-progress workflow run triggered by a branch push, **When** a newer commit is pushed to the same branch, **Then** GitHub Actions cancels the earlier workflow run, releasing runners immediately for the new commit.
3. **Given** a pull request branch, **When** new commits are submitted, **Then** previous pending and running checks are cancelled, allowing runners to execute tests for the latest commit without queuing delays.

---

### User Story 2 - Per-Test Watchdog Timeout & Traceback Diagnostics (Priority: P1)

As a test engineer and developer, I want individual automated tests to execute under an active watchdog timeout (30 seconds per test) with instant traceback emission upon expiration, so that any infinite loop, deadlocked thread, or unclosed modal dialog is terminated immediately and pinpointed directly to the exact line of code causing the hang.

**Why this priority**: In CI run logs, pytest ran to ~42% before silently hanging for over 2 hours. Without per-test timeouts, there is no signal indicating which test is hanging or where execution is stuck. A 30-second watchdog ensures rapid failure, prints call-stack diagnostics, and allows the remaining 58% of the test suite to execute and produce complete test reports.

**Independent Test**: Introduce an intentional 35-second block or infinite loop in a test; execute the test runner; verify that the test runner interrupts the test at exactly 30 seconds, marks the test as failed with a timeout traceback pointing to the blocked line, and continues executing subsequent tests.

**Acceptance Scenarios**:
1. **Given** a test case that enters an infinite loop, thread deadlock, or blocking synchronous call, **When** its execution time reaches 30 seconds, **Then** the test watchdog interrupts the execution and records a failure (`FAILED`).
2. **Given** an interrupted test due to timeout, **When** test failure output is captured, **Then** a full stack traceback is emitted identifying the exact source file, function, and line number where the process was frozen.
3. **Given** a test suite containing 370+ tests where one test times out at 30 seconds, **When** the watchdog triggers, **Then** the remaining tests continue to execute normally to completion.

---

### User Story 3 - Optional Dependency Collection Safety & CI Dependency Alignment (Priority: P1)

As a developer and CI engineer running tests across environments with varying installed packages, I want test modules that exercise optional document formats (e.g. `.docx`, `.md`) to safely guard their imports using standard test collection skip mechanisms (`pytest.importorskip`) rather than top-level unguarded imports, and I want the CI environment to install test-suite dependencies so that test collection never crashes with `ModuleNotFoundError` and tests produce 100% clean passes and skips.

**Why this priority**: In CI runs, `tests/test_docx_omml_diagnostics.py` imported `from docx import Document` at the module top level. Because `python-docx` was not in `requirements-dev.txt`, pytest aborted immediately during the collection phase with `ModuleNotFoundError: No module named 'docx'`, halting all testing before a single test could run. Furthermore, tests raising `OptionalDependencyError` instead of calling `pytest.skip` produce false-negative `FAILED` test results.

**Independent Test**: Uninstall `python-docx` from a test environment and run `pytest`; verify that pytest collection completes with 0 errors and all docx-dependent test modules are cleanly marked as `SKIPPED` rather than crashing collection. Then install all document extras and verify that all docx and markdown tests execute and pass (`PASSED`).

**Acceptance Scenarios**:
1. **Given** an environment without `python-docx` installed, **When** pytest collects tests across the entire test suite, **Then** collection succeeds with 0 collection errors and `test_docx_omml_diagnostics.py` is cleanly skipped with an informative reason.
2. **Given** an environment where optional document format dependencies are missing, **When** running any importer test, **Then** the test fixture or test body skips execution cleanly (`SKIPPED`) rather than failing with an unhandled `OptionalDependencyError` or `ImportError`.
3. **Given** the CI workflow environment running pull requests or pushes, **When** installing test dependencies, **Then** all packages necessary to run the comprehensive document importer test suites (including `python-docx`, `markdown-it-py`, `mdit-py-plugins`, and `pytest-timeout`) are installed and tested.

---

### User Story 4 - Real-Time Streaming Test Verbosity in CI Logs (Priority: P2)

As a developer monitoring CI test execution, I want the test runner to stream live, verbose test progress (`-vv -s`) in real-time rather than suppressing output with quiet flags (`-q`), so that the exact executing test name, stdout messages, and step progress are immediately visible in the continuous integration console.

**Why this priority**: Running pytest in quiet mode (`-q`) buffers output and prints progress only incrementally or at the end. When a test freezes, developers cannot see which test was running when output ceased. Verbose streaming output provides live observability.

**Independent Test**: Run the CI test command locally and in CI; verify that each individual test path and name is streamed live to the console alongside execution status markers (`PASSED`, `SKIPPED`, `FAILED`).

**Acceptance Scenarios**:
1. **Given** the CI test step running on Linux or Windows, **When** tests execute, **Then** each individual test case name and module path is written to stdout in real time prior to and immediately upon completion.
2. **Given** any test that emits diagnostic print statements or logging output, **When** running under CI, **Then** stdout and stderr are flushed live without silent suppression.

---

### User Story 5 - Layout Engine, Pagination, and File Lock Bounded Termination Safety (Priority: P2)

As a core layout engine developer, I want all document layout loops (paragraph wrapping, table pagination, math formula AST traversal) and cross-process file locks to have strictly bounded iteration limits and non-blocking safety escapes, so that degenerate inputs, edge-case dimensions, or concurrent file access can never trigger an infinite loop or thread deadlock.

**Why this priority**: Commit `20ef69c` and `8b4aae0` introduced complex multi-page document layout engines, table pagination, and inline math formatting. Layout algorithms that split rows or calculate page breaks across `cur_y > max_page_y` are susceptible to infinite `while` loops if row advancement fails to increment `cur_y` or if table cell splitting cannot fit within page boundaries.

**Independent Test**: Feed the document layout engine with degenerate boundary conditions (e.g. zero line height, cell taller than page capacity, empty table, negative margins); verify the layout completes within 5 seconds without freezing or hanging.

**Acceptance Scenarios**:
1. **Given** a document with tables spanning multiple pages, **When** layout engine computes pagination, **Then** each pagination step guarantees monotonic cursor progress or forces a page break, never repeating the same row coordinate infinitely.
2. **Given** cross-process `FileLock` acquisition, **When** a lock cannot be obtained within the timeout period, **Then** it cleanly raises `FileLockTimeoutError` and does not block indefinitely.
3. **Given** math AST parsing and stroke rendering, **When** parsing deeply nested or malformed mathematical expressions, **Then** parsing terminates in bounded steps proportional to input length.

---

### User Story 6 - Headless GUI Virtual Display Modal Dialog Interception (Priority: P3)

As a QA automation engineer, I want all GUI tests to guarantee safe headless execution under virtual displays (`xvfb-run`), where all modal dialogs (`messagebox`, `filedialog`, `simpledialog`) are comprehensively mocked, so that tests never block waiting for user input.

**Why this priority**: In CI, tests run under headless virtual displays. If any GUI test triggers an unmocked modal dialog (such as `askyesno`, `showwarning`, or `askstring`), the window manager halts waiting for a mouse click that will never arrive. Comprehensive mocking guarantees non-blocking execution.

**Independent Test**: Audit all GUI test cases and run them under `xvfb-run` without interactive inputs; verify all dialogs are intercepted and 0 tests hang.

**Acceptance Scenarios**:
1. **Given** any GUI test executing under headless virtual display, **When** application code invokes any standard Tkinter dialog or prompt, **Then** the dialog call is intercepted by test fixtures without opening a blocking native modal event loop.

---

## Edge Cases

- **What happens if a test legitimately requires long processing time (e.g. a 5,000-sample persistence benchmark)?**
  Specific long-running benchmark tests are explicitly marked with extended timeout thresholds (e.g. `@pytest.mark.timeout(120)`) to prevent premature termination while keeping the global 30-second watchdog active for all standard unit and integration tests.
- **What happens if `pytest-timeout` runs on Windows where POSIX signals (`SIGALRM`) are not supported?**
  `pytest-timeout` automatically selects thread-based timeout interruption on Windows and signal-based interruption on Linux, guaranteeing consistent cross-platform timeout enforcement.
- **What happens if multiple commits are pushed in rapid succession to `main`?**
  The GitHub Actions concurrency group with `cancel-in-progress: true` automatically cancels all superseded intermediate runs, dedicating runners exclusively to the latest commit and preventing pending queue buildup.
- **What happens if `python-docx` or `markdown-it-py` is missing in a developer's local virtualenv?**
  `pytest.importorskip("docx")` gracefully skips the entire test module during collection, reporting a skip message rather than crashing the test session.
- **What happens if a table row height exceeds the entire maximum printable page height?**
  The layout engine must enforce a fallback rule (e.g. force page break and render with clamped dimensions or split block) to ensure vertical progress and avoid endless page-break looping.
- **What happens if `xvfb` fails to initialize a virtual display on Linux?**
  `xvfb-run` exits with a non-zero code immediately, failing the step fast rather than hanging the test runner.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CI workflow (`.github/workflows/ci.yml`) MUST configure a maximum execution timeout (`timeout-minutes: 10`) at the test job level.
- **FR-002**: The CI workflow concurrency configuration MUST cancel in-progress runs when a new push occurs on the same branch or pull request (`cancel-in-progress: true`), preventing runner starvation.
- **FR-003**: The development environment configuration (`requirements-dev.txt`) MUST include `pytest-timeout` to provide watchdog timeout capabilities across all development and CI environments.
- **FR-004**: Pytest execution MUST enforce a default per-test watchdog timeout of 30 seconds (via CLI `--timeout=30` or `pytest.ini`), interrupting any test that runs longer with a complete diagnostic traceback.
- **FR-005**: Pytest test steps in CI MUST execute with verbose streaming output (`-vv -s`) instead of quiet mode (`-q`), streaming real-time test progress and diagnostic logs to stdout.
- **FR-006**: Test modules covering optional dependencies (`tests/test_docx_omml_diagnostics.py`, `tests/test_importer_docx.py`, etc.) MUST use `pytest.importorskip` at the module level rather than top-level unguarded imports, ensuring collection never fails with `ModuleNotFoundError`.
- **FR-007**: Test fixtures and tests asserting on optional features MUST catch or convert `OptionalDependencyError` into `pytest.skip(...)` so missing optional packages skip cleanly instead of recording false failures.
- **FR-008**: The CI workflow MUST install full document parsing dependencies (`python-docx`, `markdown-it-py`, `mdit-py-plugins`) during the dependency installation step to ensure comprehensive coverage across supported formats.
- **FR-009**: Document and table layout pagination algorithms (`chuviettay/layout/engine.py` and `chuviettay/layout/table_layout.py`) MUST maintain a forward-progress invariant ensuring cursor position strictly advances or page breaks terminate after bounded iterations.
- **FR-010**: GUI test fixtures (`tests/test_gui.py`, `tests/test_gui_document.py`) MUST mock all modal dialog functions (`messagebox`, `filedialog`, `simpledialog`, `dialogs`) to prevent unhandled blocking modal dialogs during automated execution.

---

### Key Entities

- **CI Test Job**: The automated execution unit in GitHub Actions running across operating systems (Ubuntu, Windows) and Python versions (3.10–3.13), bounded by a strict 10-minute maximum runtime.
- **Test Watchdog**: The runtime monitor (`pytest-timeout`) that tracks per-test execution duration, triggering thread dump tracebacks and test termination when any test exceeds 30 seconds.
- **Concurrency Group**: The GitHub Actions queuing controller configured to auto-cancel obsolete workflow runs on branch updates, eliminating runner backlog.
- **Optional Dependency Guard**: Test-level mechanism (`pytest.importorskip`) providing deterministic skipping when optional libraries are absent during collection.
- **Layout Pagination State**: The state tracker managing vertical coordinates (`cur_y`), page buffers, and row splits, with guarantees against infinite loop recurrence.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of CI workflow test jobs terminate in under 10 minutes under all operating conditions, even when an infinite loop or deadlock is present.
- **SC-002**: Obsolete in-progress CI runs on the same branch are cancelled within 15 seconds of a new commit push, keeping queued pending time for new commits under 30 seconds.
- **SC-003**: Any hanging test case or deadlocked operation is interrupted within 30 seconds, generating an actionable traceback pinpointing the offending source file and line number.
- **SC-004**: 100% of test modules collect with zero `ModuleNotFoundError` or collection errors, regardless of whether optional packages (`python-docx`, `markdown-it-py`) are installed.
- **SC-005**: 100% of collected tests output their individual execution status and name in real-time logs during CI runs.
- **SC-006**: Document layout engine and table pagination processing complete in $< 5.0\text{s}$ for documents up to 50 pages, with zero infinite loop occurrences.
- **SC-007**: Automated test suite achieves a clean run (0 hangs, 0 unhandled modal dialog blocks, 0 collection crashes) across all 8 matrix configurations in CI.

---

## Assumptions

- Standard GitHub-hosted runners (`ubuntu-latest`, `windows-latest`) have network connectivity to install `pytest-timeout` and optional document packages.
- Normal unit tests in the repository execute in under 1 second; a 30-second watchdog provides a $30\times$ margin of safety before triggering.
- Standard development workflow pushes commits to branch refs monitored by GitHub Actions.
- When optional dependencies are installed, all format importer tests run to completion; when absent, they skip cleanly without causing build failure.
