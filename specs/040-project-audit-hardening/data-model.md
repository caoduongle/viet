# Data Model: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng (Project Audit & Hardening)

**Feature Branch**: `040-project-audit-hardening`  
**Date**: 2026-10-16  
**Status**: Completed  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Mô hình Căn lề Đoạn văn (Paragraph Alignment Model)

### 1.1 Thực thể `Paragraph` (trong `chuviettay.document.ir`)
Thuộc tính `align` xác định cách tính tọa độ ngang của từng dòng chữ trên trang viết tay:

```python
@dataclass
class Paragraph(Block):
    inlines: list[Inline] = field(default_factory=list)
    align: Literal["left", "center", "right", "justify"] = "left"
```

### 1.2 Quy tắc Trạng thái & Biến đổi Tọa độ Hình học
Khi `DocumentLayoutEngine.render_paragraph_inlines` kết xuất một dòng chữ gồm danh sách các mục hiển thị `cur_line: list[RenderItem]`:
- Chiều rộng khả dụng: `avail_w = max(self.width - indent, 1.0)`
- Tổng độ rộng nội dung dòng: `curw = cur_line[-1].start + cur_line[-1].width`
- Độ rộng dư thừa trên dòng: `rem_space = max(0.0, avail_w - curw)`

| Chế độ `align` | Điều kiện áp dụng | Tọa độ `line_start_x` | Điều chỉnh vị trí phần tử trong dòng |
| :--- | :--- | :--- | :--- |
| `"left"` | Mặc định (hoặc khối Heading / List) | `self.x0 + indent` | Giữ nguyên `itm.start` gốc |
| `"center"` | Mọi dòng của đoạn Paragraph | `self.x0 + indent + rem_space / 2.0` | Giữ nguyên `itm.start` gốc |
| `"right"` | Mọi dòng của đoạn Paragraph | `self.x0 + indent + rem_space` | Giữ nguyên `itm.start` gốc |
| `"justify"` | Dòng tràn (overflow) và $N \ge 2$ từ | `self.x0 + indent` | Phân bổ khoảng cách từ: `gap = rem_space / (N - 1)`; `itm[i].start += i * gap` |
| `"justify"` | Dòng kết thúc bằng `LineBreak`, dòng cuối đoạn, hoặc $N < 2$ từ | `self.x0 + indent` | Giữ nguyên khoảng cách tự nhiên (căn trái) |

---

## 2. Mô hình Tuần tự hóa DocumentIR sang Markdown có Escaping

Ánh xạ giữa các khối cấu trúc nội bộ của `DocumentIR` và định dạng văn bản được trả về cho trình soạn thảo Web trong `BrowserBridge._document_to_markdown_dict`:

| Khối `DocumentIR` | Cấu trúc dữ liệu | Biểu diễn chuỗi Markdown đầu ra |
| :--- | :--- | :--- |
| `Heading` | `inlines: list[Inline]`, `level: int (1..6)` | `f"{'#' * level} {escaped_inlines}"` |
| `Paragraph` | `inlines: list[Inline]`, `align: str` | `escaped_inlines` |
| `MathBlock` | `latex: str` | `f"$${latex}$$"` |
| `TableCell` chứa `MathBlock` | `blk: MathBlock` bên trong `cell.blocks` | `f"${escaped_latex}$"` (escape `\|`) |
| `TableCell` chứa `LineBreak` | `inl: LineBreak` trong ô bảng | Thay thế bằng khoảng trắng `" "` |
| `ListBlock` | `items: list[list[Block]]`, `ordered: bool` | `f"- {item_text}"` hoặc `f"{idx}. {item_text}"` |

### Quy tắc Escape Ký tự Điều khiển Markdown
- Khi serialize `Text.text`, các ký tự sau được escape bằng dấu `\`: `\`, `*`, `_`, `~`, `#`, `$`, `|`.
- Ở đầu dòng, các tiền tố số thứ tự `1.` hoặc gạch đầu dòng `- ` được escape an toàn để không bị nhận nhầm thành List.

---

## 3. Mô hình An toàn Hiển thị và Xem thử Kho mẫu (`webapp/js/`)

### 3.1 Cấu trúc Dữ liệu Thẻ Mẫu An toàn
Mọi nhãn ký tự trước khi hiển thị trên giao diện người dùng phải tuân thủ chuẩn mã hóa ký tự HTML:

```typescript
interface SafeBankItem {
  label: string;          // Chuỗi ký tự gốc (ví dụ: "<", ">", "&", "a")
  escapedLabel: string;   // Chuỗi đã qua escape (ví dụ: "&lt;", "&gt;", "&amp;")
  category: string;       // "letters" | "words" | "symbols" | "digits"
  count: number;          // Số lượng mẫu hiện có
}
```

### 3.2 Cấu trúc Kết quả Xem thử Ngẫu nhiên
Mỗi thẻ xem thử chứa hình ảnh nét vẽ trực quan được giải nén từ tệp `.xopp` với viewBox cắt gọn:

```typescript
interface RandomPreviewCard {
  seed: number;           // Hạt giống ngẫu nhiên (ví dụ: 7, 42, 99)
  xopp_base64: string;    // Dữ liệu nhị phân nén của tài liệu kết xuất
  svgElement: SVGSVGElement; // Phần tử DOM SVG được tạo qua renderPageSvgElement với viewBox bbox
}
```

---

## 4. Mô hình Tùy chọn Kết xuất & Di sản Desktop

```python
@dataclass
class WriteOptions:
    # ...
    missing_grid: bool = False  # Mặc định False: Không tự động tạo file _thieu.xopp gây rác MEMFS
```
