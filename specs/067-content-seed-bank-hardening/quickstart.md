# Quickstart: Hướng dẫn Kiểm chứng Tính năng 067

**Feature**: `067-content-seed-bank-hardening`  
**Date**: 2026-10-31  
**Spec Reference**: [spec.md](./spec.md)

---

## 1. Môi trường Yêu cầu (Prerequisites)

- Python 3.10+ (đã cài đặt `pytest`, `markdown_it`, `mdit_py_plugins`).
- Node.js (tùy chọn cho bộ kiểm thử đơn vị JavaScript trong `tests/web/`).

---

## 2. Kịch bản Kiểm chứng Từng bước (Validation Scenarios)

### Kịch bản 1: Kiểm chứng Thông báo Không Hỗ trợ từ Markdown sang Cầu nối Web (P1)

```powershell
python -m pytest tests/test_markdown_math_import.py tests/test_importer_fidelity.py -vv
python -m pytest tests/test_browser_bridge.py -k "unsupported" -vv
```

**Kết quả kỳ vọng**:
- `MarkdownImporter` bảo toàn hợp đồng `["hr: horizontal rule", "code_block: python"]`, bổ sung ghi nhận `"image..."` vào `unsupported` (giữ lại văn bản thay thế nếu có) và ghi nhận thông báo làm phẳng `blockquote` vào `warnings`.
- `BrowserBridge.write_text` trả về đầy đủ cả `warnings` và `unsupported` trong phản hồi JSON.

---

### Kịch bản 2: Kiểm chứng Chống va chạm PUA qua HTML Entity & Sửa Delimiter Escape (P1)

```powershell
python -m pytest tests/test_markdown_math_block_isolation.py -k "pua or entity or escape" -vv
```

**Kết quả kỳ vọng**:
- Đầu vào chứa `&#xE000;`, `&#x00E000;`, `&#57344;` hoặc `&#057344;` kèm công thức trong blockquote lồng nhau không bao giờ bị biến thành `$$` sau khi phân tích cú pháp.
- Số chẵn dấu `\` trước delimiter (`\(x\)`, `\\\(x\\\)`, `\\\\\(x\\\\\)`) được nhận diện là công thức toán hợp lệ; số lẻ dấu `\` trước delimiter (`\\(x\\)`, `\\\\(x\\\\)`) được giữ nguyên làm văn bản thường; nội dung trong khối mã được bảo toàn 100%.

---

### Kịch bản 3: Kiểm chứng Ổn định Seed cho Tài liệu Lặp & Kiểm tra `WriteOptions` (P2)

```powershell
python -m pytest tests/test_stable_variants.py -k "repeat or long" -vv
python -m pytest tests/test_composer.py -k "validate" -vv
```

**Kết quả kỳ vọng**:
- Chèn hoặc xóa đoạn văn ở giữa tài liệu có 300–1.000 từ lặp lại bảo toàn 100% `occurrence` và tọa độ hình học nét chữ của tất cả các từ không đổi ở cả nửa đầu và nửa sau tài liệu.
- `WriteOptions.validate()` từ chối mọi giá trị âm, `NaN`, `Infinity`, vượt ngưỡng trên hoặc sai kiểu `bool` cho `letter_gap`, `target_xh`, `pen_clearance_factor` và các cờ Boolean.

---

### Kịch bản 4: Kiểm chứng Bản chụp Kho mẫu Một Lượt (`get_bank_snapshot`) (P3)

```powershell
python -m pytest tests/test_browser_bridge.py -k "snapshot" -vv
```

**Kết quả kỳ vọng**:
- `get_bank_snapshot` trả về đầy đủ `stats`, `letters`, `digits`, `punct`, `symbols`, `marks` và `revision` trong 1 lượt gọi.
- `revision` tăng đơn điệu sau mỗi thao tác thay đổi kho mẫu và được điều phối đầy đủ qua `webapp/js/worker/py-worker.js`.

---

### Kịch bản 5: Chạy Kiểm thử Hồi quy Hiệu năng (Performance Regression) (P3)

```powershell
# Chạy kiểm thử bất biến hiệu năng trong luồng CI chuẩn
python -m pytest tests/test_performance_regression.py -m "not benchmark" -vv

# Chạy đo kiểm benchmark chi tiết theo yêu cầu
python -m pytest tests/test_performance_regression.py -m "benchmark" -vv -s
```

**Kết quả kỳ vọng**:
- Các bài kiểm thử mặc định trên CI chạy ổn định, xác nhận cắt bỏ tiền tố/hậu tố $O(N)$ + `SequenceMatcher(..., autojunk=False)` hoàn tất nhanh và chính xác.
- Các bài đo `@pytest.mark.benchmark` xuất số liệu thời gian và bộ nhớ cho Markdown (10 KB, 100 KB, 1 MB), seed alignment và bank snapshot.
