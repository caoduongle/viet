# Contract: Bộ Phân Tách Khối Công Thức Tuyến Tính và Bảo Vệ Khối Mã

**Feature**: [054-repo-audit-hardening](../spec.md)  
**Target Module**: `chuviettay.importer.markdown_importer.MarkdownImporter`  

---

## 1. Mục đích
Quy định giao diện và hành vi chuẩn tắc của phương thức tiền xử lý cách ly khối công thức toán display (`_isolate_display_math_blocks`), bảo đảm tính tuyến tính $O(n)$, bảo vệ nguyên vẹn các khối mã và đoạn mã, và tương thích an toàn với định dạng ngắt dòng Windows CRLF.

## 2. Đặc tả Giao diện

```python
class MarkdownImporter(BaseImporter):
    @classmethod
    def _isolate_display_math_blocks(cls, text: str) -> str:
        """Cách ly các khối công thức toán display ($$..$$) trên dòng mới hoặc liền sau
        dấu hai chấm dẫn nhập bằng dòng trống CommonMark chuẩn.
        
        Bảo toàn 100% nội dung bên trong code fence (``` và ~~~) và inline code (`...`).
        Hoạt động với độ phức tạp tuyến tính O(n)."""
```

## 3. Các Điều kiện Tiền đề & Hậu nghiệm (Pre & Post Conditions)

### Pre-conditions
- Đầu vào `text` là chuỗi ký tự UTF-8 chứa văn bản Markdown (đã qua bước chuẩn hóa `_normalize_math_delimiters`).

### Post-conditions
1. **Line Ending Normalization (CRLF Protection)**:
   - Chuẩn hóa mọi biến thể ngắt dòng (`\r\n`, `\r`) về chuẩn `\n` trước khi quét, ngăn ngừa lỗi bám ký tự `\r` làm trượt nhận diện `$$`.
2. **Code Fence & Inline Code Immunity**:
   - Nếu một đoạn văn bản nằm giữa cặp code fence (mở bằng 3 hoặc nhiều hơn dấu `` ` `` hoặc `~`), hoặc cặp backtick nội dòng (`` ` ``), chuỗi đó giữ nguyên 100% ký tự.
   - Các chuỗi như ```` ```latex prefix:$$x=1$$ ``` ```` không bị chèn thêm bất kỳ dấu xuống dòng hay khoảng trắng nào.
   - Khối mã chưa đóng ở cuối tệp (unclosed fence at EOF) được bảo toàn nguyên vẹn tới cuối tệp theo chuẩn CommonMark.
3. **Linear Time Complexity ($O(n)$)**:
   - Với tài liệu chứa $N$ dòng, số phép so sánh và bước duyệt tỷ lệ thuận tuyến tính với $N$.
   - Các dấu `$$` mở không đóng ở cuối tài liệu được coi là văn bản thường và không gây ra lặp duyệt tìm kiếm trên các dòng trước đó.
4. **CommonMark MathBlock Isolation**:
   - Dòng văn bản kết thúc bằng ký tự thông thường, tiếp nối bởi dòng bắt đầu bằng `$$...$$` được chèn dòng trống phân cách trước `$$`.
   - Dòng kết thúc bằng `$$...$$` tiếp nối bởi dòng chữ tiếp theo được chèn dòng trống phân cách sau `$$`.
   - Bảng GFM (`| a | $$...$$ |` hoặc hàng bảng không có `|` ngoài cùng) không bị chèn dòng trống phá vỡ bảng.
   - Thụt lề danh sách (`- $$...$$`) được bảo tồn tiền tố thụt lề.
