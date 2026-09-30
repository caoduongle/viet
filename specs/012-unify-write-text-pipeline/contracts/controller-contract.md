# Interface Contract: Controller & Options Validation

**Feature**: `012-unify-write-text-pipeline` | **Date**: 2026-09-30

---

## 1. AppController Contract

### `write_text(self, text: str, opts: WriteOptions, out_path: str) -> WriteResult`
- **Purpose**: Render raw text into a handwriting `.xopp` file using the unified `DocumentLayoutEngine`.
- **Preconditions**:
  - `self.bank` is loaded (raises `BankNotFoundError` or `BankError` if missing).
  - `opts` passes `opts.validate()`.
- **Processing**:
  1. Validates options via `opts.validate()`.
  2. Converts `text` to `Document` IR via `TxtImporter().import_text(text).document`.
  3. Instantiates `DocumentLayoutEngine(self.bank, opts)`.
  4. Returns `engine.render(doc, out_path)`.
- **Postconditions**:
  - The generated file at `out_path` contains exact page dimensions and background tags matching `opts.resolve_page_format()`.
  - Memory-safe streaming via `PageBuffer` ensures temporary files are cleaned up on failure.

---

## 2. WriteOptions Validation Contract

### `validate(self) -> None`
- **Errors Raised**:
  - `ValueError`: If any margin value is negative or non-finite.
  - `ValueError`: If `self.margin_left + self.margin_right >= effective_width`.
  - `ValueError`: If `self.margin_top + self.margin_bottom >= effective_height`.
  - `ValueError`: If paper size or background options are invalid.
