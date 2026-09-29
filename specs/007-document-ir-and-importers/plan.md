# Implementation Plan: Document IR, Multi-Format Importers (TXT/MD/DOCX), Layout Engine, and Math/Table Rendering (Iteration 2)

**Branch**: `007-document-ir-and-importers` | **Date**: 2026-09-29 | **Spec**: [specs/007-document-ir-and-importers/spec.md](file:///d:/viet/app/specs/007-document-ir-and-importers/spec.md)

**Input**: Feature specification update from `/specs/007-document-ir-and-importers/spec.md` resolving 13 critical functional gaps across commits `33185d7` and `20ef69c`.

---

## Summary

Complete the transition from the legacy linear handwriting pipeline to a unified, extensible Document IR architecture:
1. **Math AST Handwritten Stroke Generation (P0 - Critical)**: Implement real glyph and stroke extraction for `TextNode` (algebraic variables and digits) and `SymbolNode` in `MathLayoutEngine`, bridging to `Writer.token()`, `Writer.number()`, and `Bank.symbols`, with fallback vector strokes for operators (`+`, `-`, `=`, `/`).
2. **Inline Math Single-Scale Coordinate Space (P0/P1)**: Standardize all typographic item coordinates to base bank units so that `_render_text_line()` scales inline math uniformly with surrounding text (`s = self.S * scale_mult`), eliminating quadratic double-scaling.
3. **Rich Table Cell Inlines & Alignments (P1)**: Refactor table cell rendering from plain string splitting to native `_layout_inlines()` execution, preserving `MathInline`, `Symbol`, and `LineBreak` inside cells; apply column alignments (`left`, `center`, `right`).
4. **Table Merged Cells (`colspan` & `rowspan`) (P1)**: Parse `w:gridSpan` and `w:vMerge` in `DocxImporter`, measure merged cells spanning multiple rows/columns, and suppress interior horizontal/vertical border strokes across merged cell regions.
5. **Unified Plaintext IR Pipeline & Paragraph Spacing (P1)**: Route `.txt` files through `TxtImporter` and Document IR in CLI/GUI while strictly retaining blank lines as vertical paragraph spacing, and preserving 100% byte-for-byte SHA-256 compatibility for `ctl.write_text()`.
6. **Streaming `PageBuffer` End-to-End (P1)**: Wire `PageBuffer` into `DocumentLayoutEngine.render()` to flush completed pages sequentially to disk for multi-page documents.
7. **DOCX Diagnostics & Strict Validation (P2)**: Log unsupported OMML elements (`m:m`, `m:nary`, `m:limLow`, `m:limUpp`, `m:func`, `m:bar`, `m:acc`, `m:groupChr`, `m:eqArr`) into `ImportResult.unsupported`; reject unknown file formats in `get_importer_for_path()` with `UnsupportedFormatError`; fix dependency install syntax typo (`pip install ".[docs]"`).

---

## Technical Context

**Language/Version**: Python >= 3.10 (verified across Python 3.10, 3.11, 3.12, 3.13 on Windows and Ubuntu)

**Primary Dependencies**:
- Core handwriting generation: `dependencies = []` (zero external dependencies)
- Optional document extras: `[project.optional-dependencies] docs = ["markdown-it-py>=3.0.0", "mdit-py-plugins>=0.4.0", "python-docx>=1.1.0"]`
- Dev/Test: `pytest>=8`, `pyinstaller>=6`, `ruff`

**Storage**:
- Bank storage: Gzip-compressed JSON file (`.json.gz`), Schema v3 format with `"symbols": {}`
- Output storage: Xournal++ document format (`.xopp`), gzip-compressed XML

**Testing**: `pytest` test suite with SHA-256 golden-master regression tests, synthetic bank fixtures, Tk probe resilient testing, parameterized parser test fixtures

**Target Platform**: Cross-platform (Windows, Linux, macOS) CLI and Tkinter GUI desktop application

**Constraints**:
- Absolute zero external dependencies for core handwriting generation
- 100% byte-for-byte SHA-256 hash compatibility for `ctl.write_text(...)` against `tests/test_golden_master.py`
- HTML parsing explicitly disabled (`html=False`) in Markdown import to prevent script injection
- Missing glyphs/symbols must reserve non-zero typographic bounding boxes (`[ symbol ]`) to prevent formula or table column collapse
- Interior borders must not be drawn through merged cells

**Scale/Scope**:
- 6 User Stories (P0 to P2)
- 26 Functional Requirements (FR-001 to FR-026)
- 13 Success Criteria (SC-001 to SC-013)
- 8 Implementation Phases

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Verification / Justification |
| :--- | :--- | :--- | :--- |
| **I. Maintainability & Code Cleanliness** | Self-documenting code, clear module organization, documented design decisions | **PASS** | Clean separation of math glyph synthesis, cell inlines, and streaming layout into modular functions with clear contracts. |
| **II. Simple Architecture (KISS & YAGNI)** | Direct solutions, no speculative features, external dependencies justified | **PASS** | Reuses existing `Writer` and `Bank` lookup mechanisms without introducing external font engines or TeX binaries. |
| **III. Comprehensive Automated Testing** | Automated tests for all core logic, deterministic, CI automated, regressions tested | **PASS** | Dedicated end-to-end regression tests for all 13 functional areas; golden master parity 100% preserved. |
| **IV. Loose Coupling & High Cohesion** | Interaction through public contracts, high internal cohesion, no circular dependencies | **PASS** | Importers produce Document IR; Layout Engine consumes Document IR; Bank provides glyph samples; Controller coordinates. |

---

## Project Structure

### Documentation (this feature)

```text
specs/007-document-ir-and-importers/
├── spec.md              # Feature specification (Iteration 2)
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

### Source Code (affected paths)

```text
chuviettay/
├── document/
│   └── ir.py            # TableCell (colspan, rowspan), Table (col_alignments)
├── importer/
│   ├── base.py          # get_importer_for_path(), UnsupportedFormatError
│   ├── dependency.py    # require_dependency() install syntax fix
│   ├── txt_importer.py  # Preserving empty lines as paragraph spacing
│   └── docx_importer.py # w:gridSpan, w:vMerge, OMML unsupported diagnostics
├── math/
│   ├── ast.py           # Math AST nodes
│   └── parser.py        # LaTeX tokenizer and AST builder
├── layout/
│   ├── engine.py        # Single-scale inline math, cell inlines & alignment, PageBuffer streaming
│   ├── math_layout.py   # MathLayoutEngine TextNode/SymbolNode stroke generation & baseline alignment
│   ├── table_layout.py  # Colspan/rowspan column sizing & interior border suppression
│   └── stream.py        # PageBuffer streaming XOPP page writer
├── controller/
│   ├── app_controller.py# write_document(), write_text(), import_document()
│   └── results.py       # WriteResult, WriteOptions
├── view/
│   └── write_tab.py     # "Mở tài liệu...", unified TXT loading, diagnostic display
└── cli.py               # CLI write --format, unified TXT routing, strict format validation

tests/
├── test_math_ast_strokes.py   # Math formula variable/number stroke generation tests
├── test_math_scaling.py       # Inline math single-scaling & heading tests
├── test_table_rich_inlines.py # Table cells with math, symbols, and linebreaks
├── test_table_merged_cells.py # Colspan & rowspan sizing and border suppression
├── test_table_alignments.py   # Left, center, right cell stroke alignments
├── test_txt_unified_pipeline.py# TXT IR pipeline and blank line preservation
├── test_page_buffer_stream.py # Streaming PageBuffer end-to-end verification
├── test_docx_omml_diagnostics.py# OMML unsupported reporting and warnings categorization
├── test_format_validation.py  # UnsupportedFormatError on invalid extensions
└── test_golden_master.py      # Golden master byte parity (100% pass)
```

---

## Implementation Roadmap (8 Phases)

- **Phase 1: Math AST Handwritten Stroke Generation (P0 ⭐ Critical)**
  - Update `MathLayoutEngine.measure()` in `chuviettay/layout/math_layout.py`:
    - For `TextNode(text)`: tokenize text; for digits use `writer.number()`, for letters/words use `writer.token()`.
    - Populate `PositionedGlyph` with generated strokes and accurate baseline-relative bounding boxes.
    - For missing words/digits, record in `self.missing_symbols` and reserve typography bounding box.
    - For `SymbolNode(sym)`: check `bank.symbols`, fallback to `writer.token()` / `bank.punct`, or generate vector strokes for operators (`+`, `-`, `=`, `/`).
  - Unit tests in `tests/test_math_ast_strokes.py`.

- **Phase 2: Inline Math Coordinate Standardization & Single-Scaling (P0/P1)**
  - Refactor `MathLayoutEngine` to measure items in normalized base bank units (`scale=1.0` or relative `scale_mult`).
  - In `DocumentLayoutEngine._layout_inlines()`, convert `MathLayoutItem` strokes to unscaled bank units.
  - In `DocumentLayoutEngine._render_text_line()`, apply uniform scaling `s = self.S * scale_mult * (1 + jitter)` across all text and math items.
  - Unit tests in `tests/test_math_scaling.py`.

- **Phase 3: Rich Table Cell Inlines & Column Alignments (P1)**
  - In `TableLayoutEngine` (`table_layout.py`), compute column widths taking into account inline elements.
  - In `DocumentLayoutEngine.render()`, refactor table cell rendering to call `_layout_inlines()` on each cell's block paragraphs instead of flattening to plain strings.
  - Apply `col_alignments` (`left`, `center`, `right`) when calculating cell text offset `start_x`.
  - Unit tests in `tests/test_table_rich_inlines.py` and `tests/test_table_alignments.py`.

- **Phase 4: Table Merged Cells (`colspan` & `rowspan`) (P1)**
  - Parse `w:gridSpan` (`colspan`) and `w:vMerge` (`rowspan`) in `DocxImporter._parse_table()`.
  - In `TableLayoutEngine.compute_column_widths()`, adjust width allocation for spanned cells.
  - In `TableLayoutEngine.layout_table()`, compute merged cell widths: $W = \sum_{k=col}^{col+colspan-1} col\_widths[k]$ and heights: $H = \sum_{r=row}^{row+rowspan-1} row\_heights[r]$.
  - In `TableLayoutEngine.generate_border_strokes()`, suppress interior horizontal and vertical lines crossing merged cells.
  - Unit tests in `tests/test_table_merged_cells.py`.

- **Phase 5: Unified Plaintext IR Pipeline & Blank Line Preservation (P1)**
  - In `TxtImporter` (`txt_importer.py`), preserve empty lines as empty paragraphs (`Paragraph(inlines=[])`).
  - In `DocumentLayoutEngine.render()`, render empty paragraphs as vertical paragraph spacing (`cur_y += self.line_h * 0.8`).
  - In `cli.py` and `write_tab.py`, route `.txt` files through `ctl.import_document()` and `ctl.write_document()`.
  - Guarantee `ctl.write_text()` remains unchanged and passes `tests/test_golden_master.py` with 100% SHA-256 parity.
  - Unit tests in `tests/test_txt_unified_pipeline.py`.

- **Phase 6: End-to-End Streaming `PageBuffer` (P1)**
  - In `DocumentLayoutEngine.render()`, integrate `with PageBuffer(out_path, page_w) as pb:`.
  - Whenever `new_page()` triggers, write the completed page XML to `pb.append_page(cur_page)` and clear `cur_page = []`.
  - Close and finalize the XOPP file atomically upon completion.
  - Unit tests in `tests/test_page_buffer_stream.py`.

- **Phase 7: DOCX Diagnostics, Strict Validation & Syntax Fix (P2)**
  - In `docx_importer.py`, detect unsupported OMML tags (`m:m`, `m:nary`, `m:limLow`, `m:limUpp`, `m:func`, `m:bar`, `m:acc`, `m:groupChr`, `m:eqArr`) and log into `ImportResult.unsupported`.
  - In `chuviettay/importer/base.py`, update `get_importer_for_path()` to raise `UnsupportedFormatError` for unrecognized extensions (`.pdf`, `.xlsx`, `.jpg`, `.zip`).
  - In `chuviettay/importer/dependency.py`, fix typo `pip install ".[ {extra} ]"` to `pip install ".[{extra}]"`.
  - Unit tests in `tests/test_docx_omml_diagnostics.py` and `tests/test_format_validation.py`.

- **Phase 8: Comprehensive Regression & Architecture Verification**
  - Run `ruff check .`
  - Run `pytest -v` across all test suites, verifying 100% pass on golden master and new regression suites.
