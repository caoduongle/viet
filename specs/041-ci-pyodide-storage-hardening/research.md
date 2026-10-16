# Research & Technical Decisions: CI Pyodide Golden Master Fix, Storage Hardening & Worker Resilience

**Feature**: `041-ci-pyodide-storage-hardening`  
**Date**: 2026-10-16  
**Status**: Completed  

---

## 1. Pyodide Golden Master Verification & Diagnostics (`scripts/test_golden_pyodide.mjs`)

### Vấn đề thực tế (Root Cause Analysis)
Khi thực thi `node scripts/test_golden_pyodide.mjs`, quy trình CI thất bại tại ca kiểm thử `markdown_list`:
```text
[FAIL] markdown_list:
       Kỳ vọng: 46ce78d8a571216dd549e3557e53ef711679a7863cbef17ff5cfdf776bc3c4b9
       Nhận:    46ce78d8a571216dd549e3557e53ef711679a7863cbef17ff5cfdf776bc3c4b9
```
Mã băm thực tế và mã băm kỳ vọng được in ra hoàn toàn trùng khớp từng ký tự, nhưng bài kiểm thử vẫn bị đánh dấu là `FAIL`.

**Nguyên nhân gốc rễ**:
1. Trong `scripts/test_golden_pyodide.mjs` (dòng 180):
   ```python
   res_l = ctl_l.write_document(doc_l, WriteOptions(seed=19), out_l)
   ```
   Lời gọi này **không** truyền `missing_grid=True`.
2. Từ Feature 040, tùy chọn `missing_grid` trong `WriteOptions` được mặc định là `False` (để tối ưu hóa không sinh tệp phụ khi không cần thiết). Do đó, `res_l.missing_grid_path` nhận giá trị `None`.
3. Trong `tests/test_golden_master_real_path.py` (dòng 136), ca CPython thực thi:
   ```python
   result = ctl.write_document(doc, WriteOptions(seed=19, missing_grid=True), out)
   ```
4. Đoạn kiểm tra trong Pyodide (dòng 183-186) thực hiện:
   ```python
   thieu_l_ok = False
   if res_l.missing_grid_path and sha(res_l.missing_grid_path) == GOLDEN_REAL["markdown_list"]["thieu"]:
       thieu_l_ok = True
   test_results.append(("markdown_list", (xopp_l_sha == exp_l) and thieu_l_ok, xopp_l_sha, exp_l))
   ```
   Vì `res_l.missing_grid_path` là `None`, `thieu_l_ok` là `False`, dẫn đến biểu thức điều kiện `(xopp_l_sha == exp_l) and thieu_l_ok` nhận giá trị `False`.
5. Khi kết quả được chuyển về JavaScript:
   `test_results` chỉ ghi nhận tuple 4 phần tử `(name, passed, actualSha, expectedSha)`, trong đó `actualSha` và `expectedSha` là của tệp chính `out_l`. Vòng lặp báo cáo in ra `actualSha` và `expectedSha` của tệp chính, tạo ra hiện tượng "cùng hash nhưng báo FAIL" và che giấu hoàn toàn lỗi thực sự là tệp `_thieu.xopp` không được tạo.

### Quyết định kỹ thuật
- **Quyết định 1**: Cấu hình `WriteOptions(seed=19, missing_grid=True)` cho ca `markdown_list` trong `scripts/test_golden_pyodide.mjs` để đồng bộ 100% với kịch bản CPython chuẩn trong `tests/test_golden_master_real_path.py`.
- **Quyết định 2**: Tái cấu trúc cấu trúc dữ liệu kết quả kiểm tra `GoldenTestResult` trong `test_golden_pyodide.mjs`. Thay vì nén mọi thứ vào một tuple 4 phần tử, kết quả trả về sẽ phân định rõ:
  - `name`: Tên ca kiểm thử.
  - `main`: `{ ok, expectedSha, actualSha, fileExists, length }`
  - `grid`: `{ required, ok, expectedSha, actualSha, fileExists, path, length }`
