# Implementation Plan: DOCX Fidelity and In-Place Handwriting Replacement Mode

**Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification updated with P0 zero-fixture fallback, P1 DrawingML shape whiteout, and P1 mixed-inline spatial segmentation.

---

## Summary

Implement a dedicated **Fidelity Mode** alongside the existing Semantic Mode for processing DOCX documents.
In Fidelity Mode:
1. Locks the source document's geometry, dimensions, and page count (e.g. 19 pages remain 19 pages).
2. Embedded images (19 PNG inline drawings), table borders, charts, diagrams, and shapes are 100% preserved in a non-text visual companion background generated via DOCX whiteout run transformation converted to PDF.
3. The whiteout transformation comprehensively whitens text in standard paragraphs, nested table cells, headers, footers, and DrawingML/textbox shapes (`w:txBody`, `w:drawing`, `v:textbox`), ensuring 0% printed text ghosting.
4. Text spans are extracted with exact spatial bounding boxes, segmenting paragraphs with interleaved inline images (`text -> image -> text`) into distinct non-overlapping spatial boxes.
5. In-place replacement: handwritten strokes are fitted directly into text bounding boxes without reflow or image collision.
6. Zero-fixture fallback in production: if neither Microsoft Word COM nor LibreOffice is available, the system halts with an explicit error instead of leaking test fixture data.
7. Output is generated as a multi-page `.xopp` file referencing the companion background PDF via portable relative paths.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested on 3.10, 3.11, 3.12, 3.13)

**Primary Dependencies**: `python-docx` (already installed), standard library (`xml.etree.ElementTree`, `subprocess`, `dataclasses`, `gzip`, `pathlib`, `tempfile`)

**Storage**: Gzip-compressed XML (`.xopp` format) and PDF companion background (`_background.pdf`)

**Testing**: `pytest` with test-specific fixtures/mocks (unit, integration, CLI, GUI, and fidelity layout tests)

**Target Platform**: Cross-platform (Windows, Linux, macOS). Native MS Word COM/PowerShell converter on Windows; headless LibreOffice on Linux/macOS. Production strictly fails fast if converters are missing.

**Project Type**: Desktop GUI app and CLI utility

**Performance Goals**: Fast conversion (<10s for 19-page documents), sub-second stroke calculation, vector crispness

**Constraints**: Zero regression on existing test suite (422+ tests passing); strict preservation of layered architecture (`test_architecture.py` compliance); clean separation of Semantic vs. Fidelity modes; zero dummy fixture leakage in production code.

**Scale/Scope**: Handles complex technical problem sets, exams, and notes containing multiple images, tables, and multi-page layouts.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Maintainability & Code Cleanliness**: PASS. Fixed-layout replacement is isolated in `chuviettay/fidelity/` rather than convoluting `DocxImporter` or `DocumentLayoutEngine`.
- **Principle II: Simple Architecture (KISS & YAGNI)**: PASS. Uses whiteout XML transformation on DOCX to produce the background PDF, avoiding heavy binary dependencies or unstable post-render redaction hacks.
- **Principle III: Comprehensive Automated Testing**: PASS. All fidelity behavior validated with automated tests in `tests/test_docx_fidelity.py`, `tests/test_cli_format.py`, and `tests/test_gui_document.py`.
- **Principle IV: Loose Coupling & High Cohesion**: PASS. The fidelity module (`chuviettay/fidelity/`) is decoupled from GUI and CLI, communicating strictly via `AppController`.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-docx-fidelity-replacement/
├── spec.md              # Feature specification (updated with P0/P1 requirements)
├── plan.md              # Implementation plan (this file)
├── research.md          # Technical research & architectural decisions
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
│   ├── fixed_model.py         # FixedDocument, FixedPage, TextBox, ImageBox, TableGeometry
│   ├── converter.py           # FidelityConverter (Word COM / LibreOffice, zero-fallback production)
│   ├── background.py          # WhiteoutBackgroundGenerator (paragraphs, nested tables, DrawingML/shapes)
│   ├── extractor.py           # SpatialTextExtractor (multiline splitting & mixed-inline segmentation)
│   └── engine.py              # FidelityLayoutEngine (bounding box fitting, alignment, jitter, XOPP output)
├── model/
│   ├── composer.py            # WriteOptions mode enum, WriteResult statistics
│   └── xopp.py                # pdf_background_xml helper with relative domain support
├── cli.py                     # CLI --mode argument and fidelity reporting
└── view/
    └── write_tab.py           # GUI Combobox selection and DOCX requirement enforcement

tests/
├── test_docx_fidelity.py      # Unit & integration tests for Fidelity Mode
├── test_cli_format.py         # CLI mode flags and rejection of non-DOCX files
└── test_gui_document.py       # GUI fidelity selection and error dialog tests
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `fidelity/` package | Clean architectural separation between fixed-layout text replacement and semantic reflow | Cramming coordinate locking into `DocumentLayoutEngine` would violate Single Responsibility and break existing reflow logic |
| Strict fail-fast without fixture fallback | Prevents production data corruption when host lacks conversion tools | Silently copying a 2-page sample fixture on a real 19-page file creates completely corrupted outputs |
| Deep XML traversal for DrawingML whiteout | Eliminates printed text ghosting in shapes, textboxes, and canvas elements | Only whitening `doc.paragraphs` misses all callout boxes and diagram text in Word documents |
