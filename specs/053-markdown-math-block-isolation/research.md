# Research: Nhận Diện Khối Công Thức Toán Display Khi Xuống Dòng Và Ngăn Ngừa Đè Nét Cận Toán Tử

**Feature**: `053-markdown-math-block-isolation`  
**Date**: 2026-10-22  
**Status**: Completed  

---

## 1. Nghiên cứu 1: Cơ chế phân tích khối toán display trong CommonMark & dollarmath

### Bối cảnh & Vấn đề
Trong ứng dụng Chữ Viết Tay, tệp `chuviettay/importer/markdown_importer.py` sử dụng thư viện `markdown-it-py` với plugin `dollarmath_plugin` (cấu hình `allow_space=False, double_inline=True`).
Theo đặc tả CommonMark:
- Một đoạn văn bản (`Paragraph`) bắt đầu bằng một dòng văn bản và sẽ tiếp tục nuốt tất cả các dòng tiếp theo cho đến khi gặp **dòng trống** (`\n\n`) hoặc một phần tử ngắt khối đặc biệt (như Heading `#`, Blockquote `>`, Horizontal Rule `---`).
- Khối toán học `$$...$$` của plugin `dollarmath` **không thể tự ngắt** đoạn văn bản nếu không có dòng trống ngăn cách phía trước.
- Khi người dùng viết:
  ```markdown
  a
  $$\sum_{j=1}^9 P(D = j) = 1$$
  ```
  Trình phân tích CommonMark xem `$$\sum...$$` là nội dung nội dòng hai dấu đô la (`math_inline_double`) nằm trong cùng đoạn văn chứa chữ `a`.
- Khi chuyển đổi sang Document IR, `_parse_inlines` tạo ra:
  ```python
  Paragraph(inlines=[Text("a"), LineBreak(), MathInline(latex="\\sum_{j=1}^9 P(D = j) = 1")])
  ```
- Kết quả: Biểu thức toán bị xem là `MathInline`, `display=False`, làm mất cận xếp chồng của dấu $\sum$, và engine bố cục đoạn văn cố gắng co ép (scale down tới 50%) toàn bộ phương trình dài trên một dòng kẻ giấy viết.

### Quyết định kỹ thuật
- **Quyết định**: Triển khai bước tiền chuẩn hóa cách ly khối công thức display trong hàm `MarkdownImporter._normalize_math_delimiters` (hoặc hàm hỗ trợ `_isolate_display_math_blocks`).
- **Nguyên lý hoạt động**:
  1. Bảo vệ nguyên vẹn các đoạn mã (`_CODE_SEGMENT`: ```, ~~~, `).
  2. Phát hiện các mẫu `$$...$$` bắt đầu ở dòng mới (được dẫn trước bởi `\n` hoặc đầu tệp) nhưng thiếu dòng trống (`\n\n`) phân cách với dòng văn bản trước đó, tự động bổ sung một dấu `\n` để tạo ranh giới dòng trống chuẩn CommonMark (`\1\n\n\2`).
  3. Phát hiện các dòng kết thúc bằng `$$` nhưng theo sau là văn bản ở dòng kế tiếp mà không có dòng trống, tự động bổ sung dòng trống sau `$$` (`\1\n\n\2`).
  4. Hỗ trợ trường hợp viết liền sau dấu hai chấm: `[chữ dẫn nhập]:\s*\$\$` -> tự động tách thành `[chữ dẫn nhập]:\n\n$$`.
  5. Đối với `\[...\]`: Vì hàm `_convert_delimited` đã đổi `\[...\]` thành `$$...$$`, quy tắc cách ly này tự động áp dụng hoàn hảo cho cả cú pháp LaTeX truyền thống.
