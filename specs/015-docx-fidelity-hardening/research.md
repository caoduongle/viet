# Research & Technical Decisions: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Feature**: `015-docx-fidelity-hardening`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. External Tool Availability Caching Across Platforms

### Context & Problem
Continuous integration on Linux runners (Python 3.10–3.13) failed on `test_r6_converter_availability_caching` with:
```text
assert FidelityConverter._word_available_cache is not None
```
In `chuviettay/fidelity/converter.py`, `FidelityConverter.is_word_available()` checked:
```python
if sys.platform != "win32":
    return False
```
It returned immediately without setting `cls._word_available_cache = False`. On Windows, the cache was set, but on Linux/macOS the cache variable remained `None`, causing inconsistent cache semantics across platforms.

### Decision
Update `is_word_available()` to populate `cls._word_available_cache = False` prior to returning `False` on non-Windows platforms. Ensure `reset_cache()` resets `_word_available_cache` to `None`.

### Rationale
- **Deterministic state**: The cache contract guarantees that after `is_word_available()` is called, `_word_available_cache` is a boolean (`True` or `False`), never `None`.
- **Zero performance overhead**: On Linux/macOS, subsequent calls return `False` immediately from cache without checking `sys.platform`.
- **Clean test semantics**: Tests expecting cache memoization will pass identically across Windows, Linux, and macOS without platform-specific test branches.

### Alternatives Considered
- *Modify the test to allow `None` on Linux*: Rejected. This weakens the cache guarantee and leaves non-Windows systems without cache memoization.

---

## 2. Fidelity Mode-Aware GUI Controls & Layout Parameter Locking

### Context & Problem
In `chuviettay/view/write_tab.py`, the user can toggle between:
- "Tự do (Semantic)"
- "Khóa bố cục & ảnh (Fidelity)"

However, there was no event binding (`<<ComboboxSelected>>`) on `self.cb_mode`, and no handler `_on_mode_changed()`. In Fidelity mode, physical page dimensions (width, height), orientation (portrait, landscape), background style (plain, ruled, grid, music), and line spacing are fixed strictly by the source DOCX document. Allowing the user to select contradictory options (e.g. A3 paper + Graph grid in Fidelity mode) confuses users and gives the false impression that those settings affect the Fidelity output.

### Decision
1. Implement `_on_mode_changed(self, event=None)` in `WriteTab`.
2. Bind `self.cb_mode.bind("<<ComboboxSelected>>", self._on_mode_changed)`.
3. Retain references to:
   - `self.cb_paper` (Combobox)
   - `self.btn_paper_custom` (Button "Cỡ...")
   - `self.cb_ori` (Combobox)
   - `self.cb_bg` (Combobox)
   - `self.entry_spacing` (Entry)
4. When mode is `"Khóa bố cục & ảnh (Fidelity)"`:
   - Set states to `"disabled"`.
   - Update visual hints or tooltips indicating that paper and background are locked to the original document.
5. When mode is `"Tự do (Semantic)"`:
   - Set comboboxes to `"readonly"`, entry and custom button to `"normal"`.
   - Preserve previously selected user values so they are restored seamlessly.

### Rationale
- Immediate visual feedback prevents invalid configuration states.
- Follows standard desktop GUI UX conventions (disabling irrelevant input controls based on mode).

### Alternatives Considered
- *Hiding the controls completely*: Rejected. Dynamically hiding and showing large UI panels causes jarring layout jumps and reflows. Disabling controls communicates intent much more clearly.

---

## 3. Native OpenXML Surgical Text Whiteout via ZIP Archive Manipulation

### Context & Problem
Currently, `WhiteoutBackgroundGenerator.create_whiteout_docx()` loads the input DOCX using `docx.Document(docx_abs)` (`python-docx`), iterates through runs and XML DOM nodes, and calls `doc.save(output_path)`.
While this works for simple documents, `python-docx` performs a full document re-serialization. In complex Word documents containing:
- DrawingML charts and diagrams
- SmartArt objects
- Complex group shapes and text canvas boxes
- Mathematical equations (OMML)
- Embedded OLE objects
- Legacy VML shapes
- Custom XML schemas and parts
- Intricate section relationships (`_rels/`)

