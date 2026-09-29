# Contract: Automated Test Runner & Optional Dependency Guard Specification

**Contract Identifier**: `TEST-RUNNER-V1`
**Location**: `tests/` and test configuration

---

## 1. Optional Dependency Collection Guard Contract

Any test module or function requiring optional third-party packages MUST conform to the collection guard pattern:

### 1.1 Module-Level Optional Dependency Pattern
When an entire test file requires an optional library (e.g. `docx` or `markdown_it`), the module header MUST guard imports using `pytest.importorskip`:

```python
import pytest

# Guard collection: skips the whole module if package is absent
pytest.importorskip("docx")

from docx import Document as DocxDoc
from docx.oxml import parse_xml
```

### 1.2 Function-Level Optional Dependency Pattern
When only specific tests in a module require an optional library (e.g. `test_table_merged_cells.py::test_docx_import_table_with_merged_cells`), the test function MUST guard its execution at the very beginning:

```python
def test_docx_import_table_with_merged_cells(tmp_path):
    pytest.importorskip("docx")
    import docx
    ...
```

### 1.3 Invariants
1. **Zero Collection Crashes**: In an environment where optional packages (`docx`, `markdown_it`) are completely absent, running `pytest --collect-only` MUST exit with code 0 and 0 errors.
2. **Deterministic Status**: Tests requiring missing packages MUST report `SKIPPED`, never `FAILED` or `ERROR`.

---

## 2. Fixture Exception Translation Contract

Fixtures and test helpers asserting on optional package presence MUST translate `OptionalDependencyError` into a test skip:

```python
@pytest.fixture(autouse=True)
def require_docx():
    pytest.importorskip("docx", reason="Cần cài đặt python-docx để chạy kiểm thử định dạng Word")
```

### Invariants
* Under no circumstances may an `OptionalDependencyError` bubble up unhandled into the pytest test execution runner.

---

## 3. Test Watchdog & Timeout Contract

When tests are executed with `pytest --timeout=30`:

1. **Normal Completion**: Any test completing under 30.0s terminates with its natural status (`PASSED`, `SKIPPED`, or `FAILED`).
2. **Watchdog Intervention**: If any test runs for $> 30.0\text{s}$:
   * The watchdog thread / signal interrupts the test.
   * Pytest prints `+++ Timeout (30.0s) +++` followed by thread dump stack frames to stderr.
   * The test status is recorded as `FAILED`.
   * Pytest proceeds to the next test in sequence without aborting the entire session.
3. **Long Benchmark Exemption**: Tests intentionally designated as long benchmarks (e.g. 50-word persistence benchmark with $\ge 5,000$ samples) MUST specify `@pytest.mark.timeout(120)` to declare their extended budget.
