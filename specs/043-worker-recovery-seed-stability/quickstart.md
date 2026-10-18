# Quickstart Validation Guide: Feature 043 — Worker Recovery & Render Seed Pipeline Hardening

**Branch**: `043-worker-recovery-seed-stability` | **Date**: 2026-10-18 | **Spec**: [spec.md](file:///d:/viet/app/specs/043-worker-recovery-seed-stability/spec.md)

---

## 1. Prerequisites
- Python 3.12+ with dev dependencies installed
- Node.js 20+ with npm dependencies installed
- Repository root directory: `d:\viet\app`

---

## 2. Validation Scenarios

### Scenario A: Web Worker Recovery & False-Positive Prevention
Validate that `recoverWorker()` handles error states, timeouts, and successful retries correctly without false positives.

```bash
# 1. Run unit tests for Worker resilience and recovery lifecycle
node --test tests/js/worker_resilience.test.mjs
```
**Expected Outcome**:
- Tests pass verifying that a failed worker, timed-out worker (10s), or `messageerror` resolves `recoverWorker()` to `false` and preserves `#btn-worker-retry`.
- Successful recovery restores the worker, loads the bank, hides `#btn-worker-retry`, and resolves to `true`.

---

### Scenario B: Storage Teach Count Concurrency & Transaction Safety
Validate that `incrementTeachCount()` and `resetTeachCount()` run atomically without unconditioned overwrite.

```bash
# 1. Run IndexedDB storage unit tests
npm run test:unit
```
**Expected Outcome**:
- Storage tests pass validating atomic read-modify-write on `teach_count_since_backup`, monotonic timestamp increments, and prevention of profile resurrection.

---

### Scenario C: Canonical Key Encoding & Seed Invariance
Validate collision-free key encoding and editing invariance in stable variant mode.

```bash
# 1. Run Python unit tests for ScopedRNG, derive_seed v2, and stable variants
pytest tests/test_stable_variants.py tests/test_rng.py -v
```
**Expected Outcome**:
- Canonical key encoding tests pass (distinct keys with different types/delimiters never collide).
- Invariance tests pass: inserting new tokens or duplicate words before existing tokens does not alter stroke variants or geometry of unmodified tokens.

---

### Scenario D: Baseline Golden Master Protection
Ensure 100% byte-exact reproducibility of default rendering (`stable_variants=False`).

```bash
# 1. Run the Golden Master test suite in Pyodide
node scripts/test_golden_pyodide.mjs
```
**Expected Outcome**:
- 8/8 test cases match their reference SHA-256 hashes with 0 mismatches.

---

### Scenario E: Full Quality Gates
Execute the complete quality verification pipeline.

```bash
# 1. Python Lint & Bytecode Compilation
ruff check .
python -m compileall -q .

# 2. Python Core Test Suite
pytest -q -m "not benchmark"

# 3. Web Client Build
python scripts/build_web.py

# 4. Playwright End-to-End Test Suite
npx playwright test
```
**Expected Outcome**:
- All 19 Playwright E2E tests, 36+ JS tests, and 1234+ Python tests pass cleanly with 0 regressions.
