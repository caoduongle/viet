# Implementation Plan: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-docx-fidelity-replacement/spec.md`

---

## Summary

Implement a dedicated **Fidelity Mode** alongside the existing Semantic Mode for processing DOCX documents. In Fidelity Mode, the system locks the source document's geometry, dimensions, and page count (e.g. 19 pages remain 19 pages). Embedded images (19 PNG inline drawings), table borders, charts, and diagrams are 100% preserved in a non-text visual companion background (generated via DOCX whiteout run transformation converted to PDF). Text spans are extracted with exact spatial bounding boxes, and handwritten strokes are fitted directly in-place without reflow. Output is generated as a multi-page `.xopp` file referencing the companion background PDF.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested on 3.10, 3.11, 3.12, 3.13)

**Primary Dependencies**: `python-docx` (already installed), standard library (`xml.etree.ElementTree`, `subprocess`, `dataclasses`, `gzip`, `pathlib`)

**Storage**: Gzip-compressed XML (`.xopp` format) and PDF companion background (`.pdf`)

**Testing**: `pytest` (unit, integration, CLI, and fidelity layout tests)

**Target Platform**: Cross-platform (Windows, Linux, macOS). Native MS Word COM/PowerShell converter on Windows; headless LibreOffice / vector fallback on Linux/macOS.

**Project Type**: Desktop GUI app and CLI utility

**Performance Goals**: Fast conversion (<10s for 19-page documents), sub-second stroke calculation, vector crispness

**Constraints**: Zero regression on existing 411 tests; strict preservation of layered architecture (`test_architecture.py` compliance); clean separation of Semantic vs. Fidelity modes.

**Scale/Scope**: Handles complex technical problem sets, exams, and notes containing multiple images, tables, and multi-page layouts.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Maintainability & Code Cleanliness**: PASS. Separates fixed-layout replacement from semantic reflow rather than convoluting `DocxImporter` or `DocumentLayoutEngine`.
- **Principle II: Simple Architecture (KISS & YAGNI)**: PASS. Uses whiteout text transformation on DOCX to produce the background PDF, avoiding heavy binary dependencies or unstable post-render redaction hacks.
- **Principle III: Comprehensive Automated Testing**: PASS. All fidelity behavior validated with automated tests in `tests/test_docx_fidelity.py`.
- **Principle IV: Loose Coupling & High Cohesion**: PASS. The new fidelity module (`chuviettay/fidelity/`) is decoupled from GUI and CLI, communicating strictly via `AppController`.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-docx-fidelity-replacement/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical research & decisions
├── data-model.md        # Domain entities and spatial models
├── quickstart.md        # Runnable validation scenarios
├── contracts/
│   └── fidelity-contract.md # Public API and CLI contracts
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code Layout

```text
chuviettay/
├── controller/
│   └── app_controller.py      # Exposed write_docx_fidelity() method
├── fidelity/
│   ├── __init__.py            # Package export
│   ├── fixed_model.py         # FixedDocument, FixedPage, TextBox, ImageBox
│   ├── extractor.py           # DOCX spatial text & image extractor
│   ├── background.py          # Whiteout run transform & PDF background generator
│   └── engine.py              # FidelityLayoutEngine placing strokes into bounding boxes
├── model/
│   ├── composer.py            # WriteOptions mode enum ('semantic' | 'fidelity')
│   └── xopp.py                # page_open_xml with PDF background support
└── cli.py                     # CLI --mode argument handling

tests/
├── test_docx_fidelity.py      # Unit & integration tests for Fidelity Mode
└── fixtures/
    └── sample.docx            # Test fixture DOCX
```

**Structure Decision**: Introduces cohesive `chuviettay/fidelity/` package keeping fixed-geometry algorithms cleanly isolated from the semantic `chuviettay/document/` and `chuviettay/layout/` reflow engines.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `fidelity/` package | Clean architectural separation between fixed-layout text replacement and semantic reflow | Cramming coordinate locking into `DocumentLayoutEngine` would violate Single Responsibility and break existing reflow logic |
