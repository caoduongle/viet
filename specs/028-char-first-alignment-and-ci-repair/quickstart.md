# Quickstart Validation Guide

**Feature**: Đồng Bộ Mô Hình Char-First, Khắc Phục Dấu Thanh & Sửa Lỗi CI Toàn Diện  
**Branch**: `028-char-first-alignment-and-ci-repair`  
**Date**: 2026-10-07  

---

## 1. Prerequisites
- Python 3.12+ với các thư viện trong `requirements-dev.txt`.
- Node.js 20+ và Playwright (`npm ci` & `npx playwright install chromium`).
- Môi trường kiểm thử màn hình ảo (nếu chạy trên Linux/CI: `xvfb-run`).

---

## 2. Kiểm Thử Đơn Vị & Tích Hợp (Core Test Suite)

### Kịch bản 1: Kiểm thử kiểm tra khả năng viết char-first (`Bank.can`)
Xác nhận rằng kho chỉ có mẫu nguyên từ cũ mà không có mẫu chữ cái thành phần sẽ báo không viết được, và khi đủ chữ cái + dấu thanh thì viết được.

```bash
pytest tests/test_bank.py -k "test_can" -vv
```
**Kỳ vọng**:
- `Bank.can("ba") == True` khi đủ mẫu chữ 'b', 'a'.
- `Bank.can("bá") == False` khi thiếu dấu sắc.
- Từ cũ trong `words` không làm cho `can()` trả về `True` nếu thiếu chữ cái.

---

### Kịch bản 2: Kiểm thử đa nét cho dấu thanh & xuất file kiểm tra
Xác nhận rằng dấu thanh nhiều nét được lưu giữ nguyên vẹn và file `.xopp` xuất ra chứa đủ 5 dấu thanh.

```bash
pytest tests/test_controller.py -k "test_teach_mark_multi_stroke or test_export_check_includes_marks" -vv
```
**Kỳ vọng**:
- Lưu dấu thanh với 2 nét bút rời $\to$ nạp lại kho vẫn có đúng 2 nét.
- File `.xopp` kiểm tra kho chứa đủ các ô cho `"dấu huyền"`, `"dấu sắc"`, `"dấu hỏi"`, `"dấu ngã"`, `"dấu nặng"`.

---

### Kịch bản 3: Kiểm thử khoảng cách hình học chống dính nét (`segment_distance`)
Xác nhận tính năng đo khoảng cách giữa 2 đoạn nét phát hiện va chạm chính xác hơn phép đo điểm.

```bash
pytest tests/test_text_utils.py -k "test_segment_distance or test_stroke_clearance" -vv
```
**Kỳ vọng**:
- Đoạn thẳng cắt nhau hoặc gần nhau giữa các đỉnh được phát hiện khoảng cách $\approx 0$.
- Thời gian tính toán $< 0.1$ms cho mỗi cặp nét.

---

### Kịch bản 4: Kiểm thử GUI & Định dạng thống kê
Xác nhận Desktop GUI hiển thị thống kê theo số lượng ký tự và mẫu nét, không dùng `n_words` làm số đếm chính.

```bash
pytest tests/test_gui.py -vv
```
(Trên Linux chạy: `xvfb-run -a pytest tests/test_gui.py -vv`)

**Kỳ vọng**:
- 100% các bài kiểm thử GUI vượt qua thành công (0 failures).

---

## 3. Kiểm Thử Web Client & Playwright E2E

### Kịch bản 5: Đơn vị Javascript Web Client
Kiểm tra logic nạp hàng đợi phân biệt giữa nhập chữ và nạp danh mục:

```bash
npm run test:unit
```
**Kỳ vọng**:
- `addCatalogLabels(["dấu sắc", "dấu huyền"])` giữ nguyên 2 nhãn nghiệp vụ trong hàng đợi.
- `addCharactersFromText("mùa")` tách thành `'m'`, `'ù'`, `'a'` (hoặc các ký tự NFC).

---

### Kịch bản 6: Playwright E2E Tests
Chạy kiểm thử toàn diện trên trình duyệt:

```bash
npx playwright test tests/e2e/bank.spec.ts tests/e2e/teach.spec.ts tests/e2e/write.spec.ts
```
**Kỳ vọng**:
- `bank.spec.ts`: Tìm kiếm ký tự thành công, mở modal chi tiết, xuất `.xopp` kiểm tra.
- `teach.spec.ts`: Dạy ký tự thành công, kiểm tra từ chối lòng bàn tay, phím tắt.
- `write.spec.ts`: Kết xuất văn bản ghép chữ thành công.
- Toàn bộ kịch bản E2E PASS 100%.

---

## 4. Kiểm Thử Toàn Diện CI (Full Pipeline Run)

```bash
ruff check .
pytest -vv --timeout=30 -m "not benchmark"
npm run test:unit
npm run test:browser
npx playwright test --workers=2
```
**Kỳ vọng**:
- Lint: 0 errors.
- Pytest: 100% pass (xóa sổ hoàn toàn 14 lỗi cũ).
- Playwright: 100% pass (xóa sổ hoàn toàn 4 lỗi cũ).
