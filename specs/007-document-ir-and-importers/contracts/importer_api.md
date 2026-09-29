# Contract: Importer API

**Feature**: `007-document-ir-and-importers`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Overview

The Importer API defines the contract between file parsers and the handwriting engine. All importers transform specific source representations into a standard `Document` Intermediate Representation (IR).

---

## 2. Base Interface

```python
from abc import ABC, abstractmethod
from chuviettay.document.ir import Document
from chuviettay.importer.result import ImportResult

class BaseImporter(ABC):
    """Abstract base class for all file and string importers."""

    @abstractmethod
    def import_file(self, path: str) -> ImportResult:
        """Parse a document from a file path on disk.
        
        Args:
            path: Absolute or relative file path to the source file.
            
        Returns:
            ImportResult containing Document IR, warnings, and unsupported features.
            
        Raises:
            FileNotFoundError: If the file does not exist.
            OptionalDependencyError: If required third-party parser is not installed.
            ImportError / ValueError: If the file is physically corrupted or unreadable.
        """
        ...

    @abstractmethod
    def import_text(self, text: str) -> ImportResult:
        """Parse a document from an in-memory string.
        
        Args:
            text: Raw string content.
            
        Returns:
            ImportResult containing Document IR, warnings, and unsupported features.
        """
        ...
```

---

## 3. Importer Registry & Factory

```python
def get_importer_for_path(path: str, format_name: str = "auto") -> BaseImporter:
    """Detects and returns the appropriate importer for a given file path based on extension or explicit format.
    
    Supported extensions:
    - .txt -> TxtImporter
    - .md, .markdown -> MarkdownImporter
    - .docx -> DocxImporter
    
    Raises:
        UnsupportedFormatError: If file extension or format name is not in the supported set.
    """
```

---

## 4. Error Handling & Diagnostics Contract

1. **`UnsupportedFormatError`**:
   - Subclasses `ValueError`.
   - Raised immediately by `get_importer_for_path()` when an unrecognized file extension (e.g. `.pdf`, `.xlsx`, `.jpg`, `.zip`) is provided.

2. **`OptionalDependencyError`**:
   - Subclasses `RuntimeError`.
   - Raised when `MarkdownImporter` or `DocxImporter` is invoked but optional packages (`markdown-it-py`, `python-docx`) are not installed.
   - Message contract: MUST explain exact command to run: `pip install ".[docs]"`.

3. **`CorruptedDocumentError`**:
   - Subclasses `ValueError`.
   - Raised when input file cannot be decoded as UTF-8 (for text/markdown) or is an invalid zip archive (for docx).

4. **Diagnostics Differentiation**:
   - **`ImportResult.warnings`**: Non-blocking formatting adjustments (e.g. padding jagged table rows, heading level clamped to 1..6).
   - **`ImportResult.unsupported`**: Content elements that cannot be rendered into handwriting strokes (e.g. `OMML: m:m (Matrix)`, `drawing: embedded image`, `pict: drawing shape`). Parsing MUST NOT crash upon encountering unsupported elements; it logs them and continues.
