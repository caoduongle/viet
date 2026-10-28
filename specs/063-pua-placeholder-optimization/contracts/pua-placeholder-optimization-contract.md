# Contract: Cơ chế chọn ký tự PUA và kiểm thử cạn kiệt

**Branch**: `063-pua-placeholder-optimization` | **Date**: 2026-10-28 | **Spec**: [spec.md](../spec.md)

---

## 1. Internal API Contract

### Phương thức: `MarkdownImporter._choose_fake_close_placeholder`

```python
@classmethod
def _choose_fake_close_placeholder(cls, text: str) -> str | None:
    """Chọn ký tự giữ chỗ cho dấu đóng giả từ vùng Private Use Area của BMP (U+E000..U+F8FF).
    
    Thuật toán:
    1. Nếu text rỗng hoặc U+E000 không có trong text: trả về U+E000 ngay lập tức (Fast-path O(1)).
    2. Nếu U+E000 có trong text (va chạm):
       - Lọc used_cps = {ord(c) for c in set(text) if _FAKE_CLOSE_PUA_START <= ord(c) <= _FAKE_CLOSE_PUA_END}.
       - Nếu len(used_cps) == _FAKE_CLOSE_PUA_COUNT: trả về None ngay (O(1) early exit).
       - Duyệt cp từ U+E001 đến U+F8FF: nếu cp not in used_cps thì trả về chr(cp).
    3. Trả về None nếu cạn kiệt.
    """
```

#### Tiền điều kiện (Preconditions)
- `text`: Chuỗi bất kỳ (`str`), có thể rỗng hoặc chứa hàng triệu ký tự.

#### Hậu điều kiện (Postconditions)
1. **Giá trị trả về (`str | None`)**:
   - Nếu trả về `str`: chuỗi có độ dài đúng bằng 1 (`len(result) == 1`).
   - Ký tự trả về nằm trong dải `[0xE000, 0xF8FF]` và đảm bảo `result not in text`.
   - Điểm mã là nhỏ nhất có thể trong dải không xuất hiện trong `text`.
   - Nếu trả về `None`: đảm bảo mọi ký tự `chr(cp)` với $cp \in [0xE000, 0xF8FF]$ đều xuất hiện trong `text`.
2. **Hiệu năng (Complexity Contract)**:
   - Khi `chr(0xE000) not in text`: Thời gian thực thi là $O(1)$ fast check (không duyệt set, không cấp phát thêm bộ nhớ).
   - Khi `chr(0xE000) in text`: Thời gian thực thi là $O(N)$ với $N = \operatorname{len}(text)$, chỉ duyệt chuỗi đúng 1 lần để gom `used_pua`.

---

## 2. Integration Fallback Contract

### Phương thức: `MarkdownImporter.import_text` và `MarkdownImporter._isolate_display_math_blocks`

Khi `fake_close_placeholder is None`:
- `_isolate_display_math_blocks(seg, fake_close_placeholder=None)` không thực hiện thay thế chuỗi trên bất kỳ dòng nào.
- Toàn bộ cây tài liệu được nhập bình thường.
- Không có bất kỳ ngoại lệ (Exception) nào được ném ra ngoài.
- Toàn bộ các ký tự PUA do người dùng cung cấp trong văn bản gốc được giữ nguyên vẹn trong các nút tương ứng của `Document`.

---

## 3. Test Cases Specification

| Mã ca kiểm thử | Mô tả kiểm thử | Dữ liệu đầu vào | Kết quả mong đợi |
| :--- | :--- | :--- | :--- |
| **C-FAST** | Fast-path khi văn bản không chứa U+E000 | `"Văn bản thông thường\n$$x=1$$"` | Trả về `"\ue000"` ngay lập tức |
| **C-EMPTY** | Fast-path khi văn bản rỗng | `""` | Trả về `"\ue000"` |
| **C-COLL-MULTI** | Va chạm chuỗi liên tiếp nhiều ký tự PUA đầu dãy | `"".join(chr(0xE000 + i) for i in range(10)) + " nội dung"` | Trả về `"\ue00a"` |
| **C-COLL-SPARSE** | Va chạm không liên tục (có khoảng trống ở giữa) | `"\ue000\ue002\ue003"` | Trả về `"\ue001"` (chọn vị trí trống đầu tiên) |
| **C-EXHAUST-NONE** | Cạn kiệt toàn bộ 6.400 ký tự PUA | `"".join(chr(cp) for cp in range(0xE000, 0xF8FF + 1))` | Trả về `None` |
| **C-EXHAUST-E2E** | Luồng `import_text` khi cạn kiệt PUA kèm blockquote math | Chuỗi 6.400 ký tự PUA + `"\n\n> $$\n> x = 1\n>> $$\n> x = 2\n> $$"` | `import_text` thành công, không ném exception, bảo toàn toàn bộ ký tự PUA gốc |