- **Quyết định 3**: Định dạng thông báo chẩn đoán rõ ràng:
  - Nếu tệp không tồn tại: in rõ `[THIẾU TỆP: <đường_dẫn>]`.
  - Nếu tệp sai mã băm: in rõ mã băm mong đợi, mã băm thực tế, dung lượng byte và kiểu dữ liệu.
  - Không bao giờ dùng mã băm tệp chính để đại diện cho lỗi tệp phụ.

### Các phương án đã cân nhắc
- *Phương án loại bỏ*: Bỏ qua kiểm tra `_thieu.xopp` trong Pyodide. **Bác bỏ** vì vi phạm nguyên tắc bảo đảm tính tương thích Golden Master giữa CPython và WebAssembly.
- *Phương án loại bỏ*: Sửa hash kỳ vọng cho khớp. **Bác bỏ** vì hash tệp chính vốn dĩ đã khớp 100%, vấn đề là thiếu tùy chọn `missing_grid=True` và cấu trúc chẩn đoán bị gộp.

---

## 2. IndexedDB Transaction Lifecycle & Multitab Sync (`webapp/js/storage.js`)

### Vấn đề thực tế
1. **Transaction Commit Semantics**:
   - Trong `storage.js`: `saveProfile()`, `setSetting()`, `deleteProfile()` gọi `resolve()` ngay trong sự kiện `req.onsuccess`.
   - Trong tiêu chuẩn W3C IndexedDB, `req.onsuccess` chỉ biểu thị thao tác đã được tiếp nhận vào transaction. Dữ liệu chỉ thực sự được ghi bền vững xuống đĩa khi transaction kích hoạt `tx.oncomplete`.
   - Nếu transaction bị hủy ngang (`tx.onabort`), ví dụ do vượt quá dung lượng lưu trữ (`QuotaExceededError`) hoặc lỗi hệ thống tệp, `req.onsuccess` vẫn có thể đã kích hoạt trước đó, khiến ứng dụng báo "Đã lưu" giả mạo trong khi dữ liệu thực tế bị hủy bỏ.
2. **Lệch dấu thời gian đồng bộ (`localSyncedTimestamp` Drift)**:
   - Trong `syncAndSaveActiveProfile()`, hàm tạo `const now = Date.now()` rồi gán vào `updatedProfile.updated_at = now`.
   - Sau đó gọi `await saveProfile(updatedProfile)`.
   - Trong `saveProfile(profile)`, hàm lại thực thi `updated_at: Date.now()`.
   - Cuối cùng, `syncAndSaveActiveProfile()` gán `localSyncedTimestamp = now` (giá trị cũ ở bước 1).
   - Nếu `saveProfile` gán timestamp mới hơn dù chỉ 1ms, ở lần kiểm tra tiếp theo `currentProfile.updated_at > localSyncedTimestamp` sẽ trả về `true`. Tab đó sẽ tự coi thay đổi do chính mình vừa ghi là dữ liệu ngoại lai đến từ tab khác và kích hoạt hợp nhất lặp lại thừa thãi.
3. **Mất khóa khi trình duyệt thiếu Web Locks API**:
   - `requestProfileLock()` chỉ kiểm tra `if (navigator.locks && navigator.locks.request)`. Nếu không có, hàm chạy thẳng `taskFn()` mà không có bất kỳ rào chắn nào.
   - Khi người dùng dùng trình duyệt không hỗ trợ Web Locks hoặc môi trường nhúng, nhiều tab hoặc nhiều thao tác bất đồng bộ cùng lúc có thể ghi đè dữ liệu kho mẫu.

