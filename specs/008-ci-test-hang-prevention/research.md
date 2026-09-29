# Research & Technical Decisions: CI Deadlock Prevention & Timeout Diagnostics

**Feature**: `008-ci-test-hang-prevention`
**Date**: 2026-09-30

---

## 1. CI Workflow Job Timeout and Concurrency Preemption

### Decision
1. Add `timeout-minutes: 10` to the `jobs.test` definition in `.github/workflows/ci.yml`.
2. Update the concurrency setting in `.github/workflows/ci.yml` from:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: ${{ github.event_name == 'pull_request' }}
   ```
   to:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

### Rationale
* **Job Timeout**: GitHub Actions defaults to an execution limit of 360 minutes (6 hours). When a matrix of 8 jobs runs without `timeout-minutes`, a single hung process consumes runners for 6 hours, depleting the repository's monthly CI minute allocation. A 10-minute timeout is more than $10\times$ the typical test run time (~45 seconds) and guarantees automatic termination if any process hangs.
* **Concurrency Preemption**: Previously, `cancel-in-progress` was active only for pull requests. When commits were pushed to `main`, earlier runs continued running to completion. With 8 matrix jobs occupying the GitHub Actions account concurrency limit, commit #8 remained queued in `Pending` behind commit #7. Setting `cancel-in-progress: true` immediately terminates older workflow runs when a new commit is pushed to the same branch or PR ref.

### Alternatives Considered
* **Step-level timeout only (`timeout-minutes` on pytest step)**: Rejected because it does not protect against hangs during environment setup, package installation, or PyInstaller builds. Job-level timeout protects the entire lifecycle.
* **Manual workflow cancellation**: Rejected as the primary mechanism because it requires constant human monitoring and fails when pushes occur unattended or overnight.

---

## 2. Per-Test Watchdog Timeout via `pytest-timeout`

### Decision
1. Add `pytest-timeout>=2.3.1` to `requirements-dev.txt`.
2. Configure pytest execution to enforce `--timeout=30` (30 seconds per individual test) in CI test steps:
   * Linux: `xvfb-run -a python -m pytest -vv -s --timeout=30`
   * Windows: `python -m pytest -vv -s --timeout=30`
3. Support test-level overrides via `@pytest.mark.timeout(N)` for known long-running benchmarks (e.g. 50-word large-bank persistence benchmark).

### Rationale
* Pytest does not provide a native per-test execution timeout. When a test deadlocks (e.g. infinite `while` loop, thread contention, or unhandled modal dialog), the entire test process freezes.
* `pytest-timeout` attaches an asynchronous timer to each test:
  * On POSIX systems (Linux/macOS), it can use `SIGALRM` or thread monitoring.
  * On Windows, it uses background watchdog threads to interrupt the blocked test.
  * When a timeout triggers, `pytest-timeout` dumps the full stack frame and traceback of all active threads directly into the test failure output, pinpointing the exact line of code that caused the hang.
  * After logging the failure, the runner proceeds to execute the rest of the test suite.

### Alternatives Considered
* **Custom signal handler in `tests/conftest.py`**: Rejected because POSIX signals (`signal.alarm`) are unsupported on Windows, creating platform inconsistency and fragile custom code.
* **Global process timeout (e.g. `timeout 30s pytest`)**: Rejected because it kills the entire test runner without printing python tracebacks, failing to identify which specific test caused the issue.

---

## 3. Test Collection Guarding with `pytest.importorskip`

### Decision
1. Guard all test files requiring optional document packages with `pytest.importorskip`:
   * In `tests/test_docx_omml_diagnostics.py`: replace top-level `from docx import Document` with `pytest.importorskip("docx")` before any docx imports.
   * In `tests/test_importer_docx.py`: add module-level `pytest.importorskip("docx")`.
   * In `tests/test_importer_markdown.py`: add module-level `pytest.importorskip("markdown_it")` and `pytest.importorskip("mdit_py_plugins")`.
   * In tests that conditionally test docx (such as `tests/test_table_merged_cells.py::test_docx_import_table_with_merged_cells`, `tests/test_gui_document.py::test_gui_open_docx_document`, `tests/test_cli_format.py::test_cli_write_docx_file_uses_document_ir`): add `pytest.importorskip("docx")` at the beginning of the test function.
2. In fixtures using `require_dependency()`, wrap in `pytest.skip` if called within test contexts so missing libraries produce clean `SKIPPED` results rather than unhandled `OptionalDependencyError` failures (`FAILED`).

### Rationale
* When pytest collects tests, it imports every `test_*.py` file. If a file contains a top-level import for a module that is not installed (e.g. `from docx import Document`), Python raises `ModuleNotFoundError` during the collection phase before any test can execute or any fixture can run. This results in pytest exiting with error code 2.
* `pytest.importorskip(modname)` imports the module; if missing, it immediately raises a special skip exception with `allow_module_level=True`, telling pytest to skip the entire module cleanly.

### Alternatives Considered
* **`try: import docx; except ImportError: docx = None`**: Rejected because every test function would need manual `if docx is None: pytest.skip()` checks, adding repetitive boilerplate.
* **Making `python-docx` a mandatory runtime dependency**: Strictly forbidden by the project constitution. The core application runtime must have 0 non-standard library dependencies for end users.

---

## 4. CI Workflow Dependency Matrix Alignment

### Decision
In `.github/workflows/ci.yml`, update the test dependency installation step to install both development tools and optional document format dependencies:
```yaml
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
          pip install .[docs]