- **Lý do lựa chọn**:
  - Không can thiệp vào mã nguồn gốc trong ô soạn thảo của người dùng.
  - Tận dụng 100% sức mạnh phân tích chuẩn của `markdown-it-py` và `dollarmath_plugin` mà không cần vá (monkey-patch) thư viện bên ngoài.
  - Độ phức tạp thời gian đạt $O(L)$ với $L$ là độ dài văn bản, thực thi dưới 0.2ms cho văn bản 10.000 ký tự.
- **Phương án khác đã xem xét và bác bỏ**:
  - *Sửa đổi quy tắc block của dollarmath*: Không khả thi trên môi trường Pyodide/WASM vì dùng gói bánh xe chuẩn (wheel) từ PyPI.
  - *Tách Paragraph sau khi phân tích inlines*: Đòi hỏi bóc tách IR sau khi đã xây dựng cây cú pháp, phức tạp và dễ gây lỗi với các phần tử lồng nhau như bảng hoặc danh sách.

---

## 2. Nghiên cứu 2: Ngăn ngừa đè nét chỉ số trên và dưới trong bố cục toán tử lớn (Side Limits Clearance)

### Bối cảnh & Vấn đề
Trong tệp `chuviettay/layout/math_layout.py`, hàm `_m_NAry` chịu trách nhiệm bố cục toán tử lớn ($\sum, \prod, \int...$).
Khi công thức nằm ở chế độ nội dòng hoặc không xếp chồng (`stacked = False`):
```python
if sup is not None:
    y = (sup.size.ascent - op.size.ascent) if tall else -0.55 * max(op.size.ascent, self.xh * eff)
    canvas.put(sup, x + sup_dx, y)
    ascent = max(ascent, -y + sup.size.ascent)
    right = max(right, x + sup_dx + sup.size.width)
if sub is not None:
    y = (op.size.descent - sub.size.descent) if tall else 0.35 * op.size.descent + 3.0 * eff
    canvas.put(sub, x, y)
    descent = max(descent, y + sub.size.descent)
    right = max(right, x + sub.size.width)
```
- Khi `tall = True` (dấu $\sum$), công thức tính toạ độ `y`:
  - `sup_y = sup.size.ascent - op.size.ascent`: Đặt đỉnh của `sup` ngang bằng đỉnh của `op`. Đáy của `sup` nằm tại `sup_y + sup.size.descent`.
  - `sub_y = op.size.descent - sub.size.descent`: Đặt đáy của `sub` ngang bằng đáy của `op`. Đỉnh của `sub` nằm tại `sub_y - sub.size.ascent`.
- Tính toán thực tế trên `\sum_{j=1}^9`:
  - `op` có `ascent = 9.76`, `descent = 3.70`, tổng chiều cao $13.46$.
  - `sup` (`9`) có `ascent = 5.66`, `descent = 0.0`. Do đó `sup_y = -4.10`, đáy của `sup` là `-4.10`.
  - `sub` (`j=1`) có `ascent = 5.66`, `descent = 0.94`. Do đó `sub_y = 2.76`, đỉnh của `sub` là `2.76 - 5.66 = -2.90`.
  - Khoảng cách thẳng đứng giữa đáy `sup` và đỉnh `sub`:
    $$\text{gap} = (-2.90) - (-4.10) = 1.20\text{ pt}$$
- Nét bút viết tay `_pen(eff)` có độ dày $1.41\text{ pt}$. Khoảng hở $1.20\text{ pt} < 1.41\text{ pt}$ khiến nét mực thực tế của chỉ số trên `9` và chỉ số dưới `j=1` **đè bẹp trực tiếp lên nhau**.
- Trong kiểu chữ viết tay, ký tự `9` có đuôi nhô xuống và `j` có dấu chấm nhô lên, khiến hiện tượng đè nét càng thêm trầm trọng như thấy ở Ảnh 2.

