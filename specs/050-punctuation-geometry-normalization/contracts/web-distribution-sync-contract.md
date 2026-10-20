# Contract: Đồng bộ Bản Đóng gói Ứng dụng Web (Web Distribution Sync Contract)

**Feature Branch**: `050-punctuation-geometry-normalization`  
**Date**: 2026-10-20  
**Status**: Ratified  
**Spec Reference**: [specs/050-punctuation-geometry-normalization/spec.md](spec.md)

---

## 1. Mục đích & Phạm vi Hợp đồng
Hợp đồng này quy định quy trình và tiêu chí nghiệm thu cho việc đồng bộ mã nguồn Python lõi sang gói phân phối tĩnh WebAssembly/Pyodide chạy trong trình duyệt.

---

## 2. Các Ràng buộc Phân phối

### 2.1 Tệp Phân phối Mục tiêu
Lệnh đóng gói `python scripts/build_web.py` phải tạo ra hoặc cập nhật:
1. `webapp/dist/pyodide/chuviettay.zip`:
   - Phải chứa mã nguồn mới nhất của gói `chuviettay/` (bao gồm `model/writer.py`, `layout/math_layout.py`, `layout/engine.py`).
   - Kích thước hợp lệ (> 100KB), không bị lỗi nén hoặc thiếu tệp module.
2. `webapp/dist/sw.js`:
   - Service worker cache version hoặc cache manifest phải được cập nhật tương ứng với các tệp dist mới.

### 2.2 Tiêu chí Xác nhận Hợp đồng (Contract Verification)
- Chạy bài kiểm tra tự động `pytest tests/test_build_web.py`:
  - Kiểm tra tệp zip tồn tại và đọc được danh sách module bên trong.
  - Kiểm tra mã nguồn bên trong `chuviettay.zip` chứa các hàm và logic mới nhất vừa cập nhật.
- Bộ kiểm thử unit test Web Worker trên Node.js (`npm run test:unit`) chạy thành công 100%.
