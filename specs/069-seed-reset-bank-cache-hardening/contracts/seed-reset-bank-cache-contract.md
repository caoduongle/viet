# Contract: Thông điệp Xóa Lịch sử Hạt giống và Giao diện Bộ nhớ đệm Kho mẫu

Tài liệu này xác lập hợp đồng giao tiếp giữa các thành phần phần mềm liên quan đến việc đặt lại lịch sử hạt giống và quản lý bộ nhớ đệm kho mẫu.

---

## 1. Web Worker Message Contract: `clear_document_history`

### Yêu cầu (Request từ Main Thread gửi xuống Web Worker)
```json
{
  "id": 1042,
  "action": "clear_document_history"
}
```

### Phản hồi thành công (Response từ Web Worker trả về Main Thread)
```json
{
  "id": 1042,
  "ok": true
}
```

### Phản hồi thất bại (Error Response)
```json
{
  "id": 1042,
  "ok": false,
  "error": "Mô tả nguyên nhân lỗi"
}
```

---

## 2. Python BrowserBridge Contract: `clear_document_history`

### Phương thức
```python
def clear_document_history(self) -> dict[str, Any]:
    """Đặt lại tài liệu và hạt giống đã căn chỉnh của lượt trước trong AppController."""
```

### Kết quả trả về
- Thành công: `{"ok": True}`
- Thất bại: `{"ok": False, "error": "<chuỗi lỗi>"}`

---

## 3. Web Client Interface Contract: `write.js` Trigger Points

### 1. Khi người dùng xóa trắng ô soạn thảo (`triggerPreviewImmediate`)
```javascript
const text = textarea.value;
if (!text.trim()) {
  clearPreview();
  sendWorkerMessage("clear_document_history").catch((e) => console.warn("Lỗi xóa lịch sử seed:", e));
  return;
}
```

### 2. Khi người dùng mở tệp tài liệu mới (`handleFileImport`)
```javascript
async function handleFileImport(file, textarea) {
  // Xóa lịch sử đối chiếu của tài liệu cũ trước khi nạp tệp mới
  await sendWorkerMessage("clear_document_history").catch((e) => console.warn("Lỗi xóa lịch sử seed khi mở file:", e));
  
  // Nạp nội dung mới và kết xuất
  // ...
  triggerPreviewImmediate();
}
```

---

## 4. Web Client Interface Contract: `bank.js` Two-Phase Cache Commit

### Thuật toán cập nhật `refreshBankView(force = false)`:
```javascript
let lastBankSnapshotCache = { epoch: null, revision: null, profileId: null };

export async function refreshBankView(force = false) {
  try {
    await updateProfileChip();
    const activeProfileId = (await storage.getSetting("active_profile_id", "default_profile")) || "default_profile";

    const snapRes = await sendWorkerFn("get_bank_snapshot", { profileId: activeProfileId });
    if (!snapRes || !snapRes.ok) {
      showBankErrorBanner(`Lỗi tải kho mẫu: ${snapRes?.error || "Không thể nạp dữ liệu kho mẫu"}`);
      return;
    }
    showBankErrorBanner(null);

    const snapshot = snapRes.data || {};
    const rev = snapshot.revision;
    const epoch = snapshot.worker_epoch || "";

    // 1. Kiểm tra cache
    if (
      !force &&
      lastBankSnapshotCache.epoch === epoch &&
      lastBankSnapshotCache.revision === rev &&
      lastBankSnapshotCache.profileId === activeProfileId
    ) {
      return;
    }

    const pendingCacheKey = { epoch, revision: rev, profileId: activeProfileId };

    // 2. Chuẩn bị dữ liệu hiển thị
    allBankItems = [];
    // ... tổng hợp snapshot.letters, symbols, marks ...

    // 3. Thực hiện dựng giao diện DOM
    applyFiltersAndRender();

    // 4. CHỈ cam kết cache khi bước 3 hoàn tất thành công
    lastBankSnapshotCache = pendingCacheKey;
  } catch (err) {
    // Vô hiệu hóa cache khi có bất kỳ ngoại lệ nào xảy ra
    lastBankSnapshotCache = { epoch: null, revision: null, profileId: null };
    console.error("Lỗi refreshBankView:", err);
    showBankErrorBanner(`Lỗi hiển thị kho mẫu: ${err.message}`);
  }
}
```
