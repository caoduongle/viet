# Technical Research & Architectural Decisions: Feature 070

**Feature**: Kiểm soát thế hệ kết xuất, thế hệ nhập tệp, khóa xuất bản cũ và tăng cường tính xác định kiểm thử  
**Date**: 2026-11-01  
**Status**: Completed  

---

## Decision 1: Cơ chế Thế hệ kết xuất (Render Generation / Request ID) chống Race Condition trong `write.js`

### Bối cảnh & Vấn đề
Trong `requestRender(params)` tại `webapp/js/write.js`, luồng xử lý gửi yêu cầu `write_text` bất đồng bộ xuống Web Worker. Nếu người dùng nhập tài liệu $A$ rồi đổi sang tài liệu $B$ trong lúc Worker đang xử lý $A$, kết quả trả về muộn của $A$ có nguy cơ ghi đè lên giao diện và dữ liệu xuất của $B$.

### Quyết định kỹ thuật
- Sử dụng biến toàn cục tăng đơn điệu `currentRenderGeneration = 0`.
- Mỗi khi phát sinh một yêu cầu kết xuất mới, tăng `const thisGeneration = ++currentRenderGeneration;` và đánh dấu ngay `isRenderStale = true`.
- Kiểm tra thế hệ kết xuất ở cả 2 giai đoạn (sau khi Worker trả kết quả và sau khi giải nén XOPP xong).

---

## Decision 2: Tương tác giữa Render Generation và mô hình Một yêu cầu chờ (One-Pending-Request)

### Bối cảnh & Vấn đề
`write.js` sử dụng cờ `isRendering`, `hasPendingRequest` và `pendingParams` để kiểm soát không gửi dồn dập nhiều yêu cầu xuống Worker.

### Quyết định kỹ thuật
Khi một yêu cầu kết xuất mới đến trong lúc `isRendering === true`:
1. Tăng `currentRenderGeneration++` và đặt `isRenderStale = true`.
2. Gán `hasPendingRequest = true; pendingParams = params;`.
3. Khi yêu cầu đang chạy trong Worker trả về, vì `thisGeneration < currentRenderGeneration`, kết quả cũ bị loại bỏ ngay lập tức.
4. Trong khối `finally`, giải phóng hàng chờ và gọi đệ quy `requestRender(nextParams)` cho yêu cầu mới nhất.

---

## Decision 3: Thiết kế kiểm thử E2E Playwright chứng minh Reset Seed khi Mở tài liệu mới

### Quyết định kỹ thuật
1. **Kiểm thử đối chiếu Occurrence độc lập**: Soạn thảo tài liệu $A$ có từ lặp `"xin xin chào ba"`, sau đó mở tệp $B$ chỉ chứa `"xin"`. Khẳng định nét vẽ của từ `"xin"` trong $B$ trùng khớp 100% với baseline ở trạng thái `occurrence = 0`.
2. **Kiểm thử trên đa định dạng tệp**: Bao phủ cả 3 định dạng `.txt`, `.md`, `.docx`.

---

## Decision 4: Xử lý an toàn và kiểm tra trạng thái API `clear_document_history`

### Quyết định kỹ thuật
Chuẩn hóa hàm `resetDocumentSeedHistory()` trong `write.js`, kiểm tra tường minh `res && res.ok === true`. Nếu trả về `false` hoặc ném ngoại lệ, hiển thị cảnh báo lỗi rõ ràng và dừng thao tác nạp tệp.

---

## Decision 5: Bền vững hóa Assertion hình thái nét chữ trong `test_stable_variants.py`

### Quyết định kỹ thuật
Sử dụng hàm `group_strokes_by_word_proximity(strokes)` phân tách nét vẽ theo khoảng cách trục X thay vì dùng chỉ số mảng cố định.

---

## Decision 6: Chuẩn hóa số liệu chú thích đo kiểm hiệu năng Snapshot

### Quyết định kỹ thuật
Đồng bộ docstring và log `[BENCHMARK]` trong `test_performance_regression.py` thành `"1.050+ nhãn và 3.520 mẫu nét đa biến thể"`.

