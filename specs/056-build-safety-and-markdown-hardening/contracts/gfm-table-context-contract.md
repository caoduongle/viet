# Contract: Context-Aware GFM Table Detection & Cell Value Parity

**Feature**: `056-build-safety-and-markdown-hardening`  
**Module**: `chuviettay/importer/markdown_importer.py`  
**Consumers**: `MarkdownImporter._isolate_display_math_blocks`, `MarkdownImporter.import_text`

---

## 1. Specification

### 1.1 Khối Bảng GFM Hợp lệ
- Một khối bảng GFM hợp lệ bắt buộc phải có một dòng phân cách cột (delimiter line: chứa ít nhất một cặp hyphens `---|---` hoặc `:---:|:---:`) ngăn cách giữa hàng tiêu đề và các hàng dữ liệu.
- Một dòng đơn độc lập chứa ký tự `|` (ví dụ: `$$x=1$$ | 2`) nhưng không có hàng phân cách cột KHÔNG PHẢI là bảng GFM. Dòng này phải được xử lý phân tách display math bình thường.

### 1.2 Bảo toàn Dữ liệu Ô Bảng Compact
- Bảng compact:
  ```markdown
  Col | Val
  ---|---
  $$x=1$$ | 2
  ```
  Sau khi chuyển đổi sang Document IR:
  - Nút `Table` có đúng 2 hàng (`len(table.rows) == 2`).
  - Hàng 1: Ô 1 là Text("Col"), Ô 2 là Text("Val").
  - Hàng 2: Ô 1 là MathInline("x=1"), Ô 2 là Text("2"). Không bị mất mát dữ liệu hoặc chuyển thành chuỗi rỗng.

---

## 2. Test Invariants

1. Dòng đứng một mình `$$x=1$$ | 2`:
   - Phân tách thành `MathBlock(latex="x=1")` và `Paragraph` chứa `| 2`.
2. Bảng compact hợp lệ:
   - Tạo `Table` block với đầy đủ dữ liệu các ô.
