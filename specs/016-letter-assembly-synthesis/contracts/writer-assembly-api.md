# Contract: Writer Assembly & Text Utilities API

**Feature**: `016-letter-assembly-synthesis`  
**File**: `chuviettay/model/text_utils.py` & `chuviettay/model/writer.py`  

---

## 1. `text_utils.split_letters`

Decomposes a single Vietnamese word into atomic base letters in NFC and its tone mark metadata.

```python
def split_letters(word: str) -> tuple[list[str], str, int]:
    """Phân tách một từ tiếng Việt thành danh sách chữ cái cơ sở (NFC), dấu thanh và vị trí nguyên âm mang dấu.
    
    Args:
        word: Từ tiếng Việt (đã chuẩn hoá NFC hoặc bất kỳ dạng Unicode nào).
        
    Returns:
        letters: Danh sách chữ cái cơ sở (NFC) không chứa dấu thanh (ví dụ: 'đ', 'ư', 'ơ', 'n', 'g').
        tone: Ký tự dấu thanh Unicode (trong config.TONES) hoặc "" nếu không có dấu thanh.
        vowel_index: Chỉ số của nguyên âm mang dấu thanh trong danh sách `letters` (-1 nếu không có).
        
    Invariants:
        - Chuẩn hoá đầu ra ở dạng NFC.
        - Giữ nguyên các chữ cái có mũ/móc/gạch (ă, â, đ, ê, ô, ơ, ư).
        - Chỉ bóc tách 5 dấu thanh (huyền, sắc, hỏi, ngã, nặng).
    """
```

### Examples
- `split_letters("bà") -> (['b', 'a'], '\u0300', 1)`
- `split_letters("đường") -> (['đ', 'ư', 'ơ', 'n', 'g'], '\u0300', 2)`
- `split_letters("chào") -> (['c', 'h', 'a', 'o'], '\u0300', 2)`
- `split_letters("học") -> (['h', 'o', 'c'], '\u0323', 1)`
- `split_letters("ba") -> (['b', 'a'], "", -1)`

---

## 2. `text_utils.missing_letters_ranked`

Computes the greedy set-cover ranking of missing character units needed to unlock unlearned words.

```python
def missing_letters_ranked(
    missing_words: list[str],
    bank_letters: dict[str, list[dict]],
    bank_marks: dict[str, list[dict]],
    strict_case: bool = False,
) -> list[tuple[str, int, list[str]]]:
    """Xác định các chữ cái và dấu thanh còn thiếu, sắp xếp theo thuật toán tham lam (greedy set-cover).
    
    Args:
        missing_words: Danh sách các từ chưa có mẫu hoặc chưa thể ghép.
        bank_letters: Từ điển chữ cái đã học trong kho.
        bank_marks: Từ điển dấu thanh đã gặt được trong kho.
        strict_case: Có phân biệt hoa thường nghiêm ngặt hay không.
        
    Returns:
        Danh sách [(ký_tự_thiếu, số_từ_mở_khoá, [danh_sách_từ_mở_khoá]), ...]
        được sắp xếp giảm dần theo số lượng từ mở khoá được.
    """
```

---

## 3. `Writer.assemble_word`

Synthesizes an unlearned word from learned letter samples and tone marks.

```python
class Writer:
    def assemble_word(self, core: str) -> tuple[list[Stroke], float] | None:
        """Ghép một từ từ các mẫu chữ cái đơn lẻ trong bank.letters và dấu thanh rời trong bank.marks.
        
        Args:
            core: Từ tiếng Việt cần ghép (đã tách dấu câu).
            
        Returns:
            (strokes, width): Danh sách nét vẽ tương đối và độ rộng tổng của từ,
            hoặc None nếu thiếu ít nhất một chữ cái cấu thành hoặc thiếu dấu thanh cần thiết.
            
        Rules:
            1. Tìm mẫu cho từng chữ cái (có hỗ trợ loose-case hạ chữ hoa đầu nếu không có mẫu hoa).
            2. Xếp chữ cái nối tiếp nhau dọc theo baseline y = 0.
            3. Áp dụng độ chồng lấn (kerning) tự nhiên giữa các nét chữ liền kề.
            4. Nếu từ có dấu thanh, định vị tâm nguyên âm (vowel_x) và gắn dấu thanh rời vào đỉnh hoặc đáy.
            5. Nếu nguyên âm mang dấu thanh trên là 'i', loại bỏ nét chấm (dot) của chữ 'i' trước khi gắn dấu.
        """
```

---

## 4. `Writer.word` (Resolution Cascade)

```python
def word(self, core: str) -> tuple[list[Stroke], float] | None:
    """Ghép một từ theo cascade 4 bậc:
    1. Khớp thẳng mẫu nguyên từ (bank.words).
    2. Thay thế thân từ + dấu thanh rời (substitute).
    3. Ghép từ các mẫu chữ cái (assemble_word) - CHỈ KHI self.assemble_letters == True.
    4. Trả về None (để token() tính khoảng trống và báo thiếu).
    """
```