---

## Decision 7: Two-Stage Stale Guard & Atomic State Commit sau giải nén XOPP

### Quyết định kỹ thuật
1. **Giai đoạn 1 (Sau Worker)**: Kiểm tra `thisGeneration === currentRenderGeneration` và `textarea.value === currentRenderSnapshot.text`.
2. **Giải nén cục bộ**: Giải nén `decompressXoppBase64` và parse XML vào biến cục bộ `parsedDoc`. Nếu giải nén lỗi, thoát ra và không chạm vào `currentXoppBase64`.
3. **Giai đoạn 2 (Sau giải nén)**: Kiểm tra lại `thisGeneration === currentRenderGeneration` và `textarea.value === currentRenderSnapshot.text`.
4. **Atomic Commit**: Chỉ khi vượt qua cả 2 giai đoạn mới cập nhật đồng thời `currentXoppBase64`, `currentDoc`, `renderedGeneration = thisGeneration`, `renderedSnapshot`, và `isRenderStale = false`.

---

## Decision 8 (P1): Hoàn thiện `canExport()` với `renderedGeneration` và `renderedSnapshot` đầy đủ (Text, Format & WriteOptions)

### Bối cảnh & Vấn đề
Trong commit `53258d2`, hàm `canExport()` mới kiểm tra `isRendering`, `isRenderStale` và `textarea.value !== currentRenderSnapshot?.text`, dẫn tới 2 lỗ hổng:
1. **Thay đổi tùy chọn viết chữ (`writeOptions`)**: Trong `setupOptionsModal()`, người dùng thay đổi cỡ chữ (`scale`), khoảng cách (`space`), hạt giống (`seed`), màu sắc (`color`) hoặc khổ giấy (`paper`) trực tiếp trên `writeOptions` rồi đóng modal không bấm Áp dụng. Khi đó `canExport()` vẫn trả về `true` và xuất ra tài liệu cũ không khớp với cấu hình hiện hành.
2. **Yêu cầu kết xuất mới thất bại**: Tài liệu $A$ kết xuất thành công ở thế hệ 1. Người dùng đổi hạt giống và kích hoạt kết xuất $B$ ở thế hệ 2, nhưng Worker trả lỗi. Khi đó `isRendering` về `false`, `currentXoppBase64` vẫn giữ dữ liệu của $A$ (thế hệ 1), nếu không kiểm tra `renderedGeneration === currentRenderGeneration` thì người dùng vẫn xuất nhầm tài liệu $A$.

### Quyết định kỹ thuật
1. Lưu trữ bản chụp đã cam kết `renderedSnapshot` tại thời điểm Atomic Commit thành công:
   ```javascript
   renderedSnapshot = {
     generation: thisGeneration,
     text: params.text,
     format: params.format,
     options: cloneWriteOptions(params.options || writeOptions),
   };
   ```
2. Mỗi khi bắt đầu `requestRender()`, đánh dấu ngay `isRenderStale = true` và cập nhật trạng thái các nút xuất. Nếu `requestRender()` thất bại ở bất kỳ bước nào, `isRenderStale` vẫn giữ nguyên là `true` và `renderedGeneration` vẫn nhỏ hơn `currentRenderGeneration`.
3. Trong `setupOptionsModal()`, mọi sự kiện chỉnh sửa thuộc tính của `writeOptions` đều đánh dấu `isRenderStale = true` và gọi `updateExportButtonsState()`.
4. Trong `canExport()`, thực hiện kiểm tra toàn diện:
   ```javascript
   export function canExport() {
     if (isRendering) return false;
     if (isRenderStale) return false;
     if (renderedGeneration === 0 || renderedGeneration !== currentRenderGeneration) return false;
     if (!currentXoppBase64 || !currentDoc || !renderedSnapshot) return false;
     const textarea = typeof document !== "undefined" ? document.getElementById("editor-text") : null;
     const currentVal = textarea?.value?.trim() || "";
     if (!currentVal) return false;
     if (textarea && textarea.value !== renderedSnapshot.text) return false;
     if (currentFormat !== renderedSnapshot.format) return false;
     if (!areWriteOptionsEqual(writeOptions, renderedSnapshot.options)) return false;
     return true;
   }
   ```

