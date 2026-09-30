# Implementation Plan: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Branch**: `015-docx-fidelity-hardening` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/015-docx-fidelity-hardening/spec.md`

---

## Summary

This plan resolves the Linux CI failure (`test_r6_converter_availability_caching`), hardens the Fidelity UX in the GUI by locking paper and background options when Fidelity mode is active, upgrades `WhiteoutBackgroundGenerator` to surgical ZIP/OpenXML text whitening (guaranteeing 100% byte-for-byte preservation of non-text assets such as images, charts, SmartArt, and shapes), secures PowerShell invocation by removing `shell=True`, and clarifies platform capabilities in documentation and error messages.

---

## Technical Context

**Language/Version**: Python 3.10+ (tested on Python 3.10, 3.11, 3.12, 3.13)  
**Primary Dependencies**: `zipfile`, `xml.etree.ElementTree` (standard library), `tkinter` / `ttk`, `pytest`  
**Storage**: Filesystem / temporary files (`.docx`, `.json`, `.pdf`, `.xopp`)  
**Testing**: `pytest`, `pytest-timeout`, `unittest.mock`  
**Target Platform**: Windows 10/11 (full Word COM Fidelity + GUI), Linux/macOS (Semantic mode + LibreOffice PDF background conversion + headless CI)  
**Project Type**: Desktop GUI (Tkinter) and CLI tool  
**Performance Goals**: Surgical whiteout completes in < 500ms for typical DOCX documents (< 100 pages); GUI mode switch latency < 50ms  
**Constraints**: Zero byte alterations on non-text OpenXML parts; 100% pass rate across all 472+ tests; no `shell=True` subprocess calls  
**Scale/Scope**: Targeted hardening across `chuviettay/fidelity/`, `chuviettay/view/`, `README.md`, and test suites  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Evaluation | Status |
|---|---|---|
| **I. Maintainability & Code Cleanliness** | Clear, self-documenting implementation with explicit rationale comments for XML namespaces and GUI state toggles. | ✅ PASS |
| **II. Simple Architecture (KISS & YAGNI)** | Uses standard library `zipfile` and `xml.etree.ElementTree` directly instead of adding new heavy XML/DOCX dependencies. Direct Win32 `CreateProcess` via `shell=False`. | ✅ PASS |
| **III. Comprehensive Automated Testing** | Automated tests added/updated for cross-platform cache consistency, GUI mode lock/unlock states, and zip part preservation. | ✅ PASS |
| **IV. Loose Coupling & High Cohesion** | `WhiteoutBackgroundGenerator` encapsulates XML text transformation; `WriteTab` encapsulates UI control state; `FidelityConverter` encapsulates external tool detection. | ✅ PASS |

*Constitution Check Result*: All gates pass without violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/015-docx-fidelity-hardening/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Technical decisions and trade-offs
├── data-model.md        # Entities, OpenXML parts, and UI state models
├── quickstart.md        # Validation scenarios and testing instructions
├── contracts/
│   └── fidelity-hardening-contract.md # API, GUI, and whiteout contracts
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
chuviettay/
├── fidelity/
│   ├── converter.py     # Fix is_word_available caching on non-Windows; remove shell=True
│   ├── background.py    # Native ZIP/OpenXML surgical text whitening
│   ├── extractor.py     # Clear error messaging when Word COM is unavailable
│   └── ...
├── view/
│   └── write_tab.py     # Add _on_mode_changed(), lock paper/bg controls in Fidelity mode
└── ...

tests/
├── test_fidelity_pdf_first.py # Verify cross-platform cache behavior (R6)
├── test_docx_fidelity.py      # Verify surgical whiteout and non-text part preservation
├── test_gui_write_tab.py       # Verify GUI mode locking and restoration
└── ...

README.md                # Clarify platform capability matrix (Word COM vs LibreOffice)
```

**Structure Decision**: Monorepo Python package layout adhering to existing `chuviettay` architecture. All changes modify existing modules without adding new directories or external libraries.

---

## Complexity Tracking

> *No constitutional violations. Direct, minimal-dependency solutions chosen throughout.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | N/A |
