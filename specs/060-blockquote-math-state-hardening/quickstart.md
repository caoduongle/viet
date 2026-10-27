# Quickstart & Validation Guide: Feature 060

**Feature**: `060-blockquote-math-state-hardening`
**Date**: 2026-10-28

---

## 1. Chạy Kiểm thử Trạng thái Khối Toán Blockquote & Bất biến Nội dung

```powershell
pytest tests/test_markdown_math_block_isolation.py -v
```

**Kết quả kỳ vọng**:
- `test_display_math_in_blockquote_exits_on_dedent`: Vượt qua — công thức `$$y=2$$` ở ngoài trích dẫn (hoặc ở cấp trích dẫn nông hơn) ngay sau khối toán trích dẫn chưa đóng `> $$\n> x = 1` được tách thành `MathBlock("y=2")`.
- `test_code_fence_in_blockquote_auto_closes_on_dedent`: Vượt qua — xác nhận đầy đủ cả `x=2` và `y=3`.
- `test_pipeline_code_preservation_and_outside_math_invariants`: Vượt qua — mọi khối code fence và indented code block được bảo toàn từng ký tự; mọi công thức ngoài code được tách đúng.
- `test_adversarial_complexity_multi_length_backticks_and_long_lines`: Vượt qua — vừa thỏa mãn $T(4N)/T(N) \le 6.0$, vừa thỏa mãn các bất biến bảo toàn nội dung trên cả $N, 2N, 4N$.

---

## 2. Chạy Toàn bộ Kiểm tra Chất lượng (Lint, Unit, Golden Master, E2E)

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
- Pytest, JS unit tests, Browser tests, Playwright E2E: 100% vượt qua.
- Golden Master Pyodide: 8/8 ca khớp mã băm SHA-256 tuyệt đối.
