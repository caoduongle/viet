# Data Model: Hoàn thiện Đối chiếu Hạt giống Đa bước, Đồng bộ Phiên bản Kho mẫu và Khắc phục Kiểm thử E2E (068-seed-bank-e2e-hardening)

Tài liệu này định nghĩa cấu trúc dữ liệu, các thực thể trạng thái, quy tắc ràng buộc (validation rules) và các bước chuyển trạng thái (state transitions) cho tính năng `068-seed-bank-e2e-hardening`.

---

## 1. Multi-Step Seed Alignment State (Trạng thái Đối chiếu Hạt giống Đa bước)

Đối tượng trạng thái nằm trong `AppController` nhằm duy trì sự liên tục của biến thể nét chữ qua nhiều lượt chỉnh sửa liên tiếp trong một phiên làm việc.

### Cấu trúc dữ liệu
```python
class AppController:
    _last_doc: Document | None = None   # Cây IR của tài liệu kết xuất thành công liền trước
    _last_seed: int | None = None       # Giá trị seed của lượt kết xuất liền trước
```

### Quy tắc chuyển trạng thái (State Transitions)
```
                                 [Khởi tạo Controller]
                                           │
                                           ▼
                                 ┌───────────────────┐
                                 │ _last_doc = None  │
                                 │ _last_seed = None │
                                 └─────────┬─────────┘
                                           │
                        write_document()   │
                                           ▼
                 ┌───────────────────────────────────────────────────┐
                 │ Kiểm tra: opts.stable_variants == True            │
                 │ VÀ _last_doc is not None                          │
                 │ VÀ _last_seed == opts.seed ?                      │
                 └──────────────────┬─────────────────┬──────────────┘
                                    │                 │
                             CÓ     │                 │ KHÔNG
                                    ▼                 ▼
             ┌──────────────────────────────┐  ┌─────────────────────────────┐
             │ doc = align_document_seeds(  │  │ Giữ nguyên doc mới         │
             │         _last_doc, doc)      │  │ (chưa gán occurrences)      │
             └──────────────┬───────────────┘  └──────────────┬──────────────┘
                            │                                 │
                            └────────────────┬────────────────┘
                                             ▼
                                ┌──────────────────────────┐
                                │ engine.render(doc)       │
                                └────────────┬─────────────┘
                                             ▼
                                ┌──────────────────────────┐
                                │ Cập nhật trạng thái:     │
                                │ _last_doc = doc          │
                                │ _last_seed = opts.seed   │
                                └──────────────────────────┘
```

- **Reset**: Khi gọi `clear_document_history()`, khi nạp kho mẫu mới qua `load_bank()`, hoặc khi tài liệu mới là tài liệu rỗng (không có khối nội dung nào), `_last_doc` và `_last_seed` được đặt lại về `None`.

---

## 2. Document IR Node Occurrences (Chỉ số Xuất hiện trên Cây IR)

Các thuộc tính lưu trữ chỉ số xuất hiện của từng phần tử nội dung trên cây Document IR.

### Cấu trúc trường trên Node IR
| Node Type | Trường lưu trữ | Kiểu dữ liệu | Ý nghĩa |
|-----------|----------------|--------------|---------|
| `Text` | `token_occurrences` | `list[int]` | Danh sách chỉ số xuất hiện ứng với từng token đã chuẩn hóa (tách theo `_normalize_text(text).split()`). Độ dài bằng số token trong `norm.split()`. |
| `Symbol` | `occurrence` | `int` | Thứ tự xuất hiện của ký hiệu toán học / đặc biệt trong tài liệu. |
| `MathInline` | `occurrence` | `int` | Thứ tự xuất hiện của công thức toán nội dòng ($...$). |
| `MathBlock` | `occurrence` | `int` | Thứ tự xuất hiện của khối công thức toán độc lập ($$...$$). |
| `Table` | `occurrence` | `int` | Thứ tự xuất hiện của bảng biểu. |

### Quy tắc trích xuất và bảo toàn (`extract_doc_elements`)
1. **Ưu tiên giá trị đã gán**:
   - Nếu phần tử đã mang `occurrence` hoặc `token_occurrences[i]` từ lượt trước, lấy giá trị đó làm `occ`.
   - Nếu phần tử chưa có (node mới tạo), lấy `occ = counts.get(key, 0)`.
