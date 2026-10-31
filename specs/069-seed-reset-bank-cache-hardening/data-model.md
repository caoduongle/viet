# Data Model: Xóa Lịch sử Hạt giống, Hoàn thiện Bộ nhớ đệm Kho mẫu và Kiểm chứng Nâng cao (seed-reset-bank-cache-hardening)

Tài liệu này mô hình hóa các thực thể dữ liệu, cấu trúc trạng thái vòng đời và máy trạng thái (state machines) cho tính năng `069-seed-reset-bank-cache-hardening`.

---

## 1. Document Alignment State Lifecycle (Vòng đời Lịch sử Đối chiếu Hạt giống)

Trạng thái đối chiếu tài liệu được lưu trữ trong `AppController` để tái sử dụng biến thể nét giữa các lần gõ văn bản liên tiếp khi bật tính năng `stable_variants`.

```
                    ┌────────────────────────────┐
                    │    STATE: Clean / Empty    │
                    │ _last_doc  = None          │
                    │ _last_seed = None          │
                    └──────────────┬─────────────┘
                                   │
                     write_document(doc, seed)
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │       STATE: Cached        │
                    │ _last_doc  = <Document IR> │
                    │ _last_seed = <int>         │
                    └──────────────┬─────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
clear_document_history()     User clears text      User imports new file
         │                   (!text.trim())       (.txt, .md, .docx)
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │    STATE: Reset to Clean   │
                    │ _last_doc  = None          │
                    │ _last_seed = None          │
                    └────────────────────────────┘
```

### Các thuộc tính trạng thái trong `AppController`:
- `_last_doc: Document | None`: Đối tượng Document IR đã được gán biến thể của lần kết xuất gần nhất.
- `_last_seed: int | None`: Giá trị số nguyên hạt giống của lần kết xuất gần nhất (mặc định 42).
- `clear_document_history() -> None`: Thao tác đồng bộ đặt cả hai giá trị về `None`.

---

## 2. Bank Snapshot Cache State Machine (Máy trạng thái Bộ nhớ đệm Kho mẫu)

Quá trình làm mới giao diện Kho mẫu (`refreshBankView`) áp dụng mô hình **Cam kết 2 giai đoạn (Two-Phase Commit)** để ngăn chặn việc đánh dấu cache thành công khi quá trình dựng giao diện (DOM rendering) gặp sự cố.

```
       [Start: refreshBankView]
                  │
                  ▼
         Get snapshot from Worker
                  │
                  ├─────────────────────────────[Snapshot Failed]──► Error Banner & return
                  ▼
         Snapshot OK (data received)
                  │
       pendingCacheKey = { epoch, revision, profileId }
                  │
                  ▼
       Cache check: pending matches lastBankSnapshotCache?
                  │
                  ├──[Match & !force]──► return (Skip redundant DOM render)
                  ▼
         [No Match or Force]
                  │
                  ▼
       Aggregate items & call applyFiltersAndRender()
                  │
        ┌─────────┴─────────┐
        │                   │
    [Success]            [Error / Exception]
        │                   │
        ▼                   ▼
lastBankSnapshotCache =    lastBankSnapshotCache =
    pendingCacheKey            { epoch: null, revision: null, profileId: null }
        │                   │
        │                   ▼
        │               showBankErrorBanner(err.message)
        │                   │
        ▼                   ▼
    [Complete]        [Ready for Retry]
```

### Cấu trúc thực thể `BankSnapshotCache`:
```typescript
interface BankSnapshotCache {
  epoch: string | null;      // UUIDv4 đại diện cho phiên khởi tạo của Web Worker
  revision: number | null;    // Số hiệu phiên bản kho mẫu đơn điệu tăng dần
  profileId: string | null;   // Định danh hồ sơ đang kích hoạt
}
```

---

## 3. Large-Scale Multi-Variant Bank Benchmark Model (Mô hình Kho mẫu Đa biến thể)

Mô hình cấu trúc dữ liệu JSON kho mẫu dùng trong kịch bản đo kiểm hiệu năng lớn:

```json
{
  "v": 1,
  "xh": 10.0,
  "words": {
    "word_0": [
      { "w": 10.0, "s": [[0, 0, 5, -5]], "inst_w": 10.0 },
      { "w": 10.2, "s": [[0, 0, 4.8, -5.1]], "inst_w": 10.2 },
      { "w": 9.9,  "s": [[0, 0, 5.1, -4.9]], "inst_w": 9.9 }
    ]
    // ... 700 từ (2.100 mẫu nét)
  },
  "letters": {
    "ch_0": [
      { "w": 5.0, "s": [[0, 0, 3, -4]], "inst_w": 5.0 },
      { "w": 5.1, "s": [[0, 0, 2.9, -4.1]], "inst_w": 5.1 },
      { "w": 4.9, "s": [[0, 0, 3.1, -3.9]], "inst_w": 4.9 },
      { "w": 5.0, "s": [[0, 0, 3.0, -4.0]], "inst_w": 5.0 }
    ]
    // ... 300 chữ cái (1.200 mẫu nét)
  },
  "symbols": {
    "\\sym_0": [
      { "w": 6.0, "s": [[0, 0, 4, -4]], "inst_w": 6.0 },
      { "w": 6.1, "s": [[0, 0, 3.9, -4.1]], "inst_w": 6.1 }
    ]
    // ... 20 ký hiệu (40 mẫu nét)
  },
  "marks": {
    "sắc": [
      { "w": 3.0, "s": [[0, 0, 2, 2]], "inst_w": 3.0 },
      { "w": 3.1, "s": [[0, 0, 2.1, 2.1]], "inst_w": 3.1 }
    ]
    // ... 30 dấu thanh (60 mẫu nét)
  }
}
```

### Các chỉ số kiểm định:
- Tổng số nhãn: $700 + 300 + 20 + 30 = 1.050$ nhãn.
- Tổng số mẫu nét (samples): $2.100 + 1.200 + 40 + 60 = 3.400$ mẫu nét.
- Yêu cầu hiệu năng: Thời gian trích xuất snapshot $t < 200$ ms.
