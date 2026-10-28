# Quickstart: Hướng dẫn kiểm chứng tính năng 063

**Branch**: `063-pua-placeholder-optimization` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

Tài liệu này cung cấp các lệnh cần thiết để kiểm chứng nhanh các thay đổi của tính năng tối ưu hóa tìm kiếm ký tự PUA và kiểm thử cạn kiệt toàn bộ dải PUA.

---

## 1. Chuẩn bị môi trường

Đảm bảo môi trường ảo Python đã được kích hoạt và cài đặt đầy đủ các thư viện kiểm thử:

```powershell
# Kích hoạt virtualenv (nếu có)
.venv\Scripts\Activate.ps1
```

---

## 2. Các lệnh kiểm chứng trọng tâm

### 2.1. Chạy bộ kiểm thử cô lập khối toán Markdown (bao gồm các ca PUA mới)

```powershell
pytest tests/test_markdown_math_block_isolation.py -v -k "pua or placeholder"
```

*Kỳ vọng*: Tất cả các ca kiểm thử liên quan đến `_choose_fake_close_placeholder`, va chạm liên tiếp, va chạm không liên tục, và cạn kiệt 6.400 ký tự đều hiển thị `PASSED`.

### 2.2. Chạy toàn bộ file kiểm thử cô lập khối toán Markdown

```powershell
pytest tests/test_markdown_math_block_isolation.py -v
```

*Kỳ vọng*: 100% các ca kiểm thử (bao gồm các ca bảo toàn LaTeX `\$\$`, blockquote lồng nhau của commit 81df7a2) đều `PASSED`.

### 2.3. Chạy bộ kiểm thử Markdown Importer

```powershell
pytest tests/test_markdown_importer.py -v
```

---

## 3. Kiểm tra chất lượng mã nguồn (Linting & Formatting)

```powershell
ruff check chuviettay/importer/markdown_importer.py tests/test_markdown_math_block_isolation.py
```

*Kỳ vọng*: Không có lỗi cú pháp hoặc vi phạm chuẩn ruff nào (`All checks passed!`).

---

## 4. Kiểm chứng tương thích CI hoàn chỉnh

```powershell
# 1. Chạy toàn bộ test Python
pytest

# 2. Kiểm chứng Golden Master Pyodide Web Client
node scripts/test_golden_pyodide.mjs
```