### Quyết định kỹ thuật
- **Quyết định 1 (Transaction Promise Wrapper)**:
  Xây dựng hàm tiện ích nội bộ thực thi transaction có bảo đảm hoàn tất:
  ```javascript
  function executeTransaction(db, storeNames, mode, operationFn) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeNames, mode);
      let result = undefined;

      tx.oncomplete = () => resolve(result);
      tx.onerror = () => reject(tx.error || new Error("Lỗi giao dịch IndexedDB"));
      tx.onabort = () => reject(tx.error || new Error("Giao dịch IndexedDB bị hủy bỏ"));

      try {
        const store = tx.objectStore(storeNames);
        result = operationFn(store, tx);
      } catch (err) {
        reject(err);
      }
    });
  }
  ```
  Mọi thao tác ghi (`saveProfile`, `setSetting`, `deleteProfile`) bắt buộc phải chờ `tx.oncomplete`.
- **Quyết định 2 (Timestamp Consistency)**:
  `saveProfile(profile)` giữ nguyên `updated_at` nếu đã được truyền vào, hoặc chỉ sinh một lần duy nhất nếu chưa có, và trả về bản ghi lưu trữ cuối cùng. `syncAndSaveActiveProfile()` cập nhật:
  ```javascript
  const savedProfile = await saveProfile(updatedProfile);
  localSyncedTimestamp = savedProfile.updated_at;
  return savedProfile;
  ```
- **Quyết định 3 (Web Locks Fallback Mechanism)**:
  - Khi không có `navigator.locks`:
    - Ở cấp độ nội bộ tab: Duy trì một chuỗi Promise (`inMemoryLockQueue`) để tuần tự hóa mọi yêu cầu truy xuất kho mẫu trên tab đó.
    - Ở cấp độ đa tab: Triển khai cơ chế cooperative lease lock trong store `app_settings` của IndexedDB với khóa `_lock_${profileId}` chứa `{ ownerId, expiresAt }`. Mỗi tab sinh một `tabId` ngẫu nhiên khi khởi tạo. Thao tác xin khóa đọc bản ghi lease; nếu khóa trống hoặc `expiresAt < Date.now()`, tab ghi đè lease (hạn 5000ms). Nếu khóa đang bị chiếm, tab chờ với thuật toán exponential backoff (tối đa 3000ms). Khi hoàn thành, tab xóa lease nếu `ownerId` còn khớp.

---

## 3. Web Worker Request Lifecycle & DOCX Wheel Loading (`webapp/js/app.js`, `py-worker.js`)

### Vấn đề thực tế
1. **Thiếu cơ chế Timeout cho `sendWorkerMessage`**:
   - `pendingRequests` lưu trữ `{ resolve, reject }` theo `id`. Nếu Worker bị quá tải, tính toán vòng lặp vô hạn, hoặc WebAssembly bị treo, Promise vĩnh viễn không được giải quyết. Giao diện bị kẹt ở trạng thái "Đang lưu..." hoặc "Đang xử lý...".
2. **Thiếu xử lý `worker.onerror` và `worker.onmessageerror`**:
   - Nếu Web Worker gặp uncaught exception (ví dụ OOM do Pyodide cấp phát bộ nhớ vượt giới hạn trình duyệt), luồng chính không nhận được thông báo. Tất cả các `pendingRequests` treo lại.
3. **Bỏ qua lỗi mạng khi nạp wheel DOCX tải lười trong `py-worker.js`**:
   - Trong `py-worker.js` dòng 273: `if (resp.ok) { ... }`.
   - Nếu `fetch()` trả về 404 hoặc lỗi mạng, vòng lặp lẳng lặng bỏ qua và tiếp tục gọi `_bridge.import_docx()`. Python sau đó ném lỗi `ModuleNotFoundError: No module named 'docx'`, khiến người dùng và lập trình viên không biết nguyên nhân thực sự là do wheel không tải được.

### Quyết định kỹ thuật
- **Quyết định 1 (Worker Request Timeout)**:
  Thêm tham số `timeoutMs` (mặc định 60.000ms cho các thao tác nặng, có thể cấu hình) vào `sendWorkerMessage()`. Sử dụng `setTimeout`: khi hết hạn, xóa yêu cầu khỏi `pendingRequests` và reject với lỗi `TimeoutError: Yêu cầu xử lý Worker đã hết hạn sau ${timeoutMs}ms`.
