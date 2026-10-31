# Data Model: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu

**Feature**: `067-content-seed-bank-hardening`  
**Date**: 2026-10-31  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Mô hình Thông báo Nội dung Không Hỗ trợ & Cảnh báo Giản lược (Unsupported & Warnings Model)

Để bảo toàn tương thích ngược 100% với các bài kiểm thử hợp đồng hiện có (`tests/test_markdown_math_import.py`, `tests/test_markdown_math_block_isolation.py`) đồng thời cung cấp thông báo rõ ràng trên giao diện người dùng, hệ thống phân tách rõ mã định danh chuẩn trong `ImportResult` và thông điệp hiển thị trên Web UI:

```text
+-----------------------------------------------------------------------+
|                       ImportResult (Backend IR)                       |
+-----------------------------------------------------------------------+
| - document: Document                                                  |
| - warnings: list[str]      # Thông báo giản lược định dạng / trích dẫn|
| - unsupported: list[str]   # Mã chuẩn của phần tử không vẽ nét        |
+-----------------------------------------------------------------------+
```

### Quy tắc ánh xạ phần tử Markdown:
1. **`ImportResult.unsupported` (Phần tử không tạo nét vẽ hình học tương ứng)**:
   - Khối mã (`fence`, `code_block`): `"code_block"` (khi không có info string) hoặc `f"code_block: {info}"` (khi có info string).
   - Đường kẻ ngang (`hr`): `"hr: horizontal rule"`.
   - Bảng nằm trong mục danh sách: `"table: table inside list item"`.
   - Hình ảnh nội dòng (`image`): `f"image: {alt}"` (khi có văn bản thay thế `alt`, đồng thời giữ `Text(alt)` trong đoạn văn) hoặc `"image"` (khi không có văn bản thay thế).
2. **`ImportResult.warnings` (Phần tử vẫn kết xuất đầy đủ nội dung nhưng giản lược kiểu trình bày)**:
   - Kiểu chữ nội dòng (`strong_open`, `em_open`, `s_open`, `link_open`, `code_inline`): `"Định dạng kiểu chữ (in đậm, in nghiêng, gạch ngang, mã nội tuyến...) đã được chuyển về nét viết tay chuẩn."`
   - Khối trích dẫn (`blockquote_open`): `"Khối trích dẫn (blockquote) đã được chuyển về đoạn văn viết tay tiêu chuẩn."`

---

## 2. Mô hình Quy tắc Kiểm tra Hợp lệ Tùy chọn Viết (`WriteOptions` Validation Rules)

Mô hình định nghĩa quy tắc thẩm định nghiêm ngặt cho đối tượng `WriteOptions` trong `chuviettay/model/composer.py`.