2. **Theo dõi chặn trên không trùng lặp**:
   - Mỗi khi xác định được `occ` của một phần tử có khóa `key = (content_type, element_id)`:
     $$\text{counts}[key] = \max(\text{counts}.get(key, 0), occ + 1)$$
   - Đảm bảo khi một phần tử mới hoàn toàn được chèn vào tài liệu ở các lượt sau, chỉ số được cấp phát:
     $$next\_occ = \text{counts}[key] > \max_{e \in base}(e.occ)$$
     triệt tiêu 100% khả năng trùng lặp chỉ số xuất hiện.

---

## 3. Composite Bank Revision & Worker Epoch (Phiên bản Kho mẫu Toàn cục)

Tổ hợp định danh xác thực tính hợp lệ của dữ liệu kho mẫu đang hiển thị trên giao diện người dùng.

### Cấu trúc dữ liệu
```typescript
interface CompositeBankCacheKey {
  epoch: string;        // UUIDv4 đại diện cho thế hệ vòng đời của BrowserBridge / Web Worker
  revision: number;     // Số nguyên dương đơn điệu tăng, đại diện cho phiên bản dữ liệu
  profileId: string;    // Tên định danh hồ sơ lưu trữ trong IndexedDB (vd: "default_profile")
}
```

### Quy tắc cập nhật và làm mất hiệu lực Cache
1. **Khởi tạo**:
   - Khi `BrowserBridge` khởi tạo trong Python: `self.worker_epoch = str(uuid.uuid4())`, `self.bank_revision = 1`.
2. **Tăng Revision**:
   - Mọi thao tác làm biến đổi dữ liệu kho (`load_bank`, `teach_word`, `drop_label`, `drop_chars`, `drop_label_samples`, và `sync_save`) PHẢI tăng `self.bank_revision += 1`.
3. **Mất hiệu lực bộ nhớ đệm UI (`bank.js`)**:
   - UI chỉ bỏ qua truy vấn khi và chỉ khi:
     $$(\text{cache.epoch} == \text{snap.worker\_epoch}) \land (\text{cache.revision} == \text{snap.revision}) \land (\text{cache.profileId} == \text{activeProfileId})$$
   - Khi Worker khởi động lại (epoch mới) hoặc đổi Profile hoặc revision tăng, cache tự động mất hiệu lực và UI cập nhật dữ liệu mới nhất.

---

## 4. Atomic Bank Snapshot Payload (Bản chụp Kho mẫu Nguyên tử)

Cấu trúc đối tượng trả về từ `BrowserBridge.get_bank_snapshot()`.

### Cấu trúc dữ liệu
```python
{
    "ok": bool,                 # True nếu tất cả danh mục con thành công; False nếu bất kỳ danh mục nào lỗi
    "data": {
        "revision": int,        # Phiên bản kho mẫu hiện hành
        "worker_epoch": str,    # Định danh thế hệ tiến trình nền
        "profile_id": str,      # Định danh hồ sơ người dùng
        "stats": dict,          # Thống kê tổng hợp (n_letters, n_samples, n_words, ...)
        "letters": list,        # Danh sách tuple (ch, count) cho chữ cái
        "digits": dict,         # Bảng đếm cho chữ số
        "punct": dict,          # Bảng đếm cho dấu câu
        "symbols": list,        # Danh sách tuple (sym, count) cho ký hiệu
        "marks": list,          # Danh sách tuple (mark, count) cho dấu thanh
    },
    "error": str | None         # Thông điệp lỗi chi tiết khi ok == False
}
```

### Quy tắc toàn vẹn (Atomicity Invariants)
- **All-or-Nothing**: Bản chụp chỉ trả về `ok: True` khi tất cả 4 truy vấn (`get_stats`, `list_letters`, `list_category_items('symbols')`, `list_category_items('marks')`) đều trả về `ok: True`.
- Nếu có lỗi ở bất kỳ bước nào, trả về ngay cấu trúc lỗi của bước đó, tuyệt đối không trả về `letters: []` giả tạo.
