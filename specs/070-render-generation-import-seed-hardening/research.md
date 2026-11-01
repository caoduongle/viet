# Technical Research & Architectural Decisions: Feature 070

**Feature**: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử  
**Date**: 2026-11-01  
**Status**: Completed  

---

## Decision 1: Cơ chế Thế hệ kết xuất (Render Generation / Request ID) chống Race Condition trong `write.js`

### Bối cảnh & Vấn đề
Trong `requestRender(params)` tại `webapp/js/write.js`, luồng xử lý hiện tại gửi yêu cầu `write_text` bất đồng bộ xuống Web Worker:
```javascript
const res = await sendWorkerMessage("write_text", params);
const textarea = typeof document !== "undefined" ? document.getElementById("editor-text") : null;
const currentVal = textarea?.value?.trim() || "";
if (!currentVal) {
  clearPreview();
  return;
}
if (res && res.ok) {
  // Cập nhật DOM, currentXoppBase64, currentDoc...
}
```
**Lỗ hổng race condition**:
1. Người dùng nhập tài liệu $A$, `requestRender` gửi yêu cầu $A$ xuống Worker.
2. Trong khi Worker đang xử lý $A$, người dùng xóa $A$ và nhập (hoặc mở) tài liệu $B$.
3. Khi $A$ xử lý xong, `currentVal` hiện tại là nội dung của $B$ (không rỗng), do đó điều kiện `!currentVal` không thỏa mãn.
4. Kết quả của $A$ được áp dụng vào `currentXoppBase64`, `currentDoc`, và SVG của $A$ được hiển thị trên trang giấy xem trước.
5. Nguy cơ: Người dùng nhìn thấy văn bản $B$ trong textarea nhưng trang giấy lại hiển thị $A$; nếu người dùng bấm "Tải file .xopp" trong lúc này, họ sẽ tải nhầm tệp của $A$.

### Quyết định kỹ thuật
- Sử dụng biến toàn cục tăng đơn điệu `currentRenderGeneration = 0`.
- Mỗi khi phát sinh một yêu cầu kết xuất mới (từ `triggerPreviewImmediate` hoặc hàng chờ `pendingParams`), tăng `const thisGeneration = ++currentRenderGeneration;`.
- Lưu snapshot tham số kết xuất đi kèm:
  ```javascript
  currentRenderSnapshot = {
    generation: thisGeneration,
    text: params.text,
    format: params.format,
    seed: params.options?.seed,
  };
  ```
- Khi Worker trả về kết quả `res`, thực hiện kiểm tra 2 lớp bảo vệ (Two-Layer Stale Guard):
  1. **Kiểm tra Generation ID**: `if (thisGeneration !== currentRenderGeneration) return;` (Hủy ngay lập tức nếu đã có yêu cầu mới hơn được kích hoạt).
  2. **Kiểm tra Snapshot khớp với DOM**: `if (textarea && textarea.value !== currentRenderSnapshot.text) return;` (Đảm bảo nội dung soạn thảo hiện hành vẫn trùng khớp hoàn toàn với nội dung đã kết xuất).
- Nếu kết quả bị coi là lỗi thời (stale), lập tức bỏ qua và không cập nhật bất kỳ biến trạng thái nào (`currentXoppBase64`, `currentDoc`, `currentMissingBoxes`, v.v.).

### Các giải pháp thay thế đã đánh giá
- *Hủy bỏ Worker qua `worker.terminate()`*: Quá tốn kém tài nguyên vì khởi động lại Pyodide mất 1-2 giây.
- *Chỉ so sánh chuỗi văn bản*: Dễ bị sai lệch nếu người dùng chỉnh sửa các tùy chọn khác (đổi seed, đổi cỡ chữ, đổi định dạng Markdown sang TXT) với cùng một chuỗi văn bản.

---

## Decision 2: Tương tác giữa Render Generation và mô hình Một yêu cầu chờ (One-Pending-Request)

### Bối cảnh & Vấn đề
`write.js` sử dụng cờ `isRendering`, `hasPendingRequest` và `pendingParams` để kiểm soát không gửi dồn dập nhiều yêu cầu xuống Worker.

### Quyết định kỹ thuật
Khi một yêu cầu kết xuất mới đến trong lúc `isRendering === true`:
1. Tăng `currentRenderGeneration++`.
2. Gán `hasPendingRequest = true; pendingParams = params;`.
3. Khi yêu cầu đang chạy trong Worker trả về:
   - Vì `thisGeneration < currentRenderGeneration`, kết quả này bị loại bỏ ngay tại khối `try`, không cập nhật DOM hay bộ nhớ đệm.
4. Trong khối `finally`:
   - `isRendering = false;`
   - Nhận diện `hasPendingRequest === true` $\to$ giải phóng hàng chờ và gọi đệ quy `requestRender(nextParams)` với thế hệ mới nhất.
5. Kết quả: Toàn bộ các kết quả dở dang đều bị triệt tiêu êm dịu, chỉ có yêu cầu mới nhất cuối cùng được hiển thị lên màn hình.

---

## Decision 3: Thiết kế kiểm thử E2E Playwright chứng minh Reset Seed khi Mở tài liệu mới

### Bối cảnh & Vấn đề
Bài test E2E hiện tại trong `tests/e2e/write.spec.ts` chỉ kiểm tra việc mở tệp `accept_sample.txt` có sinh ra SVG và polyline. Nó chưa chứng minh được:
1. Occurrence của từ lặp trong tài liệu mới có bị kế thừa từ tài liệu cũ hay không.
2. Hành vi reset seed có hoạt động ổn định trên cả 3 định dạng tệp: `.txt`, `.md`, `.docx`.
3. Khả năng chống race condition khi mở file trong lúc tài liệu cũ đang render.

