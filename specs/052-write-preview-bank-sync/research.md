# Research & Technical Decisions: 052-write-preview-bank-sync

## 1. Vòng đời khởi tạo & Cuộc đua bất đồng bộ (Lifecycle Race Condition)

### Vấn đề (The Problem)
Trong tệp `webapp/js/app.js`, hàm `onWorkerReady()` điều phối quá trình khởi động sau khi Pyodide Web Worker phát tín hiệu `READY`:
```javascript
// webapp/js/app.js:558-560
if (typeof document !== "undefined") {
  initBankTab(sendWorkerMessage, { signal });
  initWriteTab({ signal }); // <-- Gọi đồng bộ tại đây
  ...
}

// webapp/js/app.js:645-662
const profiles = await storage.listProfiles();
const activeId = await storage.getSetting("active_profile_id", profiles[0].id);
const profile = await storage.getProfile(activeId);
if (profile && profile.data) {
  await sendWorkerMessage("load_bank", {
    gzBytes: Array.from(new Uint8Array(profile.data)),
    createIfMissing: false,
  });
  if (typeof document !== "undefined" && document.getElementById("bank-summary")) {
    await refreshBankView();
  }
  if (typeof window !== "undefined" && window.__teachController) {
    await window.__teachController.refresh();
  }
}
```
Tại dòng 560, `initWriteTab()` kiểm tra:
```javascript
// webapp/js/write.js:122-124
if (textarea.value.trim()) {
  triggerPreviewImmediate();
}
```
Nếu trình duyệt tự động khôi phục nội dung văn bản trong `<textarea id="editor-text">` (form restoration/bfcache/reload):
1. `triggerPreviewImmediate()` lập tức gửi yêu cầu `write_text` sang Web Worker.
2. Tại thời điểm đó, lệnh `sendWorkerMessage("load_bank", ...)` ở dòng 660 **chưa hề hoàn thành** (thậm chí chưa được gọi do phải chờ `storage.listProfiles()` và `storage.getProfile()`).
3. Web Worker Pyodide thực hiện `write_text` trên kho rỗng tạm thời (`/tmp/active_bank.json.gz`, có 0 mẫu).
4. Kết quả trả về: 100% token bị xem là thiếu mẫu (`missing_sorted`), toàn bộ trang giấy bị gạch chân đỏ đứt đoạn.
5. Vài trăm mili-giây sau, `load_bank` hoàn tất, Tab Kho mẫu và Tab Dạy chữ được làm mới, nhưng **Tab Viết chữ hoàn toàn không nhận được thông báo làm mới**, khiến giao diện xem trước bị kẹt vĩnh viễn ở trạng thái kho rỗng.

### Bằng chứng xác thực (User Evidence)
Người dùng xác nhận: khi mở modal "Tùy chọn", thay đổi số `seed` hoặc bấm nút hạt giống ngẫu nhiên rồi áp dụng, bản vẽ lập tức trở lại bình thường và hiển thị đầy đủ nét viết tay. Lý do:
```javascript
// webapp/js/write.js:759-760 & 795
writeOptions.seed = nextSeed;
triggerPreviewImmediate();
```
Hành động đổi seed thực chất đã kích hoạt lại hàm `triggerPreviewImmediate()`. Vào thời điểm đó, kho mẫu đã nạp xong từ trước, nên lượt render mới thành công rực rỡ.

### Quyết định kỹ thuật (Technical Decision 1)
- **Kích hoạt tự động khi nạp xong kho**: Ngay khi tiến trình `load_bank` hoàn thành trong `onWorkerReady()`, nếu ô soạn thảo có văn bản (`textarea.value.trim()`), hệ thống MUST tự động gọi `triggerPreviewImmediate()`.
- **Đánh dấu trạng thái kho đã nạp (Bank Hydrated Flag)**: Xuất khẩu một hàm thông báo `notifyBankReady()` hoặc gọi trực tiếp `triggerPreviewImmediate()` từ `write.js` để đồng bộ lại bản xem trước ngay khi kho sẵn sàng.

---

## 2. Đồng bộ hóa khi Chuyển Tab (Tab Switching Synchronization)

