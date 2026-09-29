# Research: Document IR, Multi-Format Importers, Layout Engine, and Math/Table Rendering (Iteration 2)

**Feature**: `007-document-ir-and-importers`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Document IR Architecture & Class Hierarchy

### Decision
Define a strongly-typed, immutable, parser-independent Document Intermediate Representation (IR) in `chuviettay/document/ir.py` using Python standard dataclasses:
- **`Node`**: Abstract root node.
- **`Block(Node)`**: Structural block elements that participate in vertical page layout:
  - `Paragraph(Block)`: Contains `inlines: list[Inline]`, `align: str = "left"`.
  - `Heading(Block)`: Contains `level: int` (1 to 6), `inlines: list[Inline]`.
  - `ListBlock(Block)`: Contains `ordered: bool`, `items: list[list[Block]]`, `start: int = 1`.
  - `Table(Block)`: Contains `rows: list[TableRow]`, `border_style: TableBorder`, `col_alignments: list[str]`.
  - `MathBlock(Block)`: Contains `latex: str`, `ast: MathNode | None = None`.
  - `PageBreak(Block)`: Explicit page break request.
- **`Inline(Node)`**: Flow elements placed inside paragraphs, headings, and table cells:
  - `Text(Inline)`: Raw text content `text: str`.
  - `MathInline(Inline)`: Inline math snippet `latex: str`, `ast: MathNode | None = None`.
  - `Symbol(Inline)`: Discrete symbol/glyph `symbol: str` (e.g., `∑`, `≤`, `π`).
  - `LineBreak(Inline)`: Hard line break within block.
- **`Document`**: Root container `blocks: list[Block]`, `metadata: dict[str, Any] = field(default_factory=dict)`.

### Rationale
- Decouples importers (Markdown, DOCX, TXT) completely from the layout and rendering systems. Importers only produce `Document` IR.
- Preserves the MVC pattern: `Document` IR acts as a pure domain model in `chuviettay/document/`, free of GUI or file serialization concerns.
- Dataclasses provide lightweight structure, pattern-matching compatibility, simple equality testing, and easy serialization/debugging.

---

## 2. Optional Dependency Strategy & Zero-Core Dependency Rule

### Decision
1. Keep `dependencies = []` in `pyproject.toml` so core handwriting generation from `.txt` or raw text has **zero external dependencies**.
2. Declare document importers under `[project.optional-dependencies]`:
   ```toml
   [project.optional-dependencies]
   docs = [
       "markdown-it-py>=3.0.0",
       "mdit-py-plugins>=0.4.0",
       "python-docx>=1.1.0",
   ]
   ```
3. Use lazy imports inside `chuviettay/importer/markdown_importer.py` and `chuviettay/importer/docx_importer.py`.
4. Wrap import statements in a guarded utility `chuviettay/importer/dependency.py`:
   - If missing, raise `OptionalDependencyError` with actionable user guidance:
     `'Để mở tính năng này, bạn cần cài đặt thêm thư viện: pip install ".[docs]"'`.
5. Standalone PyInstaller releases will bundle the optional packages, so non-technical users of the pre-built desktop application never see dependency errors.

---

## 3. Importer Abstraction & Concrete Importers

### Decision
Create `chuviettay/importer/base.py` defining:
```python
@dataclass
class ImportResult:
    document: Document
    warnings: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)

class BaseImporter(ABC):
    @abstractmethod
    def import_file(self, path: str) -> ImportResult: ...
    @abstractmethod
    def import_text(self, text: str) -> ImportResult: ...
```

---

## 4. Table Layout & Multi-Border Stroke Rendering

### Decision
Implement table layout in `chuviettay/layout/table_layout.py`:
1. **Column Sizing**:
   - Compute natural width (longest word) and max width (unwrapped text) for each column.
   - If total max width exceeds available line width (`bank.width`), distribute remaining width proportionally across columns while guaranteeing natural min width.
2. **Cell Text Wrapping**:
   - Wrap text within each cell based on assigned column width.
   - Row height is determined by `max(cell_heights) + 2 * padding`.
3. **Border Styles (`TableBorder`)**:
   - `NONE`: No borders drawn; cells laid out with column gutter spacing.
   - `OUTER`: 4 outer bounding strokes framing the table.
   - `ALL`: Outer bounding strokes plus inner grid lines between every row and column.
   - `HORIZONTAL`: Outer top/bottom borders plus horizontal dividers between rows (academic paper style).

---

## 5. Math AST & Typographic Layout

