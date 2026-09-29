# Contract: Incremental Indexing for Word Teaching

**Module**: `chuviettay.model.bank` & `chuviettay.controller.app_controller`

## Overview
Replaces full-dictionary re-indexing with incremental token index maintenance when teaching new words, ensuring linear performance scaling as banks grow to tens of thousands of samples.

## Signatures

```python
class Bank:
    def add_sample_incremental(self, word: str, sample: dict[str, Any]) -> None:
        """Add a word sample and incrementally update vocab and token caches.
        
        Avoids full self.rebuild() over all unaffected words.
        
        Args:
            word: The word string.
            sample: The validated sample dictionary.
        """

class AppController:
    def teach_word(self, word: str, sample: dict[str, Any]) -> None:
        """Teach a new word sample and persist changes reliably.
        
        Calls self.bank.add_sample_incremental(word, sample) followed by
        atomic self.bank.save().
        """
```

## Guarantees
- Time complexity of adding a sample to a bank with $N$ existing words is $O(1)$ in memory (plus file I/O for save), rather than $O(N)$ for full dictionary indexing.
- Preserves identical token lookup behavior in `writer.py` and `composer.py`.
