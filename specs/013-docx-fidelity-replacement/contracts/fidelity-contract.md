# Contract: DOCX Fidelity In-Place Replacement Interface

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30

---

## 1. Controller Interface

```python
class AppController:
    def write_docx_fidelity(
        self,
        docx_path: str,
        opts: WriteOptions,
        out_path: str,
    ) -> WriteResult:
        """
        Thực hiện thay thế chữ in bằng chữ viết tay theo chế độ Fidelity Mode:
        - Giữ nguyên 100% số trang, kích thước từng trang và vị trí đồ họa.
        - Giữ nguyên toàn bộ ảnh nhúng (inline/drawing) và cấu trúc bảng ở tệp nền.
        - Đặt các nét viết tay (handwritten strokes) khớp vào đúng bounding box của từng đoạn văn/từ.
        - Xuất tệp .xopp đa trang trỏ tới companion background PDF.
        """
        ...
```

### Preconditions
- `docx_path` must exist and be a valid `.docx` OpenXML archive.
- `opts` must pass `opts.validate()`.
- A valid handwriting bank must be loaded in the controller (`self.bank is not None`).

### Postconditions
- Produces `out_path` (`.xopp` format).
- Produces companion PDF background `<basename>_background.pdf` in the same directory as `out_path`.
- Returns `WriteResult` with accurate line/stroke/token/table counts and missing token warnings.

---

## 2. CLI Interface Contract

```bash
# Thực thi chế độ Fidelity (giữ nguyên layout & ảnh)
python -m chuviettay write problem_set_03.docx -o output.xopp --mode fidelity

# Thực thi chế độ Semantic (reflow tự do)
python -m chuviettay write problem_set_03.docx -o output.xopp --mode semantic
```

### Arguments
- `--mode`: Choice of `['fidelity', 'semantic']`. Default is `semantic` (backward compatible), with auto-suggestion to `fidelity` when images are detected.
- All existing options (`--scale`, `--jitter`, `--space`, `--line`) remain valid and are applied to calibrate handwriting within bounding boxes.

---

## 3. XOPP Output Format Specification

For each page $i \in [0, N-1]$ in `out_path`:
```xml
<page width="595.28" height="841.89">
  <background type="pdf" domain="absolute" filename="problem_set_03_handwriting_background.pdf" pageno="0"/>
  <layer>
    <stroke tool="pen" color="#333399ff" width="1.41">
      100.5 200.3 102.1 202.4 ...
    </stroke>
  </layer>
</page>
```
