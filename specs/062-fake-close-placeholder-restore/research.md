# Research: Feature 062 — Khôi phục dấu đóng giả bằng dấu giữ chỗ riêng

**Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

Các phát hiện dưới đây được kiểm chứng trên mã `main` (commit `518a7e3`) bằng các script tái hiện/nguyên mẫu trong thư mục scratch của phiên làm việc (không sửa repo).

---

## R1. Nguyên nhân gốc của lỗi bảo toàn LaTeX

- **Decision**: Gỡ bỏ phép `tok.content.strip().replace(r"\$\$", "$$")` trong `MarkdownImporter._parse_blocks()`.
- **Rationale**: Phép thay thế áp dụng cho toàn bộ nội dung token công thức, không phân biệt chuỗi do bộ tiền xử lý chèn với chuỗi người dùng viết. Tái hiện:

  | Đầu vào | `MathBlock.latex` hiện tại |
  |---|---|
  | `$$\text{\$\$}$$` | `\text{$$}` |
  | `$$\n\text{\$\$}\n$$` | `\text{$$}` |
  | `> $$\n> \text{\$\$}\n> $$` | `> \text{$$}\n>` |

  Bản chất: biểu diễn escape `\$\$` (Feature 061) **trùng** với cú pháp LaTeX hợp lệ, nên mọi phép khôi phục dựa trên nó đều mơ hồ. Cần một biểu diễn không thể xuất hiện trong đầu vào.
- **Alternatives considered**:
  - *Chỉ khôi phục `\$\$` ở cuối dòng có tiền tố trích dẫn sâu hơn*: vẫn mơ hồ (người dùng có thể viết `>> \$\$` hợp lệ trong khối toán), và phụ thuộc vào việc tái dựng độ sâu trích dẫn trong token — dễ vỡ.
  - *Ghi lại danh sách vị trí dòng đã escape rồi đối chiếu `tok.map`*: `token.map` của dollarmath trỏ theo dòng của chuỗi sau tiền xử lý, có thể lệch khi bộ cô lập chèn dòng trống; phức tạp hơn mức cần thiết (vi phạm KISS).

## R2. Lựa chọn dấu giữ chỗ

- **Decision**: Thay `$$` của dấu đóng giả bằng **một ký tự đơn thuộc vùng Private Use Area của BMP (U+E000–U+F8FF)**, được chọn động: ký tự đầu tiên trong dải **không xuất hiện** trong văn bản đầu vào (sau `_normalize_math_delimiters`). Mặc định thực tế là `U+E000`.
- **Rationale**:
  - `dollarmath` chỉ nhận dấu đóng khi `lineText.strip().endswith("$$")`; dòng `>> \ue000` không thỏa → khối không bị đóng sớm (đã kiểm chứng với nguyên mẫu: ca lồng nhau, ca kèm dấu câu `>> $$,   `, ca cấp 3).
  - Ký tự PUA không phải khoảng trắng (không bị `strip()` cắt), không phải dấu câu ASCII (không bị markdown-it xử lý escape/emphasis), không bị `_sanitize_html` hay regex bảng/hàng rào tác động.
  - Chọn động đảm bảo **không va chạm** với đầu vào (FR-006): nguyên mẫu với đầu vào chứa sẵn `\ue000` tự chọn `\ue001`, và `\ue000` của người dùng được giữ nguyên trong đoạn văn.
  - Python `str` và Pyodide xử lý PUA như ký tự Unicode bình thường; không cần phụ thuộc mới.
- **Fallback**: Nếu đầu vào chứa đủ cả 6.400 ký tự PUA của BMP (thực tế không xảy ra), bỏ qua cơ chế bảo vệ dấu đóng giả (giữ `$$` nguyên dạng, tức hành vi trước Feature 061) thay vì làm hỏng nội dung. Bảo toàn dữ liệu được ưu tiên hơn chống đóng sớm.
- **Alternatives considered**:
  - *Hằng cố định `\ue000`*: đơn giản hơn nhưng vi phạm FR-006 khi đầu vào chứa sẵn ký tự đó.
  - *Ký tự điều khiển (`\x00`, `\x1f`)*: markdown-it thay `\x00` bằng `U+FFFD` khi chuẩn hóa → hỏng. Loại.
  - *Chuỗi ASCII dài kiểu `@@FAKE_CLOSE@@`*: có thể bị markdown-it diễn giải (emphasis, autolink) và vẫn có xác suất va chạm. Loại.

