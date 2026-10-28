# Research & Technical Decisions: Khống chế bộ nhớ tập hợp PUA và chuẩn hóa thống kê benchmark

**Branch**: `064-pua-memory-and-benchmark` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

---

## R1: Thuật toán trích xuất ký tự PUA có chặn cứng bộ nhớ phụ (Bounded PUA Collection)

### Vấn đề ở commit a9da0c2
Ở commit `a9da0c2`, nhánh va chạm (khi văn bản chứa `U+E000`) được viết:
```python
used_cps = {ord(c) for c in set(text) if _FAKE_CLOSE_PUA_START <= ord(c) <= _FAKE_CLOSE_PUA_END}
```
- Thao tác `set(text)` khởi tạo một tập hợp chứa **toàn bộ các ký tự phân biệt** xuất hiện trong văn bản trước khi lọc.
- Nếu tài liệu văn bản lớn (hàng triệu ký tự) chứa bảng chữ cái đa dạng (chữ Hán, chữ Nôm, chữ Ả Rập, Cyrillic, biểu tượng toán học, emoji, font kỹ thuật) với hàng chục nghìn ký tự phân biệt, `set(text)` sẽ phân bổ một cấu trúc bảng băm lớn trong bộ nhớ phụ, tỉ lệ thuận với số ký tự phân biệt của tài liệu.
- Điều này vi phạm nguyên tắc thiết kế: bộ nhớ phụ chỉ được phép tỉ lệ thuận với số lượng ký tự PUA thực tế và bị chặn trên bởi $6.400$ phần tử (`_FAKE_CLOSE_PUA_COUNT`).

### Thực nghiệm đo đạc (Micro-benchmark trên chuỗi 1MB chứa 10.000 ký tự Unicode phân biệt)
| Phương án | Thời gian quét | Ký tự ngoài PUA bị nạp vào bộ nhớ | Kích thước cấu trúc tạm | Đánh giá |
| :--- | :---: | :---: | :---: | :--- |
| **A. `set(text)` ban đầu** | $0.1155\text{s}$ | 10.000 ký tự | Tập hợp băm 10.000 phần tử | Tiêu tốn bộ nhớ theo bảng chữ cái tài liệu |
| **B. Generator `{ord(c) for c in text if ...}`** | $0.1260\text{s}$ | 0 ký tự | Bị chặn bởi PUA | Chậm do vòng lặp bytecode Python |
| **C. `re.finditer`** | $0.0050\text{s}$ | 0 ký tự | Bị chặn bởi PUA | Rất nhanh, tạo Match wrapper |
| **D. `re.findall` pre-compiled** | **$0.0053\text{s}$** | **0 ký tự** | **Chỉ chứa các ký tự PUA khớp** | **Nhanh nhất và tiết kiệm bộ nhớ nhất** |

### Quyết định kỹ thuật
Pre-compile biểu thức chính quy ở cấp module:
```python
_PUA_RE = re.compile(r"[\uE000-\uF8FF]")
```
Trong `_choose_fake_close_placeholder`:
```python
used_cps: set[int] = set()
for m in _PUA_RE.finditer(text):
    used_cps.add(ord(m.group(0)))
    if len(used_cps) == _FAKE_CLOSE_PUA_COUNT:
        return None
```
**Lợi ích vượt trội của `finditer` so với `findall`**:
1. **Khống chế tuyệt đối bộ nhớ heap**: Không bao giờ tạo danh sách trung gian (`list`). Ngay cả khi văn bản bất lợi chứa hàng triệu ký tự `\ue000` lặp đi lặp lại, `finditer` chỉ cập nhật vào `used_cps` (chỉ có 1 phần tử), bộ nhớ luôn $< 1\text{KB}$.
2. **Thoát sớm ngay trong quá trình quét**: Nếu văn bản chứa đủ 6.400 ký tự PUA phân biệt, vòng lặp dừng ngay lập tức khi `len(used_cps) == 6400` mà không cần duyệt nốt phần còn lại của tài liệu.
3. **Kích thước tập hợp bị chặn trên tuyệt đối**: Dung lượng tối đa của `used_cps` luôn $\le 6.400$ phần tử số nguyên (~200KB), hoàn toàn độc lập với kích thước văn bản và tính đa dạng của bảng chữ cái.
4. **Tốc độ thực thi vượt trội**: Quét ở tầng C bằng bộ máy regex của CPython, nhanh gấp **gần 20 đến 25 lần** so với `set(text)` hoặc generator khi xử lý tài liệu đa ngữ.