### Decision
1. **Two-Level Math Approach**:
   - **Level 1 (Symbols)**: Discrete symbols like `≤`, `≥`, `≠`, `≈`, `±`, `×`, `÷`, `π`, `∑`, `∫`, `∞`, Greek letters.
   - **Level 2 (Structured Math AST)**: Expressions containing 2D spatial relationships:
     - `Fraction(numerator, denominator)`
     - `Superscript(base, exp)`
     - `Subscript(base, sub)`
     - `SubSuperscript(base, sub, exp)`
     - `Root(radicand, degree=None)`
     - `MathRow(elements)`
2. **Metrics & Typographic Alignment**:
   - Every `MathNode` evaluates a `Size(width, height, ascent, descent, baseline)`.
   - Baseline alignment: Numerator is placed above the math axis; denominator below; fraction bar drawn at the math axis (roughly $0.45 \times \text{x\_height}$).
   - Superscripts and subscripts scale font size (0.7x for first level, 0.5x minimum) and adjust baseline offsets.

---

## 6. Bank Schema v3 & Migration Strategy

### Decision
1. Update `CURRENT_VERSION = 3` in `chuviettay/model/bank_schema.py`.
2. Schema v3 requires a top-level `"symbols": dict[str, list[Sample]]` key.
3. Add `_migrate_v2_to_v3(d: dict) -> dict`:
   ```python
   def _migrate_v2_to_v3(d: dict[str, Any]) -> dict[str, Any]:
       d["schema_version"] = 3
       if "symbols" not in d:
           d["symbols"] = {}
       return d
   ```
4. Register `2: _migrate_v2_to_v3` in `_MIGRATORS`.

---

## 7. Backward Compatibility & Golden-Master Preservation

### Decision
1. Retain `chuviettay/model/composer.py` and `ctl.write_text(text, opts, out_path)` with their exact current logic.
2. Introduce `ctl.write_document(document: Document, opts: WriteOptions, out_path: str) -> WriteResult` as the new API for structured documents.
3. Keep `test_golden_master.py` untouched to continuously verify that SHA-256 hashes of standard text generation remain byte-identical.

---

## 8. Math AST Handwritten Stroke Generation & Operator Fallbacks (Iteration 2)

### Context & Problem
In commit `33185d7`, `MathLayoutEngine.measure(node)` for `TextNode` (e.g. $x$, $y$, numbers $10$) only returned a bounding box without any glyph strokes (`glyphs=[]`). In a formula like $x^2 + y^2 = 10$, only the exponent "2" (if measured) or blank gaps appeared; variables and constants were completely missing from the rendered output.

### Decision
1. In `MathLayoutEngine`:
   - Initialize with `Writer` instance (or create one using `self.bank` and random seed).
   - In `measure(node: TextNode)`:
     - If `node.text.isdigit()`: query `self.writer.number(node.text)` -> `(strokes, width, miss)`.
     - Else: query `self.writer.token(node.text)` -> `(strokes, width, miss)`.
     - When strokes exist, attach `PositionedGlyph(strokes=strokes, x=0.0, y=0.0, scale=eff_scale)`.
     - If missing samples occur, track in `self.missing_symbols` and reserve bounding box `[ text ]`.
2. In `measure(node: SymbolNode)`:
   - Check `self.bank.symbols[sym]`.
   - If missing, check `self.bank.punct` / `self.writer.token(sym)`.
   - For standard operators (`+`, `-`, `=`, `/`): if no sample exists in bank, generate crisp synthetic vector strokes (`PositionedStroke`) so formulas always display readable operator glyphs rather than empty spaces.

### Alternatives Considered
- *Rendering TeX via Matplotlib/dvipng to image*: Violates zero external dependency rule, introduces raster artifacts, and clashes visually with handwriting strokes.

---

## 9. Inline Math Single-Scale Coordinate Space (Iteration 2)

### Context & Problem
In `chuviettay/layout/engine.py`, `_layout_inlines()` pre-scaled math strokes by `self.S * scale_mult`. Then `_render_text_line()` applied `s = self.S * ...` to all line items inside `place(st, 0, 0, s, rot)`. This caused inline math to undergo quadratic scaling $(S^2 \times \text{scale\_mult})$, blowing up formula dimensions whenever scale $\ne 1.0$ or inside headings.

### Decision
1. Standardize all typographic items (`Text`, `MathInline`, `Symbol`) to **unscaled base bank coordinate space** (where $S = 1.0$).
2. `MathLayoutEngine.measure()` calculates relative coordinates normalized to base bank units.
3. In `_render_text_line()`, pass `scale_mult` and apply uniform scaling:
   $$s = \text{self.S} \times \text{scale\_mult} \times (1 + \text{jitter})$$
   uniformly to both text strokes and math strokes.