### Quyết định kỹ thuật
- **Quyết định**: Áp dụng quy tắc khoảng cách an toàn quang học tối thiểu (Minimum Sub-Superscript Clearance - TeX Rule 18):
  - Định nghĩa ngưỡng khoảng hở an toàn:
    $$\text{min\_gap} = \max(3.5 \times \text{eff}, 0.40 \times \text{xh} \times \text{eff})$$
  - Khi cả `sup` và `sub` đều hiện diện:
    1. Xác định biên quang học thực tế của hai chỉ số bằng `_get_item_ink_bounds`:
       - `sup_bot = sup_y + max(sup.size.descent, sup_ink_bot)`
       - `sub_top = sub_y + min(-sub.size.ascent, sub_ink_top)`
    2. Tính khoảng cách thực tế: $\text{gap} = \text{sub\_top} - \text{sup\_bot}$.
    3. Nếu $\text{gap} < \text{min\_gap}$:
       - Tính độ hụt: $\text{deficit} = \text{min\_gap} - \text{gap}$.
       - Đẩy chỉ số dưới xuống: $\text{sub\_y} \mathrel{+}= \text{deficit} \times 0.65$.
       - Nâng chỉ số trên lên: $\text{sup\_y} \mathrel{-}= \text{deficit} \times 0.35$.
    4. Cập nhật lại `ascent` và `descent` của `MathLayoutItem` tương ứng:
       - $\text{ascent} = \max(\text{ascent}, -\text{sup\_y} + \text{sup.size.ascent})$
       - $\text{descent} = \max(\text{descent}, \text{sub\_y} + \text{sub.size.descent})$
- **Lý do lựa chọn**:
  - Giải quyết triệt để vấn đề đè nét mực theo đúng chuẩn in ấn toán học quốc tế (TeX Book Appendix G).
  - Tự động thích ứng với mọi kích thước tỉ lệ `scale` và nét chữ viết tay cụ thể nhờ kiểm tra biên mực quang học `_get_item_ink_bounds`.
- **Phương án khác đã xem xét và bác bỏ**:
  - *Đẩy chỉ số dưới lùi sang phải (Horizontal Staggering)*: Làm mất tính thẩm mỹ tiêu chuẩn của ký hiệu toán $\sum_i^n$ (chỉ phù hợp với ký hiệu tensor).

---

## 3. Nghiên cứu 3: Quy trình đóng gói và đồng bộ Web Distribution

### Bối cảnh & Vấn đề
- Ứng dụng Web tĩnh (`webapp/`) chạy engine Python trong trình duyệt thông qua Pyodide WebAssembly.
- Mã nguồn Python nằm trong `chuviettay/` được đóng gói thành tệp zip tại `webapp/dist/pyodide/chuviettay.zip`.
- Trình duyệt và Service Worker dựa vào mã băm nội dung của bản đóng gói để tự động tải lại phiên bản mới nhất.

### Quyết định kỹ thuật
- Tự động chạy lệnh `python scripts/build_web.py` sau khi hoàn thành sửa đổi trong `chuviettay/` để cập nhật gói `chuviettay.zip` và tệp `sw.js`.
- Bổ sung kiểm thử tự động xác thực gói đóng gói và kiểm thử hồi quy trên các mẫu Markdown toán học.

---

## Tóm tắt các quyết định (Decisions Summary)

| Vấn đề | Quyết định | Vị trí can thiệp |
|--------|------------|------------------|
| `a\n$$...$$` bị biến thành `MathInline` | Tiền chuẩn hóa cách ly dòng trống cho khối toán `$$` | `chuviettay/importer/markdown_importer.py` |
| `ta có:$$...$$` bị dính liền | Tách nhãn mở đầu `:` ra khỏi `$$` với dòng trống | `chuviettay/importer/markdown_importer.py` |
| Cận trên `9` đè cận dưới `j=1` khi cận bên | Cưỡng chế khoảng hở quang học an toàn $\ge 3.5\text{ pt}$ | `chuviettay/layout/math_layout.py` |
| Đồng bộ bản chạy Web Client | Chạy script đóng gói tự động `build_web.py` | `scripts/build_web.py` |
