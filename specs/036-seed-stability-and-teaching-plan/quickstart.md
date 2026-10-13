# Quickstart: Hướng dẫn Kiểm chứng & Chạy thử nghiệm Feature 036

**Feature**: `036-seed-stability-and-teaching-plan`  
**Branch**: `feat/036-seed-stability`  
**Spec & Contracts**: [spec.md](./spec.md) | [Contracts](./contracts/)

---

## 1. Môi trường & Tiền điều kiện

- **Python**: `>= 3.10` (Hiện tại máy phát triển chạy Python 3.14).
- **Node.js**: `>= 18.0` (dành cho bộ kiểm thử web/parseSeed và pyodide).
- **Phụ thuộc runtime**: `dependencies = []` (tuyệt đối không cài thêm thư viện runtime bên ngoài).

Kiểm tra trạng thái môi trường:
```bash
python --version
node --version
ruff --version
```

---

## 2. Kịch bản Kiểm chứng Tự động (Automated Verification)

### Kịch bản 1: Kiểm chứng Vòng đời Seed và Miền giá trị (WP1)
Chứng minh `WriteOptions` chặn seed âm/sai kiểu, `seed=None` sinh `seed_used`, và CLI in thông báo tái tạo:
```bash
python -m pytest tests/test_seed_lifecycle.py -v
```
**Kỳ vọng**:
- `WriteOptions(seed=-1)` ném `ValueError` với thông báo tiếng Việt.
- `WriteOptions(seed=True)` ném `ValueError` (kiểu bool).
- `write_text(..., seed=None)` trả về `result.seed_used` là số nguyên $[0, 2^{32}-1]$.
- Tái tạo kết quả với `--seed <seed_used>` tạo ra tệp đầu ra giống nhau 100% từng byte.

### Kịch bản 2: Kiểm chứng Hàm Web `parseSeed()` (WP1)
Kiểm chứng xử lý seed trên giao diện web độc lập:
```bash
node --test tests/test_web_parse_seed.test.mjs
```
**Kỳ vọng**:
- `parseSeed("0", 42)` trả về `{ seed: 0, valid: true }`.
- `parseSeed("", 42)` trả về `{ seed: 42, valid: false }` (không tự ép thành 42).
- `parseSeed("-5", 42)` trả về `{ seed: 42, valid: false }`.

### Kịch bản 3: Kiểm chứng Luồng Ngẫu nhiên Cục bộ & Stable Variants Đỏ sang Xanh (WP2)
Chứng minh `test_stable_variants.py` thất bại trên mã nguồn cũ và thành công trên mã nguồn mới:
```bash
python -m pytest tests/test_stable_variants.py -v
```
**Kỳ vọng**:
- So sánh tag thật `let:h`, `let:ô`, `variant_idx` và vector nét vẽ thay vì `None == None`.
- Chèn từ "a" phía trước không làm đổi hình thái từ "nay" (prepend invariance).
- Lặp từ 50 lần không có 2 lần liên tiếp trùng mẫu.
- Bất biến tịnh tiến trục Y khi chèn đoạn văn mới ở đầu.

### Kịch bản 4: Kiểm chứng Bảo toàn Tuyệt đối Golden Master Cũ (Zero Regression)
Bảo đảm mã băm SHA-256 của chế độ mặc định (`stable_variants=False`) không đổi từng byte:
```bash
python -m pytest tests/test_golden_master_real_path.py -v
```
**Kỳ vọng**: Tất cả 8 ca kiểm thử golden master đều PASS với mã SHA-256 gốc không đổi.

### Kịch bản 5: Kiểm chứng Phân trang Bảng Ô Gộp và Bounding Box (P1/P2)
Kiểm chứng quét ô nguồn toàn bảng và không làm bẹt nét chữ:
```bash
python -m pytest tests/test_table_continuation.py -v
```
**Kỳ vọng**:
- Ô `rowspan=4` chứa 80 dòng trải qua 3+ trang giữ nguyên vẹn 100% dòng, không ghi đè ô khác cùng cột.
- Không có đoạn collinear bẹt dí ở đáy trang; bounding box nét chữ nằm trọn trong lề in.
- `TableCell` trong Document IR không có trường lạ bị gán vào.

### Kịch bản 6: Kiểm chứng 38 Mục Cốt lõi và Gỡ nghẽn Hàng đợi Dạy chữ (Teaching Plan)
Kiểm chứng độ phủ 700 từ SEED và giải phóng từ đã dạy:
```bash
python -m pytest tests/test_teaching_plan.py -v
```
**Kỳ vọng**:
- 38 mục cốt lõi (33 chữ cái thường + 5 dấu thanh) mở khóa 100% (700/700) từ điển `SEED`.
- `teach_char("tôi")` lưu vào `bank.words` và `Bank.can("tôi")` trả về `True`, gỡ bỏ "tôi" khỏi `missing_minimal_essentials()`.

---

## 3. Kiểm tra Toàn diện CI & Linter

Chạy linter và toàn bộ test suite dự án:
```bash
ruff check .
python -m pytest -q --timeout=60 -m "not benchmark"
npm run test:unit
```
**Kỳ vọng**: Rút cuộc toàn bộ $\ge 1269$ tests đều xanh, ruff sạch 100%, 0 warning, 0 regression.
