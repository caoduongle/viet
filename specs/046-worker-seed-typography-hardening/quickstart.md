# Quickstart & Verification Guide: Worker Resilience, Seed Integrity & Typography Hardening

**Feature**: `046-worker-seed-typography-hardening`  
**Date**: 2026-10-20

## 1. Automated Verification via Tests

### Chạy các bài kiểm tra Python hiện tại và kiểm tra hồi quy
```bash
pytest tests/test_writer.py tests/test_number_fraction_typography.py tests/test_render_pipeline_seed_stability.py tests/test_golden_master_real_path.py -q
```
*Kỳ vọng: 100% test hiện có pass.*

### Chạy bài kiểm tra chuyên biệt cho Feature 046
```bash
pytest tests/test_system_hardening_feature_046.py -v
```
*File test `test_system_hardening_feature_046.py` sẽ bao phủ các ca kiểm tra:*
1. **Kiểm tra cách ly Seed cho Heading vs Paragraph**:
   - Thêm một đoạn văn mới chứa từ trùng lặp với `Heading`; xác nhận nét vẽ và `occurrence` của `Heading` không đổi 100%.
2. **Kiểm tra chuyển tiếp Occurrence của MathBlock trong ô bảng**:
   - Chèn thêm nội dung vào ô bảng trước; xác nhận công thức toán trong ô kế tiếp bảo toàn biến thể nét vẽ.
3. **Kiểm tra định danh hình học của Chunk trong token dài**:
   - Token dài bị ngắt dòng có `sub_index` phân biệt trong định danh `render_id`.
4. **Kiểm tra mẫu chữ số cực đoan & Spacing dấu âm**:
   - Mẫu số tổng hợp cực nhỏ (`0.10 * xh`) và cực lớn (`4.0 * xh`) được co giãn hoặc fallback vector an toàn.
   - Khoảng cách sau dấu trừ ở đầu số trong `-25` và `-0,39` đạt `0.05 * xh .. 0.12 * xh`.
   - Độ rộng từ `measure_text_width()` khớp với `number()` trong sai số `<= 0.05 * xh`.

### Chạy bài kiểm tra JavaScript / Web Client (Node.js)
```bash
node --test tests/test_worker_resilience.mjs
```
*Bao phủ:*
- Mô phỏng thay đổi `workerGeneration` khi `onWorkerReady` đang chờ bất đồng bộ; xác nhận `recoverWorker()` không bị treo, giải phóng `isRecovering` và mở khóa nút "Thử lại".
- Mô phỏng 2 chu kỳ khởi tạo thất bại rồi thành công; xác nhận số listener trên các nút không bị nhân đôi.

---

## 2. End-to-End Build & Pyodide Golden Verification

```bash
python scripts/build_web.py
node scripts/test_golden_pyodide.mjs
```
*Kỳ vọng:*
- Đóng gói Static Web Client thành công và vượt qua kiểm tra Sanity Check.
- 100% 8 ca Golden Master trong Pyodide 314.0.7 đạt mã băm SHA-256 trùng khớp tuyệt đối.
