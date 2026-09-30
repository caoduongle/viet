# Technical Research: Unify Direct Text Input into Document IR Pipeline & Margin Validation

**Feature**: `012-unify-write-text-pipeline` | **Date**: 2026-09-30

---

## 1. Direct Text Input to Document IR Transformation

### Decision
Implement `AppController.write_text()` as a clean wrapper around the unified Document IR pipeline using `TxtImporter`.

```python
def write_text(self, text: str, opts: WriteOptions, out_path: str) -> WriteResult:
    opts.validate()
    bank = self._require_bank()
    from chuviettay.importer.txt_importer import TxtImporter
    from chuviettay.layout.engine import DocumentLayoutEngine

    doc = TxtImporter().import_text(text).document
    engine = DocumentLayoutEngine(bank, opts)
    return engine.render(doc, out_path)
```

### Rationale
- `TxtImporter().import_text(text).document` already handles paragraphs, empty paragraph line spacing, and unicode text normalization into IR `Document`.
- Eliminates dual layout algorithms: direct GUI input, GUI imported files, CLI `-t`, CLI `-f`, and API calls all traverse the identical layout and pagination engine (`DocumentLayoutEngine`).
- Directly satisfies the user's architectural requirement: a single, unified layout pipeline.

### Alternatives Considered
- *Constructing `Document(blocks=[Paragraph(inlines=[Text(text=text)])])` directly*: Does not preserve empty lines (`\n\n`) as paragraph spacing, leading to visual differences when typing multi-paragraph notes.
- *Maintaining two separate engines (`composer` vs `engine`)*: Violates KISS and DRY, leads to divergence where features like paper sizing only work on imported documents.

---

## 2. Margin Boundary Validation in `WriteOptions.validate()`

### Decision
In `WriteOptions.validate()`, resolve the effective page dimensions via `self.resolve_page_format()` (which swaps width and height if `orientation == "landscape"`), and assert:
```python
pf = self.resolve_page_format()
if self.margin_left + self.margin_right >= pf.width:
    raise ValueError(
        f"Tổng lề trái ({self.margin_left} pt) và lề phải ({self.margin_right} pt) "
        f"phải nhỏ hơn bề ngang trang ({pf.width} pt)."
    )
if self.margin_top + self.margin_bottom >= pf.height:
    raise ValueError(
        f"Tổng lề trên ({self.margin_top} pt) và lề dưới ({self.margin_bottom} pt) "
        f"phải nhỏ hơn bề dọc trang ({pf.height} pt)."
    )
```

### Rationale
- Evaluates against the true effective width/height after orientation (portrait vs landscape) and unit parsing (mm, cm, in $\to$ pt) are applied.
- Catches edge-case misconfigurations immediately at initialization/validation time before any layout calculations occur.
- Replaces silent clamping to `20.0 pt` with explicit, helpful error feedback.

### Alternatives Considered
- *Validating in `PageFormat.__post_init__`*: `PageFormat` is a frozen data class in the document domain; performing validation at `WriteOptions.validate()` preserves user-friendly error messages at the configuration boundary and prevents bad options from ever instantiating downstream components.

---

## 3. Deprecation and Role of Legacy `composer.py`

### Decision
Mark `composer.compose_document()` and `composer.write_document()` as deprecated with explicit docstrings. Keep `composer.write_document` accessible solely for backward-compatibility verification (e.g. testing legacy baseline behavior).

### Rationale
- Avoids abrupt breakage for any external scripts or test suites that imported `composer.write_document`.
- Signals clearly to maintainers that all new layout and rendering capabilities belong in `DocumentLayoutEngine`.

---

## 4. Test Fortification Strategy for Direct GUI Text

### Decision
In `tests/test_gui_document.py`:
- In `test_gui_write_tab_paper_and_background_options`:
  1. Insert direct text into `app.write_tab.text`.
  2. Assert `assert app.write_tab.current_doc is None`.
  3. Select A3, Landscape, Ô Li (Graph).
  4. Execute `app.write_tab.do_write()`.
  5. Decompress the generated `.xopp` file and assert `<page width="1190.55" height="841.89">` and `<background ... style="graph" .../>` are present.

### Rationale
- Guarantees that typing directly in the GUI without opening a file exercises `ctl.write_text` and uses the unified `DocumentLayoutEngine` with full paper options.
