# Feature Specification: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Feature Branch**: `015-docx-fidelity-hardening`  
**Created**: 2026-09-30  
**Status**: Draft  
**Input**: Comprehensive review of commit `00e1087ff20a7fc9b59c4f33432b0e475b681919`, resolving Linux CI failure (`test_r6_converter_availability_caching`), enforcing Fidelity UX mode locking in the GUI (`write_tab.py`), upgrading `WhiteoutBackgroundGenerator` to native ZIP/OpenXML surgical text whitening to guarantee preservation of complex document elements (charts, SmartArt, shapes, drawings), eliminating unnecessary `shell=True` in PowerShell invocations, and aligning documentation regarding platform capabilities (Windows Word COM vs LibreOffice).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Converter Availability Caching Across Platforms (Priority: P1) 🎯 MVP

As a developer running automated tests and continuous integration across Linux, macOS, and Windows, I need external tool availability checks (`is_word_available`) to cache their results consistently regardless of the operating system, so that CI test suites pass deterministically and the application avoids redundant platform probes.

**Why this priority**: Linux CI runs across all Python versions (3.10–3.13) are currently failing on `test_r6_converter_availability_caching` because the non-Windows early exit returns without writing to the cache attribute. Fixing this restores green CI builds across the entire repository.

**Independent Test**:
- Reset the converter cache.
- Call `is_word_available()` on Linux/macOS.
- Verify that `False` is returned and the cache state is explicitly set to `False` (not `None`).
- Call `is_word_available()` a second time and verify the cached result is returned.
- Reset the cache and verify it returns to `None`.

**Acceptance Scenarios**:
1. **Given** a non-Windows environment (Linux or macOS), **When** `FidelityConverter.is_word_available()` is called for the first time, **Then** it returns `False` and records `_word_available_cache = False`.
2. **Given** `_word_available_cache` is populated, **When** `is_word_available()` is called again, **Then** it returns the cached boolean without re-evaluating system platform or running shell commands.
3. **Given** `FidelityConverter.reset_cache()` is called, **Then** both Word and LibreOffice cache variables are reset to `None` on all platforms.

---

### User Story 2 - Fidelity Mode-Aware GUI Controls & Layout Parameter Locking (Priority: P1) 🎯 MVP

As an end user writing handwriting documents from DOCX templates in the GUI, when I select "Khóa bố cục & ảnh (Fidelity)", the application must automatically lock and disable paper size, orientation, background grid, and spacing controls, because Fidelity mode derives all physical dimensions and backgrounds strictly from the original DOCX file. When I switch back to "Tự do (Semantic)", the controls must automatically unlock and return to editable states.

**Why this priority**: Users currently can configure contradictory options (such as selecting Fidelity mode while simultaneously setting paper to A3 or background to Ô li), which causes user confusion since Fidelity completely overrides paper dimensions and backgrounds. Locking these controls makes the interface intuitive and self-explanatory.

**Independent Test**:
- Open the application and navigate to the Write tab.
- Switch DOCX mode from "Tự do (Semantic)" to "Khóa bố cục & ảnh (Fidelity)".
- Verify that Khổ giấy, Chiều giấy, Nền giấy, Khoảng cách (mm), and the "Cỡ..." button become disabled and non-interactable.
- Switch back to "Tự do (Semantic)".
- Verify that all locked controls are re-enabled and restored to active state.

**Acceptance Scenarios**:
1. **Given** the Write tab in Semantic mode, **When** the user changes the DOCX mode combobox to "Khóa bố cục & ảnh (Fidelity)", **Then** the paper size dropdown, orientation dropdown, background dropdown, spacing entry, and custom size button are disabled.
2. **Given** the Write tab in Fidelity mode with locked paper controls, **When** the user switches back to "Tự do (Semantic)", **Then** all paper controls return to normal/readonly interactive state and retain their previous values.
3. **Given** a user loading a DOCX document in Fidelity mode, **Then** the interface clearly indicates that page dimensions, orientation, and backgrounds are governed by the original document.

---

### User Story 3 - Non-Destructive OpenXML Surgical Text Whiteout (Priority: P1) 🎯 MVP

As a user converting complex DOCX documents containing charts, SmartArt, shapes, drawing canvases, equations, text boxes, and custom relationships into handwriting backgrounds, the whiteout generator must only whiten printed text runs without re-parsing and re-saving the entire document structure with high-level libraries, guaranteeing 100% preservation of all embedded images, diagrams, vector shapes, layout geometries, and custom XML parts.

