# Contract: Single-Source Render Readiness

**Specification Version**: 1.0.0  
**Feature**: 028-char-first-alignment-and-ci-repair  
**Module**: `chuviettay.model.bank` & `chuviettay.model.writer`  

---

## 1. Overview
Hợp đồng này quy định quy tắc duy nhất để xác định một từ/token có thể kết xuất được ra trang viết tay hay không. Mọi thành phần trong hệ thống (`Bank.can()`, `Writer.word()`, `AppController.missing_letters_for_words()`, `CLI`) PHẢI tuân thủ 100% logic này mà không có ngoại lệ hoặc nhánh rẽ riêng.

---

## 2. API Signatures

### 2.1 `Bank.can(w: str) -> bool`
Kiểm tra xem kho mẫu hiện tại có đủ mẫu để kết xuất token/từ `w` hay không.

- **Đầu vào**: `w` (chuỗi token hoặc từ tiếng Việt cần kiểm tra, ví dụ: `"xin"`, `"bà"`, `"123"`, `","`, `"+"`, `"dấu sắc"`).
- **Đầu ra**: `bool` (`True` nếu có thể viết được; `False` nếu thiếu ít nhất 1 thành phần).

### 2.2 `Writer.word(core: str) -> tuple[list[Stroke], float, list[str]] | None`
Kết xuất một từ thành các nét viết tay.
- **Bất biến**:
  $$\text{Writer.word}(w) \ne \text{None} \iff \text{Bank.can}(w) == \text{True}$$

---

## 3. Quy Tắc Phân Giải (Resolution Algorithm)

```python
def can_render_token(bank, w: str) -> bool:
    w_clean = w.strip()
    if not w_clean:
        return False

    # 1. Khớp trực tiếp ký tự đặc thù hoặc nhãn đơn lẻ
    if w_clean in bank.digits or w_clean in bank.punct or w_clean in getattr(bank, "symbols", {}):
        return True

    # 2. Nhãn dấu thanh rời
    if w_clean in bank.marks and bool(bank.marks[w_clean]):
        return True

    letters_dict = getattr(bank, "letters", {})

    # 3. Path 1: Thử khớp tất cả ký tự nguyên khối NFC trong bank.letters
    nfc_chars = list(unicodedata.normalize("NFC", w_clean))
    if all(ch in letters_dict or (ch.isupper() and ch.lower() in letters_dict) for ch in nfc_chars):
        return True

    # 4. Path 2: Phân tách dấu thanh rời
    from chuviettay.model.text_utils import split_letters
    chars, T, _ = split_letters(w_clean)
    if not chars:
        return False

    # Nếu có dấu thanh nhưng không có mẫu dấu thanh trong bank.marks -> Thất bại
    if T and not bool(bank.marks.get(T)):
        return False

    # Tất cả chữ cái thân phải có mẫu trong letters
    return all(ch in letters_dict or (ch.isupper() and ch.lower() in letters_dict) for ch in chars)
```

---

## 4. Các Quy Định Cấm (Prohibitions)

1. **CẤM** kiểm tra `w in bank.words` hoặc `strip_tone(w) in bank.tl` trong quy trình kiểm tra khả năng viết.
2. **CẤM** báo `True` cho một từ khi kho chỉ có mẫu nguyên từ cũ nhưng thiếu các chữ cái cấu thành.
3. **CẤM** tạo fallback sinh nét ngầm nếu không có sự đồng thuận của bộ kiểm tra độ sẵn sàng.
