# Quickstart & Verification Guide: Feature 070

**Feature**: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử  
**Branch**: `070-render-generation-import-seed-hardening`  

---

## 1. Kịch bản kiểm chứng 1: Chống ghi đè kết quả render cũ (P1 - SC-001)

### Mục tiêu
Chứng minh rằng khi đang xử lý kết xuất một tài liệu dài mà người dùng xóa hoặc thay thế bằng tài liệu khác, kết quả của tài liệu cũ trả về sau đó không bao giờ ghi đè lên giao diện hay tệp xuất của tài liệu mới.

### Lệnh thực thi
```powershell
npx playwright test tests/e2e/write.spec.ts -g "không ghi đè bản xem trước mới"
```

### Kỳ vọng (Expected Outcome)
- Khi nhập văn bản dài $A$, lập tức thay thế bằng văn bản ngắn $B$, trang giấy xem trước chỉ hiển thị nội dung của $B$.
- Dữ liệu `currentXoppBase64` và SVG của trang giấy chỉ chứa các nét chữ của $B$, hoàn toàn không có nét chữ nào của $A$.
- Bảng điều khiển Console của trình duyệt sạch sẽ, không có lỗi ngoại lệ.

---

## 2. Kịch bản kiểm chứng 2: Độc lập hạt giống khi mở tài liệu mới (P1 - SC-002)

### Mục tiêu
Chứng minh rằng việc mở một tài liệu mới (.txt, .md, .docx) luôn xóa sạch lịch sử seed và căn chỉnh của tài liệu cũ, không làm tăng hoặc kế thừa occurrence của các từ lặp.

### Lệnh thực thi
```powershell
npx playwright test tests/e2e/write.spec.ts -g "xóa trắng hoặc mở file mới"
```

### Kỳ vọng (Expected Outcome)
- Soạn thảo tài liệu $A$ có từ lặp `"xin xin chào ba"` khiến từ `"xin"` thứ hai nhận `occurrence = 1`.
- Mở tài liệu mới $B$ chứa từ `"xin"`, nét vẽ của từ `"xin"` trong tài liệu $B$ trùng khớp 100% với nét vẽ khi kết xuất trên một phiên làm việc mới tinh (`occurrence = 0`).
- Kiểm thử bao phủ cả việc nhập tệp văn bản `.txt`, `.md` và tệp Word `.docx`.

---

## 3. Kịch bản kiểm chứng 3: Bền vững hóa Assertion kiểm thử nét vẽ (P2 - SC-004)

### Mục tiêu
Xác nhận bộ kiểm thử so sánh toàn bộ hình thái nét vẽ trong `test_stable_variants.py` hoạt động chính xác, ổn định và không bị phụ thuộc vào chỉ số mảng cố định.

### Lệnh thực thi
```powershell
pytest tests/test_stable_variants.py -k "test_app_controller_stable_variants_workflow" -v
```

### Kỳ vọng (Expected Outcome)
- Toàn bộ các nét vẽ của các từ được giữ lại (`"xin"`, `"chào"`) và cấu trúc hình học tương đối của từ `"ba"` được đối sánh thành công.
- Kiểm thử vượt qua (`PASSED`) với thời gian dưới 2 giây.

---

## 4. Kịch bản kiểm chứng 4: Đo kiểm hiệu năng Kho mẫu quy mô lớn (P3 - SC-005)

### Mục tiêu
Xác nhận thời gian trích xuất bản chụp kho mẫu với 1.050+ nhãn và 3.520 mẫu nét đa biến thể hoàn tất trong thời gian dưới 200 mili-giây, và phần chú thích kỹ thuật khớp chính xác 100% với cấu trúc dữ liệu thực tế.

### Lệnh thực thi
```powershell
pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s
```