---

## R2: Chuẩn hóa tuyên bố độ phức tạp thuật toán (Complexity Accuracy)

### Phân tích hiện trạng
Tài liệu trước đây tuyên bố nhánh kiểm tra nhanh:
`if first_pua not in text: return first_pua`
là $O(1)$.
Điều này không chính xác về mặt lý thuyết thuật toán:
- Khi `first_pua` không có trong văn bản, Python phải duyệt qua văn bản (thuật toán Two-Way/Boyer-Moore trong C) để xác nhận chuỗi con không tồn tại. Thời gian xấu nhất là $O(N)$ với $N = \operatorname{len}(text)$.
- Điểm vượt trội của nhánh này là **độ phức tạp không gian bộ nhớ phụ $O(1)$** (không cấp phát tập hợp phụ, không tạo danh sách trung gian).
- Trong nhánh va chạm: thực hiện 2 lượt quét chuỗi $O(N)$ (lượt 1: kiểm tra sự hiện diện của `first_pua`, lượt 2: `_PUA_RE.findall(text)` trích xuất PUA).
- Sau khi có `used_cps`, vòng lặp tìm điểm mã trống duyệt tối đa 6.400 bước với tra cứu tập hợp $O(1)$.

### Quyết định kỹ thuật
Cập nhật docstring và toàn bộ tài liệu đặc tả, kế hoạch, mô hình dữ liệu để:
1. Ghi nhận chính xác:
   - Nhánh kiểm tra nhanh: Thời gian $O(N)$ duyệt chuỗi ở tầng C, bộ nhớ phụ $O(1)$.
   - Nhánh va chạm: Thời gian $2 \times O(N) = O(N)$ quét chuỗi ở tầng C, bộ nhớ phụ $O(\min(N, 6400))$.
2. Bỏ toàn bộ các tuyên bố gọi phép tìm chuỗi con là "thời gian $O(1)$".

---

## R3: Phương pháp đo lường thống kê không thiên vị cho Benchmark đối kháng

### Vấn đề ở commit a9da0c2
Trong `test_adversarial_complexity_multi_length_backticks_and_long_lines`, khi tỷ lệ $T(4N)/T(N) > 6.0$, mã kiểm thử thực hiện đo lại và lấy `min(ratio, ratio_retry)`.
Cách làm này:
- Tạo ra xu hướng thiên vị (selection bias) về phía kết quả thấp hơn.
- Có rủi ro che giấu hiện tượng suy giảm hiệu năng thực sự (performance regression) nếu lần đo thứ hai tình cờ đạt ngưỡng do biến động CPU ngẫu nhiên.

### Quyết định kỹ thuật: Phương pháp thống kê trung vị (Median-based Benchmark)
Chuẩn mực đo lường hiệu năng đáng tin cậy:
1. Chạy warmup 1 lần.
2. Thực hiện $M = 5$ lượt đo lặp lại độc lập.
3. Trong mỗi lượt $k \in \{1..5\}$:
   - Dọn dẹp bộ nhớ: `gc.collect()`.
   - Đo thời gian $T(N)$ qua 3 lần chạy trung bình.
   - Dọn dẹp bộ nhớ: `gc.collect()`.
   - Đo thời gian $T(4N)$ qua 3 lần chạy trung bình.
   - Tính tỷ lệ $R_k = T(4N)_k / T(N)_k$.
4. Lấy giá trị trung vị:
   $$\operatorname{ratio}_{\text{med}} = \operatorname{median}(\{R_1, R_2, R_3, R_4, R_5\})$$
5. Khẳng định:
   $$\operatorname{ratio}_{\text{med}} \le 6.0$$
6. Kèm thông điệp báo cáo chứa toàn bộ danh sách 5 kết quả đo để minh bạch và dễ dàng chẩn đoán khi kiểm thử không đạt trên CI.

### Kết quả thực nghiệm
Đo đạc 5 lượt thực tế trên máy tính:
- Các tỷ lệ $R_k$: `[4.45, 4.21, 3.15, 4.59, 3.53]`
- Tỷ lệ trung vị: `4.21x` (gần như trùng khớp với mức lý tưởng $4.0x$ của thuật toán tuyến tính).
- Lọc bỏ hoàn toàn các ngoại lai đột biến mà không thiên vị hay che giấu lỗi.
