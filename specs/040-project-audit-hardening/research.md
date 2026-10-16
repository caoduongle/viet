# Research: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng (Project Audit & Hardening)

**Feature Branch**: `040-project-audit-hardening`  
**Date**: 2026-10-16  
**Status**: Completed  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Nghiên cứu & Quyết định Kỹ thuật

### Quyết định 1: Bảo toàn cấu trúc DOCX sang Markdown qua Round-trip Escaping

- **Vấn đề**: `BrowserBridge._document_to_markdown_dict` không escape các ký tự đặc biệt của Markdown khiến các công thức toán hoặc text chứa `*`, `_`, `~`, `#`, `$`, `\`, `|` bị hiểu nhầm thành cú pháp định dạng khi nạp vào editor; công thức toán độc lập `MathBlock` bị bỏ sót; ngắt dòng `LineBreak` trong ô bảng làm vỡ dòng bảng.
- **Quyết định chọn**:
  1. Xử lý tường minh các khối `MathBlock` (`$$...$$`), `Heading` (`#`..`######`) và `Paragraph`.
  2. Áp dụng hàm escape cho nội dung text khi serialize sang Markdown: escape các ký tự `\`, `*`, `_`, `~`, `#`, `$`, `|` để bảo đảm khi chạy qua `MarkdownImporter.import_text`, tài liệu được tái tạo 100% nguyên trạng.
  3. Trong ô bảng: escape `\|` cho cả text và công thức LaTeX; chuyển `LineBreak` thành khoảng trắng thay vì `\n`.
  4. Nối các run trong inlines bằng chuỗi rỗng `"".join(parts)` vì các phần tử `Text` đã bảo toàn khoảng trắng gốc.
- **Lý do**: Giải quyết triệt để vấn đề mất dữ liệu và vỡ cấu trúc khi mở tài liệu DOCX trên Web.

---

### Quyết định 2: Hỗ trợ Căn lề Đoạn văn (`left`, `center`, `right`, `justify`) ở cấp độ Core Engine & IR

- **Vấn đề**: `Paragraph.align` đã có trong IR nhưng `DocumentLayoutEngine.render_paragraph_inlines` luôn đặt dòng ở `line_start_x = self.x0 + indent`.
- **Quyết định chọn**:
  1. Truyền `align=block.align` vào `render_paragraph_inlines` (chỉ áp dụng cho `Paragraph`, các khối `Heading` và `ListBlock` giữ mặc định `"left"`).
  2. Trong hàm `flush_line`:
     - Phân biệt 3 trường hợp flush: (a) Dòng tràn; (b) Dòng kết thúc bằng `LineBreak`; (c) Dòng cuối của đoạn.
     - Với `align == "left"`: `line_start_x = self.x0 + indent`.
     - Với `align == "center"`: `line_start_x = self.x0 + indent + rem_space / 2.0`.
     - Với `align == "right"`: `line_start_x = self.x0 + indent + rem_space`.
     - Với `align == "justify"`:
       - Chỉ phân bổ khoảng cách từ cho dòng tràn (`gap = rem_space / (N - 1)`).
       - Dòng kết thúc bởi `LineBreak` hoặc dòng cuối đoạn giữ căn trái tự nhiên.
       - Dựng lại `RenderItem` mới với `start` đã dời để `token_layout_callback` nhận đúng tọa độ hộp bao quanh từ.
- **Lý do**: Thuật toán hình học chuẩn xác, đảm bảo căn trái giữ nguyên kết xuất Golden Master.

---

### Quyết định 3: Chống XSS & Hiển thị SVG Xem thử Thật trong `webapp/js/bank.js`

- **Vấn đề**:
  - Các nhãn `label` và `err.message` được nội suy trực tiếp vào `innerHTML` trong `bank.js`.
  - `handleRandomPreview()` gửi yêu cầu `write_text` nhưng chỉ hiển thị chuỗi seed, không vẽ nét chữ.
- **Quyết định chọn**:
  1. Tạo module `webapp/js/html-utils.js` xuất hàm `escapeHtml(str)` dùng chung cho cả `bank.js` và `write.js`.
  2. Tích hợp `decompressXoppBase64`, `parseXoppXml`, và `renderPageSvgElement` từ `paper.js` vào `handleRandomPreview`. Cắt gọn viewBox theo bbox của nét vẽ cộng padding, gửi kèm tùy chọn `missing_grid: false` để tránh rác MEMFS, và kiểm tra hủy kết quả cũ nếu người dùng chuyển nhãn khác.
- **Lý do**: Đảm bảo an toàn DOM và mang lại trải nghiệm xem trước trực quan cho người dùng.

---

### Quyết định 4: Bật `strikethrough` và Ghi nhận Cảnh báo trong `MarkdownImporter`

- **Vấn đề**: `markdown-it-py` chưa bật plugin `strikethrough` khiến `~~text~~` để lại dấu `~~` trên giấy; các định dạng kiểu chữ giàu bị làm phẳng mà không có cảnh báo.
- **Quyết định chọn**:
  1. Kích hoạt `.enable("strikethrough")` trên `MarkdownIt`.
  2. Ghi nhận cảnh báo hợp nhất vào `ImportResult.warnings` (tối đa 1 thông điệp cảnh báo cho mỗi lần import) khi phát hiện thẻ kiểu chữ giàu (`strong`, `em`, `s`, `code_inline`, `link`).
- **Lý do**: Làm sạch nét chữ viết tay và minh bạch hóa hành vi làm phẳng định dạng cho người dùng.

---

### Quyết định 5: Loại bỏ Cơ chế Desktop Cũ & Chuẩn hóa Kho Mã nguồn

- **Vấn đề**: Tàn dư từ CLI desktop cũ: tự sinh file `*_thieu.xopp` làm rò rỉ MEMFS, nhánh sinh lưới cũ `hw2`, tệp test trùng lặp và script chẩn đoán `repro_viet_baseline.py` ở thư mục gốc.
- **Quyết định chọn**:
  1. Đổi mặc định `WriteOptions.missing_grid = False`, chấm dứt việc tự động ghi file `*_thieu.xopp`.
  2. Xóa nhánh sinh lưới `hw2` trong `xopp.make_grid` (chỉ tạo chuẩn `hw3`), cập nhật thông điệp hướng dẫn trên trang lưới ô theo đúng nhãn giao diện Web hiện hành.
  3. Chuyển test thứ 5 từ `tests/test_web_parse_seed.test.mjs` sang `tests/js/parse_seed.test.mjs` rồi xóa file trùng.
  4. Chuyển các ca kiểm thử hồi quy từ `repro_viet_baseline.py` vào `tests/test_regression_audit.py` rồi xóa `repro_viet_baseline.py`.
  5. Giữ `chuviettay/fidelity/` làm archive cách ly.
- **Lý do**: Chấm dứt rò rỉ tài nguyên bộ nhớ trên trình duyệt và làm sạch 100% kho mã nguồn.
