# Technical Research: Comprehensive Quality, Correctness, and Performance Hardening

**Feature**: `014-core-engine-hardening`  
**Date**: 2026-09-30  
**Status**: Completed

---

## 1. Digit and Punctuation Learning & Lookup Pipeline (L1)

### Context & Problem
When teaching samples via the GUI or batch learning (`chuviettay/model/learning.py`), all samples were being placed into `bank.words`. When generating handwriting for multi-digit numbers (e.g., `"2024"`) or decimals (e.g., `"3,5"`), `Writer.number` looked for individual digits in `bank.digits` and punctuation in `bank.punct`. Because `add_sample` never populated `bank.digits` or `bank.punct`, newly trained banks completely failed on numbers and punctuation.

### Decision
1. **Shared Classifier Function**: Implement a shared `classify_token(token: str) -> str` utility used by both `learn_from_grid` and `teach_word`:
   - Single ASCII/Unicode digit (`char.isdigit()`): `"digits"`
   - Standard punctuation marks (`.,!?:;-"'()[]{}/`): `"punct"`
   - Known mathematical/special symbols: `"symbols"`
   - All other multi-character words: `"words"`
2. **Backward-Compatible Lookup in `Writer.number`**:
   - `Writer.number` first checks `self.bank.digits.get(digit)`.
   - If not found, it checks `self.bank.words.get(digit)` before declaring the digit missing.
   - For punctuation, `Writer.word` and `token` look in `bank.punct`, falling back to `bank.words`.
   - This eliminates the need for a breaking schema migration, maintaining 100% compatibility with older bank files.

### Alternatives Evaluated
- *Full Schema v4 Migration*: Convert all old banks on load. Rejected because it mutates user files without explicit consent and creates unnecessary risk.
- *Only store in `words`*: Deprecate `digits` and `punct`. Rejected because it degrades performance and breaks the separation between single-character glyphs and multi-character word tokens.

---

## 2. Importer Sanitization, Mathematical Inequalities & List Preservation (L6, L7, L8, L10)

### Context & Problem
1. **HTML Sanitization (L7)**: `_sanitize_html` in `markdown_importer.py` used a naive regex `<[^<]+?>` that stripped mathematical comparison operators such as `"1 < 2 và 3 > 2"` or `$a < b$`. However, `markdown-it-py` is configured with `html: False`, meaning raw HTML tags are never executed or rendered as HTML elements anyway.
2. **Markdown Nested Lists & Structural Blocks (L8)**: Nested list items were flattened into disjoint paragraphs, and code blocks or horizontal rules were silently discarded without reporting.
3. **Inline Boundary Space Inflation (L6)**: When bold/italic formatting was immediately followed by punctuation (e.g., `"**chào**,"`), tokens were split with an erroneous synthetic whitespace.
4. **DOCX Traversal (L10)**: `docx_importer.py` directly read `paragraph.text`, dropping text following soft line breaks (`<w:br/>`), tabs (`<w:tab/>`), tracked revisions (`<w:ins>`), and omitting alignment metadata.

### Decision
1. **Remove `_sanitize_html`**: Since `markdown-it-py` already escapes HTML when `html: False`, remove `_sanitize_html`. Mathematical comparisons `<` and `>` pass through completely intact.
2. **Recursive List Parsing in Markdown**: Traverse `markdown-it` token streams hierarchically. Nested `ordered_list_open` / `bullet_list_open` tokens maintain their nesting depth (`level`) and parent-child associations.
3. **Transparent Reporting in `Document.unsupported`**: Structural elements not yet fully rendered as handwriting (e.g., complex code blocks, raw HTML embeds, horizontal rules) must append a structured entry to `document.unsupported` so users and logs are aware of omitted content.
4. **Fine-Grained OpenXML Traversal**: In `docx_importer.py`, iterate through child elements of each run:
   - Extract `<w:t>` (text)
   - Convert `<w:tab/>` to standard tab indent or spaces
   - Convert `<w:br/>` to a newline boundary
   - Traverse `<w:ins>` (inserted text) while ignoring `<w:del>` and `<w:delText>`
   - Suppress field instruction text (`<w:instrText>`)
   - Preserve paragraph alignment (`paragraph.alignment`).

---

## 3. Proportional Geometry & Layout Scaling (L4, L5, R8, R9)

### Context & Problem
- **Line Spacing (L4)**: `line_h` was computed as a fixed constant (`~29.0`) based on baseline font height, without multiplying by `opts.scale`. When users set `--scale 2.0`, character glyphs doubled in height while line spacing remained constant, causing consecutive lines to collide.
- **Math Block Scaling (L5)**: Inline math scaled, but standalone math blocks and formula matrices did not scale consistently with `opts.scale`, creating visually jarring font disparities.
- **Table Column Measurement (R8)**: Table column widths were estimated by counting characters rather than measuring actual stroke bounding boxes (`calc_text_bounds`), causing long Vietnamese words (e.g., "nghiên cứu") to overflow cell borders.

