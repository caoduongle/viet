# Implementation Plan: Number Typography and CI Fallback Hardening

**Branch**: `047-number-typography-ci-fix` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/047-number-typography-ci-fix/spec.md`

## Summary

This plan resolves the three automated test failures observed in Continuous Integration (`test_minus_and_percent_digit_normalization`, `test_decimal_number_spacing_harmony`, `test_measure_text_width_number_sync`).
The technical approach hardens `Writer.number()` and `Writer.measure_text_width()` with native vector glyph fallbacks for missing numeric operators (`-`, `%`), decouples decimal separator advance from sentence-level whitespace by using optical glyph bounding widths, and updates `scripts/gen_synthetic_bank.py` to regenerate `tests/data/kho_mau_tong_hop.json.gz` with complete, properly calibrated punctuation samples.

## Technical Context

**Language/Version**: Python 3.10+ (compatible with Python 3.10 through 3.12, and Pyodide WebAssembly runtime).

**Primary Dependencies**: Standard library (`math`, `re`, `gzip`, `json`), `pytest`, `pytest-timeout`. Zero external graphics or font dependencies.

**Storage**: Gzip-compressed JSON bank format (`kho_mau_tong_hop.json.gz`) adhering to schema v4.

**Testing**: `pytest`, `pytest tests/test_number_fraction_typography.py`, `pytest tests/test_system_hardening_feature_046.py`.

**Target Platform**: Cross-platform (Windows, Linux, macOS) and browser Web Worker (Pyodide).

**Project Type**: Python core rendering library and web application engine.

**Performance Goals**: Sub-millisecond execution for single number layout (`< 0.5ms` per numeric token); zero noticeable overhead on document layout passes.

**Constraints**:
- Strict mathematical tolerances:
  - Minus vertical center: `abs(mid_y - (-0.45 * xh)) <= 0.15 * xh`
  - Decimal comma gap: `0.08 * xh <= gap_after_comma <= 0.14 * xh`
  - Measure vs render sync: `abs(measured_w - rendered_w) <= 0.05 * xh`
- Zero uncommitted file dependencies for automated testing.

**Scale/Scope**: Impacts core numeric rendering in `writer.py`, text fallback utilities in `text_utils.py`, test fixture data, and unit test verification.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Maintainability & Code Cleanliness**: PASS. Changes in `writer.py` and `text_utils.py` will be cleanly partitioned into dedicated helper logic with clear comments documenting the proportional geometric formulas (`0.10 * xh`, `0.45 * xh`).
- **Principle II: Simple Architecture (KISS & YAGNI)**: PASS. Reuses existing vector fallback patterns without adding complex external layout libraries or speculative typography systems.
- **Principle III: Comprehensive Automated Testing**: PASS. Solves the CI failure where tests failed on clean environments lacking uncommitted local assets. Ensures 100% test reproducibility.
- **Principle IV: Loose Coupling & High Cohesion**: PASS. Keeps numeric formatting cohesive within `Writer.number()` and advance calculation in `Writer.measure_text_width()` without mutating external application state.

## Project Structure

### Documentation (this feature)

```text
specs/047-number-typography-ci-fix/
├── plan.md              # This implementation plan
├── research.md          # Architectural decisions & research findings
├── data-model.md        # Entities, metrics, and typographic invariants
├── quickstart.md        # Verification scenarios and run commands
├── contracts/
│   └── number_typography_contract.md # API contracts & invariants
└── checklists/
    └── requirements.md  # Spec quality validation checklist
```

### Source Code (affected paths)

```text
chuviettay/
├── model/
│   ├── writer.py        # Writer.number(), Writer.measure_text_width(), get_char_advance_width()
│   └── text_utils.py    # get_vector_glyph_fallback() for '-' and '%'
scripts/
└── gen_synthetic_bank.py# Update punct definitions ('-', '%', calibrated ',') and regeneration logic
tests/
├── data/
│   └── kho_mau_tong_hop.json.gz # Regenerated synthetic bank fixture
├── test_number_fraction_typography.py # Verification of US1 and US2
└── test_system_hardening_feature_046.py # Verification of US3 and US4
```

## Implementation Strategy & Phases

### Phase 1: Vector Glyph Fallbacks for Numeric Operators
- Extend `get_vector_glyph_fallback()` in `chuviettay/model/text_utils.py` to handle `%` and ensure `-` complies with `0.45 * xh` centering.
- Update `Writer.number()` in `chuviettay/model/writer.py`:
  - When `ch == "-"` or `ch == "%"` and absent in bank, retrieve vector fallback glyph.
  - Normalize through `_normalize_digit_sample(sample, ch)`.
  - Do not record as `missing` when fallback is successfully supplied.
  - Route single `%` in `Writer.token()` consistently.

### Phase 2: Decoupled Optical Comma Advance
- In `Writer.number()` in `chuviettay/model/writer.py`:
  - For `ch in ",."`, calculate optical stroke width `glyph_w = max(xs) - min(xs)`.
  - Advance `x += p_gap + glyph_w + 0.10 * xh`.
  - Eliminate reliance on text-level `p_w` for decimal punctuation.

### Phase 3: Exact Measurement Synchronization
- In `Writer.measure_text_width()` and `Writer.get_char_advance_width()` in `chuviettay/model/writer.py`:
  - Synchronize comma advance in `NUMRE` branch to match optical `glyph_w + 0.10 * xh`.
  - Ensure fallback advance for `-` in `get_char_advance_width("-")` matches `Writer.number()` advance (`0.5 * xh`).

### Phase 4: Synthetic Bank Fixture Regeneration
- Update `scripts/gen_synthetic_bank.py` to add `-` and `%` samples and calibrated `,` stroke to `generate_synthetic_bank()`.
- Regenerate `tests/data/kho_mau_tong_hop.json.gz`.

### Phase 5: Comprehensive Verification
- Execute `quickstart.md` scenarios:
  1. `test_minus_and_percent_digit_normalization`
  2. `test_decimal_number_spacing_harmony`
  3. `test_measure_text_width_number_sync`
  4. Full `pytest` suite across the entire repository.
