# Interface Contract: Hợp đồng Giao diện Kiểm chứng và Benchmark PUA

**Feature**: `065-pua-verification-reproducibility` | **Date**: 2026-10-28

---

## 1. Hợp đồng Giao diện Python (Code Contracts)

### 1.1. `MarkdownImporter._collect_used_pua_codepoints`

Phương thức lớp (classmethod) thu thập các điểm mã BMP PUA xuất hiện trong văn bản.

```python
@classmethod
def _collect_used_pua_codepoints(cls, text: str) -> set[int]:
    """Thu thập tập hợp các điểm mã PUA (U+E000..U+F8FF) xuất hiện trong văn bản.

    Cơ chế và độ phức tạp:
    - Quét văn bản ở tầng C bằng _PUA_RE.finditer(text), không cấp phát danh sách trung gian.
    - Bộ nhớ phụ khống chế nghiêm ngặt <= 6.400 phần tử (tương đương _FAKE_CLOSE_PUA_COUNT).
    - Thoát sớm ngay trong vòng lặp khi tập hợp used_cps đạt đủ 6.400 phần tử.

    Args:
        text (str): Chuỗi văn bản Markdown đầu vào.

    Returns:
        set[int]: Tập hợp chứa các điểm mã nguyên trong khoảng [0xE000, 0xF8FF] đã xuất hiện.
                  Nếu text rỗng hoặc không chứa PUA, trả về set() rỗng.
    """
```

**Các ràng buộc hợp đồng (Contract Guarantees)**:
1. **Kiểu trả về**: Luôn là một `set` chứa các số nguyên (`int`).
2. **Miền giá trị**: Mọi phần tử đều nằm trong đoạn `[0xE000, 0xF8FF]`.
3. **Kích thước tối đa**: `len(result) <= 6400`.
4. **Không ngoại lệ**: Hàm không ném ngoại lệ với bất kỳ chuỗi Unicode hợp lệ nào.

---

### 1.2. `MarkdownImporter._choose_fake_close_placeholder`

Phương thức lớp chọn ký tự giữ chỗ cho dấu đóng giả (giữ nguyên giao diện công khai hiện tại).

```python
@classmethod
def _choose_fake_close_placeholder(cls, text: str) -> str | None:
    """Chọn ký tự giữ chỗ cho dấu đóng giả từ vùng Private Use Area của BMP (U+E000..U+F8FF).

    Độ phức tạp và cơ chế:
    1. Fast-path: Nếu text rỗng hoặc first_pua not in text -> trả về U+E000 ngay lập tức.
       - Phép tìm kiếm chuỗi con 'not in' thực thi ở tầng C với thời gian O(N), bộ nhớ phụ O(1).
    2. Collision path: Khi U+E000 xuất hiện trong text:
       - Gọi cls._collect_used_pua_codepoints(text) để gom tập hợp PUA (bộ nhớ <= 6.400 phần tử).
       - Nếu số lượng điểm mã bằng 6.400 -> trả về None (cạn kiệt).
       - Duyệt dải mã U+E001..U+F8FF để tìm điểm mã chưa dùng đầu tiên; trả về None nếu cạn kiệt.

    Args:
        text (str): Chuỗi văn bản Markdown đầu vào.

    Returns:
        str | None: Ký tự giữ chỗ PUA chưa bị sử dụng, hoặc None nếu cạn kiệt toàn bộ 6.400 ký tự.
    """
```

---

## 2. Hợp đồng Giao diện Dòng lệnh (CLI Schema)

### `scripts/benchmark_pua_memory.py`

Kịch bản thực nghiệm benchmark độc lập đo đạc và tái lập các số liệu hiệu năng.

```text
Usage: python scripts/benchmark_pua_memory.py [OPTIONS]

Options:
  --rounds INTEGER     Số lượt đo lặp lại cho mỗi phương pháp (Mặc định: 5)
  --json               Xuất kết quả ở định dạng JSON thay vì bảng Markdown
  --help               Hiển thị hướng dẫn sử dụng và thoát
```

**Định dạng Đầu ra Chuẩn (Stdout Format)**:
```text
========================================================================================
PUA MEMORY & PERFORMANCE REPRODUCIBILITY BENCHMARK
========================================================================================
Environment:
  - Python:       3.14.4 (CPython, 64-bit)
  - Platform:     Windows-11-10.0.26100-SP0 (AMD64)
  - Processor:    Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
  - Timestamp:    2026-10-28 16:35:00 UTC+7

Dataset:
  - Text Length:       510,001 characters (~1.0 MB UTF-8)
  - Distinct Characters: 10,001 characters (Multilingual: Han/Nom, Cyrillic, Math)
  - PUA Target:        1 collision character (U+E000)

Results Summary:
| Method              | Avg Time (ms) | Peak Memory (KB) | Elements | Speedup vs Baseline |
| :------------------ | ------------: | ---------------: | -------: | ------------------: |
| 1. set(text)        |        703.18 |          1099.64 |        1 |               1.00x |
| 2. regex findall()  |          4.06 |             1.60 |        1 |             173.20x |
| 3. regex finditer() |          4.08 |             2.30 |        1 |             172.35x |

Adversarial Stress Test (100,000 PUA repeated chars):
| Method              | Avg Time (ms) | Peak Memory (KB) | Memory Reduction    |
| :------------------ | ------------: | ---------------: | ------------------: |
| 2. regex findall()  |        160.65 |          6642.68 | 1.0x (Baseline)     |
| 3. regex finditer() |        485.29 |             2.85 | 2331x less memory   |
========================================================================================
```

**Mã Thoát (Exit Codes)**:
- `0`: Thực thi thành công và hoàn tất đo lường.
- `1`: Tham số không hợp lệ hoặc lỗi không lường trước.
