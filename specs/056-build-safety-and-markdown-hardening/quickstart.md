# Quickstart & Verification Guide: External Build Safety & CommonMark Hardening

**Feature**: `056-build-safety-and-markdown-hardening`  
**Date**: 2026-10-23  

---

## 1. Prerequisites

- Python 3.12+ (với `pytest`, `ruff`)
- Node.js 20+ (với `npm test`)

---

## 2. Validation Scenarios

### Kịch bản 1: Kiểm thử An toàn Thư mục Ngoài có Tệp Người Dùng
```bash
python -m pytest tests/test_build_web.py -k "external" -vv
```
*Kết quả kỳ vọng*: Script từ chối xóa thư mục ngoài có chứa tệp người dùng khi không có cờ `--force-clean`.

### Kịch bản 2: Kiểm thử Khối mã Blockquote và Indented Code
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "nested or indented or escape" -vv
```
*Kết quả kỳ vọng*: Blockquote code fence và indented code block bảo toàn 100% công thức bên trong.

### Kịch bản 3: Kiểm thử Ngữ cảnh Bảng GFM và Giá trị Ô Compact
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "table" -vv
```
*Kết quả kỳ vọng*: Dòng đơn `$$x=1$$ | 2` tách thành MathBlock, bảng compact có đầy đủ dữ liệu cả 2 ô.

### Kịch bản 4: Kiểm thử Hiệu năng Toàn diện Pipeline
```bash
python -m pytest tests/test_markdown_math_block_isolation.py -k "scalability" -vv -s
```
*Kết quả kỳ vọng*: Tỷ lệ $T(2N) / T(N) \le 3.5$ trên toàn bộ luồng `_split_code_segments` và `_isolate_display_math_blocks`.

### Kịch bản 5: Rà soát Lint và Toàn bộ Test Suite
```bash
ruff check .
python -m pytest tests/ -q
npm run test:unit
```
*Kết quả kỳ vọng*: 100% xanh.
