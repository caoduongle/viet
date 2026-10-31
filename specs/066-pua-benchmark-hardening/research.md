# Research: Phân tích Kỹ thuật Chuẩn hóa Benchmark PUA và CI Smoke Test

**Feature**: `066-pua-benchmark-hardening` | **Date**: 2026-10-28

---

## 1. Vấn đề Kỹ thuật Cần Xử lý

Từ đợt đánh giá commit `3b20612`, ba điểm P3 được chỉ ra:
1. **P3-1**: Tham số `--rounds` chỉ áp dụng cho bộ dữ liệu chính, kịch bản đối kháng lặp 100k PUA truyền cứng `rounds=3`, gây mâu thuẫn với mô tả CLI.
2. **P3-2**: Mô tả bộ dữ liệu ghi là đa ngữ (Cyrillic, Math, Han/Nom) nhưng thực tế mã cũ chỉ sinh từ dải CJK; kích thước byte ghi cố định `~1.0 MB` trong khi thực tế 510k ký tự CJK chiếm `~1.53 MB`.
3. **P3-3**: Workflow CI (`.github/workflows/ci.yml`) chưa có bước gọi trực tiếp `scripts/benchmark_pua_memory.py`, dẫn đến nguy cơ script bị hỏng âm thầm mà CI không phát hiện được.

---

## 2. Giải pháp Kỹ thuật Chi tiết

### 2.1. Chuẩn hóa tham số `--rounds`
- Trong hàm `run_benchmarks(rounds: int = 5)`:
  - Áp dụng thống nhất `rounds` cho cả `results_main` và `results_stress`.
  - Giúp tham số `--rounds` thực hiện đúng cam kết CLI: "Số lượt đo lặp lại cho mỗi phương pháp".

### 2.2. Sinh tập dữ liệu đa ngữ thực sự & Tính kích thước byte động
- Cấu trúc tập mẫu đa ngữ:
  - **CJK / Hán Nôm**: `[U+4E00..U+6D40]` (8.000 ký tự, 3 bytes UTF-8 mỗi ký tự).
  - **Cyrillic**: `[U+0410..U+0604]` (500 ký tự, 2 bytes UTF-8 mỗi ký tự).
  - **Hy Lạp**: `[U+0391..U+0585]` (500 ký tự, 2 bytes UTF-8 mỗi ký tự).
  - **Ký hiệu toán học**: `[U+2200..U+25E8]` (1.000 ký tự, 3 bytes UTF-8 mỗi ký tự).
  - **PUA va chạm**: `U+E000` (1 ký tự, 3 bytes UTF-8).
- Tính toán kích thước byte thực tế:
  - `utf8_bytes = len(text.encode("utf-8"))`
  - Báo cáo định dạng: `{utf8_bytes:,} bytes (~{utf8_bytes / (1024 * 1024):.2f} MB)`
  - JSON lưu cả trường số nguyên `text_bytes` và chuỗi định dạng `text_size_human`.

### 2.3. Bổ sung Smoke Test Pytest (`tests/test_benchmark_pua_smoke.py`)
- Bài test tự động thực thi script bằng subprocess:
  ```python
  import subprocess
  import sys
  import json

  def test_benchmark_pua_memory_script_smoke():
      cmd = [sys.executable, "scripts/benchmark_pua_memory.py", "--rounds", "1", "--json"]
      res = subprocess.run(cmd, capture_output=True, text=True, check=True)
      data = json.loads(res.stdout)
      assert "environment" in data
      assert "results_main" in data
      assert len(data["results_main"]) == 3
      assert "results_stress" in data
      assert len(data["results_stress"]) == 2
  ```
- Không kiểm tra ngưỡng thời gian tuyệt đối (tránh flaky trên CI).

### 2.4. Tích hợp vào Workflow CI (`.github/workflows/ci.yml`)
- Thêm bước sau vào các job `test-core` và `test-python-314`:
  ```yaml
  - name: Run PUA Benchmark Smoke Test
    run: python scripts/benchmark_pua_memory.py --rounds 1 --json
  ```
- Bước này hoàn tất trong 1-2 giây, đảm bảo mọi commit đều xác thực script benchmark hoạt động tốt.

---

## 3. Quyết định Kỹ thuật

1. **Quyết định 1**: Áp dụng đồng nhất `rounds` cho kịch bản đối kháng thay vì thêm tùy chọn mới `--stress-rounds` để giữ CLI tối giản và dễ sử dụng theo nguyên tắc KISS.
2. **Quyết định 2**: Sinh dữ liệu đa ngữ kết hợp 4 hệ chữ Unicode thực sự và tính toán dung lượng bằng `len(text.encode("utf-8"))`.
3. **Quyết định 3**: Thêm cả smoke test cấp repository (`tests/test_benchmark_pua_smoke.py`) và step trong GitHub Actions CI để tạo lưới bảo vệ kép.