---

## Decision 9 (P2): Kiểm thử Trực tiếp Stage 2 Stale Guard với Giải nén Bị Trì hoãn Có Kiểm soát

### Bối cảnh & Vấn đề
Trong `tests/js/render_generation.test.mjs`, nếu yêu cầu $B$ được gửi trước khi Worker trả kết quả $A$, thì $A$ đã bị loại ngay ở Stage 1 (trước khi gọi `decompressXoppBase64`). Do đó nhánh bảo vệ Stage 2 (sau khi `await decompressXoppBase64` hoàn tất) chưa được kiểm chứng thực nghiệm.

### Quyết định kỹ thuật
- Bổ sung hàm hook kiểm thử `setXoppDecompressorForTesting(fn)` trong `webapp/js/write.js` (mặc định dùng `decompressXoppBase64`).
- Trong bài kiểm thử đơn vị:
  1. Gửi yêu cầu $A$, Worker trả kết quả $A$ ngay khi chưa có $B$ $\to$ $A$ vượt qua Stage 1 và bước vào `await xoppDecompressor(...)`.
  2. Hàm `xoppDecompressor` giả lập giữ $A$ ở trạng thái đang giải nén (chờ Promise `deferredDecompressA`).
  3. Trong lúc $A$ đang giải nén, kích hoạt yêu cầu $B$ $\to$ `currentRenderGeneration` tăng lên.
  4. Cho phép `deferredDecompressA` hoàn tất giải nén XML hợp lệ của $A$.
  5. Khẳng định Stage 2 chặn đứng $A$: `renderedGeneration` không đổi, `currentDoc` không cập nhật $A$.
  6. Cho phép $B$ hoàn tất và khẳng định chỉ có $B$ được cam kết.

---

## Decision 10 (P2): Bộ đếm Thế hệ Nhập tệp (`currentImportGeneration`) Chống Ghi đè Khi Mở Nhiều Tệp Liên tiếp

### Bối cảnh & Vấn đề
Trong `handleFileImport()`, quá trình đọc tệp (`file.text()`, `file.arrayBuffer()`), đặt lại hạt giống (`resetDocumentSeedHistory()`) và chuyển đổi Word (`sendWorkerMessage("import_docx")`) đều là bất đồng bộ. Nếu người dùng chọn mở `A.docx` (chuyển đổi lâu) rồi chọn tiếp `B.txt` (xử lý nhanh), `B.txt` hoàn tất trước nhưng sau đó `A.docx` hoàn tất muộn và ghi đè nội dung cũ lên `textarea`.

### Quyết định kỹ thuật
- Khai báo bộ đếm `let currentImportGeneration = 0;` trong `webapp/js/write.js`.
- Đầu hàm `handleFileImport(file, textarea)`, gán `const thisImportGen = ++currentImportGeneration;`.
- Sau mỗi điểm `await` (`await file.text()`, `await resetDocumentSeedHistory()`, `await file.arrayBuffer()`, `await sendWorkerMessage("import_docx")`), kiểm tra:
  ```javascript
  if (thisImportGen !== currentImportGeneration) return false;
  ```
- Không sửa `pendingImportNotices` hay gọi `clearPreview()` trước khi xác nhận `thisImportGen === currentImportGeneration`.
- Cập nhật `currentFormat` trực tiếp theo phần mở rộng tệp (`.txt` $\to$ `"txt"`, `.md`/`.docx` $\to$ `"md"`), không phụ thuộc vào việc phần tử DOM `#select-format` có tồn tại hay không.
- Trong khối `finally` của nhánh `.docx`, chỉ tắt đèn báo `showRenderingIndicator(false)` khi `!isRendering && thisImportGen === currentImportGeneration` để không làm tắt đèn báo của tệp mới hơn đang kết xuất.
- Viết bài kiểm thử đơn vị kiểm chứng cả 2 chiều: `.docx` hoàn tất chậm hơn `.txt` và `.txt` hoàn tất chậm hơn `.docx`.

