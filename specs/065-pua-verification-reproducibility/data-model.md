# Data Model: Mô hình Dữ liệu và Bất biến Kỹ thuật PUA

**Feature**: `065-pua-verification-reproducibility` | **Date**: 2026-10-28

---

## 1. Thực thể Dữ liệu (Key Entities)

### 1.1. Tập hợp Điểm Mã PUA (`used_cps: set[int]`)

Cấu trúc tập hợp số nguyên biểu diễn danh sách các điểm mã thuộc miền BMP Private Use Area (`U+E000`..`U+F8FF`) đã xuất hiện trong chuỗi văn bản đầu vào.

- **Kiểu dữ liệu**: `set[int]`
- **Dải giá trị hợp lệ**: Mọi phần tử $x \in \text{used\_cps}$ đều thỏa mãn:
  $$0\text{xE000} \le x \le 0\text{xF8FF} \quad (57.344 \le x \le 63.743)$$
- **Số lượng phần tử tối đa (Giới hạn cứng)**:
  $$|\text{used\_cps}| \le 6.400$$
- **Nguồn gốc sinh**: Được trích xuất trực tiếp qua phương thức `MarkdownImporter._collect_used_pua_codepoints(text)` bằng bộ lặp `_PUA_RE.finditer(text)`.
- **Đặc tính vòng đời**: Tồn tại tạm thời trong phạm vi thực thi của hàm chọn dấu giữ chỗ hoặc kiểm thử đơn vị, được bộ thu gom rác tự động giải phóng ngay sau khi kết thúc.

---

### 1.2. Bản ghi Báo cáo Hiệu năng Benchmark (`BenchmarkMetricReport`)

Cấu trúc lưu trữ kết quả thực nghiệm so sánh các phương án kỹ thuật thu thập PUA.

| Trường thông tin | Kiểu dữ liệu | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- | :--- |
| `method_name` | `str` | Tên phương án đo | `"regex_finditer"`, `"set_text"` |
| `text_length` | `int` | Độ dài chuỗi thử nghiệm (ký tự) | `510001` |
| `distinct_chars`| `int` | Số lượng ký tự phân biệt trong chuỗi | `10001` |
| `pua_chars_found`| `int` | Số điểm mã PUA tìm thấy | `1` |
| `execution_time_ms`| `float` | Thời gian chạy trung bình (mili-giây) | `4.08` |
| `peak_memory_kb`| `float` | Mức tăng bộ nhớ đỉnh (Kilobytes) | `2.30` |
| `speedup_ratio` | `float` | Tỷ lệ tăng tốc so với baseline `set(text)`| `172.3` |

---

## 2. Bất biến Kỹ thuật (Technical Invariants)

1. **Bất biến Khống chế Bộ nhớ (Memory Boundedness)**:
   - Với mọi chuỗi văn bản $T$ có độ dài bất kỳ $N \in [0, \infty)$ và bảng chữ cái phân biệt bất kỳ:
     $$|\text{MarkdownImporter.\_collect\_used\_pua\_codepoints}(T)| \le 6.400$$
   - Tuyệt đối không có bất kỳ điểm mã nào ngoài dải $[0\text{xE000}, 0\text{xF8FF}]$ lọt vào tập hợp `used_cps`.

2. **Bất biến Định lượng Phân bổ (Allocation Boundary)**:
   - Khi đo lường bằng `tracemalloc`, mức tăng bộ nhớ đỉnh phân bổ (peak traced memory) trong hàm `_collect_used_pua_codepoints` trên chuỗi có 10.000 ký tự phân biệt kèm $\le 10$ ký tự PUA không được vượt quá **$50\text{KB}$**.

3. **Bất biến Thoát Sớm (Early Exit Invariant)**:
   - Khi văn bản chứa từ 6.400 điểm mã PUA phân biệt trở lên, bộ lặp ngắt ngay lập tức khi kích thước tập hợp chạm ngưỡng 6.400, không duyệt tiếp phần còn lại của chuỗi văn bản.

4. **Bất biến Tái lập Độc lập (CLI Reproducibility Invariant)**:
   - Script `scripts/benchmark_pua_memory.py` khi thực thi với Python $\ge 3.10$ trả về mã thoát $0$ (`exit code 0`), tự động phát hiện siêu dữ liệu môi trường và in ra bảng tổng kết định lượng có thể kiểm chứng.
