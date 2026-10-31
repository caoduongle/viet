# Quickstart Validation Guide: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

Tài liệu này hướng dẫn cách thiết lập môi trường, thực thi các kịch bản kiểm thử độc lập và kiểm chứng các mục tiêu thành công của tính năng `069-seed-reset-bank-cache-hardening`.

---

## 1. Chuẩn bị môi trường & Điều kiện tiên quyết

- **Thư mục làm việc**: Gốc repository `d:\viet\app`.
- **Python**: Phiên bản 3.10 trở lên.
- **Node.js**: Phiên bản 18+ đã cài đặt `@playwright/test`.

Kiểm tra trạng thái môi trường:
```powershell
python --version
npm --version
npx playwright --version
```

---

## 2. Kịch bản kiểm chứng 1: Xóa trắng hoặc Mở tệp mới tự động xóa lịch sử hạt giống (P1 - SC-001)

### Mục tiêu
Xác nhận sau khi xóa trắng ô soạn thảo hoặc mở tài liệu mới qua `handleFileImport`, các từ trùng lặp trong tài liệu mới nhận biến thể bắt đầu từ đầu (`occurrence = 0`) và không kế thừa từ tài liệu trước.

### Lệnh thực thi
```powershell
# Chạy kiểm thử E2E Playwright cho tình huống xóa trắng và mở tài liệu mới
npx playwright test tests/e2e/write.spec.ts -g "xóa trắng hoặc mở file mới"
```

### Kỳ vọng (Expected Outcome)
- Soạn thảo văn bản A $\to$ xóa trắng $\to$ soạn lại văn bản A: hình thái nét chữ của văn bản mới giống hệt lần đầu tiên.
- Soạn thảo văn bản A $\to$ mở tệp văn bản B: các từ trong tệp B được gán occurrence độc lập, không kế thừa chỉ số của A.
- Không phát sinh ngoại lệ trên browser console.

---

## 3. Kịch bản kiểm chứng 2: Cam kết Bộ nhớ đệm Kho mẫu an toàn chỉ sau khi Render thành công (P1 - SC-002)

### Mục tiêu
Xác nhận nếu quá trình dựng thẻ mẫu gặp sự cố ở lần gọi đầu tiên, bộ nhớ đệm snapshot bị vô hiệu hóa và lần gọi tiếp theo sẽ tự động dựng lại thành công toàn bộ danh sách thẻ chữ.

### Lệnh thực thi
```powershell
# Chạy kiểm thử đơn vị JS cho cơ chế Two-Phase Cache Commit trong bank.js
npm run test:unit -- -t "refreshBankView"
```

### Kỳ vọng (Expected Outcome)
- Khi mô phỏng `applyFiltersAndRender()` ném ngoại lệ ở lần 1, `lastBankSnapshotCache` vẫn ở trạng thái `{ epoch: null, revision: null, profileId: null }`.
- Lần gọi 2 không bị chặn bởi cache và hiển thị đầy đủ danh sách thẻ mẫu.

---

## 4. Kịch bản kiểm chứng 3: Bảo toàn Toàn bộ Hình thái Nét vẽ (All Strokes) qua Các Lượt Sửa (P2 - SC-003)

### Mục tiêu
Xác nhận kiểm tra assertion `occs_d3[3] == 1` và so sánh 100% dữ liệu nét vẽ (all strokes) của toàn bộ các từ được giữ lại giữa các lượt chỉnh sửa liên tiếp.

### Lệnh thực thi
```powershell
pytest tests/test_stable_variants.py -k "multi_step or stable_variants_workflow" -v
```

### Kỳ vọng (Expected Outcome)
- `assert occs_d3[3] == 1` vượt qua thành công.
- Toàn bộ danh sách chuỗi nét vẽ của các từ `"xin"`, `"chào"`, `"ba"` giữa 2 lần render trùng khớp 100%.

---

## 5. Kịch bản kiểm chứng 4: Đo kiểm Hiệu năng Kho mẫu Đa biến thể Quy mô lớn (P3 - SC-004)

### Mục tiêu
Xác nhận `BrowserBridge.get_bank_snapshot` duy trì tốc độ xử lý dưới 200ms trên kho mẫu quy mô lớn chứa hơn 1.050 nhãn và 3.400+ mẫu nét đa biến thể.

