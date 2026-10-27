# Quickstart & Validation Guide: Feature 062

**Feature**: `062-fake-close-placeholder-restore` | **Date**: 2026-10-28

Chạy từ thư mục gốc repo (`d:\viet\app`). Hợp đồng chi tiết: [contracts/fake-close-placeholder-contract.md](./contracts/fake-close-placeholder-contract.md).

> [!NOTE]
> PowerShell mở rộng `$$` trong chuỗi nháy kép. Kiểm chứng thủ công nên viết thành tệp `.py` hoặc chạy qua pytest, không dùng `python -c "...$$..."`.

## 1. Kiểm thử trọng tâm

```powershell
pytest tests/test_markdown_math_block_isolation.py -k "escaped_dollar or blank_line_exit_and_matching_depth_close or placeholder" -v
```

**Kỳ vọng**: Tất cả PASS — công thức chứa `\$\$` giữ nguyên từng ký tự (T-ESC1..3, T-MULTI, T-COMBO); ca lồng nhau so sánh `==` cho cả chuỗi cô lập (T-ISO) và `MathBlock.latex` (T-NEST, T-PUNCT); không rò rỉ ký tự PUA (T-LEAK, T-COLL).

## 2. Toàn bộ tệp kiểm thử importer

```powershell
pytest tests/test_markdown_math_block_isolation.py -v
```

**Kỳ vọng**: 32 test cũ + các test mới đều PASS; benchmark vẫn thỏa `T(4N)/T(N) ≤ 6.0`.

## 3. Cổng chất lượng đầy đủ

```powershell
ruff check chuviettay tests scripts
pytest
npm run test:unit
npm run test:browser
python scripts/build_web.py
node scripts/test_golden_pyodide.mjs
npm run test:e2e
```

**Kỳ vọng**: Ruff 0 lỗi; Pytest 100% (≥ 1.325 test + test mới); 65 JS unit test; 2 browser suite; Golden Master 8/8 trùng SHA-256 (không cập nhật mã băm); 19 Playwright E2E.
