# Research: Document IR, Multi-Format Importers, Layout Engine, and Math/Table Rendering

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

### Alternatives Considered
- *Dict/JSON-based AST*: Flexible but prone to runtime KeyError/type errors, lacked static validation and IDE auto-completion.
- *Extending Markdown-it tokens directly*: Violates dependency inversion and ties the whole application to a third-party parser AST.

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
     `"Tính năng mở định dạng này yêu cầu cài đặt bổ sung: pip install .[docs]"`.
5. Standalone PyInstaller releases will bundle the optional packages, so non-technical users of the pre-built desktop application never see dependency errors.

### Rationale
- Core project constitution principle II (Simple Architecture, KISS/YAGNI) and principle IV (Loose Coupling).
- Avoids bloat and installation friction for users who only want Vietnamese handwriting for raw notes or text files.

### Alternatives Considered
- *Making `markdown-it-py` and `python-docx` required dependencies*: Violates the project's long-standing lightweight zero-dependency guarantee for core features.
- *Writing custom Markdown and DOCX ZIP parsers from scratch*: High maintenance burden, fragile, reinventing well-tested community standards.

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

Concrete implementations:
1. **`TxtImporter`**: Zero dependencies. Splits lines, produces `Paragraph` with `Text` inlines. Preserves exact line breaking and spacing semantics.
2. **`MarkdownImporter`**: Uses `markdown-it-py` with `mdit_py_plugins.dollarmath` enabled.
   - **Security**: Disables HTML parsing (`enable_rules=['table']`, `html=False`) to neutralize `<script>` and malicious HTML injection.
   - Converts tokens into `Heading`, `Paragraph`, `ListBlock`, `Table`, `MathInline`, and `MathBlock`.
3. **`DocxImporter`**: Uses `python-docx` (version >= 1.1.0).
   - Uses `doc.iter_inner_content()` to iterate paragraphs and tables in their strict document appearance order (fixing the common bug where tables are read separately after all paragraphs).
   - Inspects paragraph XML for Office Math Markup Language (`m:oMath`, `m:oMathPara`) and translates OMML structures into `MathBlock` / `MathInline`.
   - Traverses runs for inline text and detects unsupported inline elements (drawings, inline shapes, SmartArt) into `ImportResult.unsupported`.

### Rationale
- Consistent error and warning reporting across all formats.
- Complete parity with Word document ordering thanks to `iter_inner_content()`.
- Safe Markdown parsing with zero attack surface for GUI/desktop execution.

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
4. **Stroke Rendering**:
   - Straight line strokes are generated using the existing `xopp.stroke_xml` mechanism with 2 endpoints: `[(x1, y1), (x2, y2)]`, using the configured pen width and color.
5. **Pagination**:
   - When a table exceeds the remaining page height, it splits cleanly between rows. No row is sliced midway through a text line.

### Rationale
- Reuses vector pen stroke generation already verified in `xopp.make_grid()`.
- Supports clean typographic output for school exercises and technical reports.

---

## 5. Math AST & Typographic Layout

### Decision
1. **Two-Level Math Approach**:
   - **Level 1 (Symbols)**: Discrete symbols like `≤`, `≥`, `≠`, `≈`, `±`, `×`, `÷`, `π`, `∑`, `∫`, `∞`, Greek letters. These are treated as individual glyphs stored in the bank's `"symbols"` category and laid out as single inline tokens.
   - **Level 2 (Structured Math AST)**: Expressions containing 2D spatial relationships:
     - `Fraction(numerator, denominator)`
     - `Superscript(base, exp)`
     - `Subscript(base, sub)`
     - `SubSuperscript(base, sub, exp)`
     - `Root(radicand, degree=None)`
     - `MathRow(elements)`
2. **Metrics & Typographic Alignment**:
   - Every `MathNode` evaluates a `Size(width, height, ascent, descent, baseline)`.
   - Baseline alignment: Numerator is placed above the math axis; denominator below; fraction bar drawn at the math axis (roughly $0.5 \times \text{x\_height}$).
   - Superscripts and subscripts scale font size (0.7x for first level, 0.5x minimum) and adjust baseline offsets.
3. **Missing Symbol Placeholder**:
   - When a symbol glyph is missing from the bank, it does not collapse to width 0.
   - Instead, a placeholder bounding box `[ symbol ]` is computed with estimated width $1.2 \times \text{x\_height}$ and ascent equal to capital letters, preserving the surrounding formula layout.

### Rationale
- Avoids brittle regex/string manipulation for 2D math layout.
- Ensures formulas align naturally with adjacent handwritten text baselines.
- Missing symbols do not deform formulas or corrupt table cell alignment.

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
5. In `validate_bank_dict()`, allow v2 if `allow_legacy=True`, then `load_and_validate()` automatically runs the migration pipeline in memory.

### Rationale
- Fully preserves all existing user banks and test banks without requiring manual conversion scripts.
- Schema version progression is clear, audited, and strictly validated.

---

## 7. Backward Compatibility & Golden-Master Preservation

### Decision
1. Retain `chuviettay/model/composer.py` and `ctl.write_text(text, opts, out_path)` with their exact current logic.
2. Introduce `ctl.write_document(document: Document, opts: WriteOptions, out_path: str) -> WriteResult` as the new API for structured documents.
3. Keep `test_golden_master.py` untouched to continuously verify that SHA-256 hashes of standard text generation remain byte-identical.

### Rationale
- Guarantees 0 regression for existing users, automation scripts, and test suites.
- Decouples risk: new document features can evolve without threatening legacy stability.
