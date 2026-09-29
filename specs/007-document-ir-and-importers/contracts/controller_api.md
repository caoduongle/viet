# Contract: AppController & Layout Engine API

**Feature**: `007-document-ir-and-importers`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Overview

`AppController` coordinates the flow between user interfaces (CLI/GUI), document importers, bank management, and the handwriting layout engine.

---

## 2. Controller Methods

### 2.1 Backward-Compatible Text API
```python
def write_text(self, text: str, opts: WriteOptions, out_path: str) -> WriteResult:
    """Legacy entry point: converts plain text to .xopp handwriting file.
    
    Guarantees:
    - Retains exact byte-for-byte SHA-256 output on golden-master benchmarks.
    - Zero modification to legacy random jitter or token assembly.
    """
```

### 2.2 Structured Document API
```python
def write_document(self, document: Document, opts: WriteOptions, out_path: str) -> WriteResult:
    """Renders a structured Document IR into .xopp handwriting format.
    
    Args:
        document: Document IR instance containing paragraphs, headings, tables, or math.
        opts: WriteOptions controlling scale, line spacing, margins, jitter, ink color.
        out_path: Target path for the generated .xopp file.
        
    Returns:
        WriteResult detailing lines, strokes, tokens, missing tokens, and missing symbols.
        
    Raises:
        BankError: If no bank is loaded or bank data is invalid.
        ValueError: If opts validation fails.
    """
```

### 2.3 File Import Entry Point
```python
def import_document(self, file_path: str) -> ImportResult:
    """Parses a file into Document IR using auto-detected importer.
    
    Args:
        file_path: Path to .txt, .md, or .docx file.
        
    Returns:
        ImportResult containing Document IR, warnings, and unsupported features.
        
    Raises:
        OptionalDependencyError: If optional parser package is missing.
        FileNotFoundError: If file does not exist.
    """
```

---

## 3. WriteResult Metrics Contract

`WriteResult` is extended with:
- `missing_symbols: dict[str, int]`: Dictionary mapping missing math symbols (e.g. `{"∑": 3, "≤": 1}`) to encounter counts.
- `missing_symbols_sorted() -> list[tuple[str, int]]`: Sorted descending by count, then alphabetically.
- `n_tables: int = 0`: Total tables rendered.
- `n_math_blocks: int = 0`: Total math blocks/formulas rendered.
