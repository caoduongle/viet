# Contract: Đồng Bộ Hóa Bản Xem Trước Theo Số Hiệu Phiên Bản Kho Mẫu

**Feature**: [054-repo-audit-hardening](../spec.md)  
**Target Module**: `webapp/js/write.js`  

---

## 1. Mục đích
Quy định cơ chế quản lý trạng thái đồng bộ giữa kho mẫu trong Web Worker và giao diện xem trước (Tab Viết) bằng số hiệu phiên bản tăng đơn điệu (`bankRevision`), loại bỏ race condition khi render bị lỗi hoặc bị chen ngang.

## 2. Đặc tả Biến Trạng Thái & Hàm Công Khai

```javascript
// Số hiệu phiên bản kho mẫu hiện hành
let bankRevision = 1;
// Số hiệu phiên bản kho mẫu của bản vẽ đang hiển thị
let lastRenderedRevision = 0;
// Cờ báo hiệu giao diện chưa phản ánh kho mới nhất
let isBankDirty = false;

export function notifyBankUpdated(details = {}) {
  // Tăng bankRevision đơn điệu và đánh dấu isBankDirty = true
}

export function getWritePreviewSyncState() {
  return {
    isBankDirty,
    bankRevision,
    lastRenderedRevision,
    // ... các trường hiện có
  };
}

export function resetWriteSyncStateForTesting() {
  isBankDirty = false;
  bankRevision = 1;
  lastRenderedRevision = 0;
  // ... reset các trường khác
}
```

## 3. Các Quy tắc Xử lý Tranh chấp (Concurrency Invariants)

1. **Monotonic Revision Increment**:
   - Bất kỳ hành động nạp kho mẫu, dạy thêm mẫu chữ, hoặc đồng bộ hóa kho từ tab khác đều PHẢI tăng `bankRevision++` và đặt `isBankDirty = true`.
2. **Request Revision Snapshotting**:
   - Khi `requestRender(params)` bắt đầu thực thi yêu cầu `sendWorkerMessage("write_text")`, tác vụ PHẢI chụp lại phiên bản kho tại thời điểm gửi: `const reqRev = bankRevision;`.
3. **Strict In-Sync Assertion**:
   - Khi kết quả `res.ok` trả về thành công:
     `lastRenderedRevision = reqRev;`
     - Nếu `reqRev === bankRevision`: Đặt `isBankDirty = false`.
     - Nếu `reqRev < bankRevision` (có cập nhật mới phát sinh trong lúc đang render): Giữ nguyên `isBankDirty = true`.
4. **Failure Preservation**:
   - Nếu yêu cầu render trả về lỗi (`res.ok === false`) hoặc bị reject/timeout:
     - Giữ nguyên `isBankDirty = true`.
     - Không cập nhật `lastRenderedRevision`.
5. **Test Isolation**:
   - Hàm `resetWriteSyncStateForTesting()` đặt lại `bankRevision = 1` và `lastRenderedRevision = 0` để cô lập hoàn toàn giữa các ca kiểm thử đơn vị.
