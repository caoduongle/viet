# Quickstart: Hướng dẫn Kiểm chứng Đo lường Bộ nhớ và Tái lập Benchmark PUA

**Feature**: `065-pua-verification-reproducibility` | **Date**: 2026-10-28

---

## 1. Kiểm thử Đơn vị & Đo lường Bộ nhớ Đỉnh trực tiếp

Kích hoạt các bài kiểm thử xác nhận trực tiếp kích thước tập hợp `used_cps` và mức tăng bộ nhớ đỉnh qua `tracemalloc`:

```powershell
pytest tests/test_markdown_math_block_isolation.py -v -k "pua or placeholder or tracemalloc"
```

*Kỳ vọng*:
- `test_pua_codepoint_collection_direct_and_bounded`: PASS (xác nhận `len(used_cps) == 1` với 10k chữ Nôm và `len(used_cps) == 10` với 10 PUA).
- `test_pua_memory_allocation_bounded_tracemalloc`: PASS (xác nhận mức tăng bộ nhớ đỉnh $\le 50\text{KB}$, không bùng nổ theo kích thước bảng chữ cái tài liệu).
- Toàn bộ các bài kiểm thử PUA khác tiếp tục PASSED 100%.

---

## 2. Tái lập Số liệu Hiệu năng bằng Kịch bản Dòng lệnh Độc lập

Chạy trực tiếp kịch bản benchmark bằng Python để kiểm chứng các chỉ số thời gian và mức tiêu thụ bộ nhớ:

```powershell
# Chạy mặc định 5 lượt đo kèm in bảng định dạng Markdown
python scripts/benchmark_pua_memory.py

# Hoặc xuất dữ liệu dạng JSON cho phân tích tự động
python scripts/benchmark_pua_memory.py --json
```

*Kỳ vọng*:
- Kịch bản tự động hiển thị thông tin môi trường (phiên bản Python, hệ điều hành, CPU, timestamp).
- Kết quả cho thấy phương pháp `finditer()` nhanh hơn ít nhất **10x** đến **100x** so với `set(text)` trên văn bản đa ngữ 10.000 ký tự phân biệt.
- Trong kịch bản đối kháng lặp lại 100.000 ký tự PUA, `finditer()` tiêu thụ bộ nhớ đỉnh thấp hơn hàng nghìn lần so với `findall()`.

---

## 3. Kiểm tra Tính Toàn vẹn Mã nguồn (Lint & Regression)

```powershell
# 1. Lint code style
ruff check chuviettay tests scripts

# 2. Toàn bộ test suite markdown isolation
pytest tests/test_markdown_math_block_isolation.py

# 3. Web Client Pyodide Golden Master
node scripts/test_golden_pyodide.mjs
```

*Kỳ vọng*:
- Tất cả các kiểm tra hoàn thành với mã thoát 0.
