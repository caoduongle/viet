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
def get_importer_for_path(path: str) -> BaseImporter:
    """Detects and returns the appropriate importer for a given file path based on extension.
    
    Supported extensions:
    - .txt -> TxtImporter
    - .md, .markdown -> MarkdownImporter
    - .docx -> DocxImporter
    
    Raises:
        ValueError: If file extension is unsupported.
    """
```

---

## 4. Error Handling Contract

1. **`OptionalDependencyError`**:
   - Subclasses `RuntimeError`.
   - Raised when `MarkdownImporter` or `DocxImporter` is invoked but optional packages (`markdown-it-py`, `python-docx`) are not installed.
   - Message contract: MUST explain which command to run (e.g. `pip install ".[docs]"`).

2. **`CorruptedDocumentError`**:
   - Subclasses `ValueError`.
   - Raised when input file cannot be decoded as UTF-8 (for text/markdown) or is an invalid zip archive (for docx).

3. **`UnsupportedContentWarning`**:
   - Recorded inside `ImportResult.unsupported`.
   - Parsing MUST NOT crash upon encountering unsupported elements (images, SmartArt, audio); it logs the item in `ImportResult.unsupported` and continues parsing the remaining document.
