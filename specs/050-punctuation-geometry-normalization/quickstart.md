# Quickstart: Hướng dẫn Kiểm chứng Chuẩn hóa Hình học Dấu câu

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Date**: 2026-10-20  
**Spec Reference**: [specs/050-punctuation-geometry-normalization/spec.md](spec.md)

---

## 1. Môi trường Yêu cầu

- Python 3.10+ (có `pytest`, `pillow`, `reportlab`)
- Node.js 18+ (có hỗ trợ `node --test`)
- PowerShell hoặc Bash

---

## 2. Kịch bản Kiểm chứng Nhanh (Validation Scenarios)

### Kịch bản 1: Kiểm chứng Kích thước và Tọa độ Dấu ngoặc Đơn
Kiểm tra dấu ngoặc `(`, `)` vươn cao hơn chữ số và vươn qua đường cơ sở.

```bash
pytest tests/test_punctuation_geometry.py -k "test_parentheses_height_and_anchors" -v
```
**Kết quả mong đợi**:
- Chiều cao dấu ngoặc đạt `1.45 * xh` (trong dải `[1.35 * xh, 1.55 * xh]`).
- Đỉnh `min_y <= -1.20 * xh`, đáy `max_y >= +0.15 * xh`.

---

### Kịch bản 2: Kiểm chứng Khoảng hở Chữ số 1 và Dấu đóng ngoặc `)`
Kiểm tra các biểu thức `P(X >= 1)`, `k!(e^\lambda - 1)`, `\log_{10}(\lfloor x \rfloor + 1)`.

```bash
pytest tests/test_punctuation_geometry.py -k "test_digit_one_closing_paren_clearance" -v
```
**Kết quả mong đợi**:
- Khoảng hở ngang giữa nét mực cực phải của chữ số `1` và nét vẽ của `)` $\ge 0.18 \times x_h$ (tối thiểu 1.4pt).
- Hai nét mực hoàn toàn không tiếp xúc hoặc giao cắt nhau.

---

### Kịch bản 3: Kiểm chứng Dấu phẩy và Dấu chấm Bám sát Đường cơ sở
Kiểm tra các chuỗi `0,`, `1,`, `k = 1, 2, 3, ...`.

```bash
pytest tests/test_punctuation_geometry.py -k "test_comma_and_dot_baseline_anchoring" -v
```
**Kết quả mong đợi**:
- Dấu phẩy có đỉnh ở $\approx -0.14 \times x_h$ và đuôi ở $\approx +0.24 \times x_h$ (không bay lơ lửng).
- Dấu chấm có đáy chạm đúng đường cơ sở $y = 0.0$ và chiều cao $\le 0.22 \times x_h$.

---

### Kịch bản 4: Kiểm chứng Dấu ba chấm `...` Không bị Báo Thiếu Mẫu
Kiểm tra kết xuất token `"..."` khi kho mẫu đã có mẫu dấu chấm `.`.

```bash
pytest tests/test_punctuation_geometry.py -k "test_ellipsis_not_reported_as_missing" -v
```
**Kết quả mong đợi**:
- Cả 3 dấu chấm được kết xuất đều đặn trên đường cơ sở.
- Danh sách ký tự thiếu `missing` rỗng (`[]`).

---

### Kịch bản 5: Kiểm chứng Tương thích Tuyệt đối Golden Master (9/9 Tests)
Bảo đảm toàn bộ các bản vẽ chuẩn không bị thay đổi dù chỉ một điểm ảnh.

```bash
pytest tests/test_golden_master_real_path.py -v
```
**Kết quả mong đợi**:
- 9/9 ca kiểm thử PASS với mã băm SHA-256 trùng khớp 100%.

---

### Kịch bản 6: Kiểm chứng Đóng gói Web và Unit Test JS
Xây dựng lại bản phân phối Web và chạy kiểm thử tự động.

```bash
python scripts/build_web.py
npm run test:unit
pytest tests/test_build_web.py -v
```
**Kết quả mong đợi**:
- `webapp/dist/pyodide/chuviettay.zip` được tạo mới và chứa toàn bộ mã nguồn cập nhật.
- Toàn bộ các bài test JS và test đóng gói PASS 100%.