**Why this priority**: High-level DOCX libraries can strip or corrupt unsupported OpenXML elements (such as DrawingML charts, SmartArt diagrams, complex group shapes, and legacy VML objects) during a full document load/save cycle. Direct OpenXML ZIP-level surgical editing guarantees bit-level preservation of all non-text assets.

**Independent Test**:
- Provide a complex DOCX file containing embedded images, tables, shapes, and text runs.
- Run `WhiteoutBackgroundGenerator.create_whiteout_docx()`.
- Unpack the resulting DOCX archive and inspect all parts:
  - All non-XML files (images, media, binary streams) match original checksums.
  - In `word/document.xml`, `word/header*.xml`, `word/footer*.xml`, etc., all text runs (`<w:r>` and DrawingML `<a:r>`) have their color values set to white (`#FFFFFF`).
  - No elements, attributes, or relationship definitions are deleted or modified outside text run color specifications.

**Acceptance Scenarios**:
1. **Given** a DOCX archive with text runs in body paragraphs, tables, textboxes, and headers/footers, **When** surgical whiteout is performed, **Then** all `<w:r>` run properties receive `<w:color w:val="FFFFFF"/>` and all `<a:r>` receive `<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>`.
2. **Given** a DOCX containing embedded images and media files, **When** surgical whiteout is performed, **Then** the media files and relationship parts (`_rels/`) are copied verbatim without byte alterations.
3. **Given** a DOCX containing charts, SmartArt, and shapes, **When** surgical whiteout is performed, **Then** all visual boundaries, drawing containers, and coordinate systems remain identical to the original file.

---

### User Story 4 - Subprocess Invocation Hygiene & Execution Safety (Priority: P2)

As a security-conscious administrator and developer running the application on Windows systems, external PowerShell scripts executed for COM automation must run via direct executable invocation without `shell=True`, preventing shell injection vulnerabilities and unpredictable command-line quoting behavior.

**Why this priority**: Using `shell=True` when invoking an executable with structured argument lists introduces unnecessary attack surface and potential shell parsing discrepancies.

**Independent Test**:
- Invoke `FidelityConverter._run_powershell_script()` with valid and invalid commands.
- Verify execution completes successfully with `shell=False`.
- Verify return code, standard output, and standard error capture operate as expected.

**Acceptance Scenarios**:
1. **Given** a PowerShell script execution request in `FidelityConverter`, **When** the subprocess is spawned, **Then** `shell=False` is used and argument parameters are passed directly as an array.
2. **Given** a script path containing spaces or Unicode characters, **When** executed with `shell=False`, **Then** PowerShell executes the script successfully without syntax errors.

---

### User Story 5 - Transparent Platform Capabilities & Accurate Documentation (Priority: P2)

As a user on Linux, macOS, or Windows consulting documentation and CLI messages, I need clear and honest explanations of system requirements so that I understand which Fidelity features require Windows with Microsoft Word COM and which features run across all platforms with LibreOffice.

**Why this priority**: Documentation previously implied that LibreOffice could replace Word COM for spatial text extraction. Clarifying that spatial extraction currently requires Word COM on Windows while LibreOffice handles PDF background conversion prevents user confusion and invalid bug reports.

**Independent Test**:
- Inspect CLI error messages when invoking Fidelity mode without Word COM.
- Inspect README.md and user guides for accurate feature matrices.
- Verify clear recommendations to use `--mode semantic` when running on systems without Word COM.

**Acceptance Scenarios**:
1. **Given** a system with LibreOffice but without Word COM, **When** spatial text extraction is attempted in Fidelity mode, **Then** the error message explicitly explains that spatial coordinate extraction requires Microsoft Word on Windows and suggests using Semantic mode as an alternative.
2. **Given** user-facing documentation (README.md), **When** reviewing the DOCX Fidelity section, **Then** the feature matrix clearly delineates Windows Word COM capabilities versus LibreOffice cross-platform capabilities.

---

## Edge Cases

