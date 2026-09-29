# Quickstart: CI Timeout Hardening & Watchdog Validation Guide

**Feature**: `008-ci-test-hang-prevention`
**Date**: 2026-09-30

This guide describes runnable validation scenarios that verify the CI timeout guards, watchdog timer, concurrency cancellation, and optional dependency skip protections.

---

## Prerequisites

* Python 3.10, 3.11, or 3.12 installed.
* Working copy of the repository on branch `008-ci-test-hang-prevention`.
* Development dependencies installed via:
  ```bash
  pip install -r requirements-dev.txt
  ```

---

## Scenario 1: Validate Collection Without Optional Dependencies

Prove that in an environment without `python-docx` installed, pytest collects all tests without crashing:

```bash
# In an environment without docx:
python -m pytest --collect-only tests/test_docx_omml_diagnostics.py
```

**Expected Outcome**:
* Exit code is `0`.
* Output shows `1 file skipped` or test skipped with informative message:
  `Skipped: condition: 'docx' is not installed`.
* Zero unhandled `ModuleNotFoundError` or collection crashes.

---

## Scenario 2: Validate Per-Test Watchdog Timeout Termination

Prove that any test running beyond 30 seconds is forcefully interrupted with a stack trace:

1. Create a temporary test with an infinite loop:
   ```python
   # tests/test_hang_probe.py (temporary validation probe)
   import time
   def test_infinite_loop_probe():
       while True:
           time.sleep(0.1)
   ```
2. Run pytest with the watchdog timeout:
   ```bash
   python -m pytest tests/test_hang_probe.py -vv -s --timeout=5
   ```
3. Observe termination:
   * Test fails at exactly 5.0 seconds.
   * Pytest prints `+++ Timeout (5.0s) +++` followed by the stack frame showing `time.sleep(0.1)`.
   * Exit code is `1` (`FAILED`), proving pytest caught the hang and reported its exact line.

---

## Scenario 3: Validate Real-Time Verbose Streaming Output

Prove that `-vv -s` outputs test names and prints immediately to console:

```bash
python -m pytest tests/test_format_validation.py -vv -s
```

**Expected Outcome**:
* Every single test case path and name (e.g. `tests/test_format_validation.py::test_supported_formats_return_correct_importer`) is printed on its own line in real time.
* Output includes status markers (`PASSED`, `SKIPPED`).

---

## Scenario 4: Validate CI Workflow Configuration Syntax & Invariants

Verify that `.github/workflows/ci.yml` satisfies all contract invariants using a schema or linter check:

1. Inspect `concurrency`:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
2. Inspect `jobs.test`:
   ```yaml
   timeout-minutes: 10
   ```
3. Inspect `steps`:
   * Installs `pip install .[docs]`.
   * Invokes pytest with `-vv -s --timeout=30`.

Refer to [Contract: CI Workflow](contracts/ci-workflow.md) and [Contract: Test Runner](contracts/test-runner.md) for full interface constraints.
