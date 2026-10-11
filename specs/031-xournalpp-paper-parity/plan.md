# Implementation Plan: Xournal++ Paper Background and Geometry Parity

**Branch**: `031-xournalpp-paper-parity` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-xournalpp-paper-parity/spec.md`

## Summary

Achieve 1:1 paper geometry, XML specification, and preview rendering parity with Xournal++ (master branch):
1. **Fix PDF Backgrounds (Mục 1)**: Correct `pageno` to 1-based (`page_index + 1`), enforce `domain="absolute"` with bare relative filenames, and purge all `domain="relative"` references from codebase and tests.
2. **Web SVG Paper Preview Parity (Mục 2)**: Unify `renderPageSvgString` and `renderPageSvgElement` in `webapp/js/paper.js`. Accurately render Xournal++ geometry for Ruled/Lined (header 80, footer 60, negative $m_1$), Graph (margins, bold intervals), Dotted, Isometric Graph/Dotted, and 5-line Staves with automatic light/dark contrast coloring.
3. **Adaptive Baseline Ruling Snapping (Mục 3)**: Introduce `WriteOptions.snap_to_ruling: bool = True` in `chuviettay/model/composer.py` and `chuviettay/layout/engine.py`. Align text baselines to $y = 80 + k \cdot \text{pitch}$ where $\text{pitch} = r_1 \cdot \max(1, \text{round}(\text{line\_h} / r_1))$, break pages at $\text{pageHeight} - 60$, and clamp to lined margins. Keep Plain paper layout 100% untouched to preserve `test_golden_master.py` hash invariance.
4. **PageBackground Serialization & Presets (Mục 4)**: Enhance `PageBackground` with full Xournal++ config keys (`r1`, $m_1$ including negative offsets, `lw`, `f1`, `f2`, `rm`, `bli`, `blw`). Define `BACKGROUND_PRESETS` in `chuviettay/document/page_format.py` matching `pagetemplates.ini.in`. Add CLI options `--bg-preset`, `--bg-r1`, `--bg-m1`, `--bg-color`.
5. **Unified Page Catalog & Cross-Platform UI (Mục 5)**: Create canonical `get_page_catalog()` serving Python core, Web frontend, and Tkinter UI with paper formats, presets, and color palettes.

## Technical Context

**Language/Version**: Python 3.11+, JavaScript (ES6+ / Web Worker), HTML5 / SVG

**Primary Dependencies**: Standard library (`xml.etree`, `gzip`, `dataclasses`, `math`, `re`), `pytest`, `@playwright/test`

**Storage**: `.xopp` gzip XML output, in-memory Document IR, static web assets

**Testing**: `pytest` (unit & integration), `@playwright/test` / Jest (browser E2E & web unit)

**Target Platform**: Cross-platform desktop (Windows, macOS, Linux) & Modern Web Browsers (Pyodide Worker)

**Project Type**: Core Python handwriting engine + Web application client + Tkinter desktop GUI

**Performance Goals**: Snapping and XML generation overhead $< 2\,\text{ms}$ per page; SVG paper background rendering $< 10\,\text{ms}$ in browser.

**Constraints**:
- Strict adherence to MVC architecture (`test_architecture.py`).
- No changes to constants in `chuviettay/config.py` (`CW`, `CH`, `BASE`, `COLS`, `ROWS`, `PAGE_W`, `PAGE_H`).
- Zero coordinate deviation or hash change for Plain background in `test_golden_master.py`.
- No GPL C++ code copied into repo (MIT license); clean-room geometric facts only.

**Scale/Scope**: All standard paper formats (A3-A5, Letter, Legal, 16:9, 4:3, Custom), 8 paper ruling styles, and light/dark color palettes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Maintainability & Code Cleanliness**: PASS. Geometry bounds and ruling calculations are encapsulated into clear, mathematically documented helpers (`getIndexBounds`, `renderBackgroundSvg`, `resolve_snapping_metrics`).
- **II. Simple Architecture (KISS & YAGNI)**: PASS. Reuses existing `PageFormat`, `PageBackground`, and `DocumentLayoutEngine` classes with minimal additive parameters. No unnecessary abstractions or third-party libraries introduced.
- **III. Comprehensive Automated Testing**: PASS. All 5 areas are covered by unit and E2E tests: PDF background indexing, negative margin parsing, baseline snapping coordinates, golden master hash invariance, and SVG DOM structure.
- **IV. Loose Coupling & High Cohesion**: PASS. `PageBackground` and `page_format.py` act as the single source of truth for page geometry without leaking view-specific code into models.

## Project Structure

### Documentation (this feature)

```text
specs/031-xournalpp-paper-parity/
├── plan.md              # This implementation plan
├── research.md          # Phase 0 research & geometric equations
├── data-model.md        # Phase 1 entities, invariants & data types
├── quickstart.md        # Phase 1 runnable validation guide
├── contracts/           # Phase 1 interface contracts
│   ├── xopp-background-contract.md
│   └── page-catalog-contract.md
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── composer.py            # Add snap_to_ruling to WriteOptions & allow negative m1 in validate()
│   └── xopp.py                # Fix pdf_background_xml (1-based pageno, absolute domain)
├── document/
│   └── page_format.py         # Full PageBackground config attrs, BACKGROUND_PRESETS, get_page_catalog()
├── layout/
│   └── engine.py              # Implement ruling baseline snapping & lined margin clamping
├── fidelity/
│   └── engine.py              # Use 1-based page_index + 1 and domain="absolute"
├── cli.py                     # Add --bg-preset, --bg-r1, --bg-m1, --bg-color, --no-snap-ruling
└── view/
    └── write_tab.py           # Sync paper formats and background presets from get_page_catalog()
webapp/
├── index.html                 # Add preset and paper tone dropdowns
└── js/
    ├── paper.js               # Unified renderBackgroundSvg with exact Xournal++ geometry
    └── write.js               # Synchronize catalog options with Pyodide worker
tests/
├── test_architecture.py       # MVC architectural enforcement
├── test_golden_master.py      # Golden master hash invariance (plain background)
├── test_docx_fidelity.py      # PDF background 1-based pageno and absolute domain
├── test_paper_size_background.py # PageBackground config serialization & negative m1
└── test_paper_ruling_snap.py  # New test verifying baseline ruling alignment
```

**Structure Decision**: Monorepo with core logic under `chuviettay/`, static web UI under `webapp/`, and test suites under `tests/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Strictly adheres to existing patterns and simplicity principles |
