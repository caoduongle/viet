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

## 4. UI Stale Result Guard Contract: `requestRender` (`write.js`)

Trước khi áp dụng kết quả `res` từ Worker vào DOM và lưu trữ biến trạng thái, Main Thread BẮT BUỘC phải thỏa mãn toàn bộ các điều kiện sau:

1. `res && res.ok === true`
2. `currentRequestId === requestSnapshot.requestId` (kết quả không bị thế hệ mới hơn vượt qua)
3. `textarea && textarea.value === requestSnapshot.text` (nội dung ô soạn thảo hiện tại không bị gõ/thay đổi thêm trong lúc chờ Worker)
4. `textarea && textarea.value.trim().length > 0` (ô soạn thảo không bị xóa trắng giữa chừng)

Nếu **bất kỳ** điều kiện nào bị vi phạm, kết quả `res` bị BỎ QUA và xem như đã lỗi thời (stale), không được cập nhật vào `currentDoc` hay `currentXoppBase64`.
