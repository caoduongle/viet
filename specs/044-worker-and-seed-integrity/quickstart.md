# Quickstart & Verification Guide: Worker and Seed Integrity Hardening

**Feature**: `specs/044-worker-and-seed-integrity`
**Date**: 2026-10-18
**Status**: Completed

Hướng dẫn này cung cấp các kịch bản kiểm thử tự động và thủ công để xác nhận 5 vấn đề kỹ thuật đã được giải quyết dứt điểm.

---

## 1. Yêu cầu tiên quyết (Prerequisites)
- Python 3.12+ với môi trường ảo đã kích hoạt.
- Node.js 20+ và NPM.
- Trình duyệt Chromium đã cài đặt cho Playwright.

---

## 2. Kịch bản kiểm thử tự động (Automated Verification)

### Kịch bản 1: Kiểm thử cô lập không gian tên RNG theo SeedContext
Kiểm tra cùng từ/ký hiệu giữa `text` và `cell` sinh ra khóa khác nhau và biến thể khác nhau:
```powershell
pytest tests/test_stable_variants.py -k "test_namespace_isolation_text_cell_sym" -v
```
**Kỳ vọng**:
- `ScopedRNG(seed, "text", "báo", 0, "variant", tag, 0).seed != ScopedRNG(seed, "cell", "báo", 0, "variant", tag, 0).seed`.
- Biến thể và jitter của từ trong ô bảng hoàn toàn độc lập với từ trong văn bản thông thường.

### Kịch bản 2: Kiểm thử tính bất biến khi chèn mục danh sách lồng nhau (`ListBlock`)
Kiểm tra chèn mục mới vào đầu danh sách bảo toàn nét chữ cũ (`tolerance <= 0.02 pt`):
```powershell
pytest tests/test_stable_variants.py -k "test_list_insertion_invariance" -v
```
**Kỳ vọng**:
- Các nét vẽ của các mục danh sách ban đầu trùng khớp hình học với độ lệch <= 0.02 pt.

### Kịch bản 3: Kiểm thử đồng bộ occurrence khi token dài bị ngắt dòng
Kiểm tra từ dài bị chia thành nhiều chunk không làm lệch bộ đếm của từ kế tiếp:
```powershell
pytest tests/test_stable_variants.py -k "test_chunked_token_occurrence_synchronization" -v
```
**Kỳ vọng**:
- Từ kế tiếp sau từ bị ngắt dòng vẫn nhận đúng occurrence theo thứ tự từ trong câu.

### Kịch bản 4: Kiểm thử từ chối kiểu dữ liệu không hợp lệ trong `encode_canonical_key`
Kiểm tra hàm chủ động ném `TypeError` đối với `dict`, `set`, `object`:
```powershell
pytest tests/test_rng.py -k "test_canonical_key_encoding_unsupported_types" -v
```
**Kỳ vọng**:
- `pytest.raises(TypeError)` vượt qua với các kiểu dữ liệu không nằm trong hợp đồng.

### Kịch bản 5: Kiểm thử khôi phục Worker khi nạp kho kéo dài (Tách biệt Timeout READY)
Kiểm tra Worker gửi READY nhưng bước nạp kho mất nhiều thời gian:
```powershell
npm run test:unit -- --test-name-pattern="recoverWorker"
```
**Kỳ vọng**:
- `readyTimer` dừng ngay khi nhận READY.
- Worker không bị terminate sai khi quá trình nạp kho chạy bình thường.
- Lỗi giữa chừng trong khởi tạo DOM rollback `isDomListenersAttached` về `false`.

---

## 3. Chạy toàn bộ bộ kiểm chuẩn hệ thống

```powershell
# 1. Lint & Bytecode
ruff check .
python -m compileall -q .

# 2. Toàn bộ Unit & Integration tests Python
pytest -q -m "not benchmark"

# 3. Golden Master Pyodide 314.0.7
python scripts/build_web.py
node scripts/test_golden_pyodide.mjs

# 4. JS Unit & Browser tests
npm run test:unit
npm run test:browser

# 5. Playwright E2E
npx playwright test
```