```

### Rationale
* The repository's v2 architecture includes document importers for Markdown and DOCX.
* In local environments, contributors may test only core functionality without `[docs]`, and tests will skip cleanly due to `pytest.importorskip`.
* In CI, tests should validate all features across all matrix configurations (Ubuntu/Windows × Python 3.10–3.13) to ensure full regression coverage. Installing `.[docs]` ensures full importer tests run and pass on CI.

### Alternatives Considered
* **Adding `python-docx` and `markdown-it-py` to `requirements-dev.txt` directly**: Also viable, but using `pip install -r requirements-dev.txt` followed by `pip install .[docs]` (or adding them to `requirements-dev.txt`) keeps dependencies synchronized with `pyproject.toml` extra definitions. To ensure consistency for both `pip install -r requirements-dev.txt` and CI, we will include `pytest-timeout>=2.3.1` in `requirements-dev.txt` and install `.[docs]` in CI.

---

## 5. Real-Time Streaming Test Verbosity (`-vv -s`)

### Decision
Update pytest invocations in `.github/workflows/ci.yml`:
* Linux: `xvfb-run -a python -m pytest -vv -s --timeout=30`
* Windows: `python -m pytest -vv -s --timeout=30`

### Rationale
* Pytest `-q` suppresses test execution names, printing only single characters (`.`, `F`, `s`) and buffering stdout.
* Under `-vv -s`:
  * Every test module and test case name is printed to stdout as soon as execution begins.
  * Standard output and error streams are unbuffered, allowing developers to see live logs in GitHub Actions as tests run.
  * If a test is slow or hung, the CI live console shows the exact name of the active test immediately.

### Alternatives Considered
* **`-v` without `-s`**: Still buffers stdout/stderr until the test completes. If a test freezes while emitting print statements, those statements are never displayed. `-s` disables capture so logs appear instantly.

---

## 6. Layout Pagination Loops & Tkinter Headless Dialog Safety

### Decision
1. In `chuviettay/layout/engine.py` and `chuviettay/layout/table_layout.py`: verify that all pagination `while` loops (e.g. `while curr_cols < max_cols`, `while i < n`) guarantee monotonic pointer advancement and have defensive max-iteration assertions.
2. In `tests/test_gui.py`: verify that the `Dialogs` fixture intercepts all possible modal dialog functions (`messagebox.showinfo`, `showwarning`, `showerror`, `askyesno`, `askokcancel`, `askquestion`, `askretrycancel`, `filedialog.askopenfilename`, `filedialog.asksaveasfilename`, `simpledialog.askstring`, `simpledialog.askinteger`).

### Rationale
* An infinite loop in layout pagination is an algorithm defect that can freeze any document rendering request. Defensive upper bounds ensure an explicit `RuntimeError` is raised instead of hanging.
* Any unmocked Tkinter dialog creates a modal event loop waiting for native OS window events. Under virtual display (`xvfb-run`), no user is present to dismiss the dialog, causing an indefinite freeze.