- **Empty DOCX / No Text Runs**: A document containing only images or empty pages must process through surgical whiteout without errors, returning a valid DOCX with unmodified non-text parts.
- **Corrupted or Password-Protected DOCX**: When the input DOCX is not a valid ZIP archive or is password-protected, the whiteout generator must raise a descriptive `RuntimeError` and clean up any temporary files.
- **Rapid GUI Mode Toggling**: Rapidly toggling between "Tự do (Semantic)" and "Khóa bố cục & ảnh (Fidelity)" in the GUI must maintain synchronized widget states without throwing Tkinter callback exceptions or desynchronizing visual widget states.
- **DOCX with Custom XML Parts & Themes**: Complex documents containing custom schemas, VML drawings, or themes must retain all XML namespaces, prefixes, and unrelated nodes intact during surgical XML rewriting.
- **PowerShell Not Installed (Non-Windows or Minimal Windows)**: When running on environments where `powershell` is absent, calls to helper methods must fail gracefully with informative error messages instead of unhandled OS exceptions.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record `cls._word_available_cache = False` when `is_word_available()` is executed on non-Windows platforms (`sys.platform != "win32"`).
- **FR-002**: System MUST return cached results on subsequent calls to `is_word_available()` and `is_libreoffice_available()`, and cleanly reset both caches to `None` upon calling `reset_cache()`.
- **FR-003**: GUI (`WriteTab`) MUST implement a mode selection event handler (`_on_mode_changed`) bound to the DOCX mode combobox (`cb_mode`).
- **FR-004**: GUI MUST disable the paper size dropdown (`cb_paper`), paper orientation dropdown (`cb_ori`), paper background dropdown (`cb_bg`), spacing entry, and custom paper size button when the user selects "Khóa bố cục & ảnh (Fidelity)".
- **FR-005**: GUI MUST re-enable the paper size dropdown, orientation dropdown, background dropdown, spacing entry, and custom paper size button when the user selects "Tự do (Semantic)".
- **FR-006**: `WhiteoutBackgroundGenerator.create_whiteout_docx` MUST process DOCX files at the ZIP archive level, surgically modifying text colors in XML parts without round-tripping through high-level document abstraction libraries (`python-docx` save).
- **FR-007**: Surgical whiteout MUST apply pure white color (`#FFFFFF`) to all WordprocessingML runs (`<w:r>`) and DrawingML runs (`<a:r>`) across all document XML parts (`word/document.xml`, `word/header*.xml`, `word/footer*.xml`, `word/footnotes*.xml`, `word/endnotes*.xml`, `word/comments*.xml`).
- **FR-008**: Surgical whiteout MUST copy all non-modified files (including images, styles, settings, fonts, and relationship XMLs) bit-for-bit into the output archive.
- **FR-009**: `FidelityConverter._run_powershell_script` MUST execute subprocess commands with `shell=False` (or without `shell=True`).
- **FR-010**: System documentation, error messages, and logs MUST accurately reflect that spatial coordinate extraction in Fidelity mode currently requires Microsoft Word COM on Windows, while cross-platform environments can utilize Semantic mode or LibreOffice for document conversion.

---

### Key Entities

- **Document Archive**: A ZIP container housing the OpenXML package, consisting of XML parts, media assets, and relationship definitions.
- **Target XML Part**: An XML stream within the archive containing printable text runs that must undergo surgical whitening (e.g. `word/document.xml`).
- **Pass-Through Asset**: Any file within the archive (images, themes, embeddings) that must be preserved with zero byte alterations.
- **Mode Controller State**: The operational mode state in the user interface dictating whether document layout parameters are dynamically configurable (Semantic) or locked to template constraints (Fidelity).
- **Tool Availability Cache**: Process-level singleton cache capturing the availability status of Word COM and LibreOffice.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% test pass rate across all continuous integration matrix runs (Python 3.10, 3.11, 3.12, 3.13 on Linux and Windows), with zero failures on converter availability caching tests.
- **SC-002**: GUI mode switching between Semantic and Fidelity modes updates all associated control states in under 50 milliseconds with zero unhandled UI exceptions.
- **SC-003**: 100% of non-XML media files and embedded objects in a DOCX undergo zero byte modifications during surgical whiteout generation.
- **SC-004**: 100% of identified text runs in processed whiteout documents are rendered with pure white foreground color (`#FFFFFF`).
- **SC-005**: Zero subprocess calls in the fidelity converter module execute with `shell=True`.
- **SC-006**: Test suite size remains >= 472 passing tests with 0 regressions.

---

## Assumptions

- DOCX input documents adhere to OpenXML packaging conventions (standard ZIP compression with `word/` directory structure).
- Microsoft Word COM availability remains a Windows-specific capability accessible via PowerShell automation.
- Tkinter GUI operates on standard desktop platforms (Windows, Linux X11/Wayland, macOS) with standard ttk widget support.
- When paper controls are locked in Fidelity mode, previously selected values are remembered so that returning to Semantic mode seamlessly restores the user's prior configuration.
