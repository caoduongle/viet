# Contract: Concurrency & Storage Protocol (3-State OCC)

**Location**: `specs/042-sync-concurrency-worker-recovery/contracts/storage-concurrency-contract.md`  
**Target Module**: `webapp/js/storage.js`

---

## 1. `saveProfile(profile, expectedUpdatedAt)` Contract

### Signature
```typescript
function saveProfile(
  profile: { id: string; name: string; data?: any; updated_at?: number; [key: string]: any },
  expectedUpdatedAt?: number | null
): Promise<ProfileRecord>;
```

### Parameters
- `profile`: Đối tượng hồ sơ cần lưu. Trường `id` là bắt buộc.
- `expectedUpdatedAt`:
  - `number`: Kỳ vọng hồ sơ đang tồn tại với `updated_at === expectedUpdatedAt`.
  - `null`: Kỳ vọng hồ sơ hoàn toàn chưa tồn tại trong `profiles` store (khởi tạo mới lần đầu).
  - `undefined` (hoặc omitted): Ghi không điều kiện (bỏ qua kiểm tra phiên bản, chỉ dùng cho thao tác nạp đè kho mẫu chủ đích của người dùng).

### Behavior & Errors
1. Mở transaction `readwrite` trên store `"profiles"` qua `executeTransaction`.
2. Nếu `expectedUpdatedAt !== undefined`:
   - Thực hiện `store.get(profile.id)`.
   - Khi `getReq.onsuccess`:
     - Nếu `typeof expectedUpdatedAt === "number"`:
       - Nếu `!existing`: Hủy transaction (`tx.abort()`), báo lỗi `DOMException("...", "ConcurrencyConflictError")` kèm thông tin hồ sơ đã bị xóa bởi phiên khác (ngăn chặn tuyệt đối lỗi làm sống lại hồ sơ đã xóa).
       - Nếu `existing.updated_at !== expectedUpdatedAt`: Hủy transaction (`tx.abort()`), báo lỗi `DOMException("...", "ConcurrencyConflictError")` ("Hồ sơ đã bị cập nhật bởi phiên khác").
     - Nếu `expectedUpdatedAt === null`:
       - Nếu `existing`: Hủy transaction (`tx.abort()`), báo lỗi `DOMException("...", "ConcurrencyConflictError")` ("Hồ sơ đã tồn tại, không thể khởi tạo mới đồng thời").
     - Đảm bảo tính đơn điệu chặt của dấu thời gian (`monotonic timestamp`):
       - `payload.updated_at = Math.max(payload.updated_at, existing ? existing.updated_at + 1 : 1)` để ngăn chặn hai lần lưu liên tiếp trong cùng một mili-giây (`Date.now()`) có cùng giá trị `updated_at`.
   - Gọi `store.put(payload)`.
3. Nếu `expectedUpdatedAt === undefined`:
   - Gọi `store.put(payload)` trực tiếp.
4. Resolve `payload` chỉ khi `tx.oncomplete`.

---

## 2. `syncAndSaveActiveProfile(sendWorkerFn, maxRetries = 3)` Contract

### Signature
```typescript
function syncAndSaveActiveProfile(
  sendWorkerFn: (method: string, params: any) => Promise<any>,
  maxRetries?: number
): Promise<ProfileRecord>;
```

### Behavior & Errors
1. Lấy `activeId` từ `getSetting("active_profile_id", "default_profile")`.
2. Bọc toàn bộ trong `requestProfileLock(activeId, async () => { ... })`.
3. Vòng lặp `attempt = 0` đến `maxRetries - 1`:
   - Đọc `currentProfile = await getProfile(activeId)`.
   - **Kiểm tra hồ sơ đã bị xóa ở tab khác**:
     - Nếu `!currentProfile` VÀ `localSyncedTimestamp > 0` (tab hiện tại đã từng nạp/đồng bộ hồ sơ này trước đó, nhưng nay hồ sơ đã bị xóa khỏi IndexedDB):
       - Lập tức ném `DOMException("Hồ sơ đang đồng bộ đã bị xóa bởi một tab khác.", "ConcurrencyConflictError")` (với `err.codeName = "ProfileDeletedConflictError"`) và **dừng ngay vòng lặp thử lại**, tuyệt đối không gán `baseUpdatedAt = null` để tái tạo lại hồ sơ đã xóa.
   - Xác định kỳ vọng phiên bản:
     - `baseUpdatedAt = currentProfile ? currentProfile.updated_at : null`.
   - Nạp dữ liệu từ đĩa để hợp nhất nếu:
     - `currentProfile && currentProfile.data && (currentProfile.updated_at > localSyncedTimestamp || attempt > 0)`
     - Khi đó `diskGzBytes = Array.from(new Uint8Array(currentProfile.data))`.
   - Gọi `mergedBytes = await sendWorkerFn("sync_save", { diskGzBytes })`.
   - Tạo `updatedProfile` với `data = mergedBytes`, `updated_at = Date.now()`.
   - Gọi `savedProfile = await saveProfile(updatedProfile, baseUpdatedAt)`.
   - Gán `localSyncedTimestamp = savedProfile.updated_at`.
   - Phát `broadcastBankSync(activeId)`.
   - Return `savedProfile`.
   - Bắt lỗi trong `catch (err)`:
     - Nếu `err.name === "ConcurrencyConflictError"` và `err.codeName !== "ProfileDeletedConflictError"`:
       - Nếu `attempt < maxRetries - 1`:
         - Kiểm tra lại `fresh = await getProfile(activeId)`.
         - Nếu `!fresh` (hồ sơ vừa bị tab khác xóa ngay giữa lúc worker đang `sync_save`):
           - Ném lỗi `ConcurrencyConflictError` (`codeName = "ProfileDeletedConflictError"`), dừng retry ngay lập tức.
         - Tiếp tục vòng lặp retry (`attempt++`).
       - Nếu đã hết số lần retry: ném lỗi `err`.
     - Nếu lỗi khác: ném `err` ngay.

---

## 3. `executeTransaction()` Synchronous Error Safety Contract

### Signature
```typescript
function executeTransaction<T>(
  db: IDBDatabase,
  storeNames: string | string[],
  mode: "readonly" | "readwrite",
  operationFn: (store: IDBObjectStore | null, tx: IDBTransaction, onError: (err: any) => void) => T
): Promise<T>;
```

### Safety Guarantee
- Nếu `operationFn` ném ra ngoại lệ đồng bộ (sync throw) sau khi đã xếp hàng một hoặc nhiều request vào `tx`:
  - Khối `catch (err)` **BẮT BUỘC** gọi `try { tx.abort(); } catch (_) {}` trước khi gọi `safeReject(err)`.
  - Đảm bảo mọi request đã xếp hàng trước thời điểm ném lỗi đều bị hủy bỏ hoàn toàn (không bao giờ được commit xuống đĩa) và Promise trả về bị reject bằng đúng ngoại lệ đồng bộ `err`.
