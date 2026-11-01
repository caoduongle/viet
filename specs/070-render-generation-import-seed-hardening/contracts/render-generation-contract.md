# Interface Contracts: Feature 070 - Render Generation, Import Generation & Export Stale Guard

**Feature**: Kiểm soát thế hệ kết xuất, thế hệ nhập tệp, khóa xuất bản cũ và tăng cường tính xác định kiểm thử  
**Date**: 2026-11-01  
**Status**: Completed  

---

## 1. Web Worker Message Contract: `write_text` với Request ID

### Gửi từ Main Thread (`write.js`) xuống Worker (`py-worker.js`):
```typescript
interface WriteTextMessagePayload {
  action: "write_text";
  params: {
    text: string;
    format: "txt" | "md";
    options: WriteOptionsSnapshot;
    requestId: number; // Định danh thế hệ kết xuất tăng đơn điệu
  };
}
```

### Phản hồi từ Worker (`py-worker.js`) về Main Thread:
```typescript
interface WriteTextResponsePayload {
  ok: boolean;
  xopp_base64?: string;
  missing_token_boxes?: Array<[number, number, number, number]>;
  seed_used?: number;
  n_tokens?: number;
  n_pages?: number;
  requestId?: number;
  error?: string;
}
```

---

## 2. UI Export Stale Guard Contract: `canExport` (`write.js`)

Tất cả các nút xuất tệp (`#btn-export-xopp`, `#btn-print-pdf`, `#btn-export-png`, `#btn-export-svg`, `#btn-export-zip`) BẮT BUỘC phải thông qua hàm kiểm tra toàn diện `canExport()`:

```typescript
export function canExport(): boolean {
  if (isRendering) return false;
  if (isRenderStale) return false;
  if (renderedGeneration === 0 || renderedGeneration !== currentRenderGeneration) return false;
  if (!currentXoppBase64 || !currentDoc || !renderedSnapshot) return false;
  const textarea = typeof document !== "undefined" ? document.getElementById("editor-text") : null;
  const currentVal = textarea?.value?.trim() || "";
  if (!currentVal) return false;
  if (textarea && textarea.value !== renderedSnapshot.text) return false;
  if (currentFormat !== renderedSnapshot.format) return false;
  if (!areWriteOptionsEqual(writeOptions, renderedSnapshot.options)) return false;
  return true;
}
```

### Hành vi bắt buộc:
- Khi người dùng thay đổi bất kỳ tùy chọn nào trong `setupOptionsModal()` (sliders, seed, màu sắc, khổ giấy, hướng giấy, nền giấy): phải đánh dấu `isRenderStale = true` và gọi `updateExportButtonsState()`.
- Khi một yêu cầu `requestRender()` bắt đầu: đặt ngay `isRenderStale = true` và `updateExportButtonsState()`. Nếu yêu cầu thất bại, `renderedGeneration` vẫn nhỏ hơn `currentRenderGeneration` và `isRenderStale` giữ nguyên `true`, khóa xuất tệp cũ.

---

## 3. UI File Import Generation Contract: `handleFileImport` (`write.js`)

```typescript
/**
 * Nhập tệp văn bản (.txt, .md, .docx) với cơ chế bảo vệ thế hệ nhập tệp (currentImportGeneration)
 * và đặt lại lịch sử hạt giống bắt buộc.
 * @param {File} file
 * @param {HTMLTextAreaElement} textarea
 * @returns {Promise<boolean>} true nếu tệp được áp dụng thành công, false nếu bị hủy do lỗi hoặc bị thay thế bởi tệp mới hơn.
 */
export async function handleFileImport(file: File, textarea: HTMLTextAreaElement): Promise<boolean>;
```

### Bất biến:
1. Tăng `const thisImportGen = ++currentImportGeneration;` ngay khi hàm được gọi.
2. Sau mọi thao tác bất đồng bộ (`file.text()`, `resetDocumentSeedHistory()`, `file.arrayBuffer()`, `sendWorkerMessage("import_docx")`), bắt buộc kiểm tra `if (thisImportGen !== currentImportGeneration) return false;`.
3. Không sửa `pendingImportNotices`, không gọi `clearPreview()` hay chạm vào `textarea.value` nếu `thisImportGen !== currentImportGeneration`.
4. Cập nhật `currentFormat` độc lập với sự tồn tại của `#select-format` trong DOM; trong khối `finally` của `.docx`, chỉ gọi `showRenderingIndicator(false)` khi `!isRendering && thisImportGen === currentImportGeneration`.

---

## 4. Deterministic Testing Hooks Contract (`write.js`)

```typescript
/**
 * Thay thế hàm giải nén XOPP trong kiểm thử đơn vị để kiểm chứng trực tiếp Stage 2 Stale Guard.
 */
export function setXoppDecompressorForTesting(fn: ((base64: string) => Promise<string>) | null): void;

/**
 * Cài đặt cổng chặn (barrier) có điều khiển cho yêu cầu kết xuất tiếp theo phục vụ kiểm thử E2E xác định.
 */
export function installRenderBarrierForTesting(): {
  waitForRequestStart: () => Promise<number>;
  release: () => void;
};
```

### Quy tắc dọn dẹp trạng thái kiểm thử (`resetWriteSyncStateForTesting`):
- Hủy và xóa `debounceTimer`.
- Đặt lại `currentRenderGeneration = 0`, `renderedGeneration = 0`, `currentImportGeneration = 0`, `currentRenderSnapshot = null`, `renderedSnapshot = null`, `isRenderStale = false`.
- Khôi phục `writeOptions` và `currentFormat` về giá trị mặc định ban đầu (`DEFAULT_WRITE_OPTIONS`), đặt lại `xoppDecompressor = decompressXoppBase64` và `activeRenderBarrier = null`.
