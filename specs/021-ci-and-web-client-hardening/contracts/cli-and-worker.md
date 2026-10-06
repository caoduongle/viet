# Contracts & External Interfaces: 021 — Sửa lỗi CI và hoàn thiện Web Client

## 1. CLI Contract: `scripts/build_web.py`

### Cú pháp gọi
```bash
python scripts/build_web.py [--dist <THƯ_MỤC_ĐÍCH>]
```

### Tham số
- `--dist`: Đường dẫn thư mục xuất bản (tuỳ chọn).
  - Mặc định: `webapp/dist` (tương đối từ gốc repo).
  - Ràng buộc an toàn: Bị từ chối (exit code != 0) nếu trỏ tới gốc repo, thư mục cha, thư mục gốc của hệ thống tập tin, hoặc bất kỳ thư mục con nào trong `webapp/` (ngoại trừ `webapp/dist`).

### Mã trả về
- `0`: Xây dựng thành công bản phân phối sạch.
- Khác `0`: Phát hiện vi phạm an toàn đường dẫn, thiếu phụ thuộc `node_modules/pyodide`, lỗi mạng không thể phục hồi khi tải wheels, hoặc vi phạm kiểm tra tính sạch (`Sanity Check`).

---

## 2. Web Worker Contract: `import_docx`

### Tin nhắn yêu cầu từ Main Thread
```javascript
worker.postMessage({
  id: 123,
  method: "import_docx",
  params: {
    bytes: Uint8Array /* dữ liệu nhị phân file docx */
  }
});
```

### Phản hồi từ Worker
```javascript
// Thành công
{
  id: 123,
  result: {
    text: "Nội dung văn bản được trích xuất từ Word...",
    warnings: []
  }
}

// Thất bại
{
  id: 123,
  error: "Mô tả lỗi chi tiết"
}
```

---

## 3. npm Scripts Contract: `package.json`

```json
{
  "scripts": {
    "test:unit": "node --test 'tests/js/*.test.mjs'",
    "test:browser": "node tests/browser/test_bridge_no_tkinter.mjs && node tests/browser/test_bank_merge_memfs.mjs",
    "test:golden": "node scripts/test_golden_pyodide.mjs",
    "test:e2e": "playwright test"
  }
}
```