### Quyết định kỹ thuật
1. **Kiểm thử đối chiếu Occurrence độc lập**:
   - Bước 1: Soạn thảo tài liệu $A$ có từ lặp `"xin xin chào ba"`. Ở lượt này, từ `"xin"` thứ hai được gán `occurrence = 1`.
   - Bước 2: Mở tệp tài liệu $B$ chỉ chứa một từ `"xin"`.
   - Bước 3: Thu thập mảng tọa độ nét vẽ của từ `"xin"` trong tài liệu $B$.
   - Bước 4: So sánh với nét vẽ chuẩn của từ `"xin"` khi kết xuất ở trạng thái ban đầu (`occurrence = 0`). Khẳng định trùng khớp 100%. Nếu có hiện tượng kế thừa occurrence từ $A$, từ `"xin"` trong $B$ sẽ nhận `occurrence = 1` hoặc `occurrence = 2` và nét vẽ sẽ bị lệch hoàn toàn.
2. **Kiểm thử trên đa định dạng tệp**:
   - Sử dụng các fixture tệp có sẵn trong kho: `tests/data/sample.docx`, `tests/data/accept_sample.txt`.
   - Xác nhận cả 3 luồng nạp tệp đều gửi `clear_document_history` thành công.
3. **Kiểm thử Race Condition**:
   - Nhập một đoạn văn bản dài, ngay khi vừa gửi lệnh (chưa đầy 50ms, đang render), lập tức nạp tệp mới.
   - Xác nhận kết quả hiển thị trên màn hình là nội dung của tệp mới, không bao giờ xuất hiện nét chữ của văn bản dài trước đó.

---

## Decision 4: Xử lý an toàn và kiểm tra trạng thái API `clear_document_history`

### Bối cảnh & Vấn đề
Trong `write.js`, hiện tại lệnh xóa lịch sử seed được gọi:
```javascript
sendWorkerMessage("clear_document_history").catch((e) => console.warn("Lỗi xóa lịch sử seed:", e));
```
`BrowserBridge.clear_document_history()` trong Python trả về dictionary `{"ok": True}` hoặc `{"ok": False, "error": ...}`. Việc chỉ bắt Promise rejection (`.catch()`) sẽ bỏ sót trường hợp Python trả về `{"ok": False}`.

### Quyết định kỹ thuật
Chuẩn hóa hàm gọi nội bộ `resetDocumentSeedHistory()` trong `write.js`:
```javascript
async function resetDocumentSeedHistory() {
  try {
    const res = await sendWorkerMessage("clear_document_history");
    if (!res || res.ok === false) {
      console.warn("Dịch vụ nền phản hồi lỗi khi xóa lịch sử hạt giống:", res?.error);
      return false;
    }
    return true;
  } catch (err) {
    console.warn("Không thể gửi thông điệp xóa lịch sử hạt giống:", err);
    return false;
  }
}
```
Mọi vị trí cần xóa lịch sử (khi ô soạn thảo rỗng, khi mở file .txt/.md/.docx) đều gọi qua hàm chuẩn hóa này.

---

## Decision 5: Bền vững hóa Assertion hình thái nét chữ trong `test_stable_variants.py`

### Bối cảnh & Vấn đề
Trong `test_app_controller_stable_variants_workflow`, các kiểm tra nét vẽ hiện dựa vào chỉ số mảng cố định:
`strokes1[0:3] == strokes2[0:3]`, `strokes1[6:11] == strokes2[6:11]`.
Nếu bộ mẫu chữ trong kho có thay đổi nhỏ về số nét (ví dụ chữ "x" gồm 2 nét thay vì 1 nét), các chỉ số mảng cố định sẽ bị lệch và làm test thất bại dù logic hạt giống hoàn toàn chính xác.

### Quyết định kỹ thuật
- Xây dựng hàm trợ giúp `group_strokes_by_word_proximity(strokes, expected_words)` hoặc phân tích cấu trúc phần tử từ XML XOPP dựa trên khoảng cách tọa độ trục X (`gap`).
- Trong phạm vi Feature 070: Chuẩn hóa hàm trích xuất nét vẽ từ file XOPP thành danh sách các nhóm nét vẽ theo từng từ, đảm bảo tính bền vững và khả năng bảo trì lâu dài.

---

## Decision 6: Chuẩn hóa số liệu chú thích đo kiểm hiệu năng Snapshot

### Bối cảnh & Vấn đề
Trong `tests/test_performance_regression.py` hàm `test_bank_snapshot_large_scale_performance`:
- Chú thích ghi: "20 ký hiệu x 2 biến thể = 40 mẫu, 30 dấu thanh x 2 biến thể = 60 mẫu -> 3.420 mẫu nét".
- Dữ liệu thực tế tạo ra:
  - 700 từ $\times$ 3 biến thể = 2.100 mẫu
  - 300 chữ cái $\times$ 4 biến thể = 1.200 mẫu
  - 50 ký hiệu $\times$ 2 biến thể = 100 mẫu
  - 5 nhóm dấu thanh $\times$ 20 mẫu = 100 mẫu
  - 10 chữ số $\times$ 2 biến thể = 20 mẫu
  - Tổng số mẫu nét thực tế tính trong `total_bank_samples` = 3.520 mẫu nét.

### Quyết định kỹ thuật
Cập nhật lại toàn bộ docstring và phần in thông báo `[BENCHMARK]` trong `test_performance_regression.py` thành:
`"1.050+ nhãn và 3.520 mẫu nét đa biến thể"`, đảm bảo tính trung thực và nhất quán 100% giữa lý thuyết và thực nghiệm.
