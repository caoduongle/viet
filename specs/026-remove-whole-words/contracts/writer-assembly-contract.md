# Contract: Pure Character Assembly Writer API

**Module**: `chuviettay.model.writer`
**Feature**: `026-remove-whole-words`
**Date**: 2026-10-06

## 1. Phương thức Kết xuất Từ: `Writer.word(core)`

### Chữ ký hàm
```python
def word(self, core: str) -> tuple[list[Stroke], float] | None:
    """Ghép từ `core` từ các ký tự mẫu đơn lẻ.
    
    Phương thức này KHÔNG tra cứu `bank.words` và KHÔNG gọi `substitute()`.
    
    Returns:
        tuple[list[Stroke], float]: (danh sách nét, độ rộng từ) nếu ghép thành công.
        None: Nếu thiếu bất kỳ ký tự hoặc dấu thanh nào trong kho mẫu.
    """
```

### Luồng xử lý
1. Chuẩn hóa `core` (loại bỏ khoảng trắng biên).
2. Tạo danh sách các biến thể viết hoa/thường: `variants = [core, core.lower()] if self.loose else [core]`.
3. Với mỗi biến thể `c`:
   - Gọi `r = self.assemble_word(c)`.
   - Nếu `r` thành công: ghi nhận `self.assembled.append(core)` và trả về `r`.
4. Nếu duyệt hết các biến thể mà không thành công:
   - Trả về `None` (không fallback sang `bank.words` hay `substitute`).

---

## 2. Phương thức Lấy Mẫu Ký tự Đơn: `Writer.get_letter_sample(char)`

### Chữ ký hàm
```python
def get_letter_sample(self, char: str) -> dict | None:
    """Lấy mẫu cho ký tự đơn `char` theo thứ tự ưu tiên:
    1. bank.letters[char]
    2. bank.letters[char.lower()] (nếu loose và char viết hoa)
    3. bank.digits[char] (nếu char là chữ số)
    4. bank.punct[char] (nếu char là dấu câu)
    5. bank.symbols[char] (nếu char là ký hiệu)
    6. get_vector_glyph_fallback(char, xh) (nét vector dự phòng)
    
    TUYỆT ĐỐI KHÔNG tra cứu `bank.words`.
    """
```

---

## 3. Phương thức Phân tích Token: `Writer.token(tok)`

### Chữ ký hàm
```python
def token(self, tok: str) -> tuple[list[Stroke], float, list[str]]:
    """Phân tích một token thành (danh sách nét, độ rộng, danh sách ký tự còn thiếu).
    
    Không còn tra cứu nguyên khối `tok in bank.words`.
    Token được phân rã thành: lead (ký tự đầu) + core (thân từ / số) + trail (ký tự cuối).
    """
```

### Luồng xử lý
1. Kiểm tra trực tiếp các danh mục đơn lẻ nếu `len(tok) == 1`:
   - Nếu `tok in bank.digits`: trả về mẫu số.
   - Nếu `tok in bank.punct`: trả về mẫu dấu câu.
   - If `tok in bank.symbols`: trả về mẫu ký hiệu.
2. Phân rã regex: `lead, core, trail = TOKRE.match(tok).groups()`.
3. Duyệt `ch in lead`: lấy mẫu từ `punct` / `symbols` / `letters`; nếu thiếu thêm vào `miss`.
4. Xử lý `core`:
   - Nếu là số (`NUMRE.match(core)`): gọi `self.number(core)`.
   - Nếu là chữ: gọi `self.word(core)`. Nếu không ghép được, ghi nhận các ký tự thiếu cấu thành `core` vào `miss`.
5. Duyệt `ch in trail`: lấy mẫu từ `punct` / `symbols` / `letters`; nếu thiếu thêm vào `miss`.
