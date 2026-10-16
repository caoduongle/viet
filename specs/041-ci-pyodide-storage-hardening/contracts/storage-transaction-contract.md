# Interface Contract: Storage Transaction & Locking Protocol

**Document**: `storage-transaction-contract.md`  
**Feature**: `041-ci-pyodide-storage-hardening`  
**Consumer**: `webapp/js/storage.js`, `webapp/js/app.js`, Multi-tab E2E Tests  

---

## 1. Hợp đồng Giao dịch Ghi dữ liệu (Durable Write Guarantees)

Mọi phương thức ghi vào IndexedDB trong `storage.js` (`saveProfile`, `setSetting`, `deleteProfile`) phải tuân thủ hợp đồng cam kết bền vững:

```typescript
function saveProfile(profile: ProfileRecord, expectedUpdatedAt?: number): Promise<ProfileRecord>;
function setSetting(key: string, value: any): Promise<boolean>;
function deleteProfile(profileId: string): Promise<boolean>;
```

### Các điều kiện cam kết:
1. **Cam kết Commit (Post-Condition)**:
   - Promise chỉ được `resolve()` sau khi sự kiện `tx.oncomplete` kích hoạt.
   - Khi Promise trả về giá trị, dữ liệu được bảo đảm 100% đã được ghi vào hệ thống lưu trữ bền vững của trình duyệt.
2. **Cam kết Bắt lỗi và Hủy bỏ (Error & Abort Handlers)**:
   - Wrapper transaction phải lưu vết lỗi cấp request `lastRequestError = req.error`.
   - Khi xảy ra `tx.onerror` hoặc `tx.onabort`, Promise bị từ chối với `tx.error || lastRequestError || new DOMException("Giao dịch bị hủy", "AbortError")`.
   - Nếu lỗi cấp request là `QuotaExceededError`, thuộc tính `name === "QuotaExceededError"` bắt buộc phải được bảo toàn nguyên vẹn để tầng trên bắt và hiển thị cảnh báo dung lượng (`showQuotaWarning`).
3. **Tính toàn vẹn Dấu thời gian (Timestamp Invariance)**:
   - `saveProfile(profile)` chỉ sinh `updated_at: Date.now()` nếu bản ghi chưa có sẵn dấu thời gian, hoặc cập nhật và trả về chính xác bản ghi đã lưu vào IndexedDB.
   - `syncAndSaveActiveProfile` cập nhật `localSyncedTimestamp = savedProfile.updated_at` ngay sau khi lưu thành công, triệt tiêu 100% hiện tượng tự đồng bộ lặp lại.

---

## 2. Hợp đồng Khóa Tuần tự hóa & Kiểm soát Cạnh tranh (Concurrency Control)

```typescript
function requestProfileLock<T>(profileId: string, taskFn: () => Promise<T>): Promise<T>;
```

### Yêu cầu thực thi:
1. **Trường hợp Trình duyệt hỗ trợ Web Locks API**:
   - Sử dụng `navigator.locks.request("chuviettay_lock_" + profileId, taskFn)` để điều phối giữa các tab.
2. **Trường hợp Trình duyệt thiếu Web Locks API (Fallback via In-Memory Queue + OCC)**:
   - **Nội bộ Tab**: Duy trì chuỗi Promise `tabLockChain = tabLockChain.then(() => taskFn())` để tuần tự hóa các tác vụ ghi trên cùng một tab, ngăn chặn xung đột in-flight.
   - **Liên Tab (Optimistic Concurrency Control)**:
     - `saveProfile(profile, expectedUpdatedAt)`: nếu `expectedUpdatedAt` được truyền vào, transaction `readwrite` sẽ đọc bản ghi hiện tại từ store; nếu bản ghi đã tồn tại và `currentRecord.updated_at !== expectedUpdatedAt`, transaction lập tức abort và ném `ConcurrencyConflictError`.
     - Trong `syncAndSaveActiveProfile()`, khi gặp `ConcurrencyConflictError`, hàm tự động đọc lại hồ sơ mới nhất từ IndexedDB, nạp vào Worker để hợp nhất lại và thử lưu lại (tối đa 3 lần) trước khi báo lỗi.
