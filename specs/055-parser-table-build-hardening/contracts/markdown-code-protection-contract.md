# Contract: Markdown Code Protection & CommonMark Compliance

**Feature**: `055-parser-table-build-hardening`  
**Module**: `chuviettay/importer/markdown_importer.py`  
**Consumers**: `MarkdownImporter._normalize_math_delimiters`, `MarkdownImporter._isolate_display_math_blocks`, `MarkdownImporter._sanitize_html`, `MarkdownImporter.import_text`

---

## 1. Specification

### 1.1 Fenced Code Blocks (Khối mã)
- **Cú pháp mở**: Dòng bắt đầu bằng 0 đến 3 dấu cách, theo sau bởi $K \ge 3$ ký tự backtick (`` ` ``) hoặc dấu ngã (`~`), kèm chuỗi thông tin (info string, không chứa backtick nếu dùng fence backtick).
- **Cú pháp đóng**: Dòng bắt đầu bằng 0 đến 3 dấu cách, theo sau bởi $M \ge K$ ký tự phân cách cùng loại với dấu mở, và chỉ chứa khoảng trắng/tab phía sau.
- **Quy tắc bảo vệ**:
  - Dòng chứa ít hơn $K$ ký tự phân cách (ví dụ: dòng có 3 backticks nằm bên trong khối mở bằng 4 backticks) là nội dung hợp lệ bên trong khối mã, KHÔNG ĐƯỢC coi là dấu đóng.
  - Toàn bộ nội dung bên trong khối mã từ dòng mở đến dòng đóng (hoặc đến EOF nếu unclosed) KHÔNG ĐƯỢC chịu bất kỳ phép thay thế ký tự nào trong `_normalize_math_delimiters`, `_isolate_display_math_blocks` hay `_sanitize_html`.
  - Cụ thể: các chuỗi như `\[x=1\]`, `\(y=2\)`, `$$z=3$$`, `prefix:$$x=1$$` phải được giữ nguyên từng ký tự.

### 1.2 Inline Code Spans (Đoạn mã nội tuyến)
- **Cú pháp mở**: Chuỗi $N \ge 1$ ký tự backtick liên tiếp.
- **Cú pháp đóng**: Chuỗi đúng $N$ ký tự backtick liên tiếp tiếp theo trong cùng đoạn văn bản.
- **Quy tắc bảo vệ**:
  - Các ký tự backtick bên trong có độ dài khác $N$ (ví dụ: 1 backtick nằm trong cặp 2 backticks: ```` `` `foo` `` ````) được xem là ký tự dữ liệu.
  - Bất kỳ chuỗi nào trông giống công thức toán học (`$$...$$`, `$..$`, `prefix:$$...$$`) nằm bên trong code span TUYỆT ĐỐI KHÔNG được xem là điểm bắt đầu của khối công thức display hoặc công thức nội dòng.

---

## 2. API Contract

```python
def split_code_segments(text: str) -> list[tuple[str, bool]]:
    """Phân tách chuỗi văn bản thành danh sách các đoạn (segment, is_code).
    
    Args:
        text: Chuỗi văn bản Markdown đầu vào.
        
    Returns:
        Danh sách các tuple (segment_text, is_code), trong đó:
        - is_code=True: segment_text là khối mã (fenced code) hoặc đoạn mã nội tuyến (code span).
        - is_code=False: segment_text là văn bản Markdown thông thường.
    """
    ...
```

---

## 3. Test Invariants

1. `import_text("````markdown\n```\n\\[x=1\\]\n````")`:
   - Khối mã không bị cắt, không bị đổi thành `$$x=1$$`.
   - Cây Document IR sinh ra 1 unsupported code_block có nội dung chứa `\\[x=1\\]` hoặc giữ nguyên vẹn.
2. `import_text("``prefix:$$x=1$$``")`:
   - Sinh ra 1 `Paragraph` chứa `Text(text="prefix:$$x=1$$")`.
   - Tuyệt đối không sinh ra `MathBlock`.
