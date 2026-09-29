# Implementation Plan: Preserve Markdown Ordered List Start Numbering

**Branch**: `010-markdown-ordered-list-start` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-markdown-ordered-list-start/spec.md`

---

## Summary

When an ordered list in Markdown starts at an index other than 1 (e.g. `4. Item`) or is interrupted by an unindented block element (such as a table or paragraph), `markdown-it-py` assigns the starting index attribute to the `ordered_list_open` token (e.g. `attrGet("start") == 4`). `MarkdownImporter` currently ignores this token attribute and constructs `ListBlock(ordered=is_ordered, items=items)` defaulting `start=1`, which corrupts numbering in rendered output (`1. D, 2. E` instead of `4. D, 5. E`).

This plan extracts `start` safely from `ordered_list_open` in `MarkdownImporter`, passes `start=start` to `ListBlock`, and verifies end-to-end rendering and handwriting generation across uninterrupted, interrupted, and nested ordered lists without regressions.

---

## Technical Context

**Language/Version**: Python >= 3.10

**Primary Dependencies**: `markdown-it-py>=3.0.0`, `mdit-py-plugins>=0.4.0` (standard parser dependencies for Markdown import)

**Storage**: In-memory Document IR, serializing to compressed `.xopp` XML

**Testing**: `pytest>=8.0.0` with `pytest-timeout>=2.3.1`

**Target Platform**: Cross-platform (Windows, Linux, macOS)

**Project Type**: Desktop CLI & GUI application / Document Layout & Synthesis Engine

**Performance Goals**: Zero noticeable overhead during Markdown token parsing (< 1ms per list block)

**Constraints**:
- Must preserve backward compatibility with existing tests and callers
- Must handle missing, malformed, or string attribute types gracefully without crashing
- Must not alter bullet list behavior (`ordered=False` remains bullet `- `)

**Scale/Scope**: Tightly scoped fix in `chuviettay/importer/markdown_importer.py` and dedicated regression tests in `tests/test_markdown_importer.py` (or `tests/test_cli_format.py`).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Maintainability & Code Cleanliness**: PASS. The attribute extraction logic is encapsulated cleanly within `MarkdownImporter._process_tokens()` (or `import_text()`) with clear fallback defaults.
- **II. Simple Architecture (KISS & YAGNI)**: PASS. Reuses existing `ListBlock.start` and existing `DocumentLayoutEngine` prefix rendering (`f"{block.start + idx}. "`). No new abstractions, classes, or dependencies introduced.
- **III. Comprehensive Automated Testing**: PASS. Will add unit tests for `start` extraction (interrupted lists, custom starts, malformed attributes) and integration tests with rendering.
- **IV. Loose Coupling & High Cohesion**: PASS. Decoupled via `Document IR` contract (`ListBlock(ordered=True, start=int)`).

---

## Project Structure

### Documentation (this feature)

```text
specs/010-markdown-ordered-list-start/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── markdown-list-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
chuviettay/
├── document/
│   └── ir.py                     # Document IR dataclasses (ListBlock with start: int = 1)
├── importer/
│   └── markdown_importer.py      # Extract start from ordered_list_open and pass to ListBlock
└── layout/
    └── engine.py                 # DocumentLayoutEngine formatting f"{block.start + idx}. "

tests/
├── test_markdown_importer.py     # Unit tests verifying ListBlock.start extraction
└── test_cli_format.py            # Integration tests verifying CLI and rendered output
```

**Structure Decision**: Standard single package structure under `chuviettay/` and `tests/`.

---

## Complexity Tracking

*No violations of Constitution. Clean bugfix reusing existing IR fields and rendering logic.*