## R3. Phạm vi khôi phục dấu giữ chỗ

- **Decision**: Khôi phục dấu giữ chỗ về `$$` trên **toàn bộ cây token** ngay sau `md.parse()` trong `import_text()` (duyệt đệ quy cả `token.content`, `token.info` và `token.children`), trước `_parse_blocks()`.
- **Rationale**: `dollarmath` trả về `False` khi khối không có dấu đóng (`if not haveEndMarker: return False`), nên các dòng — kể cả dòng đã gắn dấu giữ chỗ — rơi vào đoạn văn hoặc khối mã (ví dụ dòng mở fence lồng nhau `>> ```python $$` trong khối toán không đóng sẽ đặt dấu giữ chỗ vào `token.info`, sau đó đi vào `ImportResult.unsupported`). Tái hiện hiện tại với `\$\$`: đoạn văn hiển thị chữ `$$` (nhờ escape của markdown-it). Nếu chỉ khôi phục trong `MathBlock` hoặc chỉ trên `token.content`, dấu giữ chỗ có thể rò rỉ vào `Text` hoặc `unsupported` (vi phạm FR-005). Duyệt toàn cây trên cả `token.content` và `token.info`: một điểm khôi phục duy nhất, `_parse_blocks()`/`_parse_inlines()` không cần biết cơ chế (high cohesion). Nguyên mẫu xác nhận ca không đóng cho đúng chữ `$$` như hiện tại.
- **Alternatives considered**: Khôi phục rải rác trong `_parse_blocks`, `_parse_inlines`, `_parse_table` — nhiều điểm sửa, dễ sót nhánh. Hậu xử lý trên Document IR — phải duyệt nhiều kiểu node và `unsupported`; cây token đồng nhất hơn.

## R4. Truyền dấu giữ chỗ giữa các bước

- **Decision**: `_isolate_display_math_blocks(seg, fake_close_placeholder="")` nhận tham số tùy chọn với giá trị mặc định `""` (sentinel kiểu `str` biểu thị tự động chọn qua `_choose_fake_close_placeholder(seg)` sau khi chuẩn hóa CRLF và kiểm tra `"$$" in seg`), trong khi `None` biểu thị tường minh trạng thái không dùng dấu giữ chỗ (fallback khi cạn kiệt vùng PUA hoặc kiểm thử đơn vị truyền `None`). `import_text()` gọi `_choose_fake_close_placeholder(normalized_text)` một lần (khi `"$$" in normalized_text`), truyền cho bước cô lập và cho bước khôi phục token.
- **Rationale**: Không dùng trạng thái instance (an toàn khi tái sử dụng importer), giữ tương thích chữ ký với mọi lời gọi hiện có, phân biệt rõ giữa "không truyền tham số" (`""`) và "không có dấu giữ chỗ khả dụng" (`None`), tránh quét lặp 6.400 điểm mã PUA và giúp test có thể kiểm chứng trực tiếp nhánh fallback `fake_close_placeholder=None`.

## R5. Hành vi có sẵn ngoài phạm vi (ghi nhận, không sửa)

- `MathBlock` trong trích dẫn giữ tiền tố `> ` (ví dụ `> x = 1\n>> $$\n> x = 2\n>`): do dollarmath lấy `state.src` thô. Giá trị mong đợi trong test phản ánh đúng hành vi này.
- `$$a\$\$$$` (một dòng, `\$` sát dấu đóng): bước cô lập tách sai thành `$$a\$\$$\n\n$` → khối `a\$\` + đoạn `$`. Lỗi có sẵn của bộ quét `$$` nội dòng, độc lập với cơ chế khôi phục.
- Ca có dòng `>` trống ở giữa khối toán trích dẫn vẫn cho 1 `MathBlock` — không thay đổi.

## R6. Ảnh hưởng hiệu năng và Golden Master

- Chọn dấu giữ chỗ: một phép `in` trên chuỗi (thường dừng ở `U+E000`) → O(n). Duyệt cây token: O(số token). Ngưỡng benchmark `T(4N)/T(N) ≤ 6.0` không bị ảnh hưởng (benchmark gọi trực tiếp bước cô lập).
- 8 ca Golden Master không chứa dấu đóng giả lồng nhau hay `\$\$` → mã băm SHA-256 dự kiến không đổi.