| Thuộc tính | Kiểu dữ liệu | Ràng buộc hợp lệ (`validate()`) |
| :--- | :--- | :--- |
| `scale` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0` |
| `line` | `float \| int \| None` | `None` hoặc (`not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0`) |
| `width` | `float \| int \| None` | `None` hoặc (`not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0`) |
| `space` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v >= 0.0` |
| `jitter` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v >= 0.0` |
| `wscale` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0` |
| `letter_gap` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `0.0 <= v <= 10.0` |
| `target_xh` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `0.0 < v <= 100.0` |
| `pen_clearance_factor` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `0.0 <= v <= 10.0` |
| `margin_left`, `margin_right`, `margin_top`, `margin_bottom` | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v >= 0.0` |
| `paper_width`, `paper_height` (khi `paper="custom"`) | `float \| int` | `not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0` |
| `background_spacing` | `float \| int \| None` | `None` hoặc (`not isinstance(v, bool)`, `math.isfinite(v)`, `v > 0.0`) |
| `background_margin` | `float \| int \| None` | `None` hoặc (`not isinstance(v, bool)`, `math.isfinite(v)`) |
| `auto_xh`, `stable_variants`, `assemble_letters`, `snap_to_ruling`, `strict_case`, `missing_grid` | `bool` | `isinstance(v, bool)` |

---

## 3. Mô hình Bản chụp Kho mẫu (`BankSnapshot` Model)

Mô hình dữ liệu trả về từ API `get_bank_snapshot()` của `BrowserBridge` (qua `py-worker.js`) phục vụ tab Kho mẫu trên Web UI (`webapp/js/bank.js`).

```text
+------------------------------------------------------------------+
|                           BankSnapshot                           |
+------------------------------------------------------------------+
| - revision: int                   # Số hiệu phiên bản đơn điệu   |
| - stats: BankStatsDict            # Thống kê tổng quan kho mẫu   |
| - letters: list[list[str | int]]  # Danh sách [chữ cái, số mẫu]  |
| - digits: dict[str, int]          # Thống kê mẫu chữ số          |
| - punct: dict[str, int]           # Thống kê mẫu dấu câu         |
| - symbols: list[list[str | int]]  # Danh sách [ký hiệu, số mẫu]  |
| - marks: list[list[str | int]]    # Danh sách [dấu thanh, số mẫu]|
+------------------------------------------------------------------+
```

### Chu kỳ chuyển dịch trạng thái (`bank_revision` Lifecycle):
1. **Khởi tạo**: `BrowserBridge.bank_revision = 1`.
2. **Biến đổi kho mẫu**: Mỗi khi gọi thành công một trong các thao tác thay đổi trạng thái kho mẫu (`init`, `load_bank`, `teach_sample`, `teach_char`, `import_grid`, `drop_label`, `drop_chars`, `drop_label_samples`), tăng `self.bank_revision += 1`.
3. **Truy vấn & Đồng bộ Web UI**:
   - `get_bank_snapshot()` trả về `revision` hiện hành cùng toàn bộ dữ liệu danh mục.
   - `webapp/js/bank.js` lưu cặp `(lastLoadedRevision, lastLoadedProfileId)`.
   - Nếu `options.force` không bật và `(snapshot.revision === lastLoadedRevision && currentProfileId === lastLoadedProfileId && allBankItems.length > 0)`, giao diện giữ nguyên lưới thẻ DOM hiện tại.

---

## 4. Mô hình Đối chiếu Hạt giống Tài liệu (`SeedAlignmentContext` Model)

Cấu trúc ánh xạ giữa tài liệu nguồn (`base_doc`) và tài liệu chỉnh sửa (`edited_doc`) trong `chuviettay/document/ir.py`:

```text
+--------------------------------------------------------------------+
|                    SeedAlignmentContext                            |
+--------------------------------------------------------------------+
| - base_keys: list[tuple[str, str]]    # (content_type, element_id) |
| - edited_keys: list[tuple[str, str]]  # (content_type, element_id) |
| - prefix_len: int                     # Độ dài tiền tố khớp O(N)   |
| - suffix_len: int                     # Độ dài hậu tố khớp O(N)    |
| - autojunk: bool                      # False cho vùng giữa <=8000 |
| - assigned_occs: list[int]            # Chỉ số occurrence ánh xạ   |
+--------------------------------------------------------------------+
```

### Bất biến nghiệp vụ:
- Cắt bỏ tiền tố chung (`prefix_len`) và hậu tố chung (`suffix_len`) trong thời gian $O(N)$ trước khi gọi `SequenceMatcher` giúp mọi thao tác chèn/sửa/xóa cục bộ giữ nguyên 100% `occurrence` của phần đầu và phần cuối tài liệu trong $< 5\text{ms}$.
- Đối với phần giữa (`base_mid`, `edited_mid`), tắt `autojunk=False` (khi tổng độ dài đoạn giữa $\le 8.000$ token) để các từ tiếng Việt phổ biến lặp lại hàng trăm lần vẫn được ghép khớp LCS chính xác tuyệt đối.
