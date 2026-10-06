# Quickstart & Verification Guide: 025 — Sửa lỗi CI Kiểm Thử Tự Động

Tài liệu này hướng dẫn cách chạy và nghiệm thu các bài test CI sau khi áp dụng bản vá.

## 1. Nghiệm thu Kiểm thử Playwright E2E với Đa luồng (2 Workers)

### Lệnh thực thi:
```bash
npx playwright test --workers=2
```

### Kỳ vọng nghiệm thu:
1. Tổng số 14 tests đều chạy qua và đạt `PASSED` (14 passed).
2. Test `tests/e2e/sw-update.spec.ts` khởi tạo `tmpDist` độc lập và server trên port `8101`.
3. Không có lỗi `/bin/sh: 1: py: not found` xuất hiện dù chạy trên Linux hay Windows.
4. Các worker chạy song song (ví dụ `grid-import.spec.ts` và `sw-update.spec.ts`) không gây lỗi ngắt kết nối hoặc reload service worker ngoài ý muốn của nhau.
5. Sau khi kết thúc, file `webapp/js/app.js` không bị bẩn (không còn chuỗi `/* SW_UPDATE_TEST_... */`).

---

## 2. Nghiệm thu Kiểm thử GUI Tkinter

### Lệnh thực thi:
Trên Linux (hoặc môi trường CI):
```bash
xvfb-run -a python -m pytest -vv -k "test_gui.py"
```
Trên Windows (nếu có môi trường Python với Tkinter):
```bash
pytest -vv tests/test_gui.py
```

### Kỳ vọng nghiệm thu:
1. Bài test `test_nap_bo_ky_tu_co_ban` vượt qua thành công:
   - Mở dialog "Chọn bộ ký tự".
   - Kích hoạt nút "Nạp ký tự".
   - `t.queue` được nạp đầy đủ các ký tự còn thiếu thuộc nhóm `co_ban` mà không bị trùng với các ký tự đã có.
2. Bài test `test_huy_bo_ky_tu_khong_them_gi` vượt qua thành công:
   - Bấm nút "Huỷ" và hàng đợi `t.queue` được bảo toàn nguyên vẹn.
3. Không còn bất kỳ lỗi `AssertionError: assert (1 == 6)` nào xuất hiện.

---

## 3. Nghiệm thu Linter & Kiểm tra Kiến trúc Toàn diện

```bash
ruff check .
pytest -q tests/test_architecture.py
```
Kỳ vọng: 0 lint errors, 17/17 kiến trúc tests passed.
