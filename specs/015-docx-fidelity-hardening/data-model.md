# Data Model: DOCX Fidelity Hardening, Cross-Platform CI Stability & Native OpenXML Whiteout

**Feature**: `015-docx-fidelity-hardening`  
**Date**: 2026-09-30  
**Status**: Completed  

---

## 1. Entities & Data Structures

### 1.1 OpenXmlPartDescriptor
Represents an individual item inside the DOCX ZIP package during surgical whiteout processing.

| Field | Type | Description |
|---|---|---|
| `filename` | `str` | Full relative path within ZIP archive (e.g. `word/document.xml`, `word/media/image1.png`). |
| `is_target_xml` | `bool` | `True` if this part contains printable text runs needing whitening; `False` if pass-through. |
| `raw_bytes` | `bytes` | Unmodified byte content from the archive. |
| `modified_bytes` | `bytes \| None` | Rewritten XML byte stream if processed, or `None` if passed through verbatim. |

#### Identification Rules for `is_target_xml`:
- Must match patterns:
  - `word/document.xml`
  - `word/header*.xml`
  - `word/footer*.xml`
  - `word/footnotes*.xml`
  - `word/endnotes*.xml`
  - `word/comments*.xml`
- All other files (e.g., `word/media/*`, `word/charts/*`, `word/styles.xml`, `_rels/*`, `[Content_Types].xml`) MUST have `is_target_xml = False` and be copied with zero modifications.

---

### 1.2 GuiModeState
Represents the operational state of the document writing UI in `WriteTab`.

| Field | Type | Allowed Values | Description |
|---|---|---|---|
| `current_mode` | `str` | `"semantic"`, `"fidelity"` | Selected DOCX mode in UI. |
| `paper_size_enabled` | `bool` | `True` (semantic), `False` (fidelity) | Interactive state of `cb_paper` and `btn_paper_custom`. |
| `orientation_enabled` | `bool` | `True` (semantic), `False` (fidelity) | Interactive state of `cb_ori`. |
| `background_enabled` | `bool` | `True` (semantic), `False` (fidelity) | Interactive state of `cb_bg`. |
| `spacing_enabled` | `bool` | `True` (semantic), `False` (fidelity) | Interactive state of `entry_spacing`. |
| `saved_paper_config` | `dict[str, str]` | Key-value mapping | Preserved values of paper options when toggling modes. |

#### State Transition Diagram

```
                 Select "Khóa bố cục & ảnh (Fidelity)"
  [Semantic Mode] ------------------------------------> [Fidelity Mode]
  - Paper: normal/readonly                             - Paper: disabled
  - Ori: normal/readonly                               - Ori: disabled
  - Bg: normal/readonly                                - Bg: disabled
  - Spacing: normal                                    - Spacing: disabled
  - Custom Btn: normal                                 - Custom Btn: disabled
                  <------------------------------------
                   Select "Tự do (Semantic)"
                   (Restores saved parameters)
```

---

### 1.3 ToolAvailabilityState
Singleton process-level state tracking availability of external document processing engines.

| Field | Type | Description |
|---|---|---|
| `_word_available_cache` | `bool \| None` | Cached result for Microsoft Word COM automation. `None` before first probe or after `reset_cache()`. |
| `_libreoffice_available_cache` | `bool \| None` | Cached result for LibreOffice CLI (`soffice`/`libreoffice`). `None` before first probe or after `reset_cache()`. |

#### Validation Invariants
- On non-Windows platforms (`sys.platform != "win32"`):
  - Initial: `_word_available_cache is None`
  - After `is_word_available()`: `_word_available_cache is False`
  - After `reset_cache()`: `_word_available_cache is None`
- On Windows:
  - Initial: `_word_available_cache is None`
  - After `is_word_available()`: `_word_available_cache in (True, False)`
  - After `reset_cache()`: `_word_available_cache is None`

---

## 2. XML Namespaces & Element Specifications

For OpenXML surgical modification, the following standard OpenXML namespaces are used:

| Prefix | Namespace URI | Description |
|---|---|---|
| `w` | `http://schemas.openxmlformats.org/wordprocessingml/2006/main` | WordprocessingML core |
| `a` | `http://schemas.openxmlformats.org/drawingml/2006/main` | DrawingML main drawing namespace |
| `r` | `http://schemas.openxmlformats.org/officeDocument/2006/relationships` | Office document relationships |
| `wp` | `http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing` | DrawingML word processing anchors |

### Run Whitening Transformations

1. **WordprocessingML (`<w:r>`)**:
   - Locate or create `<w:rPr>` child under `<w:r>`.
   - Set `<w:color w:val="FFFFFF"/>`.
   - If `<w:highlight>` is present, set `<w:highlight w:val="none"/>` or remove it.
   - If `<w:shd>` is present with a non-clear fill, set `<w:shd w:fill="auto" w:val="clear"/>`.

2. **DrawingML (`<a:r>`)**:
   - Locate or create `<a:rPr>` child under `<a:r>`.
   - Remove any existing child tag in `("solidFill", "gradFill", "blipFill", "pattFill", "noFill")`.
   - Append `<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>`.
