# Quickstart & Verification Guide: Feature 070

**Feature**: Kiểm soát thế hệ kết xuất, thế hệ nhập tệp, khóa xuất bản cũ và tăng cường tính xác định kiểm thử  
**Branch**: `070-render-generation-import-seed-hardening`  

---

## 1. Kịch bản kiểm chứng 1: Khóa xuất tệp theo Thế hệ Kết xuất và Bản chụp Tùy chọn (`canExport`)

### Mục tiêu
Chứng minh chức năng xuất tệp (`.xopp`, `.pdf`, `.png`, `.svg`, `.zip`) chỉ cho phép tải xuống khi `renderedGeneration === currentRenderGeneration` và nội dung văn bản, định dạng cùng toàn bộ `writeOptions` khớp 100% với `renderedSnapshot`. Nếu người dùng sửa tùy chọn viết chữ (cỡ chữ, hạt giống, màu sắc...) hoặc nếu lần kết xuất mới bị lỗi, thao tác xuất tệp bị chặn ngay lập tức.

### Lệnh thực thi
```powershell
node --test tests/js/render_generation.test.mjs
npx playwright test tests/e2e/write.spec.ts -g "Export Stale Guard"
```

### Kỳ vọng (Expected Outcome)
- Khi thay đổi `writeOptions` hoặc khi yêu cầu kết xuất mới gặp lỗi từ Worker, `canExport()` trả về `false` và nút xuất hiển thị cảnh báo.
- Chỉ khi yêu cầu kết xuất mới với bộ tùy chọn mới hoàn tất Atomic Commit thì `canExport()` mới trả về `true`.

---

## 2. Kịch bản kiểm chứng 2: Chốt chặn Giai đoạn 2 (Stage 2 Stale Guard) trong lúc Giải nén XOPP

### Mục tiêu
Chứng minh rằng khi tài liệu $A$ đã nhận kết quả từ Worker (vượt qua Stage 1) và đang trong quá trình giải nén XOPP bất đồng bộ mà tài liệu $B$ được yêu cầu, kết quả giải nén muộn của $A$ bị loại bỏ tại Stage 2 và không bao giờ cập nhật `currentDoc`, `currentXoppBase64` hay SVG.

### Lệnh thực thi
```powershell
node --test tests/js/render_generation.test.mjs
```

### Kỳ vọng (Expected Outcome)
- Khi `setXoppDecompressorForTesting` giữ quá trình giải nén của $A$ tạm dừng và $B$ được kích hoạt, ngay sau khi giải nén $A$ hoàn tất, $A$ bị hủy bỏ tại Stage 2.
- Chỉ có tài liệu $B$ được cam kết vào `renderedSnapshot` và `currentDoc`.

---

## 3. Kịch bản kiểm chứng 3: Chống ghi đè khi Mở nhiều Tệp Liên tiếp (`currentImportGeneration`)

### Mục tiêu
Chứng minh khi người dùng mở liên tiếp 2 tệp có tốc độ xử lý khác nhau (`.docx` cần chuyển đổi qua Worker và `.txt` đọc trực tiếp), chỉ có tệp được chọn cuối cùng mới được áp dụng vào trình soạn thảo, cho dù tệp cũ hoàn tất muộn hơn.

### Lệnh thực thi
```powershell
node --test tests/js/render_generation.test.mjs
```

### Kỳ vọng (Expected Outcome)
- Cả hai chiều (`.docx` hoàn tất chậm hơn `.txt` và `.txt` hoàn tất chậm hơn `.docx`) đều giữ đúng nội dung và định dạng của tệp được chọn sau cùng.
- Nếu `resetDocumentSeedHistory()` trả về `false`, thao tác nhập tệp dừng lại ngay và báo lỗi cảnh báo.

---

## 4. Kịch bản kiểm chứng 4: Kiểm thử E2E Race Condition Xác định 100% và Ổn định CI (`--workers=2`)

### Mục tiêu
1. Xác nhận bài kiểm thử E2E race condition sử dụng cổng chặn điều khiển (`installRenderBarrierForTesting`) giữ yêu cầu `write_text` của văn bản dài $A$ ở trạng thái đang chờ xử lý cho tới khi tệp $B$ được nạp, loại bỏ hoàn toàn sự phụ thuộc vào thời gian chờ cố định.
2. Xác nhận bài kiểm thử chống XSS trên thanh thông báo lỗi Kho mẫu (`tests/e2e/bank.spec.ts:137`) chạy ổn định 100% với `--workers=2`, không bị `refreshBankView()` xóa mất thông báo lỗi.

### Lệnh thực thi
```powershell
npx playwright test tests/e2e/write.spec.ts tests/e2e/bank.spec.ts --workers=2
```

### Kỳ vọng (Expected Outcome)
- Toàn bộ 8 bài kiểm thử trong `write.spec.ts` (6 tests) và `bank.spec.ts` (2 tests) đạt `PASS` 100% khi chạy song song 2 workers.

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

# 4. Bộ kiểm thử E2E Playwright trên trình duyệt (24 tests với 2 workers giống CI)
npx playwright test --workers=2

# 5. Toàn bộ kiểm thử Python (>1.427 tests)
pytest
```

---

## 6. Bảng Ghi nhận Kết quả Kiểm chứng Thực tế (Verification Record)

| Kịch bản kiểm chứng | Lệnh thực thi | Kết quả kỳ vọng / thực tế | Trạng thái |
| :--- | :--- | :--- | :--- |
| **Kịch bản 1** (`canExport` với `renderedGeneration` & `writeOptions`) | `node --test tests/js/render_generation.test.mjs` | 12/12 test PASS (787ms). Khóa xuất tệp khi đổi `writeOptions` (scale, seed, color, paper), đổi `format`, hoặc khi lần render mới thất bại từ Worker. | ✅ PASS 100% |
| **Kịch bản 2** (Stage 2 Stale Guard khi giải nén bị trì hoãn) | `node --test tests/js/render_generation.test.mjs` | Đã chứng minh qua hook `setXoppDecompressorForTesting`: Loại bỏ 100% kết quả của $A$ sau khi giải nén xong nếu $B$ đã phát sinh trong lúc giải nén. | ✅ PASS 100% |
| **Kịch bản 3** (`currentImportGeneration`: `.docx` vs `.txt`) | `node --test tests/js/render_generation.test.mjs` | Giữ đúng nội dung của tệp được chọn cuối cùng ở cả 2 chiều lệch thứ tự (.docx chậm hơn .txt và .txt chậm hơn .docx); dừng nạp tệp an toàn khi reset seed thất bại. | ✅ PASS 100% |
| **Kịch bản 4** (Deterministic E2E Race Condition & Bank XSS) | `npx playwright test --workers=2` | 24/24 bài kiểm thử E2E vượt qua 100% với `--workers=2`. Bài test race condition kiểm soát chính xác bằng Render Barrier (`installRenderBarrierForTesting`); bài test XSS trên `bank.spec.ts:137` chạy ổn định không flaky. | ✅ PASS 100% |
| **Kiểm thử Node.js Unit & Golden Master** | `npm run test:unit`, `test:browser`, `test:golden` | 79/79 unit test PASS; 2/2 browser Pyodide test PASS; 8/8 Golden Master test Pyodide PASS. | ✅ PASS 100% |
| **Kiểm thử Python Lint & Regression** | `python -m ruff check`, `pytest` | Ruff lint sạch sẽ 100%; 36/36 tests python stable variants & performance regression PASS. | ✅ PASS 100% |
