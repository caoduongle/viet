# Implementation Plan: Table Layout and DOCX Import Fidelity

**Branch**: `031-table-docx-layout-fidelity` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-table-docx-layout-fidelity/spec.md`

## Summary

Resolve critical table handling issues across the entire pipeline from DOCX document import to multi-page pagination and math formula rendering:
1. Prevent silent table deletion in `chuviettay/browser/bridge.py` during web DOCX import by serializing `Table` blocks to Markdown pipe tables (handling pipe escaping `\|`, cell whitespace normalization without breaking Markdown rows, 1-row table delimiter synthesis, and flattened merge warnings), preserving inlines and math expressions, and surfacing diagnostic warnings in `webapp/js/write.js`.
2. Fix unsafe pagination in `chuviettay/layout/table_layout.py` (`slice_page`) by computing the transitive closure of multi-row merged cells (`rowspan`) so interdependent merge groups never split across page breaks, and ensuring atomic group progression on fresh pages to prevent infinite loops.
3. Compute exact line vertical metrics (ascent, descent, baseline) for math formulas in table cells by reusing `self._math_extent` from `_layout_inlines()`, dynamically expanding row height and ensuring formula strokes maintain minimum clearance from cell borders.
4. Safeguard column widths against unbroken wide tokens with character-level wrapping, and optimize border stroke generation from $O(R^3 \cdot C^2)$ to $O(R \cdot C)$ using precomputed occupancy masks.
5. Enhance web table insertion with a customizable row/column prompt instead of a hardcoded 3x3 template.
6. Complement with deterministic unit, integration, and Playwright E2E tests verifying concrete coordinates, stroke bounds, and table content retention.

## Technical Context

**Language/Version**: Python 3.11+, JavaScript (ES6+ / Web Worker), TypeScript (Playwright E2E)

**Primary Dependencies**: `python-docx`, `lxml`, `pytest`, `@playwright/test`, Native Pyodide Web Worker

**Storage**: In-memory document IR, `.xopp` XML output, `.json.gz` handwriting banks

**Testing**: `pytest` (unit & integration), `@playwright/test` (browser E2E)

**Target Platform**: Cross-platform (Windows, Linux, macOS), Web Client (Modern Web Browsers via Pyodide)

**Project Type**: Python Core Engine Library + Browser Web Client (Pyodide Worker)

**Performance Goals**: Table border stroke generation for 100 rows $\times$ 20 cols $< 50\text{ms}$; DOCX import to editor preview $< 500\text{ms}$ (excluding one-time wheel downloads).

**Constraints**: Memory efficiency in Web Worker, 0% data drop during DOCX table import, strict boundary containment ($\ge 1\text{mm}$ clearance) for math formulas.

**Scale/Scope**: Tables from 1x1 up to 100x20, multi-page worksheets, nested tables, multi-tier LaTeX math formulas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Maintainability & Code Cleanliness**: PASS. Code changes strictly modularize table conversion, row closure calculation, and line metrics measurement into dedicated, testable functions with comprehensive docstrings explaining *why* decisions were made.
- **II. Simple Architecture (KISS & YAGNI)**: PASS. Reuses the existing Markdown editing and live preview pipeline by converting DOCX tables to standard pipe tables and extracting nested content with diagnostics, rejecting overly complex and speculative WYSIWYG block rewrites.
- **III. Comprehensive Automated Testing**: PASS. All regressions (DOCX table drop, transitive rowspan splits, formula border collisions) are backed by automated unit and E2E tests checking concrete cell content and geometric coordinates.
- **IV. Loose Coupling & High Cohesion**: PASS. `TableLayoutEngine` remains the sole geometric authority; `bridge.py` orchestrates browser communication; `docx_importer.py` parses OpenXML; `engine.py` coordinates document-level flow. No cross-module private leaks.

## Project Structure

### Documentation (this feature)

```text
specs/031-table-docx-layout-fidelity/
├── plan.md              # This implementation plan
├── research.md          # Phase 0 research & architectural decisions
├── data-model.md        # Phase 1 data entities, metrics & invariants
├── quickstart.md        # Phase 1 runnable verification guide
├── contracts/           # Phase 1 interface contracts
│   ├── table-layout-contract.md
│   └── browser-bridge-import-contract.md
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── browser/
│   └── bridge.py              # Update import_docx to serialize Table blocks & return warnings
├── document/
│   └── ir.py                  # Ensure Table, TableCell, TableRow support needed metrics
├── importer/
│   └── docx_importer.py       # Support nested table extraction & unsupported diagnostics
├── layout/
│   ├── engine.py              # Integrate line vertical metrics & baseline positioning
│   └── table_layout.py        # Transitive row closure, token wrapping, O(R*C) border strokes
webapp/
├── index.html                 # Add table creation dialog / modal elements
└── js/
    └── write.js               # Handle warnings from import_docx, custom table insertion
tests/
├── test_table_layout.py       # Transitive merge pagination, border stroke benchmarks
├── test_table_rich_inlines.py # Formula height, bounding box clearance in cells
├── test_docx_table_import.py  # Lossless table import & warnings verification
└── e2e/
    └── docx-import.spec.ts    # Playwright E2E verifying table presence in editor & preview
```

**Structure Decision**: Monorepo structure with Python core engine under `chuviettay/`, static web application under `webapp/`, and test suites under `tests/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Design strictly follows KISS and constitution standards |
