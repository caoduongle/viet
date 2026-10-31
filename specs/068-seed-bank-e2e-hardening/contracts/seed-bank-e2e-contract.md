# Interface Contracts: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

Tài liệu này xác lập các hợp đồng giao tiếp (API & message contracts) giữa các tầng: Python Core (`AppController`, `Document IR`), Cầu nối Web (`BrowserBridge`), Luồng xử lý nền (`Web Worker`) và Giao diện người dùng (`bank.js`, `storage.js`).

---

## 1. Cầu nối Python: `BrowserBridge.get_bank_snapshot`

### Chữ ký hàm
```python
def get_bank_snapshot(self, profile_id: str = "default") -> dict[str, Any]
```

### Tham số đầu vào
- `profile_id` (`str`, mặc định `"default"`): Định danh của hồ sơ lưu trữ cần lấy bản chụp.

### Cấu trúc kết quả thành công (`ok == True`)
```json
{
  "ok": true,
  "data": {
    "revision": 3,
    "worker_epoch": "b78b8772-c28f-4d92-b413-568eb2a3b04c",
    "profile_id": "default_profile",
    "stats": {
      "n_words": 150,
      "n_letters": 65,
      "n_samples": 420,
      "digit_counts": { "0": 2, "1": 3 },
      "punct_counts": { ".": 5, ",": 4 }
    },
    "letters": [["a", 4], ["b", 3], ["c", 5]],
    "digits": { "0": 2, "1": 3 },
    "punct": { ".": 5, ",": 4 },
    "symbols": [["\\alpha", 2], ["\\le", 1]],
    "marks": [["acute", 10], ["grave", 8]]
  }
}
```

### Cấu trúc kết quả thất bại (`ok == False`)
```json
{
  "ok": false,
  "error": "Mô tả nguyên nhân lỗi cụ thể từ truy vấn con (vd: Kho mẫu chưa được nạp hoặc tệp hỏng)"
}
```

---

## 2. Bộ điều khiển trung tâm: `AppController.write_document`

### Chữ ký hàm
```python
def write_document(
    self,
    document: Document,
    opts: WriteOptions,
    out_path: str,
    token_layout_callback: Callable[[TokenBox], None] | None = None,
) -> WriteResult
```

### Hành vi nghiệp vụ
1. Nếu `opts.stable_variants is True`:
   - Kiểm tra `self._last_doc` và `self._last_seed`.
   - Nếu `self._last_doc is not None` và `self._last_seed == opts.seed`:
     Gọi `document = align_document_seeds(self._last_doc, document)`.
   - Tiến hành kết xuất qua `DocumentLayoutEngine`.
   - Sau khi kết xuất thành công:
     `self._last_doc = document`
     `self._last_seed = opts.seed`
2. Nếu `opts.stable_variants is False` hoặc `self._last_seed != opts.seed`:
   - Kết xuất trực tiếp tài liệu mới.
   - Cập nhật `self._last_doc = document`, `self._last_seed = opts.seed`.

### Hàm hỗ trợ xóa lịch sử
```python
def clear_document_history(self) -> None:
    """Xóa bỏ tài liệu và seed của lượt trước, đặt lại trạng thái đối chiếu hạt giống."""
    self._last_doc = None
    self._last_seed = None
```
*Lưu ý*: Hàm này được tự động gọi bên trong `AppController.load_bank()` để tránh ô nhiễm ngữ cảnh biến thể khi người dùng nạp kho mẫu mới.

---

## 3. Web Worker Contract: `sync_save` & `get_bank_snapshot`

### A. Message `sync_save`
- **Gửi từ Main Thread sang Worker**:
  ```javascript
  {
    id: 12,
    method: "sync_save",
    params: {
      diskGzBytes: [31, 139, 8, ...] // Dữ liệu gzip nén từ IndexedDB (hoặc null nếu tab này là tab đầu tiên ghi)
    }
  }
  ```
- **Xử lý trong Worker**:
  - Nếu có `diskGzBytes`: ghi tệp `/tmp/active_bank.json.gz` và gọi `_bridge.load_bank(..., create_if_missing=True)`.
  - Thực thi:
    ```python
    _bridge.flush_save()
    _bridge.bank_revision += 1
    _synced_bytes = _bridge.export_bank()
    ```
- **Phản hồi về Main Thread**:
  ```javascript
  {
    id: 12,
    ok: true,
    result: Uint8Array [...] // Dữ liệu nén đã lưu đồng bộ
  }
  ```

### B. Message `get_bank_snapshot`
- **Gửi từ Main Thread sang Worker**:
  ```javascript
  {
    id: 13,
    method: "get_bank_snapshot",
    params: {
      profileId: "default_profile"
    }
  }
  ```
- **Phản hồi về Main Thread**:
  ```javascript
  {
    id: 13,
    ok: true,
    result: {
      ok: true,
      data: {
        revision: 4,
        worker_epoch: "...",
        profile_id: "default_profile",
        stats: { ... },
        letters: [ ... ],
        ...
      }
    }
  }
  ```

---

## 4. Giao diện người dùng: `bank.js`

### A. Hàm hiển thị thông báo lỗi `showBankErrorBanner`
- **Chữ ký**: `function showBankErrorBanner(message: string | null): void`
- **Ràng buộc an toàn DOM**:
  - Không sử dụng `innerHTML` hoặc phép nối chuỗi chứa HTML tags.
  - Sử dụng `banner.replaceChildren()` và `span.textContent = ...`.
  - Nút đóng gắn sự kiện qua `onclick` function thay vì chuỗi inline script.

### B. Hàm cập nhật dữ liệu `refreshBankView`
- **Chữ ký**: `async function refreshBankView(force: boolean = false): Promise<void>`
- **Truy xuất Profile an toàn**:
  ```javascript
  const activeProfileId = (await storage.getSetting("active_profile_id", "default_profile")) || "default_profile";
  ```
- **Bộ nhớ đệm đa yếu tố**:
  ```javascript
  if (
    !force &&
    lastBankSnapshotCache.epoch === snapshot.worker_epoch &&
    lastBankSnapshotCache.revision === snapshot.revision &&
    lastBankSnapshotCache.profileId === activeProfileId
  ) {
    return;
  }
  lastBankSnapshotCache = {
    epoch: snapshot.worker_epoch,
    revision: snapshot.revision,
    profileId: activeProfileId,
  };
  ```