4. Result: Both text and inline math scale proportionally together across all heading levels and custom scale settings without double-scaling.

---

## 10. Rich Table Cell Rendering (Inlines, Colspan, Rowspan & Borders) (Iteration 2)

### Context & Problem
Table cells were previously flattened into plain strings via `_extract_cell_text()`, stripping `MathInline`, `Symbol`, and `LineBreak`. Furthermore, Word merged cells (`colspan` and `rowspan`) were ignored, and table column alignments were disregarded.

### Decision
1. **Rich Cell Inlines**:
   - Instead of tokenizing plain text strings, execute `_layout_inlines()` on each `Paragraph` block inside `TableCell`.
   - Support `MathInline`, `Symbol`, `Text`, and `LineBreak` natively within table cells.
2. **Column Alignments**:
   - In `Table.col_alignments`: support `"left"`, `"center"`, `"right"`.
   - When positioning lines inside a cell of width $W$, calculate horizontal start:
     - Left: $x_{\text{start}} = x_{\text{cell}} + \text{padding}$
     - Center: $x_{\text{start}} = x_{\text{cell}} + (W - w_{\text{content}}) / 2.0$
     - Right: $x_{\text{start}} = x_{\text{cell}} + W - \text{padding} - w_{\text{content}}$
3. **Merged Cells (`colspan` & `rowspan`)**:
   - In `DocxImporter`, extract `w:gridSpan` (for `colspan`) and `w:vMerge` (for `rowspan`).
   - Calculate cell dimensions as sums of spanned column widths and row heights.
   - In `generate_border_strokes()`, track active merged cell spans and suppress interior vertical and horizontal border strokes that cross inside merged cells.

---

## 11. Unified Plaintext IR Pipeline & Paragraph Spacing Retention (Iteration 2)

### Context & Problem
Plaintext `.txt` files bypassed Document IR in CLI/GUI, and `TxtImporter` stripped blank lines, causing multiple paragraphs to collapse into one without vertical separation.

### Decision
1. In `TxtImporter`:
   - Split input text into lines.
   - Empty lines are preserved as empty paragraphs `Paragraph(inlines=[])`.
2. In `DocumentLayoutEngine.render()`:
   - When encountering an empty paragraph, advance `cur_y += self.line_h * 0.8` to create clean vertical paragraph spacing.
3. In `cli.py` and `write_tab.py`:
   - Route `.txt` files through `ctl.import_document(path)` and `ctl.write_document()`.
   - Maintain `ctl.write_text(text, opts, out)` as a pure legacy entry point calling `composer.write_document()` to guarantee 100% SHA-256 byte parity on `tests/test_golden_master.py`.

---

## 12. End-to-End Streaming `PageBuffer` (Iteration 2)

### Context & Problem
`PageBuffer` existed in `chuviettay/layout/stream.py` but was not wired into `DocumentLayoutEngine.render()`, which accumulated all pages in memory and wrote the file at the end.

### Decision
1. In `DocumentLayoutEngine.render(doc, out_path)`:
   - Use `with PageBuffer(out_path, page_w=self.x0 + self.width + 20) as pb:`.
   - In `new_page()`, immediately call `pb.append_page(cur_page)` and clear `cur_page = []`.
   - Upon loop completion, write the final page.
   - `PageBuffer.close()` flushes and atomically renames the completed gzip file.
2. Result: Constant memory footprint even when rendering 50+ page documents.

---

## 13. Strict Format Validation & Unsupported OMML Diagnostics (Iteration 2)

### Context & Problem
`get_importer_for_path()` defaulted any unknown extension (`.pdf`, `.xlsx`, `.jpg`) to `TxtImporter()`, causing binary garbage to be parsed. DOCX importer silently skipped unsupported OMML tags without notifying the user.

### Decision
1. **Strict Format Validation**:
   - Define `UnsupportedFormatError(ValueError)` in `chuviettay/importer/base.py`.
   - `get_importer_for_path(path, fmt)` verifies extensions against `(".txt", ".md", ".markdown", ".docx")`. If unknown, raises `UnsupportedFormatError`.
2. **OMML Unsupported Diagnostics**:
   - When encountering OMML tags in `("m", "nary", "limLow", "limUpp", "func", "bar", "acc", "groupChr", "eqArr")`, record `unsupported.append(f"OMML: {tag}")`.
3. **Dependency Typo Fix**:
   - Correct installation prompt in `chuviettay/importer/dependency.py` to `pip install ".[docs]"`.
