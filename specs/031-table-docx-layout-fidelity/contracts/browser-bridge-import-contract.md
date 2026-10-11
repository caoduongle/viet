# Contract: Browser Bridge Document Import & Web Editor Feedback

**Feature Branch**: `031-table-docx-layout-fidelity`
**Date**: 2026-10-11
**Spec**: [spec.md](../spec.md)

## 1. Purpose

This contract defines the communication interfaces between `chuviettay/browser/bridge.py` (`BridgeController`), the web worker, and the web frontend (`webapp/js/write.js`) for document import data preservation, warning diagnostics, and table authoring controls.

---

## 2. API Signatures

### 2.1 Python Bridge: `import_docx`

```python
def import_docx(self, docx_bytes: bytes) -> dict[str, Any]:
    """
    Parses a .docx document and converts it to editor Markdown.
    
    Returns:
    {
        "ok": True,
        "markdown_text": str,   # Serialized document including markdown pipe tables
        "warnings": list[str],  # Diagnostic warnings (e.g. flattened merged cells, nested tables)
        "unsupported": list[str] # Elements not fully representable
    }
    or on failure:
    {
        "ok": False,
        "error": str
    }
    """
```

### 2.2 Table-to-Markdown Serialization Rules

1. **Standard Tables**:
   - Converted to standard Markdown pipe tables:
     ```markdown
     | Header 1 | Header 2 |
     | :--- | :---: |
     | Row 1 Col 1 | Row 1 Col 2 |
     ```
2. **Single-Row Tables**:
   - If a DOCX table contains only 1 row without a header, synthesize a valid Markdown header or use that row as header with delimiter row `| --- | ... |` so `MarkdownImporter` parses it as a valid `Table` rather than plain text.
3. **Cell Content Sanitization**:
   - Any literal pipe `|` inside cell text is escaped as `\|`.
   - Newlines within cells are converted to spaces or cleaned dividers, avoiding invalid newline breaks in Markdown rows (noting that `MarkdownImporter` strips `<br>` tags).
   - LaTeX math formulas are wrapped in `$math$`.
4. **Complex Merged Cells (`rowspan > 1` or `colspan > 1`)**:
   - The cell text is placed in the primary cell position.
   - An informative diagnostic warning is appended to `res.warnings`:
     `"Bảng chứa ô gộp (hàng/cột): cấu trúc được giản lược sang dạng bảng Markdown."`
5. **Nested Tables**:
   - Child table content is extracted into cell text with clear separation.
   - Appends warning to `res.unsupported`: `"Bảng lồng nhau: nội dung đã được trích xuất vào ô cha."`

---

## 3. Web Client UX Contract

### 3.1 DOCX Import Response Handling in `write.js`

1. Upon receiving `res = await sendWorkerMessage("import_docx", { bytes: buffer })`:
   - Set `textarea.value = res.markdown_text || ""`.
   - Set format selector `#select-format` to `"md"`.
   - If `res.warnings.length > 0 || res.unsupported.length > 0`:
     - Display a visible notification banner or toast informing the user:
       `"Nhập DOCX hoàn tất với cảnh báo: [tóm tắt cảnh báo]"`.
   - Trigger immediate live preview.

### 3.2 Interactive Table Insertion Toolbar Control

1. When `#btn-md-table` is clicked:
   - Display a modal or popover prompting for:
     - `rows` (integer $\ge 1$, default 3)
     - `cols` (integer $\ge 1$, default 3)
     - `header` (boolean, default true)
   - On confirmation, insert the corresponding markdown template at the cursor position:
     ```markdown
     | Cột 1 | Cột 2 | ... |
     | :--- | :--- | ... |
     | ... | ... | ... |
     ```
