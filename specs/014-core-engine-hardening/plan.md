# Implementation Plan: Comprehensive Quality, Correctness, and Performance Hardening

**Branch**: `014-core-engine-hardening` | **Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-core-engine-hardening/spec.md` derived from the comprehensive code audit across `model/`, `layout/`, `math/`, `document/`, `importer/`, and `fidelity/`.

---

## Summary

This feature resolves verified defects L1–L14 and architectural suspicions R1–R10 across the entire handwriting generation pipeline. The implementation is executed in strict phases:
- **Phase 0**: Safety net test harness & local benchmark suite.
- **Phase 1 (v2.0.1)**: Digit and punctuation classification and backward-compatible lookup (`bank.digits`, `bank.punct`, `Writer.number`).
- **Phase 2 (v2.0.1)**: Truth and correctness fixes (accurate page counts, missing token calculations, HTML sanitizer removal, nested list parsing, DOCX run traversal, sample deduplication, symbol tombstones, symmetric quartile trimming, MVC decoupling).
- **Phase 3 (v2.1)**: Layout & geometry scaling invariants (proportional line height, math block scaling, stroke-based table measurement).
- **Phase 4 (v2.1)**: LaTeX parser and mathematical macro expansion (`^` and `_` inside `{}` at arbitrary depth, standard mathematical macro map).
- **Phase 5 (v2.1)**: Bank persistence performance (debounced 2s flush, background worker thread, atomic file write).
- **Phase 6 (v2.2 → v3.0)**: Fidelity mode redesign (PDF-first line extraction with MIT-licensed parser, safe process cleanup).
- **Phase 7**: GUI experience and options synchronization.
- **Phase 8**: Packaging, release readiness, and CI discipline.

---

## Technical Context

**Language/Version**: Python 3.10, 3.11, 3.12, 3.13 (Python 3.12 active in development environment)  
**Primary Dependencies**: `python-docx`, `markdown-it-py`, `lxml`, `pytest`, `pytest-timeout`, `ruff`, `pdfplumber` (MIT)  
**Storage**: `json.gz` with atomic temp write, thread-safe locking, and debounced background flushing  
**Testing**: `pytest`, `pytest-timeout` (425+ existing tests maintained at 100% pass rate)  
**Target Platform**: Cross-platform (Windows, Linux, macOS)  
**Project Type**: Python CLI utility and desktop application (Tkinter GUI)  
**Performance Goals**: <50ms interactive teaching latency for 1,500-word banks; <10s generation for 20-page documents  
**Constraints**: Zero regression on existing 425 tests; Strict MIT license preservation (zero AGPL dependencies); Golden Master updates only after manual inspection in Xournal++ for Group B changes  
**Scale/Scope**: Core engine codebase (`chuviettay/model/`, `chuviettay/layout/`, `chuviettay/math/`, `chuviettay/importer/`, `chuviettay/fidelity/`, `chuviettay/controller/`, `chuviettay/view/`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Plan Compliance Status | Notes |
| :--- | :--- | :--- | :--- |
| **I. Maintainability & Code Cleanliness** | Self-documenting code, eliminate technical debt, unified shared functions | ✅ **PASS** | Shared `classify_token` eliminates duplicate logic in `learn` and `teach_word`. |
| **II. Simple Architecture (KISS & YAGNI)** | Direct solutions, avoid premature abstractions or complex database shifts | ✅ **PASS** | Retains `json.gz` storage; introduces debounced background saving rather than premature SQLite schema v4. |
| **III. Comprehensive Automated Testing** | High automated test coverage, regressions reproduced before fixing | ✅ **PASS** | Phase 0 mandates red tests for all confirmed bugs L1–L14 before implementation. |
| **IV. Loose Coupling & High Cohesion** | Strict MVC layering, explicit boundaries, no cross-module private calls | ✅ **PASS** | Removes controller dependency from `layout/engine.py` (R7), verified by `test_architecture.py`. |
| **Quality Gates** | CI verification, 0 ruff errors, 100% test pass rate | ✅ **PASS** | All changes validated with `ruff check .` and `pytest -v --timeout=60`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/014-core-engine-hardening/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Technical research & decisions (/speckit-plan output)
├── data-model.md        # Entities & state transitions (/speckit-plan output)
├── quickstart.md        # Runnable verification guide (/speckit-plan output)
├── checklists/
│   └── requirements.md  # Specification quality checklist
├── contracts/           # Interface contracts
│   ├── bank-storage-contract.md
│   ├── importer-ir-contract.md
│   └── layout-engine-contract.md
└── tasks.md             # Implementation tasks (/speckit-tasks output)
```

### Source Code (repository root)

