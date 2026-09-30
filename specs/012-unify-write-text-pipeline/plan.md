# Implementation Plan: Unify Direct Text Input into Document IR Pipeline & Margin Validation

**Branch**: `012-unify-write-text-pipeline` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-unify-write-text-pipeline/spec.md`

---

## Summary

Unify the text rendering pipeline across the application by routing direct text entry in `AppController.write_text()` through the Document IR architecture (`TxtImporter` $\to$ `DocumentLayoutEngine` $\to$ `PageBuffer` $\to$ `.xopp`). This ensures that paper size, orientation, content margins, and native background tags apply universally to all text inputs (GUI direct typing/pasting, CLI `-t`, CLI `-f`, and API calls). In addition, enforce strict margin boundary checks in `WriteOptions.validate()` to reject margin sums that exceed paper dimensions, and fortify GUI regression tests.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested across Python 3.10, 3.11, 3.12, 3.13)

**Primary Dependencies**: Standard library (`math`, `re`, `dataclasses`, `gzip`, `xml.etree.ElementTree`, `tkinter`)

**Storage**: Gzip-compressed XML (`.xopp` format) and gzip-compressed JSON (`.json.gz` sample banks)

**Testing**: `pytest` (unit, integration, CLI, architecture, and golden master suites)

**Target Platform**: Cross-platform (Windows, Linux, macOS)

**Project Type**: Desktop GUI app and CLI utility

**Performance Goals**: Sub-second text layout and streaming page generation with bounded memory usage

**Constraints**: Zero regression on existing 355 tests; 100% adherence to layered architecture boundaries (`chuviettay/document/` remains decoupled from `model/`, `view/`, `controller/`)

**Scale/Scope**: Unified pipeline handling small notes up to large multi-page notebooks

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Maintainability & Code Cleanliness**: PASS. Replaces divergent duplicate layout paths with a single unified layout engine.
- **Principle II: Simple Architecture (KISS & YAGNI)**: PASS. Reuses existing `TxtImporter` and `DocumentLayoutEngine` without creating redundant wrappers or speculative abstractions.
- **Principle III: Comprehensive Automated Testing**: PASS. All changes covered by unit tests (`test_page_format.py`), integration tests (`test_document_pipeline.py`), CLI tests (`test_cli_format.py`), and GUI tests (`test_gui_document.py`).
- **Principle IV: Loose Coupling & High Cohesion**: PASS. Preserves clean separation between document IR, layout engine, and application controller.

---

## Project Structure

### Documentation (this feature)

```text
specs/012-unify-write-text-pipeline/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Technical research and architecture decisions
├── data-model.md        # Domain models and validation constraints
├── quickstart.md        # Runnable validation scenarios
├── contracts/
│   └── controller-contract.md # Public API contracts
└── tasks.md             # Implementation tasks (generated via /speckit-tasks)
```

### Source Code Layout

```text
chuviettay/
├── controller/
│   └── app_controller.py   # AppController.write_text() unified into DocumentLayoutEngine
├── document/
│   └── page_format.py      # PaperSize, PageFormat, PageBackground, parse_length
├── importer/
│   └── txt_importer.py     # TxtImporter converting plain text to Document IR
├── layout/
│   ├── engine.py           # DocumentLayoutEngine coordinates layout, pagination & background
│   └── stream.py           # PageBuffer streams pages to .xopp
├── model/
│   ├── composer.py         # WriteOptions.validate() with margin bound checks
│   └── xopp.py             # page_open_xml generating native XML tags
└── view/
    └── write_tab.py        # GUI WriteTab invoking ctl.write_text() on direct input

tests/
├── test_cli.py             # CLI input tests
├── test_cli_format.py      # CLI paper and background tests
├── test_document_pipeline.py # Document pipeline integration tests
├── test_gui_document.py    # GUI document and direct text tests
└── test_page_format.py     # Unit tests for PageFormat and margin validation
```

**Structure Decision**: Retains existing modular layout and single-project architecture.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | Direct, minimal implementation using existing abstractions |
