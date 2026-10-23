# Contract: Chuẩn Hóa Và Phân Tách Khối Công Thức Toán Trong Markdown

**Module**: `chuviettay.importer.markdown_importer.MarkdownImporter`  
**Consumers**: CLI Parser, Web Worker Pyodide, Test Suites  

---

## 1. Phương thức tiền xử lý `_normalize_math_delimiters`

### Chữ ký hàm (Signature):
```python
@classmethod
def _normalize_math_delimiters(cls, text: str) -> str:
    """
    Chuẩn hóa các dấu phân cách công thức toán trong Markdown.
    
    1. Bảo toàn 100% nội dung bên trong các đoạn mã (code blocks/fences).
    2. Chuyển đổi \( ... \) thành $...$ và \[ ... \] thành $$...$$.
    3. Tách các khối toán display $$...$$ bắt đầu ở dòng mới hoặc liền sau dấu hai chấm
       để có dòng trống (\n\n) phân cách với văn bản xung quanh theo chuẩn CommonMark.
    """
```

### Hợp đồng đầu vào / đầu ra (Input/Output Contract):

| Trường hợp đầu vào | Kết quả sau chuẩn hóa | Cấu trúc IR mong đợi |
|-------------------|----------------------|----------------------|
| `a\n$$x=1$$\nb` | `a\n\n$$x=1$$\n\nb` | `[Paragraph("a"), MathBlock("x=1"), Paragraph("b")]` |
| `ta có:$$x=1$$` | `ta có:\n\n$$x=1$$` | `[Paragraph("ta có:"), MathBlock("x=1")]` |
| `$$x=1$$\ntrong đó...` | `$$x=1$$\n\ntrong đó...` | `[MathBlock("x=1"), Paragraph("trong đó...")]` |
| `a\n\[x=1\]\nb` | `a\n\n$$x=1$$\n\nb` | `[Paragraph("a"), MathBlock("x=1"), Paragraph("b")]` |
| `\| a \| $$x=1$$ \|` | Không đổi (giữ nguyên một dòng) | `[Table(...)]` không bị vỡ bảng |
| `- Mục 1\n  $$x=1$$\n- Mục 2` | `- Mục 1\n\n  $$x=1$$\n\n- Mục 2` | Giữ nguyên thụt lề trong `ListBlock` |
| `$$\sum x=1$$, với...` | `$$\sum x=1$$\n\n, với...` | Nhận diện đúng dấu đóng và giữ dấu câu |
| ```` ```\na\n$$x=1$$\n``` ```` | Không thay đổi | Khối mã nguồn không bị phân tách |
| `Giá tiền: 100$ và 200$` | Không thay đổi | Dấu đô la đơn tiền tệ không bị nhận nhầm |
| `a\n$$x=1` (chưa đóng) | An toàn, không treo | Xử lý như văn bản thường, chống ReDoS |

---

## 2. Ràng buộc bảo toàn (Invariants)
1. **Idempotence**: Gọi `_normalize_math_delimiters` nhiều lần trên cùng một chuỗi không làm nhân đôi các dòng trống vô tận.
2. **Safety & Security**: Không làm mất mát hoặc thay đổi bất kỳ ký tự nào của công thức toán học bên trong `$$...$$`; thuật toán xử lý tuyến tính tránh lỗi treo do ReDoS.
3. **Table & List Invariance**: Tuyệt đối không chèn `\n\n` vào các dòng của bảng GFM (`|...|`) và bảo toàn mức thụt lề khi khối toán nằm trong danh sách.
4. **CommonMark Compliance**: Mọi khối công thức toán học display ngoài bảng đều được phân tích thành khối `MathBlock` cấp 1 trong tài liệu.
