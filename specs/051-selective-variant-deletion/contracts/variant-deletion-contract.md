# Contract: Cầu nối IPC và Giao diện Xóa Biến Thể Mẫu Nét

**Feature Branch**: `051-selective-variant-deletion`  
**Date**: 2026-10-20  
**Spec**: [spec.md](../spec.md)

---

## 1. Hợp đồng tầng Mô hình Cốt lõi (`Bank.drop_samples`)

### Định nghĩa phương thức:
```python
def drop_samples(
    self,
    label: str,
    indices: list[int],
    category: str | None = None
) -> dict[str, Any]:
    """Xóa các biến thể mẫu nét cụ thể của nhãn theo danh sách chỉ số (0-based indices).

    Quy tắc nghiệp vụ:
    1. Thread-safe: Bao bọc hoàn toàn bên trong `with self._lock:`.
    2. Chỉ số hợp lệ: Loại bỏ trùng lặp và sắp xếp giảm dần `sorted(set(indices), reverse=True)`.
       Bỏ qua các chỉ số ngoài biên (`idx < 0` hoặc `idx >= len(samples)`).
    3. Cập nhật biến thể: Gọi `samples.pop(idx)` cho từng chỉ số hợp lệ.
    4. Xóa cạn kiệt (Zero Remaining):
       - Nếu sau khi xóa, `len(samples) == 0`:
         * `target_dict.pop(label, None)`
         * Nếu `cat == "marks"`: đồng thời xóa khỏi `self.d.get("marks", {})`, `self._raw_marks` và `self.marks`.
         * Nếu `cat == "words"`: dọn dẹp `self.tl` và `self._raw_marks`, gọi `_refresh_tone_marks`.
         * Đánh dấu tombstone: `tomb_key = f"{cat}:{label}"` vào `self._tombstones` và `self._deleted_words`.
         * Gỡ bỏ khỏi `self._readded_words`.
         * Trả về `label_deleted = True`.
    5. Còn biến thể:
       - Nếu `len(samples) > 0`:
         * Không ghi tombstone.
         * Tái lập chỉ mục `self.rebuild()` nếu `cat in ("words", "marks")` (với `marks`, gọi `self._refresh_tone_marks(label)`).
         * Trả về `label_deleted = False`.
    6. Cập nhật trạng thái: Tăng `self._mutation_seq += 1`, `self._generation += 1`, `self._dirty = True`.

    Trả về:
        dict chứa:
            - "label": str
            - "category": str
            - "removed_count": int (số biến thể thực tế đã xóa)
            - "remaining_count": int (số biến thể còn lại của nhãn)
            - "label_deleted": bool (true nếu nhãn bị xóa hoàn toàn khỏi kho)
    """
```

---

## 2. Hợp đồng tầng Điều khiển (`AppController.drop_label_samples`)

### Định nghĩa phương thức:
```python
def drop_label_samples(
    self,
    label: str,
    indices: list[int],
    category: str = "words"
) -> dict[str, Any]:
    """Ủy quyền xóa biến thể cho Bank, lưu kho mẫu vào đĩa, và ghi nhận log."""
```
- Gọi `bank = self._require_bank()`.
- Thực thi `res = bank.drop_samples(label, indices, category=category)`.
- Gọi `bank.save()` nếu `res["removed_count"] > 0`.
- Ghi log info: `_log.info("Đã xóa %d biến thể của nhãn %s (%s), còn lại %d mẫu", ...)`.
- Trả về `res`.

---

## 3. Hợp đồng Cầu nối Trình duyệt (`BrowserBridge.drop_label_samples`)

### Định nghĩa phương thức:
```python
def drop_label_samples(
    self,
    label: str,
    indices: list[int],
    category: str = "words"
) -> dict[str, Any]:
    """Đóng gói phản hồi chuẩn dạng JSON an toàn cho Web Worker."""
    try:
        res = self._ctl.drop_label_samples(label, indices, category=category)
        return {"ok": True, "data": _clean_json(res)}
    except Exception as e:
        return _err_res(e)
```

---

## 4. Hợp đồng Web Worker (`py-worker.js`)

Khi nhận thông điệp với `method === "drop_label_samples"`:
```javascript
} else if (method === "drop_label_samples") {
  const { label, indices, category } = params || {};
  pyodide.globals.set("_drop_lbl", label || "");
  pyodide.globals.set("_drop_indices_json", JSON.stringify(indices || []));
  pyodide.globals.set("_drop_cat", category || "words");
  result = pyodide.runPython(`
import json
_indices = json.loads(_drop_indices_json)
_bridge.drop_label_samples(_drop_lbl, _indices, category=_drop_cat)
`).toJs({ dict_converter: Object.fromEntries });
}
```

---

## 5. Hợp đồng Đồng bộ Dữ liệu Đa Tab (`storage.js`)

Sau khi gọi worker thành công và `removed_count > 0`:
1. Gọi `await storage.syncAndSaveActiveProfile(sendWorkerFn)` để:
   - Ghi dữ liệu `.json.gz` đã cập nhật vào IndexedDB.
   - Phát sóng sự kiện qua `BroadcastChannel("chuviettay_sync")` với payload `{ type: "BANK_SYNCHRONIZED", profileId, ... }`.
2. Gọi `await refreshBankView()` để cập nhật thẻ tổng quan bên ngoài kho mẫu.
