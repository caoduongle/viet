# Implementation Plan: Paper Sizes, Page Margins & Native XOPP Backgrounds

**Branch**: `011-paper-size-and-background` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-paper-size-and-background/spec.md`

## Summary

Decouple document layout from arbitrary fixed bounds (`MAXH = 3000.0 pt` and handwriting-dependent page width) by introducing standardized paper sizes (A5, A4, A3, Letter, Legal, 16:9, 4:3, Custom), page orientations (portrait, landscape), configurable content margins (`margin_left`, `margin_right`, `margin_top`, `margin_bottom`), and native XOPP XML backgrounds (`plain`, `lined`, `ruled`, `graph`, `dotted`, `iso_graph`, `iso_dotted`, `music` with configurable grid spacing such as `r1=14.17` for 5 mm ô li). Expose these options consistently through CLI flags and GUI WriteTab controls while preserving 100% backward compatibility for existing calibration and write workflows.

## Technical Context

**Language/Version**: Python 3.10+ (tested across Python 3.10 - 3.13 on Ubuntu and Windows)

**Primary Dependencies**: Standard library (`dataclasses`, `typing`, `math`, `re`, `gzip`, `xml.etree.ElementTree`, `tkinter`), `markdown-it-py` (Markdown parser), `python-docx` (DOCX import)

**Storage**: Direct streaming gzip-compressed XML file format (`.xopp`)

**Testing**: `pytest`, `pytest-cov`, `ruff`

**Target Platform**: Windows 10/11, Linux (Ubuntu 22.04+), macOS

**Project Type**: Desktop CLI & GUI Application / Core handwriting synthesis library

**Performance Goals**: Instantaneous geometry calculation (<1 ms overhead per document), memory-efficient streaming page generation via `PageBuffer`

**Constraints**:
- Zero pen strokes drawn for page backgrounds (let Xournal++ render backgrounds natively via `<background .../>` XML tags).
- All internal layout and XML dimensions use typography points ($72\text{ pt} = 1\text{ in}$, $1\text{ mm} \approx 2.83465\text{ pt}$).
- Usable width and height must never be negative or zero (minimum fallback boundaries enforced).
- Golden master compatibility: existing calibration tools (`make_grid`, `check`, `seed`) remain unaffected.

**Scale/Scope**:
- 1 new module: `chuviettay/document/page_format.py`
- 5 modified core modules: `chuviettay/model/composer.py`, `chuviettay/model/xopp.py`, `chuviettay/layout/stream.py`, `chuviettay/layout/engine.py`, `chuviettay/cli.py`, `chuviettay/view/write_tab.py`
- Comprehensive unit and integration tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | Clear dataclasses (`PaperSize`, `PageBackground`, `PageFormat`) with strict type annotations and docstrings. Clean separation between units (user-facing mm/cm vs internal pt). | ✅ PASS |
| **II. Simple Architecture (KISS & YAGNI)** | Dedicated `page_format.py` isolates page metrics without overengineering. Backgrounds rely on native Xournal++ XML attributes rather than custom rendering engines. | ✅ PASS |
| **III. Comprehensive Automated Testing** | Unit tests for unit conversion, paper size dictionaries, orientation flipping, XML generation, and end-to-end multi-page layout pagination. | ✅ PASS |
| **IV. Loose Coupling & High Cohesion** | `DocumentLayoutEngine` queries `PageFormat` for boundaries; `PageBuffer` handles XML page tagging; `WriteOptions` acts as the parameter transport. | ✅ PASS |

## Project Structure

### Documentation (this feature)

```text
specs/011-paper-size-and-background/
├── spec.md              # Feature specification
├── checklists/          # Requirements verification checklists
│   └── requirements.md
├── research.md          # Technical investigation & XOPP background schema
├── plan.md              # Implementation plan (this file)
├── data-model.md        # Entities, attributes, and relationships
├── contracts/           # API contracts & CLI/GUI schemas
│   └── page-format-contract.md
├── quickstart.md        # Runnable verification and testing guide
└── tasks.md             # Dependency-ordered task breakdown (/speckit-tasks output)
```

### Source Code Layout

```text
chuviettay/
├── document/
│   ├── __init__.py
│   ├── page_format.py       # [NEW] PaperSize, PageBackground, PageFormat, PAPER_SIZES, parse_length
│   └── ...
├── layout/
│   ├── engine.py            # [MODIFIED] Consume PageFormat, margins, and realistic pagination
│   └── stream.py            # [MODIFIED] PageBuffer support for per-page dimensions & background
├── model/
│   ├── composer.py          # [MODIFIED] WriteOptions paper/background fields & resolve_page_format()
│   └── xopp.py              # [MODIFIED] page_open_xml() with native background element
├── view/
│   └── write_tab.py         # [MODIFIED] "Trang & Nền giấy" controls & Custom Paper dialog
└── cli.py                   # [MODIFIED] Flags: --paper, --orientation, --background, --background-spacing, etc.

tests/
├── test_page_format.py      # [NEW] Tests for PaperSize, conversions, orientations, backgrounds
├── test_document_pipeline.py# [MODIFIED] Validate page dimensions & pagination in XOPP output
└── test_cli_format.py       # [NEW] CLI argument parsing for paper & background options
```

## Complexity Tracking

> **No Constitution violations detected.** Direct, decoupled dataclasses and native XML tag emissions require no complex abstractions or additional dependencies.
