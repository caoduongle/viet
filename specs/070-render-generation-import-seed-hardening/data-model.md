# Data Model: Feature 070 - Render Generation & Import Seed Lifecycle

**Feature**: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử  
**Date**: 2026-11-01  
**Status**: Completed  

---

## 1. Mô hình Trạng thái Thế hệ Kết xuất (Render Generation Lifecycle)

Mô hình trạng thái quản lý chu kỳ sống của các yêu cầu kết xuất trong `webapp/js/write.js`, đảm bảo loại trừ triệt để tình trạng cạnh tranh (race condition) và áp dụng nhầm kết quả lỗi thời lên DOM.

```
                  [Người dùng gõ / Mở file / Đổi định dạng]
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    Tăng requestId++         │
                      │    Lưu Snapshot tham số     │
                      └──────────────┬──────────────┘
                                     │
                        Có đang bận render? (isRendering)
                                     │
                       ┌─────────────┴─────────────┐
                       │ Không                     │ Có
                       ▼                           ▼
          ┌───────────────────────────┐ ┌───────────────────────────┐
          │  Gửi write_text xuống     │ │ Đặt hasPendingRequest     │
          │  Web Worker kèm requestId │ │ Ghi đè pendingParams      │
          └────────────┬──────────────┘ └─────────────┬─────────────┘
                       │                              │
                       ▼                              │
             [Worker trả về kết quả]                  │
                       │                              │
          requestId == currentRequestId?              │
                       │                              │
           ┌───────────┴───────────┐                  │
           │ Đúng                  │ Sai              │
           ▼                       ▼                  │
    Snapshot khớp DOM?     [BỎ QUA KẾT QUẢ CŨ]        │
           │                                          │
     ┌─────┴─────┐                                    │
     │ Có        │ Không                              │
     ▼           ▼                                    │
  [Cập nhật   [BỎ QUA]                                │
   DOM & XOPP]                                        │
     │           │                                    │
     └─────┬─────┘                                    │
           │                                          │
           ▼                                          │
      finally: isRendering = false                    │
           │                                          │
           └─── Có pendingRequest? ───────────────────┘
                       │
                       ▼
          [Kích hoạt ngay lượt render mới nhất]
```

### Các Thực thể và Thuộc tính

#### `RenderRequestSnapshot` (Client-side Memory)
```typescript
interface RenderRequestSnapshot {
  requestId: number;          // Số nguyên tăng đơn điệu (1, 2, 3...)
  text: string;               // Nội dung văn bản thô tại thời điểm gửi
  format: "txt" | "md";       // Định dạng tài liệu
  options: {
    seed: number;             // Hạt giống ngẫu nhiên (hoặc null nếu ngẫu nhiên)
    line_spacing?: number;    // Giãn dòng
    font_size?: number;       // Cỡ chữ
    stable_variants: boolean; // Cờ bật tính ổn định biến thể
  };
  timestamp: number;          // Mốc thời gian tạo yêu cầu (ms)
}
```

#### `RenderLifecycleState` (Client-side Session)
```typescript
interface RenderLifecycleState {
  currentRequestId: number;                       // ID của yêu cầu mới nhất hiện tại
  activeRequestSnapshot: RenderRequestSnapshot | null; // Snapshot của yêu cầu đang được hiển thị
  isRendering: boolean;                           // Cờ báo hiệu Worker đang bận xử lý
  hasPendingRequest: boolean;                     // Cờ báo hiệu có yêu cầu mới đang xếp hàng
  pendingParams: Record<string, any> | null;      // Tham số của yêu cầu đang chờ thực thi
}
```

#### `DocumentHistoryState` (Python Worker / MEMFS)
```typescript
interface DocumentHistoryState {
  _last_doc: Document | null; // Cấu trúc phân tích tài liệu của lượt kết xuất trước
  _last_seed: number | null;  // Hạt giống được sử dụng ở lượt trước
}
```

---

## 2. Mô hình Vòng đời Xóa Lịch sử Hạt giống (Seed Reset Flow)

Đảm bảo tài liệu mới mở hoàn toàn độc lập với tài liệu trước đó.

```
[Người dùng chọn file / Kéo thả file]
                 │
                 ▼
     [Đọc nội dung file thành công]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Gọi resetDocumentSeedHistory()                         │
│ -> Worker dispatch 'clear_document_history'            │
│ -> BrowserBridge.clear_document_history()              │
│ -> AppController.clear_document_history()              │
│ -> Đặt _last_doc = None, _last_seed = None             │
│ -> Trả về { ok: true }                                 │
└────────────────────────┬───────────────────────────────┘
                         │
              Phản hồi { ok: true }?
                         │
             ┌───────────┴───────────┐
             │ Có                    │ Không
             ▼                       ▼
    [Nạp text vào textarea]   [Cảnh báo nhẹ vào console]
    [Chuyển currentFormat]    [Vẫn nạp text vào textarea]
             │
             ▼
    [triggerPreviewImmediate()]
    (Bắt đầu thế hệ kết xuất mới với seed sạch)
```

---

## 3. Mô hình Cấu trúc Dữ liệu Benchmark Kho mẫu Đa biến thể

Khẳng định cấu trúc dữ liệu tổng hợp phục vụ đo kiểm hiệu năng trích xuất bản chụp kho mẫu quy mô lớn trong `test_performance_regression.py`:

```typescript
interface LargeSyntheticBank {
  schema_version: number;
  words: Record<string, Array<WordSample>>;     // 700 nhãn x 3 biến thể = 2.100 mẫu
  letters: Record<string, Array<LetterSample>>; // 300 nhãn x 4 biến thể = 1.200 mẫu
  symbols: Record<string, Array<SymbolSample>>; // 50 nhãn x 2 biến thể  =   100 mẫu
  marks: Record<string, Array<MarkSample>>;     // 5 nhóm x 20 biến thể  =   100 mẫu
  digits: Record<string, Array<DigitSample>>;   // 10 nhãn x 2 biến thể  =    20 mẫu
  punct: Record<string, Array<PunctSample>>;   // 1 nhãn x 1 mẫu        =     1 mẫu
}
```

### Các chỉ số kiểm định:
- **Tổng số nhãn**: $700 + 300 + 50 = 1.050$ nhãn (chưa tính 5 dấu thanh và 10 chữ số).
- **Tổng số mẫu nét (samples)**: $2.100 + 1.200 + 100 + 100 + 20 + 1 = 3.521$ mẫu nét (vượt ngưỡng yêu cầu $3.520$).
- **Thời gian xử lý yêu cầu**: $t < 200$ ms (thực tế đo được $< 2.0$ ms).
