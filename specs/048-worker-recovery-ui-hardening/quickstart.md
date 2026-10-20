# Quickstart & Verification Guide: 048-worker-recovery-ui-hardening

Tài liệu hướng dẫn xác minh và kiểm thử toàn diện tính năng củng cố phục hồi Worker, vòng đời giao diện và đo đạc chữ số.

## Điều kiện tiên quyết (Prerequisites)
- Node.js 20+ cài đặt sẵn trên hệ thống.
- Python 3.10+ kèm môi trường ảo đã cài `pytest` và các phụ thuộc dự án (`pip install -e .`).

---

## 1. Xác minh kiểm thử đơn vị JavaScript trong CI (User Story 1, 2, 3, 4)

### Lệnh thực thi
```bash
npm run test:unit
```

### Kết quả mong đợi
- Toàn bộ các bài kiểm thử trong `tests/js/*.test.mjs` được thực thi tự động.
- Không có bất kỳ tệp kiểm thử mồ côi nào nằm ở `tests/test_worker_resilience.mjs`.
- Bộ kiểm thử `tests/js/worker_resilience.test.mjs` bao gồm:
  - Kiểm thử phục hồi phiên thay thế (US1): phiên A kết thúc không làm `isRecovering` chuyển về `false`.
  - Kiểm thử chấm dứt vật lý Worker khi quá hạn sau READY (US4).
  - Kiểm thử tính lũy đẳng của `initBankTab`, `initWriteTab`, `TeachController` và `ResizeObserver` (US3).
- **Trạng thái**: `pass 15+` (hoặc toàn bộ pass), `fail 0`.

---

## 2. Xác minh kiểm thử hình học và đo độ rộng chữ số Python (User Story 5)

### Lệnh thực thi
```bash
pytest tests/test_system_hardening_feature_046.py tests/test_number_fraction_typography.py -v
```

### Kết quả mong đợi
- Kiểm thử `test_measure_text_width_number_sync`: Sai lệch giữa `measure_text_width` và `number` $\le 0.05 \times x_h$ trên mọi trường hợp số âm, số thập phân và số nguyên lớn.
- Kiểm thử `test_decimal_number_spacing_harmony`: Khoảng cách quang học thực tế và tính hài hòa dấu phẩy đạt chuẩn.
- Kiểm thử mẫu chữ số suy biến (`sample_h <= 1e-3`): Không gây ra lỗi chia cho 0, trả về độ rộng hợp lệ.
- **Trạng thái**: 100% passed.

---

## 3. Xác minh toàn bộ hệ thống (Full Regression Suite)

### Lệnh thực thi
```bash
# Toàn bộ test suite Python
pytest

# Toàn bộ test suite Web Client & Browser Bridge
npm test
```

### Kết quả mong đợi
- 1265+ tests Python passed (0 failed).
- Toàn bộ JavaScript tests, Browser Bridge tests và Pyodide Golden Master tests passed.
