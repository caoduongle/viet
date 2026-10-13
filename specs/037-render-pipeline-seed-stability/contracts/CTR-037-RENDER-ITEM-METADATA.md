# Contract CTR-037-RENDER-ITEM-METADATA: Cấu trúc RenderItem và Bảo toàn Metadata

## Mục đích
Quy định cấu trúc dữ liệu chính thức cho các mục kết xuất trong dòng chữ và ô bảng biểu, thay thế tuple rời rạc nhằm ngăn chặn việc đánh rơi metadata token trong toàn bộ pipeline kết xuất, đồng thời bảo đảm tương thích ngược 100% với cả cú pháp giải nén tuple (unpacking) và truy cập chỉ số (indexing).

---

## 1. Định nghĩa Giao diện RenderItem

Trong `chuviettay/layout/engine.py`:

```python
from dataclasses import dataclass, field
from typing import Any, Iterator
from chuviettay.model.bank import Stroke

@dataclass(slots=True)
class RenderItem:
    """Mục hiển thị trong dòng chữ với đầy đủ định danh token và nét vẽ."""
    start: float                          # Vị trí X tương đối trong dòng
    strokes: list[Stroke]                 # Danh sách các nét chữ
    width: float                          # Chiều rộng mục
    missing: list[str] = field(default_factory=list)  # Ký tự thiếu mẫu
    token: str = ""                       # Chuỗi token gốc
    token_id: str = ""                    # Định danh token trong phiên
    occurrence: int = 0                   # Thứ tự xuất hiện trong phạm vi khối/tài liệu

    def __iter__(self) -> Iterator[Any]:
        """Hỗ trợ giải nén tuple (unpacking: start, st, w = item[:3] hoặc a, b, c, d, e = item)."""
        yield self.start
        yield self.strokes
        yield self.width
        yield self.missing
        yield self.token
        yield self.token_id
        yield self.occurrence

    def __getitem__(self, idx: int) -> Any:
        """Hỗ trợ truy cập chỉ số kiểu tuple để tương thích ngược 100% với mã nguồn cũ."""
        if idx == 0: return self.start
        if idx == 1: return self.strokes
        if idx == 2: return self.width
        if idx == 3: return self.missing
        if idx == 4: return self.token
        if idx == 5: return self.token_id
        if idx == 6: return self.occurrence
        raise IndexError(f"Chỉ số RenderItem không hợp lệ: {idx}")

    def __len__(self) -> int:
        return 7
```

---

## 2. Quy tắc Chuyển đổi Pipeline

1. **Giai đoạn tách inline (`_layout_inlines`)**:
   - Khi tách từ/ký hiệu, mỗi mục được tạo thành đối tượng:
     ```python
     RenderItem(
         start=0.0,
         strokes=st,
         width=w * self.S * scale_mult,
         missing=miss,
         token=tok_str,
         token_id=f"{tok_str}#{occ}",
         occurrence=occ,
     )
     ```
2. **Giai đoạn ngắt dòng (`cur_line` trong `render_paragraph_inlines`)**:
   - Mảng `cur_line` lưu trữ các đối tượng `RenderItem`.
   - Vị trí `start` được cập nhật theo khoảng cách từ `sp`.
3. **Giai đoạn chuyển giao cho `_render_text_line`**:
   - `render_items = list(cur_line)`: Giữ nguyên vẹn danh sách đối tượng `RenderItem`, **tuyệt đối không nén** thành `[(start, st, w) for ...]`.
4. **Giai đoạn ô bảng (`cell_inlines_formatter`)**:
   - Các dòng trong ô bảng (`laid_cell.rendered_lines`) lưu trữ danh sách các đối tượng `RenderItem`.
   - Khi ngắt dòng qua trang trong bảng, các đối tượng `RenderItem` được bảo toàn nguyên vẹn metadata sang trang sau.