### Lệnh thực thi
```powershell
pytest tests/test_performance_regression.py -k "test_bank_snapshot_large_scale_performance" -v -s
```

### Kỳ vọng (Expected Outcome)
- Bài test nạp kho với 700 từ (3 biến thể/từ), 300 chữ cái (4 biến thể/chữ), 20 ký hiệu và 30 dấu thanh.
- Tổng số mẫu nét $\ge 3.400$ mẫu.
- Kết quả `res["ok"] is True`, thời gian thực thi $t < 200$ ms.

---

## 6. Toàn bộ Quy trình Kiểm chứng Hồi quy (Full Regression Verification)

Trước khi nghiệm thu tính năng, thực thi toàn bộ kiểm thử hệ thống:
```powershell
# 1. Đóng gói phân phối tĩnh Web Client
python scripts/build_web.py

# 2. Bộ kiểm thử Node.js đơn vị & Golden Master
npm run test:unit
npm run test:browser
npm run test:golden

# 3. Bộ kiểm thử E2E Playwright trên trình duyệt (21 tests)
npx playwright test

# 4. Toàn bộ kiểm thử Python (>1.410 tests)
pytest
```
Tất cả các kiểm thử phải đạt trạng thái xanh (ALL PASS).

### Ghi chú Minh bạch Số liệu Kiểm thử Python:
- **Môi trường máy phát triển cục bộ (Windows)**: `1.427 passed` (toàn bộ kiểm thử Word COM và Tkinter chạy đầy đủ, bổ sung thêm `test_clear_document_history`).
- **Môi trường CI GitHub Actions (Ubuntu Linux Runner, Python 3.12 / 3.13)**: `1.406 passed · 14 skipped · 7 deselected`:
  - `14 skipped`: Do các bài kiểm thử chuyển đổi tệp Word Fidelity (`test_fidelity_pdf_first.py`, `test_docx_fidelity.py`, `test_fidelity_whiten_math.py`, `test_importer_fidelity.py`) tự động kiểm tra `win32com.client` và bỏ qua khi chạy trên Linux.
  - `7 deselected`: Do tham số cấu hình CI `-m "not tkinter"` loại trừ các bài kiểm thử giao diện Tkinter cũ trên môi trường máy chủ headless không có màn hình X11.

---

## 7. Bảng Ghi nhận Kết quả Kiểm chứng Thực tế (Verification Record)

| Kịch bản kiểm chứng | Lệnh thực thi | Kết quả thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Kịch bản 1** (Xóa lịch sử seed khi xóa/mở file) | `npx playwright test tests/e2e/write.spec.ts` | 3 passed in 26.2s (test case xóa trắng và mở file mới PASS trong 7.8s) | ✅ PASS |
| **Kịch bản 2** (Two-Phase Cache Commit) | `npm run test:unit tests/js/bank_cache.test.mjs` | 2 passed in 14.3ms (toàn bộ 67/67 unit test JS đạt 100% PASS) | ✅ PASS |
| **Kịch bản 3** (All Strokes Parity & occs_d3[3]) | `pytest tests/test_stable_variants.py` | 26 passed in 25.5s (Khẳng định 100% nét vẽ của 'xin', 'chào', 'ba' khớp tuyệt đối, `occs_d3[3] == 1`) | ✅ PASS |
| **Kịch bản 4** (Multi-variant Bank Benchmark) | `pytest tests/test_performance_regression.py -k "large_scale"` | 1 passed in 1.67 ms (Kho mẫu 1.050+ nhãn, 3.420 mẫu nét đa biến thể hoàn tất < 200ms) | ✅ PASS |
| **Hồi quy Web E2E (21 tests)** | `npx playwright test` | 21 passed in 3.6m (21/21 tests đạt 100% PASS trên trình duyệt Chromium) | ✅ PASS |
| **Hồi quy Python (CI vs Local)** | `pytest` | **Local (Windows):** 1.427 passed in 89.23s<br>**CI (Linux Python 3.12/3.13):** 1.406 passed · 14 skipped · 7 deselected | ✅ PASS |
