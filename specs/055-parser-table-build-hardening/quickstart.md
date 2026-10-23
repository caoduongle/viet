# Quickstart & Verification Guide: CommonMark Fences, Compact Tables & Build Safety

**Feature**: `055-parser-table-build-hardening`  
**Date**: 2026-10-23  

---

## 1. Prerequisites

- Python 3.12+ (với `pytest`, `ruff`)
- Node.js 20+ (với `npm test`)
- Đã cài đặt đầy đủ dependencies:
  ```bash
  pip install -r requirements-dev.txt
  npm ci
  ```

---

## 2. Validation Scenarios

### Kịch bản 1: Kiểm thử bảo toàn Code Fence & Code Span theo CommonMark
Kiểm tra rằng các khối mã có độ dài phân cách khác nhau và đoạn mã nội tuyến nhiều backtick không bị biến đổi công thức:
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "code_fence or code_span" -vv
```
*Kết quả kỳ vọng*: Cả test `test_code_fence_preservation` (bao gồm fence 4 backticks chứa dòng 3 backticks và `\[...\]`) và `test_code_span_preservation` (bao gồm ``prefix:$$x=1$$``) đều PASS 100%.

### Kịch bản 2: Kiểm thử bảo toàn Bảng GFM Compact với Công thức ở Ô Đầu Tiên
Kiểm tra rằng bảng compact `Col | Val\n---|---\n$$x=1$$ | 2` không bị xé dòng:
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "table" -vv
```
*Kết quả kỳ vọng*: `test_gfm_table_math_not_broken` và `test_gfm_compact_table_math_first_cell` PASS 100%, sinh ra đối tượng `Table` 2 hàng hoàn chỉnh.

### Kịch bản 3: Kiểm thử Hiệu năng Co giãn Tương đối Bền bỉ
Đo tỷ lệ tăng trưởng thời gian khi tăng gấp đôi kích thước tài liệu có nhiều `$$` không đóng:
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "scalability" -vv -s
```
*Kết quả kỳ vọng*: Tỷ lệ $T(2N) / T(N) \le 3.5$, thời gian thực thi $< 2.0$s, vượt qua ổn định trên mọi môi trường CI.

### Kịch bản 4: Kiểm thử Loại trừ Marker Khỏi Service Worker và Precache
Chạy bài kiểm thử đóng gói web để xác nhận không còn `.chuviettay_build_dist` trong `sw.js`:
```bash
python -m pytest tests/test_build_web.py -vv
```
*Kết quả kỳ vọng*: Tệp `sw.js` không chứa `.chuviettay_build_dist` trong `PRECACHE_URLS`, toàn bộ test trong `test_build_web.py` PASS.

### Kịch bản 5: Rà soát Lint và Toàn bộ Test Suite
```bash
ruff check .
python -m pytest tests/ -q
npm run test:unit
```
*Kết quả kỳ vọng*: Không có lỗi linter, 100% test Python và JavaScript đều xanh.
