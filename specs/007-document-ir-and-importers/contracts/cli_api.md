# Contract: CLI Interface API

**Feature**: `007-document-ir-and-importers`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Overview

The CLI interface (`chuviettay/cli.py`, invoked via `python hw_note.py` or `hw-note`) is updated to support multi-format document input with automatic format detection.

---

## 2. Command: `write`

```text
hw-note write [-h] [-b BANK] [-o OUT] [-f FILE] [--format {auto,txt,md,docx}]
              [--scale S] [--line L] [--width W] [--space SP] [--jitter J]
              [--wscale WS] [--color C] [--seed SEED] [--strict-case]
              [text ...]
```

### New Arguments
- `--format {auto,txt,md,docx}`: Explicitly sets input format parser. Default: `auto`.
  - When `auto`:
    - `.md`, `.markdown` -> Markdown parser.
    - `.docx` -> DOCX parser.
    - `.txt` -> Plain text parser (via Document IR).
    - Other/unrecognized extensions -> raises `UnsupportedFormatError` and exits with error code 1.
    - Text passed directly as CLI positional arguments -> Plain text parser.

### Diagnostics Output Contract
When writing documents with structured elements, the CLI prints:
1. Document summary:
   `Tài liệu: N đoạn, M tiêu đề, K bảng, P công thức`
2. Unsupported elements notice (if any):
   `Bỏ qua N thành phần không hỗ trợ: [danh sách]`
3. Handwriting result:
   `Đã ghi N trang, K dòng, S nét vào <out_path>`
4. Missing symbols notice (if any):
   `Ký hiệu toán chưa có mẫu: ∑ (3), ≤ (1)`
   `Đã tạo file lưới ô bổ sung: <out_path>_thieu.xopp`
