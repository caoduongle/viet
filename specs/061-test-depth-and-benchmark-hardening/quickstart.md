# Quickstart & Validation Guide: Feature 061

**Feature**: `061-test-depth-and-benchmark-hardening`
**Date**: 2026-10-28

---

## 1. Chạy Kiểm thử Đóng Khối Toán Lồng Nhau & Bất biến Benchmark

```powershell
pytest tests/test_markdown_math_block_isolation.py -k "test_display_math_in_blockquote or test_adversarial" -v
```

**Kết quả kỳ vọng**:
- `test_display_math_in_blockquote_blank_line_exit_and_matching_depth_close`: Vượt qua — xác nhận chính xác cấu trúc chuỗi đầu ra không bị ngắt quãng dở dang bởi `>> $$` và `import_text()` sinh đúng 1 khối `MathBlock` duy nhất chứa đầy đủ biểu thức.
- `test_adversarial_complexity_multi_length_backticks_and_long_lines`: Vượt qua — vừa thỏa mãn $T(4N)/T(N) \le 6.0$, vừa thỏa mãn đầy đủ các bất biến về công thức toán (`$$display_formula$$`, `$$x=1$$`) và mã nguồn đại diện trên cả $N, 2N, 4N$.
- `test_adversarial_complexity_unclosed_backticks_and_blockquotes`: Vượt qua — khôi phục đúng trạng thái `gc.isenabled()`.

---

## 2. Kiểm thử Tính Độc Lập của Trạng Thái Garbage Collector

```powershell
python -c "import gc, pytest; gc.disable(); pytest.main(['tests/test_markdown_math_block_isolation.py', '-k', 'test_adversarial']); assert not gc.isenabled(), 'GC was unexpectedly re-enabled!'; print('GC State Hygiene: PASS!')"
```

**Kết quả kỳ vọng**:
- `GC State Hygiene: PASS!` — khi môi trường chạy test đã tắt GC, sau bài test GC vẫn ở trạng thái tắt.

---

## 3. Chạy Toàn bộ Kiểm tra Chất lượng (Lint, Unit, Golden Master, E2E)

```powershell
ruff check chuviettay tests scripts
pytest
npm run test:unit
npm run test:browser
node scripts/test_golden_pyodide.mjs
npm run test:e2e
```

**Kết quả kỳ vọng**:
- Ruff: 0 lỗi.
- Pytest (1,325+ tests), JS unit tests (65 tests), Browser tests (2 suites), Playwright E2E (19 tests): 100% vượt qua.
- Golden Master Pyodide: 8/8 ca khớp mã băm SHA-256 tuyệt đối.
