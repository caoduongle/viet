# Quickstart: DOCX Fidelity Mode Validation Guide

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30

---

## Scenario 1: CLI Fidelity Replacement on Multi-Page DOCX with Images

### Prerequisites
- Python 3.10+ installed with dependencies.
- Sample handwriting bank available at `tests/data/kho_mau_tong_hop.json.gz`.
- Target DOCX file containing embedded images and tables (e.g. `tests/fixtures/sample.docx` or `problem_set_03_dap_an_ghi_chu.docx`).
- Microsoft Word (Windows) or LibreOffice installed on the system.

### Execution Command
```powershell
python -m chuviettay --bank tests/data/kho_mau_tong_hop.json.gz write tests/fixtures/sample.docx -o output_fidelity.xopp --mode fidelity
```

### Expected Output
1. Console reports:
   - Mode: `Fidelity mode: N trang, N hình ảnh, N bảng biểu được giữ nguyên.`
   - Generated files: `output_fidelity.xopp` and `output_fidelity_background.pdf`.
   - Token matching and missing sample statistics.
2. `output_fidelity_background.pdf` exists and contains original tables, borders, and images with all printed text (including shapes/textboxes) invisible/white.
3. `output_fidelity.xopp` contains `<background type="pdf" domain="relative" .../>` tags on all pages, with handwriting strokes in `<layer>`.

---

## Scenario 2: Fail-Fast Verification without Conversion Dependencies (P0)

### Execution Command (Simulated without Word / LibreOffice)
```powershell
python -m chuviettay --bank tests/data/kho_mau_tong_hop.json.gz write my_file.docx -o out.xopp --mode fidelity
```

### Expected Output
The process halts immediately with an explicit error:
```text
RuntimeError: Fidelity Mode yêu cầu Microsoft Word (Windows) hoặc LibreOffice (Linux/macOS) để xử lý bố cục cố định. Vui lòng cài đặt Microsoft Word hoặc sử dụng chế độ Semantic Mode (--mode semantic).
```
Zero dummy fixture files (`sample_fidelity_data.json` or `sample_background.pdf`) are used or written.

---

## Scenario 3: Python Controller API Integration

```python
from chuviettay.controller.app_controller import AppController
from chuviettay.model.composer import WriteOptions

ctl = AppController()
ctl.load_bank("tests/data/kho_mau_tong_hop.json.gz")

opts = WriteOptions(scale=1.0, mode="fidelity")
result = ctl.write_docx_fidelity(
    docx_path="tests/fixtures/sample.docx",
    opts=opts,
    out_path="sample_fidelity.xopp",
)

print(f"Total pages: {result.n_pages}")
print(f"Images preserved: {result.n_images}")
print(f"Strokes: {result.n_strokes}")
assert result.out_path == "sample_fidelity.xopp"
```

---

## Scenario 4: Verification with Automated Test Suite

```powershell
pytest tests/test_docx_fidelity.py -v
```

All fidelity test cases validate:
1. Exact preservation of page count (`n_pages`).
2. Complete retention of embedded images (`n_images`).
3. Accurate stroke placement within bounding boxes.
4. Clean whiteout of text across body, tables, and shapes.
5. Absolute zero-fixture fallback in production paths.
