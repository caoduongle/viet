# Contract: DOCX Import & DocumentIR Serialization

**Scope**: Ràng buộc dữ liệu chuyển đổi giữa `DocxImporter`, `DocumentIR`, và `BrowserBridge._document_to_markdown_dict`.

---

## 1. Hợp đồng Chuyển đổi Khối DocumentIR sang Chuỗi Soạn thảo có Escaping

Khi phương thức `BrowserBridge._document_to_markdown_dict(doc: Document)` thực thi:

### 1.1 Khối Tiêu đề (`Heading`)
- **Đầu vào**: `Heading(inlines=[Text("Tiêu đề")], level=2)`
- **Đầu ra yêu cầu**: `## Tiêu đề`
- **Ràng buộc**: Số dấu `#` bằng chính xác `level` (giới hạn từ 1 đến 6).

### 1.2 Khối Phương trình Toán độc lập (`MathBlock`)
- **Đầu vào**: `MathBlock(latex="E = mc^2")`
- **Đầu ra yêu cầu**: `$$E = mc^2$$`
- **Ràng buộc**: Không được bỏ qua `MathBlock`. Trong ô bảng (`TableCell`), phương trình toán được chuyển thành `$E = mc^2$` và dấu `|` trong LaTeX phải được escape thành `\|`.

### 1.3 Quy tắc Escape Ký tự Điều khiển Markdown
- Khi serialize `Text.text` sang Markdown, bắt buộc escape các ký tự: `\`, `*`, `_`, `~`, `#`, `$`, `|`.
- Không chèn khoảng trắng thừa giữa các text runs liền kề.

### 1.4 Xử lý Ô Bảng (`TableCell`)
- `LineBreak` bên trong ô bảng phải được chuyển đổi thành khoảng trắng thay vì ký tự xuống dòng `\n`.
- Dấu gạch đứng `|` trong văn bản hoặc LaTeX bên trong ô bảng bắt buộc phải escape thành `\|`.

### 1.5 Hợp đồng Round-trip
- Chuỗi Markdown sinh ra từ `_document_to_markdown_dict` khi chạy qua `MarkdownImporter.import_text` phải tái tạo đúng 100% các khối và nội dung ban đầu.
