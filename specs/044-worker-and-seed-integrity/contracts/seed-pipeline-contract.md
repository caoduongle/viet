# Interface Contract: Seed Pipeline & Canonical Serialization (CTR-044-SEED-PIPELINE)

**Status**: Active
**Version**: 2.0.0
**Feature**: `specs/044-worker-and-seed-integrity`

---

## 1. Scope & Purpose
Hợp đồng này quy định chi tiết cách thức sinh số ngẫu nhiên, biểu diễn khóa chuẩn tắc và bảo toàn danh tính hạt giống xuyên suốt pipeline kết xuất (từ Document IR, DocumentLayoutEngine, FidelityLayoutEngine tới Writer).

---

## 2. Canonical Serialization Contract (`encode_canonical_key`)

### 2.1 Supported Types and Format
Mọi phần tử tham gia dẫn xuất hạt giống phải được mã hóa theo định dạng:
`[1-byte tag] + [4-byte big-endian unsigned length] + [normalized payload]`

```python
def encode_canonical_key(val: Any) -> bytes: ...
```

- **Type `NoneType`**: `b"n\x00\x00\x00\x00"`
- **Type `bool`**: `b"?" + struct.pack(">I", 1) + (b"\x01" if val else b"\x00")`
- **Type `int`**: `b"i" + struct.pack(">I", len(ascii_str)) + ascii_str` (ASCII decimal string)
- **Type `float`**: `b"f" + struct.pack(">I", 8) + struct.pack(">d", val)`
- **Type `str`**: `b"s" + struct.pack(">I", len(utf8_bytes)) + utf8_bytes` (Unicode NFC normalized)
- **Type `bytes` / `bytearray`**: `b"b" + struct.pack(">I", len(val)) + bytes(val)`
- **Type `SeedContext`**: `b"c" + struct.pack(">I", 5) + encode_canonical_key(field)...`
- **Type `tuple` / `list`**: `b"t" + struct.pack(">I", len(val)) + encode_canonical_key(item)...`

### 2.2 Strict Rejection Clause
Nếu `val` không thuộc bất kỳ kiểu dữ liệu nào ở mục 2.1, hàm `encode_canonical_key(val)` **BẮT BUỘC** ném `TypeError`:
```python
raise TypeError(f"Unsupported key type for canonical encoding: {type(val).__name__}")
```
Tuyệt đối không được fallback chuyển đổi âm thầm sang `str(val)`.

---

## 3. Context-Bound RNG Derivation Contract

Mọi lệnh gọi `ScopedRNG` trong `Writer` và `LayoutEngine` phải truyền `content_type` làm tham số phân vùng không gian tên:

### 3.1 Variant Selection
```python
ScopedRNG(master_seed, ctx_type, token, occurrence, "variant", tag, char_index)
```
- `ctx_type`: Bắt buộc truyền giá trị từ `context.content_type` (`"text"`, `"cell"`, `"sym"`, `"heading"`, `"math"`).
- Cấm sử dụng hằng số tĩnh `"tok"`.

### 3.2 Jitter Sampling
```python
ScopedRNG(master_seed, ctx_type, token, occurrence, "jitter", char_index)
```

### 3.3 Digit Gap (dgap)
```python
ScopedRNG(master_seed, ctx_type, token, occurrence, "dgap", digit_index)
```

---

## 4. Recursive IR Seed Alignment Contract (`align_document_seeds`)

1. **Full IR Coverage**:
   Thuật toán `extract_doc_elements(doc)` bắt buộc duyệt qua:
   - `Paragraph`, `Heading`
   - `ListBlock`: Duyệt đệ quy tất cả các mục danh sách `item_blocks: list[Block]` trong `block.items`, bao gồm các đoạn văn `Paragraph`, công thức và danh sách con lồng nhau.
   - `Table`: Duyệt tất cả các hàng (`rows`), ô (`cells`) và các khối (`blocks`) bên trong ô.
   - `MathBlock` & `MathInline`
   - `Symbol`

2. **Chunked Token Invariance**:
   - Khi một `Text` inline có `inline.token_occurrences`, mảng này được đánh chỉ số theo từng **token nguyên bản** trong câu (`_normalize_text(text).split()`).
   - Nếu một token bị chia nhỏ thành nhiều đoạn (`chunks`) do vượt chiều rộng khả dụng:
     - Tất cả các đoạn của cùng token này sử dụng chung `occurrence` của token mẹ.
     - Phân biệt các đoạn bằng `ctx.sub_index = chunk_idx`.
     - Chỉ số `inline_tok_idx` trong `_layout_inlines` chỉ tăng 1 lần sau khi đã xử lý xong toàn bộ các chunks của token mẹ.
