# Implementation Plan: Table Merged-Cell Occupancy Grid Layout, Single-Pipeline Architecture, and Math Root Stroke Deduplication

**Branch**: `009-table-and-math-layout-fixes` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-table-and-math-layout-fixes/spec.md`

## Summary

This plan resolves the two critical rendering defects (P0) and architectural debts (P1) highlighted in the user review of commit `8b4aae0bf83c7bca7c45d60c668333c071dd3b87`:
1. **Math Root Deduplication (P0)**: Fix `RootNode` measurement in `chuviettay/layout/math_layout.py` to prevent duplicate character glyphs and vector strokes under radical expressions ($\sqrt{x^2+1}$).
2. **Table 2D Occupancy Grid (P0)**: Introduce a canonical `grid[row][col]` matrix in `TableLayoutEngine` and document layout rendering, ensuring cells with `rowspan > 1` reserve their full vertical span so subsequent rows find the first vacant column instead of resetting to column 0.
3. **Unified Table Layout Architecture (P1)**: Consolidate table geometry calculation, row height accumulation, pagination slicing, and border stroke generation into `TableLayoutEngine` as the single source of truth. `DocumentLayoutEngine.render()` consumes `TableLayoutData` directly without re-implementing layout logic.
4. **Test Suite Expansion & CI Hardening (P1)**:
   - Add regression tests in `tests/test_math_layout.py` asserting non-empty glyphs and positive stroke counts (`total_glyph_strokes > 0`) for math expressions.
   - Add regression tests in `tests/test_table_layout.py` asserting exact cell coordinates, non-overlapping bounds, and interior border suppression for `colspan=2`, `rowspan=2`, and combined spans.
   - Guard headless Tkinter imports in `tests/test_gui_document.py` to eliminate collection errors when `tkinter` is unavailable.
5. **Real-World Sample Verification (P2)**: Validate end-to-end `.xopp` export from `sample.txt`, `sample.md`, and `sample.docx`.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.13)

**Primary Dependencies**: Standard library (`math`, `dataclasses`, `typing`, `enum`), `pytest>=8.0.0`, optional document dependencies (`python-docx`, `markdown-it-py`)

**Storage**: Single gzip-compressed XML file (`*.xopp`), bank file (`*.json.gz`)

**Testing**: `pytest` with `pytest-timeout`, unit tests, regression geometry assertions

**Target Platform**: Windows, Linux (Ubuntu), macOS

**Project Type**: Desktop GUI application and CLI document converter (`chuviettay`)

**Performance Goals**: Table layout execution $< 50\text{ms}$ for tables up to 100 rows; math layout execution $< 5\text{ms}$ per equation; zero memory leaks during page streaming

**Constraints**: Single source of truth for table layout; zero duplicate glyphs/strokes; deterministic multi-page pagination; zero collection-time crashes in CI

**Scale/Scope**: ~3 core layout modules (`chuviettay/layout/math_layout.py`, `chuviettay/layout/table_layout.py`, `chuviettay/layout/engine.py`), ~3 test files (`tests/test_math_layout.py`, `tests/test_table_layout.py`, `tests/test_gui_document.py`), and test fixtures (`tests/fixtures/`)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | Clear single source of truth for table layout; self-documenting occupancy grid | ✅ PASS — Eliminates duplicated cell math in `DocumentLayoutEngine.render()` in favor of centralized `TableLayoutEngine` |
| **II. Simple Architecture (KISS & YAGNI)** | Standard 2D grid matrix `grid[row][col]`; clean list initialization in math root | ✅ PASS — Direct, standard algorithmic pattern; no speculative complexity |
| **III. Comprehensive Automated Testing** | Automated regression tests verifying exact stroke counts, non-overlapping bounds, and border suppression | ✅ PASS — Replaces shallow width checks with rigorous glyph/stroke assertions; fixes test collection crashes |
| **IV. Loose Coupling & High Cohesion** | `DocumentLayoutEngine` delegates table layout to `TableLayoutEngine` via structured `TableLayoutData` | ✅ PASS — High cohesion in `TableLayoutEngine`; clean interface decoupling in renderer |

---

## Project Structure

### Documentation (this feature)

```text
specs/009-table-and-math-layout-fixes/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 technical decisions & rationale
├── data-model.md        # Phase 1 entities & validation rules
├── quickstart.md        # Phase 1 runnable validation guide
├── contracts/           # Phase 1 interface contracts
│   ├── table-layout-contract.md
│   └── math-root-contract.md
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
chuviettay/
├── layout/
│   ├── math_layout.py         # Fix RootNode: initialize empty glyphs/strokes, append shifted radicand
│   ├── table_layout.py        # 2D occupancy grid, unified layout_table(), slice_page(), border suppression
│   └── engine.py              # Refactor table rendering to consume TableLayoutData directly
└── math/
    └── ast.py                 # Math AST structures (Root, Fraction, etc.)

tests/
├── test_math_layout.py        # Add root deduplication & TextNode handwriting stroke assertions
├── test_table_layout.py       # Add colspan, rowspan, occupancy grid, and border suppression tests
├── test_gui_document.py       # Guard Tkinter imports before conftest.is_tk_usable() check
└── fixtures/
    ├── sample.txt             # Plain text sample with Vietnamese diacritics & empty lines
    ├── sample.md              # Markdown sample with tables, lists, and math expressions
    └── sample.docx            # Word sample with merged tables and equations
```

**Structure Decision**: Standard package layout. Core fixes are localized strictly to the layout subsystem (`chuviettay/layout/`) with corresponding regression tests in `tests/`.

---

## Complexity Tracking

No violations to justify. The changes reduce architectural complexity by eliminating duplicated layout calculations in `DocumentLayoutEngine` and adopting standard 2D grid algorithms for table cells.