- **Quyết định 2 (Worker Error Event Listeners)**:
  Trong `initWorker()`:
  ```javascript
  worker.onerror = (err) => handleWorkerFatalError("Worker encountered an unhandled error", err);
  worker.onmessageerror = (err) => handleWorkerFatalError("Worker failed to deserialize message", err);
  ```
  Hàm `handleWorkerFatalError` duyệt qua toàn bộ `pendingRequests`, reject tất cả với thông báo lỗi, dọn sạch map, và hiển thị thanh cảnh báo lỗi trên giao diện với nút "Khởi động lại / Thử lại".
- **Quyết định 3 (Fail-Fast DOCX Wheel Fetching)**:
  Trong `py-worker.js`, kiểm tra phản hồi HTTP nghiêm ngặt:
  ```javascript
  let resp;
  try {
    resp = await fetch(whlUrl);
  } catch (netErr) {
    throw new Error(`Lỗi kết nối mạng khi tải thư viện ${whl}: ${netErr.message}`);
  }
  if (!resp.ok) {
    throw new Error(`Không thể tải thư viện ${whl}: Máy chủ phản hồi mã lỗi HTTP ${resp.status} (${resp.statusText})`);
  }
  ```
  Chỉ thêm vào `loadedWheels` sau khi giải nén zip thành công vào site-packages. Nếu có bất kỳ lỗi nào, dừng ngay quy trình và trả lỗi chi tiết về giao diện.

---

## 4. DOM Safety in LaTeX Symbol Modal & Documentation Alignment

### Vấn đề thực tế
1. **Nội suy chuỗi vào innerHTML trong `webapp/js/write.js`**:
   - Dòng 837: `catDiv.innerHTML = \`<div style="font-weight: 600; margin-bottom: 0.35rem; color: var(--text-primary);">${catName}</div>\`;`
   - Dòng 860: `container.innerHTML = \`<div>Lỗi tải ký hiệu: ${err.message}</div>\`;`
   - Dù `catName` và `err.message` hiện tại bắt nguồn từ dữ liệu nội bộ, việc đưa trực tiếp chuỗi thô vào `innerHTML` vi phạm nguyên tắc phòng thủ theo chiều sâu (Defense-in-Depth) và tiêu chuẩn an toàn DOM được quy định trong dự án.
2. **Lệch thông tin phiên bản Python giữa tài liệu và CI**:
   - `README.md` dòng 32 ghi: `Python 3.10+ (đã kiểm thử tự động trên CI với Python 3.10, 3.11, 3.12, 3.13)`.
   - Tuy nhiên, cấu hình CI thực tế (`.github/workflows/ci.yml`):
     - `test-core` chạy ma trận: Python 3.12, 3.13.
     - `test-python-314` chạy Python 3.14.
     - `.python-version` chỉ định Python 3.13.5.
     - `pyproject.toml` khai báo: `requires-python = ">=3.10"` và classifiers từ 3.10 đến 3.14.
   - Cần đồng bộ hóa để tài liệu phản ánh chính xác ma trận kiểm thử thực tế trên CI.

### Quyết định kỹ thuật
- **Quyết định 1 (Safe DOM Construction)**:
  Tái cấu trúc `loadLatexSymbols()` sử dụng `document.createElement()`, `element.textContent`, và `container.replaceChildren()`, loại bỏ 100% việc gán chuỗi động vào `innerHTML`.
- **Quyết định 2 (Version Matrix Synchronization)**:
  - Cập nhật `README.md`: Nêu rõ `Python 3.10+` là yêu cầu tương thích tối thiểu của mã nguồn, và ma trận CI tự động kiểm thử chính thức trên các phiên bản hiện đại: `Python 3.12, 3.13` (Core) và `Python 3.14` (Future-proofing).
  - Giữ nguyên cấu hình `pyproject.toml` (`requires-python = ">=3.10"`) để đảm bảo thư viện có thể cài đặt trên các môi trường Python 3.10+.