### Vấn đề (The Problem)
Trong `webapp/js/app.js`:
```javascript
// webapp/js/app.js:878-883
if (targetTab === "teach" && window.__teachController && window.__teachController.canvas) {
  window.__teachController.canvas.resize();
} else if (targetTab === "bank") {
  refreshBankView();
}
```
Khi người dùng chuyển sang Tab "Kho mẫu" (`targetTab === "bank"`), giao diện gọi `refreshBankView()`.
Khi người dùng chuyển sang Tab "Dạy chữ" (`targetTab === "teach"`), giao diện gọi `canvas.resize()`.
Tuy nhiên, khi người dùng chuyển sang Tab "Viết chữ" (`targetTab === "write"`), hệ thống **không làm gì cả**. Nếu người dùng vừa nạp file lưới `.xopp` thành công ở Tab Dạy chữ, hoặc vừa nạp file `.json.gz` ở Tab Kho mẫu, rồi chuyển về Tab Viết chữ, bản xem trước không tự cập nhật.

### Quyết định kỹ thuật (Technical Decision 2)
Trong `switchTab(targetTab)`:
```javascript
if (targetTab === "write") {
  if (typeof triggerPreviewImmediate === "function") {
    // Chỉ kích hoạt nếu có văn bản và trạng thái kho có sự thay đổi
    triggerPreviewImmediate();
  }
}
```
Bổ sung nhánh `targetTab === "write"` để kích hoạt làm mới bản xem trước khi người dùng quay lại soạn thảo, bảo đảm bản xem trước luôn hiển thị trạng thái mới nhất của kho mẫu.

---

## 3. Đồng bộ Đa Tab (Multi-Tab Sync) & Nhập Kho Mới (Import Sync)

### Vấn đề (The Problem)
1. **Đồng bộ đa tab qua BroadcastChannel**:
   Khi một tab khác lưu hoặc sửa kho mẫu, kênh `storage.getSyncChannel` nhận thông điệp `BANK_SYNCHRONIZED`:
   ```javascript
   // webapp/js/app.js:591-601
   if (profile && profile.data) {
     await sendWorkerMessage("load_bank", { gzBytes: Array.from(new Uint8Array(profile.data)), createIfMissing: false });
     if (typeof document !== "undefined" && document.getElementById("bank-summary")) {
       await refreshBankView();
     }
     if (typeof window !== "undefined" && window.__teachController) {
       await window.__teachController.refresh();
     }
   }
   ```
   Khối mã này cũng thiếu việc làm mới Tab Viết chữ.
2. **Nhập kho thủ công (`loadBankFromBytes`) & Nhập lưới (`import_grid`)**:
   Khi người dùng bấm "Nạp kho (.json.gz)" trong `bank.js` hoặc "Nạp lưới (.xopp)" trong `teach.js`, sau khi kho được cập nhật và lưu vào IndexedDB, Tab Viết chữ cũng cần được tự động kích hoạt làm mới nếu đang có văn bản trong ô soạn thảo.

### Quyết định kỹ thuật (Technical Decision 3)
- Bổ sung lời gọi `triggerPreviewImmediate()` vào callback của `BANK_SYNCHRONIZED` sau khi `load_bank` hoàn thành.
- Bổ sung thông báo cập nhật Tab Viết chữ khi `loadBankFromBytes` hoặc `import_grid` hoàn tất.

---

## 4. Ngăn ngừa Render Dồn Dập (Idempotency & Debouncing)

### Phân tích (Analysis)
Liệu việc gọi `triggerPreviewImmediate()` sau khi `load_bank` hoàn tất có gây giật lag hay xung đột với hành động gõ phím của người dùng?
Trong `webapp/js/write.js`, cơ chế **One Pending Request** đã được thiết kế sẵn:
```javascript
// webapp/js/write.js:156-161
async function requestRender(params) {
  if (isRendering) {
    hasPendingRequest = true;
    pendingParams = params;
    return;
  }
  ...
}
```
Nếu một yêu cầu kết xuất đang chạy (ví dụ do `initWriteTab` gọi trước đó trên kho rỗng), lời gọi `triggerPreviewImmediate()` từ `load_bank` sẽ được ghi nhận vào `pendingParams`. Ngay khi yêu cầu đầu tiên kết thúc trong khối `finally`, hệ thống sẽ tự động thực thi ngay `nextParams` với kho mẫu vừa nạp xong. Cơ chế này hoàn toàn tự nhiên, không gây nghẽn luồng và bảo đảm kết quả cuối cùng hiển thị trên màn hình luôn là kết quả chính xác nhất.