`python-docx` does not understand or preserve all modern OpenXML schemas, leading to silent drops, schema corruptions, or shifted geometries.

### Decision
Re-architect `WhiteoutBackgroundGenerator.create_whiteout_docx()` to operate as a surgical OpenXML ZIP filter:
1. Open the source `.docx` file using Python's standard `zipfile.ZipFile`.
2. Inspect every member of the archive:
   - For XML parts that contain text runs:
     - `word/document.xml`
     - `word/header*.xml`
     - `word/footer*.xml`
     - `word/footnotes.xml`
     - `word/endnotes.xml`
     - `word/comments.xml`
     Parse the XML tree (using `xml.etree.ElementTree`).
     Locate all WordprocessingML runs (`<w:r>`) and ensure `<w:rPr>` contains `<w:color w:val="FFFFFF"/>`. Remove or neutralize `<w:highlight>` and `<w:shd>` if set to non-white.
     Locate all DrawingML runs (`<a:r>`) and set `<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>`.
     Serialize back to UTF-8 XML.
   - For all other archive members (media images in `word/media/`, charts in `word/charts/`, diagrams in `word/diagrams/`, embeddings in `word/embeddings/`, styles, fonts, settings, relationships `_rels`, and `[Content_Types].xml`):
     Copy the raw byte stream verbatim to the new archive without parsing or altering a single byte.
3. Use atomic temporary file writing and replace.

### Rationale
- **100% preservation**: Non-text assets (images, charts, SmartArt, relationships) are bit-for-bit identical to the original file.
- **Zero external dependencies**: Uses standard library `zipfile` and `xml.etree.ElementTree`.
- **High performance**: Only target XML parts are parsed; binary media files (which can be tens of megabytes) are passed through as raw streams.
- **Fail-safe fallback**: If any XML part fails to parse, it raises a clean exception rather than producing a corrupt file.

### Alternatives Considered
- *Continue using python-docx with extra patches*: Rejected. High-level document libraries inherently re-serialize the entire DOM and strip unsupported schemas on save.

---

## 4. Subprocess Invocation Hygiene (`shell=False`)

### Context & Problem
In `chuviettay/fidelity/converter.py`, `_run_powershell_script()` currently uses:
```python
subprocess.run(
    ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script_path],
    shell=True,
    ...
)
```
When passing a list of arguments to `subprocess.run()`, setting `shell=True` creates an unnecessary `cmd.exe` intermediary process, which can introduce command injection risks, quoting issues with spaces/special characters, and signal propagation hurdles.

### Decision
Set `shell=False` (or remove `shell=True`). On Windows, `powershell` (or `powershell.exe`) is resolved directly from `PATH` by the Win32 `CreateProcess` API.

### Rationale
- Safer, cleaner process execution.
- Eliminates dependency on `cmd.exe` quoting behavior.

---

## 5. Transparent Documentation & Platform Capabilities

### Context & Problem
Previous documentation ambiguously suggested that LibreOffice could replace Microsoft Word for the entire Fidelity pipeline. In reality:
- **Spatial coordinate extraction**: Requires Microsoft Word COM via PowerShell on Windows. LibreOffice does not provide a comparable headless COM/CLI interface to measure precise rendered bounding boxes of individual paragraph text lines.
- **PDF background conversion**: Supported by both Microsoft Word COM (Windows) and LibreOffice (Linux, macOS, Windows).

### Decision
Update README.md, CLI help, and runtime error messages to clearly delineate:
- **Semantic Mode**: 100% cross-platform (Windows, Linux, macOS) for all document formats (.txt, .md, .docx).
- **Fidelity Mode**:
  - Full pipeline (layout extraction + whiteout + handwriting overlay): Requires Microsoft Word on Windows.
  - Whiteout background generation: Fully supported cross-platform.
  - Clear error message when attempting spatial extraction without Word COM, recommending `--mode semantic`.

### Rationale
- Prevents user frustration and unrealistic expectations on Linux/macOS headless servers.
- Accurately guides users to the appropriate mode.
