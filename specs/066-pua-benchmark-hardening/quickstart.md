# Quickstart: Hướng dẫn Kiểm chứng Benchmark Hardening và CI Smoke Test

**Feature**: `066-pua-benchmark-hardening` | **Date**: 2026-10-28

---

## 1. Kiểm chứng Kịch bản Benchmark Độc lập

Thực thi kịch bản với các tham số khác nhau:

```powershell
# 1. Chạy mặc định (5 rounds) và kiểm tra mô tả đa ngữ cùng kích thước byte UTF-8
python scripts/benchmark_pua_memory.py

# 2. Chạy với số rounds tùy chỉnh (ví dụ 2 rounds) và kiểm tra cả kịch bản chính lẫn đối kháng
python scripts/benchmark_pua_memory.py --rounds 2

# 3. Xuất JSON và kiểm tra các trường dữ liệu
python scripts/benchmark_pua_memory.py --rounds 1 --json
```

*Kỳ vọng*:
- Báo cáo hiển thị đúng: "Han/Nom (CJK), Cyrillic, Greek, Math Operators".
- Kích thước byte UTF-8 được tính chính xác: `~1.48 MB` (1.479.003 bytes).
- Cả hai kịch bản đều hoàn tất đúng số lượt đo được chỉ định.

---

## 2. Kiểm chứng Smoke Test Pytest

```powershell
pytest tests/test_benchmark_pua_smoke.py -v
```

*Kỳ vọng*:
- Test hoàn thành thành công trong < 3 giây, xác nhận JSON hợp lệ và mã thoát 0.

---

## 3. Kiểm tra Tính Hợp lệ CI và Linting

```powershell
# 1. Kiểm tra cú pháp YAML của CI workflow
git diff .github/workflows/ci.yml

# 2. Linting toàn bộ
ruff check chuviettay tests scripts
```

*Kỳ vọng*: `All checks passed!`
