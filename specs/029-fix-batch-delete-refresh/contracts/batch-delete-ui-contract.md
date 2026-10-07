# Contract: Giao diện và Luồng Xóa Hàng Loạt trong Tab Kho Mẫu (Web Client)

**Mô-đun**: `webapp/js/bank.js`

## 1. Luồng Xóa Hàng Loạt (`handleDeleteSelected`)

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Bank Tab UI
    participant Handler as handleDeleteSelected()
    participant Worker as Pyodide Worker
    participant Storage as IndexedDB Storage
    participant Refresh as refreshBankView()

    User->>UI: Bấm "Xoá đã chọn (N)"
    UI->>Handler: Kích hoạt sự kiện click
    Handler->>User: Hiển thị confirm() xác nhận số lượng ký tự và mẫu
    alt Người dùng từ chối (Cancel)
        Handler-->>UI: Dừng thực thi, giữ nguyên trạng thái chọn
    else Người dùng đồng ý (OK)
        Handler->>Worker: sendWorkerFn("drop_chars", { chars: labelsToDelete })
        Worker-->>Handler: { ok: true, data: { removed: ... } }
        Handler->>Handler: selectedLabels.clear()
        Handler->>Storage: storage.syncAndSaveActiveProfile(sendWorkerFn)
        Storage-->>Handler: Đã lưu xuống IndexedDB và phát sóng BroadcastChannel
        Handler->>Refresh: await refreshBankView()
        Refresh->>Worker: sendWorkerFn("list_all_chars")
        Worker-->>Refresh: Danh sách ký tự cập nhật
        Refresh->>UI: Vẽ lại lưới thẻ và reset thanh chọn hàng loạt
    end
```

## 2. Hợp đồng Định danh Hàm (Function Identifier Invariant)

- **Cấm hoàn toàn**: Gọi hàm không tồn tại `refreshBankTab()`.
- **Bắt buộc**: Sử dụng `refreshBankView()` trong toàn bộ các hàm xử lý sau biến đổi dữ liệu của `webapp/js/bank.js`.
- **Chữ ký hàm**:
  ```javascript
  export async function refreshBankView(): Promise<void>
  ```
- **Nhiệm vụ của `refreshBankView()`**:
  1. Yêu cầu worker liệt kê danh sách toàn bộ ký tự hiện có (`list_all_chars`).
  2. Cập nhật số lượng các thẻ phân loại (`updateCategoryCounts()`).
  3. Lọc danh sách theo từ khóa tìm kiếm và danh mục đang mở (`applyFiltersAndRender()`).
  4. Cập nhật lại thanh chọn hàng loạt (`updateBatchBar()`).