### Kỳ vọng (Expected Outcome)
- Chú thích và log console in đúng: `[BENCHMARK] get_bank_snapshot 1.050+ nhãn và 3.520 mẫu nét đa biến thể hoàn tất trong: ... ms`.
- Kết quả `res["ok"] is True`, `stats["n_samples"] >= 1400`, tổng mẫu nét $\ge 3.520$, thời gian thực thi $t < 200$ ms (thực tế đo được $< 2$ ms).

---

## 5. Quy trình Kiểm chứng Hồi quy Toàn diện (Full Regression Verification)

Trước khi nghiệm thu tính năng, thực thi toàn bộ kiểm thử hệ thống:

```powershell
# 1. Lint mã nguồn Python
python -m ruff check chuviettay tests

# 2. Đóng gói phân phối tĩnh Web Client
python scripts/build_web.py

# 3. Bộ kiểm thử Node.js đơn vị & Golden Master
npm run test:unit
npm run test:browser
npm run test:golden

# 4. Bộ kiểm thử E2E Playwright trên trình duyệt (22 tests)
npx playwright test

# 5. Toàn bộ kiểm thử Python (>1.427 tests)
pytest
```

### Ghi chú Minh bạch Số liệu Kiểm thử Python:
- **Môi trường máy phát triển cục bộ (Windows)**: `1.427 passed` (toàn bộ kiểm thử Word COM và Tkinter chạy đầy đủ).
- **Môi trường CI GitHub Actions (Ubuntu Linux Runner, Python 3.12 / 3.13)**: `1.406 passed · 14 skipped · 7 deselected`:
  - `14 skipped`: Do các bài kiểm thử chuyển đổi tệp Word Fidelity (`test_fidelity_pdf_first.py`, `test_docx_fidelity.py`, `test_fidelity_whiten_math.py`, `test_importer_fidelity.py`) tự động kiểm tra `win32com.client` và bỏ qua khi chạy trên Linux.
  - `7 deselected`: Do tham số cấu hình CI `-m "not tkinter"` loại trừ các bài kiểm thử giao diện Tkinter cũ trên môi trường máy chủ headless không có màn hình X11.

---

## 6. Bảng Ghi nhận Kết quả Kiểm chứng Thực tế (Verification Record)

| Kịch bản kiểm chứng | Lệnh thực thi | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Kịch bản 1** (Chống ghi đè render cũ) | `npx playwright test tests/e2e/write.spec.ts -g "không bị kết quả cũ ghi đè"` | 100% PASS. Two-Layer Stale Guard chặn đứng race condition in-flight, bản xem trước chỉ hiển thị nét chữ tài liệu mới. | ✅ PASS |
| **Kịch bản 2** (Độc lập seed khi mở file) | `npx playwright test tests/e2e/write.spec.ts -g "xóa trắng hoặc mở file mới"` | 100% PASS. Nét vẽ từ "xin" của tài liệu mới trùng khớp 100% với baseline `occurrence = 0`, không kế thừa lịch sử cũ (.txt, .md, .docx). | ✅ PASS |
| **Kịch bản 3** (Bền vững hóa assertion nét) | `pytest tests/test_stable_variants.py -k "test_app_controller_stable_variants_workflow" -v` | 1 passed in 0.40s. `group_strokes_by_word_proximity` phân tách chính xác 4 từ (doc1) và 5 từ (doc2), đối sánh hình thái nét tương đối của từ "ba" thành công. | ✅ PASS |
| **Kịch bản 4** (Multi-variant Benchmark) | `pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s` | 1 passed in 1.51s. Log in: `[BENCHMARK] get_bank_snapshot 1.050+ nhãn và 3.520 mẫu nét đa biến thể hoàn tất trong: 1.91 ms` ($< 200$ ms). | ✅ PASS |
| **Hồi quy Web E2E (23 tests)** | `npx playwright test` | 23 passed in 3.2m (100% PASS toàn bộ 23 bài test Playwright). | ✅ PASS |
| **Hồi quy Python (1.427 tests)** | `pytest` | 1.427 passed in 61.00s (100% PASS trên Windows local; tương ứng 1.406 passed trên Ubuntu Linux CI). | ✅ PASS |