---

## Decision 11 (P2): Xác định hóa 100% Kiểm thử E2E Race Condition bằng Cổng Điều khiển Render (`Render Barrier`)

### Bối cảnh & Vấn đề
Việc dùng `await page.waitForTimeout(260)` trong `tests/e2e/write.spec.ts` chỉ đảm bảo qua thời gian debounce 250ms nhưng không chứng minh chắc chắn rằng Worker vẫn đang bận xử lý tài liệu $A$ khi tệp $B$ được mở (nếu máy chạy cực nhanh, $A$ có thể đã xong trước khi mở $B$).

### Quyết định kỹ thuật
- Bổ sung hàm hỗ trợ kiểm thử `installRenderBarrierForTesting()` trong `webapp/js/write.js`.
- Khi barrier được cài đặt trong bài test E2E:
  1. Ngay khi `requestRender()` gửi yêu cầu của văn bản $A$ đi, barrier phát tín hiệu `started` (cho phép test E2E `await waitForRenderStart()`) và tạm giữ phản hồi của $A$ tại cổng chờ `release()`.
  2. Test E2E xác nhận chắc chắn $A$ đang in-flight (`isRendering === true`), sau đó thực hiện mở tệp mới $B$ (`sample_word.txt`).
  3. Sau khi tệp $B$ đã được chọn và kích hoạt luồng nhập tệp, test giải phóng cổng chờ `release()` cho $A$.
  4. Khẳng định kết quả cũ của $A$ bị loại bỏ hoàn toàn và giao diện hiển thị chính xác nét vẽ của tệp $B$.

---

## Decision 12 (P3): Khắc phục Tranh chấp Thời điểm Làm ẩn `#bank-error-banner` trong Bài kiểm thử XSS trên CI

### Bối cảnh & Vấn đề
Trên GitHub Actions (`npx playwright test --workers=2`), bài kiểm thử `tests/e2e/bank.spec.ts:137` thất bại do `#bank-error-banner` có trạng thái `hidden`.
Nguyên nhân gốc rễ:
1. Tại dòng 150 của `bank.spec.ts`, lệnh `await page.click('[data-tab="bank"]')` kích hoạt `switchTab("bank")` $\to$ gọi hàm bất đồng bộ `refreshBankView()` (không `await`).
2. Trong `webapp/js/bank.js`, hàm `refreshBankView()` thực hiện 3 lệnh `await` liên tiếp (`updateProfileChip`, `storage.getSetting`, `sendWorkerFn("get_bank_snapshot")`) rồi mới gọi `showBankErrorBanner(null)` ở dòng 215 để xóa banner lỗi cũ.
3. Trong lúc `refreshBankView()` đang chờ Worker trả về `get_bank_snapshot`, bài test chạy `page.evaluate` gọi `showBankErrorBanner("<b id='xss-test-payload'>...")` làm hiện banner. Ngay sau đó vài mili-giây, `get_bank_snapshot` hoàn tất và dòng 215 `showBankErrorBanner(null)` chạy, ẩn mất banner mà bài test vừa bật!

### Quyết định kỹ thuật
1. **Trong `webapp/js/bank.js`**: Di chuyển lệnh `showBankErrorBanner(null)` lên đầu khối `try` của `refreshBankView()` (trước mọi lệnh `await` bất đồng bộ) để việc xóa thông báo lỗi cũ diễn ra đồng bộ ngay khi bắt đầu làm mới, tuyệt đối không xóa đè lên các thông báo lỗi phát sinh trong khoảng thời gian chờ bất đồng bộ.
2. **Trong `tests/e2e/bank.spec.ts`**: Trong `page.evaluate`, đợi `await bankModule.refreshBankView()` hoàn tất ổn định trước khi gọi `bankModule.showBankErrorBanner(...)`, đảm bảo tính xác định tuyệt đối 100% trên mọi cấu hình luồng CI (`--workers=2`).
