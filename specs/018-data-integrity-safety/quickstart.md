# Quickstart & Verification Guide: Data Integrity Safety Net (P0)

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](./spec.md)  

---

## 1. Prerequisites & Environment Setup

Ensure testing dependencies and linter are installed:

```bash
# Verify Python version (3.10, 3.12, or 3.14)
python --version

# Run linter check
python -m ruff check .
```

On Windows, ensure UTF-8 console output is enabled:
```powershell
$env:PYTHONUTF8="1"
```

---

## 2. End-to-End Reproduction Suite

Run the provided Phase 0 verification suite to validate all bug fixes:

```bash
# Verify all Phase 0 items
python repro_viet_baseline.py --repo . --only D1a D1b D2 D3 D4a D4b D5
```

**Expected Outcome**:
```text
[ĐÃ SỬA  ] D1a  Xoá CHỮ CÁI 'a' rồi lưu có hợp nhất làm mất luôn TỪ 'a'
[ĐÃ SỬA  ] D1b  Chọn TỪ 'a' ở tab Kho mẫu rồi xoá lại xoá nhầm CHỮ CÁI 'a'
[ĐÃ SỬA  ] D2   Xoá ký hiệu rồi dạy lại bằng add_symbol_sample: mẫu mới mất sau lần hợp nhất kế
[ĐÃ SỬA  ] D3   learn không idempotent: lưu lại cùng tờ lưới (header gzip đổi) bị học trùng
[ĐÃ SỬA  ] D4a  WriteOptions(missing_grid=False) bị bỏ qua ở chế độ Semantic; CLI không có --no-missing-grid
[ĐÃ SỬA  ] D4b  Chạy lại write ghi đè ra_thieu.xopp, mất nét người dùng đã viết dở
[ĐÃ SỬA  ] D5   Lưu hoãn trên luồng Timer: RuntimeError 'dictionary changed size during iteration'

Tổng: 7 mục | BUG: 0 | ĐÃ SỬA: 7 | LỖI-CHẠY: 0 | BỎ-QUA: 0
```

---

## 3. Automated Regression Verification

### 3.1 Golden-Master Real Path (Step 0)

Verify that the real production layout engine produces deterministic, invariant XML output:

```bash
python -m pytest tests/test_golden_master_real_path.py -v
python -m pytest tests/test_golden_master.py -v
```

**Expected Outcome**: Both suites pass with 100% green tests; all computed SHA-256 hashes match reference digests.

### 3.2 Bank Concurrency & Persistence (D1, D2, D5)

```bash
python -m pytest tests/test_bank.py -v
```

**Expected Outcome**: All persistence tests pass, atomic temporary file handling is validated, and multi-threaded debounce saving completes with zero errors.

### 3.3 Missing Grid & CLI Options (D4)

```bash
python -m pytest tests/test_cli.py -k "missing_grid" -v
python -m pytest tests/test_cli_format.py -v
```

### 3.4 Architecture & Quality Gate

```bash
python -m pytest tests/test_architecture.py -v
python -m ruff check .
```

**Expected Outcome**: Zero architectural boundary violations (`view` -> `controller`, `model` isolated), and zero ruff lint errors.
