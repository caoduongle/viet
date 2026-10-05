# Phase 0 Research: P1 — Core Foundation & Ecosystem Harmonization

**Feature**: `019-core-foundation`  
**Date**: 2026-10-05  

## Research Topics & Decisions

### 1. Q3 — Schema v4 Single Source of Truth & Documentation Alignment

- **Decision**: Standardize exclusively on **Schema Version 4** across all codebase locations, documentation, migration scripts, and synthetic data generators.
- **Rationale**:
  - Phase 0 (item D1) bumped `bank_schema.CURRENT_VERSION` to 4 and introduced category-qualified tombstones (`<cat>:<label>`).
  - Currently, docstring headers in `chuviettay/model/bank_schema.py` still mention `schema_version = 2`, `scripts/gen_synthetic_bank.py` generates v2 dictionaries, and `scripts/migrate_letter_bank.py` leaves `schema_version` implicit or unversioned.
  - Setting `schema_version = 4` across all components ensures no tool inadvertently produces legacy schema dictionaries that require runtime migration.
- **README Rectification**:
  - In `README.md` (around line 100), the description stating *"Ngoài bảng chữ cái và chữ số, lưới bao gồm 14 cụm…"* is incorrect.
  - In reality, `export_letter_grid` produces 77 cells containing 29 letters (x2 case = 58) + 14 vowel/consonant digraphs + 5 tone marks, with **0 digits**.
  - Digits and punctuation are intentionally learned via the minimal essentials buttons in the GUI Teach tab (`MINIMAL_DIGITS`, `MINIMAL_PUNCT`). `README.md` will be updated to reflect this accurate separation of concerns.
- **Visual Artifacts (`docs/img/after_fix.png`)**:
  - `after_fix.png` was created at commit `4b71523` (prior to the fix for dấu nặng in `d17a142`), and was rendered from the author's private, authentic handwriting bank (which is not stored in the repository).
  - Regenerating this image using a synthetic bank would degrade visual authenticity.
  - Decision: Leave `after_fix.png` as-is and explicitly document in the handover report that the repository owner should re-render the image using their authentic private bank.

---

### 2. Q2 — Real-Path Test Convergence & Legacy Composer Cleanup

- **Decision**: Migrate all 12 test invocations from `compose_document` to the production engine (`DocumentLayoutEngine` / `AppController.write_text`), verify test invariants, and prune deprecated functions (~150 lines) from `chuviettay/model/composer.py` along with `tests/test_golden_master.py`.
- **Rationale**:
  - The real production path (`DocumentLayoutEngine` generating A4 595.28 x 841.89 pt pages) is now guarded by `tests/test_golden_master_real_path.py` (established in Step 0).
  - The legacy `composer.write_document` and `composer.compose_document` generate obsolete non-standard pages (598 x 200 pt) and were marked `[DEPRECATED]`.
  - Audited calls:
    - 10 in `tests/test_composer.py`
    - 2 in `tests/test_letter_assembly_quality.py`
    - 1 in `tests/test_golden_master.py`
  - Invariants checked in tests (minimum stroke clearance >= 0.8x pen thickness, contour pair gap, bounding box overlap <= 10%, auto-xh scaling) remain identical and valid when executed against `DocumentLayoutEngine`.
- **Public API Preservation**:
  - Core dataclasses `WriteOptions` and `WriteResult`, as well as layout constants (`DEFAULT_LINE`, `DEFAULT_WIDTH`, `DEFAULT_SPACE`), are imported by `chuviettay.controller.app_controller`, `chuviettay.cli`, `chuviettay.view.write_tab`, and `chuviettay.fidelity.engine`.
  - These contracts will remain intact in `chuviettay.model.composer` to prevent breaking imports.

---

### 3. Q4 — Quantitative Acceptance Testing with Deterministic Synthetic Letters

- **Decision**: Provide an exportable synthetic bank generator `build_synthetic_letter_bank(seed: int = 42) -> dict` in `scripts/gen_synthetic_bank.py` and write an automated acceptance test in `tests/test_acceptance_metrics.py`.
- **Rationale**:
  - The repository's minimal test bank (`tests/data/kho_mau_tong_hop.json.gz`) contains only 125 samples without `letters`, covering 0 of the 38 words in `tests/data/accept_sample.txt`.
  - Private user archives cannot be stored in version control or CI runners.
  - A deterministic synthetic letter bank provides:
    - 29 Vietnamese letters (lowercase + uppercase)
    - 4 loan letters (f, j, w, z, lowercase + uppercase)
    - 5 standalone tone marks
    - Calibrated target x-height of 7.94 pt, pen thickness of 1.41 pt
    - Predictable geometric strokes with exact bounding boxes and baselines
