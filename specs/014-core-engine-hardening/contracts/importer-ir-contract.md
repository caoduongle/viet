# Contract: Importer Intermediate Representation & Content Integrity

**Document**: `contracts/importer-ir-contract.md`  
**Feature**: `014-core-engine-hardening`  
**Status**: Ratified

---

## 1. Text Preservation Contract

1. **Mathematical Inequality Operators**:
   - Comparison operators `<` and `>` MUST be passed through to the document IR unaltered.
   - Any raw HTML stripping logic MUST be bypassed when parser operates with `html: False`.
2. **Whitespace Integrity Across Inline Boundaries**:
   - Consecutive inline formatting spans (e.g., `TextSpan("chào")` followed immediately by `TextSpan(",")`) MUST NOT synthesize whitespace between the word and the punctuation.
   - Whitespace between tokens is only created when an explicit whitespace character (`' '`, `'\t'`, `'\n'`) exists in the source text.
3. **OpenXML Run Traversal Contract**:
   - In DOCX import, text extraction MUST inspect `<w:t>`, convert `<w:tab/>` to whitespace/tab indent, convert `<w:br/>` to a line break, and parse revisions in `<w:ins>`.
   - Field instructions (`<w:instrText>`) and deleted text (`<w:delText>`) MUST be suppressed.
4. **Unsupported Block Transparency**:
   - If an imported document contains blocks that cannot currently be mapped to handwriting strokes (e.g., raw code fences, horizontal dividers), the importer MUST record an entry in `Document.unsupported`:
     ```python
     {
         "type": "code_block",
         "line": 42,
         "content": "def foo(): pass"
     }
     ```
   - Content MUST NOT be silently omitted without an `unsupported` notification.
