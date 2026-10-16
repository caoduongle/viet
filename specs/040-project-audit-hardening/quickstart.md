# Quickstart Validation Guide: Rà soát Toàn diện Dự án và Kế hoạch Cải thiện Chất lượng

**Feature Branch**: `040-project-audit-hardening`  
**Date**: 2026-10-16  
**Status**: Ready  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Điều kiện Tiên quyết

- Python 3.12 (môi trường CI & cục bộ).
- Node.js 18+.
- Môi trường đã cài đặt dependencies qua `pip install -e .` và `npm install`.

---

## 2. Các Kịch bản Kiểm chứng Độc lập

### Kịch bản 1: Kiểm chứng Toàn vẹn Khối DOCX & Round-trip Markdown (US1)
Mục tiêu: Đảm bảo `MathBlock`, `Heading`, `*`, `_`, `~`, `#`, `$`, `\`, `|` không bị biến dạng khi chuyển đổi sang Markdown và re-import.

```bash
py -3.12 -m pytest tests/test_regression_audit.py -k "test_docx_markdown_roundtrip" -vv
```

---

### Kịch bản 2: Kiểm chứng Căn lề Đoạn văn (`left`, `center`, `right`, `justify`) (US2)
Mục tiêu: Đảm bảo tọa độ ngang dòng chữ và hộp bao quanh từ khớp chuẩn hình học, bảo đảm căn trái giữ nguyên Golden Master.

```bash
py -3.12 -m pytest tests/test_regression_audit.py -k "test_paragraph_alignment" -vv
py -3.12 -m pytest tests/test_golden_master_real_path.py -vv
```

---

### Kịch bản 3: Kiểm chứng An toàn Giao diện & Hiển thị SVG trong Kho mẫu (US3)
Mục tiêu: Module `escapeHtml` xử lý sạch ký tự đặc biệt và modal xem thử dựng SVG nét vẽ.

```bash
# Unit test hàm escapeHtml và logic xử lý viewBox
npm run test:unit

# E2E test kiểm tra tương tác DOM và modal xem thử
npm run test:e2e
```

---

### Kịch bản 4: Kiểm chứng Gạch ngang Markdown & Cảnh báo Định dạng Giàu (US4)
Mục tiêu: Cú pháp `~~text~~` được xử lý sạch dấu `~~` và `ImportResult.warnings` ghi nhận cảnh báo.

```bash
py -3.12 -m pytest tests/test_regression_audit.py -k "test_markdown_strikethrough" -vv
```

---

### Kịch bản 5: Kiểm chứng Loại bỏ Cơ chế Desktop Cũ & Quality Gates (US5)
Mục tiêu: `missing_grid` mặc định `False`, không tự sinh file `*_thieu.xopp`, không còn `hw2`, và toàn bộ cổng CI pass.

```bash
# 1. Kiểm tra không đẻ file _thieu.xopp và không còn hw2
py -3.12 -m pytest tests/test_regression_audit.py -k "test_desktop_legacy" -vv

# 2. Toàn bộ cổng chất lượng CI
ruff check .
py -3.12 -m compileall -q .
py -3.12 -m pytest -vv -s --timeout=60 -m "not benchmark"
py -3.12 scripts/build_web.py && npm run test:unit && npm run test:browser
```
