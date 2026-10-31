# Data Model: Mô hình Dữ liệu và Bất biến Script Benchmark

**Feature**: `066-pua-benchmark-hardening` | **Date**: 2026-10-28

---

## 1. Thực thể Dữ liệu (Key Entities)

### 1.1. Tập mẫu Đa ngữ Thử nghiệm (`MultilingualCorpus`)

- **Thành phần cấu tạo**:
  - `cjk_chars`: 8.000 ký tự Hán/Nôm (`U+4E00..U+6D40`)
  - `cyrillic_chars`: 500 ký tự Slav (`U+0410..U+0604`)
  - `greek_chars`: 500 ký tự Hy Lạp (`U+0391..U+0585`)
  - `math_chars`: 1.000 ký hiệu toán học (`U+2200..U+25E8`)
  - `pua_char`: 1 ký tự va chạm PUA (`U+E000`)
- **Thuộc tính định lượng**:
  - `text_length`: Số lượng ký tự Unicode (mặc định: `510.001` ký tự).
  - `distinct_characters`: Số lượng ký tự phân biệt trong mẫu ($\ge 9.500$ ký tự).
  - `text_bytes`: Kích thước byte UTF-8 thực tế, tính bằng `len(text.encode("utf-8"))` (~1.48 MB).

---

### 1.2. Cấu trúc Báo cáo JSON (`BenchmarkJsonReportSchema`)

```json
{
  "environment": {
    "python_version": "str",
    "os_platform": "str",
    "processor": "str",
    "timestamp": "str"
  },
  "dataset_main": {
    "text_length": "int",
    "text_bytes": "int",
    "text_size_human": "str",
    "distinct_characters": "int",
    "character_families": "list[str]",
    "pua_characters_in_text": "int",
    "rounds": "int"
  },
  "results_main": [
    {
      "name": "str",
      "avg_time_ms": "float",
      "peak_memory_kb": "float",
      "elements": "int",
      "speedup_vs_baseline": "str"
    }
  ],
  "dataset_stress": {
    "text_length": "int",
    "description": "str",
    "rounds": "int",
    "memory_reduction_ratio": "str"
  },
  "results_stress": [
    {
      "name": "str",
      "avg_time_ms": "float",
      "peak_memory_kb": "float",
      "elements": "int"
    }
  ]
}
```

---

## 2. Bất biến Kỹ thuật (Technical Invariants)

1. **Bất biến Nhất quán Vòng lặp**:
   - Khi chạy với tham số `--rounds N`, số vòng lặp được thực thi cho các phương pháp trong `results_main` và `results_stress` đều bằng $\max(N, 1)$.
2. **Bất biến Tính đúng Dung lượng**:
   - Giá trị `dataset_main.text_bytes` phải bằng chính xác `len(text.encode("utf-8"))`.
3. **Bất biến Kháng Lỗi Smoke Test**:
   - Khi chạy với `--rounds 1 --json`, script luôn trả về mã thoát $0$ và chuỗi JSON hợp lệ chứa đầy đủ 5 trường cấp 1 (`environment`, `dataset_main`, `results_main`, `dataset_stress`, `results_stress`).
