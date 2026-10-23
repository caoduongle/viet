# Contract: GFM Compact Table Row Preservation

**Feature**: `055-parser-table-build-hardening`  
**Module**: `chuviettay/importer/markdown_importer.py`  
**Consumers**: `MarkdownImporter._isolate_display_math_blocks`, `MarkdownImporter.import_text`

---

## 1. Specification

### 1.1 GFM Compact Table Syntax
- Bảng GitHub Flavored Markdown cho phép:
  - Bảng tiêu chuẩn: Có dấu `|` ở đầu dòng và cuối dòng: `| Col 1 | Col 2 |`
  - Bảng compact: Không có dấu `|` ở hai đầu biên: `Col 1 | Col 2`
  - Đường phân cách cột: `---|---` hoặc `:---:|---:`
  - Dòng dữ liệu: `val 1 | val 2` hoặc `$$x=1$$ | val 2`

### 1.2 Table Row Detection Invariants
1. Một dòng KHÔNG bị coi là khối công thức display độc lập nếu dòng đó chứa ký tự phân cách cột `|` nằm bên ngoài các công thức toán hoàn chỉnh và ngoài code span.
2. Dòng dữ liệu compact có ô đầu tiên bắt đầu bằng `$$...$$` (ví dụ: `$$x=1$$ | 2`) PHẢI được nhận diện là hàng bảng.
3. Không thực hiện chèn dòng trống hoặc tách dòng trên bất kỳ hàng bảng nào.
4. Ngược lại, nếu dòng chứa ký hiệu `|` nhưng ký hiệu này nằm HOÀN TOÀN bên trong công thức display (ví dụ: `$$\int |x| dx = 1$$`), dòng đó KHÔNG PHẢI là hàng bảng mà là khối công thức display, cần được xử lý phân tách đúng chuẩn.

---

## 2. Test Invariants

1. Nhập bảng compact với công thức ở ô đầu tiên:
   ```markdown
   Col | Val
   ---|---
   $$x=1$$ | 2
   ```
   Kết quả trả về:
   - 1 phần tử `Table` duy nhất trong `Document.blocks`.
   - `len(table.rows) == 2`.
   - Hàng 2 ô 1 chứa công thức `MathInline` (hoặc `Text` nếu cấu hình toán học), ô 2 chứa giá trị `2`.
   - Không bị vỡ thành nhiều khối `Paragraph` rời rạc.

2. Khối toán chứa dấu giá trị tuyệt đối:
   ```markdown
   $$\int |x| dx = 1$$
   ```
   Kết quả trả về:
   - 1 phần tử `MathBlock` với `latex="\int |x| dx = 1"`.
   - Không bị nhận nhầm thành `Table`.
