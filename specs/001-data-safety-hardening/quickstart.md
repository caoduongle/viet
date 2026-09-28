# Quickstart Validation Guide: Data Safety and Core Reliability Hardening

**Feature**: `001-data-safety-hardening` | **Date**: 2026-09-29

## Prerequisites

- Python 3.10+ installed
- `pip install pytest filelock` (or `pip install -r requirements-dev.txt`)
- Repository cloned at `d:\viet\app` (or equivalent)

---

## Validation Scenario 1: Personal Data Removed from Source

**Purpose**: Confirm personal handwriting data is excluded from version control and test fixtures are independent.

```bash
# 1. Verify .gitignore blocks personal bank
grep "^chu_cua_ban.json.gz" .gitignore
# Expected: line "chu_cua_ban.json.gz" (uncommented)

# 2. Verify personal bank is untracked
git status --porcelain chu_cua_ban.json.gz
# Expected: no output (file untracked/ignored) or "!! chu_cua_ban.json.gz"

# 3. Verify test fixture has a different SHA than any personal file
git hash-object tests/data/kho_mau_tong_hop.json.gz
# Expected: a SHA different from 9a6a420a51e38cd2e7c8a81b3818cf2e291e44fe

# 4. Run tests to confirm they pass without personal data
python -m pytest tests/test_bank.py -q
# Expected: all tests pass
```

---

## Validation Scenario 2: GUI --bank Typo Protection

**Purpose**: Confirm explicit `--bank` path that does not exist causes an error, not silent creation.

```bash
# 1. Try to launch GUI with non-existent path
python hw_gui.py --bank /nonexistent/path/bank.json.gz
# Expected: Error dialog or error message, NOT a new empty file at that path

# 2. Verify no file was created
ls /nonexistent/path/bank.json.gz 2>/dev/null
# Expected: file does not exist

# 3. Launch GUI with no --bank (default path, first-time user)
python hw_gui.py
# Expected: If default bank missing, creates empty bank at default location (OK for onboarding)
```

---

## Validation Scenario 3: Bank Schema Validation

**Purpose**: Confirm corrupted/legacy/future-version files are handled gracefully.

```bash
# Run the bank validation test suite
python -m pytest tests/test_bank.py -q -k "schema or corrupt or validation or version"
# Expected: All pass. Test cases include:
#   - Empty file → BankCorruptedError
#   - Invalid gzip → BankCorruptedError
#   - Invalid JSON → BankCorruptedError
#   - Missing "words" key → BankValidationError
#   - Future schema_version → UnsupportedSchemaVersionError
#   - Legacy bank (no schema_version) → loads successfully and migrates in-memory
```

---

## Validation Scenario 4: Concurrent Save Safety

**Purpose**: Confirm two processes saving simultaneously do not corrupt the bank.

```bash
# Run the concurrent save test
python -m pytest tests/test_bank.py -q -k "concurrent or lock"
# Expected: All pass. Simulated concurrent writes result in zero data corruption.
```

---

## Validation Scenario 5: WriteOptions Validation

**Purpose**: Confirm invalid options are rejected before document generation.

```bash
# Run the write options validation tests
python -m pytest tests/test_composer.py -q -k "invalid or validate or color"
# Expected: All pass. Invalid inputs (negative scale, NaN, malformed color) → ValueError.
```

---

## Validation Scenario 6: CI Pipeline

**Purpose**: Confirm GitHub Actions workflow is syntactically valid and runs.

```bash
# Validate workflow syntax locally (requires act or yamllint)
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
# Expected: No error

# Run full test suite locally (same as CI)
python -m compileall -q .
python -m pytest -q
# Expected: All pass
```

---

## Validation Scenario 7: Golden-Master Regression

**Purpose**: Confirm core handwriting algorithms are untouched.

```bash
python -m pytest tests/test_golden_master.py -q
# Expected: All 4 golden-master tests pass with unchanged SHA-256 hashes.
# If any fail, the core algorithm has been inadvertently modified.
```

---

## Cross-Reference

- **Data model details**: See [data-model.md](data-model.md)
- **Validation contracts**: See [contracts/write-options.md](contracts/write-options.md)
- **Schema contracts**: See [contracts/bank-schema.md](contracts/bank-schema.md)
- **Persistence contracts**: See [contracts/bank-persistence.md](contracts/bank-persistence.md)
