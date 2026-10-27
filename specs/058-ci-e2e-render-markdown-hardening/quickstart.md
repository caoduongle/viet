# Quickstart & Validation Guide: Feature 058

**Feature**: `058-ci-e2e-render-markdown-hardening`  
**Date**: 2026-10-27

---

## Prerequisites

- Python >= 3.10 (cùng `pytest`, `ruff`, `markdown-it-py`, `mdit-py-plugins`)
- Node.js >= 20.x & Playwright Chromium (`npx playwright install chromium`)

---

## Validation Scenarios

### 1. Kiểm tra Cấu hình Phiên bản Python & Render (`US2`)

```bash
pytest tests/test_version_metadata.py -vv
```
- **Expected**: Tất cả bài kiểm thử trong `test_version_metadata.py` vượt qua 100%, xác nhận `.python-version` là `3.13` và `render.yaml` không chứa biến môi trường `PYTHON_VERSION` rút gọn không hợp lệ.

### 2. Kiểm tra An toàn Build Web (`US1`)

```bash
pytest tests/test_build_web.py -vv
python scripts/build_web.py
```
- **Expected**: 9/9 bài kiểm thử trong `test_build_web.py` vượt qua (rào chắn từ chối xóa thư mục ngoài không rỗng khi thiếu `--force-clean` vẫn giữ nguyên) và build dist mặc định thành công.

### 3. Kiểm tra Playwright E2E Service Worker Update (`US1`)

```bash
npx playwright test tests/e2e/sw-update.spec.ts
```
- **Expected**: Bài kiểm thử `sw-update.spec.ts` chạy qua cả 2 lần build trên `tmpDist` (lần 1 mặc định, lần 2 có `--force-clean`) và PASS 100%.

### 4. Kiểm tra Khối Mã Thụt Lề, Bảng GFM & Độ Phức Tạp Tuyến Tính (`US3`, `US4`, `US5`)

```bash
pytest tests/test_markdown_math_block_isolation.py tests/test_importer_markdown.py tests/test_markdown_math_import.py -vv
```
- **Expected**: Toàn bộ bài kiểm thử đơn vị và tích hợp cho Markdown importer (bao gồm cả các bài benchmark độ phức tạp với đầu vào bất lợi khi chạy trực tiếp tệp test) đều PASS 100%.

### 5. Kiểm tra Toàn diện Linter, Golden Master & Regression Suite

```bash
ruff check .
npm run test:unit
node scripts/test_golden_pyodide.mjs
pytest -m "not benchmark"
```
- **Expected**:
  - `ruff check .`: `All checks passed!`
  - `npm run test:unit`: 65/65 passed
  - `node scripts/test_golden_pyodide.mjs`: 8/8 Golden Master trùng khớp SHA-256 100%
  - `pytest -m "not benchmark"`: 100% passed, 0 failed
