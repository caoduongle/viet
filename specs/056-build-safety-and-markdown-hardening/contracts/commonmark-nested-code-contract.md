# Contract: CommonMark Nested Code & Escaped Delimiters Protection

**Feature**: `056-build-safety-and-markdown-hardening`  
**Module**: `chuviettay/importer/markdown_importer.py`  
**Consumers**: `MarkdownImporter._normalize_math_delimiters`, `MarkdownImporter._isolate_display_math_blocks`, `MarkdownImporter.import_text`

---

## 1. Specification

### 1.1 Khối mã lồng trong Trích dẫn (Blockquote Code Fence)
- Cú pháp: Dòng bắt đầu bằng tiền tố trích dẫn (`^[ ]{0,3}(>[ ]?)+`), theo sau bởi khối mã fence (3 hoặc nhiều ký tự backtick/tilde).
- Đóng fence: Dòng có cùng tiền tố trích dẫn, theo sau bởi 0-3 khoảng trắng và $M \ge K$ ký tự phân cách tương ứng.
- Bảo vệ: Toàn bộ công thức toán (`\[...\]`, `\(...\)`, `$$...$$`) bên trong khối mã trích dẫn giữ nguyên vẹn 100%.

### 1.2 Khối mã Thụt lề 4 Khoảng trắng (Indented Code Block)
- Cú pháp: Các dòng liên tiếp có thụt lề từ 4 khoảng trắng trở lên hoặc bắt đầu bằng ký tự tab (`\t`) ở cấp gốc.
- Bảo vệ: Giữ nguyên vẹn, không chuyển đổi các dấu gạch ngược của LaTeX bên trong.

### 1.3 Ký tự Backtick Bị Thoát (Escaped Backtick)
- Cú pháp: Ký tự backtick đứng sau số lẻ dấu gạch ngược (`\``, `\\\``).
- Bảo vệ: Không coi là dấu mở hoặc đóng của inline code span.

---

## 2. Test Invariants

1. `import_text("> ~~~latex\n> \\[x=1\\]\n> ~~~")`:
   - Công thức `\[x=1\]` bên trong không bị đổi thành `$$x=1$$`.
2. `import_text("    \\[x=1\\]\n    \\[y=2\\]")`:
   - Giữ nguyên trong unsupported code block hoặc văn bản, không chuyển thành display math.
3. `import_text("Dấu \\` không phải code nhưng `\\[code\\]` là code.")`:
   - Dấu `\` được xử lý đúng theo CommonMark.
