# Interface Contracts: Gia cố Bảo toàn Nội dung Tài liệu, Độ ổn định Biến thể Nét chữ và Hiệu năng Kho mẫu

**Feature**: `067-content-seed-bank-hardening`  
**Date**: 2026-10-31  
**Spec Reference**: [spec.md](../spec.md)

---

## 1. Hợp đồng BrowserBridge & Web Worker (`bridge.py` & `py-worker.js`)

### 1.1. `write_text` Response Contract

Cầu nối `BrowserBridge.write_text` bổ sung trường `unsupported` bên cạnh `warnings` để chuyển tiếp đầy đủ danh sách thành phần không hỗ trợ về giao diện Web:

```json
{
  "ok": true,
  "xopp_base64": "<base64_encoded_string>",
  "n_pages": 1,
  "n_lines": 5,
  "n_strokes": 42,
  "n_tokens": 12,
  "n_missing_tokens": 0,
  "missing_sorted": [],
  "missing_token_boxes": [],
  "warnings": [
    "Định dạng kiểu chữ (in đậm, in nghiêng, gạch ngang, mã nội tuyến...) đã được chuyển về nét viết tay chuẩn.",
    "Khối trích dẫn (blockquote) đã được chuyển về đoạn văn viết tay tiêu chuẩn."
  ],
  "unsupported": [
    "code_block: python",
    "hr: horizontal rule",
    "image: sơ đồ mạch"
  ],
  "seed_used": 42,
  "ignored_options": []
}
```

### 1.2. `get_bank_snapshot` Contract

API tổng hợp mới trên `BrowserBridge` và được đăng ký nhánh điều phối `else if (method === "get_bank_snapshot")` trong `webapp/js/worker/py-worker.js`.

**Input**: Không yêu cầu tham số bắt buộc.

**Output (Success)**:
```json
{
  "ok": true,
  "data": {
    "revision": 2,
    "stats": {
      "n_letters": 45,
      "n_samples": 120,
      "n_words": 0,
      "digit_counts": { "0": 2, "1": 3 },
      "punct_counts": { ".": 2, ",": 2 },
      "tone_mark_counts": { "sắc": 5 }
    },
    "letters": [
      ["a", 3],
      ["b", 2]
    ],
    "digits": {
      "0": 2,
      "1": 3
    },
    "punct": {
      ".": 2,
      ",": 2
    },
    "symbols": [
      ["+", 2],
      ["=", 1]
    ],
    "marks": [
      ["sắc", 5]
    ]
  }
}
```

**Output (Error)**:
```json
{
  "ok": false,
  "error": "Chưa nạp kho mẫu. Hãy gọi load_bank() trước.",
  "error_type": "BankNotLoadedError"
}
```

---

## 2. Hợp đồng MarkdownImporter (`markdown_importer.py`)

### `import_text(text: str) -> ImportResult`

- **Quy tắc `ImportResult.unsupported` (bảo toàn tương thích ngược)**:
  - `code_block` / `fence`: `"code_block"` hoặc `f"code_block: {info}"`.
  - `hr`: `"hr: horizontal rule"`.
  - `table` trong danh sách: `"table: table inside list item"`.
  - `image`: `f"image: {alt}"` (khi có alt text, đồng thời giữ `Text(alt)` trong đoạn văn) hoặc `"image"` (khi không có alt text).
- **Quy tắc `ImportResult.warnings`**:
  - `blockquote_open`: thêm `"Khối trích dẫn (blockquote) đã được chuyển về đoạn văn viết tay tiêu chuẩn."` (không trùng lặp).
- **Quy tắc PUA & HTML Entity**:
  - Văn bản chứa `&#xE000;`, `&#XE000;`, `&#x00E000;`, `&#57344;`, `&#057344;` hoặc `\ue000` kết hợp công thức toán trong blockquote lồng nhau không bao giờ làm biến đổi ký tự của người dùng thành `$$`.
- **Quy tắc Escape Delimiter (`_convert_delimited`)**:
  - Đếm số dấu `\` liên tiếp ngay trước `opener` (`\(`, `\[`) và `closer` (`\)`, `\]`):
    - Số lẻ (`1, 3, 5...`) $\rightarrow$ delimiter bị thoát, giữ nguyên văn bản.
    - Số chẵn (`0, 2, 4...`) $\rightarrow$ delimiter hoạt động bình thường.

---

## 3. Hợp đồng Kiểm tra Hợp lệ `WriteOptions.validate()`

Ném ngoại lệ `ValueError` với thông điệp rõ ràng khi:
- Bất kỳ trường số học nào nhận giá trị `bool` (`True`/`False`) hoặc không phải `int`/`float` hữu hạn.
- `letter_gap < 0.0` hoặc `letter_gap > 10.0` hoặc `not math.isfinite(letter_gap)`.
- `target_xh <= 0.0` hoặc `target_xh > 100.0` hoặc `not math.isfinite(target_xh)`.
- `pen_clearance_factor < 0.0` hoặc `pen_clearance_factor > 10.0` hoặc `not math.isfinite(pen_clearance_factor)`.
- Bất kỳ cờ Boolean nào (`auto_xh`, `stable_variants`, `assemble_letters`, `snap_to_ruling`, `strict_case`, `missing_grid`) nhận giá trị không phải `bool`.

---

## 4. Hợp đồng Giao diện Web (`write.js` & `bank.js`)

### 4.1. Thông báo Web UI trong Tab Viết (`write.js`)
- Bảng thông báo `#editor-warnings` hiển thị kết hợp:
  - Các thông báo nạp tệp `.docx` đang hiệu lực (`pendingImportNotices`), không bị xóa mất bởi lượt `requestRender` tự động ngay sau khi mở tệp.
  - Các cảnh báo `res.warnings`.
  - Các mục không hỗ trợ `res.unsupported` (được định dạng sang thông báo tiếng Việt rõ nghĩa về loại thành phần và cách xử lý).

### 4.2. Cập nhật Tab Kho mẫu (`bank.js`)
- `refreshBankView(options = {})` gọi `sendWorkerFn("get_bank_snapshot")`.
- Đối chiếu `(snapshot.revision, activeProfileId)`: nếu không đổi và không có cờ `options.force`, bỏ qua việc dựng lại lưới thẻ DOM.
- Nếu phản hồi báo lỗi (`!res || !res.ok`), hiển thị thông báo lỗi trực tiếp trên giao diện tab Kho mẫu.
