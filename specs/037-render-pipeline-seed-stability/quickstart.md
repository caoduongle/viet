# Quickstart: Kiểm chứng và Chạy Thử nghiệm Ổn định Dòng kết xuất

**Feature**: `037-render-pipeline-seed-stability`  
**Date**: 2026-10-13  
**Status**: Ready for Validation  

---

## 1. Môi trường và Điều kiện Tiên quyết

- Python >= 3.10 (môi trường hiện tại: Python 3.10+)
- Node.js >= 18 (phục vụ kiểm thử Web Client)
- Thư viện kiểm thử: `pytest`, `pytest-timeout`

Cài đặt các gói dev nếu chưa có:
```bash
pip install -r requirements-dev.txt
```

---

## 2. Kịch bản Kiểm chứng Tự động (Automated Verification)

### Kịch bản 1: Kiểm chứng Bất biến khi Chèn từ phía trước qua Toàn bộ Pipeline (Prepend Invariance with Jitter)

Chứng minh rằng chèn từ vào đầu câu qua hàm điều khiển cấp cao (`write_text` / `write_document`) với độ run tay bật (`jitter=1.0`) không làm thay đổi tọa độ nét vẽ tương đối của các từ cũ.

```bash
pytest tests/test_stable_variants.py -k "test_render_pipeline_prepend_invariance_with_jitter" -v
```
**Kỳ vọng**:
- Lượt 1: Render văn bản `Hôm nay trời rất đẹp` -> Tách nét XML của từng từ.
- Lượt 2: Render văn bản `Chào buổi sáng! Hôm nay trời rất đẹp` -> Tách nét XML của từng từ cũ.
- Tọa độ nét tương đối, góc xoay, độ lệch Y và độ dày nét của `Hôm`, `nay`, `trời`, `rất`, `đẹp` trùng khớp 100% (delta = 0).

---

### Kịch bản 2: Kiểm chứng Tái lập Bit-exact trên cả Hai Engine (Semantic & Fidelity)

Chứng minh rằng khi chạy với `seed=None`, kết xuất thu được `seed_used`, và chạy lại đúng với `seed_used` tạo ra tệp `.xopp` giống nhau từng byte trên cả `DocumentLayoutEngine` và `FidelityLayoutEngine`.

```bash
pytest tests/test_seed_lifecycle.py -k "test_fidelity_seed_lifecycle_reproducibility" -v
pytest tests/test_seed_lifecycle.py -k "test_effective_seed_and_bit_exact_reproducibility" -v
```
**Kỳ vọng**:
- Cả hai bài test vượt qua, mã băm SHA-256 của tệp XML đầu ra trùng khớp 100%.

---

### Kịch bản 3: Kiểm chứng Ngữ cảnh Chữ số trong Công thức Toán học

Chứng minh chữ số trong công thức toán học không bị ảnh hưởng bởi token văn bản trước công thức và đồng bộ giữa `_scratch()` và layout chính.

```bash
pytest tests/test_stable_variants.py -k "test_math_digits_context_independence" -v
```
**Kỳ vọng**:
- Cùng một công thức toán `$x = 123.45$` đặt sau hai đoạn văn khác nhau cho ra khoảng cách chữ số và nét vẽ trùng khớp 100%.

---

### Kịch bản 4: Kiểm chứng Hiển thị Seed trong Báo cáo Kết quả (Desktop GUI & CLI)

Kiểm tra hàm `write_report_lines()` tự động bổ sung dòng `Seed đã dùng: ...`:

```bash
pytest tests/test_seed_lifecycle.py -k "test_write_report_lines_displays_seed_used" -v
```
**Kỳ vọng**:
- Dòng chữ `"Seed đã dùng: <N> (chạy lại với --seed <N> để có đúng kết quả này)"` xuất hiện trong danh sách các dòng báo cáo trả về cho Desktop GUI và CLI.

---

### Kịch bản 5: Kiểm chứng Phản hồi Nhập Seed không Hợp lệ trên Web Client

Chạy kiểm thử Node.js cho hàm thuần `parseSeed` và tương tác DOM:

```bash
node --test tests/test_web_parse_seed.test.mjs
```
**Kỳ vọng**:
- Tất cả các trường hợp seed âm, số thực, chuỗi chữ cái trả về `valid: false` cùng thông điệp lỗi tiếng Việt.
- Phần tử `#opt-seed-error` được hiển thị và ẩn đi tương ứng trên giao diện modal tùy chọn.

---

### Kịch bản 6: Kiểm tra Toàn bộ Test Suite để Chống Thoái lui (Regression Check)

Bảo đảm toàn bộ các bài test hiện có và bài test golden master vẫn tiếp tục xanh 100%:

```bash
pytest tests/test_seed_lifecycle.py tests/test_stable_variants.py tests/test_rng.py tests/test_letter_assembly_quality.py
```
**Kỳ vọng**:
- Tất cả các test suites vượt qua trong dưới 3 giây.
