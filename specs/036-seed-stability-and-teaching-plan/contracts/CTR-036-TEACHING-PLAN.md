# Contract: Kế hoạch Dạy chữ Cốt lõi & Đồng bộ Hàng đợi (CTR-036-TEACHING-PLAN)

**Mã hợp đồng**: `CTR-036-TEACHING-PLAN`  
**Gói công việc**: Kế hoạch Dạy chữ (Teaching Plan)  
**Ngày ban hành**: 2026-10-13  
**Trạng thái**: Ratified

---

## 1. Định nghĩa 38 Mục Ký tự Cốt lõi (`CORE_ESSENTIALS_38`)

### 1.1 Vị trí Áp dụng
- File: `chuviettay/model/seed_words.py`

### 1.2 Danh sách Cốt lõi
```python
from chuviettay.model.char_catalog import TONE_MARKS, VIETNAMESE_LOWERCASE

CORE_ESSENTIALS_38: tuple[str, ...] = VIETNAMESE_LOWERCASE + TONE_MARKS


def get_core_essentials_38() -> list[str]:
    """Trả về 38 mục ký tự cốt lõi (33 chữ cái thường và 5 dấu thanh rời),
    đủ điều kiện ghép và viết được 100% (700/700) từ trong tập từ điển thông dụng SEED."""
    return list(CORE_ESSENTIALS_38)
```

### 1.3 Mục tiêu Phủ Kín 100% Từ điển SEED
- 33 chữ cái thường: `a, ă, â, b, c, d, đ, e, ê, g, h, i, k, l, m, n, o, ô, ơ, p, q, r, s, t, u, ư, v, x, y, f, j, w, z`
- 5 dấu thanh rời chuẩn hw3: `dấu sắc, dấu huyền, dấu hỏi, dấu ngã, dấu nặng`
- Bất kỳ kho mẫu nào nạp đủ 38 mục này thì `Bank.can(w)` đều trả về `True` cho mọi $w \in \text{SEED}$ (tổng 700 từ).

---

## 2. Đồng bộ `Bank.can()` với Mẫu Nguyên Khối (`bank.words`)

### 2.1 Vị trí Áp dụng
- File: `chuviettay/model/bank.py` (phương thức `can`)

### 2.2 Đặc tả Cập nhật
```python
def can(self, w: str, strict_case: bool = False) -> bool:
    w_clean = w.strip()
    if not w_clean:
        return False

    with self._lock:
        # 1. Ký tự chữ số, dấu câu, ký hiệu đã có mẫu
        if w_clean in self.digits or w_clean in self.punct or w_clean in getattr(self, "symbols", {}):
            return True

        # 2. Dấu thanh rời đã có mẫu
        if w_clean in self.marks and bool(self.marks.get(w_clean)):
            return True

        # 3. Từ nguyên khối đã được dạy trong bank.words (Gỡ tắc nghẽn hàng đợi dạy chữ)
        if getattr(self, "words", None) and w_clean in self.words and bool(self.words.get(w_clean)):
            return True

        # 4. Kiểm tra khả năng ghép chữ qua các chữ cái và dấu thanh cấu thành
        letters_dict = getattr(self, "letters", {})
        if not letters_dict:
            return False

        import unicodedata
        nfc_chars = list(unicodedata.normalize("NFC", w_clean))
        if all(ch in letters_dict or (not strict_case and ch.isupper() and ch.lower() in letters_dict) for ch in nfc_chars):
            return True

        from chuviettay.model.text_utils import split_letters
        chars, T, _ = split_letters(w_clean)
        if not chars:
            return False
        if T and not bool(self.marks.get(T)):
            return False
        return all(ch in letters_dict or (not strict_case and ch.isupper() and ch.lower() in letters_dict) for ch in chars)
```

---

## 3. Hàng đợi Gợi ý Dạy chữ (`AppController`)

### 3.1 Vị trí Áp dụng
- File: `chuviettay/controller/app_controller.py`

### 3.2 Đặc tả Gợi ý Thứ tự Học
- `missing_minimal_essentials()`:
  - Khi kho mẫu còn thiếu các ký tự trong `CORE_ESSENTIALS_38`, ưu tiên trả về các ký tự cốt lõi còn thiếu trước các từ ghép đa ký tự.
  - Khi người dùng dạy một từ bất kỳ bằng `teach_char(label)`, sau khi lưu, `Bank.can(label)` ngay lập tức trả về `True`, gỡ bỏ triệt để `label` khỏi danh sách gợi ý.
