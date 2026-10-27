# Contract: Fake Close Placeholder & LaTeX Preservation

**Feature**: 062 | **Scope**: `chuviettay/importer/markdown_importer.py` (nội bộ) + `tests/test_markdown_math_block_isolation.py`

Giao diện công khai `MarkdownImporter.import_text(text) -> ImportResult` và `import_file(path)` **không đổi chữ ký**. Các hàm dưới đây là nội bộ (tiền tố `_`) nhưng được test gọi trực tiếp nên được mô tả hợp đồng.

## C1. `_choose_fake_close_placeholder(text: str) -> str | None` (classmethod/staticmethod mới)

- Trả về ký tự nhỏ nhất trong U+E000…U+F8FF không có trong `text`; `None` nếu không còn ký tự nào.
- Thuần (pure), không phụ thuộc trạng thái.

## C2. `_isolate_display_math_blocks(seg: str, fake_close_placeholder: str | None = "") -> str`

- Tham số `fake_close_placeholder` có mặc định `""` (sentinel kiểu `str`): khi không truyền (`""`) và `"$$" in seg`, hàm tự gọi C1 trên `seg` sau chuẩn hóa CRLF.
- Với dấu đóng giả (xem data-model §1): nếu `fake_close_placeholder` là chuỗi 1 ký tự khác rỗng, thay `$$` cuối dòng bằng `fake_close_placeholder`, giữ nguyên phần đuôi (dấu câu + khoảng trắng).
- Nếu `fake_close_placeholder is None`: giữ nguyên dòng (không quét lại C1; cho phép kiểm thử trực tiếp nhánh fallback).
- Không bao giờ phát sinh chuỗi `\$\$` mới.
- Mọi hành vi khác (bảng, hàng rào mã, mã thụt lề, thoát khối chứa, tách `$$` nội dòng) giữ nguyên như Feature 061.

## C3. `_restore_fake_close_placeholder(tokens, placeholder) -> None` (mới)

- Duyệt đệ quy `tokens` và `token.children`; thay mọi `placeholder` trong cả `token.content` và `token.info` bằng `$$`.
- Nếu `not placeholder`: không làm gì (`O(1)`).

## C4. `_parse_blocks(...)`

- Với token công thức khối: `MathBlock(latex=tok.content.strip())` — **không** có thêm phép thay thế nào.

## C5. Hợp đồng kiểm thử (giá trị mong đợi chính xác)

| ID | Đầu vào | Kỳ vọng |
|---|---|---|
| T-ISO | `> $$\n> x = 1\n>> $$\n> x = 2\n> $$` qua `_isolate_display_math_blocks` | `== "> $$\n> x = 1\n>> \ue000\n> x = 2\n> $$"` |
| T-NEST | Như trên qua `import_text` | Đúng 1 `MathBlock`, `latex == "> x = 1\n>> $$\n> x = 2\n>"` |
| T-PUNCT | `> $$\n> a = 1\n>> $$,   \n> a = 2\n> $$` qua `import_text` | Đúng 1 `MathBlock`, `latex == "> a = 1\n>> $$,   \n> a = 2\n>"` |
| T-ESC1 | `$$\text{\$\$}$$` | Đúng 1 `MathBlock`, `latex == r"\text{\$\$}"` |
| T-ESC2 | `$$\n\text{\$\$}\n$$` | `latex == r"\text{\$\$}"` |
| T-ESC3 | `> $$\n> \text{\$\$}\n> $$` | `latex == "> \\text{\\$\\$}\n>"` |
| T-COMBO | `> $$\n> \text{\$\$}\n>> $$\n> x = 2\n> $$` | Đúng 1 `MathBlock`, `latex == "> \\text{\\$\\$}\n>> $$\n> x = 2\n>"` |
| T-MULTI | Một dòng `$$\$ + \text{\$\$\$\$}$$` và nhiều dòng `$$\n\$ + \$\$\$\$\n$$` | Tương ứng `latex == r"\$ + \text{\$\$\$\$}"` và `latex == r"\$ + \$\$\$\$"` |
| T-COLL | Đầu vào chứa sẵn `\ue000` + ca lồng nhau | `\ue000` của người dùng giữ nguyên; `MathBlock` đúng như T-NEST |
| T-LEAK | `> $$\n> x = 1\n>> $$\n> x = 2` (không đóng) | Không ký tự PUA nào trong `Document` hay `unsupported`; đoạn văn chứa chữ `$$` như hành vi hiện tại |

Toàn bộ ca nhóm 061 hiện có (32 test trong tệp) MUST tiếp tục vượt qua.