### Decision
1. **Scale-Proportional Line Height**:
   ```python
   # In DocumentLayoutEngine
   if opts.line is not None and opts.line > 0:
       effective_line_h = opts.line
   else:
       # Default line height scales proportionally with font scale
       effective_line_h = base_line_h * opts.scale
   ```
2. **Uniform Formula Scaling**: Apply `eff_scale = opts.scale * (target_font_size / bank_xh)` consistently across both inline math nodes and display block formulas.
3. **Stroke-Based Table Column Calculation**: Measure maximum word bounding width using `Writer.calc_word_bounds` for every cell. If a word exceeds available column width, apply intelligent word wrapping or co-scaling (`scale_adj`).
4. **Table Border Jitter**: Introduce small, natural handwriting stroke variation for table borders using `opts.jitter` seeded by `opts.seed` to ensure deterministic, beautiful notebook-style tables.

---

## 4. LaTeX Formula Nesting & Macro Translation (L9)

### Context & Problem
The parser in `chuviettay/math/parser.py` processed tokens sequentially. Superscripts (`^`) and subscripts (`_`) were only recognized for single tokens. When enclosed in grouping braces `{}` (e.g., `\frac{x^2}{y}` or `e^{x^2}`), the exponent was misidentified as ordinary text. Furthermore, standard macros (`\cdot`, `\to`, `\forall`, `\left`, `\right`) were rendered as literal strings.

### Decision
1. **Unified Recursive Row Parser**: Implement a single recursive `parse_row(tokens, max_depth=32)` function for parsing expressions at the root level and within nested `{}` groups.
2. **Standard LaTeX Macro Map**: Define a comprehensive lookup dictionary mapping macros to mathematical symbol entities:
   - Operators: `\cdot` ($\cdot$), `\times` ($\times$), `\div` ($\div$), `\pm` ($\pm$)
   - Arrows: `\to`, `\rightarrow` ($\to$), `\leftarrow` ($\leftarrow$), `\Rightarrow` ($\Rightarrow$)
   - Logic & Sets: `\forall` ($\forall$), `\exists` ($\exists$), `\in` ($\in$), `\notin` ($\notin$), `\emptyset` ($\emptyset$)
   - Calculus: `\partial` ($\partial$), `\nabla` ($\nabla$), `\infty` ($\infty$)
   - Ellipses: `\ldots`, `\cdots`
   - Delimiters: `\left`, `\right` (adjust bounding box height of enclosing brackets)
3. **Graceful Fallback**: Unrecognized macros log a clear warning and add the symbol to `missing_symbols`, never leaking raw `\` commands into handwritten text.

---

## 5. Bank Persistence Performance & Deferred Writes (L14)

### Context & Problem
Writing the entire font bank (`json.gz`) took ~0.5s for 300 words, ~2.0s for 700 words, and ~6.8s for 1500 words. Because `Bank.save()` was called synchronously after every single word trained, the GUI froze for seconds during repetitive training sessions.

### Decision
1. **Debounced Deferred Save**:
   - In interactive mode (GUI), calling `add_sample` marks the bank as "dirty" (`_dirty = True`).
   - A debounce timer (2.0 seconds of idle time) triggers the actual save.
   - Switching tabs, loading another file, or closing the application immediately forces a synchronous flush.
2. **Background Thread Write with Lock**:
   - The serialized JSON compression runs on a background worker thread (`threading.Thread`) protected by an internal `threading.Lock`.
   - Disk write uses an atomic rename (`.tmp` -> `.json.gz`) to guarantee zero file corruption if power is interrupted.
3. **Fast Compression Level**: Use `gzip.compress(..., compresslevel=5)` during interactive saves for a 3x speedup with negligible file size difference.

---

## 6. PDF-First High-Fidelity Document Layout (R1–R6, v2.2 → v3.0)

### Context & Problem
The current Fidelity Mode extracts coordinates using PowerShell Word COM. This creates several challenges:
- Extracts coordinates by paragraph rather than by individual wrapped lines (R1).
- Requires Word COM to run, causing process startup overhead on each check (R6).
- Cross-platform support on Linux requires LibreOffice and external parsing.

### Decision
1. **PDF-First Architecture**:
   - Step 1: Render DOCX to PDF via Microsoft Word (Windows) or LibreOffice (`soffice` on Linux/macOS).
   - Step 2: Use an MIT-licensed PDF parser (`pdfplumber` / `pdfminer.six`) to extract exact line coordinates, character bounding boxes, and font sizes directly from the intermediate PDF.
   - Step 3: Neutralize printed text with white overlay rectangles directly in the PDF background.
   - Step 4: Lay out handwriting strokes line-by-line using true x-height scaling.
2. **Strict License Conformance**:
   - Reject `PyMuPDF` (GPL/AGPL) to strictly safeguard the MIT license of this repository.
   - Adopt `pdfplumber` / `pdfminer.six` (MIT License).
3. **Process Life-Cycle Safety**:
   - Cache `is_available()` results in memory to avoid starting Word multiple times per run.
   - Ensure Word COM suppresses alerts (`DisplayAlerts = 0`) and releases COM handles deterministically with garbage collection.