- **Acceptance Thresholds**:
  - Using `tools/measure_ink.measure_ink_metrics(xopp_path)`:
    - `missing_count == 0` (100% of words in `accept_sample.txt` rendered)
    - `min_stroke_clearance_pen >= 0.8`
    - `max_bbox_overlap_pct <= 10.0`
    - `median_x_height` within `[7.15, 8.73]` pt (7.94 pt ± 10%)
    - `pen_to_xh_ratio` within `[0.15, 0.20]`
  - Docstring explicitly states this validates the *mechanical correctness of assembly and layout geometry*, not handwriting beauty.

---

### 4. F3 — Latin Alphabet Completeness in HW3 Practice Grid (f, j, w, z)

- **Decision**: Add uppercase and lowercase `f, F, j, J, w, W, z, Z` (+8 cells) to the `hw3` grid generation in `chuviettay/controller/app_controller.py` and `chuviettay/model/xopp.py`. Enforce alphabetic validation in `chuviettay/model/learning.py`.
- **Rationale**:
  - Technical terms, proper names, and foreign loanwords (e.g. `wifi`, `win`, `jazz`, `json`) require these 4 Latin characters to avoid 0-stroke assembly failures.
  - Total cells in grid expands from 77 (29x2 + 14 + 5) to 85 (33x2 + 14 + 5).
  - `parse_learn_file` in `chuviettay/model/xopp.py` uses dynamic cell bounding box coordinate calculation `col = (x - MXT) // CW`, `row = (y - MYT) // CH`, and text tag matching. It handles both 77-cell and 85-cell layouts seamlessly.
  - In `learning.py`, check `r.label.isalpha()` before adding to `bank.letters` to prevent single-character punctuation or symbols from accidentally entering the letter bank.

---

### 5. F4 — Standard OS User Data & Log Discovery for Pip Installations

- **Decision**: Update `chuviettay/paths.py` with hierarchical bank resolution:
  1. `--bank <path>` (explicit CLI/GUI parameter)
  2. Local/portable: if `chu_cua_ban.json.gz` exists in `app_base_dir()`, use it
  3. OS user data directory:
     - Windows: `%APPDATA%\chuviettay\chu_cua_ban.json.gz`
     - macOS: `~/Library/Application Support/chuviettay/chu_cua_ban.json.gz`
     - Linux: `$XDG_DATA_HOME/chuviettay/chu_cua_ban.json.gz` (fallback `~/.local/share/chuviettay/chu_cua_ban.json.gz`)
- **Rationale**:
  - When installed via `pip install`, `app_base_dir()` resolves to `<python>/site-packages/`, which is write-protected for standard users and lacks persistent user bank storage.
  - Resolving to OS standard locations allows `hw-note stats`, `hw-note write`, and GUI to run seamlessly out-of-the-box.
  - Standard library only (`os`, `sys`, `pathlib`). No external dependency like `platformdirs`.

---

### 6. F7 — Xournal++ Background Style Compliance

- **Decision**: Map background styles when exporting to `.xopp` XML:
  - `iso_graph` -> `isograph`
  - `iso_dotted` -> `isodotted`
  - `music` -> `staves`
  - Accept both canonical and legacy forms when reading XML.
- **Source Verification**:
  - Inspected official Xournal++ C++ source code: `PageTypeHandler.cpp` (`PageTypeHandler::getPageTypeFormatForString`) at master commit `9882ffaaf2`:
    ```cpp
    if (format == "plain") return PageTypeFormat::Plain;
    if (format == "ruled") return PageTypeFormat::Ruled;
    if (format == "lined") return PageTypeFormat::Lined;
    if (format == "staves") return PageTypeFormat::Staves;
    if (format == "graph") return PageTypeFormat::Graph;
    if (format == "dotted") return PageTypeFormat::Dotted;
    if (format == "isodotted") return PageTypeFormat::IsoDotted;
    if (format == "isograph") return PageTypeFormat::IsoGraph;
    ```
  - Unrecognized strings trigger a warning and fall back to `PageTypeFormat::Plain` (white page).
  - Mapping ensures custom rulings render correctly in native Xournal++.

---

### 7. CI — Pip Install Smoke Test & Benchmark Isolation

- **Decision**:
  - Add a dedicated CI step to `.github/workflows/ci.yml`: install wheel/source into a clean venv, execute `hw-note --help`, create a temporary bank, and run `hw-note stats`.
  - Exclude `-m "not benchmark"` from coverage test runs; run `-m benchmark` in an isolated step without coverage instrumentation.
- **Rationale**:
  - Directly validates F4 in CI.
  - Prevents coverage overhead from triggering timing threshold failures in benchmark tests.
