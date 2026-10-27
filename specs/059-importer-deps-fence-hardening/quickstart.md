# Quickstart & Validation Guide: Feature 059

**Feature**: `059-importer-deps-fence-hardening`
**Date**: 2026-10-28

---

## 1. Kiểm thử Môi trường Tối giản và Bộ phân tích Markdown

Chạy bộ kiểm thử đơn vị và tích hợp cho phụ thuộc tùy chọn, trích dẫn lồng nhau, điều kiện mở code fence và hiệu năng đối kháng:

```powershell
pytest tests/test_markdown_math_block_isolation.py -v
```

**Kết quả kỳ vọng**:
- Các kiểm thử mô phỏng môi trường thiếu `markdown_it` xác nhận import `chuviettay.importer`, `TxtImporter`, `get_importer_for_path(..., format_name="txt")` và controller thành công; gọi `MarkdownImporter()` hoặc處理 bảng khi thiếu `markdown_it` ném `OptionalDependencyError`.
- Các kiểm thử code fence trong blockquote (`>` vs `>>`), chuỗi thông tin chứa backtick (```` ```info`invalid ````), và khối mã thụt lề trong blockquote đều vượt qua.
- Kiểm thử hiệu năng đối kháng với đa độ dài backtick không đóng và dòng dài đạt tỷ lệ $T(4N)/T(N) \le 6.0$ và bảo toàn 100% nội dung.

---

## 2. Kiểm thử Toàn bộ Suite Python & Golden Master

```powershell
pytest
node scripts/test_golden_pyodide.mjs
npm run test:unit
```

**Kết quả kỳ vọng**:
- 100% bài kiểm thử Python và JavaScript vượt qua.
- 8/8 ca chuẩn Golden Master khớp mã băm SHA-256 tuyệt đối.
