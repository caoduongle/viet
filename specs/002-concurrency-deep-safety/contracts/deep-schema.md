# Contract: Deep Schema & Runtime Invariants Validation

**Module**: `chuviettay.model.bank_schema`

## Overview
Enforces deep structural integrity on stroke coordinates and ensures all runtime-required metadata keys exist and are typed correctly.

## Signatures

```python
def validate_stroke(stroke: Any, path: str = "stroke") -> None:
    """Validate a single stroke coordinate list.
    
    Raises:
        BankValidationError: If stroke is not a list, has length < 2, has odd length,
                             or contains non-finite numbers (NaN/inf).
    """

def validate_sample(sample: Any, path: str = "sample") -> None:
    """Validate a sample dictionary containing strokes and stroke width.
    
    Raises:
        BankValidationError: If 's' or 'w' is missing/invalid, or 'w' <= 0 or not finite.
    """

def validate_bank_dict(d: dict[str, Any]) -> None:
    """Validate full bank dictionary including schema_version, words, deep strokes, and metadata.
    
    Verifies:
    1. 'schema_version' == 2.
    2. 'words' is a non-empty dict where each entry passes validate_sample.
    3. Required metadata keys ('line', 'width', 'wgaps', 'dgaps', 'v', 'x0', 'ratio')
       exist and have finite positive numeric values.
    
    Raises:
        BankValidationError: If any structure or value fails validation.
    """

def migrate_bank_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy bank dictionary to schema version 2 in-memory.
    
    For unversioned/v1 banks:
    - Adds 'schema_version': 2.
    - Backfills missing metadata keys ('line', 'width', 'wgaps', 'dgaps', 'v', 'x0', 'ratio')
      using standard defaults from chuviettay.config.
    
    Returns:
        The migrated dictionary.
    """
```

## Guarantees
- Any bank dictionary passing `validate_bank_dict()` is 100% immune to `KeyError` or `TypeError` when queried by `composer.py` or `xopp.py`.
- Error messages explicitly report the exact offending path, e.g. `"words['xin'][0]['s'][1]: stroke coordinate count must be even, got 3"`.
