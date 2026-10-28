# Quickstart: Hướng dẫn kiểm chứng tính năng 064

**Branch**: `064-pua-memory-and-benchmark` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

Tài liệu này cung cấp các lệnh cần thiết để kiểm chứng các cải tiến khống chế bộ nhớ tập hợp PUA và kiểm thử hiệu năng đối kháng bằng thống kê trung vị.

---

## 1. Kiểm tra đơn vị khống chế bộ nhớ PUA

```powershell
pytest tests/test_markdown_math_block_isolation.py -v -k "pua or placeholder"
```

*Kỳ vọng*:
- Tất cả các ca kiểm thử PUA (fast-path, chuỗi va chạm, va chạm ngắt quãng, cạn kiệt và kiểm thử đa ngữ khống chế bộ nhớ) đều hiển thị `PASSED`.

---

## 2. Kiểm chứng bài kiểm thử hiệu năng đối kháng (Thống kê trung vị)

```powershell
pytest tests/test_markdown_math_block_isolation.py -v -k "test_adversarial_complexity_multi_length_backticks_and_long_lines"
```

*Kỳ vọng*:
- Kiểm thử chạy 5 lượt đo độc lập, tính toán trung vị $T(4N)/T(N) \le 6.0$, hoàn tất thành công mà không phát sinh lỗi dao động.

---

## 3. Kiểm tra chất lượng mã nguồn (Linting)

```powershell
ruff check chuviettay/importer/markdown_importer.py tests/test_markdown_math_block_isolation.py
```

*Kỳ vọng*: `All checks passed!`

---

## 4. Kiểm chứng toàn diện CI

```powershell
# 1. Toàn bộ test suite Python
python -m pytest

# 2. Kiểm chứng Golden Master WebAssembly trong Pyodide
node scripts/test_golden_pyodide.mjs
```
