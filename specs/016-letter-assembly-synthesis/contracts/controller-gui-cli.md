# Contract: Controller, GUI & CLI Contracts

**Feature**: `016-letter-assembly-synthesis`  
**Files**: `chuviettay/controller/app_controller.py`, `chuviettay/view/*.py`, `chuviettay/cli.py`  

---

## 1. `AppController` Extensions

```python
class AppController:
    def teach_letter(
        self,
        letter: str,
        rel_strokes: list[Stroke],
        width: float,
        deferred_save: bool = False,
    ) -> TeachOutcome:
        """Lưu một mẫu chữ cái đơn lẻ vào kho mẫu."""

    def get_stats(self) -> BankStats:
        """Thống kê mở rộng bao gồm n_letters và letter_counts."""

    def missing_letters_for_words(
        self,
        words: list[str],
        strict_case: bool = False,
    ) -> list[tuple[str, int, list[str]]]:
        """Tính toán danh sách chữ cái thiếu kèm số lượng từ mở khoá."""
```

### `BankStats` Dataclass Extension
```python
@dataclass
class BankStats:
    n_words: int
    n_samples: int
    digit_counts: dict[str, int] = field(default_factory=dict)
    punct_counts: dict[str, int] = field(default_factory=dict)
    tone_mark_counts: dict[str, int] = field(default_factory=dict)
    n_letters: int = 0
    letter_counts: dict[str, int] = field(default_factory=dict)
```

---

## 2. CLI Contract

### `write` command
- New flag: `--assemble`
  - Action: Sets `opts.assemble_letters = True`.
  - Default: `False` (legacy whole-word behavior, 100% Golden Master parity).
- Output report:
  - If words were assembled, outputs:
    `"Đã tự động ghép %d từ từ các chữ cái mẫu." % len(result.assembled_words)`
  - If letters are missing, outputs:
    `"Các chữ cái cần dạy thêm để mở khoá các từ còn thiếu: %s" % ...`

### `stats` command
- Output includes:
  `"Chữ cái có mẫu: %d chữ cái (%d mẫu)" % (stats.n_letters, sum(stats.letter_counts.values()))`

---

## 3. GUI Contract

### `WriteTab`
- Checkbox: `"Ghép từ chữ cái (Assembly fallback)"` bound to `self.v_assemble` (BooleanVar, default `True` on GUI for optimal user experience, while CLI and programmatic defaults remain `False` for backward compatibility, or default `False` configurable).
- Results Section:
  - Text area lists assembled words: `"Từ ghép tự động: ..."`
  - Listbox displays missing letters: `"Chữ cái còn thiếu (mở khoá X từ)"`
  - Button: `"Dạy các chữ cái này →"` triggers `on_teach_missing(missing_letters)`.

### `TeachTab`
- Canvas accepts single letters (width and baseline calculated identically).
- When a single letter is saved, routed via `ctl.teach_letter()`.

### `BankTab`
- Stats label displays letter counts.
- Filter list supports tab/filter toggle between "Từ", "Chữ cái", "Ký hiệu".
- Selected letter can be dropped via `ctl.drop_letter()`.
