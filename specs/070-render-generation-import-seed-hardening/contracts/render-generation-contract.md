# Interface Contracts: Feature 070 - Render Generation & Seed Reset

**Feature**: Kiểm soát thế hệ kết xuất, bảo toàn hạt giống khi nhập file và tăng cường độ bền vững kiểm thử  
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
    options: {
      seed?: number | null;
      line_spacing?: number;
      font_size?: number;
      stable_variants: boolean;
      jitter?: number;
    };
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
  requestId?: number; // Truyền ngược lại để Main Thread xác nhận tính mới nhất
  error?: string;
}
```

---

## 2. Web Worker Message Contract: `clear_document_history`

### Gửi từ Main Thread xuống Worker:
```typescript
interface ClearDocumentHistoryMessagePayload {
  action: "clear_document_history";
  params?: Record<string, never>;
}
```

### Phản hồi từ Worker về Main Thread:
```typescript
interface ClearDocumentHistoryResponsePayload {
  ok: boolean; // true nếu đặt lại thành công, false nếu có lỗi
  error?: string; // Thông điệp lỗi nếu ok === false
}
```

---

## 3. UI Function Contract: `resetDocumentSeedHistory` (`write.js`)

```typescript
/**
 * Gửi lệnh xóa lịch sử hạt giống xuống Worker và kiểm tra phản hồi tường minh.
 * @returns {Promise<boolean>} true nếu xóa thành công, false nếu dịch vụ nền báo lỗi hoặc mất kết nối.
 */
async function resetDocumentSeedHistory(): Promise<boolean>;
```

### Điều kiện kích hoạt:
1. Khi người dùng xóa trắng ô soạn thảo văn bản (`!textarea.value.trim()`).
2. Khi người dùng mở thành công một tệp văn bản mới (`.txt`, `.md`, `.markdown`).
3. Khi người dùng mở thành công một tệp tài liệu Word (`.docx`).

---

## 4. UI Two-Stage Stale Guard Contract: `requestRender` (`write.js`)

Để đảm bảo tính toàn vẹn trạng thái và loại trừ triệt để race condition, Main Thread BẮT BUỘC phải thực hiện kiểm tra 2 giai đoạn (Two-Stage Stale Guard):

### Giai đoạn 1 (Ngay khi Worker trả kết quả):
1. `res && res.ok === true`
2. `thisGeneration === currentRenderGeneration`
3. `textarea && textarea.value === currentRenderSnapshot.text`
4. `textarea && textarea.value.trim().length > 0`

Nếu vi phạm bất kỳ điều kiện nào $\to$ HỦY BỎ ngay lập tức, không giải nén XOPP.

### Giai đoạn 2 (Sau khi giải nén XOPP và parse XML thành công vào biến cục bộ):
1. Quá trình giải nén và parse XML vào `parsedDoc` thành công, không phát sinh ngoại lệ.
2. `thisGeneration === currentRenderGeneration` (kiểm tra lại lần 2 để đảm bảo không có yêu cầu mới xuất hiện trong thời gian giải nén)
3. `textarea && textarea.value === currentRenderSnapshot.text`

Chỉ khi thỏa mãn cả 3 điều kiện ở Giai đoạn 2, hệ thống mới thực hiện **Atomic Commit**:
```javascript
currentXoppBase64 = res.xopp_base64;
currentMissingBoxes = res.missing_token_boxes || [];
currentDoc = parsedDoc;
renderedGeneration = thisGeneration;
isRenderStale = false;
// Cập nhật DOM SVG và thông tin trang
```

---

## 5. UI Export Stale Guard Contract (`write.js`)

Tất cả các nút xuất file (`#btn-export-xopp`, `#btn-export-pdf`, `#btn-export-png`, `#btn-export-svg`, `#btn-export-zip`) BẮT BUỘC phải kiểm tra điều kiện xuất an toàn:

```typescript
function canExport(): boolean {
  if (isRendering) return false;
  if (isRenderStale) return false;
  if (!currentXoppBase64) return false;
  const textarea = document.getElementById("editor-text");
  if (textarea && textarea.value !== currentRenderSnapshot?.text) return false;
  return true;
}
```

Nếu `canExport() === false`:
- Chặn hành vi tải file.
- Hiển thị thông báo trên `warningsBox`: `"Bản xem trước đang được cập nhật hoặc nội dung đã thay đổi. Vui lòng đợi kết xuất hoàn tất trước khi xuất file."`
