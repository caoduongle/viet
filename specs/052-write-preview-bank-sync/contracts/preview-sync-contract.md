# Contract: Giao Tiếp Đồng Bộ Giữa Bộ Điều Phối Ứng Dụng (app.js) và Tab Viết Chữ (write.js)

## 1. Export Interface từ `webapp/js/write.js`

Module `write.js` cung cấp các phương thức và thông số đồng bộ phục vụ cho `app.js`:

```javascript
/**
 * Yêu cầu kết xuất ngay lập tức nội dung hiện tại của editor-text.
 * Được gọi khi:
 * 1. Kho mẫu hoàn tất nạp từ IndexedDB vào Web Worker.
 * 2. Người dùng chuyển về Tab Viết chữ (switchTab("write")).
 * 3. Đồng bộ đa tab qua BroadcastChannel (BANK_SYNCHRONIZED).
 * 4. Người dùng thay đổi tùy chọn viết chữ (seed, font size, paper...).
 */
export function triggerPreviewImmediate(): void;

/**
 * Trả về thông tin trạng thái đồng bộ hiện hành của Tab Viết chữ.
 */
export function getWritePreviewSyncState(): {
  hasText: boolean;
  isRendering: boolean;
  hasRendered: boolean;
};
```

---

## 2. Quy ước Tương Tác Trong `webapp/js/app.js`

### 2.1. Sau khi `load_bank` hoàn thành trong `onWorkerReady()`:
```javascript
// Sau khi load_bank vào worker thành công:
if (profile && profile.data) {
  storage.setLocalSyncedTimestamp(profile.updated_at || Date.now());
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
  // BẮT BUỘC: Làm mới bản xem trước Tab Viết chữ nếu có văn bản
  if (typeof document !== "undefined") {
    const editorText = document.getElementById("editor-text");
    if (editorText && editorText.value.trim()) {
      triggerPreviewImmediate();
    }
  }
}
```

### 2.2. Khi chuyển tab sang "Viết chữ" (`switchTab`):
```javascript
export function switchTab(targetTab) {
  ...
  if (targetTab === "teach" && window.__teachController && window.__teachController.canvas) {
    window.__teachController.canvas.resize();
  } else if (targetTab === "bank") {
    refreshBankView();
  } else if (targetTab === "write") {
    const editorText = document.getElementById("editor-text");
    if (editorText && editorText.value.trim()) {
      triggerPreviewImmediate();
    }
  }
}
```

### 2.3. Khi nhận tín hiệu đồng bộ đa tab (`BANK_SYNCHRONIZED`):
```javascript
storage.getSyncChannel(async (msg) => {
  if (msg.type === "BANK_SYNCHRONIZED") {
    const activeId = await storage.getSetting("active_profile_id", "default_profile");
    if (msg.profileId === activeId) {
      ...
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
        // BẮT BUỘC: Cập nhật Tab Viết chữ
        if (typeof document !== "undefined") {
          const editorText = document.getElementById("editor-text");
          if (editorText && editorText.value.trim()) {
            triggerPreviewImmediate();
          }
        }
      }
    }
  }
});
```