```text
chuviettay/
├── model/
│   ├── bank.py          # Bank storage, categorize digits/punct/words/symbols, tombstones, debounced save
│   ├── composer.py      # WriteOptions, WriteResult models
│   ├── learning.py      # classify_token, sample signature deduplication
│   ├── text_utils.py    # Symmetric tone mark quartile trimming
│   ├── writer.py        # Writer.number fallback lookup to words
│   └── xopp.py          # XML generation, escape pen attributes, context manager read
├── layout/
│   ├── engine.py        # DocumentLayoutEngine, scale-proportional line height, n_pages reporting
│   └── table_layout.py  # Table column measurement from stroke bounds, border jitter
├── math/
│   ├── parser.py        # Recursive row parser for nested {} superscripts/subscripts, macro expansion
│   └── layout.py        # Uniform eff_scale for math blocks and inline formulas
├── importer/
│   ├── markdown_importer.py  # Remove _sanitize_html, recursive nested list traversal
│   └── docx_importer.py      # Run children iteration (t, tab, br, ins), alignment preservation
├── fidelity/
│   ├── converter.py     # Safe Word COM cleanup, alert suppression, LibreOffice output move
│   ├── background.py    # Deep OpenXML whiteout for DrawingML/tables
│   └── engine.py        # FidelityLayoutEngine
├── controller/
│   └── app_controller.py # Controller bridging models and views
└── view/
    └── write_tab.py     # GUI options, error dialogs, training queue ergonomics

tests/
├── test_architecture.py # Layered architecture enforcement
├── test_docx_fidelity.py
├── test_cli_format.py
├── test_math_scaling.py
└── test_golden_master.py # Visual verification before constant update
```

---

## Phased Execution Strategy

### Phase 0: Test Safety Net & Benchmark Harness
- Implement dedicated regression tests reproducing L1–L14.
- Create benchmark script for bank serialization performance.
- Verify tests fail (red) for expected reasons while existing 425 tests remain green.

### Phase 1: Digits and Punctuation (L1) -> v2.0.1
- Implement unified `classify_token(token)` in `learning.py`.
- Update `add_sample` to route digits and punctuation to `bank.digits` and `bank.punct`.
- Update `Writer.number` to search `bank.digits` with fallback to `bank.words`.
- Add "Minimal Essentials" queue in GUI and CLI.

### Phase 2: Correctness & Truth Fixes (L2–L3, L7–L8, L10–L12, R7, R10) -> v2.0.1
- Calculate missing tokens by unique token counts, extract `n_pages` from `PageBuffer` (L2, L3).
- Remove `_sanitize_html` from `markdown_importer.py` to preserve `<` and `>` (L7).
- Implement recursive list traversal and `unsupported` tracking in `markdown_importer.py` (L8).
- Traverse run children (`w:t`, `w:tab`, `w:br`, `w:ins`) in `docx_importer.py` (L10).
- Add sample signature deduplication (`_sample_signature`) on `add_sample` (L11).
- Add tombstones for `symbols`, `digits`, `punct` in `Bank.drop_symbol` (L12).
- Fix symmetric percentile trimming for tone marks in `text_utils.py` (L13).
- Decouple `layout/engine.py` from controller, import only `model.composer` (R7).
- Fix `read_xopp` context manager, escape pen XML attributes, update README test counts (R10).

### Phase 3: Layout & Geometry Scaling Invariants (L4, L5, L6, R8, R9) -> v2.1
- Merge consecutive inline text spans when followed by punctuation (L6).
- Implement scale-proportional default line height: `base_line_h * opts.scale` (L4).
- Apply unified `eff_scale` across math blocks and body text (L5).
- Measure table columns from actual stroke bounding boxes (`calc_text_bounds`) (R8).
- Calculate font height from stroke bounding boxes rather than fixed `xh` (R9).
- Apply subtle jitter to table border strokes matching `opts.jitter` and `opts.seed`.
- **Checkpoint**: Visual inspection in Xournal++ before updating golden master constants.

### Phase 4: LaTeX Formulas & Macro Expansion (L9) -> v2.1
- Unify formula row parsing (`parse_row`) across root and `{}` expressions (L9).
- Expand LaTeX macro table (`\cdot`, `\to`, `\forall`, `\exists`, `\partial`, `\nabla`, `\left`, `\right`, Greek letters).
- Bound recursion depth to 32 to prevent stack overflow.

### Phase 5: Bank Performance & Debounced Persistence (L14) -> v2.1
- Implement debounced deferred saving (2-second idle window, tab change, window close).
- Move compression and disk writes to a background worker thread with atomic tempfile replacement.
- Optimize compression level (`compresslevel=5`) for interactive saves.

### Phase 6: Fidelity PDF-First Redesign (R1–R6) -> v2.2 → v3.0
- Re-architect Fidelity Mode to parse intermediate PDF per-line via `pdfplumber` (MIT).
- Neutralize printed text via white overlay bounding boxes in background PDF.
- Cache tool availability checks to eliminate repeated Word COM startups.

### Phase 7 & 8: GUI Polish & Technical Discipline
- Sync GUI options (`lined`, `iso_dotted`, paper sizes) with CLI flags.
- Update `pyproject.toml` dependencies (`pytest-timeout`, `ruff`, Python 3.13 classifier).
- Verify CI workflows and git hygiene.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| *None* | All designs strictly comply with Constitution principles | N/A |
