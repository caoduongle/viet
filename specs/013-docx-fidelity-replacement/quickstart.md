# Quickstart: DOCX Fidelity Mode Validation Guide

**Feature Branch**: `013-docx-fidelity-replacement` | **Date**: 2026-09-30

---

## Scenario 1: CLI Fidelity Replacement on Multi-Page DOCX with Images

### Prerequisites
- Python 3.10+ installed with dependencies.
- Sample handwriting bank available at `tests/data/kho_mau_tong_hop.json.gz`.
- Target DOCX file containing embedded images and tables (e.g. `tests/fixtures/sample.docx` or `problem_set_03_dap_an_ghi_chu.docx`).

### Execution Command
```powershell
python -m chuviettay --bank tests/data/kho_mau_tong_hop.json.gz write tests/fixtures/sample.docx -o output_fidelity.xopp --mode fidelity
```

### Expected Output
1. Console reports:
   - Mode: `Fidelity (Fixed Layout & Non-Text Preservation)`
   - Generated files: `output_fidelity.xopp` and `output_fidelity_background.pdf`.
   - Processed page count, text blocks replaced, and images preserved.
2. `output_fidelity_background.pdf` exists and contains the original tables, borders, and images with printed text invisible/white.
3. `output_fidelity.xopp` contains `<background type="pdf" .../>` tags on all pages, with handwriting strokes in `<layer>`.

---

## Scenario 2: Python Controller API Integration

```python
from chuviettay.controller.app_controller import AppController
from chuviettay.model.composer import WriteOptions

ctl = AppController()
ctl.load_bank("tests/data/kho_mau_tong_hop.json.gz")

opts = WriteOptions(scale=1.0)
result = ctl.write_docx_fidelity(
    docx_path="tests/fixtures/sample.docx",
    opts=opts,
    out_path="sample_fidelity.xopp",
)

print(f"Total pages: {result.n_lines}") # or specialized fidelity stats
print(f"Strokes: {result.n_strokes}")
assert result.out_path == "sample_fidelity.xopp"
```

---

## Scenario 3: Verification with Automated Test Suite

```powershell
pytest tests/test_docx_fidelity.py -v
```

All fidelity test cases validate:
1. Exact preservation of page count.
2. Complete retention of embedded images.
3. Accurate stroke placement within bounding boxes.
4. Clean fallback to semantic mode when explicitly requested.
