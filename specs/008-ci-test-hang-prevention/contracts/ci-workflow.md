# Contract: GitHub Actions CI Workflow Specification

**Contract Identifier**: `CI-WORKFLOW-V1`
**Location**: `.github/workflows/ci.yml`

---

## 1. Concurrency Contract

The continuous integration workflow MUST define a top-level concurrency block satisfying the following contract:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Constraints & Invariants
1. `group`: Must combine workflow name and Git reference (`${{ github.workflow }}-${{ github.ref }}`).
2. `cancel-in-progress`: **MUST be boolean `true`**.
   * It must NOT be conditionally restricted to pull requests.
   * Pushes to `main`, tags, and branches MUST preempt running workflows for the same ref.
   * Replaced jobs must transition to `cancelled` within 15 seconds.

---

## 2. Test Job Contract

The `test` job definition in `.github/workflows/ci.yml` MUST satisfy:

```yaml
jobs:
  test:
    name: Test (${{ matrix.os }} / Python ${{ matrix.python-version }})
    needs: [lint]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 10
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12', '3.13']
```

### Constraints & Invariants
1. `timeout-minutes`: **MUST be `10`**. No runner may execute longer than 10 minutes total.
2. `fail-fast`: Must remain `false` so failures on one Python version or OS do not cancel diagnostic collection on others.
3. `matrix`: Must cover 8 combinations (`ubuntu-latest`, `windows-latest` across Python `3.10`, `3.11`, `3.12`, `3.13`).

---

## 3. Dependency Installation Contract

The dependency installation step MUST install developer tooling, test runners, and optional document parsing packages:

```yaml
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
          pip install .[docs]
```

### Constraints & Invariants
1. `requirements-dev.txt`: Must install `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `pyinstaller==6.12.0`, `ruff>=0.4.0`.
2. `pip install .[docs]`: Must install `python-docx>=1.1.0`, `markdown-it-py>=3.0.0`, and `mdit-py-plugins>=0.4.0`.

---

## 4. Test Execution Step Contract

Test runner invocations MUST stream real-time logs and enforce the 30-second watchdog:

```yaml
      - name: Run pytest with virtual display (Linux)
        if: runner.os == 'Linux'
        run: xvfb-run -a python -m pytest -vv -s --timeout=30

      - name: Run pytest (Windows)
        if: runner.os == 'Windows'
        run: python -m pytest -vv -s --timeout=30
```

### Constraints & Invariants
1. Virtual Display: Linux runs must be wrapped in `xvfb-run -a` to support Tkinter GUI windows.
2. Verbosity: Flags `-vv -s` are mandatory to stream live test names and live stdout.
3. Timeout Watchdog: Flag `--timeout=30` is mandatory to abort any deadlocked test in 30 seconds.
