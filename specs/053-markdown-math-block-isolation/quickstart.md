# Quickstart: Hướng Dẫn Kiểm Chứng Khối Toán Display Và Ngăn Đè Nét Cận Toán Tử

**Feature**: `053-markdown-math-block-isolation`  
**Date**: 2026-10-22  
**Status**: Ready for Execution  

Tài liệu này cung cấp các kịch bản chạy thực tế để chứng minh tính năng giải quyết triệt để lỗi phân tách khối toán và hiện tượng đè nét mực như đã thấy trong 3 ảnh chụp màn hình của người dùng.

---

## 1. Điều kiện tiên quyết (Prerequisites)

- Môi trường Python 3.10+ đã cài đặt `pytest`.
- Thư viện `markdown-it-py` và `mdit_py_plugins` có sẵn trong môi trường ảo.

---

## 2. Kịch bản xác thực 1: Kiểm thử nhận diện khối toán `MathBlock` trên dòng mới (Tái hiện & Sửa lỗi Ảnh 2)

### Lệnh chạy kiểm thử:
```powershell
pytest tests/test_importer_markdown.py -k "test_math_block"
```

### Kịch bản kiểm chứng tự động:
1. **Kiểm tra ca không có dòng trống**:
   Đầu vào:
   ```markdown
   a
   $$\sum_{j=1}^9 P(D = j) = 1$$
   b
   ```
   **Kết quả mong đợi**:
   - Tài liệu IR có 3 khối:
     1. `Paragraph(inlines=[Text("a")])`
     2. `MathBlock(latex="\\sum_{j=1}^9 P(D = j) = 1")`
     3. `Paragraph(inlines=[Text("b")])`
   - Khối công thức là `MathBlock`, không phải `MathInline` lồng trong đoạn văn `a`.

2. **Kiểm tra ca dính liền dấu hai chấm**:
   Đầu vào:
   ```markdown
   Ta có:$$\sum_{j=1}^9 P(D = j) = 1$$
   ```
   **Kết quả mong đợi**:
   - `blocks[0]`: `Paragraph(inlines=[Text("Ta có:")])`
   - `blocks[1]`: `MathBlock(latex="\\sum_{j=1}^9 P(D = j) = 1")`

---

## 3. Kịch bản xác thực 2: Kiểm thử khoảng hở an toàn cận bên của toán tử lớn (Ngăn đè nét)

### Lệnh chạy kiểm thử:
```powershell
pytest tests/test_math_layout.py -k "test_nary_side_limits"
```

### Kịch bản kiểm chứng:
1. Tạo một biểu thức toán nội dòng chứa toán tử $\sum$ có cả cận trên và cận dưới:
   ```latex
   \sum_{j=1}^9 P(D = j)
   ```
2. Đo đạc hình học với `MathLayoutEngine(display=False)`:
   - Đo biên quang học thực tế của chỉ số trên `9` (`sup_bot`).
   - Đo biên quang học thực tế của chỉ số dưới `j=1` (`sub_top`).
   - **Kết quả mong đợi**:
     $$\text{sub\_top} - \text{sup\_bot} \ge 3.5\text{ pt}$$
   - Không có điểm mực nào của chữ số `9` chạm vào hoặc đè lên chữ số `j=1`.

---

## 4. Kịch bản xác thực 3: Kiểm thử toàn bộ hệ thống & Golden Master

Chạy toàn bộ các bộ kiểm thử liên quan để đảm bảo không có hồi quy:

```powershell
# 1. Kiểm thử Markdown & Math Import
pytest tests/test_importer_markdown.py tests/test_markdown_math_import.py

# 2. Kiểm thử Math Layout
pytest tests/test_math_layout.py tests/test_math_layout_extended.py

# 3. Kiểm thử Golden Master bảo toàn nét vẽ
pytest tests/test_golden_master_real_path.py

# 4. Kiểm thử đóng gói Web Client
python scripts/build_web.py
pytest tests/test_build_web.py
```

---

## 5. Tham chiếu chi tiết
- [Mô hình dữ liệu và máy trạng thái](./data-model.md)
- [Hợp đồng chuẩn hóa Markdown](./contracts/markdown-math-block-contract.md)
- [Hợp đồng khoảng hở cận toán tử](./contracts/operator-limits-clearance-contract.md)
