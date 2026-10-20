# Quickstart & Verification Guide: Feature 049

Hướng dẫn kiểm thử và xác minh tính đúng đắn cho Feature 049.

## 1. Kiểm thử Unit Test JavaScript (Worker Error Isolation & Resilience)

Chạy lệnh kiểm thử đơn vị frontend tiêu chuẩn:
```bash
npm run test:unit
```
Xác nhận toàn bộ các test case trong `tests/js/worker_resilience.test.mjs` vượt qua 100%:
- `recoverWorker giải quyết dứt điểm promise cũ khi thế hệ thay đổi giữa chừng`
- `late onerror từ Worker thế hệ cũ bị bỏ qua không ảnh hưởng Worker mới`
- `late onmessageerror từ Worker thế hệ cũ bị bỏ qua không ảnh hưởng Worker mới`
- `onerror/onmessageerror từ Worker hiện hành kích hoạt fatal error và reject pending`
- `chu trình timeout sau READY terminate worker cũ và thu hồi listeners`

## 2. Kiểm thử Python Core (Seed Context Parity & Optical Clearance)

Chạy kiểm thử bố cục toán và đo độ rộng:
```bash
pytest tests/test_math_layout.py tests/test_math_layout_extended.py -v
```

Chạy kiểm thử quang học dấu câu và số thập phân:
```bash
pytest tests/test_punctuation_optical_spacing.py -v
```

## 3. Kiểm thử Golden Master Bất biến (Regression Guard)

Kiểm tra toàn bộ 9 ca kiểm thử Golden Master đường thật:
```bash
pytest tests/test_golden_master_real_path.py -v
```
Toàn bộ 9/9 tests **BẮT BUỘC** phải `PASSED` với mã băm SHA-256 khớp 100% bản gốc.

## 4. Kiểm tra Lint và Cú pháp Toàn diện

```bash
npm run lint:js
flake8 chuviettay tests
```
