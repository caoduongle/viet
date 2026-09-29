# Implementation Plan: CI Workflow Deadlock Prevention, Test Timeout Diagnostics, and Runner Concurrency Hardening

**Branch**: `008-ci-test-hang-prevention` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-ci-test-hang-prevention/spec.md`

## Summary

Resolve CI test suite hangs and runner queuing deadlocks by:
1. Setting `timeout-minutes: 10` on the CI test job and setting `concurrency.cancel-in-progress: true` unconditionally across branch pushes and PRs.
2. Integrating `pytest-timeout>=2.3.1` into `requirements-dev.txt` and enforcing a 30-second per-test watchdog timeout (`--timeout=30`).
3. Switching CI pytest execution from quiet mode (`-q`) to live verbose streaming (`-vv -s`).
4. Eliminating collection-time crashes (`ModuleNotFoundError: No module named 'docx'`) by adding `pytest.importorskip` guards across all test modules exercising optional document format dependencies.
5. Updating CI dependency installation to include `.[docs]` so the entire document pipeline is thoroughly exercised in CI.
6. Ensuring bounded termination guarantees in layout pagination loops and comprehensive modal dialog mocking in headless GUI tests.

## Technical Context

**Language/Version**: Python 3.10+ (tested across 3.10, 3.11, 3.12, 3.13 on Ubuntu Linux and Windows)

**Primary Dependencies**: `pytest>=8.0.0`, `pytest-timeout>=2.3.1`, `python-docx>=1.1.0` (optional extra: docs), `markdown-it-py>=3.0.0` (optional extra: docs), `mdit-py-plugins>=0.4.0` (optional extra: docs)

**Storage**: Single gzip-compressed JSON file (`*.json.gz`); Xournal++ output (`*.xopp`)

**Testing**: `pytest` with `pytest-timeout`, `pytest.importorskip`, virtual display (`xvfb-run` on Linux), headless Tkinter mocking

**Target Platform**: GitHub Actions CI (`ubuntu-latest`, `windows-latest`), local developer workstations

**Project Type**: Desktop application & CLI tool (`chuviettay`)

**Performance Goals**: 100% CI jobs terminate under 10 minutes; individual tests timeout within 30 seconds upon hang; zero collection crashes; pending queue time for new commits $< 30\text{s}$

**Constraints**: Zero mandatory non-standard runtime dependencies for end-users; development dependencies isolated to `requirements-dev.txt` and `pyproject.toml [project.optional-dependencies]`; cross-platform deterministic test execution

**Scale/Scope**: 1 CI workflow (`.github/workflows/ci.yml`), 1 requirements file (`requirements-dev.txt`), ~6 test modules (`tests/test_docx_omml_diagnostics.py`, `tests/test_importer_docx.py`, `tests/test_importer_markdown.py`, `tests/test_gui_document.py`, `tests/test_table_merged_cells.py`, `tests/test_cli_format.py`), and layout/gui safety checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Maintainability & Code Cleanliness | Self-documenting test skip guards, clear timeout error messages with stack traces | ✅ PASS — `pytest.importorskip` and `pytest-timeout` tracebacks pinpoint issues immediately |
| II. Simple Architecture (KISS & YAGNI) | Use standard workflow configurations and proven plugins without custom timer hacks | ✅ PASS — native GitHub Actions `timeout-minutes`, standard `pytest-timeout`, standard `pytest.importorskip` |
| III. Comprehensive Automated Testing | Deterministic CI execution; eliminate silent hangs and collection errors; 100% test pass/skip integrity | ✅ PASS — prevents runner starvation, unblocks queue, provides live streaming logs |
| IV. Loose Coupling & High Cohesion | Optional format tests gracefully decouple when optional packages are not installed | ✅ PASS — core application and base tests remain 100% decoupled from `python-docx` |

## Project Structure

### Documentation (this feature)

```text
specs/008-ci-test-hang-prevention/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical decisions & rationale
├── data-model.md        # Phase 1 entities & validation rules
├── quickstart.md        # Phase 1 runnable validation guide
├── contracts/           # Phase 1 interface contracts
│   ├── ci-workflow.md   # CI configuration & concurrency contract
│   └── test-runner.md   # Pytest execution & timeout contract
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
.github/workflows/
└── ci.yml                     # timeout-minutes: 10, cancel-in-progress: true, -vv -s, pip install .[docs]

requirements-dev.txt          # Add pytest-timeout>=2.3.1

tests/
├── test_docx_omml_diagnostics.py # Add pytest.importorskip("docx") before docx imports
├── test_importer_docx.py         # Add pytest.importorskip("docx")
├── test_importer_markdown.py     # Add pytest.importorskip("markdown_it")
├── test_gui_document.py          # Add pytest.importorskip("docx") for docx test
├── test_table_merged_cells.py    # Add pytest.importorskip("docx") for docx test
├── test_cli_format.py            # Add pytest.importorskip("docx") for docx test
└── test_gui.py                   # Verify complete modal dialog interception

chuviettay/layout/
├── engine.py                 # Verify bounded loop iteration invariants in pagination
└── table_layout.py           # Verify bounded column and row measurement loops
```

**Structure Decision**: Standard desktop repository layout. Changes are localized strictly to CI workflow definitions, developer requirements, test skip guards, and algorithm iteration bounds.

## Complexity Tracking

No constitution violations to justify. All additions use standard, minimal configurations to harden test resilience and debugging observability.
