# Interface Contract: Hợp đồng Giao diện Benchmark CLI và CI Workflow

**Feature**: `066-pua-benchmark-hardening` | **Date**: 2026-10-28

---

## 1. Hợp đồng Giao diện Dòng lệnh (CLI Contract)

### `scripts/benchmark_pua_memory.py`

```text
Usage: python scripts/benchmark_pua_memory.py [OPTIONS]

Options:
  --rounds INTEGER     Số lượt đo lặp lại cho mỗi phương pháp (áp dụng cho cả kịch bản chính và đối kháng, mặc định: 5)
  --json               Xuất kết quả ở định dạng JSON thay vì bảng Markdown
  --help               Hiển thị hướng dẫn sử dụng và thoát
```

**Các ràng buộc hợp đồng (Contract Guarantees)**:
1. **Tham số `--rounds`**:
   - Nếu $N \le 0$, tự động ép về $1$.
   - Số vòng lặp được truyền đồng nhất cho tất cả các kịch bản đo lường.
2. **Định dạng JSON (`--json`)**:
   - Đầu ra stdout là một chuỗi JSON hợp lệ 100%, không bị lẫn text debug hoặc cảnh báo không mong muốn.
   - Trả về mã thoát $0$ khi thành công.

---

## 2. Hợp đồng Kiểm thử Tự động (Smoke Test Contract)

### `tests/test_benchmark_pua_smoke.py`

Kiểm thử đơn vị độc lập chạy trong test suite pytest:

```python
def test_benchmark_pua_script_smoke_execution():
    """Xác nhận scripts/benchmark_pua_memory.py chạy thành công với --rounds 1 --json:
    - Mã thoát = 0
    - Đầu ra stdout là JSON hợp lệ
    - Khóa environment chứa python_version, os_platform, processor, timestamp
    - Khóa dataset_main chứa text_bytes và character_families
    - Khóa results_main chứa đúng 3 phương án đo
    - Khóa results_stress chứa đúng 2 phương án đo
    """
```

---

## 3. Hợp đồng Continuous Integration (CI Workflow Contract)

### `.github/workflows/ci.yml`

Bổ sung bước thực thi benchmark smoke test trong các job kiểm thử:

```yaml
- name: Run PUA Benchmark Smoke Test
  run: python scripts/benchmark_pua_memory.py --rounds 1 --json
```

**Ràng buộc**:
- Phải được thực thi sau bước cài đặt thư viện và trước khi kết thúc job.
- Thời gian thực thi không được vượt quá 10 giây.
