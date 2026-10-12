# Implementation Plan: Table Content Continuation Across Pages, True Geometry Clamping & Layout Hardening

**Branch**: `033-table-content-continuation-and-geometry` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-table-content-continuation-and-geometry/spec.md`

---

## Summary

This feature resolves 5 critical table layout, content preservation, and geometry defects identified during senior repository review:
1. **P1: Multi-Page Table Text Content Continuation (Zero Text Loss)**: In `TableLayoutData.slice_page()` and `DocumentLayoutEngine.render()`, partition cell lines (`rendered_lines` and `line_metrics`) dynamically across page slices and transfer remaining lines to continuation cells on subsequent pages instead of assigning empty arrays (`rendered_lines=[]`). For single rows taller than a page, maintain incremental row continuation across pages until complete.
2. **P1: True Stroke Geometry Boundary Containment**: Evaluate line bottom boundaries using $\text{bottom\_y} = \text{baseline\_y} + \text{effective\_descent} + \text{jitter\_tolerance}$ rather than baseline position alone. Ensure no stroke with letter descenders, tall formulas, or handwriting jitter exceeds printable page margins ($\text{page\_height} - \text{margin\_bottom}$) or cell bounding boxes.
3. **P2: Pure Geometric Width Measurement Without Writer Mutation**: Implement a pure, non-mutating text measurement method in `Writer` for candidate prefixes during character-level token wrapping, eliminating $O(n^2)$ full stroke assemblies and preventing mutation of `Writer.counts`, `Writer.last`, and `Writer.assembled`.
4. **P2: Tight Per-Cell Stroke Bounding Box Verification**: Strengthen test assertions in `test_table_wrapping_pipeline.py` and `test_table_rich_inlines.py` to verify that strokes stay strictly within individual cell bounding boxes ($[x_{\min}, x_{\max}]$ and $[y_{\min}, y_{\max}]$) and do not collide with cell borders.
5. **P2: End-to-End Layout Warning Propagation**: Add a `warnings: list[str]` field to `WriteResult`, collect table slicing warnings from `TableLayoutData.warnings` in `DocumentLayoutEngine.render()`, forward them through `BrowserBridge.write_text()`, and display them in the Web UI `#editor-warnings` container and CLI reports.

---

## Technical Context

**Language/Version**: Python 3.10+ (supporting Python 3.10, 3.11, 3.12, 3.13, 3.14 via Pyodide), JavaScript ES2022 (Node.js 20+, browser ESM)

**Primary Dependencies**: Zero external dependencies for core Python layout (`chuviettay`), standard browser DOM/SVG APIs, Playwright (for E2E tests)

**Storage**: In-memory document AST, `.xopp` (gzipped XML), IndexedDB (web client)

**Testing**: `pytest` (with `pytest-timeout`), `node:test`, `@playwright/test`

**Target Platform**: Linux, macOS, Windows desktop (CLI/Tkinter), Web client (Pyodide WASM in Web Worker)

**Project Type**: Python library, CLI, desktop GUI, static web application

**Performance Goals**: Layout latency under 100ms for typical tables (< 50 rows), linear $O(N)$ token wrapping measurement, zero pagination hangs

**Constraints**:
- Strict MVC boundaries enforced by `tests/test_architecture.py`.
- Golden Master hash invariance for Plain paper (`tests/test_golden_master_real_path.py`).
- 100% of handwritten and border strokes within printable page boundaries ($y \le \text{page\_height} - 60.0$) and cell bounding boxes.
- Zero text content dropped across table page splits.

**Scale/Scope**: 5 core files modified (`table_layout.py`, `engine.py`, `writer.py`, `composer.py`, `bridge.py`), ~5 targeted test suites.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|:---:|
| **I. Maintainability & Code Cleanliness** | Self-documenting algorithms, explicit coordinate math, clean contracts. | **PASS** |
| **II. Simple Architecture (KISS & YAGNI)** | Reuses existing `TableLayoutEngine` and `LaidOutCell`; extends existing data flow without speculative abstractions. | **PASS** |
| **III. Comprehensive Automated Testing** | Adds strict per-cell coordinate bounds, multi-page text preservation assertions, and state invariance tests. | **PASS** |
| **IV. Loose Coupling & High Cohesion** | Strict MVC boundary adherence; `WriteResult` encapsulates results cleanly; UI displays diagnostics without model leaks. | **PASS** |
| **V. Quality Gates & Verification** | All automated quality checks pass: ruff lint, golden master, browser tests, full pytest suite. | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/033-table-content-continuation-and-geometry/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data entities and validation rules
├── quickstart.md        # Phase 1 runnable validation scenarios
├── contracts/           # Phase 1 interface contracts
│   ├── table-continuation-contract.md
│   ├── stroke-geometry-containment-contract.md
│   ├── writer-measurement-contract.md
│   └── layout-warning-propagation-contract.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 task checklist (generated by /speckit-tasks)
```

### Source Code (repository root)

```text
chuviettay/
├── layout/
│   ├── table_layout.py       # TableLayoutEngine: line partitioning across slices, continuation cell line transfer
│   └── engine.py             # DocumentLayoutEngine: bottom_y clamping, pure width measurement in cell_inlines_formatter, warning aggregation
├── model/
│   ├── writer.py             # Writer: pure measure_text_width() without state mutation
│   └── composer.py           # WriteResult: warnings field addition
├── browser/
│   └── bridge.py             # BrowserBridge: merge WriteResult.warnings into response payload
└── formatting.py             # CLI formatting: print layout warnings in report

tests/
├── test_table_pagination_closure.py  # Multi-page text preservation & warning propagation tests
├── test_table_rich_inlines.py        # Per-cell bounding box & descender/math boundary tests
├── test_table_wrapping_pipeline.py   # Writer state invariance & cell bounding box tests
└── test_golden_master_real_path.py   # Regression invariant check
```

**Structure Decision**: Monorepo layout with pure Python backend core in `chuviettay/`, static frontend in `webapp/`, and test suites in `tests/`.

---

## Complexity Tracking

> Zero constitution violations; no unnecessary abstractions introduced.

| Potential Issue | Why Needed | How Complexity Was Kept Minimal |
|---|---|---|
| Line Partitioning in Table Slices | Prevent silent text loss when table cells cross page breaks | Directly partition `rendered_lines` and `line_metrics` during `slice_page()` using line heights |
| True Stroke Bottom Checking | Prevent descenders/formulas from bleeding past page and cell boundaries | Single algebraic formula ($\text{baseline\_y} + \text{effective\_descent} + \text{jitter}$) evaluated before drawing |
| Pure Width Measurement | Prevent $O(n^2)$ synthesis overhead and `Writer` random cache pollution | Cache character advance widths in `Bank`/`Writer`; simple linear sum for candidate slices |
