# CLI Interface Contract: `--no-missing-grid` Support

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](../spec.md)  

---

## 1. Command Syntax

```bash
# Writing text with missing grid disabled
hw-note write "văn bản mẫu" --no-missing-grid -o output.xopp

# Or via python module invocation
python -m chuviettay write "văn bản mẫu" --no-missing-grid -o output.xopp
```

## 2. Argument Specification

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--no-missing-grid` | Flag (`store_true`) | `False` | Tắt việc tự động tạo file luyện viết cho các từ/ký tự còn thiếu trong kho mẫu (`<output>_thieu.xopp`). |

## 3. Output Behavior

### When `--no-missing-grid` is omitted (default):
- If missing words or letters occur during synthesis:
  - If `<out>_thieu.xopp` does not exist or contains only guide lines, `<out>_thieu.xopp` is created.
  - If `<out>_thieu.xopp` contains user pen strokes, `<out>_thieu_2.xopp` (or first available `<out>_thieu_N.xopp`) is created.
  - Console report outputs:
    ```text
    Đã tạo file chữ thiếu: <path_to_missing_grid> (gồm N từ/ký tự)
    ```

### When `--no-missing-grid` is present:
- Missing words/letters are reported in the console warning, but **no** missing grid file is created on disk.
- Return code remains `0` if synthesis succeeds.
