# Data Model: Feature 070 - Render Generation, Import Generation & Export Freshness Lifecycle

**Feature**: Kiểm soát thế hệ kết xuất, thế hệ nhập tệp, khóa xuất bản cũ và tăng cường tính xác định kiểm thử  
**Date**: 2026-11-01  
**Status**: Completed  

---

## 1. Mô hình Trạng thái Thế hệ Kết xuất và Bản chụp Đã Cam kết (Render Generation & Committed Snapshot)

Mô hình trạng thái quản lý chu kỳ sống của các yêu cầu kết xuất trong `webapp/js/write.js`, đảm bảo loại trừ triệt để tình trạng cạnh tranh (race condition) và khóa xuất tệp khi trạng thái hiện hành khác với bản chụp đã cam kết.

```
                   [Người dùng gõ / Mở file / Đổi định dạng / Đổi tùy chọn]
                                      │
                                      ▼
                       ┌────────────────────────────────────┐
                       │ Tăng currentRenderGeneration++     │
                       │ Đặt isRenderStale = true           │
                       │ Lưu currentRenderSnapshot          │
                       │ Cập nhật updateExportButtonsState()│
                       └──────────────┬─────────────────────┘
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
      Stage 1: thisGeneration == currentRenderGeneration│
               và text == currentRenderSnapshot.text?   │
                        │                              │
            ┌───────────┴───────────┐                  │
            │ Đúng                  │ Sai              │
            ▼                       ▼                  │
  [Giải nén XOPP qua     [BỎ QUA KẾT QUẢ CŨ]           │
   xoppDecompressor &                                  │
   Parse XML vào parsedDoc]                            │
            │                                          │
            ▼                                          │
      Stage 2: Giải nén thành công,                    │
               thisGeneration == currentRenderGeneration│
               và text == currentRenderSnapshot.text?   │
            │                                          │
      ┌─────┴───────────┐                              │
      │ Sai / Lỗi       │ Đúng                         │
      ▼                 ▼                              │
  [GIỮ STALE,      [ATOMIC COMMIT:                     │
   BỎ QUA KẾT QUẢ]  - currentXoppBase64 = res.xopp_base64
                    - currentDoc = parsedDoc           │
                    - renderedGeneration = thisGeneration
                    - renderedSnapshot = clone(snapshot)│
                    - isRenderStale = false            │
                    - Cập nhật DOM SVG & Nút xuất]     │
      │                 │                              │
      └────────┬────────┘                              │
               ▼                                       │
          finally: isRendering = false                 │
                   updateExportButtonsState()          │
               │                                       │
               └─── Có hasPendingRequest? ─────────────┘
                           │
                           ▼
              [Kích hoạt ngay lượt render mới nhất]
```

### Các Thực thể và Thuộc tính

#### `WriteOptionsSnapshot` (Client-side Memory)
```typescript
interface WriteOptionsSnapshot {
  scale: number;
  line: number | null;
  space: number;
  jitter: number;
  wscale: number;
  color: string;
  seed: number;
  paper: string;
  orientation: string;
  background: string;
  background_color?: string;
  stable_variants: boolean;
  assemble_letters: boolean;
}
```

#### `RenderSnapshot` (`currentRenderSnapshot` & `renderedSnapshot`)
```typescript
interface RenderSnapshot {
  generation: number;             // Số nguyên tăng đơn điệu (1, 2, 3...)
  text: string;                   // Nội dung văn bản tại thời điểm kết xuất
  format: "txt" | "md";           // Định dạng tài liệu
  options: WriteOptionsSnapshot;  // Bản sao độc lập của toàn bộ writeOptions
}
```

#### `RenderLifecycleState` (Client-side Session)
```typescript
interface RenderLifecycleState {
  currentRenderGeneration: number;        // Thế hệ của yêu cầu kết xuất mới nhất đã phát sinh
  renderedGeneration: number;             // Thế hệ của bản kết xuất đã được Atomic Commit thành công
  currentRenderSnapshot: RenderSnapshot | null; // Snapshot của yêu cầu đang chạy
  renderedSnapshot: RenderSnapshot | null;      // Snapshot của bản kết xuất đã cam kết trên giao diện
  currentImportGeneration: number;        // Thế hệ của thao tác mở/kéo thả tệp mới nhất
  isRendering: boolean;                   // Cờ báo hiệu Worker hoặc giải nén đang xử lý
  isRenderStale: boolean;                 // Cờ báo hiệu nội dung/tùy chọn hiện hành chưa được kết xuất xong
}
```

---

## 2. Mô hình Thế hệ Nhập tệp và Xóa Lịch sử Hạt giống (Import Generation & Seed Reset Flow)

Đảm bảo khi người dùng mở nhiều tệp liên tiếp (.docx và .txt/.md), chỉ tệp được chọn cuối cùng mới được phép cập nhật giao diện và kết xuất.

```
[Người dùng chọn tệp / Kéo thả tệp]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ Gán thisImportGen = ++currentImportGeneration          │
└────────────────────────┬───────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │ .txt / .md              │ .docx
            ▼                         ▼
   [await file.text()]       [await file.arrayBuffer()]
            │                [await sendWorker("import_docx")]
   thisImportGen ==                   │
   currentImportGeneration?  thisImportGen ==
   (Nếu sai -> HỦY BỎ)       currentImportGeneration?
            │                (Nếu sai -> HỦY BỎ)
            ▼                         │
   [clearPreview()]                   ▼
   [await resetSeed()]       [clearPreview()]
            │                [await resetSeed()]
   thisImportGen ==                   │
   currentImportGeneration?  thisImportGen ==
   (Nếu sai hoặc !resetOk    currentImportGeneration?
    -> HỦY BỎ)               (Nếu sai hoặc !resetOk -> HỦY BỎ)
            │                         │
            └────────────┬────────────┘
                         ▼
       [ATOMIC IMPORT APPLY (chỉ cho thisImportGen mới nhất):
        - Cập nhật textarea.value
        - Cập nhật currentFormat (độc lập với DOM #select-format)
        - Cập nhật pendingImportNotices
        - Gọi triggerPreviewImmediate()]
```

---

## 3. Quy tắc Xác thực Xuất tệp (`canExport` Validation Rules)

Một thao tác xuất tệp (`.xopp`, `.pdf`, `.png`, `.svg`, `.zip`) chỉ hợp lệ khi TẤT CẢ 7 điều kiện bất biến sau đây đồng thời thỏa mãn:
1. `isRendering === false`
2. `isRenderStale === false`
3. `renderedGeneration > 0 && renderedGeneration === currentRenderGeneration`
4. `Boolean(currentXoppBase64) && Boolean(currentDoc) && Boolean(renderedSnapshot)`
5. `textarea.value.trim().length > 0 && textarea.value === renderedSnapshot.text`
6. `currentFormat === renderedSnapshot.format`
7. `areWriteOptionsEqual(writeOptions, renderedSnapshot.options) === true`
