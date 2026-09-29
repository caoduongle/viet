# Implementation Plan: Document IR, Multi-Format Importers (TXT/MD/DOCX), Layout Engine, and Math/Table Rendering

**Branch**: `007-document-ir-and-importers` | **Date**: 2026-09-29 | **Spec**: [specs/007-document-ir-and-importers/spec.md](file:///d:/viet/app/specs/007-document-ir-and-importers/spec.md)

**Input**: Feature specification from `/specs/007-document-ir-and-importers/spec.md` and user architectural proposal.

---

## Summary

Decouple the current linear `str -> Writer.token -> composer -> .xopp` pipeline into a modern, structured architecture:
1. **Document IR (`chuviettay/document/ir.py`)**: Define strongly typed block and inline dataclasses (`Document`, `Paragraph`, `Heading`, `ListBlock`, `Table`, `MathBlock`, `Text`, `MathInline`, `Symbol`).
2. **Multi-Format Importers (`chuviettay/importer/`)**: Support plaintext (`TxtImporter`), Markdown with GFM tables and math syntax (`MarkdownImporter`), and Word documents (`DocxImporter`) using `iter_inner_content()` and OMML extraction. Maintain zero core dependencies with `[project.optional-dependencies] docs = [...]`.
3. **Layout Engine (`chuviettay/layout/`)**: Implement independent measurement and layout for document flow, tables (multi-border stroke rendering: `NONE`, `OUTER`, `ALL`, `HORIZONTAL`), and math formulas (baseline alignment, fraction bars, root signs).
4. **Bank Schema v3 (`chuviettay/model/bank_schema.py`)**: Introduce `"symbols": {}` in the bank model with automated migration from v2.
5. **Golden-Master Parity**: Preserve `ctl.write_text(...)` and `chuviettay/model/composer.py` to ensure 100% SHA-256 byte parity on legacy benchmarks.

---

## Technical Context

**Language/Version**: Python >= 3.10 (tested and verified across Python 3.10, 3.11, 3.12, 3.13 on Windows and Ubuntu)

**Primary Dependencies**:
- Core handwriting: `dependencies = []` (zero external dependencies)
- Optional document extras: `[project.optional-dependencies] docs = ["markdown-it-py>=3.0.0", "mdit-py-plugins>=0.4.0", "python-docx>=1.1.0"]`
- Dev/Test: `pytest>=8`, `pyinstaller>=6`, `ruff`

**Storage**:
- Bank storage: Gzip-compressed JSON file (`.json.gz`), Schema v3 format with `"symbols": {}`
- Output storage: Xournal++ document format (`.xopp`), gzip-compressed XML

**Testing**: `pytest` test suite with SHA-256 golden-master regression tests, synthetic bank fixtures, Tk probe resilient testing, parameterized parser test fixtures

**Target Platform**: Cross-platform (Windows, Linux, macOS) CLI and Tkinter GUI desktop application

**Project Type**: Hybrid desktop application and CLI tool with reusable core library modules

**Performance Goals**:
- Document import and layout under 2 seconds for a 50-page document
- Memory footprint remaining constant with streaming page emission
- Interactive UI response during file loading and structure diagnostics

**Constraints**:
- Absolute zero external dependencies for core handwriting generation
- 100% byte-for-byte SHA-256 hash compatibility for `ctl.write_text(...)` against `tests/test_golden_master.py`
- HTML parsing explicitly disabled (`html=False`) in Markdown import to prevent script injection
- Missing glyphs/symbols must reserve non-zero typographic bounding boxes (`[ symbol ]`) to prevent formula or table column collapse

**Scale/Scope**:
- 6 User Stories (P1 to P3)
- 16 Functional Requirements (FR-001 to FR-016)
- 8 Success Criteria (SC-001 to SC-008)
- 7 Implementation Phases

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Verification / Justification |
| :--- | :--- | :--- | :--- |
| **I. Maintainability & Code Cleanliness** | Self-documenting code, clear module organization, documented design decisions | **PASS** | Clean separation into `document/`, `importer/`, `math/`, `layout/` packages with typed dataclasses and detailed docstrings. |
| **II. Simple Architecture (KISS & YAGNI)** | Direct solutions, no speculative features, external dependencies justified | **PASS** | Core remains zero-dependency; document parsers isolated as optional extras. Importers only parse what is rendered. |
| **III. Comprehensive Automated Testing** | Automated tests for all core logic, deterministic, CI automated, regressions tested | **PASS** | Every new importer, layout module, and schema migration has dedicated unit test suites; existing golden-master tests protected. |
| **IV. Loose Coupling & High Cohesion** | Interaction through public contracts, high internal cohesion, no circular dependencies | **PASS** | Importers depend only on Document IR; Layout engine depends on Document IR and Bank; Controller serves as single coordinator. |

---

## Project Structure

### Documentation (this feature)

```text
specs/007-document-ir-and-importers/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output: Technical decisions & research
├── data-model.md        # Phase 1 output: IR, Math AST, Layout & Schema v3 models
├── quickstart.md        # Phase 1 output: Step-by-step validation guide
├── contracts/           # Phase 1 output: Public API contracts
│   ├── importer_api.md
│   ├── controller_api.md
│   └── cli_api.md
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── document/            # Document IR
│   ├── __init__.py
│   └── ir.py            # Node, Block, Inline, Document, Paragraph, Heading, Table, Math
├── importer/            # Multi-format document importers
│   ├── __init__.py
│   ├── base.py          # BaseImporter, ImportResult
│   ├── dependency.py    # Optional dependency checker & exceptions
│   ├── txt_importer.py  # Plaintext parser
│   ├── markdown_importer.py # Markdown parser (markdown-it-py, GFM, math)
│   └── docx_importer.py # Word parser (python-docx, iter_inner_content, OMML)
├── math/                # Mathematical AST & parsing
│   ├── __init__.py
│   ├── ast.py           # MathNode, Fraction, Superscript, Subscript, Root
│   └── parser.py        # LaTeX math tokenizer & AST generator
├── layout/              # Typographic layout & vector stroke engine
│   ├── __init__.py
│   ├── metrics.py       # Size, TypographicMetrics, PositionedGlyph, PositionedStroke
│   ├── engine.py        # DocumentLayoutEngine, pagination, margins
│   ├── table_layout.py  # Table column measurement, cell wrapping, borders
│   ├── math_layout.py   # Baseline alignment, fraction bars, radical lines
│   └── stream.py        # PageBuffer for streaming XOPP page generation
├── model/
│   ├── bank.py          # Updated with symbols attribute and lookup
│   ├── bank_schema.py   # Schema v3 validation and v2->v3 migration
│   ├── composer.py      # Preserved legacy write_document for golden-master
│   ├── writer.py        # Preserved core token assembler
│   └── xopp.py          # XML helpers and stroke formatting
├── controller/
│   ├── app_controller.py# Extended with write_document() and import_document()
│   └── results.py       # Extended WriteResult with missing_symbols
├── view/
│   └── write_tab.py     # "Mở tài liệu...", structural stats, missing symbols
├── cli.py               # --format {auto,txt,md,docx} extension auto-detection
└── config.py

tests/
├── test_importer_txt.py
├── test_importer_markdown.py
├── test_importer_docx.py
├── test_table_layout.py
├── test_math_layout.py
├── test_schema_v3.py
├── test_document_pipeline.py
└── test_golden_master.py (existing, 100% pass guaranteed)
```

**Structure Decision**:
Organize new modules into four clean domain packages (`chuviettay/document/`, `chuviettay/importer/`, `chuviettay/math/`, `chuviettay/layout/`) to ensure high cohesion, loose coupling, and clean testability without cluttering the existing `model/` package.

---

## Implementation Roadmap (7 Phases)

- **Phase 1: Foundation (Document IR & Plaintext Importer)**
  - Implement `chuviettay/document/ir.py` with dataclass nodes.
  - Implement `chuviettay/importer/base.py` and `chuviettay/importer/txt_importer.py`.
  - Wire `ctl.write_document(...)` alongside existing `ctl.write_text(...)`.
  - Verify `test_golden_master.py` passes 100%.

- **Phase 2: Bank Schema v3 & Symbol Infrastructure**
  - Update `chuviettay/model/bank_schema.py` to `CURRENT_VERSION = 3` with `"symbols": {}`.
  - Implement `_migrate_v2_to_v3()` and register in `_MIGRATORS`.
  - Update `merge_bank_dicts()` in `chuviettay/model/bank.py` to merge `symbols` across concurrent processes without data loss.
  - Update `Bank.add_sample()` and `learning.py` to support learning missing symbols from `_thieu.xopp`.
  - Add tests in `tests/test_schema_v3.py`.

- **Phase 3: Markdown Importer & Optional Dependency Handling**
  - Implement `chuviettay/importer/dependency.py` for graceful dependency guards (`OptionalDependencyError`).
  - Implement `chuviettay/importer/markdown_importer.py` (`markdown-it-py`, GFM tables, math, HTML sanitized and stripped from stroke pipeline).
  - Update `pyproject.toml` with `[project.optional-dependencies] docs = [...]`.
  - Add tests in `tests/test_importer_markdown.py`.

- **Phase 4: Math Engine (AST, Pure-Python LaTeX Parser & Baseline Layout)**
  - Implement `chuviettay/math/ast.py` and pure-Python `chuviettay/math/parser.py` (zero external TeX binaries, max depth guard 10).
  - Implement `chuviettay/layout/math_layout.py` with baseline alignment, minimum font scale 0.5x, and fraction/radical stroke generation.
  - Implement missing symbol placeholder bounding boxes (`[ symbol ]`) to prevent formula distortion.
  - Add tests in `tests/test_math_layout.py`.

- **Phase 5: Table Engine (Column Sizing & Multi-Border Strokes)**
  - Implement `chuviettay/layout/table_layout.py` with column width distribution, cell text wrapping, and jagged row padding.
  - Implement stroke generation for border modes (`NONE`, `OUTER`, `ALL`, `HORIZONTAL`).
  - Implement row-level table page breaking, with line-split fallback for oversized cells taller than page height.
  - Add tests in `tests/test_table_layout.py`.

- **Phase 6: DOCX Importer & OMML Translation**
  - Implement `chuviettay/importer/docx_importer.py` using `iter_inner_content()` with fallback iteration over `doc.element.body` for older `python-docx` versions.
  - Extract OMML equations (`m:oMath`, `m:f`, `m:sSup`, `m:rad`) to `MathNode` AST.
  - Capture unsupported elements (images, SmartArt) into `ImportResult.unsupported`.
  - Add tests in `tests/test_importer_docx.py`.

- **Phase 7: GUI, CLI, Streaming Hardening & Architecture Guard**
  - Update `chuviettay/view/write_tab.py`: change to "Mở tài liệu...", add structural summary display, separate missing words and missing symbols.
  - Update `chuviettay/cli.py`: add `--format {auto,txt,md,docx}` with extension auto-detection.
  - Implement streaming `PageBuffer` in `chuviettay/layout/stream.py` for multi-page documents.
  - Update `tests/test_architecture.py` to enforce strict import boundaries for `document/`, `importer/`, `layout/`, and `math/`.
  - Execute full regression verification: lint (`ruff check .`), tests (`pytest`), and build (`PyInstaller`).

---

## Complexity Tracking

*No constitutional violations identified. Design adheres to KISS, YAGNI, Loose Coupling, and Zero Core Dependencies.*
