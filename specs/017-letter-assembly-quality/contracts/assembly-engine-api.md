# Contract: Letter Assembly Engine API

**Feature Branch**: `017-letter-assembly-quality`  
**Date**: 2026-10-03  
**Spec**: [spec.md](../spec.md)  
**Status**: Active  

---

## 1. Overview & Architectural Boundaries

The Letter Assembly Engine resides in the pure domain model layer (`chuviettay/model/writer.py`). It adheres strictly to the project constitution:
- **Zero UI / CLI imports**: No imports of `tkinter`, `argparse`, `view`, or `controller`.
- **Zero I/O side-effects**: No `print()`, `sys.exit()`, or disk writes.
- **Zero external dependencies**: Standard library only (`math`, `random`, `unicodedata`, `dataclasses`).

---

## 2. Public Interface Contracts

### 2.1 `Writer.assemble_word`

Synthesizes a single word from individual character samples with boundary contour spacing and stroke clearance enforcement.

```python
def assemble_word(
    self,
    word: str,
    letter_gap: float = 1.0,
    pen_clearance_factor: float = 0.8,
) -> tuple[list[Stroke], float] | None:
    """Ghép một từ từ các chữ cái đơn lẻ và dấu thanh theo mô hình kerning biên.

    Args:
        word: Từ cần ghép (chuỗi unicode bất kỳ).
        letter_gap: Hệ số nhân khoảng cách giữa các chữ cái (mặc định 1.0).
        pen_clearance_factor: Hệ số sàn khe hở tối thiểu theo độ dày bút (mặc định 0.8).

    Returns:
        (strokes, total_width) nếu ghép thành công.
        None nếu thiếu chữ cái hoặc dấu thanh bắt buộc.
    """
```

**Preconditions**:
- `word` is a non-empty string.
- If `word` contains letters not present in `bank.letters` (or `bank.words` fallback) and lacks whole-word samples, method returns `None` cleanly.

**Postconditions**:
- Output `strokes` are relative to the word origin $(0, 0)$.
- For all adjacent letter pairs, minimum physical point distance $\ge \text{pen\_clearance\_factor} \times \text{pen\_thickness}$.
- Bounding-box overlap between adjacent characters $\le 10\%$ of $\min(\text{width}(A), \text{width}(B))$.
- If vowel is `i` or `j` with an upper tone mark, the dot stroke is stripped.

---

### 2.2 Dual-Path Character Lookup Contract

```python
def get_letter_sample(
    self,
    char: str,
    strict_case: bool = False,
) -> dict | None:
    """Tìm mẫu chữ cái theo thứ tự ưu tiên:
    1. bank.letters[char]
    2. bank.letters[char.lower()] (nếu không strict_case)
    3. bank.words[char] (nếu len(char) == 1)
    4. bank.words[char.lower()] (nếu không strict_case và len(char) == 1)
    5. None nếu không tìm thấy.
    """
```

---

### 2.3 `Writer.word` Cascade Contract

```python
def word(self, w: str) -> tuple[list[Stroke], float, bool]:
    """Tìm hoặc ghép nét cho một từ theo thứ tự ưu tiên:
    1. bank.words[w] (mẫu nguyên từ - ưu tiên số 1, bảo tồn liên kết tự nhiên)
    2. self.substitute(w) (thay thế dấu thanh trên từ gốc)
    3. self.assemble_word(w) (nếu assemble_letters=True)
    4. Khoảng trống ước lượng nếu không có mẫu.

    Returns:
        (strokes, width, is_missing_flag)
    """
```

**Golden Master Guarantee**:
If `self.assemble_letters` is `False` (default), branch 3 is completely bypassed, producing 100% identical outputs to legacy synthesis engines.
